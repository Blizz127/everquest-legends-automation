"""Real retained-engine/pipe handoff, synthetic route, scene and game feedback."""
from dataclasses import replace
import time

import pytest

from eql_automation.camp_source_runtime import CampSourcePlan
from eql_automation.g2_safety_provider import GameWindowIdentity
from eql_automation.owner_zone_tracker import ZoneReaderLease
from eql_automation.scene_log_veto import SceneLogVeto
from eql_automation.supervised_route import SupervisedRouteDeclaration
from eql_automation.supervised_source import SupervisedSourcePolicy
from test_owner_camp_probe import configure_route, finish
from test_owner_camp_position import camp
from test_camp_floor_checkpoint import checkpoint
from test_source_motion import f
from test_route_floor_commit import legacy
from test_motion_collection import retained
from test_owner_journey_runtime import h
from test_route_step_sender import after_down


def configure_execution(h, monkeypatch, legacy, *, policy_fault=None):
    import eql_automation.camp_source_runtime as module
    configure_route(h, monkeypatch)
    e=h.engine;provider=e._camp_probe_plan
    def plan(p):
        base=provider(p)
        def execution(probe, calibration):
            assert probe is p.runtime and calibration is p.probe_record['calibration']
            bounds=replace(base.bounds, record_id='synthetic-camp-onward-bounds', maximum_requested_hold=.02)
            def policy(ledger, current):
                if policy_fault=='missing':return None
                if policy_fault=='F9':e.stop_action('F9 during source policy construction')
                if policy_fault=='foreign_input':owner_input=object()
                else:owner_input=p.monitor.observer
                veto=SceneLogVeto(p.reader.tail.path, expected_character=p.reader.expected_character,
                    expected_server=p.reader.expected_server, cancel_generation=p.generation, clock=time.monotonic)
                declaration=SupervisedRouteDeclaration('synthetic-camp-route',ledger.observer.itinerary.sha256,
                    bounds.calibration_record_id,bounds.record_id,True,60.,32,3.,2.)
                return SupervisedSourcePolicy(ledger,declaration=declaration,gate=e.gate,
                    owner_input=owner_input,log_veto=veto,expected_window=GameWindowIdentity(*p.window),
                    topology_generation=1,check_current=current)
            return CampSourcePlan(bounds,legacy,
                legacy.Motion(run_speed=10.,turn_rate=170.,right_sign=1,turn_latency=.005,back_speed=0.),
                90.,.25,policy)
        return replace(base,route_plan_factory=execution)
    e._camp_probe_plan=plan
    def reply():
        p=e.camp_position;r=None if p is None else p.route_runtime
        if r is not None and r.input_kind=='location':h.position_reply(x=h.probe_x)
    after_down(monkeypatch,reply)
    real=module.run_checked_source_step
    def move(*args,**kwargs):
        seal=real(*args,**kwargs)
        if seal.receipt.key_code==103:h.probe_x+=.2
        return seal
    monkeypatch.setattr(module,'run_checked_source_step',move)


def test_same_scope_probes_startup_walk_acknowledgment_and_arrival(camp,monkeypatch,legacy):
    h=camp;e=h.engine;configure_execution(h,monkeypatch,legacy)
    h.recovered();p=e.camp_position
    finish(h)
    record=e.camp_position_last_result
    assert record['outcome']=='route_complete','\n'.join(h.notices)+'\n'+str(
        record.get('route',{}).get('route',{}).get('movement_reason'))
    route=p.route_runtime
    assert route.probe is p.runtime and route.sender is p.sender and route.lease is p.lease
    assert route.lock is e.g0_stop_lock and route.reader is p.reader
    assert record['route']['route']['completed_movements']>=1
    assert record['route']['arrival']['historical_floor_only']
    assert record['route']['arrival']['current_position_verified'] is False
    startup=record['route']['startup_pairs'][0]
    assert startup['raw_fixes'][0]['log_line_seq']>route.observer.calibration.last_calibration_log_line_seq
    assert record['route']['original_scope_started']==p.runtime.started
    assert record['route']['original_scope_expires']==p.runtime.started+p.runtime.maximum_seconds
    assert not record['route']['real_client_accepted']
    assert not e.sender.held and p.runtime.closed and p.tracker.lease is None
    assert e.camp_session is None and e.journey is None and not e.active and not h.commands


@pytest.mark.parametrize('mode',('F8','F9'))
@pytest.mark.parametrize('phase',('startup','movement','positions'))
def test_stop_during_child_down_releases_before_lease_and_assist(camp,monkeypatch,legacy,mode,phase):
    h=camp;e=h.engine;configure_execution(h,monkeypatch,legacy)
    e.prepared=True;e.prepared_level=7;stopped=[];released=[]
    original=ZoneReaderLease.release
    def release(lease):
        if stopped and lease is stopped[0].lease:
            p=stopped[0]
            assert not p.busy and not p.runtime.busy and not p.route_runtime.busy
            assert not e.sender.held and e.sender._eql_route_operation is None
            h.drain();assert h.events[-1][0]!=1 or h.events[-1][2]==0
            released.append(lease)
        return original(lease)
    monkeypatch.setattr(ZoneReaderLease,'release',release)
    def stop():
        p=e.camp_position;r=None if p is None else p.route_runtime
        if r is not None and ((phase=='movement' and r.input_kind=='movement')
                or phase==r.phase and r.input_kind=='location'):
            stopped.append(p)
            if mode=='F8':e.handle_job('arm',e.cancel_generation)
            else:e.stop_action('F9 during camp source DOWN')
            assert p.busy and r.busy and e._navigation_busy()
            assert not e.active and not p.lease.active and p.tracker.lease is p.lease
    after_down(monkeypatch,stop)
    h.recovered();finish(h)
    assert len(stopped)==1 and released==[stopped[0].lease],'\n'.join(h.notices)
    assert e.camp_position_last_result['outcome']=='stopped'
    assert e.camp_position_last_result['route']['phase']=='stopped'
    assert not e.sender.held and not h.commands and e.camp_session is None and e.journey is None
    if mode=='F8':
        assert e._journey_assist is not None
        before=list(h.events);h.tick();h.drain();assert e.active and h.events==before
    else:assert e._journey_assist is None and not e.active


@pytest.mark.parametrize('fault',('missing','foreign_input','F9'))
def test_missing_changed_or_cancelled_policy_sends_no_onward_movement(camp,monkeypatch,legacy,fault):
    h=camp;e=h.engine;configure_execution(h,monkeypatch,legacy,policy_fault=fault)
    h.recovered();finish(h)
    assert e.camp_position_last_result['outcome']=='stopped','\n'.join(h.notices)
    assert len([key for kind,key,value in h.events if kind==1 and value==1 and key==103])==1
    assert not e.sender.held and e.live_zone_tracker.lease is None and not h.commands


@pytest.mark.parametrize('fault',('parent_cancelled','deadline','plan_changed','lease_released',
    'owner_child','observer','ledger','driver','physical_input'))
def test_original_scope_change_before_startup_sends_no_child_input(camp,monkeypatch,legacy,fault):
    h=camp;e=h.engine;configure_execution(h,monkeypatch,legacy);h.recovered()
    deadline=time.monotonic()+20
    while e.camp_position is not None and e.camp_position.route_runtime is None and time.monotonic()<deadline:
        h.tick();h.drain();time.sleep(.01)
    p=e.camp_position
    assert p is not None and p.route_runtime is not None,'\n'.join(h.notices)
    before=list(h.events)
    if fault=='parent_cancelled':p.runtime.cancel('ancestor stopped')
    elif fault=='deadline':p.probe_started-=p.probe_plan.maximum_seconds+1.
    elif fault=='plan_changed':object.__setattr__(p.route_runtime.plan,'heading',180.)
    elif fault=='lease_released':p.lease.active=False
    elif fault=='owner_child':p.route_runtime=object()
    elif fault=='physical_input':
        sample=p.monitor.observer.sample
        p.monitor.observer.sample=lambda:replace(sample(),held_key_count=1)
    else:setattr(p.route_runtime,fault,object())
    finish(h)
    assert h.events==before and e.camp_position_last_result['outcome']=='stopped'
    assert not e.sender.held and e.live_zone_tracker.lease is None and not h.commands
