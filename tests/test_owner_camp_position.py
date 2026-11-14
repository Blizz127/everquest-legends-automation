"""Actual retained sender/OS pipe and production height validation, synthetic scene."""
from datetime import timedelta
import time
from types import SimpleNamespace

import pytest

from eql_automation.camp_recovery import CampRecovery
from eql_automation.location_hotkey import OwnerLocationHotkey
from eql_automation.owner_journey_runtime import Journey
from eql_automation.owner_navigation_preflight import settings_identity
from eql_automation.owner_input_observer import OwnerInputObservation
from eql_automation.owner_route_trial import zone_binding
from eql_automation.owner_zone_tracker import ZoneReaderLease
from test_camp_floor_checkpoint import checkpoint
from test_source_motion import f
from test_route_floor_commit import legacy
from test_motion_collection import retained
from test_owner_journey_runtime import h
from test_route_step_sender import after_down


@pytest.fixture
def camp(h,checkpoint,monkeypatch):
    e=h.engine;f=checkpoint
    f.reader.tail.path.replace(h.log);f.reader.tail.path=h.log
    tracker=e.live_zone_tracker;tracker.reader=f.reader
    e.tail=e.make_tail();e.tail.poll()
    assert e.start_stationary_camp(),h.notices
    session=e.camp_session
    session.preparation_due=False
    import rotation_core
    e.profile={};e.rotation=rotation_core.Rotation(e.profile,7,damage_interval=4.)
    # The synthetic source fixture has a separate, monotonic wall-clock epoch.
    base_time=time.monotonic();base_wall=f.wall()
    e.camp_wall=lambda:base_wall+timedelta(seconds=time.monotonic()-base_time)
    j=e.journey=Journey(e.cancel_generation,settings_identity(e.settings),'camp',arrival_floor=f.checkpoint,
        continue_camps=getattr(h,'camp_continuation_enabled',False))
    hotkey=OwnerLocationHotkey.configured('F4',confirmation_id='synthetic-current-owner-test',
        configuration_paths=(h.game/'eqclient.ini',h.game/'Probe_private_LO1.ini'))
    class Observer:
        def sample(self):
            now=time.monotonic()
            return OwnerInputObservation(now,now,1,True,1,0,False,0,'synthetic camp devices')
        def close(self):h.observer_closed=True
    observer=Observer()
    token=SimpleNamespace(journey=j,sender=e.sender,gate=e.gate,tracker=tracker,
        zone=zone_binding(f.reader),window=(42,10,100),floor_checkpoint=f.checkpoint,
        pending={'observer':observer,'topology':1,'binding':hotkey},motion_basis=b'{}')
    e._retain_camp_input(token)
    # No old source observer may become active during camp.
    monkeypatch.setattr(f.observer,'check',lambda:pytest.fail('Old source observer resumed'))
    h.scope_journey=j;h.floor=f.checkpoint;h.collection_replies=[]
    def append(x=4.,y=2.,z=2.7):
        with f.reader.tail.path.open('a') as out:
            out.write(e.camp_wall().strftime('[%a %b %d %H:%M:%S %Y] ')+
                f'Your Location is {y}, {x}, {z}\n')
    h.position_reply=append
    def recovered(kills=1):
        now=time.monotonic();session.kills=kills;session.phase='recovery'
        r=session.recovery=CampRecovery(now-3,phase='stand_after_rest')
        r.submitted('/stand',now-2)
        r.sample(now-.8,now-.8,1.,1.);r.sample(now-.5,now-.5,1.,1.)
        assert r.phase=='recovered'
        e.hp=e.mana=1.;e.last_gauge=now;e.active=False;e.target_ready=False
        e.command_pause_until=0.;e.rotation.busy_until=0.
        e._camp_recovery_tick(session,now)
    h.recovered=recovered
    def reply():
        p=e.camp_position
        if p is not None and p.sending:
            h.collection_replies.append(p.request.serial);h.position_reply()
    after_down(monkeypatch,reply)
    return h


def finish(h):
    deadline=time.monotonic()+10.
    while h.engine.camp_position is not None and time.monotonic()<deadline:
        h.tick();h.drain();time.sleep(.01)
    assert h.engine.camp_position is None,h.notices
    h.drain()


def test_first_recovered_kill_collects_fresh_pair_then_resumes_same_camp(camp):
    h=camp;e=h.engine;session=e.camp_session
    # Initial preparation recovery must not perform a pointless check.
    h.recovered(kills=0)
    assert e.camp_position is None and not h.events
    h.recovered();p=e.camp_position
    assert p is not None and p.floor is h.floor and p.lease.reader is h.floor._reader
    assert p.collector.seq==p.baseline and not e.allowed()
    finish(h)
    assert e.camp_session is session and session.phase=='select' and h.scope_journey.height_check_done,h.notices
    assert not h.commands and not e.sender.held and e.live_zone_tracker.lease is None
    assert h.collection_replies==[0,1]
    assert [event for event in h.events if event[0]==1 and event[2]==1]==[(1,62,1)]*2
    assert all(kind!=1 or key==62 for kind,key,value in h.events)
    result=e.camp_position_last_result
    assert result['height']['raw_z_minus_source_z']==2.5
    assert not result['height']['old_calibration_renewed'] and not result['movement_sent']
    assert result['height']['minimum_log_seq']==p.baseline
    assert all(row['log_line_seq']>p.baseline for row in result['height']['observations'])
    assert not result['real_client_accepted'] and h.floor.valid
    before=list(h.events);h.recovered(kills=2);h.drain()
    assert e.camp_position is None and h.events==before and session.phase=='select'


@pytest.mark.parametrize('mode',('F9','F8'))
def test_stop_after_second_down_releases_key_before_returning_reader(camp,monkeypatch,mode):
    h=camp;e=h.engine;released=[];stopped=[]
    e.prepared=True;e.prepared_level=7
    release=ZoneReaderLease.release
    def checked_release(lease):
        if stopped and lease is stopped[0].lease:
            assert getattr(e.sender,'_eql_route_operation',None) is None
            h.drain();keys=[v for v in h.events if v[0]==1]
            second=next(i for i,v in enumerate(keys) if v==(1,62,1) and i>0)
            assert (1,62,0) in keys[second+1:]
            released.append(lease)
        return release(lease)
    monkeypatch.setattr(ZoneReaderLease,'release',checked_release)
    def stop():
        p=e.camp_position
        if p is not None and p.request is not None and p.request.serial==1:
            stopped.append(p)
            if mode=='F8':e.handle_job('arm',e.cancel_generation)
            else:e.stop_action('F9 during second hotbutton')
            assert not p.lease.active and p.tracker.lease is p.lease
            assert getattr(e.sender,'_eql_route_operation',None) is not None
            assert e._navigation_busy() and not e.active
    after_down(monkeypatch,stop)
    h.recovered();finish(h)
    assert stopped and released==[stopped[0].lease]
    assert e.journey is None and e.camp_session is None and e.live_zone_tracker.lease is None
    assert e.camp_position_last_result['outcome']=='stopped' and not h.scope_journey.height_check_done
    assert not e.sender.held and not h.floor.valid
    if mode=='F8':
        assert e._journey_assist is not None
        before=list(h.events);h.tick();h.drain()
        assert e.active and h.events==before and not h.commands
        assert e.camp_position is None and e.journey is None


@pytest.mark.parametrize('change',('focus','settings','floor','hotkey','other_lease'))
def test_changed_scope_refuses_before_request(camp,change):
    h=camp;e=h.engine;h.recovered();p=e.camp_position
    if change=='focus':h.focused=False
    elif change=='settings':e.settings.level+=1
    elif change=='floor':h.floor.invalidate('changed floor')
    elif change=='hotkey':(h.game/'eqclient.ini').write_text('changed configuration')
    else:p.tracker.lease=ZoneReaderLease(p.tracker)
    finish(h)
    assert e.camp_session is None and not h.events and not h.commands
    assert e.camp_position_last_result['outcome']=='stopped' and not p.lease.active


def test_preacquisition_reply_is_drained_not_reused(camp):
    h=camp;e=h.engine;h.position_reply()
    h.recovered();p=e.camp_position
    assert p.reader.latest is None and p.collector.first is None
    finish(h)
    assert h.collection_replies==[0,1] and e.camp_position_last_result['outcome']=='complete'
    assert p.collector.first.log_line_seq==p.baseline+1


def test_wrong_postcombat_height_never_resumes_camp(camp):
    h=camp;e=h.engine;append=h.position_reply
    h.position_reply=lambda:append(z=9.7)
    h.recovered();finish(h)
    assert e.camp_session is None and e.camp_position_last_result['outcome']=='stopped'
    assert any('heights disagree' in str(v) for v in h.notices),h.notices


def test_actual_travel_handoff_floor_supplies_new_camp_pair(h,monkeypatch):
    from test_owner_source_travel import configure
    from test_owner_journey_runtime import start
    from test_owner_route_trial import finish as finish_route
    from eql_automation.source_observer import SourceItineraryObserver
    import rotation_core
    e=h.engine;configure(h,monkeypatch)
    check=SourceItineraryObserver.check
    def source_check(observer):
        assert e.journey is None or e.journey.phase!='camp'
        return check(observer)
    monkeypatch.setattr(SourceItineraryObserver,'check',source_check)
    start(h);h.due_trial();route=finish_route(h,timeout=80.)
    assert route['outcome']=='arrived' and route['continuation']['camp_started'],h.notices
    camp=e.camp_session;floor=e.journey.arrival_floor
    assert e.journey.location_binding is not None and floor.valid
    # Synthetic completed spell preparation, kill and recovery: this case tests
    # the real travel-owned floor and new collection, not combat behavior.
    camp.preparation_due=False;e.rotation=rotation_core.Rotation({},7)
    now=time.monotonic();camp.kills=1;camp.phase='recovery'
    camp.recovery=CampRecovery(now-3,phase='stand_after_rest')
    camp.recovery.submitted('/stand',now-2)
    camp.recovery.sample(now-.8,now-.8,1.,1.);camp.recovery.sample(now-.5,now-.5,1.,1.)
    e.active=False;e.target_ready=False;e.hp=e.mana=1.;e.last_gauge=now
    e.command_pause_until=0.
    def reply():
        if e.camp_position is not None and e.camp_position.sending:
            h.append('Your Location is '+', '.join(f'{v:.2f}' for v in h.point))
    after_down(monkeypatch,reply)
    h.drain();prior=len(h.events)
    e._camp_recovery_tick(camp,now);assert e.camp_position is not None,h.notices
    finish(h)
    assert e.camp_session is camp and camp.phase=='select',h.notices
    assert e.camp_position_last_result['height']['checkpoint_sha256']==floor.sha256
    assert e.journey.height_check_done and not h.commands and not e.sender.held
    assert all(kind!=1 or key==62 for kind,key,value in h.events[prior:])
    assert [v for v in h.events[prior:] if v[0]==1 and v[2]==1]==[(1,62,1)]*2
