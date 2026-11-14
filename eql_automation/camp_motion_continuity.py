"""Read-only input continuity through camp; no authority to resume movement.

Arrival heading/speed are historical estimates. No physical input does not
exclude forced movement, auto-facing or speed changes during combat. A later
route must obtain fresh stopped positions and heading/motion evidence.
"""
from dataclasses import asdict
from hashlib import sha256
import json
import math

from .camp_floor_checkpoint import CampFloorCheckpoint
from .camp_contact_checkpoint import CampContactCheckpoint


def arrival_motion_basis(runtime, pending,checkpoint=None):
    if pending['session'].record_id!=runtime.ledger.bounds.calibration_record_id:
        raise ValueError('Arrival bounds and original calibration differ')
    return _arrival_basis(runtime,checkpoint=checkpoint)


def camp_route_motion_basis(runtime, calibration,checkpoint=None):
    """Record fresh route steering separately from its historical bound ID."""
    fit=calibration['estimate'];estimate=fit['estimate'];motion=runtime.ledger.motion
    if (calibration['status']!='conditional' or any(getattr(motion,k)!=estimate[k]
            for k in ('run_speed','turn_rate','right_sign','turn_latency'))):
        raise ValueError('Arrival motion differs from its sealed camp fit')
    return _arrival_basis(runtime,dict(camp_fit_record_id=fit['record_id'],
        camp_fit_sha256=sha256(json.dumps(calibration,sort_keys=True,separators=(',',':'),
            allow_nan=False).encode()).hexdigest(),motion_bounds_verified=False),checkpoint=checkpoint)


def _arrival_basis(runtime, extra=None,checkpoint=None):
    if type(checkpoint) is CampContactCheckpoint:
        if checkpoint._arrival is not runtime.completed_arrival:
            raise ValueError('Contact motion basis must belong to the exact completed arrival')
        record=json.loads(checkpoint.motion_basis());record.update(extra or {})
        return json.dumps(record,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    ledger=runtime.ledger;reference=runtime.completed_arrival.reference
    heading=ledger.pose.heading
    if type(heading) not in (int,float) or not math.isfinite(heading) or not 0<=heading<360:
        raise ValueError('Arrival heading estimate is unavailable')
    record=dict(format='eql-camp-arrival-motion-v1',
        itinerary_sha256=runtime.completed_arrival.itinerary_sha256,
        floor_proof_sha256=ledger.chain.previous.proof_sha256,
        arrival_position=reference.package_xyz,arrival_log_seq=reference.raw_fix.log_line_seq,
        arrival_received_at=reference.raw_fix.received_monotonic,
        arrival_heading_estimate=heading,motion=asdict(ledger.motion),bounds=asdict(ledger.bounds),
        calibration_record_id=ledger.bounds.calibration_record_id,
        current_heading_verified=False,current_motion_verified=False,movement_authorized=False)
    record.update(extra or {})
    return json.dumps(record,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


class CampInputContinuity:
    """Own the original observer until camp ends; invalidation is permanent."""
    def __init__(self,observer,*,topology,basis,binding,clock,floor=None):
        if (type(basis) is not bytes or not basis or type(topology) is not int
                or floor is not None and type(floor) not in (CampFloorCheckpoint,CampContactCheckpoint)):
            raise ValueError('Camp requires copied arrival metadata and input topology')
        self.observer=observer;self.topology=topology;self.basis=basis
        self.binding=binding;self.clock=clock;self.valid=True;self.closed=False
        self.reason='';self.last_observed_at=None;self.samples=0
        self.basis_sha256=sha256(basis).hexdigest()
        self._context=(observer,topology,basis,binding,clock)
        self.floor=self._floor_context=floor

    def invalidate(self,reason):
        if self.valid:self.reason=str(reason)
        self.valid=False
        if self._floor_context is not None:self._floor_context.invalidate(reason)

    def check_binding(self,binding):
        # The first six members are live objects and must retain identity.
        if (not self.valid or self.closed or self.observer is not self._context[0] or
                self.topology!=self._context[1] or self.basis is not self._context[2] or
                self.binding is not self._context[3] or self.clock is not self._context[4] or
                self.floor is not self._floor_context or
                len(binding)!=len(self.binding) or
                any(a is not b for a,b in zip(binding[:6],self.binding[:6])) or
                binding[6:]!=self.binding[6:] or sha256(self.basis).hexdigest()!=self.basis_sha256):
            self.invalidate('Camp movement-observation binding changed')
            raise ValueError(self.reason)
        if self.floor is not None:
            try:self.floor._assert_intact()
            except Exception as error:
                self.invalidate(str(error));raise ValueError(self.reason) from error

    def check(self,binding):
        self.check_binding(binding)
        try:
            if self.floor is not None:self.floor.check()
            self.check_binding(binding)
            sample=self.observer.sample();now=self.clock()
            if (not sample.clear_at(now) or sample.topology_generation!=self.topology or
                    self.last_observed_at is not None and sample.started_at<self.last_observed_at):
                raise ValueError('Physical input or observation continuity changed during camp')
            self.check_binding(binding)
        except Exception as error:
            self.invalidate(str(error));raise ValueError(self.reason) from error
        self.last_observed_at=sample.finished_at;self.samples+=1

    def close(self,reason):
        self.invalidate(reason)
        if self.closed:return
        self.closed=True
        self.observer.close()

    def transfer_to(self,successor):
        """Retire this historical scope without closing the shared observer."""
        if (type(successor) is not CampInputContinuity or successor is self
                or successor.observer is not self.observer or successor.topology!=self.topology
                or successor.floor is None or successor.floor is self.floor):
            raise ValueError('New camp must own the same observer and a new reached floor')
        self.check_binding(self.binding)
        successor.check_binding(successor.binding)
        if (self.last_observed_at is not None and (successor.last_observed_at is None
                or successor.last_observed_at<self.last_observed_at)):
            raise ValueError('New camp input observation cannot move backward')
        self.invalidate('Input observer transferred to the newly reached camp')
        self.closed=True

    def snapshot(self,*,include_basis=False):
        result=dict(valid=self.valid,closed=self.closed,reason=self.reason,samples=self.samples,
            last_observed_at=self.last_observed_at,basis_sha256=self.basis_sha256,
            movement_authorized=False,current_heading_verified=False,current_motion_verified=False)
        if include_basis:result['arrival_basis']=json.loads(self.basis)
        if self._floor_context is not None:
            result['arrival_floor']=self._floor_context.snapshot(include_evidence=include_basis)
        return result
