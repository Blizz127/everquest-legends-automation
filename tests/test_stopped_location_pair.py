from datetime import datetime,timedelta
from types import SimpleNamespace

import pytest

from eql_automation.motion_collection import CommandReceipt
from eql_automation.owner_zone_tracker import LiveZoneTracker
from eql_automation.stopped_location_pair import StoppedLocationPair


def setup(tmp_path):
    h=SimpleNamespace(now=100.,owner=('same-session',))
    clock=lambda:h.now
    wall=lambda:datetime(2026,11,14,12)+timedelta(seconds=h.now-100.)
    log=tmp_path/'eqlog_Probe_private.txt';log.touch()
    zones=tmp_path/'ZoneNames.txt';zones.write_text('54^Fixture^0^0\n')
    h.tracker=LiveZoneTracker(log,zones,expected_character='Probe',expected_server='private',
        binding_reader=lambda:h.owner,clock=clock)
    def append(body='Your Location is 1, 2, 3'):
        with log.open('a') as out:out.write(wall().strftime('[%a %b %d %H:%M:%S %Y] ')+body+'\n')
    h.append=append
    append('You have entered Fixture.');h.tracker.poll();h.lease=h.tracker.acquire()
    h.s=StoppedLocationPair(h.lease,released_at=99.8,check_current=lambda:None,
        clock=clock,local_wall_clock=wall)
    def request():
        r=h.s.tick();h.s.command_sent(r,CommandReceipt(h.now,h.now));return r
    h.request=request
    return h


def test_pair_collects_two_new_replies_and_keeps_exact_reader_objects(tmp_path):
    h=setup(tmp_path);h.request();h.append();h.s.tick()
    first=h.s.first;h.now+=.5;h.request();h.append();h.s.tick()
    assert h.s.phase=='complete' and h.s.first is first
    assert h.s.second is h.lease.reader.latest
    assert len(h.s.snapshot()['requests'])==2
    assert not h.s.snapshot()['request_correlation_verified']


@pytest.mark.parametrize('change',['duplicate','unsolicited','transition','reset','timeout','owner','moved'])
def test_missing_or_ambiguous_feedback_stops_collection(tmp_path,change):
    h=setup(tmp_path)
    if change=='unsolicited':h.append()
    else:
        h.request()
        if change=='duplicate':h.append();h.append()
        elif change=='transition':h.append('LOADING, PLEASE WAIT...')
        elif change=='reset':h.lease.reader.tail.path.write_text('replacement\n')
        elif change=='timeout':h.now+=3
        elif change=='owner':h.owner=('other-session',)
        elif change=='moved':
            h.append();h.s.tick();h.now+=.5;h.request();h.append('Your Location is 2, 2, 3')
    with pytest.raises(ValueError):h.s.tick()
    assert h.s.phase=='stopped'


def test_cancellation_or_clock_change_inside_current_callback_refuses(tmp_path):
    h=setup(tmp_path)
    h.s.check_current=lambda:h.s.cancel('owner stop from callback')
    with pytest.raises(ValueError):h.s.tick()
    assert h.s.phase=='stopped' and not h.s.requests
