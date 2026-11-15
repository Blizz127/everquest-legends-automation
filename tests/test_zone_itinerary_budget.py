"""Root accounting across real copied crossing IDs and synthetic movement tickets."""
from dataclasses import replace
from hashlib import sha256
import threading
from types import SimpleNamespace

import pytest

from eql_automation.native_region_policy import encoded
from eql_automation.owner_source_crossing import load_source_crossing_spec
from eql_automation.source_crossing_corridor import SourceCrossingGeometry, SourceCrossingTicket
from eql_automation.zone_itinerary_budget import (
    ZoneItineraryBudget, ZoneItineraryDeclaration, load_zone_itinerary,
)
from test_journey_input_budget import bounds, ticket as ordinary_ticket


IDS = ('butcher-gfay-crossing', 'gfay-butcher-crushbone-crossing')
CATALOG = {'Butcherblock Mountains': 68, 'The Greater Faydark': 54, 'Clan Crushbone': 58}


def budget(**limits):
    state = SimpleNamespace(now=10., generation=1, callback=lambda: None)
    legs = load_zone_itinerary(IDS, zone_catalog=CATALOG)
    declaration = replace(ZoneItineraryDeclaration('synthetic-root', legs, 120., 12, 2.4, 100.), **limits)
    def binding():
        state.callback()
        return (state.generation, ('owner-settings', 42, 100))
    root = ZoneItineraryBudget(declaration, clock=lambda: state.now,
        stop_lock=threading.RLock(), owner_binding=(1, ('owner-settings', 42, 100)),
        binding_reader=binding)
    return root, state


def crossing_ticket(*, now=10., kind='forward', touches_line=True):
    payload = encoded({'synthetic': True, 'kind': kind})
    geometry = SourceCrossingGeometry(kind, ((0., 0.), (1., 0.), (0., 1.)),
        (2,) if touches_line else (), payload, sha256(payload).hexdigest())
    return SourceCrossingTicket(object(), geometry, 1, now, .1, .2,
        {'forward': 103, 'left': 105, 'right': 106}[kind], touches_line)


def enter(root, phase, zone):
    return root.advance(root.stage, phase, zone_id=zone)


def next_destination(root):
    enter(root, 'crossing', 68)
    enter(root, 'loading', None)
    enter(root, 'arrival', 54)
    enter(root, 'bootstrap', 54)


def test_copied_legs_pin_adjacent_source_and_destination_catalog_identities():
    legs = load_zone_itinerary(IDS, zone_catalog=CATALOG)
    assert [(leg.source_zone_id, leg.destination_zone_id) for leg in legs] == [(68, 54), (54, 58)]
    assert legs[0].destination_name == legs[1].source_name == 'The Greater Faydark'
    for leg in legs:
        source = load_source_crossing_spec(leg.destination_id)
        assert leg.corridor_sha256 == source.corridor_file_sha256
        assert leg.expected_zone_line_sha256 == source.expected_zone_line.sha256
    changed = dict(CATALOG)
    changed['another name for GFay'] = 54
    with pytest.raises(ValueError, match='unique'):
        load_zone_itinerary(IDS, zone_catalog=changed)
    with pytest.raises(ValueError, match='adjacent'):
        load_zone_itinerary(tuple(reversed(IDS)), zone_catalog=CATALOG)
    with pytest.raises(ValueError, match='unique'):
        load_zone_itinerary((IDS[0], IDS[0]), zone_catalog=CATALOG)


@pytest.mark.parametrize('change', (
    {'destination_id': 'gfay-crushbone-crossing'}, {'zone': 'gfaydark'},
    {'start_xy': (0., 0.)}, {'provenance_sha256': 'a'*64},
    {'destination_zone_id': 58}, {'destination_zone': 'crushbone'},
))
def test_loader_refuses_a_provider_that_no_longer_matches_pinned_guide_or_catalog(change):
    def provider(identifier):
        crossing = load_source_crossing_spec(identifier)
        return replace(crossing, **change) if identifier == IDS[0] else crossing
    with pytest.raises(ValueError):
        load_zone_itinerary(IDS, zone_catalog=CATALOG, crossing_provider=provider)


def test_walk_crossing_loading_arrival_and_bootstrap_share_one_unrenewed_budget():
    root, state = budget()
    original = root.expires_at
    root.reserve(ordinary_ticket(), bounds=bounds())
    root.reserve(ordinary_ticket('right', probe=True), bounds=bounds())
    state.now = 20.
    enter(root, 'crossing', 68)
    root.reserve(crossing_ticket(now=state.now), bounds=bounds())
    enter(root, 'loading', None)
    state.now = 40.
    enter(root, 'arrival', 54)
    state.now = 50.
    enter(root, 'bootstrap', 54)
    probe = replace(ordinary_ticket('left', probe=True), proposed_at=state.now)
    reservation = root.reserve(probe, bounds=bounds())
    root.check(reservation)
    assert root.stage.leg_index == 1 and root.stage.destination_id == IDS[1]
    assert root.expires_at == original == 130.
    assert root.cap_deadline(200.) == original
    assert root.cap_deadline(90.) == 90.
    enter(root, 'walking', 54)
    root.reserve(replace(ordinary_ticket(serial=2), proposed_at=state.now), bounds=bounds())
    enter(root, 'crossing', 54)
    root.reserve(crossing_ticket(now=state.now), bounds=bounds())
    enter(root, 'loading', None)
    enter(root, 'arrival', 58)
    enter(root, 'complete', 58)
    result = root.snapshot()
    assert result['stage']['phase'] == 'complete'
    assert result['reserved_pulses'] == 6
    assert result['reserved_maximum_hold'] == pytest.approx(1.2)
    assert result['reserved_displacement_hypothesis'] == pytest.approx(17.4)
    assert root.expires_at == original
    assert not result['input_authorized'] and not result['permits_zone_handoff']
    assert not result['child_limits_replaced'] and not result['server_destinations_verified']


@pytest.mark.parametrize('limit', ({'maximum_pulses': 2}, {'maximum_total_hold': .5},
                                  {'maximum_displacement_reserve': 9.}))
def test_reservations_before_loading_remain_charged_in_destination_bootstrap(limit):
    root, state = budget(**limit)
    root.reserve(ordinary_ticket(), bounds=bounds())
    enter(root, 'crossing', 68)
    root.reserve(crossing_ticket(), bounds=bounds())
    enter(root, 'loading', None)
    enter(root, 'arrival', 54)
    enter(root, 'bootstrap', 54)
    with pytest.raises(ValueError, match='budget exhausted'):
        root.reserve(ordinary_ticket(probe=True), bounds=bounds())
    snapshot = root.snapshot()
    assert snapshot['reserved_pulses'] == 2
    assert snapshot['reserved_maximum_hold'] == .4
    assert snapshot['reserved_displacement_hypothesis'] == pytest.approx(8.2)
    assert not root.valid
    with pytest.raises(ValueError):
        root.advance(root.stage, 'walking', zone_id=54)


@pytest.mark.parametrize('phase,zone', [('arrival', 54), ('bootstrap', 54), ('crossing', 54)])
def test_out_of_order_or_wrong_zone_handoff_cancels_without_advancing(phase, zone):
    root, _ = budget()
    initial = root.stage
    with pytest.raises(ValueError, match='out of order'):
        root.advance(initial, phase, zone_id=zone)
    assert root.stage is initial and not root.valid


def test_stage_can_only_be_consumed_once_and_prior_reservation_cannot_admit_input():
    root, _ = budget()
    first = root.stage
    reservation = root.reserve(ordinary_ticket(), bounds=bounds())
    enter(root, 'crossing', 68)
    with pytest.raises(ValueError, match='retired stage'):
        root.check(reservation)
    assert root.snapshot()['reserved_pulses'] == 1
    other, _ = budget()
    old = other.stage
    enter(other, 'crossing', 68)
    with pytest.raises(ValueError, match='unconsumed'):
        other.advance(old, 'loading', zone_id=None)
    copy, _ = budget()
    with pytest.raises(ValueError, match='unconsumed'):
        copy.advance(replace(copy.stage), 'crossing', zone_id=68)
    assert first.phase == 'walking'


@pytest.mark.parametrize('phase,ticket_kind', (
    ('walking', 'crossing'), ('crossing', 'probe'), ('crossing', 'walking'),
    ('loading', 'crossing'), ('arrival', 'probe'), ('bootstrap', 'walking'),
))
def test_only_the_active_child_kind_can_charge_a_phase(phase, ticket_kind):
    root, _ = budget()
    if phase != 'walking':
        enter(root, 'crossing', 68)
    if phase in ('loading', 'arrival', 'bootstrap'):
        enter(root, 'loading', None)
    if phase in ('arrival', 'bootstrap'):
        enter(root, 'arrival', 54)
    if phase == 'bootstrap':
        enter(root, 'bootstrap', 54)
    ticket = crossing_ticket() if ticket_kind == 'crossing' else ordinary_ticket(probe=ticket_kind == 'probe')
    with pytest.raises(ValueError, match='not allowed'):
        root.reserve(ticket, bounds=bounds())
    assert root.snapshot()['reserved_pulses'] == 0


@pytest.mark.parametrize('fault', ('copy', 'duplicate', 'touches_line', 'geometry', 'bounds'))
def test_crossing_reservation_rejects_copies_replay_and_changed_ticket_contents(fault):
    root, _ = budget()
    enter(root, 'crossing', 68)
    ticket, movement_bounds = crossing_ticket(), bounds()
    reservation = root.reserve(ticket, bounds=movement_bounds)
    with pytest.raises(ValueError):
        if fault == 'copy':
            root.check(replace(reservation))
        elif fault == 'duplicate':
            root.reserve(ticket, bounds=movement_bounds)
        else:
            if fault == 'touches_line':
                object.__setattr__(ticket, 'touches_line', False)
            elif fault == 'geometry':
                object.__setattr__(ticket.geometry, 'touched_regions', (99,))
            else:
                object.__setattr__(movement_bounds, 'post_release_drift', .01)
            root.check(reservation)
    assert root.snapshot()['reserved_pulses'] == 1


@pytest.mark.parametrize('fault', ('expired', 'backwards', 'generation', 'deadline', 'stage', 'leg', 'balance'))
def test_root_lifetime_or_identity_changes_are_sticky(fault):
    root, state = budget()
    if fault == 'expired':
        state.now = root.expires_at + .01
    elif fault == 'backwards':
        state.now = root.started - .01
    elif fault == 'generation':
        state.generation += 1
    elif fault == 'deadline':
        root.expires_at += 1.
    elif fault == 'stage':
        object.__setattr__(root.stage, 'phase', 'bootstrap')
    elif fault == 'leg':
        object.__setattr__(root.leg, 'destination_name', 'different')
    else:
        root._pulses = 1
    with pytest.raises(ValueError):
        root.check()
    assert not root.valid
    state.now, state.generation = 10., 1
    with pytest.raises(ValueError):
        root.reserve(ordinary_ticket(), bounds=bounds())


@pytest.mark.parametrize('fault', ('pretrip', 'future', 'hold_over_deadline', 'previous_stage'))
def test_proposal_must_belong_to_current_stage_and_fit_remaining_root_time(fault):
    root, state = budget()
    ticket = ordinary_ticket()
    if fault == 'pretrip':
        ticket = replace(ticket, proposed_at=9.9)
    elif fault == 'future':
        ticket = replace(ticket, proposed_at=10.1)
    elif fault == 'hold_over_deadline':
        state.now = root.expires_at - .1
        ticket = replace(ticket, proposed_at=state.now)
    else:
        state.now = 20.
        next_destination(root)
        ticket = ordinary_ticket(probe=True)
    with pytest.raises(ValueError, match='future-dated|deadline'):
        root.reserve(ticket, bounds=bounds())
    assert root.snapshot()['reserved_pulses'] == 0


@pytest.mark.parametrize('nested', ('reserve', 'advance', 'stop'))
def test_reentrant_callback_cannot_charge_or_advance_even_when_exception_is_caught(nested):
    root, state = budget()
    seen = []
    def callback():
        if seen:
            return
        seen.append(nested)
        try:
            if nested == 'reserve':
                root.reserve(ordinary_ticket(), bounds=bounds())
            elif nested == 'advance':
                root.advance(root.stage, 'crossing', zone_id=68)
            else:
                root.cancel('F9 during owner callback')
        except ValueError:
            pass
    state.callback = callback
    with pytest.raises(ValueError, match='reentered|F9'):
        root.reserve(ordinary_ticket(), bounds=bounds())
    assert root.stage.phase == 'walking' and root.snapshot()['reserved_pulses'] == 0
    assert not root.valid


def test_competing_threads_cannot_both_take_the_last_root_reservation():
    root, _ = budget(maximum_pulses=1)
    barrier = threading.Barrier(3)
    results = []
    def reserve():
        barrier.wait()
        try:
            results.append(root.reserve(ordinary_ticket(), bounds=bounds()))
        except ValueError:
            results.append(None)
    threads = [threading.Thread(target=reserve) for _ in range(2)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(2.)
        assert not thread.is_alive()
    assert sum(result is not None for result in results) == 1
    assert root.snapshot()['reserved_pulses'] == 1 and not root.valid


def test_last_clock_history_cannot_be_reset_to_hide_a_rollback():
    root, state = budget()
    state.now = 20.
    root.check()
    root.last_at = 10.
    state.now = 15.
    with pytest.raises(ValueError):
        root.check()
    assert not root.valid


@pytest.mark.parametrize('operation', ('check', 'reserve', 'advance'))
def test_second_owner_callback_cannot_spend_time_after_the_last_clock_sample(operation):
    root, state = budget()
    calls = []
    def callback():
        calls.append(True)
        if len(calls) == 2:
            state.now = root.expires_at + .01
    state.callback = callback
    with pytest.raises(ValueError, match='deadline'):
        if operation == 'check':
            root.check()
        elif operation == 'reserve':
            root.reserve(ordinary_ticket(), bounds=bounds())
        else:
            root.advance(root.stage, 'crossing', zone_id=68)
    assert not root.valid and root.snapshot()['reserved_pulses'] == 0
    assert root.stage.phase == 'walking'
