"""A retained full owner check must reject changes after read-only focus queries."""
from copy import copy
from dataclasses import replace
import time
from types import SimpleNamespace

import pytest

from eql_automation.fixed_route_follower import RouteHalt
from eql_automation.g2_safety_provider import focused_game_identity
from eql_automation.supervised_source import SupervisedSourcePolicy
import eql_automation.supervised_source as module
from test_route_floor_commit import legacy
from test_source_motion import f


def policy_with_owner_check(f, events, *, budget=None):
    """Use actual input/log/model providers behind the policy's owner callback."""
    f.real = False
    f.now = time.monotonic()
    original = f.policy
    owner, generation = f.owner, f.generation
    queued, sampled = [], []
    sample = original.owner_input.sample

    def sample_queued():
        observed = sample()
        event = queued.pop(0) if queued else False
        sampled.append(event)
        return replace(observed, activity=observed.activity or event)

    original.owner_input.sample = sample_queued

    def current():
        events.append('owner')
        if (f.owner != owner or f.generation != generation or f.mode != 'measurement'
                or focused_game_identity(f.gate) != original.window):
            raise RouteHalt('Owner scope changed after focus')
        original.ledger.model.check_policy(original.ledger.observer.policy)
        observation = original.owner_input.sample()
        veto = original.log_veto.poll()
        if not observation.clear_at(f.clock()) or not veto.continuity_available or veto.reason is not None:
            raise RouteHalt('Retained owner callback saw queued input or a log veto')

    result = SupervisedSourcePolicy(original.ledger, declaration=original.declaration,
        gate=original.gate, owner_input=original.owner_input, log_veto=original.log_veto,
        expected_window=original.window, topology_generation=original.topology,
        check_current=current, journey_budget=budget, release_deadline=f.now + .2)
    f.policy = result
    events.clear()
    sampled.clear()
    return result, queued, sampled


def record_boundaries(f, monkeypatch, events, *, boundary=None, mutate=lambda: None):
    check, focus = f.ledger._check, module.focused_game_identity
    changed = []

    def change_once(name):
        if boundary == name and not changed:
            changed.append(name)
            mutate()

    def ledger_check():
        events.append('ledger')
        result = check()
        change_once('ledger')
        return result

    def focused(gate):
        events.append('focus')
        result = focus(gate)
        change_once('focus')
        return result

    monkeypatch.setattr(f.ledger, '_check', ledger_check)
    monkeypatch.setattr(module, 'focused_game_identity', focused)
    return changed


def test_one_full_owner_check_follows_read_only_focus_without_changing_time_origin(f, monkeypatch):
    events = []
    policy, queued, sampled = policy_with_owner_check(f, events)
    record_boundaries(f, monkeypatch, events)
    before = policy.last_at
    f.now += .01
    began = policy._check()
    assert events == ['ledger', 'focus', 'owner', 'ledger']
    assert len(sampled) == 1 and sampled == [False] and queued == []
    assert before < began == policy.last_at == f.now
    assert policy.started == before and policy._authorization is None
    assert f.drain_events() == () and not f.sender.held


@pytest.mark.parametrize('boundary', ('ledger', 'focus'))
@pytest.mark.parametrize('fault', ('owner', 'generation', 'assist', 'focus', 'window',
    'process', 'ledger', 'check_current', 'input', 'attack', 'model', 'deadline'))
def test_final_owner_boundary_rejects_late_changes_without_publishing_a_scene(
        f, monkeypatch, tmp_path, boundary, fault):
    events = []
    policy, queued, sampled = policy_with_owner_check(f, events)
    before = policy.last_at
    f.now += .01

    def mutate():
        if fault == 'owner':
            f.owner = ('replaced-owner',)
        elif fault == 'generation':
            f.generation += 1
        elif fault == 'assist':
            f.mode = 'assist'
        elif fault == 'focus':
            f.focus = False
        elif fault == 'window':
            f.gate.windows = lambda: [SimpleNamespace(id=43)]
        elif fault == 'process':
            f.gate.game_session = lambda: {'pid': 11, 'start_ticks': '101'}
        elif fault == 'ledger':
            policy.ledger = copy(f.ledger)
        elif fault == 'check_current':
            policy.check_current = lambda: None
        elif fault == 'input':
            queued.append(True)
        elif fault == 'attack':
            f.append('Training dummy hits YOU for 2 points of damage.')
        elif fault == 'model':
            (tmp_path / 'EQGraphics.dll').write_bytes(b'changed')
        else:
            f.now = policy.release_deadline + .001

    changed = record_boundaries(f, monkeypatch, events, boundary=boundary, mutate=mutate)
    with pytest.raises((RuntimeError, ValueError)):
        policy._check()
    assert changed == [boundary]
    assert events[0] == 'ledger' and 'focus' in events
    assert policy.last_at == before and policy._scene is None and policy._authorization is None
    assert f.ledger.phase == 'ready' and f.ledger.steps == 0
    assert f.drain_events() == () and not f.sender.held
    if fault == 'input':
        assert queued == [] and sampled == [True]
    elif fault == 'attack':
        assert policy.log_veto.poll().reason is not None


@pytest.mark.parametrize('hazard', ('input', 'attack'))
def test_existing_hazards_stay_queued_until_retained_owner_check(f, monkeypatch, hazard):
    events = []
    policy, queued, sampled = policy_with_owner_check(f, events)
    record_boundaries(f, monkeypatch, events)
    before = policy.last_at
    if hazard == 'input':
        queued.append(True)
    else:
        f.append('Training dummy hits YOU for 2 points of damage.')
    with pytest.raises(RouteHalt, match='queued input or a log veto'):
        policy._check()
    assert events == ['ledger', 'focus', 'owner']
    assert policy.last_at == before and policy._authorization is None
    if hazard == 'input':
        assert sampled == [True] and queued == []
    else:
        assert policy.log_veto.poll().reason is not None
    assert f.drain_events() == () and not f.sender.held


@pytest.mark.parametrize('f', ['butcher'], indirect=True)
def test_root_budget_checks_still_bracket_owner_and_focus_callbacks(f, monkeypatch):
    from test_itinerary_policy_budget import root_budget
    events = []
    budget = root_budget(clock=f.clock, lock=f.ledger.lock)
    policy, _, _ = policy_with_owner_check(f, events, budget=budget)
    record_boundaries(f, monkeypatch, events)
    actual = budget.check

    def check_root(*args, **kwargs):
        events.append('root')
        return actual(*args, **kwargs)

    monkeypatch.setattr(budget, 'check', check_root)
    started, expiry = budget.started, budget.expires_at
    policy._check()
    assert events == ['root', 'ledger', 'focus', 'owner', 'ledger', 'root']
    assert (budget.started, budget.expires_at) == (started, expiry)
    assert budget.snapshot()['reserved_pulses'] == 0
    assert policy._authorization is None and f.drain_events() == ()
