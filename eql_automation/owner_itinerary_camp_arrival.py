"""One actual terminal itinerary arrival into the existing stationary camp.

The runtime captures this token while its source/root are still current, then
retires navigation without cancelling the completed source or closing input.
The owner detaches that runtime before continuing here. Historical arrival
checks never call a retired runtime, policy, budget or owner binding.
"""
from dataclasses import dataclass, field
from hashlib import sha256
import json

from .camp_floor_checkpoint import CampFloorCheckpoint
from .camp_motion_continuity import CampInputContinuity
from .camp_session import NpcCandidate
from .camp_source_runtime import CampSourceRuntime
from .flat_record import flat_record_state, _value
from .g2_safety_provider import focused_game_identity
from .ground_binding import finite
from .native_region_policy import encoded
from .owner_camp_arrival import CampDestination
from .owner_navigation_preflight import settings_identity
from .owner_route_trial import zone_binding
from .route_step_sender import _fd_identity
from .scene_log_veto import SceneLogVeto
from .section_continuation import SectionArrival
from .source_arrival import assert_retained_arrival, arrival_reference, arrival_itinerary
from .source_destinations import destination_spec
from .source_walk_driver import SourceWalkFinished
from .zone_itinerary_budget import ZoneItineraryTerminalCamp, _declaration_state


def _receipt_state(receipt):
    if type(receipt) is not SourceWalkFinished:
        raise ValueError('Exact ordinary terminal completion receipt required')
    # The checkpoint separately pins the reference's full observation state.
    # Pin every receipt field too: frozen dataclasses are not mutation proof.
    return (type(receipt), id(receipt), _value(receipt.real_client_accepted), tuple((name,
        ('reference', id(value)) if name == 'reference' else _value(value))
        for name, value in vars(receipt).items()))


@dataclass(frozen=True)
class ItineraryCampArrival:
    run: object
    journey: object
    arrival: SectionArrival
    destination: CampDestination
    candidates: tuple
    monitor: CampInputContinuity
    sender: object
    ui: object
    gate: object
    tracker: object
    reader: object
    hotkey: object
    veto: SceneLogVeto
    lease: object
    root: object
    terminal: ZoneItineraryTerminalCamp
    generation: int
    settings: tuple
    zone: tuple
    window: object
    fd: int
    fd_identity: tuple
    clock: object
    expires_at: float
    arrival_epoch: int
    _claim: list = field(default_factory=lambda: [False], repr=False, compare=False)
    _state: tuple = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        object.__setattr__(self, '_state', self.state())

    def state(self):
        objects = (self.run, self.journey, self.arrival, self.destination,
            self.candidates, self.monitor, self.sender, self.ui, self.gate,
            self.tracker, self.reader, self.hotkey, self.veto, self.lease,
            self.root, self.terminal, self.clock, self._claim)
        a = self.arrival
        return (tuple(map(id, objects)), self.generation, self.settings, self.zone,
            flat_record_state(self.window), self.fd, self.fd_identity, self.expires_at, self.arrival_epoch,
            flat_record_state(self.destination), tuple(flat_record_state(c) for c in self.candidates),
            flat_record_state(self.terminal), _declaration_state(self.root.declaration),
            self.root.started, self.root.expires_at, self.root._balance,
            id(self.veto.tail), self.veto.tail.path, self.veto.tail.identity,
            self.veto.tail.epoch, id(self.veto.clock), self.veto.cancel_generation,
            id(a.runtime), id(a.receipt), id(a.checkpoint), id(a.budget), id(a._claim),
            _receipt_state(a.receipt), flat_record_state(a.budget.declaration),
            a.motion_basis, a.guide_sha256)

    def check_identity(self):
        if self.state() != self._state:
            raise ValueError('Terminal camp token or completed itinerary provenance changed')


def capture_itinerary_camp_arrival(e, run, arrival, clock, *, candidates):
    """Publish input cleanup ownership before the runtime retires navigation.

    On return the caller must immediately mark its physical observer ownership
    transferred, without an intervening callback. It then retires its child,
    advances walking -> arrival -> complete, sets terminal_transfer to this
    token, and closes itself as terminal_transferred. The owner removes its
    itinerary slots before calling continue_itinerary_camp_arrival().
    """
    from .zone_itinerary_runtime import ZoneItineraryRuntime

    if (type(run) is not ZoneItineraryRuntime or type(arrival) is not SectionArrival
            or type(arrival.runtime) is not CampSourceRuntime
            or type(arrival.checkpoint) is not CampFloorCheckpoint
            or type(candidates) is not tuple or not candidates
            or any(type(c) is not NpcCandidate for c in candidates)
            or clock is not run.clock or run.engine is not e):
        raise ValueError('Actual terminal source arrival and observed candidate tuple required')
    with run.lock:
        run._scene()
        j = run.journey; a = arrival; r = a.runtime; terminal = run.root.leg
        if (type(terminal) is not ZoneItineraryTerminalCamp
                or run.root.declaration.terminal_camp is not terminal
                or run.phase != 'terminal_ready' or run.closed or run.busy
                or run.root.stage.kind != 'terminal_camp' or run.root.stage.phase != 'walking'
                or run.root.stage.leg_index != len(run.root.declaration.legs)
                or run.terminal_arrival is not a or a.budget is not run.child_budget
                or a._claim != [False] or getattr(r, '_section_arrival', None) is not a
                or r.lease is not run.lease or run.tracker.lease is not run.lease
                or r.sender is not run.sender or r.owner_input is not run.owner_input
                or r.reader is not run.reader or r.ui is not run.ui
                or r.clock is not clock or r.generation != run.generation
                or r.policy.log_veto is not run.veto
                or getattr(run, '_camp_arrival_token', None) is not None
                or j.camp_motion is not None or e.camp_session is not None
                or j.continue_camps is not False or j._continue_camps is not False
                or type(run.veto) is not SceneLogVeto):
            raise ValueError('Unclaimed final terminal walking scope required')
        spec = destination_spec(terminal.destination_id)
        if (spec.arrival_mode != 'camp' or spec.zone_id != run.reader.zone_id
                or run.assets.destination_id != spec.identifier
                or j.destination_assets is not run.assets):
            raise ValueError('Terminal camp differs from the reached source destination')
        a.budget.check(); r.check_current(); r.policy._check()
        run.assets.check(); a.checkpoint.check()
        if (type(a.receipt) is not SourceWalkFinished
                or a.receipt.real_client_accepted is not False
                or a.receipt.itinerary_sha256 != a.checkpoint._reference.itinerary_sha256):
            raise ValueError('Terminal receipt differs from its reached itinerary')
        destination = CampDestination(spec.identifier, encoded(dict(
            destination_id=spec.identifier, label=spec.label,
            guide_sha256=sha256(encoded(run.assets.guide.record())).hexdigest(),
            guide_file_sha256=terminal.guide_sha256,
            itinerary_id=run.root.declaration.record_id,
            terminal_camp=True, real_client_accepted=False)))
        settings = settings_identity(e.settings); zone = zone_binding(run.reader)
        binding = (e, run, j, run.sender, run.tracker, run.reader,
            run.generation, settings, zone, run.window)
        monitor = CampInputContinuity(run.owner_input, topology=run.topology,
            basis=a.motion_basis, binding=binding, clock=clock, floor=None)
        token = ItineraryCampArrival(run, j, a, destination, candidates, monitor,
            run.sender, run.ui, run.gate, run.tracker, run.reader, run.hotkey,
            run.veto, run.lease, run.root, terminal, run.generation, settings, zone,
            run.window, run.fd, run.fd_identity, clock, run.expires_at, run.root.stage.epoch)
        monitor.check(binding)
        run._scene(); token.check_identity()
        assert_retained_arrival(r, a.receipt, a.checkpoint, clock())
        if (e.journey is not j or e.cancel_generation != token.generation
                or j.settings != settings or settings_identity(e.settings) != settings
                or j.camp_motion is not None or run.terminal_arrival is not a
                or a._claim != [False] or run.closed or run.phase != 'terminal_ready'
                or run.root.stage.kind != 'terminal_camp' or run.root.stage.phase != 'walking'
                or run.root.stage.epoch != token.arrival_epoch):
            raise ValueError('Terminal owner changed before input transfer publication')
        # No callback follows publication. Journey stop now owns physical input
        # cleanup, including failures while the runtime releases its old scope.
        run._camp_arrival_token = token
        j.camp_motion = monitor
        j.arrival_floor = a.checkpoint
        return token


def _released_identity(e, t, *, new_camp=None, observations=None):
    """Check released ownership without reviving retired navigation callbacks.

    Returning the current descriptor/navigation observations permits a final
    focus read followed by these same passive identity guards, with no later
    UI/navigation callback able to invalidate that window observation.
    """
    t.check_identity()
    r = t.run; j = t.journey; a = t.arrival
    if observations is None:
        observations = (t.ui.fileno(), e._navigation_busy(), e.jobs.empty())
    descriptor, navigation_busy, queue_empty = observations
    t.root._assert_intact()
    if (e is not r.engine or e.journey is not j
            or e.zone_itinerary_run is not None or e.zone_itinerary_owner is not None
            or r.phase != 'terminal_transferred' or not r.closed or r.busy
            or r.terminal_transfer is not t or r._camp_arrival_token is not t
            or r.terminal_arrival is not a or not r._observer_transferred
            or r.owner_input is not t.monitor.observer or r.veto is not t.veto
            or r.sender is not t.sender or r.ui is not t.ui or r.root is not t.root
            or r.journey is not j or r.lease is not t.lease
            or t.root.stage.kind != 'terminal_camp' or t.root.stage.phase != 'complete'
            or t.root.stage.leg_index != len(t.root.declaration.legs)
            or t.root.stage.epoch != t.arrival_epoch+2 or t.root.leg is not t.terminal
            or a._claim != [True] or a.budget.valid
            or getattr(a.runtime, '_section_arrival', None) is not a
            or a.runtime.lease is not t.lease or t.lease.active
            or e.cancel_generation != j.generation
            or j.generation not in (t.generation, t.generation+1)
            or j.settings != t.settings or settings_identity(e.settings) != t.settings
            or j.continue_camps is not False or j._continue_camps is not False
            or e.camp_session is not new_camp or e.autopilot is not new_camp
            or new_camp is not None and j.generation != t.generation+1
            or navigation_busy or not queue_empty
            or e.stopping or e.active or e.target_ready or e.preparing
            or e.sender is not t.sender or t.sender.ui is not t.ui or e.gate is not t.gate
            or descriptor != t.fd or _fd_identity(t.fd) != t.fd_identity
            or t.sender.held or t.sender.unfinished or t.sender.dismissed
            or getattr(t.sender, '_eql_route_operation', None) is not None
            or e.live_zone_tracker is not t.tracker or t.tracker.reader is not t.reader
            or t.tracker.lease is not None or zone_binding(t.reader) != t.zone
            or t.veto.cancel_generation != t.generation):
        raise ValueError('Terminal camp lost its released itinerary owner or source provenance')
    t.check_identity()
    return observations


def check_itinerary_camp_handoff(e, token, clock, *, new_camp=None):
    if type(token) is not ItineraryCampArrival or clock is not token.clock:
        raise ValueError('Exact terminal camp token and original clock required')
    t = token; j = t.journey; a = t.arrival; m = t.monitor
    _released_identity(e, t, new_camp=new_camp)
    t.tracker.poll(); a.checkpoint.check(); m.check_binding(m.binding)
    veto = t.veto.poll()
    sample = m.observer.sample()
    m.check_binding(m.binding)
    observations = _released_identity(e, t, new_camp=new_camp)
    # Read focus after the descriptor/input providers, then charge its elapsed
    # time against the unchanged observation and trip deadlines. The final
    # clock may deliver a stop, so only passive owner guards follow it.
    window = focused_game_identity(e.gate)
    now = clock()
    _released_identity(e, t, new_camp=new_camp, observations=observations)
    assert_retained_arrival(a.runtime, a.receipt, a.checkpoint, now)
    if (t._claim != [True] or j.phase != 'handoff'
            or j.destination_id != t.destination.destination_id
            or j.destination_assets is not t.destination or j.candidates is not t.candidates
            or j.arrival_floor is not a.checkpoint or j.camp_motion is not m
            or j.location_binding is not t.hotkey or window != t.window
            or not finite(now) or now > t.expires_at
            or not sample.clear_at(now) or sample.topology_generation != m.topology
            or m.last_observed_at is not None and sample.started_at < m.last_observed_at
            or not veto.continuity_available or veto.reason is not None):
        raise ValueError('Terminal camp lost its fresh receipt, input or strict log continuity')
    m.last_observed_at = sample.finished_at; m.samples += 1


def continue_itinerary_camp_arrival(e, token, clock):
    """Consume the released terminal token once; start no movement or targets."""
    if type(token) is not ItineraryCampArrival or clock is not token.clock:
        raise ValueError('Exact terminal camp token and original clock required')
    t = token; j = t.journey; successor = None
    with e.g0_stop_lock:
        if token._claim != [False]:
            raise ValueError('Terminal camp handoff was already consumed')
        token._claim[0] = True
        try:
            _released_identity(e, t)
            if j.camp_motion is not t.monitor or j.arrival_floor is not t.arrival.checkpoint:
                raise ValueError('Terminal provisional input ownership changed')
            spec = destination_spec(t.destination.destination_id)
            j.phase = 'handoff'; j.destination_assets = t.destination
            j.destination_id = spec.identifier; j.candidates = t.candidates
            j.location_binding = t.hotkey
            check = lambda: check_itinerary_camp_handoff(e, t, clock)
            check(); e.zone = spec.zone
            started = e.start_stationary_camp(arrival_check=check)
            if e.journey is not j:
                return dict(camp_started=False, reason='Owner changed terminal camp handoff')
            if not started or e.camp_session is None:
                e.stop_action('Terminal destination reached; fresh camp did not start')
                return dict(camp_started=False)
            camp = e.camp_session
            check_itinerary_camp_handoff(e, t, clock, new_camp=camp)
            binding = e._camp_motion_binding()
            successor = CampInputContinuity(t.monitor.observer, topology=t.monitor.topology,
                basis=t.arrival.motion_basis, binding=binding, clock=clock, floor=t.arrival.checkpoint)
            successor.last_observed_at = t.monitor.last_observed_at
            successor.check(binding)
            check_itinerary_camp_handoff(e, t, clock, new_camp=camp)
            # That final handoff check sampled this same physical observer.
            successor.last_observed_at = t.monitor.last_observed_at
            t.monitor.transfer_to(successor)
            if (e.journey is not j or e.camp_session is not camp or j.camp_motion is not t.monitor
                    or e.cancel_generation != j.generation or j.generation != t.generation+1):
                raise ValueError('Owner changed terminal camp observer transfer')
            j.camp_motion = successor; j.phase = 'camp'
            j.height_check_done = False; j.last_considered_level_advance = None
            progress = camp.progress
            observations = _released_identity(e, t, new_camp=camp)
            if not e._camp_current() or e.journey is not j:
                raise ValueError('Terminal camp input continuity changed')
            now = clock()
            # Camp validation invokes live providers. Recheck the exact token,
            # completed root and reached floor afterward without reviving any
            # retired scope or making another UI/provider call.
            _released_identity(e, t, new_camp=camp, observations=observations)
            successor.check_binding(binding)
            assert_retained_arrival(t.arrival.runtime, t.arrival.receipt, t.arrival.checkpoint, now)
            if (now > t.expires_at or j.phase != 'camp' or j.camp_motion is not successor
                    or j.arrival_floor is not t.arrival.checkpoint
                    or j.destination_id != spec.identifier or j.destination_assets is not t.destination
                    or j.candidates is not t.candidates or j.location_binding is not t.hotkey
                    or e.zone != spec.zone or camp.progress is not progress):
                raise ValueError('Terminal camp attribution changed during final validation')
            receipt = t.arrival.receipt
            progress.bind_arrival(destination_id=spec.identifier, name=spec.label, zone=spec.zone,
                itinerary_sha256=arrival_itinerary(receipt),
                stopped_log_seq=arrival_reference(receipt).raw_fix.log_line_seq)
            result = dict(phase='camp', destination_id=spec.identifier,
                destination=json.loads(t.destination.source_evidence), camp_started=True,
                itinerary_sha256=arrival_itinerary(receipt),
                stopped_log_seq=arrival_reference(receipt).raw_fix.log_line_seq,
                fresh_preparation_due=camp.preparation_due, budget=t.root.snapshot(),
                safe_camp_verified=False, real_client_accepted=False,
                camp_input_continuity=successor.snapshot(include_basis=True))
            e.journey_last_result = result; e.trace('journey_itinerary_camp_handoff', **result)
            if e.journey is not j or e.camp_session is not camp or e.cancel_generation != j.generation:
                return dict(result, camp_started=False, reason='Owner changed completed terminal handoff')
            return result
        except BaseException as error:
            if e.journey is j:
                e.stop_action(str(error))
            if successor is not None and successor is not getattr(j, 'camp_motion', None):
                successor.invalidate(str(error))
            raise
