"""Source runtime: actual pipe pulses/log polling, synthetic game feedback."""
from queue import Queue
from types import SimpleNamespace
import json
import time

import pytest

from eql_automation.location_hotkey import OwnerLocationHotkey
from eql_automation.owner_source_runtime import OwnerSourceRuntime
from eql_automation.owner_zone_tracker import ZoneReaderLease
from eql_automation.source_walk_driver import SourceWalkDriver
from test_source_motion import f, legacy
from test_route_step_sender import after_down


def setup(f, tmp_path, monkeypatch, *, stop=None, elevated=False):
    tracker = SimpleNamespace(reader=f.reader, owner_binding=f.owner, check_binding=lambda:f.owner)
    lease = ZoneReaderLease(tracker)
    tracker.lease = lease
    config = tmp_path/'hotbutton.ini'
    config.write_text('synthetic configured hotbutton')
    binding = OwnerLocationHotkey.configured('F4', confirmation_id='synthetic-runtime', configuration_paths=(config,))
    p = dict(sender=f.sender, lease=lease, observer=f.policy.owner_input, binding=binding,
        veto=f.policy.log_veto, window=(42, 10, 100), topology=1, busy=False,
        source_runtime=None, corridor_runtime=None, driver=None,
        trial_id='synthetic-source-runtime', continuation=dict(scope='local_trial'))
    e = SimpleNamespace(sender=f.sender, gate=f.gate, g0_stop_lock=f.ledger.lock,
        route_session_driver=None, cancelled=False, jobs=Queue(), zone_loading_until=0.,
        pump=lambda:None, _route_idle=lambda:True)
    def current(pending):
        assert pending is p
        if e.cancelled or f.mode != 'measurement' or f.generation != 1:
            raise ValueError('Owner source runtime cancelled')
    e._trial_common_current = current
    r = OwnerSourceRuntime(e, p, SourceWalkDriver(f.ledger), clock=f.clock, local_wall_clock=f.wall)
    p['source_runtime'] = r
    e.autopilot_tick = lambda now:r.tick()
    def cancel(reason):
        e.cancelled = True
        r.cancel(reason)
    e._cancel_trial = cancel
    f.sender.gate = f.gate
    state = SimpleNamespace(y=2., z=2.7, pulses=0, stopped=False, elevated=elevated)

    def down():
        if stop == 'movement' and 103 in f.sender.held:
            state.stopped = True
            cancel('F9 during movement DOWN')
        elif r.collector is not None and r.collector.phase == 'requesting':
            if stop == 'location':
                state.stopped = True
                cancel('F9 during position DOWN')
                return
            f.now = f.clock()
            z = 3.1 if state.elevated else state.z
            f.append(f'Your Location is {state.y}, 4, {z}')
    after_down(monkeypatch, down)
    import eql_automation.owner_source_runtime as module
    real_step = module.run_checked_source_step
    positions = iter((2.2, 2.4, 2.6, 2.8, 3., 3.15, 3.35, 3.55, 3.75))
    def step(*args, **kwargs):
        seal = real_step(*args, **kwargs)
        state.y = next(positions)
        state.z = 3.01 if state.y > 3.3 else 2.7
        state.pulses += 1
        return seal
    monkeypatch.setattr(module, 'run_checked_source_step', step)
    return r, e, state


def finish(f, r, *, until=None):
    deadline = time.monotonic()+25
    while r.phase != 'complete' and time.monotonic() < deadline:
        f.now = f.clock()
        r.tick()
        f.drain_events()
        if until is not None and until():
            return
        time.sleep(.01)
    assert r.phase == 'complete', r.snapshot()


@pytest.mark.parametrize('f', ['step'], indirect=True)
def test_runtime_owns_each_reply_partial_transfer_and_resumed_walk(f, tmp_path, monkeypatch):
    r, e, state = setup(f, tmp_path, monkeypatch)
    finish(f, r)
    record = r.snapshot()
    outcomes = [v['outcome'] for v in record['executor_events'] if v['kind'] == 'source_acknowledgment']
    assert outcomes == ['approach']*6+['in_transfer', 'landed', 'walk']
    assert state.pulses == 9 and record['completed_movements'] == 9
    assert len(record['stopped_pairs']) == 9
    assert r.policy.ledger is f.ledger and r.policy.reserved_hold == pytest.approx(.45)
    assert not f.sender.held and f.sender._eql_route_operation is None
    assert r.lease.active and r.reader is f.reader  # engine owns final cleanup
    assert not record['real_client_accepted']
    json.dumps(record, allow_nan=False)
    count = len(f.events)
    r.tick()
    assert len(f.drain_events()) == count


@pytest.mark.parametrize('stop', ('movement', 'location'))
@pytest.mark.parametrize('f', ['step'], indirect=True)
def test_runtime_stop_during_down_releases_and_never_rearms(f, tmp_path, monkeypatch, stop):
    r, e, state = setup(f, tmp_path, monkeypatch, stop=stop)
    old = f.ledger.chain
    with pytest.raises((RuntimeError, ValueError)):
        finish(f, r)
    assert state.stopped and r.phase == 'stopped' and f.ledger.chain is old
    assert not f.sender.held and f.sender._eql_route_operation is None
    before = len(f.drain_events())
    with pytest.raises((RuntimeError, ValueError)):
        r.tick()
    assert len(f.drain_events()) == before


@pytest.mark.parametrize('f', ['step'], indirect=True)
def test_runtime_settling_reuses_receipt_without_movement(f, tmp_path, monkeypatch):
    r, e, state = setup(f, tmp_path, monkeypatch, elevated=True)
    finish(f, r, until=lambda:r.phase == 'settling')
    seal, started = r.seal, r.policy.started
    assert state.pulses == 1 and f.ledger.steps == 0
    state.elevated = False
    finish(f, r, until=lambda:r.phase == 'ready')
    assert state.pulses == 1 and f.ledger.steps == 1 and r.policy.started == started
    assert r.seal is None and r.transfer is None
    assert len(r.pairs) == 2 and r.pairs[0]['released_at'] == r.pairs[1]['released_at'] == seal.receipt.up_completed_at


@pytest.mark.parametrize('change', ('zone', 'mode', 'lease', 'sender'))
@pytest.mark.parametrize('f', ['step'], indirect=True)
def test_runtime_refuses_changed_scope_before_next_input(f, tmp_path, monkeypatch, change):
    r, e, state = setup(f, tmp_path, monkeypatch)
    if change == 'zone':f.reader.zone_generation += 1
    elif change == 'mode':f.mode = 'assist'
    elif change == 'lease':r.lease.active = False
    else:e.sender = object()
    with pytest.raises((RuntimeError, ValueError)):
        r.tick()
    assert not f.drain_events() and state.pulses == 0


@pytest.mark.parametrize('f', ['step'], indirect=True)
def test_stop_in_new_pair_final_clock_does_not_restore_runtime_phase(f, tmp_path, monkeypatch):
    import inspect
    r, e, state = setup(f, tmp_path, monkeypatch)
    r.tick()
    old = r.collector
    original = r.check_current
    def check():
        original()
        caller = inspect.currentframe().f_back
        if caller.f_code.co_name == 'check' and caller.f_locals.get('self') is not old:
            f.clock_hook = lambda:r.cancel('OFF during new collector final clock')
    monkeypatch.setattr(r, 'check_current', check)
    with pytest.raises((RuntimeError, ValueError)):
        r._new_pair()
    assert r.phase == 'stopped' and f.ledger.phase == 'stopped' and r.collector is old
