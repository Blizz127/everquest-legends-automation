"""Finite owner-supervised route policy, distinct from unattended clearance.

Uses actual focus/input/log observations and the owner's open-ground statement.
Terrain/static/BSP checks remain mandatory but describe explicitly supplied
planning envelopes, not verified live dimensions or future motion bounds.
Unknown UI/dynamic clearance remains false. No device or sender is created.
"""
from dataclasses import dataclass, field
import math

from .fixed_route_follower import RouteHalt, finite
from .g2_pulse_budget import G2Scene
from .g2_scene_observer import G2ObservationUnavailable
from .g2_safety_provider import GameWindowIdentity, focused_game_identity
from .owner_input_observer import OwnerInputObservation
from .route_geometry import RouteGeometryPreparer
from .route_step_sender import RouteStepAuthorization
from .scene_log_veto import SceneLogVeto


@dataclass(frozen=True)
class SupervisedRouteDeclaration:
    record_id: str
    route_sha256: str
    motion_record_id: str
    planning_bounds_record_id: str
    open_flat_clear: bool
    maximum_seconds: float
    maximum_steps: int
    maximum_distance: float
    maximum_total_hold: float
    scope: str = 'local_trial'


def scope_limits(scope):
    """Separate explicit actions; a local trial never inherits travel limits."""
    if scope == 'local_trial':
        return (120., 32, 20., 2.)
    if scope == 'destination_travel':
        return (1500., 3000, 10000., 600.)
    raise ValueError('Unknown supervised route scope')


@dataclass(frozen=True, kw_only=True)
class SupervisedRouteScene(G2Scene):
    declaration: SupervisedRouteDeclaration
    window: GameWindowIdentity
    input_before: OwnerInputObservation
    input_after: OwnerInputObservation
    log_observation: object
    finished_at: float
    independent_scene_verified: bool = field(default=False, init=False)
    motion_bounds_verified: bool = field(default=False, init=False)


@dataclass(frozen=True, kw_only=True)
class SupervisedRouteAuthorization(RouteStepAuthorization):
    declaration: SupervisedRouteDeclaration
    independent_scene_verified: bool = field(default=False, init=False)
    motion_bounds_verified: bool = field(default=False, init=False)


class SupervisedRoutePolicy:
    """Concrete read-only provider for a current, explicit owner trial scope.

    ``check_current`` belongs to the same owner-started measure-then-trial job.
    It must retain the tested hotbutton, sender, settings and continuous input
    observer from calibration. Loading saved calibration cannot supply it.
    This policy does not own/close those shared objects. A caller must release
    them after its route driver has finished key cleanup.
    """
    def __init__(self, geometry, *, declaration, gate, owner_input, log_veto,
                 expected_log_path, expected_window, topology_generation,
                 check_current):
        if (not isinstance(geometry, RouteGeometryPreparer)
                or not isinstance(declaration, SupervisedRouteDeclaration)
                or not isinstance(expected_window, GameWindowIdentity)
                or not isinstance(log_veto, SceneLogVeto)
                or type(topology_generation) is not int or topology_generation < 0
                or not callable(check_current) or not callable(getattr(owner_input, 'sample', None))):
            raise ValueError('Explicit supervised scope, real observation providers and geometry required')
        d, r, b = declaration, geometry.ledger.runner, geometry.bounds
        seconds, steps, distance, hold = scope_limits(d.scope)
        if (not all(isinstance(v, str) and v for v in
                    (d.record_id, d.route_sha256, d.motion_record_id, d.planning_bounds_record_id))
                or d.open_flat_clear is not True or d.route_sha256 != r.route.artifact_sha256
                or d.motion_record_id != r.calibration or d.planning_bounds_record_id != b.record_id
                or not all(finite(v) for v in
                           (d.maximum_seconds, d.maximum_distance, d.maximum_total_hold))
                or not 0 < d.maximum_seconds <= seconds or not 0 < d.maximum_distance <= distance
                or not 0 < d.maximum_total_hold <= hold
                or type(d.maximum_steps) is not int or not 1 <= d.maximum_steps <= steps
                or sum(s.length for s in r.route.segments) > d.maximum_distance
                or b.maximum_requested_hold > .1 or b.maximum_actual_hold > .2
                or log_veto.tail.path != expected_log_path
                or log_veto.cancel_generation != r.generation):
            raise ValueError('Trial needs matching explicit planning assumptions and finite limits')
        self.geometry, self.ledger = geometry, geometry.ledger
        self.declaration, self.bounds = d, b
        self._declaration = d
        self.gate, self.owner_input, self.log_veto = gate, owner_input, log_veto
        self.log_path, self.window, self.topology = expected_log_path, expected_window, topology_generation
        self.check_current = check_current
        self.started = self.ledger.clock()
        self.last_at = self.started
        self.origin = None
        self.reserved_hold = 0.
        self._scene = self._authorization = None
        self._cancelled = None
        self._check()

    def cancel(self, reason):
        self._cancelled = str(reason)

    def _check(self):
        began, r, d = self.ledger.clock(), self.ledger.runner, self.declaration
        if self._cancelled is not None:
            raise RouteHalt('Supervised route stopped: '+self._cancelled)
        self.check_current()
        r._check(began)
        try:
            window = focused_game_identity(self.gate)
        except G2ObservationUnavailable as error:
            raise RouteHalt('Supervised route game focus unavailable') from error
        self.check_current()
        mode, generation, finished = r.mode_reader(), r.generation_reader(), self.ledger.clock()
        if (self._cancelled is not None or d is not self._declaration
                or mode != 'measurement' or generation != r.generation
                or not finite(began) or not finite(finished)
                or not self.last_at <= began <= finished <= self.started+d.maximum_seconds
                or r.steps >= d.maximum_steps or self.geometry.ledger is not self.ledger
                or self.geometry.bounds is not self.bounds
                or self.bounds.record_id != d.planning_bounds_record_id
                or r.route.artifact_sha256 != d.route_sha256 or r.calibration != d.motion_record_id
                or self.log_veto.tail.path != self.log_path
                or self.log_veto.cancel_generation != r.generation
                or window != self.window):
            raise RouteHalt('Supervised route scope, focus, planning inputs or finite budget changed')
        self.last_at = finished
        return began

    def observe(self, reference):
        """Fresh physical/input/log observations; never invent closed-chat UI."""
        began = self._check()
        before = self.owner_input.sample()
        log = self.log_veto.poll()
        after = self.owner_input.sample()
        self._check()
        finished = self.ledger.clock()
        if (not finite(finished) or not 0 <= finished-began <= .1
                or not all(isinstance(v, OwnerInputObservation) and v.clear_at(finished)
                           and v.topology_generation == self.topology for v in (before, after))
                or not log.continuity_available or log.reason is not None
                or not began <= before.started_at <= before.finished_at <= log.started_at
                    <= log.finished_at <= after.started_at <= after.finished_at <= finished
                or log.cancel_generation != self.ledger.runner.generation):
            raise RouteHalt('Owner activity, unavailable coverage or client-log veto during trial')
        point = reference.mesh_projection.package_xyz
        if self.origin is None:
            self.origin = point
        if math.dist(self.origin[:2], point[:2]) > self.declaration.maximum_distance:
            raise RouteHalt('Supervised route displacement budget exhausted')
        raw = reference.raw_fix
        self._scene = SupervisedRouteScene(began, self.ledger.runner.route.zone,
            raw.raw_coordinates, raw.log_epoch, raw.log_line_seq, raw.zone_generation,
            focused=True, owner_keys_clear=True, declaration=self.declaration,
            window=self.window, input_before=before, input_after=after,
            log_observation=log, finished_at=finished)
        return self._scene

    def validate_scene(self, observed, ledger):
        self._check()
        scene = observed.scene
        if (ledger is not self.ledger or type(scene) is not SupervisedRouteScene
                or scene is not self._scene or scene.declaration is not self.declaration
                or scene.window != self.window or scene.focused is not True
                or scene.owner_keys_clear is not True
                or any(v is not False for v in (scene.chat_clear, scene.target_absent,
                    scene.combat_clear, scene.no_transition, scene.no_incoming_attack,
                    scene.independent_scene_verified, scene.motion_bounds_verified))):
            raise RouteHalt('Supervised evidence is absent, foreign or mislabelled as verified')

    def authorize(self, ticket, observed):
        self.validate_scene(observed, self.ledger)
        record = self.geometry.record_for(ticket)
        self.validate_scene(observed, self.ledger)
        if (not all(x.candidate is True for x in (record.terrain, record.static, record.bsp))
                or ticket.preparation.motion_bounds_record_id != self.bounds.record_id
                or ticket.preparation.requested_seconds > .1
                or ticket.preparation.maximum_actual_hold != self.bounds.maximum_actual_hold
                or self.reserved_hold + ticket.preparation.maximum_actual_hold
                    > self.declaration.maximum_total_hold):
            raise RouteHalt('Conditional geometry or supervised hold budget refused')
        self.reserved_hold += ticket.preparation.maximum_actual_hold
        self._authorization = SupervisedRouteAuthorization(ticket, observed.reference_fix,
            self.ledger.clock(), ticket.preparation.proposal.at+.05, self.declaration.record_id,
            declaration=self.declaration)
        return self._authorization

    def validate_authorization(self, authorization, observed):
        self.validate_scene(observed, self.ledger)
        if (type(authorization) is not SupervisedRouteAuthorization
                or authorization is not self._authorization
                or authorization.declaration is not self.declaration
                or authorization.reference_fix is not observed.reference_fix
                or authorization.independent_scene_verified is not False
                or authorization.motion_bounds_verified is not False):
            raise RouteHalt('Supervised route authorization changed')

    def still_authorized(self, authorization, observed):
        self.validate_authorization(authorization, observed)
        self.geometry.record_for(authorization.ticket)
        self.validate_authorization(authorization, observed)
        return True

    def snapshot(self):
        from dataclasses import asdict
        return dict(kind='owner_supervised_route_trial', declaration=asdict(self.declaration),
            planning_bounds=asdict(self.bounds), started_monotonic=self.started,
            reserved_maximum_hold=self.reserved_hold, independent_scene_verified=False,
            motion_bounds_verified=False, dynamic_clearance_verified=False,
            real_client_accepted=False)
