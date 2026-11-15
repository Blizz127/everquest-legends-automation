"""Owner-supervised source-native crossing policy.

Pairs one SourceCrossingCorridor and its ZoneArrivalHandoff with real window
focus, physical owner-input sampling, ExpectedArrivalLogVeto continuity, and
strict aggregate step/hold/displacement/time budgets. No independent scene or
motion-bound verification is claimed.
"""
from dataclasses import asdict, dataclass, field
import math

from .fixed_route_follower import RouteHalt
from .g2_safety_provider import GameWindowIdentity, focused_game_identity
from .ground_binding import digest, finite
from .owner_input_observer import OwnerInputObservation
from .scene_log_veto import ExpectedArrivalLogVeto
from .source_crossing_corridor import SourceCrossingCorridor, SourceCrossingTicket
from .supervised_corridor import SupervisedCorridorDeclaration
from .supervised_route import scope_limits
from .zone_arrival import ZoneArrivalHandoff
from .zone_itinerary_budget import ZoneItineraryBudget


@dataclass(frozen=True)
class SupervisedSourceCrossingScene:
    reference: object
    declaration: SupervisedCorridorDeclaration
    at: float
    finished_at: float
    window: GameWindowIdentity
    input_before: OwnerInputObservation
    input_after: OwnerInputObservation
    log_observation: object
    independent_scene_verified: bool = field(default=False, init=False)
    motion_bounds_verified: bool = field(default=False, init=False)


@dataclass(frozen=True)
class SupervisedSourceCrossingAuthorization:
    ticket: SourceCrossingTicket
    scene_reference: object
    declaration: SupervisedCorridorDeclaration
    issued_at: float
    expires_at: float
    independent_scene_verified: bool = field(default=False, init=False)
    motion_bounds_verified: bool = field(default=False, init=False)


class SupervisedSourceCrossingPolicy:
    def __init__(self, corridor, *, declaration, gate, owner_input,
                 expected_window, topology_generation, check_current, journey_budget=None):
        if (type(corridor) is not SourceCrossingCorridor
                or type(corridor.arrival) is not ZoneArrivalHandoff
                or type(declaration) is not SupervisedCorridorDeclaration
                or declaration.scope != 'zone_crossing_corridor'
                or type(expected_window) is not GameWindowIdentity
                or type(topology_generation) is not int or topology_generation < 0
                or not callable(check_current)
                or journey_budget is not None and (type(journey_budget) is not ZoneItineraryBudget
                    or journey_budget.lock is not corridor.lock or journey_budget.clock is not corridor.clock)
                or not callable(getattr(owner_input, 'sample', None))):
            raise ValueError('Explicit source crossing corridor, declaration and observation providers required')
        seconds, steps, distance, hold = scope_limits('zone_crossing_corridor')
        d = declaration
        b = corridor.bounds
        a = corridor.arrival
        veto = a.veto
        if (type(veto) is not ExpectedArrivalLogVeto
                or not all(type(s) is str and s for s in
                           (d.record_id, d.route_sha256, d.motion_record_id,
                            d.planning_bounds_record_id, d.destination))
                or not digest(d.expected_zone_line_sha256)
                or d.record_id != corridor.line.crossing_id
                or d.route_sha256 != corridor.corridor_sha256
                or d.motion_record_id != b.calibration_record_id
                or d.planning_bounds_record_id != b.record_id
                or d.expected_zone_line_sha256 != corridor.line.sha256
                or d.destination != a.destination
                or a.maximum_source_seconds != d.maximum_seconds
                or not (d.open_flat_clear or d.owner_supervised_continuation)
                or not all(finite(v) for v in (d.maximum_seconds, d.maximum_distance, d.maximum_total_hold))
                or not 0 < d.maximum_seconds <= seconds
                or not 0 < d.maximum_distance <= distance
                or not 0 < d.maximum_total_hold <= hold
                or type(d.maximum_steps) is not int or not 1 <= d.maximum_steps <= steps
                or veto.tail.path != corridor.observer.reader.tail.path
                or veto.cancel_generation != corridor.generation):
            raise ValueError('Source crossing declaration differs from corridor, line, destination or budgets')
        self.corridor = corridor
        self.arrival = a
        self.declaration = self._declaration = d
        self.gate = gate
        self.owner_input = owner_input
        self.log_veto = veto
        self.window = expected_window
        self.topology = topology_generation
        self.check_current = check_current
        self.journey_budget = journey_budget
        self._journey_reservation = None
        self._context = (corridor, a, d, gate, owner_input, veto, check_current, journey_budget)
        self.started = self.last_at = corridor.clock()
        self.origin = None
        self.reserved_hold = 0.
        self._tickets = []
        self._admitting = False
        self._cancelled = None
        self._scene = self._authorization = None
        self._check()

    def cancel(self, reason):
        with self.corridor.lock:
            if self._cancelled is None:
                self._cancelled = str(reason)
            self._scene = self._authorization = None
            self.corridor.cancel(reason)

    def _check(self):
        if self._cancelled is not None:
            raise RouteHalt('Source crossing policy cancelled: ' + self._cancelled)
        if self.journey_budget is not None:
            self.journey_budget.check()
        a = self.arrival
        if a.loading is not None or a.phase != 'await_loading':
            raise RouteHalt('Source crossing movement ends on loading or arrival cancellation')
        self.check_current()
        self.corridor._current()
        began = self.corridor.clock()
        window = focused_game_identity(self.gate)
        self.check_current()
        self.corridor._current()
        finished = self.corridor.clock()
        d = self.declaration
        if (self._cancelled is not None
                or any(x is not y for x, y in zip(
                    self._context,
                    (self.corridor, self.arrival, d, self.gate,
                     self.owner_input, self.log_veto, self.check_current, self.journey_budget)))
                or a.loading is not None or a.phase != 'await_loading'
                or window != self.window
                or not self.last_at <= began <= finished <= self.started + d.maximum_seconds
                or len(self._tickets) > d.maximum_steps
                or d.route_sha256 != self.corridor.corridor_sha256
                or self.log_veto.tail.path != self.corridor.observer.reader.tail.path
                or self.log_veto.cancel_generation != self.corridor.generation):
            raise RouteHalt('Source crossing scope, focus, log or aggregate budget changed')
        self.last_at = finished
        if self.journey_budget is not None:
            self.journey_budget.check()
        return began

    def _physical_observation(self, began):
        before = self.owner_input.sample()
        log = self.log_veto.poll()
        after = self.owner_input.sample()
        self._check()
        finished = self.last_at
        if (not 0 <= finished - began <= .1
                or not all(type(v) is OwnerInputObservation and v.clear_at(finished)
                           and v.topology_generation == self.topology for v in (before, after))
                or not log.continuity_available or log.reason is not None
                or not began <= before.started_at <= before.finished_at <= log.started_at
                    <= log.finished_at <= after.started_at <= after.finished_at <= finished
                or log.cancel_generation != self.corridor.generation):
            raise RouteHalt('Source crossing owner activity or log/observation veto')
        return before, log, after, finished

    def observe(self, *, validate_reference=True):
        began = self._check()
        reference = self.corridor.reference
        if validate_reference:
            self.corridor.validate_reference()
        before, log, after, finished = self._physical_observation(began)
        if reference is not self.corridor.reference:
            raise RouteHalt('Source crossing reference changed during observation')
        if self.origin is None:
            self.origin = reference.package_xyz
        if math.dist(self.origin[:2], reference.package_xyz[:2]) > self.declaration.maximum_distance:
            raise RouteHalt('Source crossing displacement budget exhausted')
        self._scene = SupervisedSourceCrossingScene(
            reference, self.declaration, began, finished,
            self.window, before, after, log,
        )
        return self._scene

    def validate_scene(self, scene, *, maximum_reference_age=.5):
        self._check()
        now = self.corridor.clock()
        if (type(scene) is not SupervisedSourceCrossingScene
                or scene is not self._scene
                or scene.reference is not self.corridor.reference
                or scene.declaration is not self.declaration
                or scene.window != self.window
                or not scene.at <= scene.finished_at <= now <= scene.at + .1
                or scene.independent_scene_verified is not False
                or scene.motion_bounds_verified is not False):
            raise RouteHalt('Source crossing supervised scene is stale or foreign')
        self.corridor.validate_reference(maximum_age=maximum_reference_age)

    def authorize(self, ticket, scene):
        with self.corridor.lock:
            if (self._admitting or any(ticket is old for old in self._tickets)
                    or len(self._tickets) >= self.declaration.maximum_steps):
                self.cancel('Crossing step already reserved or aggregate budget exhausted')
                raise RouteHalt('No new movement slot in the same source crossing corridor')
            self._admitting = True
            try:
                self.corridor.check_pending(ticket)
                self.validate_scene(scene)
                if (type(ticket) is not SourceCrossingTicket
                        or ticket.reference is not scene.reference
                        or ticket.movement_key not in (103, 105, 106)
                        or ticket.geometry.record()['corridor_sha256'] != self.corridor.corridor_sha256
                        or self.reserved_hold + ticket.maximum_actual_hold > self.declaration.maximum_total_hold):
                    raise RouteHalt('Source crossing reference, corridor identity or hold budget refused')
                issued = self.corridor.clock()
                if not ticket.proposed_at <= issued <= ticket.proposed_at + .05:
                    raise RouteHalt('Source crossing DOWN authorization expired')
                if self.journey_budget is not None:
                    self._journey_reservation = self.journey_budget.reserve(ticket, bounds=self.corridor.bounds)
                self._tickets.append(ticket)
                self.reserved_hold += ticket.maximum_actual_hold
                self._authorization = SupervisedSourceCrossingAuthorization(
                    ticket, scene.reference, self.declaration,
                    issued, ticket.proposed_at + .05,
                )
                return self._authorization
            except BaseException as error:
                self.cancel(str(error))
                raise
            finally:
                self._admitting = False

    def still_authorized(self, authorization, scene):
        if type(authorization) is not SupervisedSourceCrossingAuthorization:
            raise RouteHalt('Source crossing authorization changed')
        self.corridor.check_pending(authorization.ticket)
        self.validate_scene(scene, maximum_reference_age=1.5)
        if (type(authorization) is not SupervisedSourceCrossingAuthorization
                or authorization is not self._authorization
                or authorization.declaration is not self.declaration
                or authorization.scene_reference is not scene.reference):
            raise RouteHalt('Source crossing authorization changed')
        if self.journey_budget is not None:
            if (self._journey_reservation is None
                    or self._journey_reservation.ticket is not authorization.ticket):
                raise RouteHalt('Missing whole-itinerary crossing reservation')
            self.journey_budget.check(self._journey_reservation)
        return True

    def snapshot(self):
        return dict(
            kind='owner_supervised_source_crossing_corridor',
            declaration=asdict(self.declaration),
            reserved_movements=len(self._tickets),
            reserved_maximum_hold=self.reserved_hold,
            journey_budget=None if self.journey_budget is None else self.journey_budget.snapshot(),
            expected_zone_line=self.corridor.line.record(),
            destination=self.declaration.destination,
            installed_region_model=self.corridor.model.record(),
            independent_scene_verified=False,
            motion_bounds_verified=False,
            dynamic_clearance_verified=False,
            real_client_accepted=False,
        )
