"""Source-native crossing corridor: provisional source pulses + ZoneArrivalHandoff.

Movement envelopes use NativeCrossingRegionPolicy over copied source terrain,
static instances, scoped BSP and complete native region classifications.
No movement pulse commits a floor on release:
- If LOADING is observed during or after a pulse whose checked envelope touched
  the expected transition region, the provisional source fork is discarded and
  ZoneArrivalHandoff verifies the expected destination entry and fresh
  destination-zone stopped positions.
- If a pulse elapses without LOADING, it stays sealed until the quiet window
  expires and two fresh stopped source-zone positions + a checked endpoint cap
  resolve it. Uncorrelated LOADING (without an overlapping transition envelope)
  refuses immediately.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime
from hashlib import sha256
import json
import math

from .bsp_floor_guard import check_source_body_bsp
from .fixed_route_follower import RouteHalt
from .ground_binding import finite
from .ground_sweep import hull, motion_footprint
from .native_body_regions import classify_source_body_regions
from .native_crossing_policy import NativeCrossingRegionPolicy, SourceCrossingCell
from .native_region_policy import encoded
from .route_floor_commit import _chain_snapshot
from .source_detour import swept_square
from .source_floor_chain import inside, rational
from .source_motion import SourceMotionSeal, SourceReceiptLedger
from .source_probe_geometry import _source_storage
from .static_floor_guard import check_source_static_floor
from .uinput_watchdog import PulseReceipt
from .zone_arrival import ZoneArrivalHandoff


@dataclass(frozen=True)
class SourceCrossingCommand:
    kind: str
    requested_seconds: float
    cell_index: int
    target: tuple
    reference: object


@dataclass(frozen=True)
class SourceCrossingGeometry:
    kind: str
    footprint: tuple
    touched_regions: tuple
    payload: bytes
    sha256: str

    def record(self):
        if type(self.payload) is not bytes or sha256(self.payload).hexdigest() != self.sha256:
            raise ValueError('Source crossing geometry evidence changed')
        value = json.loads(self.payload)
        if encoded(value) != self.payload:
            raise ValueError('Source crossing geometry is not canonical')
        return value


@dataclass(frozen=True)
class SourceCrossingTicket:
    reference: object
    geometry: SourceCrossingGeometry
    serial: int
    proposed_at: float
    requested_seconds: float
    maximum_actual_hold: float
    movement_key: int
    touches_line: bool
    input_authorized: bool = field(default=False, init=False)


@dataclass(frozen=True)
class _CrossingTarget:
    cell_index: int
    start: tuple
    end: tuple


class SourceCrossingCorridor:
    def __init__(self, ledger, crossing_policy, crossing_cells, lease, destination, *,
                 release_controls, ready_for_location, check_current,
                 maximum_source_seconds, maximum_arrival_seconds=90.,
                 walk_half_width=None, local_wall_clock=datetime.now):
        if (type(ledger) is not SourceReceiptLedger
                or type(crossing_policy) is not NativeCrossingRegionPolicy
                or crossing_policy.ordinary is not ledger.observer.policy
                or type(crossing_cells) is not tuple or not 1 <= len(crossing_cells) <= 64
                or any(type(c) is not SourceCrossingCell for c in crossing_cells)
                or not all(callable(f) for f in (release_controls, ready_for_location,
                                                 check_current, local_wall_clock))):
            raise ValueError('Ready source ledger, matching native crossing policy and checked cells required')
        with ledger.lock:
            ledger._check()
            ledger.model.check_policy(crossing_policy.ordinary)
            crossing_policy.check_context(ledger.terrain, ledger.static, ledger.bsp)
            ledger.validate_reference()
            if (ledger.phase != 'ready' or ledger._busy is not None
                    or ledger._pending is not None or ledger._sealed is not None
                    or lease.reader is not ledger.observer.reader):
                raise ValueError('Idle ready source ledger and matching exclusive reader lease required')
            self.ledger = ledger
            self.observer = ledger.observer
            self.terrain, self.static, self.bsp = ledger.terrain, ledger.static, ledger.bsp
            self.bounds, self.model, self.legacy = ledger.bounds, ledger.model, ledger.legacy
            self.motion = ledger.motion
            self.lock, self.clock = ledger.lock, ledger.clock
            self.crossing_policy = crossing_policy
            self.line = crossing_policy.expected_zone_line
            self.crossing_cells = crossing_cells
            self._cells_payloads = tuple(c.payload for c in crossing_cells)
            self.walk_half_width = (ledger.observer.walk_half_width
                                    if walk_half_width is None else walk_half_width)
            if not finite(self.walk_half_width) or not .05 <= self.walk_half_width <= 6.:
                raise ValueError('Bounded crossing walk half-width required')
            self.chain = ledger.chain
            self.reference = ledger.reference
            self.pose = deepcopy(ledger.pose)
            self.pose.motion = self.motion
            self.mode = self.observer.mode_reader()
            self.generation = self.observer.generation
            self.check_current = check_current
            self._source_storage = _source_storage(self.terrain, self.static)
            self._bounds_dict = asdict(self.bounds)
            self._motion_dict = deepcopy(vars(self.motion))
            self._policy_bytes = encoded(crossing_policy.record())
            self._ValidateCells()

            # Prevent any concurrent ordinary SourceWalkDriver from using ledger:
            self._ledger_lease = object()
            ledger._busy = self._ledger_lease

            self.phase, self.reason = 'ready', ''
            self.index = 0
            self.serial = self.steps = 0
            self._prepared = self._pending = None
            self.ticket = self.receipt = self.seal = self.policy = None
            self.touches_line = False
            self.quiet_until = None
            self.source_steps = []

            def release():
                receipt = release_controls()
                if self.arrival.loading is not None and (self.ticket is None or not self.touches_line):
                    raise ValueError('Loading was not preceded by a checked footprint at the expected line')
                return receipt

            try:
                self.arrival = ZoneArrivalHandoff(
                    lease, destination,
                    release_controls=release,
                    ready_for_location=lambda: self.phase == 'await_arrival' and ready_for_location(),
                    check_current=self._current,
                    clock=self.clock,
                    local_wall_clock=local_wall_clock,
                    maximum_seconds=maximum_arrival_seconds,
                    maximum_source_seconds=maximum_source_seconds,
                    cancel_generation=self.generation,
                )
            except BaseException:
                if ledger._busy is self._ledger_lease:
                    ledger._busy = None
                raise
            self.corridor_sha256 = sha256(encoded(dict(
                crossing_policy=crossing_policy.record(),
                cells=[c.sha256 for c in crossing_cells],
                destination=self.arrival.destination,
                destination_id=self.arrival.destination_id,
            ))).hexdigest()

    def _ValidateCells(self):
        records = [c.record() for c in self.crossing_cells]
        if records[0]['departure_floor_sha256'] != self.chain.previous.proof_sha256:
            raise ValueError('Crossing cells do not start on the retained pre-line floor proof')
        targets = []
        previous_end = tuple(records[0]['start'])
        for idx, row in enumerate(records):
            start, end = tuple(row['start']), tuple(row['end'])
            if (row['radius'] != self.bounds.body_radius
                    or encoded(row['policy']) != self._policy_bytes
                    or math.dist(previous_end, start) > 1e-6):
                raise ValueError('Crossing cells differ in radius, policy or continuity')
            if start != end:
                targets.append(_CrossingTarget(
                    idx,
                    (*start, row['start_floor_height']),
                    (*end, row['end_floor_height']),
                ))
            previous_end = end
        last = records[-1]
        if (not targets or tuple(last['start']) != tuple(last['end'])
                or last['native']['possible_flags'] != [0x80000000]):
            raise ValueError('Crossing corridor must advance to a checked cap inside the exact native transition')
        if math.dist(self.reference.package_xyz[:2], tuple(records[0]['start'])) > self.walk_half_width:
            raise ValueError('Stopped reference is outside the crossing corridor start')
        self.targets = self._targets = tuple(targets)

    def _state(self):
        return (
            _chain_snapshot(self.chain),
            id(self.reference),
            self.steps,
            self.serial,
            self.index,
            id(self.pose),
            deepcopy(vars(self.pose)),
        )

    def _source_active(self):
        return getattr(getattr(self, 'arrival', None), 'loading', None) is None

    def _current(self):
        self.check_current()
        mode = self.observer.mode_reader()
        generation = self.observer.generation_reader()
        self._bound_state(mode, generation)
        return mode, generation

    def _source_check(self):
        mode, generation = self._current()
        if not self._source_active():
            raise RouteHalt('Source crossing has already transitioned to loading')
        self.observer.check()
        self.crossing_policy.check_context(self.terrain, self.static, self.bsp)
        return mode, generation

    def _bound_state(self, mode, generation):
        p = self.policy
        if getattr(getattr(self, 'arrival', None), 'phase', None) == 'stopped':
            raise RouteHalt('Crossing arrival failed or was cancelled')
        if p is not None and (p._cancelled is not None or p.corridor is not self
                              or p.arrival is not self.arrival
                              or p.declaration is not p._declaration):
            raise RouteHalt('Crossing policy cancelled or changed')
        if (self.phase == 'stopped'
                or mode != self.mode or generation != self.generation
                or self.targets is not self._targets
                or tuple(c.payload for c in self.crossing_cells) != self._cells_payloads
                or vars(self.bounds) != self._bounds_dict
                or vars(self.motion) != self._motion_dict
                or _source_storage(self.terrain, self.static) != self._source_storage
                or encoded(self.crossing_policy.record()) != self._policy_bytes
                or self.pose.motion is not self.motion
                or not finite(self.pose.heading) or not 0 <= self.pose.heading < 360
                or self.pose._sign_votes or self.pose.sign_conflict or self.pose.turn_dead):
            raise RouteHalt('Crossing corridor owner, mode, policy or motion bindings changed')
        if self._source_active():
            if self.ledger.phase == 'stopped' or self.ledger._busy is not self._ledger_lease:
                raise RouteHalt('Underlying source ledger was cancelled or modified')
            _chain_snapshot(self.chain)

    def validate_reference(self, *, maximum_age=.5):
        return self.observer.validate(self.reference, self.chain, maximum_age=maximum_age)

    def next_command(self):
        with self.lock:
            try:
                self._source_check()
                if self.phase != 'ready':
                    raise RouteHalt('Crossing corridor is not ready for a source command')
                self.validate_reference()
                p = self.reference.package_xyz
                while self.index < len(self.targets):
                    row = self.targets[self.index]
                    target = row.end
                    remaining = math.dist(p[:2], target[:2])
                    if remaining <= .25:
                        if abs(p[2] - target[2]) > .25:
                            raise RouteHalt('Observed crossing target is on a different floor')
                        self.index += 1
                        continue
                    a, b = row.start[:2], row.end[:2]
                    length = math.dist(a, b)
                    if length:
                        along = sum((p[k] - a[k]) * (b[k] - a[k]) for k in (0, 1)) / length ** 2
                        closest = tuple(a[k] + min(1., max(0., along)) * (b[k] - a[k]) for k in (0, 1))
                        if math.dist(p[:2], closest) > self.walk_half_width or along > 1. + .25 / length:
                            raise RouteHalt('Observed source crossing movement left its planned leg')
                    heading = self.legacy.bearing(*p[:2], *target[:2])
                    error = self.legacy.wrap180(heading - self.pose.heading)
                    low, high = self.bounds.minimum_requested_hold, self.bounds.maximum_requested_hold
                    if abs(error) > 1.:
                        if high <= self.motion.turn_latency:
                            raise RouteHalt('Crossing turn cannot overcome measured latency')
                        kind = 'right' if error * self.motion.right_sign > 0 else 'left'
                        seconds = min(high, max(low, self.motion.turn_latency + abs(error) / self.motion.turn_rate))
                    else:
                        kind = 'forward'
                        speed = self.pose.speed
                        if not finite(speed) or speed <= 0:
                            raise RouteHalt('No measured source crossing walk speed')
                        count = max(1, math.ceil(remaining / (speed * high)))
                        seconds = remaining / speed / count
                        if seconds < low:
                            if count != 1 or low * speed - remaining > .25:
                                raise RouteHalt('Minimum crossing pulse overshoots its target')
                            seconds = low
                    return SourceCrossingCommand(kind, seconds, row.cell_index, target, self.reference)
                raise RouteHalt('Source crossing corridor ended without expected loading')
            except BaseException as error:
                self.cancel(str(error))
                raise

    def _check_crossing_footprint(self, chain, kind, footprint):
        sources = self.terrain.source_faces_for_footprint(footprint)
        fork = chain.fork()
        floor = fork.advance(footprint, sources)
        if not floor.candidate:
            raise RouteHalt('Crossing motion terrain: ' + floor.reason)
        placed = check_source_static_floor(floor, footprint, sources, self.static)
        if not placed.candidate:
            raise RouteHalt('Crossing motion static: ' + placed.reason)
        original_bsp = check_source_body_bsp(floor, footprint, sources, self.bsp, clip_branches=True)
        scoped_bsp = (
            original_bsp if original_bsp.candidate else check_source_body_bsp(
                floor, footprint, sources, self.bsp,
                clip_branches=True, expected_zone_line=self.line,
            )
        )
        if not scoped_bsp.candidate and scoped_bsp.reason != 'missing_bsp_child':
            raise RouteHalt('Crossing motion BSP: ' + scoped_bsp.reason)
        native = classify_source_body_regions(
            floor, footprint, sources, self.static,
            self.crossing_policy.ordinary.classifier,
            source_wld_sha256=self.crossing_policy.ordinary.wld_sha256,
        )
        touched = self.crossing_policy.classify(native)
        payload = encoded(dict(
            kind=kind,
            footprint=footprint,
            terrain=asdict(floor),
            static=asdict(placed),
            original_bsp=asdict(original_bsp),
            scoped_bsp=asdict(scoped_bsp),
            native=asdict(native),
            possible_transition_regions=touched,
            corridor_sha256=self.corridor_sha256,
            policy=self.crossing_policy.record(),
            source_floor_committed=False,
            input_authorized=False,
            real_client_accepted=False,
        ))
        return fork, SourceCrossingGeometry(kind, footprint, touched, payload, sha256(payload).hexdigest())

    def prepare(self, kind, *, policy):
        """Check whole-hold crossing geometry outside the stop lock."""
        from .supervised_source_crossing import SupervisedSourceCrossingPolicy
        try:
            with self.lock:
                self._source_check()
                self.model.check_policy(self.crossing_policy.ordinary)
                if (self.phase != 'ready'
                        or type(policy) is not SupervisedSourceCrossingPolicy
                        or policy.corridor is not self or policy.arrival is not self.arrival
                        or (self.policy is not None and self.policy is not policy)
                        or self.seal is not None or self._pending is not None
                        or self.arrival.source_collector is not None
                        or self.arrival.source_result is not None
                        or kind not in ('forward', 'left', 'right')):
                    raise RouteHalt('Idle ready crossing corridor and matching policy required')
                self.policy = policy
                self.validate_reference()
                state = self._state()
                b = self.bounds
                chain = self.chain.fork()
                footprint = motion_footprint(
                    self.reference.package_xyz[:2],
                    self.pose.heading,
                    b.forward_speed_upper_bound * b.maximum_actual_hold if kind == 'forward' else 0.,
                    position_error=b.position_error,
                    heading_error_degrees=b.heading_error_degrees,
                    post_release_drift=b.post_release_drift,
                    extra_radius=b.body_radius + (0. if kind == 'forward' else b.pivot_displacement_upper_bound),
                )
                self.phase = 'preparing'
            fork, geometry = self._check_crossing_footprint(chain, kind, footprint)
            with self.lock:
                self._source_check()
                self.validate_reference()
                self.model.check_policy(self.crossing_policy.ordinary)
                if self.phase != 'preparing' or self._state() != state:
                    raise RouteHalt('Crossing geometry cancelled or reference changed')
                self._prepared = (geometry, fork, _chain_snapshot(fork), state)
                self.phase = 'prepared'
                return geometry
        except BaseException as error:
            self.cancel(str(error))
            raise

    def stage(self, geometry, *, requested_seconds):
        with self.lock:
            try:
                self._source_check()
                self.validate_reference()
                if (self.phase != 'prepared' or self._prepared is None
                        or geometry is not self._prepared[0] or self._state() != self._prepared[3]
                        or _chain_snapshot(self._prepared[1]) != self._prepared[2]
                        or self.ticket is not None
                        or not finite(requested_seconds)
                        or not self.bounds.minimum_requested_hold <= requested_seconds <= self.bounds.maximum_requested_hold):
                    raise RouteHalt('No exact prepared source crossing movement')
                geometry.record()
                now = self._source_check()
                now_ts = self.clock()
                self._bound_state(*now)
                if (self.phase != 'prepared' or self._prepared is None or geometry is not self._prepared[0]
                        or self._state() != self._prepared[3]
                        or _chain_snapshot(self._prepared[1]) != self._prepared[2]):
                    raise RouteHalt('Crossing proposal cancelled during final check')
                self.serial += 1
                ticket = SourceCrossingTicket(
                    self.reference,
                    geometry,
                    self.serial,
                    now_ts,
                    requested_seconds,
                    self.bounds.maximum_actual_hold,
                    {'forward': 103, 'left': 105, 'right': 106}[geometry.kind],
                    bool(geometry.touched_regions),
                )
                self._pending = (ticket, self._prepared[1], self._prepared[2], self._state())
                self._prepared = None
                self.ticket = ticket
                self.receipt = None
                self.touches_line = ticket.touches_line
                self.phase = 'pulsing'
                self.check_pending(ticket)
                return ticket
            except BaseException as error:
                self.cancel(str(error))
                raise

    def check_pending(self, ticket):
        with self.lock:
            self._source_check()
            if (self.phase != 'pulsing' or self._pending is None or self._pending[0] is not ticket
                    or self.ticket is not ticket or self.seal is not None
                    or self._state() != self._pending[3]
                    or _chain_snapshot(self._pending[1]) != self._pending[2]
                    or type(ticket.geometry.payload) is not bytes
                    or sha256(ticket.geometry.payload).hexdigest() != ticket.geometry.sha256):
                raise RouteHalt('Source crossing movement transaction changed')

    def poll_loading(self):
        self._current()
        if self.phase != 'pulsing':
            raise RouteHalt('No source crossing pulse is active')
        action = self.arrival.tick()
        if action is not None:
            raise RouteHalt('Position command requested before source crossing release')
        self._current()
        return self.arrival.loading is not None

    def _retire_source_ledger(self, reason):
        if self.ledger.phase != 'stopped':
            self.ledger.cancel(reason)

    def released(self, receipt):
        with self.lock:
            try:
                self._current()
                if (self.phase != 'pulsing' or self.ticket is None or self._pending is None
                        or not isinstance(receipt, PulseReceipt)):
                    raise RouteHalt('Actual selected source crossing receipt required after cleanup')
                t = self.ticket
                self.poll_loading()
                stamps = (receipt.down_started_at, receipt.down_completed_at,
                          receipt.up_started_at, receipt.up_completed_at)
                now = self.clock()
                if (receipt.key_code != t.movement_key
                        or receipt.requested_seconds != t.requested_seconds
                        or receipt.completion not in ('elapsed', 'interrupted')
                        or not all(finite(v) for v in stamps)
                        or not t.proposed_at <= stamps[0] <= stamps[1] <= stamps[2] <= stamps[3] <= now
                        or stamps[0] - t.proposed_at > .05 or now - stamps[3] > .3
                        or not 0 < receipt.maximum_held_seconds <= t.maximum_actual_hold
                        or (receipt.completion == 'interrupted' and self.arrival.loading is None)):
                    raise RouteHalt('Source crossing receipt differs or exceeded its timing bounds')
                mode, generation = self._current()
                if self._source_active():
                    self.model.check_policy(self.crossing_policy.ordinary)
                finished = self.clock()
                self._bound_state(mode, generation)
                if (not finite(finished) or not now <= finished <= stamps[3] + .3
                        or self.phase != 'pulsing'):
                    raise RouteHalt('Source crossing receipt expired or cancelled during release completion')
                if self.arrival.loading is None:
                    self.seal = SourceMotionSeal(t, receipt, finished, stamps[3] + 10.)
                    self.phase = 'settling'
                    self.quiet_until = receipt.up_completed_at + (2.5 if self.touches_line else .12)
                else:
                    if not self.touches_line:
                        raise RouteHalt('Uncorrelated source loading')
                    self.seal = None
                    self._pending = None
                    self._retire_source_ledger('Source crossing observed expected loading; source floor discarded')
                    self.phase = 'await_arrival'
                self.receipt = receipt
                return dict(
                    receipt=asdict(receipt),
                    outcome=self.phase,
                    touches_line=self.touches_line,
                    source_floor_committed=False,
                    expected_zone_line_sha256=self.line.sha256,
                    real_client_accepted=False,
                )
            except BaseException as error:
                self.cancel(str(error))
                raise

    def _check_seal(self, seal):
        self._source_check()
        now = self.clock()
        if (self.phase not in ('settling', 'source_positions')
                or self.seal is not seal or self._pending is None
                or self._pending[0] is not seal.ticket
                or self._state() != self._pending[3]
                or _chain_snapshot(self._pending[1]) != self._pending[2]
                or not seal.sealed_at <= now <= seal.expires_at):
            raise RouteHalt('Provisional source crossing seal is missing, changed or expired')
        return self._pending[1]

    def _observe_source(self, raw):
        with self.lock:
            self._current()
            if self.phase != 'source_positions' or self.seal is None:
                raise RouteHalt('No provisional source crossing observation is active')
            branch = self._check_seal(self.seal)
            result = self.observer.observe(raw, checked_chain=branch)
            if self._check_seal(self.seal) is not branch:
                raise RouteHalt('Source crossing observation branch changed')
            return result

    def _pair(self, first, second, branch, footprint, released_at, minimum_seq):
        self.observer.validate(first, branch)
        now = self.observer.validate(second, branch, maximum_age=.5)
        a, b = first.raw_fix, second.raw_fix
        if (not finite(released_at) or released_at + .12 > a.received_monotonic
                or a.log_line_seq <= minimum_seq or b.log_line_seq != a.log_line_seq + 1
                or not .4 - 1e-9 <= b.received_monotonic - a.received_monotonic <= 2.5
                or math.dist(first.package_xyz[:2], second.package_xyz[:2]) > .25
                or abs(first.package_xyz[2] - second.package_xyz[2]) > .25
                or abs(a.raw_coordinates[2] - b.raw_coordinates[2]) > .25
                or self.observer.reader.latest is not b):
            raise RouteHalt('Source crossing needs a fresh stationary pair after release')
        poly = rational(hull(footprint))
        for obs in (first, second):
            if not inside(rational((obs.package_xyz[:2],))[0], poly):
                raise RouteHalt('Observed source pair left the checked crossing movement envelope')
        return now

    def _resolve_source_pair(self, seal, first, second):
        branch = self._check_seal(seal)
        footprint = seal.ticket.geometry.footprint
        self._pair(first, second, branch, footprint,
                   seal.receipt.up_completed_at, self.reference.raw_fix.log_line_seq)
        state = self._state()
        pose = deepcopy(self.pose)
        pose.motion = self.motion
        point = second.package_xyz[:2]
        cap, cap_geo = self._check_crossing_footprint(
            branch, 'observed_crossing_cap', swept_square(point, point, self.bounds.body_radius),
        )
        self._check_seal(seal)
        self._pair(first, second, branch, footprint,
                   seal.receipt.up_completed_at, self.reference.raw_fix.log_line_seq)
        if self._state() != state:
            raise RouteHalt('Source crossing resolution state changed')
        receipt = seal.receipt
        kind = seal.ticket.geometry.kind
        pose.predict(receipt.maximum_held_seconds, self.legacy.Controls(
            forward=kind == 'forward', turn=None if kind == 'forward' else kind))
        pose.predict(second.raw_fix.received_monotonic - receipt.up_completed_at, self.legacy.STOP)
        report = pose.correct(*second.package_xyz, age=0.)
        if (report.get('jumped') or pose._sign_votes or pose.sign_conflict
                or pose.turn_dead or pose.blocked_fixes >= 2):
            raise RouteHalt('Observed source crossing movement contradicts measured motion')
        reference = self.observer.rebind_cap(second, branch, cap)
        self._check_seal(seal)
        self.observer.validate(reference, cap, maximum_age=.5)
        self.chain, self.pose, self.reference = cap, pose, reference
        self.steps += 1
        self.seal = self._pending = self.ticket = None
        self.phase = 'ready'
        # Verify at least one target leg remains; reaching the corridor end without
        # loading must fail closed rather than idling forever.
        self.next_command()
        return cap.previous.proof_sha256, cap_geo.sha256

    def tick(self):
        try:
            with self.lock:
                self._current()
                if self.phase not in ('ready', 'settling', 'source_positions', 'await_arrival', 'complete'):
                    raise RouteHalt('Crossing sender must finish cleanup before ticking')
                action = self.arrival.tick()
                self._current()
                if self.arrival.loading is not None:
                    if not self.touches_line:
                        raise RouteHalt('Uncorrelated source loading')
                    self.seal = self._pending = None
                    self._retire_source_ledger('Source crossing observed expected loading; source floor discarded')
                    self.phase = 'complete' if self.arrival.phase == 'complete' else 'await_arrival'
                    return action
                if self.phase == 'settling' and self.clock() >= self.quiet_until:
                    self._current()
                    self.arrival.start_source_pair(
                        released_at=self.receipt.up_completed_at,
                        observe_fix=self._observe_source,
                    )
                    self.phase = 'source_positions'
                    return self.arrival.tick()
                if self.phase == 'source_positions' and self.arrival.source_result is not None:
                    pair = self.arrival.take_source_pair()
                    self._current()
                    if pair is None:
                        self.seal = self._pending = None
                        self._retire_source_ledger('Source crossing loading revoked source pair')
                        self.phase = 'await_arrival'
                        return None
                    proof_sha, cap_sha = self._resolve_source_pair(self.seal, *pair.observations)
                    self.source_steps.append(dict(
                        receipt=asdict(self.receipt),
                        floor_proof_sha256=proof_sha,
                        cap_geometry_sha256=cap_sha,
                        positions=pair.record,
                    ))
                    self._current()
                return action
        except BaseException as error:
            self.cancel(str(error))
            raise

    def command_sent(self, request, receipt):
        try:
            with self.lock:
                self._current()
                if self.phase not in ('source_positions', 'await_arrival'):
                    raise RouteHalt('Crossing corridor has no active stopped-position command')
                self.arrival.command_sent(request, receipt)
                self._current()
        except BaseException as error:
            self.cancel(str(error))
            raise

    def cancel(self, reason):
        with self.lock:
            if self.phase == 'stopped':
                return
            self.phase, self.reason = 'stopped', str(reason)
            self._prepared = self._pending = self.seal = None
            if getattr(self, 'ledger', None) is not None:
                self._retire_source_ledger(reason)
            if getattr(self, 'arrival', None) is not None:
                self.arrival.cancel(reason)

    def snapshot(self):
        return dict(
            outcome=self.phase,
            reason=self.reason,
            corridor_sha256=self.corridor_sha256,
            expected_zone_line=self.line.record(),
            source_steps=list(self.source_steps),
            arrival=self.arrival.snapshot(),
            policy=None if self.policy is None else self.policy.snapshot(),
            source_floor_provisional=self.seal is not None,
            source_navigation_state_reused=False,
            real_client_accepted=False,
        )
