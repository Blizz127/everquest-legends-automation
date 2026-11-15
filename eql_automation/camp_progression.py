"""Finite Newbie -> Goblin -> Slave Mines intent, separate from input authority.

Only actual owner camp handoffs advance the retained generation. A configured
level never supplies a Goblin departure event. This module neither sends input
nor calls retired navigation bindings, and cancelling it does not own device
cleanup. The existing engine remains responsible for stopping its input owner.
"""
from dataclasses import dataclass, field
from hashlib import sha256
import json
from types import SimpleNamespace

from .camp_floor_checkpoint import CampFloorCheckpoint
from .camp_motion_continuity import CampInputContinuity
from .camp_recovery import CampRecovery
from .camp_session import CampLevelAdvance, StationaryCamp
from .camp_source_runtime import CampSourceRuntime
from .camp_stopped_height import CampStoppedHeight
from .flat_record import flat_record_state, _value
from .g2_safety_provider import focused_game_identity
from .ground_binding import finite
from .location_hotkey import OwnerLocationHotkey
from .location_log import LocationLogReader, RawLocationFix
from .native_region_policy import encoded
from .owner_camp_probe import CampProbePlan
from .owner_navigation_preflight import settings_identity
from .owner_route_trial import zone_binding
from .owner_source_runtime import OwnerSourceRuntime
from .owner_zone_tracker import LiveZoneTracker, ZoneReaderLease
from .route_step_sender import _fd_identity
from .scene_log_veto import SceneLogVeto
from .section_continuation import SectionArrival
from .source_arrival import assert_retained_arrival
from .source_section_manifest import WalkingSections
from .source_walk_driver import SourceWalkFinished
from .zone_itinerary_budget import ZoneItineraryBudget, _declaration_state


CAMP_PROGRESSION_ID = 'butcher-newbie-goblin-slave-mines'
CAMP_PROGRESSION_ITINERARY_ID = 'butcher-goblin-gfay-crushbone-slave-mines-camp'


@dataclass(frozen=True)
class CampProgressionSelection:
    profile_id: str
    initial_destination_id: str
    trigger_destination_id: str
    terminal_destination_id: str
    itinerary_id: str
    evidence: bytes
    _state: tuple = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if ((self.profile_id, self.initial_destination_id, self.trigger_destination_id,
                self.terminal_destination_id, self.itinerary_id) !=
                (CAMP_PROGRESSION_ID, 'newbie-hills', 'goblin-camp', 'slave-mines',
                 CAMP_PROGRESSION_ITINERARY_ID)
                or type(self.evidence) is not bytes or not 0 < len(self.evidence) <= 16384):
            raise ValueError('Exact finite Newbie/Goblin/Slave Mines selection required')
        record = json.loads(self.evidence)
        if (type(record) is not dict or encoded(record) != self.evidence
                or record.get('input_authorized') is not False
                or record.get('real_client_accepted') is not False):
            raise ValueError('Canonical copied selection evidence cannot claim input or acceptance')
        object.__setattr__(self, '_state', self.state())

    def state(self):
        return (type(self), id(self), self.profile_id, self.initial_destination_id,
            self.trigger_destination_id, self.terminal_destination_id, self.itinerary_id,
            id(self.evidence), self.evidence)

    def check(self):
        if self.state() != self._state:
            raise ValueError('Camp progression selection changed')


def _receipt_state(receipt):
    if type(receipt) is not SourceWalkFinished:
        raise ValueError('Exact ordinary stopped arrival required')
    return (type(receipt), id(receipt), _value(receipt.real_client_accepted),
        tuple((name, ('reference', id(value)) if name == 'reference' else _value(value))
              for name, value in vars(receipt).items()))


def _height_state(height):
    if type(height) is not CampStoppedHeight:
        raise ValueError('Actual fresh camp height correspondence required')
    return (id(height), id(height.checkpoint), flat_record_state(height.first),
        flat_record_state(height.second), height.package_xyz, height.raw_z_minus_source_z,
        height.observed_at, height.expires_at, id(height.payload), height.payload, height.sha256,
        height.input_authorized, height.real_client_accepted)


@dataclass(frozen=True)
class CampProgressionIntent:
    engine: object
    journey: object
    selection: CampProgressionSelection
    request_bytes: bytes
    sender: object
    ui: object
    gate: object
    tracker: LiveZoneTracker
    reader: LocationLogReader
    settings: tuple
    generation: int
    epochs: tuple
    window: object
    fd: int
    fd_identity: tuple
    clock: object
    lock: object
    _log_context: tuple = field(init=False, repr=False, compare=False)
    _state: tuple = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        object.__setattr__(self, '_log_context', (id(self.reader.tail), self.reader.tail.path,
            self.reader.tail.identity, self.reader.tail.epoch))
        object.__setattr__(self, '_state', self.state())

    def state(self):
        return (tuple(map(id, (self.engine, self.journey, self.selection, self.sender,
            self.ui, self.gate, self.tracker, self.reader, self.clock, self.lock))),
            self.selection.state(), id(self.request_bytes), self.request_bytes,
            self.settings, self.generation, self.epochs, flat_record_state(self.window),
            self.fd, self.fd_identity, self._log_context)

    def check(self):
        self.selection.check()
        if (self.state() != self._state or (id(self.reader.tail), self.reader.tail.path,
                self.reader.tail.identity, self.reader.tail.epoch) != self._log_context):
            raise ValueError('Original camp progression request or owner identity changed')


@dataclass(frozen=True)
class CampProgressionOrigin:
    controller: object
    pending: SimpleNamespace
    journey: object
    camp: StationaryCamp
    level_advance: CampLevelAdvance
    recovery: CampRecovery
    floor: CampFloorCheckpoint
    monitor: CampInputContinuity
    height: CampStoppedHeight
    lease: ZoneReaderLease
    reader: LocationLogReader
    hotkey: OwnerLocationHotkey
    veto: SceneLogVeto
    destination: object
    historical_settings: tuple
    current_settings: tuple
    generation: int
    epochs: tuple
    zone: tuple
    window: tuple
    captured_at: float
    _state: tuple = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        object.__setattr__(self, '_state', self.state())

    def state(self):
        return (tuple(map(id, (self.controller, self.pending, self.journey, self.camp,
            self.level_advance, self.recovery, self.floor, self.monitor, self.height,
            self.lease, self.reader, self.hotkey, self.veto, self.destination))),
            flat_record_state(self.level_advance), flat_record_state(self.recovery),
            self.floor.sha256, id(self.monitor.observer), self.monitor.topology,
            id(self.monitor.basis), self.monitor.basis, _height_state(self.height),
            self.historical_settings, self.current_settings, self.generation, self.epochs,
            self.zone, self.window, self.captured_at)

    def check_identity(self):
        if self.state() != self._state:
            raise ValueError('Observed Goblin progression origin changed')


@dataclass(frozen=True)
class TerminalProgressionReceipt:
    controller: object
    intent: CampProgressionIntent
    origin: CampProgressionOrigin
    root: ZoneItineraryBudget
    token: object
    generation: int
    consumed_at: float
    _state: tuple = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        object.__setattr__(self, '_state', self.state())

    def state(self):
        a = self.token.arrival
        return (tuple(map(id, (self.controller, self.intent, self.origin, self.root, self.token))),
            self.intent.state(), self.origin.state(), self.generation, self.consumed_at,
            _declaration_state(self.root.declaration), flat_record_state(self.root.stage),
            self.root.started, self.root.expires_at, self.root._balance,
            id(a), id(a.runtime), _receipt_state(a.receipt), id(a.checkpoint), a.checkpoint.sha256,
            id(a.budget), id(self.token.monitor), id(self.token.monitor.observer))

    def check_identity(self):
        self.intent.check(); self.origin.check_identity()
        if self.state() != self._state:
            raise ValueError('Consumed terminal progression receipt changed')


class CampProgression:
    """One original request, two checked camp adoptions, one finite trip."""
    def __init__(self, intent):
        if type(intent) is not CampProgressionIntent:
            raise ValueError('Exact original progression intent required')
        intent.check()
        self.intent = self._intent = intent
        self._phase = 'newbie_request'; self._generation = intent.generation
        self._journey_settings = intent.settings
        self._camp = self._camp_floor = self._camp_monitor = self._camp_progress = self._camp_destination = None
        self._camp_attribution = None
        self._origin = self._root = self._probe_plan = self._probe_state = None
        self._root_declaration = None; self._promoted = False
        self._terminal = self._terminal_camp = None
        self._cancelled = False; self._reason = ''
        self._adoptions = ()
        self._state = self._snapshot()

    @property
    def selection(self): return self.intent.selection
    @property
    def origin(self): return self._origin
    @property
    def root(self): return self._root
    @property
    def phase(self): return self._phase
    @property
    def terminal_receipt(self): return self._terminal

    def _snapshot(self):
        return (id(self.intent), self._phase, self._generation, self._journey_settings,
            tuple(map(id, (self._camp, self._camp_floor, self._camp_monitor, self._camp_progress,self._camp_destination,
                self._origin, self._root, self._probe_plan, self._terminal, self._terminal_camp))),
            self._camp_attribution, self._probe_state, self._root_declaration,
            self._promoted, self._cancelled, self._reason, self._adoptions)

    def _seal(self): self._state = self._snapshot()

    def _assert_intact(self):
        self._intent.check()
        if self.intent is not self._intent or self._snapshot() != self._state:
            raise ValueError('Progression lifecycle or original intent changed')
        if self._cancelled:
            raise ValueError(self._reason or 'Progression was cancelled')
        if self._origin is not None: self._origin.check_identity()
        if self._probe_plan is not None and CampProbePlan.owner_state(self._probe_plan) != self._probe_state:
            raise ValueError('Progression first walking plan changed')

    def _owner(self, e, *, generation=None, journey_settings=None):
        """Pure identity reads, independent of root/camp policy callbacks."""
        self._assert_intact(); i = self.intent; j = i.journey
        expected = self._generation if generation is None else generation
        settings = self._journey_settings if journey_settings is None else journey_settings
        if (e is not i.engine or e.journey is not j
                or getattr(j, 'progression', None) is not self
                or getattr(j, '_progression', None) is not self
                or j.continue_camps is not True or j._continue_camps is not True
                or e.cancel_generation != expected or j.generation != expected
                or j.settings != settings or settings_identity(e.settings)[:4] != i.settings[:4]
                or e.sender is not i.sender or i.sender.ui is not i.ui or e.gate is not i.gate
                or e.live_zone_tracker is not i.tracker or i.tracker.reader is not i.reader
                or i.tracker.closed or e.stopping
                or (e.supervised_epoch, e.route_session_epoch) != i.epochs):
            raise ValueError('Progression lost its original Journey, sender, settings or generation')
        return j

    def check_binding(self, e):
        """Nonrecursive owner binding; does not query UI, clocks or old scopes."""
        j = self._owner(e)
        o = self._origin
        if o is not None:
            if settings_identity(e.settings) != o.current_settings:
                raise ValueError('Observed progression departure settings changed')
            if not self._promoted and (j.destination_id != 'goblin-camp'
                    or j.destination_assets is not o.destination):
                raise ValueError('Goblin origin changed before its explicit crossing handoff')
        return (id(self), id(self.intent), id(o), self._generation,
            self.intent.settings[:4], None if o is None else o.current_settings,
            id(self.intent.sender), id(self.intent.ui), id(self.intent.gate),
            id(self.intent.tracker), id(self.intent.reader), self.intent.epochs)

    def cancel(self, reason):
        """Revoke only intent. The engine still owns input/lease cleanup."""
        with self.intent.lock:
            if self._cancelled: return
            self._cancelled = True; self._reason = str(reason); self._phase = 'cancelled'
            self._seal()

    def adopt_camp_handoff(self, e, token, camp, *, trip=None):
        """Record an actual completed handoff; never change its generation."""
        from .owner_journey_runtime import Arrival
        from .owner_camp_sections import CampWalkingJourney
        from .owner_walking_sections import WalkingJourney
        from .camp_progress import CampProgress

        with self.intent.lock:
            self._assert_intact(); i = self.intent; j = i.journey
            lifecycle = self._state
            if type(camp) is not StationaryCamp or id(token) in self._adoptions:
                raise ValueError('A new actual camp arrival is required')
            if self._phase == 'newbie_request':
                if (type(token) is not Arrival
                        or token.journey is not j or type(token.pending) is not dict
                        or token.pending.get('generation') != self._generation
                        or token.destination_id != 'newbie-hills'
                        or token.tracker is not i.tracker or token.sender is not i.sender
                        or token.gate is not i.gate):
                    raise ValueError('Initial Newbie camp needs its original source Arrival')
                if trip is None:
                    if type(token.runtime) is not OwnerSourceRuntime:
                        raise ValueError('Initial direct source runtime required')
                else:
                    a = getattr(token.runtime, '_section_arrival', None)
                    if (type(trip) is not WalkingJourney
                            or type(token.runtime) not in (CampSourceRuntime, OwnerSourceRuntime)
                            or type(a) is not SectionArrival or a.runtime is not token.runtime
                            or a.receipt is not token.receipt or a.checkpoint is not token.floor_checkpoint
                            or a._claim != [True] or a.budget is not trip.budget or a.budget.valid
                            or trip.journey is not j or trip.pending is not token.pending
                            or trip.generation != self._generation
                            or trip.index != len(trip.sections.guides)-1
                            or type(trip.sections) is not WalkingSections
                            or WalkingJourney._context(trip) != trip._state):
                        raise ValueError('Initial sectioned camp needs its exact final walking arrival')
                    if (type(token.runtime) is OwnerSourceRuntime and
                            (trip.initial_index != trip.index or token.pending.get('source_runtime') is not token.runtime)):
                        raise ValueError('Direct initial section must be the selected final source section')
                r, receipt, floor = token.runtime, token.receipt, token.floor_checkpoint
                observer, hotkey = token.pending['observer'], token.pending['binding']
                destination, settings = token.destination, self._journey_settings
                target, next_phase = 'newbie-hills', 'newbie_camp'
            elif self._phase == 'newbie_camp':
                if (type(token) is not SectionArrival or type(trip) is not CampWalkingJourney
                        or type(token.runtime) is not CampSourceRuntime
                        or trip.journey is not j or trip.camp is not self._camp
                        or trip.generation != self._generation or trip.from_id != 'newbie-hills'
                        or trip.destination_id != 'goblin-camp' or trip.stage != 'finished'
                        or trip.stage != trip._stage or trip.camp.running
                        or type(trip.sections) is not WalkingSections
                        or trip.index != len(trip.sections.guides)-1
                        or token.budget is not trip.budget or token.budget.valid
                        or token._claim != [True] or getattr(token.runtime, '_section_arrival', None) is not token
                        or type(trip.level_advance) is not CampLevelAdvance
                        or trip.camp.last_level_advance is not trip.level_advance
                        or flat_record_state(trip.level_advance) != trip.advance_state
                        or trip.level_advance.generation != self._generation
                        or not 5 <= trip.level_advance.level <= 8
                        or trip.settings[4] != trip.level_advance.level
                        or CampWalkingJourney.context(trip) != trip._state):
                    raise ValueError('Goblin camp needs the actual final Newbie camp-section arrival')
                r, receipt, floor = token.runtime, token.receipt, token.checkpoint
                observer, hotkey = trip.monitor.observer, trip.hotkey
                destination, settings = j.destination_assets, trip.settings
                target, next_phase = 'goblin-camp', 'goblin_camp'
            else:
                raise ValueError('No additional same-zone camp handoff belongs to this progression')
            receipt_state = _receipt_state(receipt)
            if type(floor) is not CampFloorCheckpoint:
                raise ValueError('Progression camp requires an actual ordinary source floor')
            floor._assert_intact()
            generation = self._generation+1
            self._owner(e, generation=generation, journey_settings=settings)
            monitor = j.camp_motion
            if (e.camp_session is not camp or e.autopilot is not camp or not camp.running
                    or camp.generation != generation or camp.level != e.settings.level
                    or j.phase != 'camp' or j.destination_id != target
                    or j.destination_assets is not destination or destination.destination_id != target
                    or j.arrival_floor is not floor or j.location_binding is not hotkey
                    or type(monitor) is not CampInputContinuity or monitor.observer is not observer
                    or monitor.floor is not floor or r.lease.active or i.tracker.lease is not None
                    or floor._reader is not i.reader or i.reader.zone_id != 68
                    or type(camp.progress) is not CampProgress
                    or camp.progress.arrival_destination is None
                    or camp.progress.arrival_destination.get('destination_id') != target
                    or camp.progress.arrival_destination.get('itinerary_sha256') != receipt.itinerary_sha256
                    or receipt.itinerary_sha256 != floor._reference.itinerary_sha256
                    or receipt.real_client_accepted is not False
                    or i.sender.held or i.sender.unfinished):
                raise ValueError('Camp adoption lost its completed receipt, floor or actual new camp')
            CampInputContinuity.check_binding(monitor, monitor.binding)
            progress = camp.progress; attribution = encoded(progress.arrival_destination)
            def adoption_state():
                if type(token) is Arrival:
                    return (id(token.journey),id(token.pending),id(token.runtime),id(token.receipt),
                        id(token.floor_checkpoint),id(token.destination),token.destination_id,
                        token.pending.get('generation'),id(token.pending.get('observer')),
                        id(token.pending.get('binding')),None if trip is None else WalkingJourney._context(trip))
                return (id(token.runtime),id(token.receipt),id(token.checkpoint),id(token.budget),
                    tuple(token._claim),CampWalkingJourney.context(trip),trip.stage,trip.index)
            adoption_pin = adoption_state()
            now = i.clock()
            if self._state is not lifecycle:
                raise ValueError('Camp adoption was already completed during its final callback')
            self._owner(e, generation=generation, journey_settings=settings)
            assert_retained_arrival(r, receipt, floor, now)
            if (receipt_state != _receipt_state(receipt) or e.camp_session is not camp
                    or e.autopilot is not camp or not camp.running or camp.generation != generation
                    or camp.progress is not progress or encoded(progress.arrival_destination) != attribution
                    or adoption_state() != adoption_pin
                    or camp.level != e.settings.level or j.phase != 'camp' or j.destination_id != target
                    or j.destination_assets is not destination or destination.destination_id != target
                    or j.camp_motion is not monitor or monitor.floor is not floor
                    or monitor.observer is not observer or j.arrival_floor is not floor
                    or j.location_binding is not hotkey or r.lease.active or i.tracker.lease is not None
                    or receipt.itinerary_sha256 != floor._reference.itinerary_sha256
                    or camp.progress.arrival_destination.get('itinerary_sha256') != receipt.itinerary_sha256
                    or camp.progress.arrival_destination.get('destination_id') != target
                    or i.sender.held or i.sender.unfinished):
                raise ValueError('Camp changed during final progression adoption')
            CampInputContinuity.check_binding(monitor, monitor.binding)
            self._generation = generation; self._journey_settings = settings
            self._camp, self._camp_floor, self._camp_monitor = camp, floor, monitor
            self._camp_progress = camp.progress
            self._camp_destination = destination
            self._camp_attribution = encoded(camp.progress.arrival_destination)
            self._phase = next_phase; self._adoptions += (id(token),)
            self._seal()
            return camp

    def claim_goblin_origin(self, e, p):
        """Claim one fresh logged level increase after actual Goblin recovery."""
        with self.intent.lock:
            j = self._owner(e); i = self.intent
            lifecycle = self._state
            if self._phase != 'goblin_camp' or self._origin is not None or type(p) is not SimpleNamespace:
                raise ValueError('An unclaimed reached Goblin camp is required')
            camp = self._camp; advance = p.level_advance; height = p.result
            def evidence_state():
                return (flat_record_state(advance), _height_state(height),
                    flat_record_state(p.recovery), p.level_advance_state, p.settings)
            evidence = evidence_state()
            def passive(now):
                self._owner(e)
                if (e.camp_position is not p or p.journey is not j or p.camp is not camp
                        or e.camp_session is not camp or e.autopilot is not camp or not camp.running
                        or j.phase != 'camp' or j.destination_id != 'goblin-camp'
                        or j.destination_assets is not self._camp_destination
                        or camp.progress is not self._camp_progress
                        or encoded(camp.progress.arrival_destination) != self._camp_attribution
                        or p.floor is not self._camp_floor or j.arrival_floor is not p.floor
                        or p.monitor is not self._camp_monitor or j.camp_motion is not p.monitor
                        or type(p.floor) is not CampFloorCheckpoint or type(p.monitor) is not CampInputContinuity
                        or not p.floor.valid or not p.monitor.valid or p.monitor.closed
                        or p.hotkey is not j.location_binding or type(p.hotkey) is not OwnerLocationHotkey
                        or p.sender is not i.sender or p.ui is not i.ui or p.gate is not i.gate
                        or p.tracker is not i.tracker or p.reader is not i.reader
                        or type(p.lease) is not ZoneReaderLease or not p.lease.active
                        or i.tracker.lease is not p.lease or p.lease.reader is not i.reader
                        or p.reader.zone_id != 68 or p.cancelled or e.cancelled
                        or p.generation != self._generation or camp.generation != self._generation
                        or p.settings != settings_identity(e.settings)
                        or p.window != (i.window.window_id, i.window.pid, i.window.start_ticks)
                        or e.active or e.target_ready or e.preparing or getattr(e, '_camp_command', None) is not None
                        or i.sender.held or i.sender.unfinished or i.sender.dismissed
                        or getattr(i.sender, '_eql_route_operation', None) is not None
                        or type(advance) is not CampLevelAdvance or camp.last_level_advance is not advance
                        or advance is j.last_considered_level_advance
                        or flat_record_state(advance) != p.level_advance_state
                        or type(advance.previous_level) is not int or type(advance.level) is not int
                        or not j.settings[4] <= advance.previous_level < advance.level
                        or advance.level not in (9, 10) or advance.level != camp.level
                        or advance.level != p.settings[4] or advance.generation != self._generation
                        or type(advance.camp_log_seq) is not int or advance.camp_log_seq < 1
                        or camp.level_source != 'client_log' or camp.pending_level is not None
                        or camp.preparation_due or camp.kills < 1
                        or camp.phase not in ('position_check', 'probe_measurement')
                        or type(p.recovery) is not CampRecovery or camp.recovery is not p.recovery
                        or p.recovery.phase != 'recovered' or not finite(p.released_at)
                        or p.released_at != p.recovery.last_stand_completed_at
                        or type(p.probe_log_veto) is not SceneLogVeto
                        or p.probe_log_veto is not p._probe_log_veto
                        or p.probe_log_veto.cancel_generation != self._generation
                        or type(height) is not CampStoppedHeight or p.result is not height
                        or height.checkpoint is not p.floor
                        or type(height.first) is not RawLocationFix or type(height.second) is not RawLocationFix
                        or height.first.log_line_seq <= p.baseline
                        or height.second.log_line_seq <= height.first.log_line_seq
                        or p.reader.latest is not height.second
                        or p.reader.log_line_seq != height.second.log_line_seq
                        or height.input_authorized is not False or height.real_client_accepted is not False
                        or sha256(height.payload).hexdigest() != height.sha256
                        or not finite(now) or not height.observed_at <= now <= height.expires_at
                        or not 0 <= now-height.second.received_monotonic <= .5):
                    raise ValueError('Fresh actual Goblin level 9/10 recovery and height proof required')
            # Queue and clock may be callback-bearing. Publish only after pure checks.
            if not e.jobs.empty(): raise ValueError('Queued work prevents progression departure')
            now = i.clock(); passive(now)
            if self._state is not lifecycle or evidence_state() != evidence:
                raise ValueError('Goblin origin changed during its capture callback')
            p.floor._assert_intact(); CampInputContinuity.check_binding(p.monitor, p.monitor.binding)
            origin = CampProgressionOrigin(self,p,j,camp,advance,p.recovery,p.floor,p.monitor,height,
                p.lease,p.reader,p.hotkey,p.probe_log_veto,j.destination_assets,j.settings,p.settings,
                self._generation,i.epochs,zone_binding(p.reader),p.window,now)
            passive(now)
            self._origin = origin; self._phase = 'origin_claimed'; self._seal()
            return origin

    def bind_root(self, origin, root):
        """Bind accounting before the first probe; do not call owner bindings."""
        with self.intent.lock:
            self._owner(self.intent.engine)
            if (self._phase != 'origin_claimed' or origin is not self._origin or self._root is not None
                    or type(root) is not ZoneItineraryBudget or root.clock is not self.intent.clock
                    or root.lock is not self.intent.lock or root.stage.phase != 'walking'
                    or root.stage.kind != 'crossing' or root.stage.leg_index != 0
                    or root._initial_measurement is not None
                    or root._balance != (0, 0., 0.) or root._reservations
                    or root.declaration.record_id != self.selection.itinerary_id
                    or tuple(leg.destination_id for leg in root.declaration.legs) !=
                        ('butcher-gfay-crossing', 'gfay-butcher-crushbone-crossing')
                    or root.declaration.terminal_camp is None
                    or root.declaration.terminal_camp.destination_id != 'slave-mines'):
                raise ValueError('One initial finite Goblin crossing root required')
            root._assert_intact()
            p = origin.pending; plan = p.probe_plan
            if (p.runtime is not None or p.route_runtime is not None
                    or type(plan) is not CampProbePlan or plan.destination_id != root.leg.destination_id
                    or plan.state() != p.probe_plan_state or type(plan.route_sections) is not WalkingSections
                    or len(plan.route_sections.guides) != 2 or plan.route_sections.original is not plan.route_guide):
                raise ValueError('Actual first crossing probe plan and two-section partition required')
            plan_state = CampProbePlan.owner_state(plan)
            self._owner(self.intent.engine); root._assert_intact()
            if (self._phase != 'origin_claimed' or self._origin is not origin or self._root is not None
                    or origin.pending is not p or p.probe_plan is not plan
                    or p.runtime is not None or p.route_runtime is not None
                    or plan_state != CampProbePlan.owner_state(plan)
                    or root.stage.phase != 'walking' or root.stage.leg_index != 0
                    or root._balance != (0, 0., 0.) or root._reservations):
                raise ValueError('Progression changed while binding the first walking plan')
            self._root = root; self._root_declaration = _declaration_state(root.declaration)
            self._probe_plan = plan; self._probe_state = plan_state
            self._phase = 'navigating'; self._seal()

    def commit_first_crossing(self, e, trip, arrival):
        """Record the explicit historical-settings promotion, without rearming."""
        from .owner_camp_sections import CampWalkingJourney
        with self.intent.lock:
            self._assert_intact(); o = self._origin; root = self._root
            lifecycle = self._state
            if o is None or root is None: raise ValueError('Claimed progression root required')
            def passive():
                j = self._owner(e, journey_settings=o.current_settings)
                root._assert_intact()
                if (self._phase != 'navigating' or self._promoted
                    or type(trip) is not CampWalkingJourney or trip.journey is not j
                    or trip.camp is not o.camp or trip.pending is not o.pending
                    or trip.generation != self._generation or trip.plan is not self._probe_plan
                    or trip.destination_id != root.declaration.legs[0].destination_id
                    or trip.stage != 'finished' or trip._stage != 'finished'
                    or trip.index != len(trip.sections.guides)-1 or trip.camp.running
                    or type(arrival) is not SectionArrival or arrival.budget is not trip.budget
                    or arrival.budget.parent_budget is not root or arrival.budget.valid
                    or arrival._claim != [True] or arrival.runtime._section_arrival is not arrival
                    or arrival.runtime.lease.active or self.intent.tracker.lease is not None
                    or j.phase != 'source_crossing_handoff' or j.destination_id != trip.destination_id
                    or root.stage.phase != 'walking' or root.stage.leg_index != 0):
                    raise ValueError('Actual final Goblin walking section is required before crossing')
            passive()
            state = _receipt_state(arrival.receipt); now = self.intent.clock()
            passive()
            if self._state is not lifecycle:
                raise ValueError('First crossing was already committed during its final callback')
            assert_retained_arrival(arrival.runtime,arrival.receipt,arrival.checkpoint,now)
            if state != _receipt_state(arrival.receipt): raise ValueError('Crossing arrival changed')
            self._journey_settings = o.current_settings; self._promoted = True; self._seal()

    def consume_terminal(self, token):
        """Spend this routing intent on the exact completed terminal handoff."""
        from .owner_itinerary_camp_arrival import ItineraryCampArrival
        with self.intent.lock:
            lifecycle = self._state
            def passive():
                e = self.intent.engine; j = self._owner(e)
                if (self._phase != 'navigating' or not self._promoted or self._terminal is not None
                    or type(token) is not ItineraryCampArrival or token.root is not self._root
                    or token.journey is not j or token.generation != self._generation
                    or token.progression_origin is not self._origin
                    or e.camp_session is not None or e.autopilot is not None
                    or j.camp_motion is not token.monitor or j.arrival_floor is not token.arrival.checkpoint
                    or token.monitor.floor is not None or not token.monitor.valid or token.monitor.closed):
                    raise ValueError('One exact unstarted terminal transfer may consume this progression')
                _terminal_proof(self,token)
                CampInputContinuity.check_binding(token.monitor, token.monitor.binding)
            passive()
            now = self.intent.clock(); passive()
            if self._state is not lifecycle:
                raise ValueError('Terminal progression was already consumed during its final callback')
            if not finite(now) or now > min(token.expires_at,self._root.expires_at):
                raise ValueError('Terminal progression transfer expired')
            assert_retained_arrival(token.arrival.runtime,token.arrival.receipt,token.arrival.checkpoint,now)
            receipt = TerminalProgressionReceipt(self,self.intent,self._origin,self._root,token,
                                                self._generation,now)
            self._terminal = receipt; self._phase = 'consumed'; self._seal()
            return receipt

    def record_terminal_camp(self, e, token, camp):
        with self.intent.lock:
            receipt = terminal_authority(self.intent.journey,self._root,token)
            if self._phase != 'consumed' or self._terminal_camp is not None:
                raise ValueError('Terminal camp may be recorded once')
            j = self._owner(e,generation=receipt.generation+1)
            _terminal_camp_proof(self,e,token,camp)
            monitor = j.camp_motion
            CampInputContinuity.check_binding(monitor,monitor.binding)
            self._owner(e,generation=receipt.generation+1)
            _terminal_camp_proof(self,e,token,camp)
            self._generation = receipt.generation+1; self._terminal_camp = camp
            self._phase = 'terminal_camp'; self._seal()


def capture_progression_intent(e, j, selection, request_bytes, *, clock):
    """Attach explicit initial intent before navigation; configured level is a gate only."""
    from .owner_journey_runtime import Journey
    if type(selection) is not CampProgressionSelection: raise ValueError('Typed progression selection required')
    selection.check()
    if type(request_bytes) is not bytes: raise ValueError('Canonical original request bytes required')
    request = json.loads(request_bytes)
    if (type(request) is not dict or encoded(request) != request_bytes
            or set(request) != {'progression_id','open_flat_clear','owner_supervised_continuation'}
            or request['progression_id'] != selection.profile_id
            or request['open_flat_clear'] is not True or request['owner_supervised_continuation'] is not True):
        raise ValueError('Explicit finite progression request required')
    with e.g0_stop_lock:
        settings = settings_identity(e.settings); generation = e.cancel_generation
        sender, gate, tracker = e.sender,e.gate,e.live_zone_tracker
        if type(j) is not Journey or type(tracker) is not LiveZoneTracker:
            raise ValueError('Actual original Journey and live tracker required')
        reader = tracker.reader; epochs = (e.supervised_epoch,e.route_session_epoch)
        ui = sender.ui
        def passive():
            if (e.journey is not j or e.cancel_generation != generation or j.generation != generation
                    or settings_identity(e.settings) != settings or j.settings != settings
                    or type(settings[4]) is not int or not 1 <= settings[4] <= 4
                    or j.destination_id != selection.initial_destination_id
                    or j.continue_camps is not True or j._continue_camps is not True
                    or getattr(j,'progression',None) is not None or getattr(j,'_progression',None) is not None
                    or e.sender is not sender or sender.ui is not ui or e.gate is not gate
                    or e.live_zone_tracker is not tracker or tracker.reader is not reader
                    or type(reader) is not LocationLogReader or tracker.closed
                    or e.stopping or e.camp_session is not None
                    or (e.supervised_epoch,e.route_session_epoch) != epochs):
                raise ValueError('Original initial progression owner changed')
        passive(); fd = ui.fileno(); fd_identity = _fd_identity(fd)
        window = focused_game_identity(gate); now = clock(); passive()
        if not finite(now): raise ValueError('Finite progression capture clock required')
        intent = CampProgressionIntent(e,j,selection,request_bytes,sender,ui,gate,tracker,reader,
            settings,generation,epochs,window,fd,fd_identity,clock,e.g0_stop_lock)
        c = CampProgression(intent); passive()
        j.progression = j._progression = c
        return c


def continuation_available(j):
    """Passive finite-intent availability; this never grants movement input."""
    from .owner_journey_runtime import Journey
    if type(j) is not Journey: return False
    c = getattr(j,'progression',None)
    if type(c) is not CampProgression or getattr(j,'_progression',None) is not c: return False
    try:
        c._owner(c.intent.engine)
        if c.phase == 'newbie_request': return True
        return (c.phase in ('newbie_camp','goblin_camp') and j.phase == 'camp'
            and c.intent.engine.camp_session is c._camp and c._camp.running
            and j.destination_assets is c._camp_destination
            and j.destination_id == ('newbie-hills' if c.phase == 'newbie_camp' else 'goblin-camp')
            and j.arrival_floor is c._camp_floor and j.camp_motion is c._camp_monitor)
    except (ValueError,AttributeError,TypeError): return False


def active_origin_authority(j, root):
    from .owner_journey_runtime import Journey
    if type(j) is not Journey: raise ValueError('Actual progression Journey required')
    c = getattr(j,'progression',None)
    if type(c) is not CampProgression: raise ValueError('Typed progression intent required')
    c.check_binding(c.intent.engine)
    if (c.phase != 'navigating' or not c._promoted or c.root is not root
            or c.origin is None or c._terminal is not None):
        raise ValueError('Active finite progression origin required')
    root._assert_intact()
    if _declaration_state(root.declaration) != c._root_declaration:
        raise ValueError('Progression root declaration changed')
    return c.origin


def _terminal_proof(c, token):
    from .owner_itinerary_camp_arrival import ItineraryCampArrival
    from .zone_itinerary_runtime import ZoneItineraryRuntime
    root = c.root; j = c.intent.journey
    if type(token) is not ItineraryCampArrival: raise ValueError('Exact terminal token required')
    token.check_identity(); root._assert_intact()
    a = token.arrival; run = token.run
    if (type(run) is not ZoneItineraryRuntime or run.root is not root or token.root is not root
            or not run.closed or run.phase != 'terminal_transferred'
            or run.terminal_transfer is not token or run._camp_arrival_token is not token
            or token.journey is not j or token.generation != c.origin.generation
            or token.progression_origin is not c.origin
            or _declaration_state(root.declaration) != c._root_declaration
            or root.stage.phase != 'complete' or root.stage.kind != 'terminal_camp'
            or root.stage.leg_index != len(root.declaration.legs)
            or token.terminal is not root.declaration.terminal_camp
            or token.destination.destination_id != 'slave-mines'
            or type(a) is not SectionArrival or a._claim != [True]
            or a.budget.valid or a.budget.parent_budget is not root
            or a.runtime._section_arrival is not a or a.runtime.phase != 'complete'
            or a.runtime.completed_arrival is not a.receipt
            or a.receipt.itinerary_sha256 != a.checkpoint._reference.itinerary_sha256
            or token.lease.active or c.intent.tracker.lease is not None
            or token.monitor.observer is not c.origin.monitor.observer
            or token.sender is not c.intent.sender or token.ui is not c.intent.ui
            or token.tracker is not c.intent.tracker or token.reader is not c.intent.reader):
        raise ValueError('Terminal transfer differs from this finite progression root')


def _terminal_camp_proof(c, e, token, camp):
    j = c.intent.journey
    if (type(camp) is not StationaryCamp or e.camp_session is not camp or e.autopilot is not camp
            or not camp.running or camp.generation != token.generation+1
            or settings_identity(e.settings) != token.settings or camp.level != token.settings[4]
            or e.cancel_generation != camp.generation or j.generation != camp.generation
            or j.phase != 'camp' or j.destination_id != 'slave-mines'
            or j.destination_assets is not token.destination or j.arrival_floor is not token.arrival.checkpoint
            or type(j.camp_motion) is not CampInputContinuity
            or not j.camp_motion.valid or j.camp_motion.closed
            or j.camp_motion.observer is not token.monitor.observer
            or j.camp_motion.floor is not token.arrival.checkpoint
            or camp.progress.arrival_destination is None
            or camp.progress.arrival_destination.get('destination_id') != 'slave-mines'
            or camp.progress.arrival_destination.get('itinerary_sha256') != token.arrival.receipt.itinerary_sha256):
        raise ValueError('Exact successful terminal stationary camp required')


def terminal_authority(j, root, token):
    """Passive consumed-origin proof, including the one camp-start generation."""
    from .owner_journey_runtime import Journey
    if type(j) is not Journey: raise ValueError('Actual progression Journey required')
    c = getattr(j,'progression',None)
    if type(c) is not CampProgression: raise ValueError('Typed progression intent required')
    c._assert_intact(); receipt = c.terminal_receipt
    if (c.phase not in ('consumed','terminal_camp') or type(receipt) is not TerminalProgressionReceipt
            or receipt.root is not root or receipt.token is not token or receipt.origin is not c.origin):
        raise ValueError('Exactly consumed terminal progression required')
    receipt.check_identity(); _terminal_proof(c,token)
    e = c.intent.engine; generation = e.cancel_generation
    if settings_identity(e.settings) != token.settings:
        raise ValueError('Terminal handoff lost its exact observed settings')
    if generation not in (receipt.generation,receipt.generation+1):
        raise ValueError('Terminal camp startup is the only allowed generation increment')
    c._owner(e,generation=generation)
    if generation == receipt.generation:
        if e.camp_session is not None or j.camp_motion is not token.monitor:
            raise ValueError('Unstarted terminal transfer changed')
    elif e.camp_session is None:
        # The existing camp starter checks its arrival again after its one
        # intentional stop increment and before publishing the new camp.
        if (c.phase != 'consumed' or e.autopilot is not None or token._claim != [True]
                or j.phase != 'handoff' or j.camp_motion is not token.monitor
                or j.arrival_floor is not token.arrival.checkpoint
                or j.destination_assets is not token.destination):
            raise ValueError('Only the claimed terminal camp startup may cross the generation gap')
    elif (type(e.camp_session) is not StationaryCamp or e.autopilot is not e.camp_session
            or e.camp_session.generation != generation or not e.camp_session.running):
        raise ValueError('Terminal generation increment requires the actual new camp')
    return receipt
