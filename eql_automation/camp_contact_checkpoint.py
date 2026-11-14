"""Historical contact arrival, distinct from an ordinary terrain checkpoint.

The private contact index cannot resume movement or fit a new height offset.
Deliberately retiring the controller does not erase history; input continuity
owns its later lifetime. No saved record can restore this in-memory object.
"""
from dataclasses import asdict
from hashlib import sha256
import json

from .camp_floor_checkpoint import _reader_identity
from .flat_record import flat_record_state
from .native_region_policy import encoded
from .observed_height import height_record,height_snapshot
from .route_floor_commit import _chain_snapshot
from .source_contact_controller import SourceContactController,SourceContactArrival
from .source_contact_plan import SourceContactIndex
from .source_probe_geometry import _source_storage


class CampContactCheckpoint:
    def __init__(self,controller,arrival):
        if type(controller) is not SourceContactController or type(arrival) is not SourceContactArrival:
            raise ValueError('Exact contact controller and stopped arrival required')
        self.valid=False;self.reason='Contact capture incomplete'
        c=controller
        with c.lock:
            c.validate_arrival(arrival);state=c._state()
            window=next(v[1] for v in c._issued if v[0] is arrival.second)
            c._window_check(window)
            self._arrival=arrival;self._arrival_state=c._arrival_snapshot(arrival)
            self._fix_states=tuple(c._fix_state(f) for f in (arrival.first,arrival.second))
            self._reference=arrival.second
            self._terrain_reference=c.chain.fork()
            self._terrain_state=_chain_snapshot(self._terrain_reference)
            self._calibration=c.observer.calibration
            self._height_state=height_snapshot(self._calibration)
            self._height_bytes=encoded(height_record(self._calibration))
            self._reader=c.observer.reader;self._reader_state=_reader_identity(self._reader)
            self._terrain,self._static,self._bsp=c.ordinary.terrain,c.ordinary.static,c.ordinary.bsp
            self._policy=c.observer.policy;self._classifier=self._policy.classifier
            self._policy_bytes=encoded(self._policy.record());self._model=c.model
            self._storage=_source_storage(self._terrain,self._static)
            self._pins=(self._terrain.archive_sha256,self._terrain.wld_sha256,
                self._static.inventory_sha256,self._bsp.inventory_sha256,self._bsp.wld_sha256)
            self._bounds=c.bounds;self._bounds_state=flat_record_state(c.bounds)
            self._motion=c.motion;self._motion_state=flat_record_state(c.motion)
            self._center_domain=window.center_footprint
            self._coverage=window.coverage
            self._coverage_state=(window.coverage.payload,window.coverage.sha256)
            plan=c.index.plan
            motion_record=dict(format='eql-camp-contact-arrival-motion-v1',
                itinerary_sha256=arrival.record()['itinerary_sha256'],
                contact_arrival_sha256=arrival.sha256,contact_plan_sha256=plan.sha256,
                original_floor_proof_sha256=c.chain.previous.proof_sha256,
                arrival_position=arrival.second.package_xyz,
                arrival_log_seq=arrival.second.raw_fix.log_line_seq,
                arrival_received_at=arrival.second.raw_fix.received_monotonic,
                arrival_heading_estimate=c.pose.heading,motion=asdict(c.motion),bounds=asdict(c.bounds),
                calibration_record_id=c.bounds.calibration_record_id,
                current_heading_verified=False,current_motion_verified=False,movement_authorized=False)
        # Rebuilding the sealed index needs no active input lock. The exact
        # arrival and original deadline are rechecked before returning.
        self._index=SourceContactIndex(plan)
        self._context=(self._arrival,self._reference,self._terrain_reference,self._calibration,
            self._reader,self._terrain,self._static,self._bsp,self._policy,self._classifier,
            self._model,self._bounds,self._motion,self._index,self._coverage,self._center_domain)
        self._payload=encoded(dict(format='eql-camp-contact-checkpoint-v1',
            arrival=arrival.record(),contact_arrival_sha256=arrival.sha256,
            contact_plan_sha256=plan.sha256,reader_identity=self._reader_state,
            arrival_position=self._reference.package_xyz,
            arrival_center_domain_exact=[[str(v) for v in p] for p in self._center_domain],
            final_coverage_sha256=self._coverage.sha256,
            source_archive_sha256=self._pins[0],source_wld_sha256=self._pins[1],
            static_inventory_sha256=self._pins[2],bsp_inventory_sha256=self._pins[3],
            historical_height=json.loads(self._height_bytes),
            historical_height_sha256=sha256(self._height_bytes).hexdigest(),
            motion_basis=motion_record,ordinary_floor_available=False,
            requires_fresh_stopped_pair=True,old_calibration_renewed=False,
            current_position_verified=False,current_height_verified=False,
            input_authorized=False,real_client_accepted=False))
        self._payload_identity=self._payload;self.sha256=sha256(self._payload).hexdigest()
        self._basis=encoded(dict(motion_record,contact_checkpoint_sha256=self.sha256))
        self._basis_identity=self._basis
        self.valid=True;self.reason=''
        try:
            self.check()
            with c.lock:
                c.validate_arrival(arrival)
                self._assert_intact()
                if c._state()!=state:
                    raise ValueError('Contact arrival changed during camp capture')
        except BaseException as error:
            self.invalidate(str(error));raise

    def invalidate(self,reason):
        if self.valid:self.reason=str(reason)
        self.valid=False
        self._context=self._arrival=self._reference=self._terrain_reference=None
        self._calibration=self._reader=self._terrain=self._static=self._bsp=None
        self._policy=self._classifier=self._model=self._bounds=self._motion=None
        self._index=self._coverage=self._center_domain=None

    def _assert_intact(self):
        if (not self.valid or self._context is None or any(a is not b for a,b in zip(self._context,
                (self._arrival,self._reference,self._terrain_reference,self._calibration,
                 self._reader,self._terrain,self._static,self._bsp,self._policy,self._classifier,
                 self._model,self._bounds,self._motion,self._index,self._coverage,self._center_domain)))
                or SourceContactController._arrival_snapshot(self._arrival)!=self._arrival_state
                or tuple(SourceContactController._fix_state(f) for f in
                    (self._arrival.first,self._arrival.second))!=self._fix_states
                or _chain_snapshot(self._terrain_reference)!=self._terrain_state
                or height_snapshot(self._calibration)!=self._height_state
                or encoded(height_record(self._calibration))!=self._height_bytes
                or _reader_identity(self._reader)!=self._reader_state or self._reader.tail.partial
                or self._reader.tail.identity is None
                or _source_storage(self._terrain,self._static)!=self._storage
                or (self._terrain.archive_sha256,self._terrain.wld_sha256,
                    self._static.inventory_sha256,self._bsp.inventory_sha256,self._bsp.wld_sha256)!=self._pins
                or self._classifier.inventory_sha256!=self._policy.classification_inventory_sha256
                or self._policy.classifier is not self._classifier
                or encoded(self._policy.record())!=self._policy_bytes
                or flat_record_state(self._bounds)!=self._bounds_state
                or flat_record_state(self._motion)!=self._motion_state
                or (self._coverage.payload,self._coverage.sha256)!=self._coverage_state
                or self._payload is not self._payload_identity or sha256(self._payload).hexdigest()!=self.sha256
                or self._basis is not self._basis_identity):
            raise ValueError('Camp contact checkpoint changed or was discarded')
        self._index.check()

    def check(self):
        """Check historical evidence, never the retired observer or old deadline."""
        try:
            self._assert_intact()
            self._policy.check_context(zone='crushbone',pins=(self._policy.mesh_sha256,
                self._terrain.archive_sha256,self._terrain.wld_sha256,self._static.inventory_sha256),bsp=self._bsp)
            self._model.check_policy(self._policy)
            self._assert_intact()
        except Exception as error:
            self.invalidate(str(error));raise ValueError(self.reason) from error

    def motion_basis(self):
        self.check();return self._basis

    def snapshot(self,*,include_evidence=False):
        result=dict(valid=self.valid,reason=self.reason,evidence_sha256=self.sha256,
            historical_contact_only=True,ordinary_floor_available=False,
            current_position_verified=False,current_height_verified=False,current_heading_verified=False,
            input_authorized=False,real_client_accepted=False)
        if include_evidence:result['evidence']=json.loads(self._payload)
        return result
