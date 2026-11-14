"""Retain a reached source floor through camp as historical provenance only.

No old observer is rearmed, no calibration expiry is extended, and no saved
record can restore this in-memory checkpoint. New stopped observations and a
fresh collection scope are still required before planning a relocation.
"""
from hashlib import sha256
import json

from .native_region_policy import encoded
from .ground_binding import finite
from .observed_height import height_record
from .route_floor_commit import _chain_snapshot
from .source_motion import SourceReceiptLedger
from .source_observer import SourceItineraryObserver
from .source_probe_geometry import _source_storage


def _reader_identity(reader):
    return (reader.tail.identity,reader.tail.epoch,reader.zone_generation,
        reader.zone_id,reader.zone_display_name,reader.expected_character,reader.expected_server)


class CampFloorCheckpoint:
    """A private snapshot-checked fork; returns further forks, never its own."""
    def __init__(self,ledger):
        if type(ledger) is not SourceReceiptLedger:
            raise ValueError('An actual source movement ledger is required')
        ledger._check();ledger.validate_reference()
        if (ledger.phase!='ready' or ledger._busy is not None or
                any(v is not None for v in (ledger._prepared,ledger._pending,ledger._sealed))):
            raise ValueError('Floor capture requires an idle stopped source ledger')
        state=ledger._state();observer=ledger.observer;reference=ledger.reference
        if (observer.reader.latest is not reference.raw_fix or
                observer.reader.log_line_seq!=reference.raw_fix.log_line_seq):
            raise ValueError('Capture requires the latest stopped source reference')
        reader=observer.reader;calibration=observer.calibration
        self._chain=ledger.chain.fork();self._chain_state=_chain_snapshot(self._chain)
        self._reference=reference;self._reference_state=observer._observation_snapshot(reference)
        self._calibration=calibration;self._height_bytes=encoded(height_record(calibration))
        self._reader=reader;self._reader_state=_reader_identity(reader)
        self._terrain,self._static,self._bsp=ledger.terrain,ledger.static,ledger.bsp
        self._policy=observer.policy;self._classifier=self._policy.classifier
        self._policy_bytes=encoded(self._policy.record())
        self._storage=_source_storage(self._terrain,self._static)
        self._pins=(self._terrain.archive_sha256,self._terrain.wld_sha256,
            self._static.inventory_sha256,self._bsp.inventory_sha256,self._bsp.wld_sha256)
        self._model=ledger.model
        self._context=(self._chain,reference,calibration,reader,self._terrain,self._static,
                       self._bsp,self._policy,self._classifier,self._model)
        self.valid=True;self.reason=''
        self._payload=encoded(dict(format='eql-camp-floor-checkpoint-v1',
            floor_proof_sha256=self._chain.previous.proof_sha256,
            seed_sha256=self._chain.seed_evidence_sha256,source_wld_sha256=self._chain.inventory_sha256,
            chain_index=self._chain.index,selected_ids=self._chain.previous.selected_ids,
            source_archive_sha256=self._terrain.archive_sha256,
            static_inventory_sha256=self._static.inventory_sha256,
            bsp_inventory_sha256=self._bsp.inventory_sha256,policy=json.loads(self._policy_bytes),
            arrival_position=reference.package_xyz,arrival_raw_coordinates=reference.raw_fix.raw_coordinates,
            arrival_log_seq=reference.raw_fix.log_line_seq,
            arrival_received_at=reference.raw_fix.received_monotonic,
            arrival_observed_at=reference.observed_at,reader_identity=self._reader_state,
            initial_plan_sha256=reference.initial_plan_sha256,itinerary_sha256=reference.itinerary_sha256,
            historical_height_sha256=sha256(self._height_bytes).hexdigest(),
            historical_height=json.loads(self._height_bytes),
            requires_fresh_stopped_pair=True,requires_fresh_height=True,
            current_position_verified=False,current_heading_verified=False,
            input_authorized=False,real_client_accepted=False))
        self.sha256=sha256(self._payload).hexdigest();self._payload_identity=self._payload
        try:
            self.check()
            ledger._check()
            self.check()
            # The observer checks mode/generation AFTER its clock/provider
            # callbacks. Do not add another clock callback after this boundary.
            now=ledger.validate_reference()
            self._assert_intact()
            if (ledger._state()!=state or ledger.observer is not observer or ledger.phase!='ready'
                    or observer.reader.latest is not reference.raw_fix
                    or observer.reader.log_line_seq!=reference.raw_fix.log_line_seq
                    or not finite(now) or not 0<=now-reference.raw_fix.received_monotonic<=.5):
                raise ValueError('Source arrival changed during floor capture')
        except BaseException as error:
            self.invalidate(str(error));raise

    def invalidate(self,reason):
        if self.valid:self.reason=str(reason)
        self.valid=False
        # Retain only immutable report bytes; no private branch remains usable.
        self._chain=self._chain_state=self._reference=self._reference_state=None
        self._calibration=self._reader=self._terrain=self._static=self._bsp=None
        self._policy=self._classifier=self._model=self._context=None
        self._storage=None

    def _assert_intact(self):
        if (not self.valid or self._context is None or
                any(a is not b for a,b in zip(self._context,
                    (self._chain,self._reference,self._calibration,self._reader,
                     self._terrain,self._static,self._bsp,self._policy,self._classifier,self._model)))
                or self._payload is not self._payload_identity
                or sha256(self._payload).hexdigest()!=self.sha256
                or _chain_snapshot(self._chain)!=self._chain_state
                or SourceItineraryObserver._observation_snapshot(self._reference)!=self._reference_state
                or encoded(height_record(self._calibration))!=self._height_bytes
                or _reader_identity(self._reader)!=self._reader_state or self._reader.tail.partial
                or self._reader.tail.identity is None
                or _source_storage(self._terrain,self._static)!=self._storage
                or (self._terrain.archive_sha256,self._terrain.wld_sha256,
                    self._static.inventory_sha256,self._bsp.inventory_sha256,self._bsp.wld_sha256)!=self._pins
                or self._classifier.inventory_sha256!=self._policy.classification_inventory_sha256
                or self._policy.classifier is not self._classifier
                or encoded(self._policy.record())!=self._policy_bytes):
            raise ValueError('Camp floor checkpoint changed or was discarded')

    def check(self):
        """Check historical identity, not current position or expired height validity."""
        try:
            self._assert_intact()
            self._policy.check_context(zone='crushbone',pins=(self._policy.mesh_sha256,
                self._terrain.archive_sha256,self._terrain.wld_sha256,self._static.inventory_sha256),bsp=self._bsp)
            self._model.check_policy(self._policy)
            self._assert_intact()
        except Exception as error:
            self.invalidate(str(error));raise ValueError(self.reason) from error

    def fork(self):
        self.check();branch=self._chain.fork();self.check()
        return branch

    def snapshot(self,*,include_evidence=False):
        result=dict(valid=self.valid,reason=self.reason,evidence_sha256=self.sha256,
            historical_floor_only=True,current_position_verified=False,
            current_height_verified=False,current_heading_verified=False,
            input_authorized=False,real_client_accepted=False)
        if include_evidence:result['evidence']=json.loads(self._payload)
        return result
