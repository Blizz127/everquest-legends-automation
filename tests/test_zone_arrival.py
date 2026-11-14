"""Real log/lease/pair implementations with explicit synthetic time and release."""
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from eql_automation.motion_collection import CommandReceipt, LocationRequest
from eql_automation.owner_zone_tracker import LiveZoneTracker
from eql_automation.zone_arrival import ZoneArrivalHandoff


@pytest.fixture
def h(tmp_path):
    h=SimpleNamespace(now=100.,owner=('Probe','private',42,10,100),ready=False,
        held={103},releases=[],requests=[],current=lambda:None,ready_hook=lambda:None,
        release_hook=lambda:None)
    base=datetime.now().replace(microsecond=0)
    h.wall=lambda:base+timedelta(seconds=h.now-100)
    h.log=tmp_path/'eqlog_Probe_private.txt';h.log.write_text('old log\n')
    catalog=tmp_path/'ZoneNames.txt'
    catalog.write_text('54^The Greater Faydark^0^0\n58^Clan Crushbone^0^0\n68^Butcherblock Mountains^0^0\n')
    h.clock=lambda:h.now
    def append(body):
        with h.log.open('a') as out:out.write(h.wall().strftime('[%a %b %d %H:%M:%S %Y] ')+body+'\n')
    h.append=append
    tracker=LiveZoneTracker(h.log,catalog,expected_character='Probe',expected_server='private',
        binding_reader=lambda:h.owner,clock=h.clock)
    append('You have entered The Greater Faydark.');tracker.poll();h.lease=tracker.acquire()
    def release():
        start=h.now;h.release_hook();h.held.clear();h.now+=.001
        r=CommandReceipt(start,h.now);h.releases.append(r);return r
    def ready():h.ready_hook();return h.ready
    h.session=ZoneArrivalHandoff(h.lease,'Clan Crushbone',release_controls=release,
        ready_for_location=ready,check_current=lambda:h.current(),clock=h.clock,local_wall_clock=h.wall)
    def tick(dt=.01):h.now+=dt;return h.session.tick()
    h.tick=tick
    def send(request,body='Your Location is -12, 34, 5'):
        assert isinstance(request,LocationRequest) and h.session.phase=='locating'
        h.requests.append(request);began=h.now;h.now+=.03
        h.session.command_sent(request,CommandReceipt(began,h.now));append(body)
    h.send=send
    yield h
    h.lease.release();tracker.close()


def enter(h):
    h.append('LOADING, PLEASE WAIT...');assert h.tick() is None
    assert h.tick(2) is None
    h.append('You have entered Clan Crushbone.');assert h.tick() is None


def test_expected_crossing_releases_before_location_and_collects_new_stopped_pair(h):
    assert h.tick() is None and h.held=={103} and not h.requests
    h.append('LOADING, PLEASE WAIT...');assert h.tick() is None
    assert not h.held and len(h.releases)==1 and h.session.phase=='loading'
    assert h.tick(2) is None and not h.requests
    h.append('You have entered Clan Crushbone.');assert h.tick() is None
    assert h.session.phase=='await_ready' and not h.requests
    h.ready=True
    assert h.tick() is None  # Entry also starts a new stopped-settling interval.
    h.send(h.tick(.13));assert h.tick() is None
    h.send(h.tick(.41));assert h.tick() is None
    assert h.session.phase=='complete' and len(h.requests)==2
    first,second=h.session.collector.first,h.session.collector.second
    assert first.zone_id==second.zone_id==58 and first.log_line_seq+1==second.log_line_seq
    assert first.raw_coordinates==second.raw_coordinates==(-12.,34.,5.)
    record=h.session.snapshot()
    assert not record['source_navigation_state_reused'] and not record['spawn_coordinate_verified']
    assert not record['crossing_movement_authorized'] and not record['real_client_accepted']
    assert h.tick() is None and len(h.requests)==2


@pytest.mark.parametrize('body',['a bat hits YOU for 3 points of damage.',
    'You have been slain by a bat!','Targeted (NPC): a bat','Auto attack is on.',
    'YOU are drowning!'])
@pytest.mark.parametrize('phase',['same_loading_batch','after_loading','after_entry','collecting'])
def test_arrival_keeps_all_hazards_after_expected_transition(h,body,phase):
    h.append('LOADING, PLEASE WAIT...')
    if phase!='same_loading_batch':h.tick()
    if phase in ('after_entry','collecting'):
        h.append('You have entered Clan Crushbone.');h.tick()
    if phase=='collecting':
        h.ready=True;h.send(h.tick(.2));h.tick()
    h.append(body)
    with pytest.raises(ValueError,match='hazard'):h.tick()
    assert h.session.phase=='stopped' and not h.held
    assert len(h.requests)==(1 if phase=='collecting' else 0)


def test_ready_callback_hazard_cannot_issue_a_location_request(h):
    enter(h);h.ready=True
    h.ready_hook=lambda:h.append('You have been slain by a bat!')
    with pytest.raises(ValueError,match='hazard'):h.tick(.2)
    assert not h.requests and h.session.phase=='stopped'


@pytest.mark.parametrize('change', ['wrong_zone','entry_without_loading','logging','malformed_logging',
    'duplicate_loading','position_while_loading','unsolicited_arrival','old_entry','partial','reset',
    'external_consumer','owner_changed','timeout'])
def test_invalid_crossing_stops_and_releases_without_location_requests(h,change):
    if change=='entry_without_loading':h.append('You have entered Clan Crushbone.')
    else:
        h.append('LOADING, PLEASE WAIT...');h.tick()
        if change=='wrong_zone':h.append('You have entered Butcherblock Mountains.')
        elif change=='logging':h.append("Logging to 'eqlog.txt' is now *ON*.")
        elif change=='malformed_logging':
            with h.log.open('a') as out:out.write("[bad] Logging to 'eqlog.txt' is now *OFF*.\n")
        elif change=='duplicate_loading':h.append('LOADING, PLEASE WAIT...')
        elif change=='position_while_loading':h.append('Your Location is 1, 2, 3')
        elif change=='unsolicited_arrival':
            h.append('You have entered Clan Crushbone.');h.append('Your Location is 1, 2, 3')
        elif change=='old_entry':h.append('You have entered Clan Crushbone.');h.now+=10
        elif change=='partial':
            with h.log.open('a') as out:out.write('[unfinished')
        elif change=='reset':
            replacement=h.log.with_suffix('.new');replacement.write_text('new log\n');replacement.replace(h.log)
        elif change=='external_consumer':
            h.append('You have entered Clan Crushbone.');h.lease.reader.poll(now=h.now)
        elif change=='owner_changed':h.owner=('Different player',)
        elif change=='timeout':h.now+=91
    with pytest.raises(ValueError):h.tick()
    assert h.session.phase=='stopped' and not h.held and not h.requests
    assert h.lease.reader.latest is None


@pytest.mark.parametrize('where',['release','ready','current','request'])
def test_cancellation_inside_callbacks_cannot_start_or_complete_destination(h,where):
    if where=='release':
        h.release_hook=lambda:h.session.cancel('F9 during release')
        h.append('LOADING, PLEASE WAIT...')
    else:
        enter(h);h.ready=True
        if where=='ready':h.ready_hook=lambda:h.session.cancel('F9 during ready')
        elif where=='current':h.current=lambda:h.session.cancel('F9 before poll')
        else:
            h.tick(.2)
            request=h.session.collector.pending
            h.session.cancel('F9 before location key')
            with pytest.raises(ValueError):h.session.command_sent(request,CommandReceipt(h.now,h.now))
            assert not h.requests and not h.held
            return
    with pytest.raises(ValueError):h.tick(.2)
    assert h.session.phase=='stopped' and not h.requests and not h.held


def test_motion_after_entry_does_not_produce_a_stopped_pair(h):
    enter(h);h.ready=True;h.tick(.2)
    h.send(h.session.collector.pending);h.tick()
    h.send(h.tick(.41),'Your Location is -10, 34, 5')
    with pytest.raises(ValueError,match='remain stopped'):h.tick()
    assert h.session.phase=='stopped' and not h.held


def test_new_zone_during_destination_pair_stops(h):
    enter(h);h.ready=True;h.tick(.2)
    h.send(h.session.collector.pending);h.append('LOADING, PLEASE WAIT...')
    with pytest.raises(ValueError):h.tick()
    assert h.session.phase=='stopped' and h.lease.reader.latest is None and not h.held


@pytest.mark.parametrize('append_entry',[False,True])
def test_reentrant_poll_cannot_erase_loading_without_releasing(h,append_entry):
    polled=[]
    def current():
        r=h.lease.reader
        if not polled and any(e.kind=='loading' for e in r.boundaries):
            polled.append(True)
            if append_entry:h.append('You have entered Clan Crushbone.')
            r.poll(now=h.now)
    h.current=current;h.append('LOADING, PLEASE WAIT...')
    if append_entry:
        with pytest.raises(ValueError,match='lease changed'):h.tick()
        assert h.session.phase=='stopped'
    else:
        assert h.tick() is None and h.session.phase=='loading'
    assert polled and len(h.releases)==1 and not h.held and not h.requests
