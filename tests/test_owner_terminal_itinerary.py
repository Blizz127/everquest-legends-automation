"""Terminal wrapper dispatch with real owner/root accounting and protocol stubs.

The transfer producer and camp adapter are spies here: these tests cover owner
handoff ordering, not source arrival or combat. The separate terminal runtime
and retained-engine camp adapter suites cover those implementations. No input
is sent and no game installation is accessed.
"""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from eql_automation.zone_itinerary_budget import load_terminal_camp
from test_owner_zone_itinerary import Base, owner, start


class TerminalRun:
    """Explicit terminal-transfer protocol; never fabricates a real arrival token."""
    def __init__(self, scope):
        self.root, self.journey = scope.root, scope.journey
        self.phase, self.closed, self.busy = 'terminal_ready', False, False
        self.candidates = (object(),)
        self.token = object()
        self.terminal_transfer = None
        self.transfer_calls, self.cancellations = [], []
        self.transfer_hook = lambda: None

    def tick(self):
        pass

    def transfer_terminal_arrival(self, *, candidates):
        self.transfer_calls.append(candidates)
        assert candidates is self.candidates
        for phase in ('arrival', 'complete'):
            self.root.advance(self.root.stage, phase, zone_id=58)
        self.terminal_transfer = self.token
        self.phase, self.closed = 'terminal_transferred', True
        self.transfer_hook()
        return self.token

    def cancel(self, reason):
        self.cancellations.append(str(reason))
        if not self.closed:
            self.phase = 'stopped'

    def release(self):
        assert not self.busy
        self.closed = True


@pytest.fixture
def terminal_owner(owner, monkeypatch):
    s = owner
    catalog = {'Butcherblock Mountains': 68, 'The Greater Faydark': 54, 'Clan Crushbone': 58}
    terminal = load_terminal_camp('slave-mines', zone_catalog=catalog)
    declaration = replace(s.plan.declaration,
        record_id='synthetic-owner-terminal-itinerary', terminal_camp=terminal)
    # Declare the terminal before starting: no active root or pinned plan edits.
    s.plan = replace(s.plan, declaration=declaration)
    s.request = dict(s.request, itinerary_id='butcher-gfay-crushbone-slave-mines')
    start(s)
    e = s.engine
    scope = e.zone_itinerary_owner
    assert scope is not None and scope.root.declaration is declaration
    e.supervised_motion = None
    for phase, zone in (
        ('crossing', 68), ('loading', None), ('arrival', 54),
        ('bootstrap', 54), ('walking', 54), ('crossing', 54),
        ('loading', None), ('arrival', 58), ('bootstrap', 58), ('walking', 58),
    ):
        scope.root.advance(scope.root.stage, phase, zone_id=zone)
    s.tracker.reader.zone_id = 58
    s.tracker.reader.zone_display_name = 'Clan Crushbone'
    scope.journey.phase = 'zone_itinerary'
    scope.journey.destination_id = terminal.destination_id
    s.scope, s.run = scope, TerminalRun(scope)
    e.zone_itinerary_run = s.run
    s.continued = []
    s.adapter_result = dict(phase='camp', camp_started=True, simulated_adapter=True)

    def adapter(engine, token, clock):
        # The wrapper must detach both old slots before any camp callback.
        assert engine is e and token is s.run.token and clock is s.clock
        assert e.zone_itinerary_owner is None and e.zone_itinerary_run is None
        assert scope.closed and s.run.closed
        assert e._terminal_itinerary_finishing is not None
        assert e.journey is scope.journey and e.cancel_generation == scope.generation
        assert scope.root.stage.kind == 'terminal_camp' and scope.root.stage.phase == 'complete'
        s.continued.append((engine, token, clock))
        return s.adapter_result

    import eql_automation.owner_itinerary_camp_arrival as arrival
    monkeypatch.setattr(arrival, 'continue_itinerary_camp_arrival', adapter)
    return s


def test_terminal_dispatch_detaches_navigation_and_preserves_exact_journey_and_token(terminal_owner):
    s = terminal_owner
    e, scope, run = s.engine, s.scope, s.run
    deadline, generation = scope.root.expires_at, e.cancel_generation
    result = e._finish_terminal_itinerary(run)
    assert result is s.adapter_result
    assert run.transfer_calls == [run.candidates]
    assert s.continued == [(e, run.token, s.clock)]
    assert e.zone_itinerary_owner is None and e.zone_itinerary_run is None and scope.closed
    assert e.journey is scope.journey and e.cancel_generation == generation
    assert e._terminal_itinerary_finishing is None
    assert scope.root.expires_at == deadline
    assert len(e.delegated) == 1 and e.jobs.empty() and not e.sender.held
    # Neither a second explicit finish nor a later engine tick posts another job.
    assert e._finish_terminal_itinerary(run) is None
    e.autopilot_tick(s.now)
    assert len(s.continued) == 1 and len(run.transfer_calls) == 1
    assert len(e.delegated) == 1 and e.cancel_generation == generation and e.jobs.empty()


def test_terminal_ready_engine_tick_dispatches_adapter_once(terminal_owner):
    s = terminal_owner
    for _ in range(2):
        s.engine.autopilot_tick(s.now)
    assert s.continued == [(s.engine, s.run.token, s.clock)]
    assert len(s.run.transfer_calls) == len(s.engine.delegated) == 1
    assert s.engine.cancel_generation == s.scope.generation and s.engine.jobs.empty()


def at_boundary(s, monkeypatch, boundary, callback):
    if boundary == 'owner_check':
        original = s.scope.check
        called = []

        def check():
            if not called:
                called.append(True)
                callback()
            return original()

        monkeypatch.setattr(s.scope, 'check', check)
    elif boundary == 'transfer':
        s.run.transfer_hook = callback
    elif boundary == 'adapter':
        import eql_automation.owner_itinerary_camp_arrival as arrival
        original = arrival.continue_itinerary_camp_arrival

        def adapter(*args):
            callback()
            return original(*args)

        monkeypatch.setattr(arrival, 'continue_itinerary_camp_arrival', adapter)
    else:
        raise AssertionError(boundary)


@pytest.mark.parametrize('boundary', ('owner_check', 'transfer'))
def test_nested_terminal_finish_cannot_transfer_or_dispatch_twice(terminal_owner, monkeypatch, boundary):
    s = terminal_owner
    nested = []

    def finish():
        marker = s.engine._terminal_itinerary_finishing
        assert marker is not None
        nested.append(s.engine._finish_terminal_itinerary(s.run))
        assert s.engine._terminal_itinerary_finishing is marker

    at_boundary(s, monkeypatch, boundary, finish)
    result = s.engine._finish_terminal_itinerary(s.run)
    assert result is s.adapter_result and nested == [None]
    assert s.run.transfer_calls == [s.run.candidates]
    assert s.continued == [(s.engine, s.run.token, s.clock)]
    assert s.engine._terminal_itinerary_finishing is None
    assert s.engine.cancel_generation == s.scope.generation
    assert len(s.engine.delegated) == 1 and s.engine.jobs.empty() and not s.engine.sender.held


@pytest.mark.parametrize('boundary', ('owner_check', 'transfer', 'adapter'))
def test_nested_tick_cannot_service_base_or_navigation_during_adoption(terminal_owner, monkeypatch, boundary):
    s = terminal_owner
    base_calls, child_ticks, nested = [], [], []
    monkeypatch.setattr(Base, 'autopilot_tick', lambda self, now: base_calls.append(now))
    monkeypatch.setattr(s.run, 'tick', lambda: child_ticks.append(True))

    def tick():
        marker = s.engine._terminal_itinerary_finishing
        assert marker is not None
        nested.append(s.engine.autopilot_tick(s.now))
        assert s.engine._terminal_itinerary_finishing is marker
        assert not base_calls and not child_ticks

    at_boundary(s, monkeypatch, boundary, tick)
    assert s.engine._finish_terminal_itinerary(s.run) is s.adapter_result
    assert nested == [None] and len(s.continued) == len(s.run.transfer_calls) == 1
    assert not base_calls and not child_ticks
    assert s.engine._terminal_itinerary_finishing is None
    s.engine.autopilot_tick(s.now)
    assert base_calls == [s.now] and not child_ticks
    assert len(s.continued) == 1 and s.engine.jobs.empty() and not s.engine.sender.held


def interrupt(s, fault):
    e = s.engine
    if fault == 'f8':
        e.handle_job('arm', e.cancel_generation)
    elif fault == 'f9':
        e.stop_action('Late owner F9 during terminal handoff')
    elif fault == 'window':
        s.gate.windows = lambda: [SimpleNamespace(id=17)]
    elif fault == 'process':
        s.gate.game_session = lambda: dict(pid=18, start_ticks='19')
    elif fault == 'job':
        e.jobs.put(('heal', None))
    elif fault == 'owner':
        s.scope.closed = True
    else:
        raise AssertionError(fault)


@pytest.mark.parametrize('fault', ('f8', 'f9', 'window', 'process', 'job', 'owner'))
@pytest.mark.parametrize('boundary', ('transfer', 'final_owner_check'))
def test_late_owner_changes_prevent_terminal_camp_dispatch(terminal_owner, fault, boundary):
    s = terminal_owner
    e, scope, run = s.engine, s.scope, s.run
    fired = []

    def change():
        fired.append(fault)
        interrupt(s, fault)

    if boundary == 'transfer':
        run.transfer_hook = change
    else:
        original = scope.ui.fileno

        def descriptor():
            value = original()
            # root.check invokes the same binding reader. Inject only at the
            # final owner binding, after the root's own chronological checks.
            if run.phase == 'terminal_transferred' and not scope.root._checking and not fired:
                change()
            return value

        scope.ui.fileno = descriptor
    with pytest.raises(ValueError):
        e._finish_terminal_itinerary(run)
    assert fired == [fault] and not s.continued
    assert len(run.transfer_calls) == 1
    assert e.zone_itinerary_owner is None and e.zone_itinerary_run is None and run.closed
    assert e.journey is None and e.journey_last_result['phase'] == 'stopped'
    assert e.cancel_generation == scope.generation + 1
    assert e._terminal_itinerary_finishing is None
    assert (e._journey_assist is not None) == (fault == 'f8')
    assert len(e.delegated) == 1 and not e.sender.held
    assert e.jobs.qsize() == (1 if fault == 'job' else 0)


@pytest.mark.parametrize('fault', ('f8', 'f9', 'window', 'process'))
def test_final_queue_callback_cannot_change_owner_before_terminal_dispatch(terminal_owner, monkeypatch, fault):
    s = terminal_owner
    e, scope, run = s.engine, s.scope, s.run
    final_owner_checked, fired, attempts = [], [], []
    original_check, original_empty = scope.check, e.jobs.empty

    def check():
        value = original_check()
        if run.phase == 'terminal_transferred':
            final_owner_checked.append(True)
        return value

    def empty():
        value = original_empty()
        # The explicit queue check after owner.check returns must not appear
        # after volatile generation/window tests inside the final conditional.
        if final_owner_checked and not fired:
            fired.append(fault)
            interrupt(s, fault)
        return value

    def adapter(*args):
        attempts.append(args)
        return s.adapter_result

    import eql_automation.owner_itinerary_camp_arrival as arrival
    monkeypatch.setattr(scope, 'check', check)
    monkeypatch.setattr(e.jobs, 'empty', empty)
    monkeypatch.setattr(arrival, 'continue_itinerary_camp_arrival', adapter)
    with pytest.raises(ValueError):
        e._finish_terminal_itinerary(run)
    assert fired == [fault] and final_owner_checked and not attempts
    assert len(run.transfer_calls) == 1 and run.closed
    assert e.zone_itinerary_owner is None and e.zone_itinerary_run is None and e.journey is None
    assert e.cancel_generation == scope.generation + 1
    assert (e._journey_assist is not None) == (fault == 'f8')
    assert e._terminal_itinerary_finishing is None
    assert len(e.delegated) == 1 and e.jobs.empty() and not e.sender.held


@pytest.mark.parametrize('action', ('none', 'f8', 'f9'))
def test_adapter_failure_after_detachment_stops_preserved_journey(terminal_owner, monkeypatch, action):
    s = terminal_owner
    e, scope, run = s.engine, s.scope, s.run
    called = []

    def fail(engine, token, clock):
        assert engine is e and token is run.token and clock is s.clock
        assert e.zone_itinerary_run is None and e.zone_itinerary_owner is None and scope.closed
        assert e.journey is scope.journey
        called.append(token)
        if action != 'none':
            interrupt(s, action)
        raise ValueError('Synthetic terminal adapter refusal')

    import eql_automation.owner_itinerary_camp_arrival as arrival
    monkeypatch.setattr(arrival, 'continue_itinerary_camp_arrival', fail)
    with pytest.raises(ValueError, match='Synthetic terminal adapter refusal'):
        e._finish_terminal_itinerary(run)
    assert called == [run.token]
    assert e.journey is None and e.journey_last_result['phase'] == 'stopped'
    assert e.cancel_generation == scope.generation + 1
    assert e._terminal_itinerary_finishing is None
    assert (e._journey_assist is not None) == (action == 'f8')
    assert e.zone_itinerary_run is None and e.zone_itinerary_owner is None
    assert len(e.delegated) == 1 and e.jobs.empty() and not e.sender.held


def test_foreign_returned_transfer_token_cannot_reach_camp_adapter(terminal_owner):
    s = terminal_owner
    s.run.transfer_hook = lambda: setattr(s.run, 'terminal_transfer', object())
    with pytest.raises(ValueError, match='ownership changed'):
        s.engine._finish_terminal_itinerary(s.run)
    assert not s.continued and len(s.run.transfer_calls) == 1
    assert s.engine.journey is None and s.engine.zone_itinerary_run is None
    assert s.engine.cancel_generation == s.scope.generation + 1
    assert s.engine._terminal_itinerary_finishing is None
    assert s.engine.jobs.empty() and len(s.engine.delegated) == 1


@pytest.mark.parametrize('fault', ('busy', 'closed', 'phase', 'root', 'journey'))
def test_ineligible_terminal_producer_never_transfers(terminal_owner, fault):
    s = terminal_owner
    e, run = s.engine, s.run
    if fault == 'busy':
        run.busy = True
    elif fault == 'closed':
        run.closed = True
    elif fault == 'phase':
        run.phase = 'source'
    elif fault == 'root':
        run.root = object()
    else:
        run.journey = replace(run.journey)
    with pytest.raises(ValueError, match='Current terminal itinerary arrival'):
        e._finish_terminal_itinerary(run)
    assert not run.transfer_calls and not s.continued
    assert e.journey is None and e.cancel_generation == s.scope.generation + 1
    assert e._terminal_itinerary_finishing is None
    run.busy = False
    e._cleanup_zone_itinerary()
    assert e.zone_itinerary_run is None and e.zone_itinerary_owner is None
    assert len(e.delegated) == 1 and e.jobs.empty() and not e.sender.held


@pytest.mark.parametrize('action', ('f8', 'f9'))
def test_terminal_status_and_busy_cancellation_keep_third_target_and_record_id(terminal_owner, action):
    s = terminal_owner
    e, scope, run = s.engine, s.scope, s.run
    status = e.autopilot_payload()['zone_itinerary']
    assert status['record_id'] == 'synthetic-owner-terminal-itinerary'
    assert status['leg'] == status['legs'] == 3
    assert status['target_kind'] == 'terminal_camp' and status['stage'] == 'walking'
    run.busy = True
    interrupt(s, action)
    assert e.zone_itinerary_owner is None and e.zone_itinerary_run is run
    stopped = e.autopilot_payload()
    assert stopped['state'] == 'stopping'
    assert stopped['zone_itinerary']['record_id'] == status['record_id']
    assert stopped['zone_itinerary']['leg'] == stopped['zone_itinerary']['legs'] == 3
    assert stopped['zone_itinerary']['stage'] == 'stopping'
    assert (e._journey_assist is not None) == (action == 'f8')
    run.busy = False
    e._cleanup_zone_itinerary()
    assert e.zone_itinerary_run is None and e._zone_itinerary_stopping is None
    assert 'zone_itinerary' not in e.autopilot_payload()
    assert not s.continued and len(e.delegated) == 1 and e.jobs.empty()
