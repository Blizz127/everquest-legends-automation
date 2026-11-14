"""Route-independent source geometry for a later camp measurement pulse.

The caller owns the exclusive reader lease and collection. Bounds are explicit
planning hypotheses, never current measured motion. Geometry work may outlive
the planning pair; another newly collected pair must match its exact reference.
Neither a prepared envelope nor a fresh start admits any input.
"""
from dataclasses import asdict,dataclass,field
from hashlib import sha256
import json
import time

from .camp_probe_floor import CAMP_FLOOR_TYPES
from .camp_stopped_height import CampStoppedHeight,measure_camp_stopped_height
from .ground_binding import finite
from .motion_collection import immutable_binding
from .native_region_policy import encoded
from .owner_zone_tracker import ZoneReaderLease
from .route_floor_commit import _chain_snapshot
from .route_geometry import RouteMotionBounds
from .source_probe_geometry import check_source_probe


def _height_state(value):
    return (value.checkpoint,value.first,value.second,value.package_xyz,
        value.raw_z_minus_source_z,value.observed_at,value.expires_at,value.payload,value.sha256)


def _raw_record(raw):
    value=asdict(raw);value['log_local_time']=raw.log_local_time.isoformat();return value


def _check_height_record(height,checkpoint,owner_binding):
    """Match the immutable report to its actual objects, not just a success bit."""
    if (type(height) is not CampStoppedHeight or height.checkpoint is not checkpoint
            or type(height.payload) is not bytes or sha256(height.payload).hexdigest()!=height.sha256):
        raise ValueError('Exact fresh camp-height record required')
    record=json.loads(height.payload)
    if (encoded(record)!=height.payload or record.get('format')!='eql-camp-stopped-height-v1'
            or record['checkpoint_sha256']!=checkpoint.sha256
            or record['source_floor_proof_sha256']!=checkpoint._chain.previous.proof_sha256
            or encoded(record['owner_binding'])!=encoded(owner_binding)
            or encoded(record['observations'])!=encoded([_raw_record(height.first),_raw_record(height.second)])
            or tuple(record['samples'][1]['package_xyz'])!=height.package_xyz
            or record['raw_z_minus_source_z']!=height.raw_z_minus_source_z
            or record['observed_at']!=height.observed_at or record['expires_at']!=height.expires_at
            or height.expires_at!=height.second.received_monotonic+.5
            or not height.second.received_monotonic<=height.observed_at<=height.expires_at
            or tuple(height.package_xyz[:2])!=(height.second.raw_coordinates[1],height.second.raw_coordinates[0])
            or checkpoint._chain.floor_at(height.package_xyz[:2])[0]!=height.package_xyz[2]
            or abs(height.second.raw_coordinates[2]-height.package_xyz[2]
                   -height.raw_z_minus_source_z)>record['residual_limit']):
        raise ValueError('Camp-height evidence differs from its observed position')
    return record


@dataclass(frozen=True)
class CampProbeStart:
    height: CampStoppedHeight
    preparation_sha256: str
    observed_at: float
    expires_at: float
    input_authorized: bool=field(default=False,init=False)
    current_motion_verified: bool=field(default=False,init=False)


class CampProbePreparation:
    """One source envelope and one fresh matching start, without a walk route."""
    def __init__(self,checkpoint,height,lease,*,probe_kind,bounds,bounds_basis,
                 owner_binding,binding_reader,local_wall_clock,clock=time.monotonic):
        if (type(checkpoint) not in CAMP_FLOOR_TYPES or type(height) is not CampStoppedHeight
                or type(lease) is not ZoneReaderLease
                or type(bounds) is not RouteMotionBounds or probe_kind not in ('forward','left','right')
                or type(bounds_basis) is not bytes or not 0<len(bounds_basis)<=16384
                or not immutable_binding(owner_binding)
                or not all(callable(f) for f in (binding_reader,local_wall_clock,clock))):
            raise ValueError('Exact camp floor, lease, explicit bounds and current scope required')
        basis=json.loads(bounds_basis)
        if not isinstance(basis,dict) or not basis or encoded(basis)!=bounds_basis:
            raise ValueError('Canonical nonempty bound-provenance record required')
        bounds.validate_values(calibration_record_id=bounds.calibration_record_id,maximum_step_seconds=.2)
        self.checkpoint=checkpoint;self.height=height;self.lease=lease;self.reader=lease.reader
        self.bounds=bounds;self.bounds_basis=bounds_basis;self.kind=probe_kind
        self.owner_binding=owner_binding;self.binding_reader=binding_reader
        self.wall=local_wall_clock;self.clock=clock
        self._context=(checkpoint,height,lease,lease.reader,bounds,bounds_basis,probe_kind,
                       owner_binding,binding_reader,local_wall_clock,clock)
        self._height_state=_height_state(height);self._bounds_bytes=encoded(asdict(bounds))
        self.phase='new';self.reason='';self.last_at=None
        self._envelope=self._envelope_state=self._start=None
        self._prepared_record=None
        self._consume_pending=False
        self.payload=None;self.sha256=None
        _check_height_record(height,checkpoint,owner_binding)
        self.check(fresh=height)

    def cancel(self,reason):
        self.phase='stopped';self.reason=str(reason)
        self._envelope=self._envelope_state=self._start=None

    def check(self,*,fresh=None):
        try:
            if self.phase=='stopped':raise ValueError(self.reason)
            binding=self.binding_reader();self.lease.check();self.checkpoint.check()
            now=self.clock()
            self.checkpoint._assert_intact()
            actual=(self.checkpoint,self.height,self.lease,self.reader,self.bounds,self.bounds_basis,
                    self.kind,self.owner_binding,self.binding_reader,self.wall,self.clock)
            if (self.phase=='stopped' or any(a is not b for a,b in zip(self._context,actual))
                    or binding!=self.owner_binding or self.lease.reader is not self.reader
                    or not self.lease.active or self.lease._tracker.lease is not self.lease
                    or self.reader is not self.checkpoint._reader
                    or _height_state(self.height)!=self._height_state
                    or encoded(asdict(self.bounds))!=self._bounds_bytes
                    or self.reader.tail.partial or not finite(now)
                    or self.last_at is not None and now<self.last_at):
                raise ValueError('Camp probe preparation context changed')
            if self._envelope is not None:
                envelope,payload,chain=self._envelope_state
                if (self._envelope is not envelope or envelope.payload is not payload
                        or _chain_snapshot(envelope.branch)!=chain):
                    raise ValueError('Prepared source envelope changed')
                envelope.record()
            if self._prepared_record is not None:
                payload,digest=self._prepared_record
                if (self.payload is not payload or self.sha256!=digest
                        or sha256(payload).hexdigest()!=digest):
                    raise ValueError('Camp probe preparation record changed')
            if fresh is not None:
                _check_height_record(fresh,self.checkpoint,self.owner_binding)
                if (self.reader.latest is not fresh.second or self.reader.log_line_seq!=fresh.second.log_line_seq
                        or not fresh.observed_at<=now<=fresh.expires_at):
                    raise ValueError('Camp probe needs a fresh latest stopped pair')
            self.last_at=now
            return now
        except Exception as error:
            self.cancel(str(error));raise ValueError(self.reason) from error

    def prepare(self,*,maximum_seconds=30.):
        """Check full occupancy under the supplied hypotheses; never renew age."""
        if self.phase!='new':raise ValueError('Camp probe geometry can only be prepared once')
        try:
            self.check(fresh=self.height)
            self.phase='preparing'
            checkpoint=self.checkpoint
            envelope=check_source_probe(checkpoint.fork(),self.height.package_xyz,
                probe_kind=self.kind,bounds=self.bounds,terrain=checkpoint._terrain,
                static=checkpoint._static,bsp=checkpoint._bsp,region_policy=checkpoint._policy,
                check_context=self.check,clock=self.clock,maximum_seconds=maximum_seconds)
            self.check()
            self._envelope=envelope
            self._envelope_state=(envelope,envelope.payload,_chain_snapshot(envelope.branch))
            self.payload=encoded(dict(format='eql-camp-probe-preparation-v1',
                checkpoint_sha256=checkpoint.sha256,planning_height_sha256=self.height.sha256,
                planning_position=self.height.package_xyz,planning_observed_at=self.height.observed_at,
                planning_expires_at=self.height.expires_at,bounds_basis=json.loads(self.bounds_basis),
                geometry=envelope.record(),geometry_sha256=envelope.sha256,
                requires_new_matching_pair=True,motion_bounds_verified=False,
                current_heading_verified=False,independent_scene_verified=False,
                input_authorized=False,real_client_accepted=False))
            self.sha256=sha256(self.payload).hexdigest()
            self._prepared_record=(self.payload,self.sha256)
            self.check();self.phase='prepared'
            return self.snapshot()
        except Exception as error:
            self.cancel(str(error));raise

    def observe_start(self,first,second,*,minimum_log_seq,released_at):
        """Use a new collected pair after planning; no timestamp refresh/floor choice."""
        if self.phase!='prepared':raise ValueError('Unconsumed checked camp probe required')
        try:
            self.check()
            if minimum_log_seq<self.height.second.log_line_seq:
                raise ValueError('Probe start baseline predates its planning pair')
            height=measure_camp_stopped_height(self.checkpoint,self.reader,first,second,
                minimum_log_seq=minimum_log_seq,released_at=released_at,
                owner_binding=self.owner_binding,binding_reader=self.binding_reader,
                clock=self.clock,local_wall_clock=self.wall)
            if (height.package_xyz!=self.height.package_xyz
                    or height.raw_z_minus_source_z!=self.height.raw_z_minus_source_z):
                raise ValueError('Probe start moved from the checked source reference; replan required')
            self.check(fresh=height)
            start=CampProbeStart(height,self.sha256,height.observed_at,height.expires_at)
            self._start=start;self.phase='ready'
            return start
        except Exception as error:
            self.cancel(str(error));raise

    def check_start(self,start):
        if (self.phase!='ready' or start is not self._start
                or start.preparation_sha256!=self.sha256
                or start.observed_at!=start.height.observed_at or start.expires_at!=start.height.expires_at):
            raise ValueError('Exact active camp probe start required')
        self.check(fresh=start.height)
        if self.phase!='ready' or self._start is not start:
            raise ValueError('Camp probe start changed during its final check')
        return self._envelope

    def consume_start(self,start):
        """Transfer this exact start once to a receipt ledger; no input permit.

        The owning controller holds its shared stop lock across this operation.
        The preparation remains available for context/geometry integrity checks.
        """
        if self._consume_pending:
            raise ValueError('Camp probe start transfer already pending')
        self._consume_pending=True
        try:
            envelope=self.check_start(start)
            self.phase='consumed'
            return envelope
        finally:
            self._consume_pending=False

    def snapshot(self):
        return dict(phase=self.phase,reason=self.reason,sha256=self.sha256,
            evidence=None if self.payload is None else json.loads(self.payload),
            input_authorized=False,current_motion_verified=False,real_client_accepted=False)
