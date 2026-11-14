"""Receipt and stopped-floor evidence for one unknown-heading camp probe.

This ledger sends no input and issues no input permission. A future executor
must supply independently current scene/motion evidence and a receipt from its
actual selected-key sender. Geometry and synthetic receipts do not supply that
authority. Neither historical calibration nor an old owner declaration is reused.
"""
from dataclasses import asdict,dataclass,field
from datetime import datetime
from hashlib import sha256
import json
import math
import threading

from .camp_probe_preparation import CampProbePreparation,CampProbeStart,_height_state,_raw_record
from .flat_record import flat_record_state
from .ground_binding import finite,point
from .ground_sweep import motion_footprint
from .location_log import RawLocationFix
from .native_region_policy import encoded
from .route_floor_commit import _chain_snapshot
from .source_probe_geometry import check_source_footprint
from .source_floor_chain import inside,rational
from .uinput_watchdog import PulseReceipt


@dataclass(frozen=True)
class CampProbeTicket:
    start: CampProbeStart
    preparation_sha256: str
    kind: str
    movement_key: int
    requested_seconds: float
    maximum_actual_hold: float
    proposed_at: float
    input_authorized: bool=field(default=False,init=False)


@dataclass(frozen=True)
class CampProbeSeal:
    ticket: CampProbeTicket
    receipt: PulseReceipt
    sealed_at: float
    expires_at: float
    input_authorized: bool=field(default=False,init=False)
    sender_origin_verified: bool=field(default=False,init=False)


@dataclass(frozen=True)
class CampProbeResult:
    seal: CampProbeSeal
    first: RawLocationFix
    second: RawLocationFix
    package_xyz: tuple
    raw_z_minus_source_z: float
    observed_at: float
    expires_at: float
    payload: bytes
    sha256: str
    input_authorized: bool=field(default=False,init=False)
    current_motion_verified: bool=field(default=False,init=False)
    real_client_accepted: bool=field(default=False,init=False)
    sender_origin_verified: bool=field(default=False,init=False)


class CampProbeTransaction:
    """One proposal, one release, one prepared endpoint and a fresh confirmation."""
    def __init__(self,preparation,*,stop_lock):
        from .camp_probe_floor import CampProbeFloorReference
        if (type(preparation) is not CampProbePreparation
                or not isinstance(stop_lock,type(threading.RLock()))):
            raise ValueError('Exact camp probe preparation and shared stop lock required')
        if (type(preparation.checkpoint) is CampProbeFloorReference
                and stop_lock is not preparation.checkpoint._transaction.lock):
            raise ValueError('Continued probes must share the original stop lock')
        self.preparation=preparation;self.lock=stop_lock
        self._context=(preparation,stop_lock)
        self.phase='new';self.reason=''
        self.ticket=self.seal=self.result=None
        self._ticket_state=self._seal_state=self._result_state=None
        self._envelope=self._endpoint=None;self._endpoint_state=None
        self._planning_pair=self._planning_position=self._planning_offset=None
        self._endpoint_payload=None;self._confirmation_deadline=None
        self._geometry_state=None
        self._continuation=None
        preparation.check()

    def cancel(self,reason):
        with self.lock:
            if self.phase=='stopped':return
            self.phase='stopped';self.reason=str(reason)
            self._envelope=self._endpoint=self._endpoint_state=None
            self._geometry_state=None
            self.result=self._result_state=None
            self.preparation.cancel(self.reason)
            if self._continuation is not None:self._continuation.invalidate(self.reason)

    @staticmethod
    def _ticket_values(ticket):
        s=ticket.start;h=s.height
        return (id(ticket),id(s),id(h),_height_state(h),id(h.first),id(h.second),
                (flat_record_state(h.first),flat_record_state(h.second)),
                s.preparation_sha256,s.observed_at,s.expires_at,s.input_authorized,
                s.current_motion_verified,ticket.preparation_sha256,ticket.kind,ticket.movement_key,
                ticket.requested_seconds,ticket.maximum_actual_hold,ticket.proposed_at,ticket.input_authorized)

    @staticmethod
    def _seal_values(seal):
        return (id(seal),id(seal.ticket),id(seal.receipt),flat_record_state(seal.receipt),
                seal.sealed_at,seal.expires_at,seal.input_authorized,seal.sender_origin_verified)

    @staticmethod
    def _result_values(result):
        return (id(result),id(result.seal),id(result.first),id(result.second),
                (flat_record_state(result.first),flat_record_state(result.second)),
                result.package_xyz,result.raw_z_minus_source_z,result.observed_at,result.expires_at,
                result.payload,result.sha256,result.input_authorized,result.current_motion_verified,
                result.real_client_accepted,result.sender_origin_verified)

    def _geometry_values(self):
        a,b=self._planning_pair
        return (id(self._endpoint),id(a),id(b),(flat_record_state(a),flat_record_state(b)),
                self._planning_position,self._planning_offset,self._endpoint_payload,
                self._confirmation_deadline)

    def _check(self):
        if (self.phase=='stopped' or self.preparation is not self._context[0]
                or self.lock is not self._context[1]):
            raise ValueError(self.reason or 'Camp probe transaction changed')
        now=self.preparation.check()
        self._assert_context()
        return now

    def _assert_context(self):
        """Provider-free transaction identity/evidence checks for ancestry."""
        if (self.phase=='stopped' or self.preparation is not self._context[0]
                or self.lock is not self._context[1]
                or self._ticket_state is not None and (type(self.ticket) is not CampProbeTicket
                    or self._ticket_values(self.ticket)!=self._ticket_state
                    or self.preparation.phase!='consumed'
                    or self.preparation._start is not self.ticket.start)
                or self._seal_state is not None and (type(self.seal) is not CampProbeSeal
                    or self._seal_values(self.seal)!=self._seal_state)
                or self._result_state is not None and (type(self.result) is not CampProbeResult
                    or self._result_values(self.result)!=self._result_state)
                or self._envelope is not None and self._envelope is not self.preparation._envelope
                or self._geometry_state is not None and (self._endpoint is None
                    or self._geometry_values()!=self._geometry_state
                    or _chain_snapshot(self._endpoint)!=self._endpoint_state)):
            raise ValueError('Camp probe evidence or scope changed')

    def stage(self,start,*,movement_key,requested_seconds):
        """Record the selected proposal after sender READY; never authorizes DOWN."""
        with self.lock:
            try:
                now=self._check();p=self.preparation;b=p.bounds
                if (self.phase!='new' or type(start) is not CampProbeStart
                        or type(movement_key) is not int
                        or movement_key!={'forward':103,'left':105,'right':106}[p.kind]
                        or not finite(requested_seconds)
                        or not b.minimum_requested_hold<=requested_seconds<=b.maximum_requested_hold):
                    raise ValueError('Exact unused start and bounded selected key required')
                self.phase='staging'
                envelope=p.consume_start(start)
                # Context callbacks above can advance time or cancel. Retain the
                # last checked time and never give an old start a new expiry.
                now=self._check()
                if (self.phase!='staging' or p.phase!='consumed' or p._start is not start
                        or not start.observed_at<=now<=start.expires_at
                        or p.reader.latest is not start.height.second
                        or p.reader.log_line_seq!=start.height.second.log_line_seq):
                    raise ValueError('Camp probe start expired before proposal')
                ticket=CampProbeTicket(start,p.sha256,p.kind,movement_key,requested_seconds,
                                       b.maximum_actual_hold,now)
                self.ticket=ticket;self._ticket_state=self._ticket_values(ticket)
                self._envelope=envelope;self.phase='proposed'
                finished=self._check()
                if (self.phase!='proposed' or finished>start.expires_at
                        or p.reader.latest is not start.height.second
                        or p.reader.log_line_seq!=start.height.second.log_line_seq):
                    raise ValueError('Camp probe start changed before proposal return')
                return ticket
            except BaseException as error:self.cancel(str(error));raise

    def seal_release(self,ticket,receipt):
        with self.lock:
            try:
                now=self._check();p=self.preparation
                if (self.phase!='proposed' or ticket is not self.ticket
                        or type(receipt) is not PulseReceipt):
                    raise ValueError('Exact pending ticket and actual pulse receipt required')
                stamps=(receipt.down_started_at,receipt.down_completed_at,
                        receipt.up_started_at,receipt.up_completed_at)
                receipt_bytes=encoded(asdict(receipt))
                if (receipt.completion!='elapsed' or type(receipt.key_code) is not int
                        or receipt.key_code!=ticket.movement_key
                        or receipt.requested_seconds!=ticket.requested_seconds
                        or not all(finite(v) for v in stamps)
                        or not ticket.proposed_at<=stamps[0]<=stamps[1]<=stamps[2]<=stamps[3]<=now
                        or stamps[2]<=stamps[1]
                        or stamps[2]-stamps[1]+1e-9<ticket.requested_seconds
                        or stamps[0]>ticket.start.expires_at
                        or stamps[0]-ticket.proposed_at>.05 or now-stamps[3]>.3
                        or not 0<receipt.maximum_held_seconds<=ticket.maximum_actual_hold
                        or p.reader.latest is not ticket.start.height.second
                        or p.reader.log_line_seq!=ticket.start.height.second.log_line_seq):
                    raise ValueError('Camp probe release differs from selected timing/key/start')
                finished=self._check()
                if (self.phase!='proposed' or not now<=finished<=stamps[3]+.3
                        or receipt_bytes!=encoded(asdict(receipt))
                        or p.reader.latest is not ticket.start.height.second
                        or p.reader.log_line_seq!=ticket.start.height.second.log_line_seq):
                    raise ValueError('Camp probe release changed or expired during sealing')
                seal=CampProbeSeal(ticket,receipt,finished,stamps[3]+10.)
                self.seal=seal;self._seal_state=self._seal_values(seal);self.phase='await_pair'
                return seal
            except BaseException as error:self.cancel(str(error));raise

    def _pair(self,first,second,branch,*,minimum_seq):
        """Fresh consecutive replies on this exact checked probe branch."""
        now=self._check();p=self.preparation;reader=p.reader
        wall=p.wall();now=self._check()
        expected=(reader.zone_id,reader.zone_display_name,reader.tail.epoch,reader.zone_generation)
        if (any(type(v) is not RawLocationFix for v in (first,second))
                or type(minimum_seq) is not int
                or minimum_seq<self.ticket.start.height.second.log_line_seq
                or not isinstance(wall,datetime) or wall.tzinfo is not None):
            raise ValueError('Exact post-probe observations and acquisition baseline required')
        if (any(not point(v.raw_coordinates) or v.coordinates_aligned_to_wld is not False
                or (v.zone_id,v.zone_display_name,v.log_epoch,v.zone_generation)!=expected
                or type(v.log_line_seq) is not int or not finite(v.received_monotonic)
                or not isinstance(v.log_local_time,datetime) or v.log_local_time.tzinfo is not None
                for v in (first,second))
                or first.log_line_seq<=minimum_seq or second.log_line_seq!=first.log_line_seq+1
                or first.received_monotonic<self.seal.receipt.up_completed_at+.12
                or not .4-1e-9<=second.received_monotonic-first.received_monotonic<=2.5
                or first.log_local_time>second.log_local_time
                or not 0<=now-second.received_monotonic<=.5
                or reader.latest is not second or reader.log_line_seq!=second.log_line_seq
                or any(abs((wall-v.log_local_time).total_seconds()-(now-v.received_monotonic))>2.
                       for v in (first,second))
                or math.dist(first.raw_coordinates[:2],second.raw_coordinates[:2])>.25
                or abs(first.raw_coordinates[2]-second.raw_coordinates[2])>.25):
            raise ValueError('Two fresh consecutive stopped replies after probe release required')
        samples=[];b=p.bounds
        center_limit=self._envelope.record()['maximum_center_travel']+b.position_error+b.post_release_drift
        reference=self.ticket.start.height.package_xyz
        for raw in (first,second):
            xy=(raw.raw_coordinates[1],raw.raw_coordinates[0])
            if math.dist(xy,reference[:2])>center_limit+1e-9:
                raise ValueError('Post-probe position exceeds the checked motion envelope')
            z,ids=branch.floor_at(xy)
            samples.append(dict(package_xyz=(*xy,z),source_ids=ids,
                                offset=raw.raw_coordinates[2]-z))
        offsets=[s['offset'] for s in samples];offset=sum(offsets)/2
        anchor=self.ticket.start.height.raw_z_minus_source_z
        if (abs(samples[0]['package_xyz'][2]-samples[1]['package_xyz'][2])>.25
                or not finite(offset) or offset<=0 or
                any(abs(v-offset)>.05 or abs(v-anchor)>.05 for v in offsets)):
            raise ValueError('Post-probe heights differ from the observed source correspondence')
        finished=self._check()
        if (reader.latest is not second or reader.log_line_seq!=second.log_line_seq
                or not now<=finished<=second.received_monotonic+.5):
            raise ValueError('Post-probe pair changed or expired during its source check')
        return samples,offset,finished

    def prepare_endpoint(self,seal,first,second,*,maximum_seconds=30.):
        """Check the endpoint body outside the stop lock; a NEW pair must confirm it."""
        try:
            with self.lock:
                began=self._check()
                if (self.phase!='await_pair' or seal is not self.seal
                        or not seal.sealed_at<=began<=seal.expires_at
                        or not finite(maximum_seconds) or not 0<maximum_seconds<=30):
                    raise ValueError('Unexpired exact camp probe release required')
                self.phase='checking_pair'
                samples,offset,began=self._pair(first,second,self._envelope.branch,
                    minimum_seq=self.ticket.start.height.second.log_line_seq)
                if self.phase!='checking_pair' or began>seal.expires_at:
                    raise ValueError('Camp probe release changed or expired during pair check')
                p=self.preparation;checkpoint=p.checkpoint
                position=tuple(samples[1]['package_xyz'])
                self.phase='checking_endpoint'
                pair_bytes=encoded([_raw_record(first),_raw_record(second)])
                footprint=motion_footprint(position[:2],0.,0.,
                    position_error=p.bounds.position_error,heading_error_degrees=0.,
                    post_release_drift=0.,extra_radius=p.bounds.body_radius)
                boundary=rational(self._envelope.record()['footprint'])
                if not all(inside(v,boundary) for v in rational(footprint)):
                    raise ValueError('Endpoint body exceeds the checked probe envelope')
                branch=self._envelope.branch
            checked=check_source_footprint(branch,footprint,
                terrain=checkpoint._terrain,static=checkpoint._static,
                bsp=checkpoint._bsp,region_policy=checkpoint._policy)
            with self.lock:
                now=self._check()
                if (self.phase!='checking_endpoint' or not began<=now<=began+maximum_seconds
                        or pair_bytes!=encoded([_raw_record(first),_raw_record(second)])
                        or p.reader.latest is not second or p.reader.log_line_seq!=second.log_line_seq):
                    raise ValueError('Camp probe endpoint work changed or exceeded its budget')
                self._endpoint=checked.branch;self._endpoint_state=_chain_snapshot(checked.branch)
                self._planning_pair=(first,second);self._planning_position=position
                self._planning_offset=offset
                self._endpoint_payload=encoded(dict(footprint=footprint,terrain=asdict(checked.terrain),
                    static=asdict(checked.static),bsp=asdict(checked.bsp),native=asdict(checked.native),
                    planning_observations=json.loads(pair_bytes),samples=samples,
                    began=began,finished=now,requires_new_matching_pair=True,
                    input_authorized=False,real_client_accepted=False))
                self._confirmation_deadline=now+10.;self.phase='endpoint_prepared'
                self._geometry_state=self._geometry_values()
                return self.snapshot()
        except BaseException as error:self.cancel(str(error));raise

    def confirm_endpoint(self,first,second,*,minimum_log_seq):
        with self.lock:
            try:
                now=self._check()
                if (self.phase!='endpoint_prepared' or now>self._confirmation_deadline
                        or type(minimum_log_seq) is not int
                        or minimum_log_seq<self._planning_pair[1].log_line_seq
                        or type(first) is not RawLocationFix
                        or first.received_monotonic<json.loads(self._endpoint_payload)['finished']):
                    raise ValueError('New post-geometry endpoint pair required')
                self.phase='confirming'
                samples,offset,now=self._pair(first,second,self._endpoint,minimum_seq=minimum_log_seq)
                if (any(tuple(s['package_xyz'])!=self._planning_position for s in samples)
                        or offset!=self._planning_offset
                        or any(self._envelope.branch.floor_at(s['package_xyz'][:2])[0]
                               !=s['package_xyz'][2] for s in samples)):
                    raise ValueError('Probe endpoint changed after its body check')
                now=self._check()
                if (self.phase!='confirming' or now>self._confirmation_deadline
                        or now>second.received_monotonic+.5
                        or self.preparation.reader.latest is not second
                        or self.preparation.reader.log_line_seq!=second.log_line_seq):
                    raise ValueError('Endpoint confirmation changed or expired')
                payload=encoded(dict(format='eql-camp-probe-result-v1',
                    preparation_sha256=self.preparation.sha256,
                    start_height_sha256=self.ticket.start.height.sha256,
                    kind=self.ticket.kind,proposed_at=self.ticket.proposed_at,
                    receipt=asdict(self.seal.receipt),sealed_at=self.seal.sealed_at,
                    initial_reply_deadline=self.seal.expires_at,
                    endpoint_geometry=json.loads(self._endpoint_payload),
                    endpoint_geometry_sha256=sha256(self._endpoint_payload).hexdigest(),
                    observations=[_raw_record(first),_raw_record(second)],samples=samples,
                    raw_z_minus_source_z=offset,observed_at=now,expires_at=second.received_monotonic+.5,
                    floor_proof_sha256=self._endpoint.previous.proof_sha256,
                    input_authorized=False,current_motion_verified=False,
                    current_heading_verified=False,real_client_accepted=False,
                    sender_origin_verified=False))
                result=CampProbeResult(self.seal,first,second,self._planning_position,offset,
                    now,second.received_monotonic+.5,payload,sha256(payload).hexdigest())
                self.result=result;self._result_state=self._result_values(result)
                self.phase='confirmed'
                return result
            except BaseException as error:self.cancel(str(error));raise

    def fork_reached(self,result):
        """Return historical floor evidence while the original reader lease is held.

        This is not a CampFloorCheckpoint and cannot start another preparation.
        The result never authorizes input or renews expired motion calibration.
        """
        with self.lock:
            try:
                self._check()
                if (self.phase!='confirmed' or result is not self.result
                        or self._result_values(result)!=self._result_state):
                    raise ValueError('Exact confirmed probe result required')
                return self._endpoint.fork()
            except BaseException as error:self.cancel(str(error));raise

    def retain_endpoint(self,result):
        """Consume a fresh confirmation once for the next probe's historical floor.

        A new stopped-height pair must be measured on the returned reference.
        No SourceItineraryObservation or replacement calibration is manufactured.
        """
        from .camp_probe_floor import CampProbeFloorReference
        with self.lock:
            try:
                now=self._check();reader=self.preparation.reader
                if (self.phase!='confirmed' or result is not self.result
                        or self._continuation is not None
                        or not result.observed_at<=now<=result.expires_at
                        or reader.latest is not result.second or reader.log_line_seq!=result.second.log_line_seq):
                    raise ValueError('Fresh exact unconsumed endpoint confirmation required')
                self.phase='retaining'
                reference=CampProbeFloorReference(self,result)
                finished=self._check()
                if (self.phase!='retaining' or not now<=finished<=result.expires_at
                        or reader.latest is not result.second or reader.log_line_seq!=result.second.log_line_seq):
                    reference.invalidate('Endpoint changed during retention')
                    raise ValueError('Endpoint changed during retention')
                self._continuation=reference;self.phase='continued'
                reference.check()
                # The ancestry check may run provider callbacks. A historical
                # record can outlive this expiry, but initial transfer cannot.
                final=self._check()
                if (self.phase!='continued' or final>result.expires_at
                        or reader.latest is not result.second or reader.log_line_seq!=result.second.log_line_seq):
                    raise ValueError('Endpoint expired before reference transfer')
                reference._assert_intact()
                return reference
            except BaseException as error:self.cancel(str(error));raise

    def snapshot(self):
        return dict(phase=self.phase,reason=self.reason,
            preparation_sha256=self.preparation.sha256,
            result_sha256=None if self.result is None else self.result.sha256,
            input_authorized=False,current_motion_verified=False,real_client_accepted=False,
            sender_origin_verified=False)
