"""Continuous log history across a real synthetic arrival/lease handoff."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from eql_automation.destination_arrival_veto import continue_destination_veto
from eql_automation.scene_log_veto import SceneLogVeto
from eql_automation.zone_arrival import ZoneArrivalHandoff
from test_zone_arrival import h, enter


def complete(h):
    enter(h)
    h.ready = True
    h.send(h.tick(.13))
    assert h.tick() is None
    h.send(h.tick(.41))
    assert h.tick() is None
    assert h.session.phase == 'complete'


def test_transfer_preserves_cursor_history_pair_and_lease_without_input(h):
    complete(h)
    a, r = h.session, h.lease.reader
    previous = a.veto
    old_tail = vars(previous.tail).copy()
    old_time, old_seq = previous._last_log_time, previous._line_seq
    old_finished = previous._last_finished
    final_fix, releases, requests = r.latest, list(h.releases), list(h.requests)
    veto = continue_destination_veto(a)
    assert type(veto) is SceneLogVeto and veto is not previous
    assert veto.tail is not previous.tail and vars(veto.tail) == old_tail
    assert veto.cancel_generation == previous.cancel_generation
    assert veto._last_log_time == old_time and veto._line_seq == old_seq
    assert veto._last_finished >= old_finished
    assert veto.classify('LOADING, PLEASE WAIT...') == 'zone_transition'
    assert veto.classify('You have entered Clan Crushbone.') == 'zone_transition'
    assert a.phase == 'stopped' and a.collector.phase == 'complete'
    assert r.latest is final_fix and h.lease.active
    assert h.releases == releases and h.requests == requests
    assert not veto.poll().input_authorized


@pytest.mark.parametrize('body,reason', [
    ('a bat hits YOU for 3 points of damage.', 'incoming_attack'),
    ('You have been slain by a bat!', 'death'),
    ('LOADING, PLEASE WAIT...', 'zone_transition'),
    ('You have entered Clan Crushbone.', 'zone_transition'),
    ('You have entered Butcherblock Mountains.', 'zone_transition'),
])
@pytest.mark.parametrize('when', ['before_transfer', 'current_callback', 'after_transfer'])
def test_no_gap_or_expected_transition_exemption(h, body, reason, when):
    complete(h)
    a = h.session
    releases, requests = list(h.releases), list(h.requests)
    if when == 'before_transfer':
        h.append(body)
    elif when == 'current_callback':
        h.current = lambda: h.append(body)
    if when == 'after_transfer':
        veto = continue_destination_veto(a)
        h.append(body)
        assert veto.poll().reason == reason
    else:
        with pytest.raises(ValueError, match=reason):
            continue_destination_veto(a)
        veto = a._destination_log_veto
    assert veto.poll().reason == reason
    assert h.releases == releases and h.requests == requests


@pytest.mark.parametrize('kind', ['replace', 'truncate', 'partial', 'backward_time'])
def test_transfer_keeps_continuity_guards(h, kind):
    complete(h)
    a = h.session
    if kind == 'replace':
        other = h.log.with_suffix('.replacement')
        other.write_text('new unrelated log\n')
        other.replace(h.log)
    elif kind == 'truncate':
        h.log.write_text('new\n')
    elif kind == 'partial':
        with h.log.open('a') as out:
            out.write('[unfinished')
    else:
        h.now -= 5
        h.append('You say, quiet.')
        h.now += 5
    with pytest.raises(ValueError, match='observer veto'):
        continue_destination_veto(a)
    assert a._destination_log_veto.poll().reason is not None


def test_latched_reason_and_observation_survive_claim(h):
    complete(h)
    a = h.session
    h.append('a bat hits YOU for 3 points of damage.')
    latched = a.veto.poll()
    with pytest.raises(ValueError, match='incoming_attack'):
        continue_destination_veto(a)
    veto = a._destination_log_veto
    assert veto._latched is latched and veto.poll() is latched
    assert veto._last_log_time == a.veto._last_log_time
    assert veto.cancel_generation == latched.cancel_generation


def test_duplicate_claim_and_stale_arrival_tick_never_consume_or_release(h):
    complete(h)
    a = h.session
    veto = continue_destination_veto(a)
    before = (veto.tail.position, a.veto.tail.position, a.reader.tail.position)
    releases = list(h.releases)
    final_fix = a.reader.latest
    h.append('LOADING, PLEASE WAIT...')
    with pytest.raises(ValueError, match='unclaimed'):
        continue_destination_veto(a)
    with pytest.raises(ValueError, match='transferred'):
        a.tick()
    assert before == (veto.tail.position, a.veto.tail.position, a.reader.tail.position)
    assert h.releases == releases and a.reader.latest is final_fix
    assert veto.poll().reason == 'zone_transition'


def test_retired_expected_observer_cannot_advance_new_cursor(h):
    complete(h)
    a = h.session
    veto = continue_destination_veto(a)
    at = veto.tail.position
    h.append('LOADING, PLEASE WAIT...')
    assert a.veto.poll().reason is None  # An old external reference.
    assert veto.tail.position == at
    assert veto.poll().reason == 'zone_transition'


def test_appended_benign_lines_are_counted_without_new_eof_baseline(h):
    complete(h)
    a = h.session
    old_position, old_sequence = a.veto.tail.position, a.veto._line_seq
    h.append('You say, the first appended line.')
    h.append('You say, the second appended line.')
    veto = continue_destination_veto(a)
    assert a.veto.tail.position == old_position
    assert veto.tail.position == h.log.stat().st_size
    assert veto._line_seq == old_sequence + 2
    h.append('a bat hits YOU for 3 points of damage.')
    assert veto.poll().reason == 'incoming_attack'
    assert veto._line_seq == old_sequence + 3


@pytest.mark.parametrize('body', ['LOADING, PLEASE WAIT...', 'a bat hits YOU for 3 points of damage.'])
def test_final_current_callback_append_is_scanned_before_return(h, body):
    complete(h)
    calls = []
    def current():
        calls.append(True)
        if len(calls) == 2:
            h.append(body)
    h.current = current
    with pytest.raises(ValueError, match='observer veto'):
        continue_destination_veto(h.session)


def test_callback_reentrant_claim_is_refused_before_any_read(h):
    complete(h)
    a = h.session
    cursor = a.veto.tail.position
    def current():
        with pytest.raises(ValueError, match='unclaimed'):
            continue_destination_veto(a)
        assert a.veto.tail.position == cursor
    h.current = current
    veto = continue_destination_veto(a)
    assert type(veto) is SceneLogVeto


def test_cancellation_callback_cannot_be_hidden_by_retiring_arrival(h):
    complete(h)
    a = h.session
    releases = len(h.releases)
    h.current = lambda: a.cancel('F9 during transfer')
    with pytest.raises(ValueError, match='context changed'):
        continue_destination_veto(a)
    assert a.phase == 'stopped' and a.reader.latest is None
    # Only the cancellation explicitly invoked by the callback releases.
    assert len(h.releases) == releases + 1


@pytest.mark.parametrize('change', ['owner', 'generation', 'deadline'])
def test_late_observation_clock_callback_cannot_return_a_current_observer(h, change):
    complete(h)
    a = h.session
    calls = []
    def clock():
        calls.append(True)
        if len(calls) == 3:  # First strict poll's completion clock.
            if change == 'owner':
                h.owner = ('different',)
            elif change == 'generation':
                a.reader.zone_generation += 1
            else:
                h.now += 100
        return h.now
    a.clock = a.veto.clock = clock
    releases = list(h.releases)
    with pytest.raises(ValueError):
        continue_destination_veto(a)
    assert h.releases == releases


@pytest.mark.parametrize('change', ['owner', 'revoked', 'generation', 'final_fix',
    'collector', 'old_observer_consumed', 'callback_generation', 'callback_reader'])
def test_current_lease_owner_generation_and_final_pair_required(h, change):
    complete(h)
    a = h.session
    if change == 'owner':
        h.owner = ('different',)
    elif change == 'revoked':
        h.lease.active = False
    elif change == 'generation':
        a.reader.zone_generation += 1
    elif change == 'final_fix':
        a.reader.latest = replace(a.reader.latest, raw_coordinates=(0., 0., 0.))
    elif change == 'collector':
        a.collector.phase = 'await_location'
    elif change == 'old_observer_consumed':
        h.append('LOADING, PLEASE WAIT...')
        assert a.veto.poll().reason is None
    elif change == 'callback_generation':
        h.current = lambda: setattr(a.reader, 'zone_generation', a.reader.zone_generation + 1)
    else:
        def consume():
            h.append('You say, a late callback.')
            a.reader.poll(now=h.now)
        h.current = consume
    releases = list(h.releases)
    with pytest.raises(ValueError):
        continue_destination_veto(a)
    assert h.releases == releases


def test_only_exact_completed_arrival_can_be_claimed(h):
    with pytest.raises(ValueError):
        continue_destination_veto(h.session)
    with pytest.raises(ValueError):
        continue_destination_veto(SimpleNamespace(phase='complete'))
    complete(h)
    class PretendArrival(ZoneArrivalHandoff):
        pass
    fake = PretendArrival.__new__(PretendArrival)
    fake.__dict__.update(h.session.__dict__)
    with pytest.raises(ValueError):
        continue_destination_veto(fake)
