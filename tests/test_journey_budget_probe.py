import pytest

from eql_automation.supervised_camp_probe import SupervisedCampProbeScope
from test_journey_input_budget import budget
from test_supervised_camp_probe import ready, configure_supervised, until_pulse, no_movement
from test_owner_camp_probe import finish
from test_owner_camp_position import camp
from test_camp_floor_checkpoint import checkpoint
from test_source_motion import f
from test_route_floor_commit import legacy
from test_motion_collection import retained
from test_owner_journey_runtime import h
from test_route_step_sender import after_down


def attach(ready, **limits):
    h, p, r, policy = ready
    s = policy.scope
    b, _ = budget(clock=r.clock, lock=r.lock, **limits)
    r.phase = 'collect_start'
    scope = SupervisedCampProbeScope(r, declaration=s.declaration, monitor=s.monitor,
        gate=s.gate, expected_window=s.window, log_veto=s.log_veto,
        check_current=s.current, started_at=s.started_at, expires_at=s.expires_at,
        journey_budget=b)
    r.policy = scope.policy(r.transaction)
    r.phase = 'pulse'
    return b, scope


def test_probe_sender_charges_the_parent_once_before_down(ready):
    h, p, r, policy = ready
    b, scope = attach(ready)
    finish(h)
    assert h.engine.camp_position_last_result['outcome'] == 'probe_complete', '\n'.join(h.notices)
    assert b.snapshot()['reserved_pulses'] == 1
    assert b.snapshot()['reserved_maximum_hold'] == .18
    assert scope.reserved_hold == .18
    assert r.policy._journey_reservation.ticket is r.transactions[0].seal.ticket
    assert not h.engine.sender.held


def test_whole_journey_limit_refuses_probe_before_down(ready):
    h, p, r, policy = ready
    b, scope = attach(ready, maximum_total_hold=.17)
    finish(h)
    assert not b.valid and b.snapshot()['reserved_pulses'] == 0
    assert scope.reserved_hold == 0.
    no_movement(h)


def test_parent_stop_during_probe_down_releases_without_floor_commit(ready, monkeypatch):
    h, p, r, policy = ready
    b, scope = attach(ready)
    after_down(monkeypatch, lambda:b.cancel('F9 entire journey'))
    finish(h); h.drain()
    assert (1,103,1) in h.events and (1,103,0) in h.events
    assert r.reference is None and not h.engine.sender.held
    assert b.snapshot()['reserved_pulses'] == 1 and not scope.valid
