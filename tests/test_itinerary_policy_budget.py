"""Root itinerary accounting through real sender pipes and synthetic game state."""
from dataclasses import replace
import threading

import pytest

from eql_automation.source_destinations import destination_spec
from eql_automation.supervised_camp_probe import SupervisedCampProbeScope
from eql_automation.supervised_source import SupervisedSourcePolicy
from eql_automation.zone_itinerary_budget import (
    ZoneItineraryBudget, ZoneItineraryDeclaration, ZoneItineraryLeg)
from test_camp_floor_checkpoint import checkpoint
from test_motion_collection import retained
from test_owner_camp_position import camp
from test_owner_camp_probe import finish
from test_owner_journey_runtime import h
from test_route_floor_commit import legacy
from test_route_step_sender import after_down
from test_source_motion import f
from test_supervised_camp_probe import ready, no_movement


def root_budget(*, clock, lock, binding=lambda:(1,), **limits):
    # Catalog/hash fixtures establish accounting stages only; no live arrival
    # or crossing geometry is claimed by these policy integration tests.
    legs = []
    for identifier, source_name, destination_zone, destination_id, destination_name in (
            ('butcher-gfay-crossing', 'Butcherblock Mountains', 'gfaydark', 54, 'The Greater Faydark'),
            ('gfay-butcher-crushbone-crossing', 'The Greater Faydark', 'crushbone', 58, 'Clan Crushbone')):
        spec = destination_spec(identifier)
        legs.append(ZoneItineraryLeg(identifier, spec.zone, spec.zone_id, source_name,
            destination_zone, destination_id, destination_name, spec.file_sha256,
            'a'*64, 'b'*64, 'c'*64))
    declaration = ZoneItineraryDeclaration('synthetic-policy-itinerary', tuple(legs),
                                          120., 8, 1.6, 100.)
    return ZoneItineraryBudget(replace(declaration, **limits), clock=clock,
        stop_lock=lock, owner_binding=(1,), binding_reader=binding)


def bootstrap_stage(budget):
    for phase, zone_id in (('crossing', 68), ('loading', None), ('arrival', 54), ('bootstrap', 54)):
        budget.advance(budget.stage, phase, zone_id=zone_id)


def source_policy(f, budget, *, declaration=None):
    p = f.policy
    f.policy = SupervisedSourcePolicy(f.ledger,
        declaration=p.declaration if declaration is None else declaration,
        gate=p.gate, owner_input=p.owner_input, log_veto=p.log_veto,
        expected_window=p.window, topology_generation=p.topology,
        check_current=p.check_current, journey_budget=budget)


def probe_policy(ready, budget):
    h, p, runtime, policy = ready
    original = policy.scope
    runtime.phase = 'collect_start'
    scope = SupervisedCampProbeScope(runtime, declaration=original.declaration,
        monitor=original.monitor, gate=original.gate, expected_window=original.window,
        log_veto=original.log_veto, check_current=original.current,
        started_at=original.started_at, expires_at=original.expires_at, journey_budget=budget)
    runtime.policy = scope.policy(runtime.transaction)
    runtime.phase = 'pulse'
    return scope


def test_source_policy_charges_root_once_before_down_without_wrapper(f):
    budget = root_budget(clock=f.clock, lock=f.ledger.lock)
    source_policy(f, budget)
    seal = f.run()
    assert type(f.policy) is SupervisedSourcePolicy
    assert f.policy._journey_reservation.ticket is seal.ticket
    assert f.policy._journey_reservation.stage is budget.stage
    assert budget.snapshot()['reserved_pulses'] == 1
    assert budget.snapshot()['reserved_maximum_hold'] == .05
    assert not f.sender.held


def test_new_source_child_cannot_reset_root_allowance(f):
    budget = root_budget(clock=f.clock, lock=f.ledger.lock, maximum_pulses=1)
    source_policy(f, budget)
    seal = f.run()
    f.ledger.acknowledge_stopped(seal, *f.replies(seal))
    source_policy(f, budget)
    assert f.policy.reserved_hold == 0.
    with pytest.raises((ValueError, RuntimeError), match='budget'):
        f.run()
    assert f.drain_events().count((1,103,1)) == 1
    assert not f.sender.held and budget.snapshot()['reserved_pulses'] == 1


@pytest.mark.parametrize('fault', ('cancel', 'stage'))
def test_source_root_invalidated_after_down_releases_without_floor_commit(f, monkeypatch, fault):
    budget = root_budget(clock=f.clock, lock=f.ledger.lock)
    source_policy(f, budget)
    old_floor = f.ledger.chain
    def invalidate():
        if fault == 'cancel':budget.cancel('whole itinerary F9')
        else:budget.advance(budget.stage, 'crossing', zone_id=68)
    after_down(monkeypatch, invalidate)
    with pytest.raises((ValueError, RuntimeError)):
        f.run()
    events = f.drain_events()
    assert (1,103,1) in events and (1,103,0) in events
    assert not f.sender.held and f.ledger.chain is old_floor and f.ledger.steps == 0
    assert not budget.valid and budget.snapshot()['reserved_pulses'] == 1


def test_source_cannot_move_during_destination_bootstrap_stage(f):
    budget = root_budget(clock=f.clock, lock=f.ledger.lock)
    bootstrap_stage(budget)
    source_policy(f, budget)
    with pytest.raises((ValueError, RuntimeError), match='stage'):
        f.run()
    assert not f.drain_events() and budget.snapshot()['reserved_pulses'] == 0


def test_probe_policy_charges_destination_bootstrap_stage(ready):
    h, p, runtime, policy = ready
    budget = root_budget(clock=runtime.clock, lock=runtime.lock)
    bootstrap_stage(budget)
    stage = budget.stage
    scope = probe_policy(ready, budget)
    finish(h)
    assert h.engine.camp_position_last_result['outcome'] == 'probe_complete', '\n'.join(h.notices)
    assert type(scope) is SupervisedCampProbeScope
    assert runtime.policy._journey_reservation.ticket is runtime.transactions[0].seal.ticket
    assert runtime.policy._journey_reservation.stage is stage
    assert budget.snapshot()['reserved_pulses'] == 1
    assert budget.snapshot()['reserved_maximum_hold'] == scope.reserved_hold == .18
    assert not h.engine.sender.held


def test_probe_root_limit_refuses_before_down(ready):
    h, p, runtime, policy = ready
    budget = root_budget(clock=runtime.clock, lock=runtime.lock, maximum_total_hold=.17)
    bootstrap_stage(budget)
    scope = probe_policy(ready, budget)
    finish(h)
    assert not budget.valid and budget.snapshot()['reserved_pulses'] == 0
    assert scope.reserved_hold == 0.
    no_movement(h)


def test_probe_root_cancel_after_down_releases_without_floor_commit(ready, monkeypatch):
    h, p, runtime, policy = ready
    budget = root_budget(clock=runtime.clock, lock=runtime.lock)
    bootstrap_stage(budget)
    scope = probe_policy(ready, budget)
    after_down(monkeypatch, lambda:budget.cancel('whole itinerary F9'))
    finish(h)
    h.drain()
    assert (1,103,1) in h.events and (1,103,0) in h.events
    assert runtime.reference is None and not h.engine.sender.held and not scope.valid
    assert budget.snapshot()['reserved_pulses'] == 1


@pytest.mark.parametrize('fault', ('clock', 'lock'))
def test_source_root_must_share_exact_sender_clock_and_lock(f, fault):
    budget = root_budget(clock=(lambda:f.clock()) if fault == 'clock' else f.clock,
        lock=threading.RLock() if fault == 'lock' else f.ledger.lock)
    with pytest.raises(ValueError):source_policy(f, budget)
    assert not f.drain_events()


@pytest.mark.parametrize('fault', ('clock', 'lock'))
def test_probe_root_must_share_exact_sender_clock_and_lock(ready, fault):
    h, p, runtime, policy = ready
    budget = root_budget(clock=(lambda:runtime.clock()) if fault == 'clock' else runtime.clock,
        lock=threading.RLock() if fault == 'lock' else runtime.lock)
    with pytest.raises(ValueError):probe_policy(ready, budget)
    no_movement(h)


def test_root_cannot_replace_source_child_hold_limit(f):
    budget = root_budget(clock=f.clock, lock=f.ledger.lock)
    source_policy(f, budget, declaration=replace(f.policy.declaration, maximum_total_hold=.025))
    with pytest.raises((ValueError, RuntimeError), match='hold budget'):f.run()
    assert not f.drain_events() and budget.snapshot()['reserved_pulses'] == 0
