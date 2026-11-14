from pathlib import Path

import pytest

from eql_automation.location_log import RawLocationFix
from eql_automation.unbound_location_log import UnboundLocationReader


def line(body,second=1):
    return f'[Sat Nov 14 03:00:{second:02d} 2026] {body}\n'


def reader(tmp_path):
    p=tmp_path/'eqlog_Test_freeport.txt';p.write_text(line('Your Location is 9, 9, 9',0))
    return p,UnboundLocationReader(p,expected_character='Test',expected_server='freeport')


def append(p,body,second=1):
    with p.open('a') as f:f.write(line(body,second))


def test_fresh_stationary_fix_is_retained_without_inventing_a_zone(tmp_path):
    p,r=reader(tmp_path)
    assert r.poll(now=0)==[]
    append(p,'Your Location is -1.25, +2.5, 3')
    fix,=r.poll(now=1)
    assert fix.raw_coordinates==(-1.25,2.5,3.)
    assert not isinstance(fix,RawLocationFix) and not hasattr(fix,'zone_id')
    assert not any((fix.zone_binding_verified,fix.coordinates_aligned_to_wld,
                   fix.request_correlation_verified,fix.input_authorized))
    assert r.poll(now=2)==[]


@pytest.mark.parametrize('body',('LOADING, PLEASE WAIT...','You have entered The Greater Faydark.',
                                'Your Location is nan, 2, 3'))
def test_transition_or_malformed_location_refuses_the_whole_batch(tmp_path,body):
    p,r=reader(tmp_path);append(p,'Your Location is 1, 2, 3');append(p,body)
    with pytest.raises(ValueError):r.poll(now=1)
    assert r.latest is None and r.refused
    append(p,'Your Location is 4, 5, 6',2)
    with pytest.raises(ValueError):r.poll(now=2)


def test_replacement_never_replays_history_or_reuses_observation(tmp_path):
    p,r=reader(tmp_path);append(p,'Your Location is 1, 2, 3');r.poll(now=1)
    replacement=tmp_path/'replacement';replacement.write_text(line('Your Location is 9, 9, 9'))
    replacement.replace(p)
    with pytest.raises(ValueError):r.poll(now=2)
    assert r.latest is None


def test_partial_lines_and_chat_cannot_supply_a_location(tmp_path):
    p,r=reader(tmp_path)
    append(p,"Someone says, 'Your Location is 1, 2, 3'")
    with p.open('a') as f:f.write(line('Your Location is 4, 5, 6',2)[:-1])
    assert r.poll(now=1)==[]
    with p.open('a') as f:f.write('\n')
    assert r.poll(now=2)[0].raw_coordinates==(4.,5.,6.)


@pytest.mark.parametrize('bad_time',(float('nan'),float('inf'),True,-1.))
def test_invalid_or_reversed_receipt_clock_refuses_before_reading(tmp_path,bad_time):
    p,r=reader(tmp_path);r.poll(now=0);append(p,'Your Location is 1, 2, 3')
    before=r.tail.position
    with pytest.raises(ValueError):r.poll(now=bad_time)
    assert r.tail.position==before and r.refused


def test_reversed_client_clock_discards_even_a_prior_fix_in_the_batch(tmp_path):
    p,r=reader(tmp_path);append(p,'Your Location is 1, 2, 3',2);append(p,'A status message.',1)
    with pytest.raises(ValueError):r.poll(now=1)
    assert r.latest is None


def test_expected_identity_and_existing_log_are_required(tmp_path):
    with pytest.raises(ValueError):
        UnboundLocationReader(tmp_path/'wrong.txt',expected_character='Test',expected_server='freeport')
    with pytest.raises(ValueError):
        UnboundLocationReader(tmp_path/'eqlog_Test_freeport.txt',expected_character='Test',expected_server='freeport')
