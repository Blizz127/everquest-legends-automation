from dataclasses import replace
from types import SimpleNamespace
import threading

import pytest

from eql_automation.camp_probe_transaction import CampProbeTicket
from eql_automation.journey_input_budget import JourneyBudgetDeclaration, JourneyInputBudget
from eql_automation.route_geometry import RouteMotionBounds
from eql_automation.source_motion import SourceMotionGeometry, SourceMotionTicket


def budget(*, clock=None, lock=None, binding=None, **limits):
    state = SimpleNamespace(now=10., generation=1)
    d = JourneyBudgetDeclaration('a'*64, 'goblin-camp-stop', 'stop', 2, 120., 8, 1.6, 100.)
    d = replace(d, **limits)
    b = JourneyInputBudget(d, clock=(lambda:state.now) if clock is None else clock,
        stop_lock=threading.RLock() if lock is None else lock, owner_binding=(1,),
        binding_reader=(lambda:(state.generation,)) if binding is None else binding)
    return b, state


def bounds():
    return RouteMotionBounds('fresh-bounds', 'fresh-fit', .01, .15, .2, 20., .4, .01, 2., .1, 1.2, 6.)


def ticket(kind='forward', *, probe=False, serial=1):
    key = {'forward':103, 'left':105, 'right':106}[kind]
    if probe:return CampProbeTicket(object(), 'b'*64, kind, key, .1, .2, 10.)
    return SourceMotionTicket(object(), SourceMotionGeometry(kind, (), b'', 'c'*64),
                              serial, 10., .1, .2, key)


def test_one_budget_counts_walk_and_probe_holds_and_displacements_without_refunds():
    b, state = budget()
    first = b.reserve(ticket(), bounds=bounds())
    second = b.reserve(ticket('right', probe=True), bounds=bounds())
    b.check(first); b.check(second)
    record = b.snapshot()
    assert record['reserved_pulses'] == 2
    assert record['reserved_maximum_hold'] == pytest.approx(.4)
    assert record['reserved_displacement_hypothesis'] == pytest.approx(4.6)
    assert not first.input_authorized and not record['permits_section_handoff']
    b.cancel('F9')
    assert b.snapshot()['reserved_maximum_hold'] == record['reserved_maximum_hold']
    with pytest.raises(ValueError, match='F9'): b.reserve(ticket(serial=2), bounds=bounds())


@pytest.mark.parametrize('limit', ({'maximum_pulses':1}, {'maximum_total_hold':.3},
                                  {'maximum_displacement_reserve':5.}))
def test_whole_trip_limit_survives_a_new_ticket_and_is_sticky(limit):
    b, _ = budget(**limit)
    b.reserve(ticket(), bounds=bounds())
    with pytest.raises(ValueError, match='budget exhausted'):
        b.reserve(ticket(serial=2), bounds=bounds())
    assert b.snapshot()['reserved_pulses'] == 1
    with pytest.raises(ValueError):b.check()


@pytest.mark.parametrize('fault', ('expired', 'backwards', 'generation', 'declaration', 'deadline', 'clock'))
def test_parent_expiry_or_identity_change_cannot_be_renewed(fault):
    b, state = budget()
    r = b.reserve(ticket(), bounds=bounds())
    if fault == 'expired':state.now = b.expires_at+.01
    elif fault == 'backwards':state.now -= .01
    elif fault == 'generation':state.generation += 1
    elif fault == 'declaration':object.__setattr__(b.declaration, 'destination_id', 'other')
    elif fault == 'deadline':b.expires_at += 1.
    else:b.clock = lambda:10.
    with pytest.raises(ValueError):b.check(r)
    state.now = 10.; state.generation = 1
    assert not b.valid
    with pytest.raises(ValueError):b.check()


@pytest.mark.parametrize('fault', ('duplicate', 'copied_reservation', 'ticket', 'bounds'))
def test_exact_reservation_and_unchanged_ticket_are_required(fault):
    b, _ = budget(); t = ticket(); envelope = bounds()
    r = b.reserve(t, bounds=envelope)
    with pytest.raises(ValueError):
        if fault == 'duplicate':b.reserve(t, bounds=envelope)
        elif fault == 'copied_reservation':b.check(replace(r))
        else:
            if fault == 'ticket':object.__setattr__(t, 'maximum_actual_hold', .1)
            else:object.__setattr__(envelope, 'forward_speed_upper_bound', 1.)
            b.check(r)
    assert b.snapshot()['reserved_pulses'] == 1


def test_stop_from_clock_callback_is_observed_before_any_charge():
    b, state = budget()
    def read():
        if state.now > 10.:b.cancel('owner stopped during callback')
        return (1,)
    # Supply the callback at construction; replacing one later must also fail.
    c = JourneyInputBudget(b.declaration, clock=lambda:state.now, stop_lock=b.lock,
                          owner_binding=(1,), binding_reader=read)
    b = c; state.now = 11.
    with pytest.raises(ValueError, match='owner stopped'):c.reserve(ticket(), bounds=bounds())
    assert c.snapshot()['reserved_pulses'] == 0


def test_shared_lock_serializes_competing_last_reservations():
    b, _ = budget(maximum_pulses=1); barrier = threading.Barrier(3); result = []
    def reserve():
        barrier.wait()
        try:result.append(b.reserve(ticket(), bounds=bounds()))
        except ValueError:result.append(None)
    threads = [threading.Thread(target=reserve) for _ in range(2)]
    for t in threads:t.start()
    barrier.wait()
    for t in threads:t.join(2.); assert not t.is_alive()
    assert sum(r is not None for r in result) == 1
    assert b.snapshot()['reserved_pulses'] == 1 and not b.valid
