"""Checked repeated corridor pulses on OS pipes with synthetic game feedback."""
from dataclasses import replace
from datetime import datetime,timedelta
import os
import time
from types import SimpleNamespace

import pytest

from eql_automation.crossing_corridor import CrossingCorridorHandoff
from eql_automation.g2_safety_provider import GameWindowIdentity
from eql_automation.ground_observer import RouteGroundObserver
from eql_automation.motion_collection import CommandReceipt,LocationRequest
from eql_automation.owner_input_observer import OwnerInputObservation
from eql_automation.owner_zone_tracker import LiveZoneTracker
from eql_automation.provisional_floor_commit import ProvisionalRouteFloorCommit
from eql_automation.route_step_sender import RouteStepScene,run_checked_corridor_step,run_checked_route_step
from eql_automation.supervised_corridor import SupervisedCorridorDeclaration,SupervisedCrossingCorridorPolicy
from eql_automation.uinput_watchdog import _EVENT
from test_route_floor_commit import legacy
from test_route_step_sender import PipeSender,after_down
from test_zone_line import prepare_crossing


@pytest.fixture
def h(tmp_path,legacy):
    time_state={'offset':0.};clock=lambda:time.monotonic()+time_state['offset']
    h,line=prepare_crossing(legacy,clock=clock,ledger_factory=lambda *a,**kw:
        ProvisionalRouteFloorCommit(*a,context_reader=lambda:('synthetic-source',54,1),**kw))
    h.offset=time_state;h.line=line;h.ready=False;h.cancelled=False;h.focus=True
    mesh=h.observer.mesh;mesh.area=h.prepare.ground.areas;mesh.mesh_sha256=line.mesh_sha256
    h.observer=RouteGroundObserver(mesh=mesh,ground=h.prepare.ground,source=h.prepare.source,
        geometry_evidence=h.runner.geometry_evidence,reciprocal_links=((0,1),(1,0)))
    h.log=tmp_path/'eqlog_Probe_private.txt';h.log.touch()
    catalog=tmp_path/'ZoneNames.txt';catalog.write_text('54^Fixture^0^0\n58^Clan Crushbone^0^0\n')
    h.wall=lambda:datetime.now()+timedelta(seconds=time_state['offset'])
    def append(body):
        with h.log.open('a') as out:out.write(h.wall().strftime('[%a %b %d %H:%M:%S %Y] ')+body+'\n')
    h.append=append
    tracker=LiveZoneTracker(h.log,catalog,expected_character='Probe',expected_server='private',
        binding_reader=lambda:('synthetic-owner',42,10,100),clock=clock)
    append('You have entered Fixture.');tracker.poll()
    tracker.reader.tail.epoch=1;tracker.reader.log_line_seq=2
    h.lease=tracker.acquire()
    h.rd,h.wr=os.pipe();h.sender=PipeSender(h.wr)
    def current():
        if h.cancelled or not h.focus:raise ValueError('Owner cancelled or focus changed')
    h.current=current
    def release():
        began=clock()
        for key in tuple(h.sender.held):h.sender.release(key)
        return CommandReceipt(began,clock())
    h.corridor=CrossingCorridorHandoff(h.prepare,h.observer,h.reference,h.lease,'Clan Crushbone',
        release_controls=release,ready_for_location=lambda:h.ready,check_current=current,
        maximum_source_seconds=60.,local_wall_clock=h.wall)
    window=SimpleNamespace(id=42)
    gate=SimpleNamespace(windows=lambda:[window],focused_window=lambda:window if h.focus else None,
        game_session=lambda:{'pid':10,'start_ticks':'100'},controls_ready=lambda:h.focus)
    def sample():
        now=clock();return OwnerInputObservation(now,now,1,True,1,0,False,0,'synthetic-device')
    declaration=SupervisedCorridorDeclaration(line.crossing_id,h.runner.route.artifact_sha256,
        h.runner.calibration,h.prepare.bounds.record_id,True,60.,10,10.,1.,
        expected_zone_line_sha256=line.sha256,destination='Clan Crushbone')
    h.policy=SupervisedCrossingCorridorPolicy(h.prepare,arrival=h.corridor.arrival,declaration=declaration,
        gate=gate,owner_input=SimpleNamespace(sample=sample),log_veto=h.corridor.arrival.veto,
        expected_log_path=h.log,expected_window=GameWindowIdentity(42,10,100),
        topology_generation=1,check_current=current)
    h.scene=lambda:RouteStepScene(h.corridor.reference,h.policy.observe(h.corridor.reference))
    h.run=lambda:run_checked_corridor_step(h.sender,h.corridor,policy=h.policy,
        scene_provider=h.scene,command_state_clear=lambda:True,pump=lambda:None)
    yield h
    h.lease.release();tracker.close()
    os.close(h.wr);data=b''
    while part:=os.read(h.rd,4096):data+=part
    os.close(h.rd)
    h.events=[(kind,key,value) for _,_,kind,key,value in _EVENT.iter_unpack(data)]
    assert not h.sender.held
    if any(kind==1 and value==1 for kind,key,value in h.events):
        assert h.events[-1]==(0,0,0) and h.events[-2][0]==1 and h.events[-2][2]==0


def wait_until(h,at):
    time.sleep(max(0.,at-h.clock())+.002)


def source_pair(h,*,loading=False):
    before=h.corridor.reference.mesh_projection.package_xyz
    x=before[0]+h.runner.motion.run_speed*h.corridor.receipt.maximum_held_seconds
    wait_until(h,h.corridor.quiet_until)
    for i in range(2):
        request=h.corridor.tick();assert isinstance(request,LocationRequest)
        h.corridor.command_sent(request,CommandReceipt(h.clock(),h.clock()))
        if loading and i==1:
            h.append('LOADING, PLEASE WAIT...');h.append('You have entered Clan Crushbone.')
        else:h.append(f'Your Location is 2, {x:.6f}, 2.7')
        assert h.corridor.tick() is None
        if i==0:time.sleep(.405)
    return x


def destination_pair(h):
    h.ready=True;h.offset['offset']+=.2
    for i in range(2):
        request=h.corridor.tick();assert isinstance(request,LocationRequest)
        h.corridor.command_sent(request,CommandReceipt(h.clock(),h.clock()))
        h.append('Your Location is -12, 34, 5');assert h.corridor.tick() is None
        if i==0:h.offset['offset']+=.41
    assert h.corridor.phase=='complete'


def test_two_actual_source_pulses_then_loading_use_one_policy_reader_and_budget(h,monkeypatch):
    reader=h.lease.reader;started=h.policy.started
    for index in range(2):
        result=h.run()
        assert result['outcome']=='settling' and not result['source_floor_committed']
        assert h.runner.steps==index and h.ledger.chain.index==index+1
        source_pair(h)
        assert h.corridor.phase=='ready' and h.runner.steps==index+1
        assert h.ledger.chain.index==index+2 and h.corridor.arrival.reader is reader
    after_down(monkeypatch,lambda:h.append('LOADING, PLEASE WAIT...'))
    result=h.run();assert result['outcome']=='await_arrival'
    assert h.policy.snapshot()['reserved_movements']==3 and h.policy.started==started
    assert h.policy.reserved_hold==pytest.approx(.3) and h.runner.steps==2
    h.append('You have entered Clan Crushbone.');h.corridor.tick();destination_pair(h)
    assert h.ledger.chain.index==3 and h.corridor.arrival.collector.second.zone_id==58
    assert not h.corridor.snapshot()['real_client_accepted']


def test_loading_during_source_pair_discards_the_actual_seal(h):
    h.run();source_pair(h,loading=True)
    assert h.corridor.phase=='await_arrival' and h.ledger.chain.index==1 and h.runner.steps==0
    assert h.ledger._sealed is None and h.corridor.seal is None
    destination_pair(h)


@pytest.mark.parametrize('cause',['owner','policy','mode','lease','hazard'])
def test_during_down_cancellation_stops_without_source_commit(h,monkeypatch,cause):
    def stop():
        if cause=='owner':h.cancelled=True
        elif cause=='policy':h.policy.cancel('F9')
        elif cause=='mode':h.state['mode']='assist'
        elif cause=='lease':h.lease.release()
        else:h.append('a bat hits YOU for 3 points of damage.')
    after_down(monkeypatch,stop)
    with pytest.raises((ValueError,RuntimeError)):h.run()
    assert h.corridor.phase=='stopped' and h.runner.steps==0 and h.ledger.chain.index==1


def test_ordinary_sender_cannot_accept_corridor_policy(h):
    with pytest.raises(ValueError,match='typed policy'):
        run_checked_route_step(h.sender,h.ledger,scene_provider=h.scene,prepare_step=h.prepare,
            authorize_step=h.policy.authorize,still_authorized=h.policy.still_authorized,
            command_state_clear=lambda:True,pump=lambda:None,supervised_policy=h.policy)


def test_no_second_pulse_while_source_receipt_unresolved(h):
    h.run()
    with pytest.raises(ValueError):h.run()
    assert h.runner.steps==0 and h.ledger.chain.index==1 and h.corridor.phase=='stopped'


def test_dry_pivot_is_allowed_without_claiming_line_overlap(h):
    h.runner.motion=h.runner.pose.motion=replace(h.runner.motion,turn_latency=.01)
    h.runner.pose.heading=0.
    result=h.run()
    assert result['receipt']['key_code'] in (105,106) and not h.corridor.touches_line
    assert h.corridor.quiet_until==h.corridor.receipt.up_completed_at+.12
    assert h.policy.snapshot()['reserved_movements']==1 and h.runner.steps==0


def test_loading_after_dry_pivot_is_uncorrelated_and_refuses_arrival(h,monkeypatch):
    h.runner.motion=h.runner.pose.motion=replace(h.runner.motion,turn_latency=.01)
    h.runner.pose.heading=0.
    after_down(monkeypatch,lambda:h.append('LOADING, PLEASE WAIT...'))
    with pytest.raises((ValueError,RuntimeError)):h.run()
    assert h.corridor.phase=='stopped' and h.runner.steps==0 and h.corridor.arrival.loading is not None


def test_last_admitted_slot_can_finish_but_cannot_be_renewed(h):
    d=replace(h.policy.declaration,maximum_steps=1,maximum_total_hold=.1)
    h.policy.declaration=h.policy._declaration=d
    h.run();source_pair(h)
    assert h.runner.steps==1 and h.policy.snapshot()['reserved_movements']==1
    with pytest.raises((ValueError,RuntimeError)):h.run()
    assert h.policy.snapshot()['reserved_movements']==1 and h.ledger.chain.index==2


def test_arrival_retains_separate_source_and_loading_deadlines(h,monkeypatch):
    arrival=h.corridor.arrival
    before=arrival.deadline;outer=arrival.outer_deadline
    after_down(monkeypatch,lambda:h.append('LOADING, PLEASE WAIT...'))
    h.run()
    assert before==arrival.started+60.
    assert arrival.deadline==min(outer,arrival.loading.received_monotonic+90.)
    assert arrival.outer_deadline==outer


def test_loading_followed_by_invalid_position_cannot_return_successful_handoff(h,monkeypatch):
    def malformed():
        h.append('LOADING, PLEASE WAIT...');h.append('Your Location is malformed')
    after_down(monkeypatch,malformed)
    with pytest.raises((ValueError,RuntimeError)):h.run()
    assert h.corridor.phase=='stopped' and h.corridor.arrival.phase=='stopped'
    assert h.ledger.chain.index==1 and h.runner.steps==0


@pytest.mark.parametrize('slow_call',[2,3])
def test_slow_release_scope_callback_cannot_accept_an_aged_interrupted_receipt(h,monkeypatch,slow_call):
    after_down(monkeypatch,lambda:h.append('LOADING, PLEASE WAIT...'))
    original=h.corridor.released
    def released(receipt):
        calls=[]
        def current():
            calls.append(1)
            if len(calls)==slow_call:h.offset['offset']+=.31
        h.corridor.check_current=current
        return original(receipt)
    h.corridor.released=released
    with pytest.raises(ValueError,match='expired'):h.run()
    assert h.corridor.phase=='stopped' and h.ledger.chain.index==1
