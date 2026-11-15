"""A root budget additionally gates the unchanged crossing sender and child caps."""
from dataclasses import replace
import os
import threading

import pytest

from eql_automation.supervised_source_crossing import SupervisedSourceCrossingPolicy
from eql_automation.source_crossing_sender import run_checked_source_crossing_step
from eql_automation.uinput_watchdog import _EVENT
from test_itinerary_policy_budget import root_budget
from test_route_floor_commit import legacy
from test_route_step_sender import after_down
from test_source_crossing_corridor import h, collect_source_pair


def attach(h, *, declaration=None, budget=None, **limits):
    if budget is None:
        budget = root_budget(clock=h.clock, lock=h.corridor.lock, **limits)
        budget.advance(budget.stage, 'crossing', zone_id=68)
    old = h.policy
    h.policy = SupervisedSourceCrossingPolicy(h.corridor,
        declaration=old.declaration if declaration is None else declaration,
        gate=old.gate, owner_input=old.owner_input, expected_window=old.window,
        topology_generation=old.topology, check_current=old.check_current,
        journey_budget=budget)
    def step():
        command = h.corridor.next_command()
        return run_checked_source_crossing_step(h.sender, h.corridor, policy=h.policy,
            kind=command.kind, requested_seconds=command.requested_seconds,
            command_state_clear=lambda: True, pump=lambda: None)
    h.step = step
    return budget


def events(h):
    os.set_blocking(h.rd, False)
    try:
        try:
            data = os.read(h.rd, 65536)
        except BlockingIOError:
            data = b''
    finally:
        os.set_blocking(h.rd, True)
    return [(kind, key, value) for _, _, kind, key, value in _EVENT.iter_unpack(data)]


def test_crossing_root_reserves_the_actual_ticket_once_before_down(h):
    root = attach(h)
    old_floor = h.corridor.chain
    result = h.step()
    assert result['outcome'] == 'settling'
    reservation = h.policy._journey_reservation
    assert reservation.ticket is h.policy._authorization.ticket
    assert reservation.stage is root.stage
    assert h.policy.snapshot()['journey_budget']['reserved_pulses'] == 1
    assert root.snapshot()['reserved_maximum_hold'] == h.corridor.bounds.maximum_actual_hold
    emitted = events(h)
    assert emitted.count((1, 103, 1)) == 1 and (1, 103, 0) in emitted
    assert h.corridor.chain is old_floor and not h.sender.held


def test_stopped_pair_does_not_renew_root_reservation_allowance(h):
    root = attach(h, maximum_pulses=1)
    h.step()
    collect_source_pair(h)
    assert h.policy.reserved_hold == h.corridor.bounds.maximum_actual_hold
    with pytest.raises((RuntimeError, ValueError), match='budget'):
        h.step()
    assert events(h).count((1, 103, 1)) == 1
    assert root.snapshot()['reserved_pulses'] == 1 and not root.valid and not h.sender.held


@pytest.mark.parametrize('fault', ('root_hold', 'child_hold', 'wrong_stage'))
def test_root_and_child_limits_both_refuse_before_down(h, fault):
    if fault == 'root_hold':
        root = attach(h, maximum_total_hold=.05)
    elif fault == 'child_hold':
        root = attach(h, declaration=replace(h.policy.declaration, maximum_total_hold=.05))
    else:
        root = root_budget(clock=h.clock, lock=h.corridor.lock)
        attach(h, budget=root)
    with pytest.raises((RuntimeError, ValueError)):
        h.step()
    assert not events(h) and not h.sender.held
    assert root.snapshot()['reserved_pulses'] == 0 and h.policy.reserved_hold == 0.


@pytest.mark.parametrize('fault', ('cancel', 'stage', 'generation'))
def test_root_invalidated_after_down_releases_without_floor_commit(h, monkeypatch, fault):
    binding = [1]
    root = root_budget(clock=h.clock, lock=h.corridor.lock, binding=lambda:(binding[0],))
    root.advance(root.stage, 'crossing', zone_id=68)
    attach(h, budget=root)
    old_floor = h.corridor.chain
    def invalidate():
        if fault == 'cancel':
            root.cancel('root F9 during crossing')
        elif fault == 'stage':
            root.advance(root.stage, 'loading', zone_id=None)
        else:
            binding[0] += 1
    after_down(monkeypatch, invalidate)
    with pytest.raises((RuntimeError, ValueError)):
        h.step()
    emitted = events(h)
    assert (1, 103, 1) in emitted and (1, 103, 0) in emitted
    assert not h.sender.held and h.corridor.chain is old_floor
    assert root.snapshot()['reserved_pulses'] == 1 and not root.valid


@pytest.mark.parametrize('fault', ('clock', 'lock'))
def test_crossing_root_must_share_the_exact_sender_clock_and_stop_lock(h, fault):
    root = root_budget(clock=(lambda:h.clock()) if fault == 'clock' else h.clock,
        lock=threading.RLock() if fault == 'lock' else h.corridor.lock)
    with pytest.raises(ValueError):
        attach(h, budget=root)
    assert not events(h)


def test_crossing_policy_root_identity_cannot_be_replaced(h):
    root = attach(h)
    h.policy.journey_budget = None
    with pytest.raises((RuntimeError, ValueError), match='scope'):
        h.step()
    assert not events(h) and root.snapshot()['reserved_pulses'] == 0
