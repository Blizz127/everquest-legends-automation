"""New destination plans through actual guards/watchdog pipes, synthetic motion."""
from datetime import datetime
import math
import os
import threading
import time

import pytest

from eql_automation.fixed_route_follower import FixedRouteFollower,RouteHalt
from eql_automation.g2_pulse_budget import G2Scene
from eql_automation.motion_collection import CommandReceipt
from eql_automation.location_log import LocationLogReader
from eql_automation.observed_height import measure_current_height
from eql_automation.portal_precision import SourceFace
from eql_automation.route_floor_commit import RouteFloorCommit
from eql_automation.route_geometry import RouteGeometryPreparer
from eql_automation.route_session import RouteSession,RouteSessionDriver
from eql_automation.route_step_sender import RouteStepAuthorization
from eql_automation.uinput_watchdog import _EVENT, PulseError
from test_destination_route import f,nav_module
from test_route_floor_commit import legacy
from test_route_step_sender import PipeSender


@pytest.mark.parametrize('wall',[False,True])
def test_destination_runtime_crosses_portal_or_stops_before_suffix_wall(f,legacy,wall):
    exercise_destination(f,legacy,wall=wall)


def exercise_destination(f,legacy,*,wall=False,refusal=None):
    start=getattr(f,'start',(4.,4.)); wall_x=getattr(f,'wall_x',12.)
    f.clock=time.monotonic;f.wall=datetime.now
    log=f.reader.tail.path
    f.reader=LocationLogReader(log,log.parent/'ZoneNames.txt',expected_character='Probe',expected_server='private')
    f.append('You have entered Fixture.');f.reader.poll(now=f.clock())
    def position():
        f.now=time.monotonic()
        f.append(f'Your Location is {start[1]:.2f}, {start[0]:.2f}, 2.70')
        return f.reader.poll(now=f.now)[0]
    f.a=position();time.sleep(.41);f.b=position()
    f.destination_options.update(clock=f.clock,local_wall_clock=f.wall,released_at=f.a.received_monotonic-.2)
    barrier=SourceFace(((0.,wall_x,0.),(8.,wall_x,0.),(4.,wall_x,8.)),0,'Diffuse',20,0)
    f.planner.static.faces_for_footprint=lambda footprint:(barrier,) if wall and max(x for x,y in footprint)>=wall_x else ()
    plan=f.plan_destination()
    released=f.clock();time.sleep(.13);a=position();time.sleep(.41);b=position()
    height=measure_current_height(plan.observer,f.reader,a,b,route=plan.route,segment_index=0,
        owner_binding=f.owner,binding_reader=lambda:f.owner,clock=f.clock,record_id='destination-pipe-height',
        released_at=released,local_wall_clock=f.wall)
    runner=FixedRouteFollower(plan.route,legacy=legacy,
        motion=legacy.Motion(run_speed=10.,turn_rate=170.,right_sign=-1,turn_latency=.03,back_speed=0.),
        heading=90.,calibration_record_id='same-session-motion',height_calibration=height,
        geometry_evidence=plan.observer.geometry,generation=1,generation_reader=lambda:1,
        mode_reader=lambda:'measurement',max_steps=100)
    ledger=RouteFloorCommit(runner,plan.floor_chain,stop_lock=threading.RLock(),clock=f.clock)
    p=f.planner
    prepare=RouteGeometryPreparer(ledger,ground=p.ground,source=p.source,static=p.static,bsp=p.bsp,
        bounds=plan.planning_bounds,static_inventory_sha256=p.pins[3],vertical_window=1.,maximum_source_z_difference=1.,
        precision_policy=plan.precision_policy)
    timing=[];precompute=prepare.precompute
    def timed_precompute(observed):
        began=f.clock();cpu=time.process_time()
        try:return precompute(observed)
        finally:timing.append((f.clock()-began,time.process_time()-cpu))
    prepare.precompute=timed_precompute
    session=RouteSession(ledger,f.reader,plan.observer,initial_release_at=f.clock(),
        binding_reader=lambda:f.owner,record_id='synthetic-destination-route',local_wall_clock=f.wall)
    rd,wr=os.pipe();sender=PipeSender(wr);point=[*start,.6];error=None;events=[]
    def location(request):
        began=f.clock()
        f.append(f'Your Location is {point[1]:.2f}, {point[0]:.2f}, 2.70')
        return CommandReceipt(began,f.clock())
    def scene(reference):
        r=reference.raw_fix
        return G2Scene(f.clock(),plan.route.zone,r.raw_coordinates,r.log_epoch,r.log_line_seq,
            r.zone_generation,True,True,True,True,True,True,True)
    def authorize(ticket,observed):
        return RouteStepAuthorization(ticket,observed.reference_fix,f.clock(),
            ticket.preparation.proposal.at+.05,'synthetic-destination-scene')
    driver=RouteSessionDriver(session,sender,request_location=location,sample_scene=scene,
        prepare_step=prepare,authorize_step=authorize,still_authorized=lambda *_:True,
        command_state_clear=lambda:True,pump=lambda:None)
    try:
        deadline=f.clock()+35
        while session.phase not in ('arrived','stopped') and f.clock()<deadline:
            count=len(session.steps)
            try:driver.tick()
            except (ValueError,RouteHalt) as exc:error=str(exc);break
            except PulseError as exc:
                exc.add_note(f'Follower reason: {runner.reason}; last-fix age: {f.clock()-runner.last_fix_at:.3f}s; '
                             f'geometry wall/cpu: {timing[-2:]}; committed steps: {len(session.steps)}')
                raise
            if len(session.steps)>count:
                receipt=session.steps[-1]['receipt']
                assert receipt['key_code']==103
                held=((receipt['up_started_at']-receipt['down_completed_at'])+
                      (receipt['up_completed_at']-receipt['down_started_at']))/2
                point[0]+=10.*held
            time.sleep(.01)
        assert not sender.held
        assert ledger.chain.index==1+len(session.steps)
        if wall or refusal:
            assert error and (refusal or 'Static geometry') in error,error
            assert point[0]<wall_x-plan.planning_bounds.body_radius
            assert ledger._pending is None
        else:
            assert session.phase=='arrived',(session.phase,error,runner.reason,point)
            assert runner.index==len(plan.route.segments)
            assert math.dist(point[:2],f.goal)<=runner.radius
            assert {0,1}<={pair['segment_index'] for pair in session.pairs}
            assert session.pairs[-1]['segment_index']==len(plan.route.segments)
    finally:
        session.cancel('test cleanup');os.close(wr)
        data=b''
        while chunk:=os.read(rd,65536):data+=chunk
        os.close(rd)
        events=[(kind,key,value) for _,_,kind,key,value in _EVENT.iter_unpack(data)]
    downs=[v for v in events if v==(1,103,1)]
    assert len(downs)==len(session.steps)>0
    assert events[-2:]==[(1,103,0),(0,0,0)]
    return session
