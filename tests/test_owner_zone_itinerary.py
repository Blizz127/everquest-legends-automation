"""Owner dispatch/cancellation contracts; fake engine plus real root accounting.

The small base below sends no input and does not stand in for client acceptance.
Separate integration tests use the retained helper with anonymous-pipe controls.
"""
from dataclasses import replace
import os
from queue import Queue
import threading
import time
from types import SimpleNamespace

import pytest

from eql_automation.native_region_policy import encoded
from eql_automation.owner_journey_runtime import Journey
from eql_automation.owner_navigation_preflight import settings_identity
from eql_automation.owner_route_trial import SOURCE_JOB
from eql_automation.owner_zone_itinerary import ITINERARY_JOB, make_zone_itinerary_engine
from eql_automation.route_geometry import RouteMotionBounds
from eql_automation.zone_itinerary_budget import ZoneItineraryDeclaration, load_zone_itinerary
from eql_automation.zone_itinerary_runtime import ZoneItineraryPlan
from test_motion_collection import retained


def synthetic_legs(catalog, first_crossing=None):
    """Registered IDs with explicit synthetic pins; no private staged files."""
    from eql_automation.owner_source_crossing import PinnedSourceCrossingSpec
    from eql_automation.source_destinations import destination_spec
    from eql_automation.zone_line import ExpectedZoneLine
    identifiers = ('butcher-gfay-crossing', 'gfay-butcher-crushbone-crossing')
    specs = {}
    for index, identifier in enumerate(identifiers):
        guide = destination_spec(identifier)
        name, zone, zone_id = (('The Greater Faydark', 'gfaydark', 54),
                              ('Clan Crushbone', 'crushbone', 58))[index]
        line = ExpectedZoneLine(identifier+'-synthetic', guide.zone,
            *('a'*64,)*5, 'DRNTP00255000001', 2, (1,), (2,))
        specs[identifier] = PinnedSourceCrossingSpec(identifier, guide.zone, name, zone_id, zone,
            guide.provenance_sha256, guide.goal, guide.goal,
            ((guide.goal, guide.goal), (guide.goal, guide.goal)), line,
            ('b' if index == 0 else 'c')*64, encoded(dict(synthetic=True, unexecuted=True)))
    if first_crossing is not None:
        guide = destination_spec(identifiers[0])
        # This manifest adapter supplies the registered metadata required by
        # the loader. Execution retains the actual synthetic corridor below.
        specs[identifiers[0]] = replace(first_crossing, start_xy=guide.goal,
                                        provenance_sha256=guide.provenance_sha256)
    legs = load_zone_itinerary(identifiers, zone_catalog=catalog,
                               crossing_provider=specs.__getitem__)
    if first_crossing is not None:
        specs[identifiers[0]] = first_crossing
    return legs, specs


class Base:
    def __init__(self, state):
        self.state = state
        self.cancel_generation = self.supervised_epoch = self.route_session_epoch = 0
        self.settings = SimpleNamespace(game_dir='/synthetic', character='Probe', server='private', level=1)
        self.jobs = Queue()
        self.g0_stop_lock = threading.RLock()
        self.sender = state.sender
        self.gate = state.gate
        self.live_zone_tracker = state.tracker
        self.journey = self.journey_last_result = self._journey_assist = None
        self.supervised_motion = self.source_crossing_run = self.camp_session = None
        self.cancelled = True
        self.stopping = self.active = False
        self.zone_loading_until = 0.
        self.messages, self.traces, self.delegated = [], [], []

    def _supervised_job_names(self): return (SOURCE_JOB,)

    def post(self, name, value=None):
        self.supervised_epoch += 1
        self.route_session_epoch += 1
        if name in self._supervised_job_names():
            value = dict(declaration=value, epoch=self.supervised_epoch,
                         generation=self.cancel_generation, settings=settings_identity(self.settings))
        self.jobs.put((name, value))

    def handle_job(self, name, value):
        if name == 'arm':
            self.stop_action('F8 owner takeover')
            self._journey_assist = (self.cancel_generation, settings_identity(self.settings))
            return
        self.delegated.append((name, value))
        if name != SOURCE_JOB: return
        self.journey = Journey(self.cancel_generation, settings_identity(self.settings), 'travel',
                               destination_id=value['declaration']['destination_id'])
        recipe = self._prepare_supervised_job(name)
        pending = dict(value, job=name, continuation=recipe, sender=self.sender,
                       gate=self.gate, cancelled=None, window=(7, 8, 9))
        self.supervised_motion = pending
        self._supervised_current(pending, active=False)
        self.cancelled = False

    def _prepare_supervised_job(self, name):
        self.state.now += self.state.asset_seconds
        self.state.asset_hook()
        return dict(started=self.state.now, maximum_seconds=180.,
                    destination=SimpleNamespace(destination_id=self.journey.destination_id))

    def _supervised_current(self, pending, *, active): return None
    def _supervised_measurement_account(self, pending, session): return None
    def _trial_scope_current(self, pending): return None
    def _section_parent_budget(self, pending): return None
    def _source_journey_budget(self, pending): return None
    def _source_input_release_deadline(self, pending): return None
    def _source_crossing_budget(self, journey, identifier): return None
    def _finish_source_crossing(self, runtime): return 'ordinary crossing result'
    def _owner_navigation_active(self): return self.journey is not None
    def _navigation_busy(self): return self.supervised_motion is not None or self.source_crossing_run is not None
    def _route_idle(self): return not self.stopping and not self.active
    def zone_changed(self, body, now): return 'ordinary zone change'
    def autopilot_payload(self): return {}
    def autopilot_tick(self, now): return None
    def pump(self): pass
    def emit(self, value): self.messages.append(value)
    def trace(self, name, **value): self.traces.append((name, value))

    def stop_action(self, reason, *, keep_autopilot=False):
        self.cancel_generation += 1
        self.cancelled = True
        self.journey = self.supervised_motion = self.source_crossing_run = None
        self._journey_assist = None
        self.journey_last_result = dict(phase='stopped', reason=str(reason))


@pytest.fixture
def owner():
    rd, wr = os.pipe()
    state = SimpleNamespace(now=100., asset_seconds=0., asset_hook=lambda:None,
                            provider_hook=lambda:None, calls=[])
    state.clock = lambda:state.now
    state.sender = SimpleNamespace(ui=SimpleNamespace(fileno=lambda:wr), held=set(),
                                   unfinished=False, dismissed=False)
    window = SimpleNamespace(id=7)
    state.gate = SimpleNamespace(windows=lambda:[window], game_session=lambda:dict(pid=8, start_ticks='9'),
                                focused_window=lambda:window, controls_ready=lambda:True)
    state.tracker = SimpleNamespace(closed=False,
        reader=SimpleNamespace(zone_id=68, zone_display_name='Butcherblock Mountains'))
    legs, _ = synthetic_legs({'Butcherblock Mountains':68, 'The Greater Faydark':54, 'Clan Crushbone':58})
    declaration = ZoneItineraryDeclaration('synthetic-owner-itinerary', legs, 120., 100, 20., 1000.)
    bounds = RouteMotionBounds('independent-test-envelope', 'explicit-test-hypotheses',
        .01, .15, .2, 60., .3, .1, 10., .2, 1.2, 6.)
    state.plan = ZoneItineraryPlan(declaration, bounds, encoded(dict(synthetic=True)),
                                  lambda _:None, lambda _:None, lambda _:None)
    def provider(engine, declaration):
        state.calls.append(declaration)
        state.provider_hook()
        return state.plan
    state.engine = make_zone_itinerary_engine(Base, itinerary_provider=provider, clock=state.clock)(state)
    state.request = dict(itinerary_id='butcher-gfay-crushbone', open_flat_clear=True,
                         owner_supervised_continuation=True)
    yield state
    state.engine.stop_action('synthetic test cleanup')
    os.close(wr)
    os.close(rd)


def start(state):
    e = state.engine
    e.post(ITINERARY_JOB, state.request)
    return e.handle_job(*e.jobs.get_nowait())


def test_explicit_job_delegates_once_and_starts_root_before_initial_assets(owner):
    s = owner; e = s.engine
    s.asset_seconds = 7.
    start(s)
    o = e.zone_itinerary_owner
    assert o is not None and o.journey is e.journey and o.pending is e.supervised_motion
    assert o.root.started == 100. and o.root.expires_at == 220.
    assert len(e.delegated) == 1 and e.delegated[0][0] == SOURCE_JOB
    assert e.delegated[0][1]['declaration'] == dict(open_flat_clear=True,
        destination_id='butcher-gfay-crossing', continue_camps=False)
    assert s.calls == [s.request] and e.jobs.empty()
    assert e._source_journey_budget(o.pending) is o.root
    assert e._section_parent_budget(o.pending) is o.root
    assert e._source_input_release_deadline(o.pending) == 220.
    p = o.pending
    p['expires'] = 2000.
    e._trial_scope_current(p)
    assert p['expires'] == 220.
    assert not e.autopilot_payload()['zone_itinerary']['real_client_accepted']


def test_queued_request_is_copied_before_the_owner_mutates_its_ui_dictionary(owner):
    s = owner; e = s.engine
    e.post(ITINERARY_JOB, s.request)
    s.request['owner_supervised_continuation'] = False
    e.handle_job(*e.jobs.get_nowait())
    assert e.zone_itinerary_owner is not None
    assert s.calls[0]['owner_supervised_continuation'] is True


@pytest.mark.parametrize('fault', ('generation', 'epoch', 'settings', 'closed_plan', 'provider_f9', 'provider_f8',
                                  'missing_supervision', 'wrong_zone'))
def test_invalid_or_revoked_request_never_delegates_a_source_job(owner, fault):
    s = owner; e = s.engine
    if fault == 'closed_plan': object.__setattr__(s.plan, 'bounds_basis', encoded(dict(changed=True)))
    elif fault == 'provider_f9': s.provider_hook = lambda:e.stop_action('F9 during provider')
    elif fault == 'provider_f8': s.provider_hook = lambda:e.handle_job('arm', e.cancel_generation)
    elif fault == 'missing_supervision': s.request['owner_supervised_continuation'] = False
    elif fault == 'wrong_zone': s.tracker.reader.zone_id = 54
    e.post(ITINERARY_JOB, s.request)
    name, value = e.jobs.get_nowait()
    if fault == 'generation': value['generation'] += 1
    elif fault == 'epoch': value['epoch'] += 1
    elif fault == 'settings': value['settings'] = ()
    e.handle_job(name, value)
    assert not e.delegated and e.zone_itinerary_owner is None and e.journey is None
    assert not e.sender.held
    if fault == 'provider_f8': assert e._journey_assist is not None


@pytest.mark.parametrize('action', ('F8', 'F9'))
@pytest.mark.parametrize('boundary', ('queue', 'window', 'descriptor'))
def test_stop_after_plan_check_cannot_be_adopted_as_a_new_request(owner, action, boundary):
    s = owner; e = s.engine
    fired = []
    target, attribute = {
        'queue': (e.jobs, 'empty'),
        'window': (s.gate, 'windows'),
        'descriptor': (s.sender.ui, 'fileno'),
    }[boundary]
    original = getattr(target, attribute)

    def late_stop():
        setattr(target, attribute, original)
        fired.append(action)
        if action == 'F8': e.handle_job('arm', e.cancel_generation)
        else: e.stop_action('F9 after plan check')
        return original()

    s.provider_hook = lambda:setattr(target, attribute, late_stop)
    start(s)
    assert fired == [action]
    assert not e.delegated and e.zone_itinerary_owner is None
    assert e.journey is None and e.supervised_motion is None
    assert e.cancel_generation == 1
    assert (e._journey_assist is not None) == (action == 'F8')
    assert not e.sender.held


def test_root_deadline_includes_slow_initial_asset_loading(owner):
    s = owner; e = s.engine
    s.asset_seconds = 121.
    start(s)
    assert e.zone_itinerary_owner is None and e.supervised_motion is None and e.journey is None
    assert any('deadline' in value for value in e.messages)


def test_root_brackets_compact_plan_binding_with_full_leg_mutation_checks(owner):
    s = owner; e = s.engine
    start(s); o = e.zone_itinerary_owner
    windows = e.gate.windows
    called = []
    def mutate():
        value = windows()
        if o.root._checking and not called:
            called.append(True)
            object.__setattr__(s.plan.declaration.legs[0], 'source_name', 'Changed during root binding')
        return value
    e.gate.windows = mutate
    with pytest.raises(ValueError, match='declaration|plan'):
        o.check()
    assert called and not o.root.valid


@pytest.mark.parametrize('boundary', ('descriptor', 'queue'))
@pytest.mark.parametrize('field', ('bounds', 'leg'))
def test_final_owner_binding_rechecks_plan_after_late_callbacks(owner, boundary, field):
    s = owner; e = s.engine
    start(s); o = e.zone_itinerary_owner
    target, attribute = (o.ui, 'fileno') if boundary == 'descriptor' else (e.jobs, 'empty')
    original = getattr(target, attribute)
    called = []
    def mutate():
        value = original()
        if not o.root._checking and not called:
            called.append(True)
            if field == 'bounds':
                object.__setattr__(s.plan.probe_bounds, 'maximum_requested_hold', .14)
            else:
                object.__setattr__(s.plan.declaration.legs[0], 'source_name', 'Changed in final binding')
        return value
    setattr(target, attribute, mutate)
    assert not o.root._checking
    with pytest.raises(ValueError, match='plan'):
        o.check()
    assert called


@pytest.mark.parametrize('fault', ('generation', 'settings', 'epoch', 'sender', 'tracker', 'journey', 'late_descriptor'))
def test_owner_context_cannot_survive_replacement_or_late_stop(owner, fault):
    s = owner; e = s.engine
    start(s); o = e.zone_itinerary_owner
    if fault == 'generation': e.cancel_generation += 1
    elif fault == 'settings': e.settings.level += 1
    elif fault == 'epoch': e.route_session_epoch += 1
    elif fault == 'sender': e.sender = SimpleNamespace(ui=o.ui)
    elif fault == 'tracker': e.live_zone_tracker = SimpleNamespace(reader=o.reader)
    elif fault == 'journey': e.journey = replace(e.journey)
    else:
        fd = o.fd
        def changed():
            e.stop_action('F9 in descriptor callback')
            return fd
        o.ui.fileno = changed
    with pytest.raises(ValueError): o.check()
    if fault == 'late_descriptor': assert e.zone_itinerary_owner is None


def test_crossing_hook_preserves_one_root_and_refuses_wrong_leg(owner):
    s = owner; e = s.engine
    start(s); o = e.zone_itinerary_owner
    assert e._source_crossing_budget(o.journey, 'butcher-gfay-crossing') is o.root
    assert o.root.stage.phase == 'crossing' and o.root.expires_at == 220.
    with pytest.raises(ValueError): e._source_crossing_budget(o.journey, 'gfay-butcher-crushbone-crossing')


class Completed:
    def __init__(self, callback=lambda:None, boundary='snapshot'):
        self.callback = callback
        self.boundary = boundary
        self.phase, self.closed, self.busy = 'complete', False, False
        self.crossing = None
        self.cancelled = []
    def snapshot(self):
        if self.boundary == 'snapshot': self.callback()
        return dict(real_client_accepted=False)
    def release(self):
        self.closed = True
        if self.boundary == 'release': self.callback()
    def cancel(self, reason): self.cancelled.append(reason); self.phase = 'stopped'


@pytest.mark.parametrize('action', ('none', 'f8', 'f9'))
@pytest.mark.parametrize('boundary', ('snapshot', 'release'))
def test_completion_cannot_overwrite_late_assist_or_stop(owner, action, boundary):
    s = owner; e = s.engine
    start(s); o = e.zone_itinerary_owner
    e.supervised_motion = None
    for phase, zone in (('crossing',68), ('loading',None), ('arrival',54), ('bootstrap',54),
                        ('walking',54), ('crossing',54), ('loading',None), ('arrival',58), ('complete',58)):
        o.root.advance(o.root.stage, phase, zone_id=zone)
    def callback():
        if action == 'f8': e.handle_job('arm', e.cancel_generation)
        elif action == 'f9': e.stop_action('late owner F9')
    run = Completed(callback, boundary)
    e.zone_itinerary_run = run
    if action == 'none':
        result = e._finish_zone_itinerary(run)
        assert result['phase'] == 'zone_itinerary_complete' and e.zone_itinerary_owner is None
    else:
        with pytest.raises(ValueError): e._finish_zone_itinerary(run)
        assert e.journey_last_result['phase'] == 'stopped'
        assert not any(name == 'zone_itinerary_completed' for name, _ in e.traces)
        if action == 'f8': assert e._journey_assist is not None


@pytest.mark.parametrize('action', ('f8', 'f9'))
def test_busy_cancel_retains_navigation_until_release_so_assist_waits(owner, action):
    s = owner; e = s.engine
    start(s)
    run = Completed(); run.phase = 'probes'; run.busy = True
    e.zone_itinerary_run = run
    if action == 'f8': e.handle_job('arm', e.cancel_generation)
    else: e.stop_action('F9 while itinerary child is busy')
    assert e.zone_itinerary_owner is None and e.zone_itinerary_run is run
    assert e._navigation_busy()
    assert (e._journey_assist is not None) == (action == 'f8')
    payload = e.autopilot_payload()
    assert payload['state'] == 'stopping' and payload['journey_phase'] == 'zone_itinerary'
    assert payload['zone_itinerary']['leg'] == 1 and payload['zone_itinerary']['legs'] == 2
    assert payload['zone_itinerary']['stage'] == 'stopping'
    run.busy = False
    e._cleanup_zone_itinerary()
    assert run.closed and e.zone_itinerary_run is None
    assert (e._journey_assist is not None) == (action == 'f8')
    assert e._zone_itinerary_stopping is None and 'zone_itinerary' not in e.autopilot_payload()


def test_initial_navigation_stop_stays_visible_until_its_input_is_released(owner, monkeypatch):
    s = owner; e = s.engine
    start(s)
    stop = Base.stop_action
    def retain_busy_measurement(engine, *args, **kwargs):
        pending = engine.supervised_motion
        stop(engine, *args, **kwargs)
        engine.supervised_motion = pending
    monkeypatch.setattr(Base, 'stop_action', retain_busy_measurement)
    e.stop_action('Initial measurement input is still releasing')
    assert e.zone_itinerary_owner is None and e.zone_itinerary_run is None
    assert e.autopilot_payload()['state'] == 'stopping'
    assert e.autopilot_payload()['zone_itinerary']['stage'] == 'stopping'
    e.supervised_motion = None
    e._cleanup_zone_itinerary()
    assert e._zone_itinerary_stopping is None and 'zone_itinerary' not in e.autopilot_payload()


@pytest.fixture
def real_owner(tmp_path, retained, monkeypatch):
    """Actual retained helper, synthetic game directory and anonymous pipe."""
    import test_owner_journey_runtime as journey_fixture
    original = journey_fixture.make_owner_journey_engine
    selected = [None]
    def combined(*args, **kwargs):
        return original(*args, **kwargs, zone_itinerary_provider=lambda engine, declaration:selected[0])
    monkeypatch.setattr(journey_fixture, 'make_owner_journey_engine', combined)
    generator = journey_fixture.h.__wrapped__(tmp_path, retained, monkeypatch, SimpleNamespace(param='walking_sections'))
    h = next(generator)
    h.itinerary_selection = selected
    yield h
    generator.close()


@pytest.mark.parametrize('stop_phase', ('initial_route', 'first_crossing'))
def test_real_owner_initial_seven_pulses_share_root_and_stop_keeps_assist_separate(real_owner, monkeypatch, stop_phase):
    from test_owner_source_crossing import _configure_sectioned_crossing
    h = real_owner; e = h.engine
    crossing = _configure_sectioned_crossing(h, monkeypatch)
    assets = h.source_loading[0]()
    catalog = {'Fixture':68, 'The Greater Faydark':54, 'Clan Crushbone':58}
    legs, crossings = synthetic_legs(catalog, crossing)
    bounds = RouteMotionBounds('synthetic-independent-itinerary', 'synthetic-bounds-only',
        .01, .15, .2, 60., .3, .1, 10., .2, 1.2, 6.)
    plan = ZoneItineraryPlan(ZoneItineraryDeclaration('synthetic-retained-owner', legs, 120., 1000, 100., 10000.),
        bounds, encoded(dict(kind='synthetic-independent-owner-bounds')),
        lambda identifier:assets, lambda _:None, crossings.__getitem__)
    h.itinerary_selection[0] = plan
    e.read_log()
    captured = []
    cancellations = []
    from eql_automation.source_motion import SourceReceiptLedger
    actual_cancel = SourceReceiptLedger.cancel
    def cancel_ledger(ledger, reason):
        cancellations.append(str(reason))
        return actual_cancel(ledger, reason)
    monkeypatch.setattr(SourceReceiptLedger, 'cancel', cancel_ledger)
    actual = e._handoff_completed_motion
    def handoff(pending, session, record):
        owner = e.zone_itinerary_owner
        captured.append((owner, owner.root.snapshot(), session, record))
        return actual(pending, session, record)
    monkeypatch.setattr(e, '_handoff_completed_motion', handoff)
    e.post(ITINERARY_JOB, dict(itinerary_id='synthetic-retained-owner', open_flat_clear=True,
                             owner_supervised_continuation=True))
    e.handle_job(*e.jobs.get_nowait())
    assert e.supervised_motion is not None, h.notices
    h.due_trial()
    deadline = time.monotonic()+45.
    while not captured and time.monotonic() < deadline:
        h.tick(); h.drain(); time.sleep(.01)
        if e.zone_itinerary_owner is None: break
    assert captured, '\n'.join(h.notices)
    owner, snapshot, session, record = captured[0]
    assert snapshot['reserved_pulses'] == 7 and len(session.receipts) == 7
    assert owner.initial_account.session is session and owner.initial_account.root is owner.root
    assert len(owner.initial_account.releases) == 7
    assert e.jobs.empty() and e.journey.generation == owner.generation
    assert owner.root.stage.phase == 'walking' and owner.root.stage.leg_index == 0
    if stop_phase == 'first_crossing':
        completed = []
        actual_finish = e._finish_source_crossing
        def finish(crossing):
            result = actual_finish(crossing)
            run = e.zone_itinerary_run
            completed.append((crossing, run, owner.root.stage, e.cancel_generation))
            assert run is not None and run.phase == 'load_destination'
            assert run.root is owner.root and run.journey is owner.journey
            assert run.sender is owner.sender and run.owner_input is crossing.owner_input
            assert run.reader is owner.reader and run.lease is crossing.lease
            assert crossing.closed and crossing.phase == 'transferred'
            assert e.source_crossing_run is None and not h.observer_closed
            e.handle_job('arm', e.cancel_generation)
            return result
        monkeypatch.setattr(e, '_finish_source_crossing', finish)
        deadline = time.monotonic()+90.
        while not completed and time.monotonic() < deadline:
            e.read_log(); h.tick(); h.drain(); time.sleep(.01)
            if e.zone_itinerary_owner is None: break
        assert completed, '\n'.join(h.notices+cancellations)
        crossing, run, stage, generation = completed[0]
        assert stage.phase == 'bootstrap' and stage.leg_index == 1
        assert generation == owner.generation and len(run.records) == 1
        assert owner.root.snapshot()['reserved_pulses'] > 7
        assert e.jobs.empty() and not run.busy and run.closed
    else:
        e.handle_job('arm', e.cancel_generation)
    for _ in range(5): h.tick(); h.drain()
    assert not h.sender.held and e.zone_itinerary_owner is None
    assert e.journey is None and e.camp_session is None
    assert e.live_zone_tracker.lease is None and h.observer_closed
    assert not owner.root.valid
