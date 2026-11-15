"""Fresh destination floor provenance before any heading or speed is measured.

The producer owns an exclusive destination reader, checks an all-heading source
envelope, then requires another stopped pair at its exact reference. The result
is a historical floor root for fresh probes, not a movement ledger or permit.
Source-zone floors, poses and calibration objects are never accepted here.
"""
from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
import json
import math
import time

from .camp_floor_checkpoint import _reader_identity
from .current_route_start import (
    CurrentProbeEnvelope, CurrentStartPlanner, encoded as planner_encoded, raw_record,
)
from .flat_record import flat_record_state
from .ground_binding import finite, point
from .installed_region_model import InstalledRegionModel
from .location_log import RawLocationFix
from .motion_collection import immutable_binding
from .native_region_policy import NativeZeroRegionTrialPolicy, encoded
from .owner_zone_tracker import ZoneReaderLease
from .route_floor_commit import _chain_snapshot
from .route_geometry import RouteMotionBounds
from .source_probe_geometry import _source_storage


def _envelope_state(envelope):
    return (envelope.probe_kind, envelope.footprint, envelope.reference,
        envelope.source_reference, id(envelope.floor_chain), id(envelope.planning_bounds),
        envelope.evidence_bytes, envelope.evidence_sha256,
        envelope.requires_fresh_start_pair, envelope.current_motion_verified,
        envelope.input_authorized, envelope.real_client_accepted)


@dataclass(frozen=True)
class DestinationFloorAnchor:
    first: RawLocationFix
    second: RawLocationFix
    package_xyz: tuple
    raw_z_minus_source_z: float
    observed_at: float
    expires_at: float
    input_authorized: bool = field(default=False, init=False)
    current_motion_verified: bool = field(default=False, init=False)


def _anchor_state(anchor):
    return (id(anchor.first), id(anchor.second), flat_record_state(anchor.first),
        flat_record_state(anchor.second), anchor.package_xyz,
        anchor.raw_z_minus_source_z, anchor.observed_at, anchor.expires_at,
        anchor.input_authorized, anchor.current_motion_verified)


class DestinationFloorBootstrap:
    """One destination scope, one checked envelope and one claimable floor."""
    def __init__(self, planner, lease, *, bounds, bounds_basis, owner_binding,
                 binding_reader, generation, generation_reader, record_id,
                 clock=time.monotonic, local_wall_clock=datetime.now,
                 maximum_seconds=120.):
        if (type(planner) is not CurrentStartPlanner or type(lease) is not ZoneReaderLease
                or type(planner.region_policy) is not NativeZeroRegionTrialPolicy
                or type(getattr(planner, 'installed_region_model', None)) is not InstalledRegionModel
                or type(bounds) is not RouteMotionBounds
                or type(bounds_basis) is not bytes or not 0 < len(bounds_basis) <= 16384
                or type(generation) is not int or generation < 0
                or not immutable_binding(owner_binding) or type(owner_binding) is not tuple
                or type(record_id) is not str or not record_id
                or not finite(maximum_seconds) or not 0 < maximum_seconds <= 1500.
                or not all(callable(v) for v in
                    (binding_reader, generation_reader, clock, local_wall_clock))):
            raise ValueError('Destination planner, exclusive lease and independent bounded scope required')
        basis = json.loads(bounds_basis)
        if not isinstance(basis, dict) or not basis or encoded(basis) != bounds_basis:
            raise ValueError('Canonical explicit destination bounds provenance required')
        bounds.validate_values(calibration_record_id=bounds.calibration_record_id,
                               maximum_step_seconds=.2)
        self.planner, self.lease, self.reader = planner, lease, lease.reader
        self.bounds, self.bounds_basis = bounds, bounds_basis
        self.owner_binding, self.binding_reader = owner_binding, binding_reader
        self.generation, self.generation_reader = generation, generation_reader
        self.record_id, self.clock, self.wall = record_id, clock, local_wall_clock
        self.model = planner.installed_region_model
        self.started = self.last_at = clock()
        self.expires_at = self.started + maximum_seconds
        self._times = (self.started, self.expires_at)
        self.phase, self.reason = 'new', ''
        self._context = (planner, lease, lease.reader, bounds, bounds_basis,
            owner_binding, binding_reader, generation, generation_reader, record_id,
            clock, local_wall_clock, self.model)
        self._bounds_state = flat_record_state(bounds)
        self._reader_state = _reader_identity(self.reader)
        self._catalog = tuple(sorted(self.reader.zone_ids.items()))
        self._path = self.reader.tail.path
        self._views = (planner.source, planner.static, planner.bsp, planner.region_policy)
        self._storage = _source_storage(planner.source, planner.static)
        self._policy_bytes = encoded(planner.region_policy.record())
        self._pins = self._geometry_pins()
        self._model_bytes = encoded(self.model.record())
        self._envelope = self._envelope_pin = self._chain_state = None
        self._envelope_identity = None
        self._planning_pair = self._planning_state = None
        self._anchor = self._anchor_pin = self._checkpoint = None
        self._anchor_identity = None
        self._planning_offset = self.prepared_at = None
        self._prepared_state = None
        self._capture_pending = False
        self.check()

    def _geometry_pins(self):
        p = self.planner
        return (p.zone, p.zone_id, p.zone_name, p.pins, p.bsp_pin,
            p.source.mesh_sha256, p.source.archive_sha256, p.source.wld_sha256,
            p.static.inventory_sha256, p.bsp.inventory_sha256, p.bsp.wld_sha256)

    def cancel(self, reason):
        if self.phase != 'stopped':
            self.reason = str(reason)
        self.phase = 'stopped'
        if self._checkpoint is not None:
            self._checkpoint.invalidate(self.reason)
        self._envelope = self._envelope_pin = self._chain_state = None

    def _assert_intact(self):
        p = self.planner
        actual = (p, self.lease, self.reader, self.bounds, self.bounds_basis,
            self.owner_binding, self.binding_reader, self.generation, self.generation_reader,
            self.record_id, self.clock, self.wall, self.model)
        if (self.phase == 'stopped' or any(a is not b for a, b in zip(self._context, actual))
                or (self.started, self.expires_at) != self._times
                or self.lease.reader is not self.reader or not self.lease.active
                or self.lease._tracker.lease is not self.lease
                or self.lease._tracker.reader is not self.reader
                or flat_record_state(self.bounds) != self._bounds_state
                or _reader_identity(self.reader) != self._reader_state
                or self.reader.tail.partial or self.reader.tail.path != self._path
                or tuple(sorted(self.reader.zone_ids.items())) != self._catalog
                or self.reader.tail.identity is None
                or (self.reader.zone_id, self.reader.zone_display_name) != (p.zone_id, p.zone_name)
                or self.reader.zone_ids.get(p.zone_name) != p.zone_id
                or p.installed_region_model is not self.model
                or any(a is not b for a, b in zip(self._views,
                    (p.source, p.static, p.bsp, p.region_policy)))
                or _source_storage(p.source, p.static) != self._storage
                or encoded(p.region_policy.record()) != self._policy_bytes
                or self._geometry_pins() != self._pins
                or encoded(self.model.record()) != self._model_bytes):
            raise ValueError(self.reason or 'Destination bootstrap context changed')
        if self._envelope is not None:
            if (self._envelope is not self._envelope_identity
                    or _envelope_state(self._envelope) != self._envelope_pin
                    or _chain_snapshot(self._envelope.floor_chain) != self._chain_state):
                raise ValueError('Destination bootstrap envelope changed')
        if self._planning_pair is not None and tuple(
                (id(v), flat_record_state(v)) for v in self._planning_pair) != self._planning_state:
            raise ValueError('Destination bootstrap planning observations changed')
        if self._anchor is not None and (self._anchor is not self._anchor_identity
                or _anchor_state(self._anchor) != self._anchor_pin):
            raise ValueError('Destination bootstrap anchor changed')
        if self._prepared_state is not None and (
                self._planning_offset, self.prepared_at) != self._prepared_state:
            raise ValueError('Destination bootstrap preparation changed')

    def check(self):
        """Preserve the original scope without renewing any position lifetime."""
        try:
            self._assert_intact()
            binding = self.binding_reader()
            generation = self.generation_reader()
            self.lease.check()
            self.planner._check_views()
            self.model.check_policy(self.planner.region_policy)
            now = self.clock()
            after_binding = self.binding_reader()
            after_generation = self.generation_reader()
            self._assert_intact()
            if (binding != self.owner_binding or after_binding != self.owner_binding
                    or type(generation) is not int or type(after_generation) is not int
                    or generation != self.generation or after_generation != self.generation
                    or not finite(now) or not self.started <= self.last_at <= now <= self.expires_at):
                raise ValueError('Destination bootstrap owner, generation or fixed deadline changed')
            self.last_at = now
            return now
        except Exception as error:
            self.cancel(error)
            raise ValueError(self.reason) from error

    def _binding(self):
        self.check()
        return self.owner_binding

    def _pair(self, first, second, *, minimum_log_seq, released_at):
        wall = self.wall()
        # The wall provider may revoke the owner scope or advance time. Check
        # its effects before the final freshness/publication boundary.
        now = self.check()
        expected = (self.reader.zone_id, self.reader.zone_display_name,
                    self.reader.tail.epoch, self.reader.zone_generation)
        if (any(type(v) is not RawLocationFix for v in (first, second))
                or type(minimum_log_seq) is not int or minimum_log_seq < 1
                or not finite(released_at) or released_at < 0
                or not isinstance(wall, datetime) or wall.tzinfo is not None
                or any(not point(v.raw_coordinates) or not finite(v.received_monotonic)
                    or v.coordinates_aligned_to_wld is not False
                    or not isinstance(v.log_local_time, datetime) or v.log_local_time.tzinfo is not None
                    or (v.zone_id, v.zone_display_name, v.log_epoch, v.zone_generation) != expected
                    or type(v.log_line_seq) is not int for v in (first, second))
                or first.log_line_seq <= minimum_log_seq
                or second.log_line_seq != first.log_line_seq + 1
                or self.reader.latest is not second or self.reader.log_line_seq != second.log_line_seq
                or not released_at + .12 <= first.received_monotonic
                or not .4 <= second.received_monotonic - first.received_monotonic <= 2.5
                or not 0 <= now - second.received_monotonic <= .5
                or first.log_local_time > second.log_local_time
                or math.dist(first.raw_coordinates[:2], second.raw_coordinates[:2]) > .25
                or abs(first.raw_coordinates[2] - second.raw_coordinates[2]) > .25
                or any(abs((wall - v.log_local_time).total_seconds()
                    - (now - v.received_monotonic)) > 2. for v in (first, second))):
            raise ValueError('Fresh consecutive destination pair after release required')
        return now

    def prepare(self, first, second, *, minimum_log_seq, released_at,
                vertical_window=1., maximum_source_z_difference=1.,
                maximum_seconds=30., allow_overhead_boundary=False):
        if self.phase != 'new':
            raise ValueError('Destination envelope can only be prepared once')
        try:
            # Claim preparation before any provider callback can reenter it.
            self.phase = 'preparing'
            self._pair(first, second, minimum_log_seq=minimum_log_seq, released_at=released_at)
            self._planning_pair = (first, second)
            self._planning_state = tuple((id(v), flat_record_state(v)) for v in (first, second))
            envelope = CurrentStartPlanner.plan_probe_envelope(self.planner, self.reader, first, second,
                probe_kind='forward', motion_record_id=self.bounds.calibration_record_id,
                bounds=self.bounds, vertical_window=vertical_window,
                maximum_source_z_difference=maximum_source_z_difference,
                owner_binding=self.owner_binding, binding_reader=self._binding,
                released_at=released_at, record_id=self.record_id,
                clock=self.clock, local_wall_clock=self.wall,
                maximum_seconds=min(maximum_seconds, self.expires_at-self.clock()),
                allow_overhead_boundary=allow_overhead_boundary)
            self.check()
            record = json.loads(envelope.evidence_bytes)
            if (type(envelope) is not CurrentProbeEnvelope
                    or planner_encoded(record) != envelope.evidence_bytes
                    or sha256(envelope.evidence_bytes).hexdigest() != envelope.evidence_sha256
                    or envelope.planning_bounds is not self.bounds
                    or envelope.probe_kind != 'forward'
                    or envelope.source_reference[:2] != (second.raw_coordinates[1], second.raw_coordinates[0])
                    or record.get('all_headings') is not True
                    or any(getattr(envelope, key) is not False for key in
                        ('input_authorized', 'current_motion_verified', 'real_client_accepted'))):
                raise ValueError('Actual destination planner envelope required')
            offsets = tuple(raw.raw_coordinates[2] - envelope.floor_chain.floor_at(
                (raw.raw_coordinates[1], raw.raw_coordinates[0]))[0] for raw in (first, second))
            offset = sum(offsets)/2
            if not finite(offset) or offset <= 0 or any(abs(v-offset) > .05 for v in offsets):
                raise ValueError('Destination source floor has inconsistent positive height correspondence')
            self._envelope = envelope
            self._envelope_identity = envelope
            self._envelope_pin = _envelope_state(envelope)
            self._chain_state = _chain_snapshot(envelope.floor_chain)
            self._planning_offset = offset
            self.prepared_at = self.check()
            self._prepared_state = (self._planning_offset, self.prepared_at)
            self.phase = 'prepared'
            return self.snapshot()
        except BaseException as error:
            self.cancel(error)
            raise

    def capture(self, first, second, *, minimum_log_seq, released_at):
        """Claim a fresh matching destination root once; it grants no input."""
        if self.phase != 'prepared' or self._capture_pending:
            raise ValueError('Unclaimed prepared destination envelope required')
        self._capture_pending = True
        try:
            now = self._pair(first, second, minimum_log_seq=minimum_log_seq, released_at=released_at)
            if (minimum_log_seq < self._planning_pair[1].log_line_seq
                    or released_at < self.prepared_at
                    or any((raw.raw_coordinates[1], raw.raw_coordinates[0]) != self._envelope.source_reference[:2]
                           for raw in (first, second))):
                raise ValueError('New destination pair must match the checked reference after planning')
            offsets = tuple(raw.raw_coordinates[2]-self._envelope.source_reference[2]
                            for raw in (first, second))
            offset = sum(offsets)/2
            if offset != self._planning_offset or any(abs(v-offset) > .05 for v in offsets):
                raise ValueError('Destination height correspondence changed; replan required')
            self._anchor = DestinationFloorAnchor(first, second, self._envelope.source_reference,
                offset, now, second.received_monotonic+.5)
            self._anchor_pin = _anchor_state(self._anchor)
            self._anchor_identity = self._anchor
            self.phase = 'capturing'
            result = DestinationFloorCheckpoint(self)
            self._pair(first, second, minimum_log_seq=minimum_log_seq, released_at=released_at)
            if self.phase != 'capturing' or self._checkpoint is not None:
                raise ValueError('Destination floor capture was revoked or reentered')
            self._checkpoint = result
            self.phase = 'claimed'
            result.check()
            self._pair(first, second, minimum_log_seq=minimum_log_seq, released_at=released_at)
            result._assert_intact()
            return result
        except BaseException as error:
            self.cancel(error)
            raise
        finally:
            self._capture_pending = False

    def snapshot(self):
        return dict(phase=self.phase, reason=self.reason, record_id=self.record_id,
            zone=self.planner.zone, envelope_sha256=None if self._envelope is None else self._envelope.evidence_sha256,
            checkpoint_sha256=None if self._checkpoint is None else self._checkpoint.sha256,
            started=self.started, expires_at=self.expires_at,
            planning_bounds=dict(vars(self.bounds)), bounds_basis=json.loads(self.bounds_basis),
            source_zone_state_reused=False, current_motion_verified=False,
            input_authorized=False, real_client_accepted=False)


class DestinationFloorCheckpoint:
    """Historical destination ancestry, available only from the live producer."""
    def __init__(self, producer):
        if (type(producer) is not DestinationFloorBootstrap or producer.phase != 'capturing'
                or not producer._capture_pending or producer._checkpoint is not None
                or type(producer._anchor) is not DestinationFloorAnchor):
            raise ValueError('Only the owning fresh destination producer can capture its floor')
        producer._assert_intact()
        self._producer, self._anchor = producer, producer._anchor
        self._chain = producer._envelope.floor_chain.fork()
        self._chain_state = _chain_snapshot(self._chain)
        self._reader = producer.reader
        self._terrain, self._static, self._bsp, self._policy = producer._views
        self._model = producer.model
        self._context = (producer, self._anchor, self._chain, self._reader,
            self._terrain, self._static, self._bsp, self._policy, self._model)
        self.valid, self.reason = True, ''
        self._payload = encoded(dict(format='eql-destination-floor-checkpoint-v1',
            bootstrap_record_id=producer.record_id,
            envelope_sha256=producer._envelope.evidence_sha256,
            floor_proof_sha256=self._chain.previous.proof_sha256,
            seed_sha256=self._chain.seed_evidence_sha256,
            source_wld_sha256=self._chain.inventory_sha256,
            chain_index=self._chain.index, selected_ids=self._chain.previous.selected_ids,
            observations=[raw_record(self._anchor.first), raw_record(self._anchor.second)],
            arrival_position=self._anchor.package_xyz,
            arrival_log_seq=self._anchor.second.log_line_seq,
            arrival_received_at=self._anchor.second.received_monotonic,
            raw_z_minus_source_z=self._anchor.raw_z_minus_source_z,
            observed_at=self._anchor.observed_at, expires_at=self._anchor.expires_at,
            reader_identity=producer._reader_state, bounds_basis=json.loads(producer.bounds_basis),
            historical_floor_only=True, requires_new_stopped_pair=True,
            source_zone_state_reused=False, old_calibration_renewed=False,
            current_position_verified=False, current_heading_verified=False,
            current_motion_verified=False, input_authorized=False, real_client_accepted=False))
        self.sha256 = sha256(self._payload).hexdigest()
        self._payload_identity = self._payload

    def invalidate(self, reason):
        if self.valid:
            self.reason = str(reason)
        self.valid = False
        self._chain = self._chain_state = None

    def _assert_intact(self):
        p = self._producer
        p._assert_intact()
        if (not self.valid or p.phase != 'claimed' or p._checkpoint is not self
                or any(a is not b for a, b in zip(self._context,
                    (p, self._anchor, self._chain, self._reader,
                     self._terrain, self._static, self._bsp, self._policy, self._model)))
                or p._anchor is not self._anchor
                or _chain_snapshot(self._chain) != self._chain_state
                or self._payload is not self._payload_identity
                or sha256(self._payload).hexdigest() != self.sha256):
            raise ValueError('Destination floor checkpoint changed or was discarded')

    def check(self):
        try:
            self._assert_intact()
            self._producer.check()
            self._assert_intact()
        except Exception as error:
            self.invalidate(error)
            raise ValueError(self.reason) from error

    def fork(self):
        self.check()
        branch = self._chain.fork()
        self.check()
        return branch

    def snapshot(self, *, include_evidence=False):
        result = dict(valid=self.valid, reason=self.reason, evidence_sha256=self.sha256,
            historical_floor_only=True, requires_new_stopped_pair=True,
            current_position_verified=False, current_heading_verified=False,
            current_motion_verified=False, input_authorized=False, real_client_accepted=False)
        if include_evidence:
            result['evidence'] = json.loads(self._payload)
        return result
