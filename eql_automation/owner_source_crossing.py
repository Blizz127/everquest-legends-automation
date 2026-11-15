"""Owner-supervised source-native zone crossing after a reached pre-line arrival.

Rebuilds crossing cells on the live reached CampFloorCheckpoint, collects fresh
stopped /location pairs on a self-owned ZoneReaderLease, runs provisional source
crossing pulses through SourceCrossingCorridor + SupervisedSourceCrossingPolicy,
and immediately discards all source-zone floor, pose, and calibration state once
expected LOADING / destination entry is observed.
"""
from dataclasses import dataclass, replace
from datetime import datetime
from hashlib import sha256
import json
import math
from pathlib import Path
import time

from .camp_floor_checkpoint import CampFloorCheckpoint
from .camp_motion_continuity import CampInputContinuity
from .camp_route_preparation import CampRoutePreparation
from .camp_source_observer import CampSourceObserver
from .camp_stopped_height import measure_camp_stopped_height
from .g2_safety_provider import GameWindowIdentity, focused_game_identity
from .ground_binding import digest, finite
from .location_hotkey import HOTKEY_CODES, send_location_hotkey
from .motion_collection import CommandReceipt, LocationRequest, immutable_binding
from .native_crossing_policy import NativeCrossingRegionPolicy, check_source_crossing_cell
from .native_region_policy import encoded
from .owner_navigation_preflight import settings_identity
from .owner_route_assets import checked_bytes
from .owner_route_trial import zone_binding
from .owner_zone_tracker import ZoneReaderLease
from .route_geometry import RouteMotionBounds
from .route_step_sender import _fd_identity
from .scene_log_veto import SceneLogVeto
from .source_arrival import arrival_reference
from .source_crossing_corridor import SourceCrossingCorridor
from .source_crossing_sender import run_checked_source_crossing_step
from .source_destinations import (
    CARBON_BUTCHER_GFAY_DATA_NAME,
    CARBON_GFAY_DATA_NAME,
    destination_spec,
)
from .source_itinerary import SourceItineraryGuide, SourceWalkHint, xy
from .source_motion import SourceReceiptLedger
from .stopped_location_pair import StoppedLocationPair
from .supervised_corridor import SupervisedCorridorDeclaration
from .supervised_route import scope_limits
from .supervised_source_crossing import SupervisedSourceCrossingPolicy
from .zone_line import ExpectedZoneLine

BUTCHER_GFAY_CORRIDOR_FILE = 'butcher-gfay-crossing-carbon-corridor-v1.json'
BUTCHER_GFAY_CORRIDOR_SHA256 = '092735a84716e7340731d376e008314e0e55daec675aabc10f08486b625f2fb0'
GFAY_CRUSHBONE_CORRIDOR_FILE = 'gfay-crushbone-crossing-carbon-corridor-v1.json'
GFAY_CRUSHBONE_CORRIDOR_SHA256 = '6755d4c63d3f778a317985d69c50935f2cf8f6f95788ab6073c3c0a90a46a323'
GFAY_BUTCHER_CRUSHBONE_CORRIDOR_FILE = 'gfay-butcher-crushbone-crossing-carbon-corridor-v1.json'
GFAY_BUTCHER_CRUSHBONE_CORRIDOR_SHA256 = 'e5a561cddadd59d6555b6450386cfb4de0b860f95c59f85b3c53eefa2aff932c'

_CORRIDOR_SPECS = {
    'butcher-gfay-crossing': (
        CARBON_BUTCHER_GFAY_DATA_NAME,
        BUTCHER_GFAY_CORRIDOR_FILE,
        BUTCHER_GFAY_CORRIDOR_SHA256,
    ),
    'gfay-crushbone-crossing': (
        CARBON_GFAY_DATA_NAME,
        GFAY_CRUSHBONE_CORRIDOR_FILE,
        GFAY_CRUSHBONE_CORRIDOR_SHA256,
    ),
    'gfay-butcher-crushbone-crossing': (
        CARBON_GFAY_DATA_NAME,
        GFAY_BUTCHER_CRUSHBONE_CORRIDOR_FILE,
        GFAY_BUTCHER_CRUSHBONE_CORRIDOR_SHA256,
    ),
}


@dataclass(frozen=True)
class PinnedSourceCrossingSpec:
    destination_id: str
    zone: str
    destination: str
    destination_zone_id: int
    destination_zone: str
    provenance_sha256: str
    start_xy: tuple
    transition_endpoint: tuple
    cell_segments: tuple
    expected_zone_line: ExpectedZoneLine
    corridor_file_sha256: str
    source_evidence: bytes

    def check(self, checkpoint, reader):
        if (type(checkpoint) is not CampFloorCheckpoint
                or type(self.expected_zone_line) is not ExpectedZoneLine
                or not digest(self.provenance_sha256)
                or not digest(self.corridor_file_sha256)
                or not xy(self.start_xy) or not xy(self.transition_endpoint)
                or type(self.cell_segments) is not tuple or not 2 <= len(self.cell_segments) <= 64
                or type(self.destination) is not str or not self.destination
                or type(self.destination_zone) is not str or not self.destination_zone
                or type(self.destination_zone_id) is not int or self.destination_zone_id <= 0
                or type(self.source_evidence) is not bytes or not 0 < len(self.source_evidence) <= 65536):
            raise ValueError('Pinned source crossing corridor specification is invalid')
        checkpoint.check()
        if (checkpoint._policy.zone != self.zone
                or self.expected_zone_line.zone != self.zone
                or reader.zone_ids.get(self.destination) != self.destination_zone_id):
            raise ValueError('Crossing corridor zone or destination catalog entry differs')
        previous_end = self.start_xy
        for seg in self.cell_segments:
            if (type(seg) is not tuple or len(seg) != 2
                    or not xy(seg[0]) or not xy(seg[1])
                    or math.dist(previous_end, seg[0]) > 1e-6):
                raise ValueError('Crossing corridor cell segments lost continuity')
            previous_end = seg[1]
        if (self.cell_segments[0][0] != self.start_xy
                or self.cell_segments[-1][0] != self.transition_endpoint
                or self.cell_segments[-1][1] != self.transition_endpoint):
            raise ValueError('Crossing corridor must start at pre-line goal and cap in transition')
        policy = NativeCrossingRegionPolicy(checkpoint._policy, self.expected_zone_line)
        policy.check_context(checkpoint._terrain, checkpoint._static, checkpoint._bsp)
        return policy


def load_source_crossing_spec(destination_id, *, root=None):
    if destination_id not in _CORRIDOR_SPECS:
        raise ValueError('Unknown or unpackaged source crossing destination')
    data_name, filename, expected_sha = _CORRIDOR_SPECS[destination_id]
    directory = (Path.home() / '.local/share/eql-automation/owner-route-data' / data_name
                 if root is None else Path(root))
    raw = checked_bytes(directory / filename, expected_sha)
    record = json.loads(raw)
    line_row = record.get('expected_zone_line')
    if (record.get('format') != 'eql-copied-source-crossing-corridor-v1'
            or record.get('destination_id') != destination_id
            or not isinstance(line_row, dict)
            or record.get('input_authorized') is not False
            or record.get('destination_server_verified') is not False
            or record.get('spawn_coordinate_verified') is not False
            or record.get('real_client_accepted') is not False):
        raise ValueError('Copied source crossing corridor record changed or claims live authority')
    line = ExpectedZoneLine(
        crossing_id=line_row['crossing_id'],
        zone=line_row['zone'],
        mesh_sha256=line_row['mesh_sha256'],
        archive_sha256=line_row['archive_sha256'],
        wld_sha256=line_row['wld_sha256'],
        bsp_inventory_sha256=line_row['bsp_inventory_sha256'],
        manifest_sha256=line_row['manifest_sha256'],
        raw_label=line_row['raw_label'],
        area_id=line_row['area_id'],
        polygon_ids=tuple(line_row['polygon_ids']),
        region_ids=tuple(line_row['region_ids']),
    )
    if line.sha256 != record.get('expected_zone_line_sha256'):
        raise ValueError('Copied source crossing expected zone line digest differs')
    start_xy = tuple(record['start_xy'])
    endpoint_xy = tuple(record['transition_endpoint'])
    segments = tuple((tuple(a), tuple(b)) for a, b in record['cell_segments'])
    spec = destination_spec(destination_id)
    if spec.arrival_mode != 'zone_crossing' or spec.zone != record['zone'] or spec.goal != start_xy:
        raise ValueError('Crossing corridor differs from its pre-line source guide destination')
    evidence = encoded(dict(
        kind='copied_source_crossing_corridor',
        destination_id=destination_id,
        zone=record['zone'],
        destination=record['destination'],
        destination_zone=record['destination_zone'],
        destination_zone_id=record['destination_zone_id'],
        corridor_file_sha256=expected_sha,
        expected_zone_line_sha256=line.sha256,
        start_xy=start_xy,
        transition_endpoint=endpoint_xy,
        destination_server_verified=False,
        spawn_coordinate_verified=False,
        real_client_accepted=False,
    ))
    return PinnedSourceCrossingSpec(
        destination_id=destination_id,
        zone=record['zone'],
        destination=record['destination'],
        destination_zone_id=record['destination_zone_id'],
        destination_zone=record['destination_zone'],
        provenance_sha256=record['provenance_sha256'],
        start_xy=start_xy,
        transition_endpoint=endpoint_xy,
        cell_segments=segments,
        expected_zone_line=line,
        corridor_file_sha256=expected_sha,
        source_evidence=evidence,
    )


def load_owner_source_crossing(engine, destination_id):
    return load_source_crossing_spec(destination_id)


class OwnerSourceCrossingRuntime:
    """Self-owned crossing runtime on a reached pre-line CampFloorCheckpoint."""

    def __init__(self, engine, journey, *, destination_id, corridor_spec,
                 checkpoint, motion_basis, motion, heading, bounds, legacy,
                 lease, sender, hotkey, owner_input, topology, gate, window,
                 released_at, owner_binding, binding_reader, generation_reader,
                 pump, command_state_clear, clock=time.monotonic,
                 local_wall_clock=datetime.now, walk_half_width=.25):
        if (type(corridor_spec) is not PinnedSourceCrossingSpec
                or corridor_spec.destination_id != destination_id
                or type(checkpoint) is not CampFloorCheckpoint
                or type(lease) is not ZoneReaderLease
                or type(bounds) is not RouteMotionBounds
                or type(window) is not GameWindowIdentity
                or not isinstance(motion, legacy.Motion)
                or not finite(heading) or not 0 <= heading < 360
                or not finite(walk_half_width) or not .05 <= walk_half_width <= 6.
                or not immutable_binding(owner_binding)
                or not all(callable(f) for f in (binding_reader, generation_reader,
                                                 pump, command_state_clear, clock, local_wall_clock))):
            raise ValueError('Reached pre-line floor, calibrated motion, lease and callbacks required')
        self.engine, self.journey = engine, journey
        self.destination_id, self.corridor_spec = destination_id, corridor_spec
        self.checkpoint = checkpoint
        self.motion, self.heading, self.legacy = motion, heading, legacy
        self.lease, self.reader = lease, lease.reader
        self.sender, self.hotkey = sender, hotkey
        self.owner_input, self.topology = owner_input, topology
        self.gate, self.window = gate, window
        self.owner_binding, self.binding_reader = owner_binding, binding_reader
        self.generation_reader = generation_reader
        self.pump, self.command_clear = pump, command_state_clear
        self.clock, self.wall = clock, local_wall_clock
        self.lock = engine.g0_stop_lock
        self.walk_half_width = walk_half_width
        self.ui = sender.ui
        self.fd = self.ui.fileno()
        self.fd_identity = _fd_identity(self.fd)
        self.generation = generation_reader()
        self.started = self.last_at = clock()
        seconds = scope_limits('zone_crossing_corridor')[0]
        self.expires_at = self.started + seconds + 90.
        self._times = (self.started, self.expires_at)
        self.phase, self.reason, self.busy, self.closed = 'collect_height', '', False, False
        self.collector = self.preparation = self.source_observer = None
        self.ledger = self.corridor = self.policy = None
        self.crossing_cells = None
        self.observations = []
        self.events = []
        self.sending_location = False
        self.location_request = None
        self.sending_movement = None
        with self.lock:
            checkpoint.check()
            lease.check()
            hotkey.check()
            if (not lease.active or lease._tracker.lease is not lease
                    or sender.held or sender.unfinished or sender.dismissed
                    or getattr(sender, '_eql_route_operation', None) is not None):
                raise ValueError('Crossing startup requires an active exclusive lease and released sender')
            self.crossing_policy = corridor_spec.check(checkpoint, self.reader)
            self.route_bounds = replace(
                bounds,
                record_id='source-crossing-' + sha256(corridor_spec.source_evidence).hexdigest(),
                maximum_requested_hold=min(.1, bounds.maximum_requested_hold),
            )
            self.route_bounds.validate_values(
                calibration_record_id=bounds.calibration_record_id,
                maximum_step_seconds=.2,
            )
            self.source_zone = zone_binding(self.reader)
            self.startup_veto = SceneLogVeto(
                self.reader.tail.path,
                expected_character=self.reader.expected_character,
                expected_server=self.reader.expected_server,
                cancel_generation=self.generation,
                clock=clock,
            )
            self.monitor = CampInputContinuity(
                owner_input,
                topology=topology,
                basis=motion_basis,
                binding=self._monitor_binding(),
                clock=clock,
                floor=checkpoint,
            )
            self.baseline = self.reader.log_line_seq
            self.released_at = released_at
            try:
                self.check_current()
                self.collector = StoppedLocationPair(
                    lease,
                    released_at=released_at,
                    check_current=self.check_current,
                    clock=clock,
                    local_wall_clock=local_wall_clock,
                )
            except BaseException as error:
                self.cancel(error)
                self.release()
                raise

    def _monitor_binding(self):
        return (self.sender, self.ui, self.gate, self.lease._tracker, self.reader, self,
                self.generation, self.owner_binding)

    def _source_active(self):
        c = self.corridor
        if c is None:
            return True
        a = getattr(c, 'arrival', None)
        if a is None:
            return True
        if a.loading is not None:
            return False
        if (c.touches_line and a.phase == 'await_loading'
                and a.reader.boundaries and a.reader.boundaries[0].kind == 'loading'):
            return False
        return True

    def current_input_key(self):
        if not self.busy:
            return None
        if self.sending_location and self.location_request is not None:
            return HOTKEY_CODES[self.hotkey.key_name]
        if self.sending_movement is not None:
            return {'forward': 103, 'left': 105, 'right': 106}.get(self.sending_movement)
        return None

    def _discard_source_floor(self, reason):
        if self.checkpoint.valid:
            self.checkpoint.invalidate(reason)
        if self.journey.arrival_floor is self.checkpoint:
            self.journey.arrival_floor = None

    def _check_owner_binding(self):
        if self.phase == 'stopped' or self.closed:
            raise ValueError(self.reason or 'Source crossing closed')
        if self.binding_reader() != self.owner_binding or self.generation_reader() != self.generation:
            raise ValueError('Source crossing owner binding or generation changed')

    def _check_context(self):
        if self.phase == 'stopped' or self.closed:
            raise ValueError(self.reason or 'Source crossing closed')
        binding = self.binding_reader()
        self.lease.check()
        self.hotkey.check()
        now = self.clock()
        key = self.current_input_key()
        if (self.phase == 'stopped' or self.closed
                or binding != self.owner_binding
                or self.generation_reader() != self.generation
                or (self.started, self.expires_at) != self._times
                or self.lease.reader is not self.reader
                or self.sender.ui is not self.ui
                or self.ui.fileno() != self.fd
                or _fd_identity(self.fd) != self.fd_identity
                or self.sender.unfinished or self.sender.dismissed
                or self.sender.held - ({key} if key is not None else set())
                or not self.command_clear()
                or not finite(now)
                or not self.started <= self.last_at <= now <= self.expires_at):
            raise ValueError('Source crossing owner, lease, sender or deadline changed')
        if self._source_active():
            self.monitor.check_binding(self._monitor_binding())
            if zone_binding(self.reader) != self.source_zone:
                raise ValueError('Source crossing source-zone log binding changed')
            self.checkpoint._model.check_policy(self.checkpoint._policy)
        else:
            self._discard_source_floor('Source crossing observed expected loading; source floor discarded')
        self.last_at = now
        return self.owner_binding

    def check_current(self):
        self._check_context()
        sample = self.owner_input.sample()
        window = focused_game_identity(self.gate)
        veto = self.startup_veto.poll() if self.corridor is None else None
        self._check_context()
        now = self.last_at
        if (window != self.window
                or not sample.clear_at(now)
                or sample.topology_generation != self.topology
                or (veto is not None and (not veto.continuity_available or veto.reason is not None))):
            raise ValueError('Source crossing owner activity, focus or startup hazard veto')
        return self.owner_binding

    def _release_controls(self):
        if (self.sender.ui is not self.ui or self.ui.fileno() != self.fd
                or _fd_identity(self.fd) != self.fd_identity):
            raise ValueError('Original source crossing sender unavailable for release')
        began = self.clock()
        for key in tuple(self.sender.held):
            self.sender.release(key)
        return CommandReceipt(began, self.clock())

    def cancel(self, reason):
        with self.lock:
            if self.phase == 'stopped' or self.closed:
                return
            text = str(reason)
            if self.corridor is not None and self.corridor.reason and self.corridor.reason not in text:
                text = f'{text}: {self.corridor.reason}'
            self.phase, self.reason = 'stopped', text
            self._discard_source_floor(reason)
            if self.collector is not None:
                self.collector.cancel(reason)
            if self.preparation is not None:
                self.preparation.cancel(reason)
            if self.source_observer is not None:
                self.source_observer.cancel(reason)
            if self.ledger is not None:
                self.ledger.cancel(reason)
            if self.policy is not None:
                self.policy.cancel(reason)
            if self.corridor is not None:
                self.corridor.cancel(reason)
            self.lease.active = False

    def release(self, *, close_observer=True):
        with self.lock:
            if self.closed:
                return
            if (self.busy or self.sender.held
                    or getattr(self.sender, '_eql_route_operation', None) is not None
                    or self.phase not in ('complete', 'stopped')):
                raise ValueError('Source crossing still owns pending input or work')
            self._discard_source_floor(self.reason or 'Zone crossing ended; source floor discarded')
            self.lease.release()
            self.closed = True
            if close_observer:
                self.monitor.close(self.reason or 'Zone crossing ended')

    def _send_startup_location(self, request, collector):
        def current():
            self.check_current()
            collector.check()
            if (not self.busy or not self.sending_location
                    or self.collector is not collector
                    or collector.pending is not request
                    or collector.phase != 'requesting'
                    or self.location_request is not request):
                raise ValueError('Crossing startup location request changed')
        self.sending_location, self.location_request = True, request
        try:
            sent = send_location_hotkey(
                self.sender,
                binding=self.hotkey,
                owner_input=self.owner_input,
                lock=self.lock,
                clock=self.clock,
                expires_at=min(request.expires_at, self.expires_at),
                ensure_current=current,
                cancel=self.cancel,
                pump=self.pump,
                record_event=self.events.append,
            )
            return CommandReceipt(sent.pulse.down_started_at, sent.released_at)
        finally:
            self.sending_location, self.location_request = False, None

    def _send_corridor_location(self, request, collector):
        c = self.corridor
        if type(request) is not LocationRequest or collector is None or c is None:
            raise ValueError('Owned crossing stopped-position request required')
        def current():
            self.check_current()
            c.arrival._check()
            collector.check()
            active = (c.arrival.source_collector
                      if c.arrival.source_collector is not None else c.arrival.collector)
            if (not self.busy or not self.sending_location
                    or active is not collector
                    or collector.pending is not request
                    or collector.phase != 'requesting'
                    or self.location_request is not request
                    or self.clock() < self.engine.zone_loading_until):
                raise ValueError('Crossing position request changed or client is loading')
        self.sending_location, self.location_request = True, request
        try:
            sent = send_location_hotkey(
                self.sender,
                binding=self.hotkey,
                owner_input=self.owner_input,
                lock=self.lock,
                clock=self.clock,
                expires_at=min(request.expires_at, self.expires_at),
                ensure_current=current,
                cancel=self.cancel,
                pump=self.pump,
                record_event=self.events.append,
            )
            return CommandReceipt(sent.pulse.down_started_at, sent.released_at)
        finally:
            self.sending_location, self.location_request = False, None

    def _complete_height_phase(self):
        c = self.collector
        height = measure_camp_stopped_height(
            self.checkpoint, self.reader, c.first, c.second,
            minimum_log_seq=self.baseline, released_at=self.released_at,
            owner_binding=self.owner_binding, binding_reader=self._check_context,
            clock=self.clock, local_wall_clock=self.wall,
        )
        if math.dist(height.package_xyz[:2], self.corridor_spec.start_xy) > self.walk_half_width:
            raise ValueError('Stopped pre-line position is outside the pinned crossing corridor start')
        cap_guide = SourceItineraryGuide(
            self.corridor_spec.zone,
            self.checkpoint._terrain.wld_sha256,
            self.checkpoint._static.inventory_sha256,
            self.corridor_spec.provenance_sha256,
            self.route_bounds.body_radius,
            self.route_bounds.body_height,
            self.corridor_spec.start_xy,
            (SourceWalkHint(self.corridor_spec.start_xy, self.corridor_spec.start_xy),),
        )
        self.preparation = CampRoutePreparation(
            self.checkpoint, height, self.lease,
            guide=cap_guide, bounds=self.route_bounds,
            owner_binding=self.owner_binding, binding_reader=self._check_context,
            local_wall_clock=self.wall, clock=self.clock,
        )
        self.preparation.prepare(maximum_seconds=min(30., self.expires_at - self.clock()))
        branch = self.checkpoint.fork()
        cells = []
        for seg_start, seg_end in self.corridor_spec.cell_segments:
            self._check_context()
            branch, cell = check_source_crossing_cell(
                branch, seg_start, seg_end,
                radius=self.route_bounds.body_radius,
                terrain=self.checkpoint._terrain,
                static=self.checkpoint._static,
                bsp=self.checkpoint._bsp,
                policy=self.crossing_policy,
            )
            cells.append(cell)
        self.crossing_cells = tuple(cells)
        self.baseline = self.reader.log_line_seq
        self.released_at = self.clock()
        self.collector = StoppedLocationPair(
            self.lease,
            released_at=self.released_at,
            check_current=self.check_current,
            clock=self.clock,
            local_wall_clock=self.wall,
        )
        self.phase = 'confirm_start'

    def _complete_confirm_start(self):
        c = self.collector
        start = self.preparation.observe_start(
            c.first, c.second,
            minimum_log_seq=self.baseline,
            released_at=self.released_at,
        )
        seconds = scope_limits('zone_crossing_corridor')[0]
        source_expires = min(self.expires_at, start.height.observed_at + seconds)
        self.source_observer = CampSourceObserver(
            self.preparation, start,
            scope_check=self._check_context,
            mode_reader=lambda: 'off' if self.phase == 'stopped' else 'camp_route',
            generation_reader=self.generation_reader,
            generation=self.generation,
            expires_at=source_expires,
            walk_half_width=self.walk_half_width,
            stop_lock=self.lock,
            route_bounds=self.route_bounds,
        )
        self.ledger = SourceReceiptLedger(
            self.source_observer,
            terrain=self.checkpoint._terrain,
            static=self.checkpoint._static,
            bsp=self.checkpoint._bsp,
            bounds=self.route_bounds,
            installed_model=self.checkpoint._model,
            legacy=self.legacy,
            motion=self.motion,
            heading=self.heading,
            stop_lock=self.lock,
        )
        self.observations = []
        self.released_at = self.clock()
        self.collector = StoppedLocationPair(
            self.lease,
            released_at=self.released_at,
            check_current=self.check_current,
            clock=self.clock,
            local_wall_clock=self.wall,
        )
        self.phase = 'startup_corridor'

    def _complete_startup_corridor(self):
        c = self.collector
        self.ledger.start(*self.observations, released_at=c.released_at)
        self.collector = None
        self.observations = []
        seconds, steps, distance, hold = scope_limits('zone_crossing_corridor')
        remaining_source = min(
            seconds,
            max(.1, self.source_observer.calibration.valid_until_monotonic - self.clock()),
        )
        self.corridor = SourceCrossingCorridor(
            self.ledger,
            self.crossing_policy,
            self.crossing_cells,
            self.lease,
            self.corridor_spec.destination,
            release_controls=self._release_controls,
            ready_for_location=lambda: (
                self.clock() >= self.engine.zone_loading_until and self.gate.controls_ready()
            ),
            # Physical/focus checks bracket tick and each location send;
            # movement policy samples them at admission and through release.
            # Nested corridor checks retain identity without resampling input.
            check_current=self._check_context,
            maximum_source_seconds=remaining_source,
            maximum_arrival_seconds=90.,
            walk_half_width=self.walk_half_width,
            local_wall_clock=self.wall,
        )
        declaration = SupervisedCorridorDeclaration(
            self.corridor.line.crossing_id,
            self.corridor.corridor_sha256,
            self.route_bounds.calibration_record_id,
            self.route_bounds.record_id,
            False,
            remaining_source,
            steps,
            distance,
            min(hold, remaining_source),
            expected_zone_line_sha256=self.corridor.line.sha256,
            destination=self.corridor_spec.destination,
            owner_supervised_continuation=True,
        )
        self.policy = SupervisedSourceCrossingPolicy(
            self.corridor,
            declaration=declaration,
            gate=self.gate,
            owner_input=self.owner_input,
            expected_window=self.window,
            topology_generation=self.topology,
            check_current=self._check_context,
        )
        self.phase = 'crossing'

    def tick(self):
        if self.closed or self.phase in ('complete', 'stopped'):
            return
        if self.busy:
            self._check_context()
            return
        self.busy = True
        try:
            self.check_current()
            if self.phase in ('collect_height', 'confirm_start'):
                c = self.collector
                request = c.tick()
                if isinstance(request, LocationRequest):
                    c.command_sent(request, self._send_startup_location(request, c))
                if c.phase == 'complete':
                    if self.phase == 'collect_height':
                        self._complete_height_phase()
                    else:
                        self._complete_confirm_start()
            elif self.phase == 'startup_corridor':
                c = self.collector
                request = c.tick()
                fixes = tuple(raw for raw in (c.first, c.second) if raw is not None)
                if len(fixes) != len(self.observations):
                    if len(fixes) != len(self.observations) + 1:
                        raise ValueError('Crossing startup skipped an owned position')
                    self.observations.append(
                        self.source_observer.observe(fixes[-1], checked_chain=self.ledger.chain)
                    )
                if isinstance(request, LocationRequest):
                    c.command_sent(request, self._send_startup_location(request, c))
                if c.phase == 'complete':
                    self._complete_startup_corridor()
            elif self.phase == 'crossing':
                c = self.corridor
                action = c.tick()
                self.check_current()
                if not self._source_active():
                    self._discard_source_floor(
                        'Source crossing observed expected loading; source floor discarded'
                    )
                if isinstance(action, LocationRequest):
                    active = (c.arrival.source_collector
                              if c.arrival.source_collector is not None else c.arrival.collector)
                    c.command_sent(action, self._send_corridor_location(action, active))
                elif c.phase == 'ready':
                    command = c.next_command()
                    self.sending_movement = command.kind
                    try:
                        result = run_checked_source_crossing_step(
                            self.sender, c,
                            policy=self.policy,
                            kind=command.kind,
                            requested_seconds=command.requested_seconds,
                            command_state_clear=self.command_clear,
                            pump=self.pump,
                        )
                    finally:
                        self.sending_movement = None
                    self.events.append(dict(kind='source_crossing_pulse', **result))
                    if not self._source_active():
                        self._discard_source_floor(
                            'Source crossing observed expected loading; source floor discarded'
                        )
                if c.phase == 'complete':
                    self._discard_source_floor('Zone crossing completed; source floor discarded')
                    self.phase = 'complete'
            else:
                raise ValueError('Unknown source crossing phase')
        except BaseException as error:
            self.cancel(error)
            raise
        finally:
            self.busy = False

    def snapshot(self):
        return dict(
            phase=self.phase,
            reason=self.reason,
            closed=self.closed,
            destination_id=self.destination_id,
            destination=self.corridor_spec.destination,
            destination_zone=self.corridor_spec.destination_zone,
            destination_zone_id=self.corridor_spec.destination_zone_id,
            corridor=None if self.corridor is None else self.corridor.snapshot(),
            executor_events=list(self.events),
            source_floor_discarded=not self.checkpoint.valid,
            source_navigation_state_reused=False,
            ordinary_route_driver_used=False,
            real_client_accepted=False,
        )


def make_source_crossing_engine(base, *, corridor_provider, clock=time.monotonic):
    if not callable(corridor_provider):
        raise ValueError('Explicit source crossing corridor provider required')

    class SourceCrossingEngine(base):
        def __init__(self, *args, **kwargs):
            self.source_crossing_run = None
            self._crossing_handoff_binding = None
            super().__init__(*args, **kwargs)

        def _source_crossing_spec(self, destination_id):
            return corridor_provider(self, destination_id)

        def _crossing_owner_binding(self, j, destination_id, sender, ui, tracker, reader, window):
            if (self.journey is not j
                    or j.phase not in ('handoff', 'source_crossing_handoff', 'source_crossing')
                    or j.destination_id != destination_id
                    or j.generation != self.cancel_generation
                    or j.settings != settings_identity(self.settings)
                    or j.continue_camps is not j._continue_camps
                    or self.sender is not sender
                    or self.sender.ui is not ui
                    or self.live_zone_tracker is not tracker
                    or tracker.reader is not reader
                    or self.stopping or not self.jobs.empty()
                    or self.camp_session is not None):
                raise ValueError('Source crossing owner, destination, generation or tracker changed')
            return (id(j), j.generation, j.settings, destination_id,
                    id(sender), id(ui), id(self.gate), id(tracker), id(reader), window)

        def _start_source_crossing_from_arrival(self, p, token):
            j = token.journey
            with self.g0_stop_lock:
                self._arrival_current(token)
                if (type(token.floor_checkpoint) is not CampFloorCheckpoint
                        or self.source_crossing_run is not None):
                    raise ValueError('Ordinary reached floor and idle crossing slot required')
                spec = self._source_crossing_spec(token.destination_id)
                self._arrival_current(token)
                sender, ui = token.sender, token.sender.ui
                tracker, reader = token.tracker, token.tracker.reader
                window = token.window
                self.cancelled = False  # Same owner generation; no new job.
                lease = tracker.acquire()
                handoff_args = (j, token.destination_id, sender, ui, tracker, reader, window)
                j.phase = 'source_crossing_handoff'
                self._crossing_handoff_binding = handoff_args
                try:
                    owner_binding = self._crossing_owner_binding(*handoff_args)
                    r = token.runtime
                    released_at = (r.last_movement_release
                                   if getattr(r, 'last_movement_release', None) is not None
                                   else arrival_reference(token.receipt).raw_fix.received_monotonic)
                    def pump():
                        self.pump()
                        self.autopilot_tick(clock())
                    runtime = OwnerSourceCrossingRuntime(
                        self, j,
                        destination_id=token.destination_id,
                        corridor_spec=spec,
                        checkpoint=token.floor_checkpoint,
                        motion_basis=token.motion_basis,
                        motion=r.ledger.motion,
                        heading=r.ledger.pose.heading,
                        bounds=r.ledger.bounds,
                        legacy=r.ledger.legacy,
                        lease=lease,
                        sender=sender,
                        hotkey=p['binding'],
                        owner_input=p['observer'],
                        topology=p['topology'],
                        gate=self.gate,
                        window=GameWindowIdentity(*window),
                        released_at=released_at,
                        owner_binding=owner_binding,
                        binding_reader=lambda: self._crossing_owner_binding(*handoff_args),
                        generation_reader=lambda: self.cancel_generation,
                        pump=pump,
                        command_state_clear=lambda: (
                            self._route_idle() and not self.cancelled and self.jobs.empty()
                        ),
                        clock=clock,
                        local_wall_clock=getattr(self, 'camp_wall', datetime.now),
                    )
                    self.source_crossing_run = runtime
                    j.phase = 'source_crossing'
                    runtime.check_current()
                except BaseException:
                    lease.release()
                    raise
                finally:
                    self._crossing_handoff_binding = None
            result = dict(
                phase='source_crossing',
                destination_id=token.destination_id,
                destination=spec.destination,
                destination_zone=spec.destination_zone,
                camp_started=False,
                real_client_accepted=False,
            )
            self.trace('journey_source_crossing_started', **result)
            self.emit(
                f'Travel into {spec.destination} active · stops after observed arrival · F9/F11 stop.'
            )
            return result

        def _start_source_crossing_from_camp_section(self, w, arrival):
            j = w.journey
            with self.g0_stop_lock:
                self._check_camp_section_arrival(w, arrival)
                if (type(arrival.checkpoint) is not CampFloorCheckpoint
                        or self.source_crossing_run is not None):
                    raise ValueError('Ordinary reached camp-section floor and idle crossing slot required')
                spec = self._source_crossing_spec(w.destination_id)
                self._check_camp_section_arrival(w, arrival)
                arrival._claim[0] = True
                w.budget.cancel('Final crossing section reached; navigation budget retired')
                w.set_stage('finished')
                self.camp_walking = None
                j.phase = 'source_crossing_handoff'
                j.settings = w.settings
                j.destination_id = w.destination_id
                j.arrival_floor = arrival.checkpoint
                j.candidates = ()
                sender, ui = w.sender, w.ui
                tracker, reader = w.tracker, w.reader
                window = w.window
                self.cancelled = False
                lease = tracker.acquire()
                handoff_args = (j, w.destination_id, sender, ui, tracker, reader, window)
                self._crossing_handoff_binding = handoff_args
                try:
                    owner_binding = self._crossing_owner_binding(*handoff_args)
                    r = arrival.runtime
                    released_at = (r.last_movement_release
                                   if getattr(r, 'last_movement_release', None) is not None
                                   else arrival_reference(arrival.receipt).raw_fix.received_monotonic)
                    def pump():
                        self.pump()
                        self.autopilot_tick(clock())
                    runtime = OwnerSourceCrossingRuntime(
                        self, j,
                        destination_id=w.destination_id,
                        corridor_spec=spec,
                        checkpoint=arrival.checkpoint,
                        motion_basis=arrival.motion_basis,
                        motion=r.ledger.motion,
                        heading=r.ledger.pose.heading,
                        bounds=r.ledger.bounds,
                        legacy=r.ledger.legacy,
                        lease=lease,
                        sender=sender,
                        hotkey=w.hotkey,
                        owner_input=w.monitor.observer,
                        topology=w.monitor.topology,
                        gate=self.gate,
                        window=GameWindowIdentity(*window),
                        released_at=released_at,
                        owner_binding=owner_binding,
                        binding_reader=lambda: self._crossing_owner_binding(*handoff_args),
                        generation_reader=lambda: self.cancel_generation,
                        pump=pump,
                        command_state_clear=lambda: (
                            self._route_idle() and not self.cancelled and self.jobs.empty()
                        ),
                        clock=clock,
                        local_wall_clock=getattr(self, 'camp_wall', datetime.now),
                    )
                    prior = w.monitor.last_observed_at
                    if prior is not None and (runtime.monitor.last_observed_at is None
                                              or prior > runtime.monitor.last_observed_at):
                        runtime.monitor.last_observed_at = prior
                    runtime.monitor.check(runtime._monitor_binding())
                    w.monitor.transfer_to(runtime.monitor)
                    j.camp_motion = None
                    self.source_crossing_run = runtime
                    j.phase = 'source_crossing'
                    runtime.check_current()
                except BaseException:
                    lease.release()
                    raise
                finally:
                    self._crossing_handoff_binding = None
            result = dict(
                phase='source_crossing',
                destination_id=w.destination_id,
                destination=spec.destination,
                destination_zone=spec.destination_zone,
                camp_started=False,
                real_client_accepted=False,
            )
            self.trace('journey_source_crossing_started', **result)
            self.emit(
                f'Travel into {spec.destination} active · stops after observed arrival · F9/F11 stop.'
            )
            return result

        def _owner_navigation_active(self):
            r = self.source_crossing_run
            if r is not None:
                try:
                    r._check_owner_binding()
                except (ValueError, AttributeError):
                    return False
                return True
            handoff = self._crossing_handoff_binding
            j = self.journey
            if handoff is not None and j is not None and j.phase == 'source_crossing_handoff':
                try:
                    self._crossing_owner_binding(*handoff)
                except (ValueError, AttributeError):
                    return False
                return True
            return super()._owner_navigation_active()

        def _navigation_busy(self):
            return self.source_crossing_run is not None or super()._navigation_busy()

        def _finish_trial_input_observer(self, pending):
            r = self.source_crossing_run
            if r is not None and r.owner_input is pending['observer']:
                r.check_current()
                return
            return super()._finish_trial_input_observer(pending)

        def zone_changed(self, body, now):
            r = self.source_crossing_run
            if (r is not None and r.corridor is not None
                    and not r.closed and r.phase != 'stopped' and not self.cancelled):
                expected = 'You have entered ' + r.corridor_spec.destination + '.'
                if body in ('LOADING, PLEASE WAIT...', expected):
                    self.zone_loading_until = now + (2. if body == expected else 120.)
                    self.trace('owner_source_crossing_transition_seen', line=body,
                        destination_id=r.destination_id, exclusive_arrival_reader=True,
                        real_client_accepted=False)
                    return
            return super().zone_changed(body, now)

        def _cleanup_source_crossing(self):
            r = self.source_crossing_run
            if r is None or r.busy:
                return
            if r.closed:
                self.source_crossing_run = None
            elif r.phase == 'stopped':
                r.release()
                self.source_crossing_run = None

        def _finish_source_crossing(self, r):
            with self.g0_stop_lock:
                j, generation = r.journey, r.generation

                def current(slot):
                    # Snapshot/release providers can reenter an owner stop even
                    # under this RLock. Never retire a newer F8/F9 decision.
                    if (self.journey is not j or self.cancel_generation != generation
                            or self.source_crossing_run is not slot):
                        return False
                    if (j.generation != generation or j.phase != 'source_crossing'
                            or j.destination_id != r.destination_id
                            or j.settings != settings_identity(self.settings)
                            or j.continue_camps is not j._continue_camps
                            or self.stopping or self.cancelled or r.busy
                            or r.phase != 'complete'):
                        raise ValueError('Completed source crossing lost its owner binding')
                    return True

                if not current(r):
                    return None
                snapshot = r.snapshot()
                if not current(r):
                    return None
                positions = r.corridor.arrival.collector.snapshot()
                if not current(r):
                    return None
                try:
                    r.release(close_observer=True)
                finally:
                    # release marks closed before closing the input observer;
                    # a callback or cleanup failure must not leave it busy.
                    if r.closed and self.source_crossing_run is r:
                        self.source_crossing_run = None
                if not current(None):
                    return None
                self.zone = r.corridor_spec.destination_zone
                result = dict(
                    phase='crossed_zone',
                    destination_id=r.destination_id,
                    destination=r.corridor_spec.destination,
                    destination_zone=r.corridor_spec.destination_zone,
                    destination_zone_id=r.corridor_spec.destination_zone_id,
                    corridor_sha256=r.corridor.corridor_sha256,
                    expected_zone_line_sha256=r.corridor.line.sha256,
                    arrival_positions=positions,
                    crossing=snapshot,
                    camp_started=False,
                    source_floor_discarded=True,
                    source_navigation_state_reused=False,
                    real_client_accepted=False,
                )
                self.stop_action(f'Reached {r.corridor_spec.destination} · movement stopped')
                if (self.cancel_generation != generation + 1 or self.journey is not None
                        or self.source_crossing_run is not None
                        or self._journey_assist is not None or self.active):
                    return None
                self.journey_last_result = result
                self.trace('journey_zone_crossing_completed', **result)
                self.emit(f'Reached {r.corridor_spec.destination} · movement stopped.')
                return result

        def stop_action(self, reason, *, keep_autopilot=False):
            self._crossing_handoff_binding = None
            if self.source_crossing_run is not None:
                self.source_crossing_run.cancel(reason)
            try:
                return super().stop_action(reason, keep_autopilot=keep_autopilot)
            finally:
                self._cleanup_source_crossing()

        def autopilot_payload(self):
            data = super().autopilot_payload()
            r = self.source_crossing_run
            if r is not None:
                data.update(
                    state='running',
                    phase=f'Crossing into {r.corridor_spec.destination} · {r.phase}',
                )
            return data

        def autopilot_tick(self, now):
            self._cleanup_source_crossing()
            result = super().autopilot_tick(now)
            r = self.source_crossing_run
            if r is None or r.busy:
                return result
            journey = self.journey
            try:
                r.tick()
                if r.phase == 'complete':
                    self._finish_source_crossing(r)
            except BaseException as error:
                detail = r.reason or str(error)
                if journey is not None and self.journey is journey:
                    self.stop_action(detail)
                else:
                    r.cancel(detail)
                self.emit('Zone crossing stopped: ' + detail)
            finally:
                self._cleanup_source_crossing()
            return result

    return SourceCrossingEngine
