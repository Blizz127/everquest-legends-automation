"""Owner-supervised source walking using real focus/input/log observations."""
from dataclasses import asdict, dataclass, field
import math

from .fixed_route_follower import RouteHalt
from .ground_binding import finite
from .g2_safety_provider import GameWindowIdentity, focused_game_identity
from .owner_input_observer import OwnerInputObservation
from .scene_log_veto import SceneLogVeto
from .source_motion import SourceReceiptLedger
from .source_transfer import SourceTransferController
from .supervised_route import SupervisedRouteDeclaration, scope_limits


@dataclass(frozen=True)
class SupervisedSourceScene:
    reference: object
    declaration: SupervisedRouteDeclaration
    at: float
    finished_at: float
    window: GameWindowIdentity
    input_before: OwnerInputObservation
    input_after: OwnerInputObservation
    log_observation: object
    independent_scene_verified: bool = field(default=False,init=False)
    motion_bounds_verified: bool = field(default=False,init=False)


@dataclass(frozen=True)
class SupervisedSourceAuthorization:
    ticket: object
    scene_reference: object
    declaration: SupervisedRouteDeclaration
    issued_at: float
    expires_at: float
    independent_scene_verified: bool = field(default=False,init=False)
    motion_bounds_verified: bool = field(default=False,init=False)


class SupervisedSourcePolicy:
    def __init__(self,ledger,*,declaration,gate,owner_input,log_veto,
                 expected_window,topology_generation,check_current):
        if (type(ledger) is not SourceReceiptLedger
                or type(declaration) is not SupervisedRouteDeclaration
                or declaration.scope not in ('local_trial','destination_travel')
                or type(expected_window) is not GameWindowIdentity
                or type(log_veto) is not SceneLogVeto
                or type(topology_generation) is not int or topology_generation<0
                or not callable(check_current) or not callable(getattr(owner_input,'sample',None))):
            raise ValueError('Explicit source measurement scope and observation providers required')
        seconds,steps,distance,hold=scope_limits(declaration.scope)
        d,b=declaration,ledger.bounds
        if (not all(type(s) is str and s for s in
                (d.record_id,d.route_sha256,d.motion_record_id,d.planning_bounds_record_id))
                or d.route_sha256!=ledger.observer.itinerary.sha256
                or d.motion_record_id!=b.calibration_record_id
                or d.planning_bounds_record_id!=b.record_id or d.open_flat_clear is not True
                or not all(finite(v) for v in (d.maximum_seconds,d.maximum_distance,d.maximum_total_hold))
                or not 0<d.maximum_seconds<=seconds or not 0<d.maximum_distance<=distance
                or not 0<d.maximum_total_hold<=hold or type(d.maximum_steps) is not int
                or not 1<=d.maximum_steps<=steps
                or log_veto.tail.path!=ledger.observer.reader.tail.path
                or log_veto.cancel_generation!=ledger.observer.generation):
            raise ValueError('Source scope must match itinerary, motion, log and finite budgets')
        self.ledger,self.declaration,self.gate=ledger,d,gate
        self._ordinary_ledger=ledger
        self.owner_input,self.log_veto=owner_input,log_veto
        self.window,self.topology,self.check_current=expected_window,topology_generation,check_current
        self._context=(ledger,d,gate,owner_input,log_veto,check_current)
        self.started=self.last_at=ledger.clock()
        self.origin=None;self.reserved_hold=0.
        self._scene=self._authorization=None
        self._check()

    def bind_transfer(self,controller):
        """Keep the same physical observers, start time and aggregate budgets."""
        if type(controller) is not SourceTransferController:
            raise ValueError('Exact source transfer controller required')
        with controller.lock:
            self._check();controller._check()
            if self.ledger is not self._ordinary_ledger or controller.ordinary is not self.ledger:
                raise RouteHalt('Source policy already leased or transfer belongs to another job')
            self.ledger=controller
            self._context=(controller,*self._context[1:])
            self._scene=self._authorization=None
            self._check()

    def finish_transfer(self,controller):
        with controller.lock:
            if (self.ledger is not controller or controller.ordinary is not self._ordinary_ledger
                    or controller.phase not in ('approach','landed')
                    or self._ordinary_ledger.phase!='ready' or self._ordinary_ledger._busy is not None):
                raise RouteHalt('Source transfer has no published observed cap')
            self.ledger=self._ordinary_ledger
            self._context=(self.ledger,*self._context[1:])
            self._scene=self._authorization=None
            self._check()

    def _check(self):
        self.check_current();began=self.ledger._check()
        window=focused_game_identity(self.gate)
        self.check_current();finished=self.ledger._check();d=self.declaration
        self.ledger.model.check_policy(self.ledger.observer.policy)
        if (any(a is not b for a,b in zip(self._context,(self.ledger,d,self.gate,
                self.owner_input,self.log_veto,self.check_current)))
                or window!=self.window or not self.last_at<=began<=finished<=self.started+d.maximum_seconds
                or self.ledger.steps>=d.maximum_steps
                or d.route_sha256!=self.ledger.observer.itinerary.sha256
                or self.log_veto.tail.path!=self.ledger.observer.reader.tail.path
                or self.log_veto.cancel_generation!=self.ledger.observer.generation):
            raise RouteHalt('Source scope, focus, log or movement budget changed')
        self.last_at=finished
        return began

    def observe(self):
        began=self._check();reference=self.ledger.reference
        self.ledger.validate_reference()
        before=self.owner_input.sample();log=self.log_veto.poll();after=self.owner_input.sample()
        self._check();finished=self.ledger.clock()
        if (reference is not self.ledger.reference
                or not 0<=finished-began<=.1
                or not all(type(v) is OwnerInputObservation and v.clear_at(finished)
                    and v.topology_generation==self.topology for v in (before,after))
                or not log.continuity_available or log.reason is not None
                or not began<=before.started_at<=before.finished_at<=log.started_at
                    <=log.finished_at<=after.started_at<=after.finished_at<=finished
                or log.cancel_generation!=self.ledger.observer.generation):
            raise RouteHalt('Source owner activity or log/observation veto')
        if self.origin is None:self.origin=reference.package_xyz
        if math.dist(self.origin[:2],reference.package_xyz[:2])>self.declaration.maximum_distance:
            raise RouteHalt('Source displacement budget exhausted')
        self._scene=SupervisedSourceScene(reference,self.declaration,began,finished,
            self.window,before,after,log)
        return self._scene

    def validate_scene(self,scene):
        self._check();now=self.ledger.clock()
        if (type(scene) is not SupervisedSourceScene or scene is not self._scene
                or scene.reference is not self.ledger.reference
                or scene.declaration is not self.declaration or scene.window!=self.window
                or not scene.at<=scene.finished_at<=now<=scene.at+.1
                or scene.independent_scene_verified is not False or scene.motion_bounds_verified is not False):
            raise RouteHalt('Source supervised scene is stale or foreign')
        self.ledger.validate_reference()

    def authorize(self,ticket,scene):
        # These checks send nothing. Validate the scene after the pending-ticket
        # callback, once, immediately before publishing authorization.
        self.ledger.check_pending(ticket)
        self.validate_scene(scene)
        if (ticket.reference is not scene.reference
                or self.reserved_hold+ticket.maximum_actual_hold>self.declaration.maximum_total_hold):
            raise RouteHalt('Source movement reference or hold budget refused')
        issued=self.ledger.clock()
        if not ticket.proposed_at<=issued<=ticket.proposed_at+.05:
            raise RouteHalt('Source DOWN authorization expired')
        self.reserved_hold+=ticket.maximum_actual_hold
        self._authorization=SupervisedSourceAuthorization(ticket,scene.reference,self.declaration,
            issued,ticket.proposed_at+.05)
        return self._authorization

    def still_authorized(self,authorization,scene):
        if type(authorization) is not SupervisedSourceAuthorization:
            raise RouteHalt('Source authorization changed')
        self.ledger.check_pending(authorization.ticket)
        self.validate_scene(scene)
        if (type(authorization) is not SupervisedSourceAuthorization
                or authorization is not self._authorization
                or authorization.declaration is not self.declaration
                or authorization.scene_reference is not scene.reference):
            raise RouteHalt('Source authorization changed')
        return True  # expires_at is the DOWN deadline, not the release deadline.

    def snapshot(self):
        return dict(kind='owner_supervised_source_walk',declaration=asdict(self.declaration),
            reserved_maximum_hold=self.reserved_hold,
            installed_region_model=self.ledger.model.record(),
            independent_scene_verified=False,motion_bounds_verified=False,
            dynamic_clearance_verified=False,real_client_accepted=False)
