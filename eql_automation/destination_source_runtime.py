"""Adopt freshly measured destination motion without replacing its live scope.

This helper sends nothing. The returned ordinary source runtime still requires
another stopped pair and a supervised policy before its first movement.
"""
from dataclasses import dataclass, replace

from .camp_source_runtime import CampSourcePlan, CampSourceRuntime
from .destination_bootstrap_runtime import DestinationBootstrapRuntime
from .flat_record import flat_record_state
from .ground_binding import finite
from .journey_input_budget import JourneyInputBudget, itinerary_root
from .native_region_policy import encoded
from .supervised_route import SupervisedRouteDeclaration, scope_limits
from .supervised_source import SupervisedSourcePolicy
from .zone_itinerary_budget import ZoneItineraryBudget


@dataclass(frozen=True)
class DestinationSourceDeclaration:
    record_id: str
    owner_supervised_continuation: bool
    maximum_seconds: float
    maximum_steps: int
    maximum_distance: float
    maximum_total_hold: float
    walk_half_width: float

    def validate(self):
        seconds, steps, distance, hold = scope_limits('camp_continuation')
        if (type(self.record_id) is not str or not 1 <= len(self.record_id) <= 128
                or self.owner_supervised_continuation is not True
                or not all(finite(v) for v in (self.maximum_seconds, self.maximum_distance,
                    self.maximum_total_hold, self.walk_half_width))
                or not 0 < self.maximum_seconds <= seconds
                or type(self.maximum_steps) is not int or not 1 <= self.maximum_steps <= steps
                or not 0 < self.maximum_distance <= distance
                or not 0 < self.maximum_total_hold <= hold
                or not .05 <= self.walk_half_width <= 6.):
            raise ValueError('Explicit finite destination source supervision and walk width required')


class _DestinationSourceScope:
    def __init__(self, destination, declaration, legacy, current, mode_reader,
                 generation_reader, generation, budget):
        self.destination, self.probe = destination, destination.runtime
        self.declaration, self.legacy = declaration, legacy
        self.current, self.mode_reader = current, mode_reader
        self.generation_reader, self.generation = generation_reader, generation
        self.budget, self.root = budget, itinerary_root(budget)
        self.clock, self.lock = destination.clock, destination.lock
        self.stage = None if self.root is None else self.root.stage
        self.started = self.last_at = self.clock()
        self.expires_at = min(destination.expires_at, self.started+declaration.maximum_seconds,
                             float('inf') if budget is None else budget.expires_at)
        self._times = self.started, self.expires_at
        self._declaration = flat_record_state(declaration)
        self._motion_type = legacy.Motion
        self._context = (destination, self.probe, declaration, legacy, current, mode_reader,
            generation_reader, generation, budget, self.root, self.clock, self.lock)
        self.runtime = self._runtime = None
        self.fit = self._fit_bytes = None
        self.valid, self.reason = True, ''

    def cancel(self, reason):
        if self.valid:self.reason = str(reason)
        self.valid = False
        if self._runtime is not None:self._runtime.cancel(self.reason)
        self.destination.cancel(self.reason)
        if self.budget is not None:self.budget.cancel(self.reason)

    def check(self):
        try:
            if not self.valid:raise ValueError(self.reason)
            self.current()
            self.destination._check_context()
            if self.budget is not None:self.budget.check()
            mode, generation = self.mode_reader(), self.generation_reader()
            now = self.clock()
            self.current()
            self.destination._check_context()
            if self.budget is not None:self.budget.check()
            after_generation, after_mode = self.generation_reader(), self.mode_reader()
            d = self.destination
            actual = (d, d.runtime, self.declaration, self.legacy, self.current, self.mode_reader,
                self.generation_reader, self.generation, self.budget, itinerary_root(self.budget),
                d.clock, d.lock)
            if (not self.valid or any(a is not b for a,b in zip(self._context, actual))
                    or getattr(d, '_source_adoption_claim', None) is not self
                    or d.phase != 'route_ready' or d.busy or d.closed
                    or self.probe.phase != 'route_ready' or self.probe.busy or self.probe.closed
                    or self.runtime is not self._runtime
                    or self._runtime is not None and self._runtime.phase == 'stopped'
                    or flat_record_state(self.declaration) != self._declaration
                    or self.legacy.Motion is not self._motion_type
                    or (self.started, self.expires_at) != self._times
                    or self.root is not None and self.root.stage is not self.stage
                    or mode != 'camp_route' or after_mode != 'camp_route'
                    or type(generation) is not int or type(after_generation) is not int
                    or generation != self.generation or after_generation != self.generation
                    or not finite(now) or not self.started <= self.last_at <= now <= self.expires_at
                    or self.fit is not None and encoded(self.fit) != self._fit_bytes):
                raise ValueError('Destination source adoption ownership, stage or fixed deadline changed')
            d.bootstrap._assert_intact()
            # The final generation/mode/provider reads may consume the shorter
            # source scope even while the destination's broader scope is live.
            finished = self.clock()
            if (not self.valid or d.phase != 'route_ready' or d.closed
                    or d.bootstrap.phase == 'stopped'
                    or self.root is not None and self.root.stage is not self.stage
                    or not finite(finished) or not now <= finished <= self.expires_at):
                raise ValueError('Destination source deadline or ownership changed during callbacks')
            self.last_at = finished
            return finished
        except BaseException as error:
            self.cancel(error)
            raise

    def scene(self):
        try:
            self.check()
            self.destination._check_scene()
            self.check()
        except BaseException as error:
            self.cancel(error)
            raise

    def policy(self, ledger, current):
        try:
            self.check()
            current()
            remaining = self.expires_at-self.clock()
            if not finite(remaining) or remaining <= 0:
                raise ValueError('Destination source deadline expired during startup')
            d = self.declaration
            declaration = SupervisedRouteDeclaration(d.record_id, ledger.observer.itinerary.sha256,
                ledger.bounds.calibration_record_id, ledger.bounds.record_id, False,
                min(d.maximum_seconds, remaining), d.maximum_steps, d.maximum_distance,
                min(d.maximum_total_hold, remaining), 'camp_continuation', True)
            destination = self.destination
            result = SupervisedSourcePolicy(ledger, declaration=declaration,
                gate=destination.gate, owner_input=destination.owner_input,
                log_veto=destination.log_veto, expected_window=destination.window,
                topology_generation=destination.topology, check_current=current,
                journey_budget=self.budget, release_deadline=self.expires_at)
            self.check()
            return result
        except BaseException as error:
            self.cancel(error)
            raise


def start_destination_source(destination, *, declaration, legacy, check_current,
                             mode_reader, generation_reader, generation, journey_budget=None):
    """Consume one fresh route start and retain the destination bootstrap parent.

    Without a separate child budget, the destination's root budget is retained.
    A section JourneyInputBudget must already bridge that root's adjacent walking
    stage. Otherwise this helper advances bootstrap to walking after validating
    the fresh fit. No saved calibration or source-zone motion is accepted.
    """
    if (type(destination) is not DestinationBootstrapRuntime
            or type(declaration) is not DestinationSourceDeclaration
            or type(generation) is not int or generation < 0
            or not isinstance(getattr(legacy, 'Motion', None), type)
            or not all(callable(v) for v in (check_current, mode_reader, generation_reader))
            or journey_budget is not None and type(journey_budget) not in
                (ZoneItineraryBudget, JourneyInputBudget)):
        raise ValueError('Exact destination parent, explicit source limits and live owner callbacks required')
    declaration.validate()
    with destination.lock:
        if (destination.phase != 'route_ready' or destination.busy or destination.closed
                or hasattr(destination, '_source_adoption_claim')):
            raise ValueError('Fresh idle destination route start may only be adopted once')
        budget = destination.journey_budget if journey_budget is None else journey_budget
        root = itinerary_root(budget)
        if (root is not destination.journey_budget
                or budget is not None and (budget.clock is not destination.clock
                                          or budget.lock is not destination.lock)
                or generation != destination.bootstrap.generation):
            raise ValueError('Destination source must retain its original root, clock, lock and generation')
        if root is not None:
            stage, initial = root.stage, destination._budget_stage
            if not (stage is initial and stage.phase == 'bootstrap' or
                    stage.phase == 'walking' and stage.leg_index == initial.leg_index
                    and stage.epoch == initial.epoch+1):
                raise ValueError('Exact destination bootstrap or adjacent walking stage required')
        scope = _DestinationSourceScope(destination, declaration, legacy, check_current,
            mode_reader, generation_reader, generation, budget)
        destination._source_adoption_claim = scope
        try:
            scope.scene()
            fit = destination.fresh_fit()
            scope.fit, scope._fit_bytes = fit, encoded(fit)
            scope.check()
            estimate = fit['estimate']
            bounds = replace(scope.probe.root.bounds,
                record_id='destination-route-'+scope.probe.route_preparation.itinerary.sha256,
                maximum_requested_hold=min(.1, scope.probe.root.bounds.maximum_requested_hold))
            motion = legacy.Motion(run_speed=estimate['run_speed'], turn_rate=estimate['turn_rate'],
                right_sign=estimate['right_sign'], turn_latency=estimate['turn_latency'], back_speed=0.)
            plan = CampSourcePlan(bounds, legacy, motion, estimate['final_heading'],
                                  declaration.walk_half_width, scope.policy)
            plan.state()
            scope.check()
            if root is not None and root.stage.phase == 'bootstrap':
                scope.stage = root.advance(scope.stage, 'walking', zone_id=destination.reader.zone_id)
                scope.check()
            runtime = CampSourceRuntime(scope.probe, plan, check_current=scope.check,
                mode_reader=mode_reader, generation_reader=generation_reader, generation=generation,
                check_scene=scope.scene, input_release_deadline=scope.expires_at)
            scope.runtime = scope._runtime = runtime
            scope.scene()
            return runtime
        except BaseException as error:
            scope.cancel(error)
            raise
