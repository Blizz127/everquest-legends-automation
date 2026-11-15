"""Actual owner camp/floor/lease/budgets with synthetic terminal scope shells.

The source receipt and runtime shells isolate the ownership handoff; they do
not claim route execution. Actual crossing/bootstrap/source execution is tested
separately in test_terminal_itinerary_runtime. No game/device input is used.
"""
from hashlib import sha256
from types import SimpleNamespace

import pytest

from eql_automation.camp_session import NpcCandidate
from eql_automation.camp_source_runtime import CampSourceRuntime
from eql_automation.g2_safety_provider import GameWindowIdentity, focused_game_identity
from eql_automation.journey_input_budget import JourneyBudgetDeclaration, JourneyInputBudget
from eql_automation.location_hotkey import OwnerLocationHotkey
from eql_automation.native_region_policy import encoded
from eql_automation.owner_input_observer import OwnerInputObservation
from eql_automation.owner_itinerary_camp_arrival import (
    capture_itinerary_camp_arrival, continue_itinerary_camp_arrival,
)
from eql_automation.owner_journey_runtime import Journey
from eql_automation.owner_navigation_preflight import settings_identity
from eql_automation.owner_source_assets import SourceDestinationAssets
from eql_automation.owner_zone_tracker import ZoneReaderLease
from eql_automation.route_step_sender import _fd_identity
from eql_automation.scene_log_veto import SceneLogVeto
from eql_automation.section_continuation import SectionArrival
from eql_automation.source_destinations import destination_spec
from eql_automation.source_itinerary import SourceItineraryGuide, SourceWalkHint
from eql_automation.source_walk_driver import SourceWalkFinished
from eql_automation.zone_itinerary_budget import (
    ZoneItineraryBudget, ZoneItineraryDeclaration, ZoneItineraryLeg, load_terminal_camp,
)
from eql_automation.zone_itinerary_runtime import ZoneItineraryRuntime
from test_camp_floor_checkpoint import checkpoint
from test_source_motion import f
from test_route_floor_commit import legacy
from test_motion_collection import retained
from test_owner_journey_runtime import h


@pytest.fixture
def terminal(h, checkpoint, request):
    e = h.engine; f = checkpoint
    f.reader.tail.path.replace(h.log); f.reader.tail.path = h.log
    tracker = e.live_zone_tracker; tracker.reader = f.reader
    e.tail = e.make_tail(); e.tail.poll()
    h.now = f.now; h.clock_hook = None
    def clock():
        if h.clock_hook is not None: h.clock_hook()
        return h.now
    h.closed = 0; h.physical = False; h.observation_hook = None
    class Observer:
        def sample(self):
            if h.observation_hook is not None: h.observation_hook()
            return OwnerInputObservation(h.now, h.now, 1, True, 1,
                int(h.physical), False, 0, 'synthetic terminal devices')
        def close(self): h.closed += 1
    observer = Observer()
    hotkey = OwnerLocationHotkey.configured('F4', confirmation_id='synthetic-terminal',
        configuration_paths=(h.game/'eqclient.ini', h.game/'Probe_private_LO1.ini'))
    j = e.journey = Journey(e.cancel_generation, settings_identity(e.settings), 'zone_itinerary')
    lease = ZoneReaderLease(tracker); tracker.lease = lease
    catalog = {'Butcherblock Mountains':68, 'The Greater Faydark':54, 'Clan Crushbone':58}
    pin = sha256(encoded(catalog)).hexdigest()
    legs = []
    for identifier, name, zone, zone_id, destination_name in (
        ('butcher-gfay-crossing', 'Butcherblock Mountains', 'gfaydark', 54, 'The Greater Faydark'),
        ('gfay-butcher-crushbone-crossing', 'The Greater Faydark', 'crushbone', 58, 'Clan Crushbone')):
        spec = destination_spec(identifier)
        legs.append(ZoneItineraryLeg(identifier, spec.zone, spec.zone_id, name,
            zone, zone_id, destination_name, spec.file_sha256, 'b'*64, 'c'*64, pin))
    target = load_terminal_camp('slave-mines', zone_catalog=catalog)
    short_deadline = getattr(request, 'param', None) == 'root_deadline'
    declaration = ZoneItineraryDeclaration('synthetic-terminal-owner', tuple(legs),
        .05 if short_deadline else 9000., 9000, .01 if short_deadline else 1800.,
        30000., terminal_camp=target)
    root = ZoneItineraryBudget(declaration, clock=clock, stop_lock=e.g0_stop_lock,
        owner_binding=('synthetic-owner',), binding_reader=lambda: ('synthetic-owner',))
    # Accounting stage setup is synthetic; no crossing/source execution claim.
    for phase, zone_id in (('crossing',68), ('loading',None), ('arrival',54),
            ('bootstrap',54), ('walking',54), ('crossing',54), ('loading',None),
            ('arrival',58), ('bootstrap',58), ('walking',58)):
        root.advance(root.stage, phase, zone_id=zone_id)
    child = JourneyInputBudget(JourneyBudgetDeclaration('d'*64, 'slave-mines',
        'camp', 1, 1500., 3000, 600., 10000.), clock=clock, stop_lock=e.g0_stop_lock,
        owner_binding=('synthetic-terminal-child',),
        binding_reader=lambda: ('synthetic-terminal-child',), parent_budget=root)
    position = f.ledger.reference.package_xyz[:2]
    guide = SourceItineraryGuide('crushbone', *f.planner.pins[2:], 'e'*64,
        .1, 6., position, (SourceWalkHint(position, position),))
    assets = SourceDestinationAssets(f.planner, guide, 'Synthetic Slave Mines', b'{}')
    j.destination_assets = assets
    veto = SceneLogVeto(h.log, expected_character=e.settings.character,
        expected_server=e.settings.server, cancel_generation=e.cancel_generation, clock=clock)
    source = object.__new__(CampSourceRuntime)
    receipt = SourceWalkFinished(f.ledger.observer.itinerary.sha256, f.ledger.reference)
    source.phase = 'complete'; source.completed_arrival = receipt; source.ledger = f.ledger
    source.lease = lease; source.sender = e.sender; source.ui = e.sender.ui
    source.reader = f.reader; source.owner_input = observer; source.clock = clock
    source.generation = e.cancel_generation
    source.policy = SimpleNamespace(_check=lambda: None, log_veto=veto)
    source.check_current = lambda: child.check()
    arrival = SectionArrival(source, receipt, f.checkpoint, b'{"synthetic_terminal":true}',
        child, sha256(encoded(guide.record())).hexdigest(), [False])
    source._section_arrival = arrival
    run = object.__new__(ZoneItineraryRuntime)
    for key, value in dict(engine=e, journey=j, root=root, clock=clock, lock=e.g0_stop_lock,
            generation=e.cancel_generation, sender=e.sender, ui=e.sender.ui, gate=e.gate,
            tracker=tracker, reader=f.reader, lease=lease, owner_input=observer, topology=1,
            hotkey=hotkey, window=focused_game_identity(e.gate), veto=veto,
            fd=e.sender.ui.fileno(), fd_identity=_fd_identity(e.sender.ui.fileno()),
            expires_at=root.expires_at, phase='terminal_ready', closed=False, busy=False,
            child_budget=child, source=source, assets=assets, terminal_arrival=arrival,
            _observer_transferred=False).items():
        setattr(run, key, value)
    def scene():
        root.check(); lease.check()
        if e.journey is not j or e.cancel_generation != run.generation or e.sender.held:
            raise ValueError('Synthetic terminal scope changed')
    run._scene = scene
    e.zone_itinerary_run = run; e.zone_itinerary_owner = object()
    h.terminal = SimpleNamespace(run=run, arrival=arrival, source=source, root=root,
        child=child, lease=lease, clock=clock, observer=observer,
        candidates=(NpcCandidate('orc fixture', (5,), 'a'*64, ((1,2),)),), token=None)
    return h


def capture(h):
    t = h.terminal
    t.token = capture_itinerary_camp_arrival(h.engine, t.run, t.arrival,
        t.clock, candidates=t.candidates)
    return t.token


def retire(h):
    """Synthetic parent transfer contract, with real lease/budget retirement."""
    t = h.terminal; token = capture(h); r = t.run
    r._observer_transferred = True
    t.arrival._claim[0] = True
    t.lease.release(); t.child.cancel('Terminal scope retired')
    t.root.advance(t.root.stage, 'arrival', zone_id=58)
    t.root.advance(t.root.stage, 'complete', zone_id=58)
    r.phase = 'terminal_transferred'; r.closed = True; r.terminal_transfer = token
    h.engine.zone_itinerary_run = h.engine.zone_itinerary_owner = None
    # Any accidental call back into retired movement authority is a test failure.
    def dead(): pytest.fail('Retired navigation authority was called')
    r._scene = t.source.check_current = t.source.policy._check = dead
    t.root.check = t.child.check = dead
    return token


def test_capture_publishes_provisional_cleanup_without_claiming_or_retiring(terminal):
    h = terminal; t = h.terminal; token = capture(h)
    assert type(token.window) is GameWindowIdentity
    assert token.monitor.floor is None and h.engine.journey.camp_motion is token.monitor
    assert h.engine.journey.arrival_floor is t.arrival.checkpoint
    assert t.arrival._claim == [False] and t.child.valid and t.lease.active
    assert t.root.stage.phase == 'walking' and not h.closed
    with pytest.raises(ValueError): capture(h)
    h.engine.stop_action('F9 after capture')
    assert h.closed == 1 and not t.arrival.checkpoint.valid


@pytest.mark.parametrize('fault', ('candidates', 'claimed', 'foreign_arrival', 'cancelled_source',
    'live_camp', 'continuation', 'source_veto', 'premature_stage', 'receipt_itinerary', 'physical'))
def test_invalid_live_capture_does_not_publish_observer_ownership(terminal, fault):
    h = terminal; e = h.engine; t = h.terminal
    if fault == 'candidates': t.candidates = list(t.candidates)
    elif fault == 'claimed': t.arrival._claim[0] = True
    elif fault == 'foreign_arrival': t.run.terminal_arrival = object()
    elif fault == 'cancelled_source': t.source.phase = 'stopped'
    elif fault == 'live_camp': e.camp_session = object()
    elif fault == 'continuation': e.journey.continue_camps = True
    elif fault == 'source_veto': t.source.policy.log_veto = object()
    elif fault == 'premature_stage': t.root.advance(t.root.stage, 'arrival', zone_id=58)
    elif fault == 'receipt_itinerary':
        object.__setattr__(t.arrival.receipt, 'itinerary_sha256', 'f'*64)
    else: h.physical = True
    with pytest.raises(ValueError): capture(h)
    assert e.journey.camp_motion is None and e.journey.arrival_floor is None
    assert not hasattr(t.run, '_camp_arrival_token') and not h.closed
    assert not h.commands and not h.events
    e.camp_session = None


def test_released_terminal_starts_existing_camp_once_with_same_observer(terminal):
    h = terminal; e = h.engine; t = h.terminal; token = retire(h)
    generation = e.cancel_generation
    assert t.run.reader.latest is None and t.arrival.checkpoint.valid
    result = continue_itinerary_camp_arrival(e, token, t.clock)
    assert result['camp_started'] and result['fresh_preparation_due']
    assert e.cancel_generation == generation+1 and e.journey.phase == 'camp'
    assert e.journey.continue_camps is False and e.journey._continue_camps is False
    assert e.journey.camp_motion.observer is token.monitor.observer
    assert e.journey.camp_motion.floor is t.arrival.checkpoint
    assert token.monitor.closed and not h.closed and t.arrival.checkpoint.valid
    assert e.camp_session.requested is None and not h.commands and not h.events
    assert not result['real_client_accepted'] and not result['safe_camp_verified']
    token.monitor.close('Late retired monitor close'); assert not h.closed
    with pytest.raises(ValueError, match='already consumed'):
        continue_itinerary_camp_arrival(e, token, t.clock)
    assert e.cancel_generation == generation+1 and e.camp_session is not None
    e.stop_action('F9'); e.stop_action('Repeated F9')
    assert h.closed == 1 and not t.arrival.checkpoint.valid


@pytest.mark.parametrize('field,value', (
    ('itinerary_sha256', 'f'*64), ('reference', object()),
    ('real_client_accepted', True), ('extra_field', 'unissued receipt metadata'),
))
def test_same_receipt_mutation_after_capture_cannot_publish_camp_provenance(terminal, field, value):
    h = terminal; e = h.engine; t = h.terminal; token = retire(h)
    receipt = t.arrival.receipt; generation = e.cancel_generation
    object.__setattr__(receipt, field, value)
    assert t.source.completed_arrival is receipt and token.arrival.receipt is receipt
    with pytest.raises(ValueError, match='provenance changed'):
        continue_itinerary_camp_arrival(e, token, t.clock)
    assert e.camp_session is None and e.journey is None
    # Only cleanup advances the generation; no stationary camp was published.
    assert e.cancel_generation == generation+1
    assert h.closed == 1 and not t.arrival.checkpoint.valid
    assert not h.commands and not h.events


@pytest.mark.parametrize('fault', ('receipt', 'root', 'floor', 'owner', 'generation',
    'destination', 'progress', 'arrival_age'))
def test_final_camp_current_callback_cannot_change_published_arrival(terminal, monkeypatch, fault):
    from eql_automation.camp_progress import CampProgress
    h = terminal; e = h.engine; t = h.terminal; token = retire(h)
    original = e._camp_current; fired = []; attributions = []
    bind_arrival = CampProgress.bind_arrival
    def record_arrival(progress, **kwargs):
        attributions.append(kwargs)
        return bind_arrival(progress, **kwargs)
    monkeypatch.setattr(CampProgress, 'bind_arrival', record_arrival)
    def current(*args, **kwargs):
        result = original(*args, **kwargs)
        if result and not fired:
            fired.append(e.camp_session)
            if fault == 'receipt':
                object.__setattr__(t.arrival.receipt, 'itinerary_sha256', 'f'*64)
            elif fault == 'root': t.root.cancel('Changed after final camp check')
            elif fault == 'floor': e.journey.arrival_floor = None
            elif fault == 'owner': e.autopilot = None
            elif fault == 'generation': e.cancel_generation += 1
            elif fault == 'destination':
                e.journey.destination_assets = type(token.destination)('north-wall', b'{}')
            elif fault == 'progress':
                e.camp_session.progress = CampProgress(e.camp_session.started, e.settings.level)
            else: h.now = t.arrival.receipt.reference.raw_fix.received_monotonic+.501
        return result
    e._camp_current = current
    with pytest.raises(ValueError):
        continue_itinerary_camp_arrival(e, token, t.clock)
    assert fired and not attributions
    assert fired[0].progress.arrival_destination is None
    assert e.camp_session is None and e.journey is None
    assert h.closed == 1 and not t.arrival.checkpoint.valid
    assert not h.commands and not h.events


@pytest.mark.parametrize('fault', ('stale', 'source_cancelled', 'receipt', 'claim', 'lease',
    'settings', 'queued', 'physical', 'observer_clock', 'root', 'veto', 'veto_tail', 'descriptor'))
def test_terminal_provenance_or_scene_failure_never_starts_camp(terminal, fault):
    h = terminal; e = h.engine; t = h.terminal; token = retire(h)
    if fault == 'stale': h.now = t.arrival.receipt.reference.raw_fix.received_monotonic+.501
    elif fault == 'source_cancelled': t.source.phase = 'stopped'
    elif fault == 'receipt': t.source.completed_arrival = object()
    elif fault == 'claim': t.arrival._claim[0] = False
    elif fault == 'lease': t.lease.active = True
    elif fault == 'settings': e.settings.level += 1
    elif fault == 'queued': e.jobs.put(('arm', e.cancel_generation))
    elif fault == 'physical': h.physical = True
    elif fault == 'observer_clock': token.monitor.last_observed_at = h.now+1.
    elif fault == 'root': t.root._pulses += 1
    elif fault == 'veto': h.append('an orc hits YOU for 1 point of damage.')
    elif fault == 'veto_tail':
        token.veto.tail = SceneLogVeto(h.log, expected_character=e.settings.character,
            expected_server=e.settings.server, cancel_generation=token.generation, clock=t.clock).tail
    else: e.sender.ui.fileno = lambda: token.fd+1
    with pytest.raises((ValueError, OSError)):
        continue_itinerary_camp_arrival(e, token, t.clock)
    assert e.camp_session is None and not h.commands and not h.events
    assert h.closed == 1 and not t.arrival.checkpoint.valid
    t.lease.active = False


@pytest.mark.parametrize('where', ('descriptor', 'sample'))
@pytest.mark.parametrize('changed', ('window', 'process'))
def test_late_provider_window_change_refuses_before_camp_dispatch(terminal, where, changed):
    h = terminal; e = h.engine; t = h.terminal; token = retire(h)
    starts = []; changed_at = []
    start = e.start_stationary_camp
    def start_camp(**kwargs):
        starts.append(True)
        return start(**kwargs)
    e.start_stationary_camp = start_camp
    def change_window():
        if changed_at: return
        changed_at.append(True)
        if changed == 'process':
            e.gate.game_session = lambda: {'pid':token.window.pid+1,
                'start_ticks':str(token.window.start_ticks+1)}
        else:
            window = SimpleNamespace(id=token.window.window_id+1)
            e.gate.windows = lambda: [window]
            e.gate.focused_window = lambda: window
    if where == 'sample':
        h.observation_hook = change_window
    else:
        original = e.sender.ui.fileno; calls = []
        def descriptor():
            value = original(); calls.append(True)
            # Initial released check, handoff entry, then the final descriptor
            # callback immediately before the handoff's focus validation.
            if len(calls) == 3: change_window()
            return value
        e.sender.ui.fileno = descriptor
    with pytest.raises(ValueError):
        continue_itinerary_camp_arrival(e, token, t.clock)
    assert changed_at and not starts and e.camp_session is None and e.journey is None
    assert h.closed == 1 and not t.arrival.checkpoint.valid
    assert not h.commands and not h.events


def test_final_focus_callback_owner_change_is_rechecked_before_dispatch(terminal):
    h = terminal; e = h.engine; t = h.terminal; token = retire(h)
    original = e.gate.game_session; fired = []
    def session():
        value = original()
        if not fired:
            fired.append(True)
            e.cancel_generation += 1
        return value
    e.gate.game_session = session
    e.start_stationary_camp = lambda **kwargs: pytest.fail('Changed owner dispatched camp startup')
    with pytest.raises(ValueError):
        continue_itinerary_camp_arrival(e, token, t.clock)
    assert fired and e.camp_session is None and e.journey is None
    assert h.closed == 1 and not t.arrival.checkpoint.valid
    assert not h.commands and not h.events


@pytest.mark.parametrize('terminal', ('arrival_age', 'root_deadline'), indirect=True)
def test_final_focus_latency_is_charged_before_camp_dispatch(terminal, request):
    h = terminal; e = h.engine; t = h.terminal; token = retire(h)
    original = e.gate.game_session; fired = []
    boundary = request.node.callspec.params['terminal']
    received = t.arrival.receipt.reference.raw_fix.received_monotonic
    def session():
        value = original()
        if not fired:
            fired.append(True)
            h.now = received+.501 if boundary == 'arrival_age' else token.expires_at+.001
        return value
    e.gate.game_session = session
    e.start_stationary_camp = lambda **kwargs: pytest.fail('Expired handoff dispatched camp startup')
    message = 'expired after capture' if boundary == 'arrival_age' else 'fresh receipt'
    with pytest.raises(ValueError, match=message):
        continue_itinerary_camp_arrival(e, token, t.clock)
    if boundary == 'root_deadline':
        # This isolates trip expiry: both the source fix and input sample would
        # still be fresh if the original absolute deadline were ignored.
        assert h.now-received < .5
        assert h.now-token.monitor.last_observed_at < .1
    assert fired and e.camp_session is None and e.journey is None
    assert h.closed == 1 and not t.arrival.checkpoint.valid
    assert not h.commands and not h.events


@pytest.mark.parametrize('mode', ('F8', 'F9', 'generation'))
def test_final_post_focus_clock_owner_change_refuses_before_camp_dispatch(terminal, mode):
    h = terminal; e = h.engine; t = h.terminal; token = retire(h)
    original = e.gate.game_session; fired = []
    def clock_stop():
        h.clock_hook = None; fired.append(True)
        if mode == 'F8': e.handle_job('arm', e.cancel_generation)
        elif mode == 'F9': e.stop_action('F9 during final handoff clock')
        else: e.cancel_generation += 1
    def session():
        value = original()
        h.clock_hook = clock_stop
        return value
    e.gate.game_session = session
    e.start_stationary_camp = lambda **kwargs: pytest.fail('Changed owner dispatched camp startup')
    with pytest.raises(ValueError):
        continue_itinerary_camp_arrival(e, token, t.clock)
    assert fired and e.camp_session is None and e.journey is None
    assert h.closed == 1 and not t.arrival.checkpoint.valid
    assert not h.commands and not h.events


@pytest.mark.parametrize('where', ('sample', 'gauges', 'start_stop', 'binding', 'trace'))
@pytest.mark.parametrize('mode', ('F8', 'F9'))
def test_owner_cancellation_during_adoption_closes_observer_once(terminal, where, mode):
    h = terminal; e = h.engine; t = h.terminal; token = retire(h); fired = []
    def stop():
        if fired: return
        fired.append(True)
        if mode == 'F8': e.handle_job('arm', e.cancel_generation)
        else: e.stop_action('Synthetic F9 during terminal handoff')
    if where == 'sample': h.observation_hook = stop
    elif where == 'gauges':
        original = e.gate.read_gauges
        def gauges(*args): stop(); return original(*args)
        e.gate.read_gauges = gauges
    elif where == 'start_stop':
        original = e.emit
        def notice(text=None):
            if text and 'Camp starting' in text: stop()
            return original(text)
        e.emit = notice
    elif where == 'binding':
        original = e._camp_motion_binding
        def binding():
            result = original(); stop(); return result
        e._camp_motion_binding = binding
    else:
        original = e.trace
        def trace(event, **kwargs):
            original(event, **kwargs)
            if event == 'journey_itinerary_camp_handoff': stop()
        e.trace = trace
    try:
        result = continue_itinerary_camp_arrival(e, token, t.clock)
    except ValueError:
        result = {'camp_started':False}
    assert fired and not result['camp_started']
    assert e.journey is None and e.camp_session is None
    assert h.closed == 1 and not t.arrival.checkpoint.valid
    assert not h.commands and not h.events and not e.sender.held
