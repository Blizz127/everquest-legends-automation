"""Independent section limits composed with one persistent itinerary root."""
from dataclasses import replace
import threading
from types import SimpleNamespace

import pytest

from eql_automation.journey_input_budget import (
    JourneyBudgetDeclaration, JourneyInputBudget, itinerary_root,
)
from test_itinerary_policy_budget import root_budget
from test_journey_input_budget import bounds, ticket


def trip(**root_limits):
    state = SimpleNamespace(now=10., generation=1, child_generation=2,
                            root_hook=lambda: None, child_hook=lambda: None, clock_hook=lambda: None)
    def clock():
        state.clock_hook()
        return state.now
    def binding():
        state.root_hook()
        return (state.generation,)
    root = root_budget(clock=clock, lock=threading.RLock(), binding=binding, **root_limits)
    return root, state


def child(root, state, **limits):
    # The canonical parsed-guide digest deliberately differs from the pinned
    # staged-file digest on root. Their correspondence belongs to asset loading.
    declaration = JourneyBudgetDeclaration('f'*64, root.leg.destination_id,
        'zone_crossing', 2, 120., 8, 1.6, 100.)
    def binding():
        state.child_hook()
        return (state.child_generation, 'section-owner')
    return JourneyInputBudget(replace(declaration, **limits), clock=root.clock,
        stop_lock=root.lock, owner_binding=(2, 'section-owner'), binding_reader=binding,
        parent_budget=root)


def test_walk_and_probe_charge_both_exact_budgets_once():
    root, state = trip()
    section = child(root, state)
    for movement in (ticket(), ticket('right', probe=True)):
        reservation = section.reserve(movement, bounds=bounds())
        parent_reservation = root._reservations[id(movement)][0]
        assert section._reservations[id(movement)][5] is parent_reservation
        assert parent_reservation.ticket is reservation.ticket is movement
        section.check(reservation)
    assert type(section) is JourneyInputBudget
    assert itinerary_root(section) is itinerary_root(root) is root
    assert section.parent_stage is root.stage
    for budget in (section, root):
        record = budget.snapshot()
        assert record['reserved_pulses'] == 2
        assert record['reserved_maximum_hold'] == pytest.approx(.4)
        assert record['reserved_displacement_hypothesis'] == pytest.approx(4.6)
    assert section.snapshot()['parent_budget']['reserved_pulses'] == 2


def test_healthy_child_retirement_keeps_parent_counts_and_absolute_deadline():
    root, state = trip()
    first = child(root, state)
    first.reserve(ticket(), bounds=bounds())
    first.cancel('healthy leg child retired')
    root.check()
    state.now = 20.
    second = child(root, state)
    second.reserve(replace(ticket(serial=2), proposed_at=state.now), bounds=bounds())
    assert first.snapshot()['reserved_pulses'] == second.snapshot()['reserved_pulses'] == 1
    assert root.snapshot()['reserved_pulses'] == 2 and root.valid
    assert root.started == 10. and root.expires_at == 130.
    assert second.started == 20. and second.expires_at == 140.


def test_new_child_cannot_replay_a_ticket_already_spent_by_its_predecessor():
    root, state = trip()
    movement = ticket()
    first = child(root, state)
    first.reserve(movement, bounds=bounds())
    first.cancel('healthy retirement')
    second = child(root, state)
    with pytest.raises(ValueError, match='duplicate'):
        second.reserve(movement, bounds=bounds())
    assert root.snapshot()['reserved_pulses'] == 1 and not root.valid
    assert second.snapshot()['reserved_pulses'] == 0


def test_next_leg_child_starts_only_after_bootstrap_has_advanced_to_walking():
    root, state = trip()
    first = child(root, state)
    first.reserve(ticket(), bounds=bounds())
    first.cancel('first leg completed')
    for phase, zone in (('crossing', 68), ('loading', None), ('arrival', 54), ('bootstrap', 54)):
        root.advance(root.stage, phase, zone_id=zone)
    with pytest.raises(ValueError, match='walking stage'):
        child(root, state)
    assert root.valid
    root.advance(root.stage, 'walking', zone_id=54)
    second = child(root, state)
    second.reserve(ticket(serial=2), bounds=bounds())
    assert second.declaration.destination_id == 'gfay-butcher-crushbone-crossing'
    assert second.parent_stage is root.stage
    assert root.snapshot()['reserved_pulses'] == 2 and root.expires_at == 130.


@pytest.mark.parametrize('limit', ({'maximum_pulses':1}, {'maximum_total_hold':.3},
                                  {'maximum_displacement_reserve':5.}))
def test_parent_exhaustion_survives_replacing_its_section_child(limit):
    root, state = trip(**limit)
    first = child(root, state)
    first.reserve(ticket(), bounds=bounds())
    first.cancel('healthy retirement')
    second = child(root, state)
    with pytest.raises(ValueError, match='budget exhausted'):
        second.reserve(ticket(serial=2), bounds=bounds())
    assert root.snapshot()['reserved_pulses'] == 1 and not root.valid
    assert second.snapshot()['reserved_pulses'] == 0 and not second.valid


@pytest.mark.parametrize('limit', ({'maximum_pulses':1}, {'maximum_total_hold':.3},
                                  {'maximum_displacement_reserve':5.}))
def test_child_limits_fail_before_charging_or_cancelling_parent(limit):
    root, state = trip()
    section = child(root, state, **limit)
    section.reserve(ticket(), bounds=bounds())
    with pytest.raises(ValueError, match='budget exhausted'):
        section.reserve(ticket(serial=2), bounds=bounds())
    assert section.snapshot()['reserved_pulses'] == root.snapshot()['reserved_pulses'] == 1
    assert not section.valid and root.valid
    root.check()
    child(root, state).reserve(ticket(serial=3), bounds=bounds())
    assert root.snapshot()['reserved_pulses'] == 2


@pytest.mark.parametrize('expired', ('child', 'parent'))
def test_reserved_hold_must_fit_both_independent_deadlines(expired):
    root, state = trip(**({'maximum_seconds':.3, 'maximum_total_hold':.3} if expired == 'parent' else {}))
    section = child(root, state, **({'maximum_seconds':.3} if expired == 'child' else {}))
    state.now += .15
    with pytest.raises(ValueError, match='deadline'):
        section.reserve(replace(ticket(), proposed_at=state.now), bounds=bounds())
    assert section.snapshot()['reserved_pulses'] == root.snapshot()['reserved_pulses'] == 0
    assert not section.valid and root.valid is (expired == 'child')


@pytest.mark.parametrize('fault', ('clock', 'lock', 'type', 'destination', 'mode'))
def test_parent_is_exact_and_child_matches_active_walking_leg(fault):
    root, state = trip()
    template = child(root, state)
    options = dict(clock=root.clock, stop_lock=root.lock, owner_binding=(1,), binding_reader=lambda:(1,),
                   parent_budget=root)
    declaration = template.declaration
    if fault == 'clock':
        options['clock'] = lambda:state.now
    elif fault == 'lock':
        options['stop_lock'] = threading.RLock()
    elif fault == 'type':
        options['parent_budget'] = template
    else:
        declaration = replace(declaration, **({'destination_id':'gfay-butcher-crushbone-crossing'}
                              if fault == 'destination' else {'arrival_mode':'stop'}))
    with pytest.raises(ValueError):
        JourneyInputBudget(declaration, **options)
    root.check()
    assert root.snapshot()['reserved_pulses'] == 0


@pytest.mark.parametrize('operation', ('check', 'reserve', 'cancel'))
def test_retired_child_cannot_poison_a_healthy_advanced_parent(operation):
    root, state = trip()
    section = child(root, state)
    reservation = section.reserve(ticket(), bounds=bounds())
    root.advance(root.stage, 'crossing', zone_id=68)
    if operation == 'cancel':
        section.cancel('healthy retirement')
    else:
        with pytest.raises(ValueError, match='retired'):
            if operation == 'check':
                section.check(reservation)
            else:
                section.reserve(ticket(serial=2), bounds=bounds())
    assert root.valid and root.snapshot()['reserved_pulses'] == 1
    root.advance(root.stage, 'loading', zone_id=None)
    assert root.stage.phase == 'loading'


@pytest.mark.parametrize('fault', ('parent', 'stage', 'declaration', 'balance', 'last_clock'))
def test_child_binding_or_accounting_mutation_cancels_only_the_child(fault):
    root, state = trip()
    section = child(root, state)
    if fault == 'parent':
        section.parent_budget = None
        with pytest.raises(ValueError):
            itinerary_root(section)
    elif fault == 'stage':
        section.parent_stage = replace(section.parent_stage)
    elif fault == 'declaration':
        object.__setattr__(section.declaration, 'maximum_pulses', 1000)
    elif fault == 'balance':
        section._pulses = 1
    else:
        state.now = 20.
        section.check()
        section.last_at = 10.
    with pytest.raises(ValueError):
        section.check()
    root.check()
    assert not section.valid and root.valid


@pytest.mark.parametrize('fault', ('cancel', 'generation', 'expired'))
def test_parent_invalidation_is_sticky_in_child(fault):
    root, state = trip()
    section = child(root, state, maximum_seconds=200.)
    reservation = section.reserve(ticket(), bounds=bounds())
    if fault == 'cancel':
        root.cancel('F9 root stop')
    elif fault == 'generation':
        state.generation += 1
    else:
        state.now = root.expires_at + .01
    with pytest.raises(ValueError):
        section.check(reservation)
    assert not root.valid and not section.valid
    assert root.snapshot()['reserved_pulses'] == section.snapshot()['reserved_pulses'] == 1


@pytest.mark.parametrize('fault', ('copied', 'foreign', 'ticket_geometry'))
def test_child_checks_its_exact_parent_reservation_and_parent_ticket_pins(fault):
    root, state = trip()
    section = child(root, state)
    movement = ticket()
    reservation = section.reserve(movement, bounds=bounds())
    row = section._reservations[id(movement)]
    if fault == 'copied':
        section._reservations[id(movement)] = (*row[:5], replace(row[5]))
    elif fault == 'foreign':
        other = ticket(serial=2)
        section.reserve(other, bounds=bounds())
        section._reservations[id(movement)] = (*row[:5], root._reservations[id(other)][0])
    else:
        object.__setattr__(movement.geometry, 'payload', b'mutated geometry')
    with pytest.raises(ValueError):
        section.check(reservation)
    assert not section.valid
    assert root.snapshot()['reserved_pulses'] == (2 if fault == 'foreign' else 1)


@pytest.mark.parametrize('action', ('cancel', 'check', 'reserve'))
def test_parent_callback_cannot_reenter_child_or_refund_an_already_taken_parent_charge(action):
    root, state = trip()
    section = child(root, state)
    called = []
    def callback():
        if root._mutating and not called:
            called.append(action)
            try:
                if action == 'cancel':
                    section.cancel('child retired during root callback')
                elif action == 'check':
                    section.check()
                else:
                    section.reserve(ticket(serial=2), bounds=bounds())
            except ValueError:
                pass
    state.root_hook = callback
    with pytest.raises(ValueError, match='retired|reentered'):
        section.reserve(ticket(), bounds=bounds())
    assert called == [action]
    assert root.valid and root.snapshot()['reserved_pulses'] == 1
    assert not section.valid and section.snapshot()['reserved_pulses'] == 0
    root.check()


def test_child_callback_can_retire_stage_but_cannot_use_it_afterward():
    root, state = trip()
    section = child(root, state)
    def advance():
        state.child_hook = lambda:None
        root.advance(root.stage, 'crossing', zone_id=68)
    state.child_hook = advance
    with pytest.raises(ValueError, match='retired'):
        section.reserve(ticket(), bounds=bounds())
    root.check()
    assert root.valid and root.snapshot()['reserved_pulses'] == 0


def test_parent_callback_time_counts_against_earlier_child_deadline():
    root, state = trip()
    section = child(root, state, maximum_seconds=.5)
    def callback():
        state.root_hook = lambda:None
        state.now += .6
    state.root_hook = callback
    with pytest.raises(ValueError, match='child deadline'):
        section.reserve(ticket(), bounds=bounds())
    assert root.valid and root.snapshot()['reserved_pulses'] == 0 and not section.valid


def test_parent_supplies_final_checked_time_without_another_callback_after_reservation_check():
    root, state = trip()
    section = child(root, state, maximum_seconds=300.)
    unexpected = []
    def parent_callback():
        state.now = 20.
        def last_clock():
            if root._checking:
                return
            unexpected.append('unnecessary clock after closed parent check')
            root.cancel('root stopped during extra child clock')
        state.clock_hook = last_clock
    state.root_hook = parent_callback
    assert section.check() == section.last_at == root.last_at == 20.
    assert not unexpected and section.valid and root.valid


@pytest.mark.parametrize('fault', ('rollback', 'root_expired', 'root_cancelled'))
def test_final_parent_clock_failures_propagate_to_child(fault):
    root, state = trip()
    section = child(root, state, maximum_seconds=300.)
    clock_calls = []
    def last_clock():
        if not root._checking:return
        clock_calls.append(True)
        if len(clock_calls) == 2:
            if fault == 'rollback':
                state.now = 9.
            elif fault == 'root_expired':
                state.now = root.expires_at + .01
            else:
                root.cancel('root stopped during final parent clock')
    state.clock_hook = last_clock
    with pytest.raises(ValueError):
        section.check()
    assert not section.valid and not root.valid
    assert root.snapshot()['reserved_pulses'] == section.snapshot()['reserved_pulses'] == 0


@pytest.mark.parametrize('fault', ('field', 'field_type', 'row_copy', 'row_resealed'))
def test_parent_callbacks_cannot_change_or_reseal_child_reservation(fault):
    root, state = trip()
    section = child(root, state)
    movement = ticket()
    reservation = section.reserve(movement, bounds=bounds())
    row = section._reservations[id(movement)]
    def callback():
        state.root_hook = lambda:None
        if fault == 'field':
            object.__setattr__(reservation, 'maximum_hold', .1)
        elif fault == 'field_type':
            object.__setattr__(reservation, 'input_authorized', 0)
        elif fault == 'row_copy':
            section._reservations[id(movement)] = tuple(list(row))
        else:
            object.__setattr__(reservation, 'maximum_hold', .1)
            fields = (*row[1][:2], .1, *row[1][3:])
            section._reservations[id(movement)] = (row[0], fields, *row[2:])
    state.root_hook = callback
    with pytest.raises(ValueError, match='reservation'):
        section.check(reservation)
    assert not section.valid and root.valid
    assert root.snapshot()['reserved_pulses'] == 1


def test_standalone_helper_does_not_invent_a_parent():
    root, state = trip()
    template = child(root, state)
    standalone = JourneyInputBudget(template.declaration, clock=root.clock, stop_lock=root.lock,
        owner_binding=(2,), binding_reader=lambda:(2,))
    assert itinerary_root(standalone) is itinerary_root(None) is None
    standalone.reserve(ticket(), bounds=bounds())
    assert root.snapshot()['reserved_pulses'] == 0
    with pytest.raises(ValueError):
        itinerary_root(object())
