"""Terminal camp accounting uses registered metadata and synthetic tickets.

These checks prove neither arrival nor game execution and send no input.
"""
from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
import threading
from types import SimpleNamespace

import pytest

from eql_automation.initial_itinerary_measurement import InitialItineraryMeasurement
from eql_automation.journey_input_budget import JourneyBudgetDeclaration, JourneyInputBudget
from eql_automation.native_region_policy import encoded
from eql_automation.source_destinations import destination_spec
from eql_automation.zone_itinerary_budget import (
    ZoneItineraryBudget, ZoneItineraryDeclaration, ZoneItineraryTerminalCamp, load_terminal_camp,
)
from test_initial_itinerary_measurement import f as initial
from test_journey_input_budget import bounds, ticket as ordinary_ticket
from test_motion_collection import retained
from test_owner_zone_itinerary import synthetic_legs
from test_zone_itinerary_budget import crossing_ticket


CATALOG = {'Butcherblock Mountains':68, 'The Greater Faydark':54, 'Clan Crushbone':58}


def declaration(**changes):
    legs, _ = synthetic_legs(CATALOG)
    terminal = load_terminal_camp('slave-mines', zone_catalog=CATALOG)
    return replace(ZoneItineraryDeclaration('synthetic-terminal-trip', legs,
        120., 12, 2.4, 100., terminal), **changes)


def budget(*, clock=None, lock=None, **limits):
    s = SimpleNamespace(now=10., callback=lambda:None)
    def binding():
        hook, s.callback = s.callback, lambda:None
        hook()
        return ('synthetic-terminal-owner',)
    root = ZoneItineraryBudget(declaration(**limits),
        clock=(lambda:s.now) if clock is None else clock,
        stop_lock=threading.RLock() if lock is None else lock,
        owner_binding=('synthetic-terminal-owner',), binding_reader=binding)
    return root, s


def advance(root, phase, zone):
    return root.advance(root.stage, phase, zone_id=zone)


def last_crossing_arrival(root, *, charge_first=False):
    for index, leg in enumerate(root.declaration.legs):
        advance(root, 'crossing', leg.source_zone_id)
        if index == 0 and charge_first:
            root.reserve(crossing_ticket(now=root.clock()), bounds=bounds())
        advance(root, 'loading', None)
        advance(root, 'arrival', leg.destination_zone_id)
        if index + 1 < len(root.declaration.legs):
            advance(root, 'bootstrap', leg.destination_zone_id)
            advance(root, 'walking', leg.destination_zone_id)


def terminal_stage(root, phase='walking', *, charge_first=False):
    last_crossing_arrival(root, charge_first=charge_first)
    advance(root, 'bootstrap', 58)
    for next_phase in ('walking', 'arrival', 'complete'):
        if root.stage.phase == phase:
            break
        advance(root, next_phase, 58)


def ticket_at(root, *, probe=False):
    return replace(ordinary_ticket(probe=probe), proposed_at=root.clock())


def child(root, *, arrival_mode='camp'):
    d = JourneyBudgetDeclaration(root.leg.guide_sha256, root.leg.destination_id,
        arrival_mode, 1, 120., 8, 1.6, 100.)
    return JourneyInputBudget(d, clock=root.clock, stop_lock=root.lock,
        owner_binding=root.owner_binding, binding_reader=root.binding_reader, parent_budget=root)


def test_registered_terminal_camp_pins_guide_and_copied_catalog():
    terminal = load_terminal_camp('slave-mines', zone_catalog=CATALOG)
    spec = destination_spec('slave-mines')
    assert type(terminal) is ZoneItineraryTerminalCamp
    assert (terminal.destination_id, terminal.source_zone, terminal.source_zone_id,
            terminal.source_name, terminal.arrival_mode) == (
                'slave-mines', 'crushbone', 58, 'Clan Crushbone', 'camp')
    assert terminal.guide_sha256 == spec.file_sha256
    assert terminal.catalog_sha256 == sha256(encoded(CATALOG)).hexdigest()
    terminal.validate()
    with pytest.raises(FrozenInstanceError):
        terminal.source_name = 'Changed'
    d = declaration()
    d.validate()
    assert d.target_count == len(d.legs) + 1 == 3


@pytest.mark.parametrize('identifier', ('missing-camp', 'throne-stair-landing',
                                      'gfay-butcher-crushbone-crossing', None))
def test_terminal_loader_requires_registered_camp(identifier):
    with pytest.raises(ValueError):
        load_terminal_camp(identifier, zone_catalog=CATALOG)


@pytest.mark.parametrize('catalog', (
    {}, {'Clan Crushbone':True}, {'':58}, {'The Greater Faydark':54},
    {**CATALOG, 'Another Crushbone name':58},
))
def test_terminal_loader_requires_unique_valid_catalog_zone(catalog):
    with pytest.raises(ValueError):
        load_terminal_camp('slave-mines', zone_catalog=catalog)


@pytest.mark.parametrize('change', (
    {'destination_id':'north-wall'}, {'source_zone':'butcher'}, {'source_zone_id':68},
    {'source_zone_id':True}, {'guide_sha256':'f'*64}, {'catalog_sha256':'bad'},
    {'source_name':''},
))
def test_terminal_record_rejects_foreign_registration_or_invalid_pins(change):
    terminal = load_terminal_camp('slave-mines', zone_catalog=CATALOG)
    with pytest.raises(ValueError):
        replace(terminal, **change).validate()


@pytest.mark.parametrize('fault', ('wrong_zone', 'name', 'catalog'))
def test_declaration_requires_terminal_adjacent_in_same_catalog(fault):
    d = declaration()
    terminal = d.terminal_camp
    if fault == 'wrong_zone':
        terminal = load_terminal_camp('goblin-camp', zone_catalog=CATALOG)
    elif fault == 'name':
        terminal = replace(terminal, source_name='Different Crushbone name')
    else:
        terminal = load_terminal_camp('slave-mines', zone_catalog={**CATALOG, 'Extra zone':999})
    with pytest.raises(ValueError, match='adjacent'):
        replace(d, terminal_camp=terminal).validate()


@pytest.mark.parametrize('fault', ('crossing_leg', 'namespace'))
def test_declaration_requires_exact_terminal_record_type(fault):
    d = declaration()
    terminal = d.legs[-1] if fault == 'crossing_leg' else SimpleNamespace(**vars(d.terminal_camp))
    with pytest.raises(ValueError):
        replace(d, terminal_camp=terminal).validate()


@pytest.mark.parametrize('field,value', (
    ('destination_id', 'north-wall'), ('guide_sha256', 'f'*64),
    ('catalog_sha256', 'e'*64), ('source_name', 'Changed'),
))
def test_terminal_mutation_invalidates_root_even_before_terminal_stage(field, value):
    root, _ = budget()
    stage = root.stage
    object.__setattr__(root.declaration.terminal_camp, field, value)
    with pytest.raises(ValueError):
        root.check()
    assert not root.valid and root.stage is stage and root._pulses == 0


def test_same_value_terminal_replacement_cannot_rebind_root():
    root, _ = budget()
    original = root.declaration.terminal_camp
    replacement = replace(original)
    assert replacement == original and replacement is not original
    object.__setattr__(root.declaration, 'terminal_camp', replacement)
    with pytest.raises(ValueError):
        root.check()
    assert not root.valid and root._pulses == 0


@pytest.mark.parametrize('fault', ('kind', 'index', 'copy'))
def test_terminal_stage_kind_index_and_exact_identity_remain_pinned(fault):
    root, _ = budget()
    terminal_stage(root)
    if fault == 'kind':
        object.__setattr__(root.stage, 'kind', 'crossing')
    elif fault == 'index':
        object.__setattr__(root.stage, 'leg_index', len(root.declaration.legs)-1)
    else:
        root.stage = replace(root.stage)
    with pytest.raises(ValueError):
        root.check()
    assert not root.valid and root._pulses == 0


def test_terminal_bootstrap_walk_and_arrival_share_fixed_root_and_child_charges():
    root, s = budget()
    deadline = root.expires_at
    root.reserve(ticket_at(root), bounds=bounds())
    last_crossing_arrival(root, charge_first=True)
    assert root.stage.kind == 'crossing' and root.stage.leg_index == 1
    s.now = 30.
    advance(root, 'bootstrap', 58)
    assert root.stage.kind == 'terminal_camp' and root.stage.leg_index == len(root.declaration.legs)
    assert root.stage.destination_id == 'slave-mines' and root.leg is root.declaration.terminal_camp
    root.reserve(ticket_at(root, probe=True), bounds=bounds())
    advance(root, 'walking', 58)
    route = child(root)
    reservation = route.reserve(ticket_at(root), bounds=bounds())
    route.check(reservation)
    assert root.snapshot()['reserved_pulses'] == 4
    assert root.snapshot()['reserved_maximum_hold'] == pytest.approx(.8)
    assert root.snapshot()['reserved_displacement_hypothesis'] == pytest.approx(16.4)
    assert route.snapshot()['reserved_pulses'] == 1
    advance(root, 'arrival', 58)
    advance(root, 'complete', 58)
    assert root.stage.kind == 'terminal_camp' and root.stage.phase == 'complete'
    assert root.expires_at == deadline == 130. and root.cap_deadline(200.) == deadline
    assert not root.snapshot()['input_authorized']


def test_no_terminal_preserves_final_crossing_completion():
    root, _ = budget(terminal_camp=None)
    deadline = root.expires_at
    assert root.declaration.target_count == len(root.declaration.legs) == 2
    last_crossing_arrival(root)
    advance(root, 'complete', 58)
    assert root.stage.kind == 'crossing' and root.stage.leg_index == 1
    assert root.leg is root.declaration.legs[-1]
    assert root.expires_at == deadline and root._pulses == 0 and root.valid


@pytest.mark.parametrize('limit', ({'maximum_pulses':2}, {'maximum_total_hold':.5},
                                  {'maximum_displacement_reserve':9.}))
def test_terminal_bootstrap_cannot_refund_crossing_charges(limit):
    root, _ = budget(**limit)
    root.reserve(ticket_at(root), bounds=bounds())
    terminal_stage(root, 'bootstrap', charge_first=True)
    with pytest.raises(ValueError, match='budget exhausted'):
        root.reserve(ticket_at(root, probe=True), bounds=bounds())
    assert not root.valid and root.snapshot()['reserved_pulses'] == 2
    assert root.snapshot()['reserved_maximum_hold'] == pytest.approx(.4)
    assert root.snapshot()['reserved_displacement_hypothesis'] == pytest.approx(8.2)


@pytest.mark.parametrize('fault', ('expired', 'hold_over_deadline'))
def test_terminal_never_renews_fixed_deadline(fault):
    root, s = budget()
    terminal_stage(root)
    stage, deadline = root.stage, root.expires_at
    s.now = deadline + .01 if fault == 'expired' else deadline - .1
    with pytest.raises(ValueError, match='deadline'):
        root.reserve(ticket_at(root), bounds=bounds())
    assert root.expires_at == deadline and root.stage is stage and root._pulses == 0


@pytest.mark.parametrize('phase', ('bootstrap', 'walking', 'arrival', 'complete'))
def test_terminal_never_accepts_crossing_ticket(phase):
    root, _ = budget()
    terminal_stage(root, phase)
    with pytest.raises(ValueError, match='not allowed'):
        root.reserve(crossing_ticket(now=root.clock()), bounds=bounds())
    assert root._pulses == 0


def test_terminal_bootstrap_requires_probe_before_ordinary_walking():
    root, _ = budget()
    terminal_stage(root, 'bootstrap')
    with pytest.raises(ValueError, match='not allowed'):
        root.reserve(ticket_at(root), bounds=bounds())
    assert root.stage.phase == 'bootstrap' and root._pulses == 0


@pytest.mark.parametrize('phase,next_phase,zone', (
    ('bootstrap','crossing',58), ('bootstrap','arrival',58),
    ('walking','crossing',58), ('walking','loading',None),
    ('walking','arrival',54), ('arrival','complete',54),
))
def test_terminal_rejects_crossing_loading_or_wrong_zone_transition(phase, next_phase, zone):
    root, _ = budget()
    terminal_stage(root, phase)
    stage = root.stage
    with pytest.raises(ValueError, match='out of order'):
        advance(root, next_phase, zone)
    assert root.stage is stage and not root.valid


@pytest.mark.parametrize('mode', ('zone_crossing', 'stop'))
def test_terminal_journey_child_requires_exact_camp_arrival_mode(mode):
    root, _ = budget()
    terminal_stage(root)
    stage = root.stage
    with pytest.raises(ValueError, match='different itinerary walking stage'):
        child(root, arrival_mode=mode)
    assert root.valid and root.stage is stage and root._pulses == 0


@pytest.mark.parametrize('phase', ('arrival', 'complete'))
def test_retired_terminal_child_cannot_submit_old_root_reservation(phase):
    root, _ = budget()
    terminal_stage(root)
    route = child(root)
    reservation = route.reserve(ticket_at(root), bounds=bounds())
    advance(root, 'arrival', 58)
    if phase == 'complete':
        advance(root, 'complete', 58)
    stage = root.stage
    with pytest.raises(ValueError, match='retired'):
        route.check(reservation)
    assert not route.valid and root.valid and root.stage is stage and root._pulses == 1
    root.check()


@pytest.mark.parametrize('operation', ('reserve', 'advance'))
@pytest.mark.parametrize('fault', ('terminal_record', 'stage_kind'))
def test_terminal_callback_mutation_prevents_reservation_or_stage_publication(operation, fault):
    root, s = budget()
    terminal_stage(root)
    stage, previous = root.stage, root.last_at
    def mutate():
        if fault == 'terminal_record':
            object.__setattr__(root.declaration.terminal_camp, 'guide_sha256', 'f'*64)
        else:
            object.__setattr__(root.stage, 'kind', 'crossing')
    s.callback = mutate
    with pytest.raises(ValueError):
        if operation == 'reserve':
            root.reserve(ticket_at(root), bounds=bounds())
        else:
            advance(root, 'arrival', 58)
    assert not root.valid and root.stage is stage and root.stage.phase == 'walking'
    assert root.last_at == root._last_at == previous and root._pulses == 0
    assert not root._reservations


@pytest.mark.parametrize('nested', ('cancel', 'check', 'reserve', 'advance'))
def test_terminal_callback_cancellation_and_caught_reentry_cannot_charge(nested):
    root, s = budget()
    terminal_stage(root)
    stage = root.stage
    def callback():
        try:
            if nested == 'cancel':
                root.cancel('F9 during terminal callback')
            elif nested == 'check':
                root.check()
            elif nested == 'reserve':
                root.reserve(ticket_at(root), bounds=bounds())
            else:
                advance(root, 'arrival', 58)
        except ValueError:
            pass
    s.callback = callback
    with pytest.raises(ValueError, match='F9|reentered'):
        root.reserve(ticket_at(root), bounds=bounds())
    assert not root.valid and root.stage is stage and root._pulses == 0


def test_terminal_cannot_attach_another_initial_measurement(initial):
    root, _ = budget(clock=initial.clock, lock=initial.lock)
    terminal_stage(root)
    initial.source.zone_id = root.leg.source_zone_id
    initial.source.zone_display_name = root.leg.source_name
    stage, deadline = root.stage, root.expires_at
    with pytest.raises(ValueError, match='ownership or hypotheses'):
        InitialItineraryMeasurement(initial.session, root, **initial.options)
    assert root._initial_measurement is None and root.stage is stage
    assert root.expires_at == deadline and root._pulses == 0 and root.valid
    assert not initial.requests and not initial.account.reservations
