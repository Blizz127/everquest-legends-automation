"""Real route/controller/ground/log pipeline; synthetic scene and pipe input."""
from datetime import datetime,timedelta
import os
import time
from types import SimpleNamespace

import pytest

from eql_automation.fixed_route_follower import FixedRouteFollower,RouteHalt
from eql_automation.floor_replay import check_floor_trial
from eql_automation.g2_pulse_budget import G2Scene
from eql_automation.ground_sweep import GroundFace,check_ground_coverage
from eql_automation.location_log import LocationLogReader
from eql_automation.motion_collection import CommandReceipt,LocationRequest
from eql_automation.route_floor_commit import RouteFloorCommit
from eql_automation.route_session import RouteSession,RouteSessionDriver,RouteStepRequest
from eql_automation.route_step_sender import RouteStepAuthorization
from eql_automation.uinput_watchdog import _EVENT
from test_route_floor_commit import legacy,setup
from test_route_step_sender import PipeSender


def make(tmp_path,legacy,*,real=False,lock=None,tracked_zone=False):
    h=SimpleNamespace(now=100.,mode='measurement',generation=1,window=42,
        point=(1.,2.,.6),events=[],commands=[],refs=[],chain_reads=[],hook=lambda:None)
    h.clock=time.monotonic if real else lambda:h.now
    f=setup(legacy,clock=h.clock,lock=lock)
    r=f.runner
    runner=FixedRouteFollower(r.route,legacy=legacy,motion=r.motion,heading=90.,
        calibration_record_id=r.calibration,height_calibration=r.height_calibration,
        geometry_evidence=r.geometry_evidence,generation=1,generation_reader=lambda:h.generation,
        mode_reader=lambda:h.mode)
    ledger=RouteFloorCommit(runner,f.chain,stop_lock=f.lock,clock=h.clock)
    h.log=tmp_path/'eqlog_Probe_private.txt';h.log.touch()
    zones=tmp_path/'ZoneNames.txt';zones.write_text('54^Fixture^0^0\n')
    start=h.clock();wall=datetime.now() if real else datetime(2026,11,14,7)
    h.wall=lambda:wall+timedelta(seconds=h.clock()-start)
    def append(body):
        with h.log.open('a') as out:out.write(h.wall().strftime('[%a %b %d %H:%M:%S %Y] ')+body+'\n')
    h.append=append
    if tracked_zone:
        from eql_automation.owner_zone_tracker import LiveZoneTracker
        h.tracker=LiveZoneTracker(h.log,zones,expected_character='Probe',expected_server='private',
            binding_reader=lambda:(h.window,'Probe','private'),clock=h.clock)
        h.reader=h.tracker.reader
        append('You have entered Fixture.');h.tracker.poll()
        h.zone_lease=h.tracker.acquire()
    else:
        h.reader=LocationLogReader(h.log,zones,expected_character='Probe',expected_server='private')
        append('You have entered Fixture.');h.reader.poll(now=h.clock())
        h.zone_lease=None
    assert h.reader.tail.epoch==1 and h.reader.zone_generation==1
    h.session=RouteSession(ledger,h.reader,f.observer,initial_release_at=h.clock(),
        binding_reader=lambda:(h.window,'Probe','private'),record_id='synthetic-route-loop',local_wall_clock=h.wall,
        zone_lease=h.zone_lease)
    h.f,h.runner,h.ledger=f,runner,ledger
    h.rd,h.wr=os.pipe();h.sender=PipeSender(h.wr)
    def location(request):
        began=h.clock();h.commands.append(request)
        x,y,z=h.point
        append('Your Location is %.2f, %.2f, %.2f'%(y,x,z-.6+.2+2.5))
        h.hook()
        h.driver.tick()
        return CommandReceipt(began,h.clock())
    h.location=location
    def scene(reference):
        h.refs.append(reference)
        raw=reference.raw_fix
        return G2Scene(h.clock(),runner.route.zone,raw.raw_coordinates,
            raw.log_epoch,raw.log_line_seq,raw.zone_generation,True,True,True,True,True,True,True)
    def prepare(proposal,observed):
        x,y,z=observed.reference_fix.mesh_projection.package_xyz
        footprint=((x-.1,y-.1),(x+.8,y-.1),(x+.8,y+.1),(x-.1,y+.1))
        detail=f.observer.mesh._detail
        ground=SimpleNamespace(polys=(0,0,1,1),triangles=detail,areas=(63,63),components=(7,7))
        view=SimpleNamespace(ground=ground,seams=(),by_polygon={},source_faces_for_footprint=lambda _:f.sources)
        def check(req,base):
            faces=tuple(GroundFace(v,63,7) for v in detail)
            original=check_ground_coverage(req.footprint,faces,reference=(x,y,z),component=7,vertical_window=1.)
            return check_floor_trial(view,base,original,req.footprint,(0,1,2,3),
                reference=(x,y,z),component=7,vertical_window=1.,maximum_source_z_difference=1.)
        duration=runner.suggest_hold(proposal,minimum_seconds=.005,maximum_seconds=.02)
        return ledger.stage(proposal,reference_fix=observed.reference_fix,footprint=footprint,
            sources=f.sources,requested_seconds=duration,maximum_actual_hold=.08,movement_key=103,
            motion_bounds_record_id='synthetic-speed-and-body-bound',check_geometry=check)
    def authorize(ticket,observed):
        return RouteStepAuthorization(ticket,observed.reference_fix,h.clock(),
            ticket.preparation.proposal.at+.05,'synthetic-scene-guard')
    h.driver=RouteSessionDriver(h.session,h.sender,request_location=location,sample_scene=scene,
        prepare_step=prepare,authorize_step=authorize,still_authorized=lambda *_:True,
        command_state_clear=lambda:True,pump=lambda:None)
    original_observe=f.observer.observe
    def observe(*args,**kwargs):
        h.chain_reads.append(kwargs['floor_chain'])
        return original_observe(*args,**kwargs)
    f.observer.observe=observe
    def tick():
        if real:time.sleep(.01)
        else:h.now+=.025
        count=len(h.session.steps)
        h.driver.tick()
        if len(h.session.steps)>count:
            # Physical feedback is synthetic and based on actual pipe hold
            # receipt, not a position supplied by the route controller.
            receipt=h.session.steps[-1]['receipt']
            duration=receipt['up_completed_at']-receipt['down_started_at']
            h.point=(h.point[0]+10.*duration,h.point[1],h.point[2])
    h.tick=tick
    def close():
        if h.zone_lease is not None:h.zone_lease.release()
        os.close(h.wr)
        data=b''
        while chunk:=os.read(h.rd,4096):data+=chunk
        os.close(h.rd)
        h.events=[(kind,key,value) for _,_,kind,key,value in _EVENT.iter_unpack(data)]
    h.close=close
    return h


@pytest.mark.parametrize('change',['none','revoke','release','process'])
def test_tracked_reader_handoff_enters_route_and_honors_revocation(tmp_path,legacy,change):
    h=make(tmp_path,legacy,tracked_zone=True)
    try:
        request=first_request(h)
        assert h.session.reader is h.zone_lease.reader
        if change=='revoke':h.tracker.revoke_lease()
        elif change=='release':h.zone_lease.release()
        elif change=='process':h.window+=1
        if change=='none':
            h.session.command_sent(request,CommandReceipt(h.clock(),h.clock()))
            h.append('Your Location is 2.00, 1.00, 2.70')
            cursor=h.reader.tail.position
            h.tracker.poll()
            assert h.reader.tail.position==cursor
            h.now+=.01;h.session.tick()
            assert h.session.first.raw_fix is h.reader.latest
        else:
            with pytest.raises(RouteHalt):h.session.tick()
            assert h.session.phase=='stopped'
        assert not h.session.steps and not h.sender.held
    finally:h.close()
    assert not h.events


@pytest.fixture
def session(tmp_path,legacy):
    h=make(tmp_path,legacy)
    yield h
    h.close()


def first_request(h):
    h.now+=.125
    action=h.session.tick();assert isinstance(action,LocationRequest)
    return action


def accept_reply(h,request,*,point=(1.,2.,.6)):
    h.session.command_sent(request,CommandReceipt(h.clock(),h.clock()))
    x,y,z=point
    h.append('Your Location is %.2f, %.2f, %.2f'%(y,x,z+2.1))
    h.now+=.01
    return h.session.tick()


def test_initial_two_fixes_use_actual_ground_producer_and_exact_reference(session):
    h=session
    assert h.session.tick() is None
    first=first_request(h);assert accept_reply(h,first) is None
    assert h.session.first.raw_fix is h.reader.latest
    h.now+=.41
    second=h.session.tick();action=accept_reply(h,second)
    assert isinstance(action,RouteStepRequest)
    assert action.reference is h.session.reference
    assert h.session.reference.raw_fix is h.reader.latest
    assert h.runner.phase=='ready' and h.session.phase=='stepping'
    assert h.chain_reads==[h.f.chain,h.f.chain]
    assert len(h.session.pairs)==1 and len(h.session.requests)==2
    assert not h.session.snapshot()['real_client_accepted']


@pytest.mark.parametrize('change',['batch','unsolicited','partial','transition','reset','stale_wall','foreign_reader','deadline','mode','generation','window'])
def test_bad_stream_or_changed_session_never_reaches_a_step(session,change):
    h=session;request=first_request(h)
    h.session.command_sent(request,CommandReceipt(h.clock(),h.clock()))
    if change=='batch':
        for _ in range(2):h.append('Your Location is 2.00, 1.00, 2.70')
    elif change=='unsolicited':
        h.append('Your Location is 2.00, 1.00, 2.70');h.session.tick()
        h.append('Your Location is 2.00, 1.00, 2.70')
    elif change=='partial':
        with h.log.open('a') as out:out.write('partial')
    elif change=='transition':h.append('LOADING, PLEASE WAIT...')
    elif change=='reset':h.log.write_text('')
    elif change=='stale_wall':
        h.append('Your Location is 2.00, 1.00, 2.70')
        h.session.wall_clock=lambda:datetime(2000,1,1)
    elif change=='foreign_reader':
        h.append('Your Location is 2.00, 1.00, 2.70');h.reader.poll(now=h.clock())
    elif change=='deadline':h.now+=3.
    elif change=='mode':h.mode='assist'
    elif change=='generation':h.generation+=1
    elif change=='window':h.window=43
    with pytest.raises(RouteHalt):h.session.tick()
    assert h.session.phase=='stopped' and h.runner.phase=='halted'
    assert not h.session.steps and h.ledger.chain is h.f.chain


def test_command_reentrant_tick_defers_printed_reply_until_completion(session):
    h=session;h.now+=.125
    h.driver.tick()
    assert h.session.phase=='await_location' and h.reader.latest is None
    h.tick()
    assert h.session.phase=='need_location' and h.reader.latest is h.session.first.raw_fix


def test_cancel_during_command_cannot_accept_its_reply(session):
    h=session;h.now+=.125
    h.hook=lambda:h.session.cancel('owner OFF')
    with pytest.raises(RouteHalt):h.driver.tick()
    assert h.session.phase=='stopped' and not h.session.pairs and not h.session.steps


def test_ground_failure_cannot_keep_session_ready(session):
    h=session;req=first_request(h)
    with pytest.raises(ValueError):accept_reply(h,req,point=(1.,2.,4.))
    assert h.session.phase=='stopped' and h.runner.phase=='halted'


def test_actual_pipe_steps_collect_next_pairs_and_cross_both_segments(tmp_path,legacy):
    h=make(tmp_path,legacy,real=True)
    try:
        deadline=time.monotonic()+20
        while h.session.phase!='arrived' and time.monotonic()<deadline:h.tick()
        assert h.session.phase=='arrived',h.session.snapshot()
        assert h.runner.index==2 and len(h.session.steps)>=2
        assert len(h.session.pairs)==len(h.session.steps)+1
        assert len(h.commands)==2*len(h.session.pairs)
        assert h.ledger.chain.index==len(h.session.steps)+1
        assert h.chain_reads[-1] is h.ledger.chain
        assert h.f.chain.index==1 and not h.sender.held
        assert len({id(ref) for ref in h.refs})==len(h.session.steps)
        assert h.session.tick() is None
        assert not h.session.snapshot()['real_client_accepted']
    finally:h.close()
    assert sum(event==(1,103,1) for event in h.events)==len(h.session.steps)
    assert sum(event==(1,103,0) for event in h.events)>=len(h.session.steps)


@pytest.mark.parametrize('body',['LOADING, PLEASE WAIT...','Your Location is 2.00, 1.10, 2.70'])
def test_log_change_during_pipe_pulse_stops_without_floor_commit(tmp_path,legacy,monkeypatch,body):
    from test_route_step_sender import after_down
    h=make(tmp_path,legacy,real=True)
    try:
        after_down(monkeypatch,lambda:h.append(body))
        with pytest.raises(RuntimeError):
            deadline=time.monotonic()+4
            while h.session.phase!='stopped' and time.monotonic()<deadline:h.tick()
        assert h.session.phase=='stopped' and h.runner.steps==0
        assert h.ledger.chain is h.f.chain and not h.sender.held
        assert len(h.commands)==2
    finally:h.close()
    assert (1,103,1) in h.events and (1,103,0) in h.events
