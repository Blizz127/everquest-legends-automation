from dataclasses import replace
from queue import SimpleQueue
from types import SimpleNamespace

import pytest

from eql_automation.owner_navigation_preflight import make_owner_nov12_engine, PREFLIGHT_JOB
from eql_automation.owner_input_observer import OwnerInputObservation


def forbidden(*args, **kwargs):
    pytest.fail('Read-only preflight called an input/sender/capture path')


class Gate:
    def __init__(self):
        self.window = SimpleNamespace(id=42)
        self.session = {'pid': 10, 'start_ticks': '100'}
        self.focus = True
    def windows(self): return [self.window]
    def game_session(self): return self.session.copy()
    def focused_window(self): return self.window if self.focus else None
    def controls_ready(self): return self.focus
    capture = forbidden


class Base:
    def __init__(self):
        self.sender = self.autopilot = self.pointer = self.deferred = None
        self.loc_request = self.loc_wanted = self.recorder = None
        self.keys = set()
        self.measurement_only = True
        self.active = self.preparing = self.stopping = self.command_recovery_pending = False
        self.cancelled = True
        self.cancel_generation = 2
        self.jobs = SimpleQueue()
        self.gate = Gate()
        self.settings = SimpleNamespace(game_dir='/fixture', character='Test', server='freeport', level=7)
        self.traces = []; self.notices = []; self.base_jobs = []
        self.run_hook = lambda: None
    def post(self, name, value=None): self.jobs.put((name, value))
    def handle_job(self, name, value): self.base_jobs.append((name, value))
    def trace(self, event, **values): self.traces.append((event, values))
    def emit(self, message): self.notices.append(message)
    def stop_action(self, *args, **kwargs): self.cancel_generation += 1
    def stop_autopilot(self, *args, **kwargs): self.cancel_generation += 1
    def autopilot_tick(self, now): return None
    def run(self): return self.run_hook()
    ensure_sender = send = hold = pump = forbidden


def setup():
    now = [100.]
    observers = []
    hooks = []

    class Observer:
        def __init__(self, **kwargs):
            self.kwargs = kwargs; self.closed = 0; self.samples = 0
            self.sample_hook = lambda: None
            self.result_hook = lambda r: r
            self.close_hook = lambda: None
            observers.append(self)
        def sample(self):
            self.samples += 1
            self.sample_hook()
            return self.result_hook(OwnerInputObservation(now[0], now[0], 1, self.samples > 1,
                3, 0, False, 0, 'topology_changed' if self.samples == 1 else 'observed'))
        def close(self): self.closed += 1; self.close_hook()

    engine = make_owner_nov12_engine(Base, observer_factory=Observer, clock=lambda: now[0])()
    def queue():
        engine.post(PREFLIGHT_JOB)
        engine.handle_job(*engine.jobs.get_nowait())
    def tick(delta):
        now[0] += delta
        engine.autopilot_tick(now[0])
    return engine, now, observers, queue, tick


def last_result(engine):
    return [v for e, v in engine.traces if e == 'nav_preflight_result'][-1]


def test_real_lifecycle_two_ticks_reports_input_separately_from_missing_live_providers():
    e, now, observers, queue, tick = setup()
    queue(); assert not observers and e.deferred is None and e.cancelled
    tick(4); assert len(observers) == 1 and observers[0].samples == 1
    assert e.navigation_preflight is not None and e.sender is None
    tick(.03)
    r = last_result(e)
    assert r['outcome'] == 'observed' and r['input_sample_clear']
    assert not r['movement_authorized'] and not r['real_client_accepted'] and not r['game_input_sent']
    assert 'calibrated_ui_scene' in r['missing_providers'] and 'current_zone_binding' in r['missing_providers']
    assert observers[0].closed == 1 and e.navigation_preflight is None and e.cancelled


@pytest.mark.parametrize('stop', ['stop_action', 'stop_autopilot'])
def test_f9_or_f11_closes_observer_and_preserves_stop_chain(stop):
    e, now, observers, queue, tick = setup(); queue(); tick(4)
    getattr(e, stop)('stop')
    tick(.03)
    assert last_result(e)['outcome'] == 'cancelled'
    assert e.cancel_generation == 3 and observers[0].closed == 1 and observers[0].samples == 1


@pytest.mark.parametrize('job', ['settings', 'quit', 'nav_stop_check_later'])
def test_post_during_sample_revokes_before_publishing_even_before_job_is_handled(job):
    e, now, observers, queue, tick = setup(); queue(); tick(4)
    observers[0].sample_hook = lambda: e.post(job, object())
    tick(.03)
    assert last_result(e)['outcome'] == 'refused' and not last_result(e)['input_sample_clear']
    assert observers[0].closed == 1 and e.base_jobs == []


def test_post_during_close_revokes_the_result():
    e, now, observers, queue, tick = setup(); queue(); tick(4)
    observers[0].close_hook = lambda: e.post('settings', object())
    tick(.03)
    assert last_result(e)['outcome'] == 'cancelled' and not last_result(e)['input_sample_clear']


@pytest.mark.parametrize('change', ['level', 'settings', 'process', 'window', 'focus', 'sender', 'exit'])
def test_changed_bound_state_never_reuses_first_sample(change):
    e, now, observers, queue, tick = setup(); queue(); tick(4)
    if change == 'level': e.settings.level = 8
    elif change == 'settings': e.settings = SimpleNamespace(**vars(e.settings))
    elif change == 'process': e.gate.session['start_ticks'] = '101'
    elif change == 'window': e.gate.window.id = 99
    elif change == 'focus': e.gate.focus = False
    elif change == 'sender': e.sender = SimpleNamespace(held=set(), unfinished=False, ui=object())
    elif change == 'exit': e.stopping = True
    tick(.03)
    assert last_result(e)['outcome'] == 'refused' and observers[0].closed == 1


@pytest.mark.parametrize('field,value', [('activity', True), ('held_key_count', 1),
                                        ('active_contact_count', 1), ('coverage_complete', False),
                                        ('topology_generation', 2)])
def test_incomplete_or_active_input_never_becomes_clear(field, value):
    e, now, observers, queue, tick = setup(); queue(); tick(4)
    observers[0].result_hook = lambda r: replace(r, **{field: value})
    tick(.03)
    assert last_result(e)['outcome'] == 'observed' and not last_result(e)['input_sample_clear']
    assert observers[0].closed == 1


def test_queued_old_request_cannot_be_restamped_with_new_generation_or_settings_epoch():
    e, now, observers, queue, tick = setup()
    e.post(PREFLIGHT_JOB); e.post('settings', object())
    e.handle_job(*e.jobs.get_nowait()); tick(4)
    assert e.navigation_preflight is None and not observers


def test_in_place_level_change_after_post_cannot_be_adopted_when_job_starts():
    e, now, observers, queue, tick = setup(); e.post(PREFLIGHT_JOB)
    e.settings.level = 8
    e.handle_job(*e.jobs.get_nowait()); tick(4)
    assert e.navigation_preflight is None and not observers


def test_direct_settings_job_invalidates_an_older_queued_request():
    e, now, observers, queue, tick = setup(); e.post(PREFLIGHT_JOB)
    request = e.jobs.get_nowait()
    e.handle_job('settings', e.settings)
    e.handle_job(*request); tick(4)
    assert e.navigation_preflight is None and not observers


def test_f9_invalidates_a_queued_preflight_before_it_starts():
    e, now, observers, queue, tick = setup()
    e.post(PREFLIGHT_JOB); request=e.jobs.get_nowait()
    e.stop_action('F9'); e.handle_job(*request); tick(4)
    assert e.navigation_preflight is None and not observers


@pytest.mark.parametrize('field,value', [('measurement_only', False), ('active', True),
                                        ('loc_request', ('pending',)), ('loc_wanted', 'pending'),
                                        ('deferred', 'nav_stop_check'), ('keys', {103})])
def test_assist_active_or_pending_work_never_opens_observer(field, value):
    e, now, observers, queue, tick = setup(); setattr(e, field, value)
    queue(); tick(4)
    assert not observers and e.navigation_preflight is None


def test_helper_ui_is_reused_without_creating_sender_and_descriptor_swap_refuses():
    e, now, observers, queue, tick = setup()
    ui=object(); e.sender=SimpleNamespace(ui=ui, held=set(), unfinished=False)
    queue(); tick(4)
    assert observers[0].kwargs['helper_ui'] is ui
    e.sender.ui=object(); tick(.03)
    assert observers[0].closed == 1 and last_result(e)['outcome'] == 'refused'


def test_run_finally_closes_observer_when_base_engine_exits_with_error():
    e, now, observers, queue, tick = setup(); queue(); tick(4)
    def fail(): raise RuntimeError('fixture engine failure')
    e.run_hook = fail
    with pytest.raises(RuntimeError): e.run()
    assert observers[0].closed == 1 and last_result(e)['outcome'] == 'cancelled'
