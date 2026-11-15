from dataclasses import replace
import threading

import pytest

from eql_automation.supervised_source import SupervisedSourcePolicy
from test_journey_input_budget import budget
from test_source_motion import f
from test_route_floor_commit import legacy
from test_route_step_sender import after_down


def attach(f, b):
    p = f.policy
    f.policy = SupervisedSourcePolicy(f.ledger, declaration=p.declaration, gate=p.gate,
        owner_input=p.owner_input, log_veto=p.log_veto, expected_window=p.window,
        topology_generation=p.topology, check_current=p.check_current, journey_budget=b)


def shared(f, **limits):
    b, _ = budget(clock=f.clock, lock=f.ledger.lock, binding=lambda:(f.generation,), **limits)
    attach(f, b)
    return b


def test_source_sender_charges_once_and_rechecks_same_reservation_during_hold(f):
    b = shared(f)
    seal = f.run()
    assert b.snapshot()['reserved_pulses'] == 1
    assert b.snapshot()['reserved_maximum_hold'] == .05
    assert f.policy._journey_reservation.ticket is seal.ticket
    assert not f.sender.held
    assert (1, 103, 1) in f.drain_events() and (1, 103, 0) in f.events


@pytest.mark.parametrize('limits', ({'maximum_pulses':1}, {'maximum_total_hold':.075},
                                   {'maximum_displacement_reserve':1.5}))
def test_replacement_child_policy_cannot_reset_whole_trip_allowance(f, limits):
    b = shared(f, **limits)
    seal = f.run(); pair = f.replies(seal); f.ledger.acknowledge_stopped(seal, *pair)
    # A fresh child has zero local hold reservations; its parent is unchanged.
    attach(f, b)
    assert f.policy.reserved_hold == 0.
    with pytest.raises((ValueError, RuntimeError), match='budget'):f.run()
    events = f.drain_events()
    assert events.count((1,103,1)) == 1 and not f.sender.held
    assert b.snapshot()['reserved_pulses'] == 1


def test_parent_cancellation_after_down_releases_without_publishing_floor(f, monkeypatch):
    b = shared(f); old_floor = f.ledger.chain
    after_down(monkeypatch, lambda:b.cancel('whole trip F9'))
    with pytest.raises((ValueError, RuntimeError)):f.run()
    events = f.drain_events()
    assert (1,103,1) in events and (1,103,0) in events
    assert not f.sender.held and f.ledger.chain is old_floor
    assert f.ledger.steps == 0 and b.snapshot()['reserved_pulses'] == 1


@pytest.mark.parametrize('fault', ('lock', 'clock'))
def test_parent_must_share_exact_sender_clock_and_stop_lock(f, fault):
    b, _ = budget(clock=(lambda:f.clock()) if fault=='clock' else f.clock,
                  lock=threading.RLock() if fault=='lock' else f.ledger.lock)
    with pytest.raises(ValueError):attach(f,b)
    assert not f.drain_events()


def test_parent_cannot_replace_existing_child_hold_limit(f):
    b = shared(f)
    p = f.policy
    f.policy = SupervisedSourcePolicy(f.ledger,
        declaration=replace(p.declaration, maximum_total_hold=.025), gate=p.gate,
        owner_input=p.owner_input, log_veto=p.log_veto, expected_window=p.window,
        topology_generation=p.topology, check_current=p.check_current, journey_budget=b)
    with pytest.raises((ValueError, RuntimeError), match='hold budget'):f.run()
    assert not f.drain_events() and b.snapshot()['reserved_pulses'] == 0


def test_replacing_parent_with_fresh_allowance_cannot_rearm_source(f):
    b = shared(f)
    other, _ = budget(clock=f.clock, lock=f.ledger.lock)
    f.policy.journey_budget = other
    with pytest.raises((ValueError, RuntimeError)):f.run()
    assert not f.drain_events()
    assert b.snapshot()['reserved_pulses'] == other.snapshot()['reserved_pulses'] == 0
