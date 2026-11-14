"""Standard seven real pipe pulses, fresh fit, then source travel.

All scene and game feedback is synthetic. Displacement uses each actual
watchdog receipt; no initial heading/speed is injected into the route plan.
"""
from dataclasses import replace
import math
import time

import pytest

from eql_automation.camp_source_runtime import CampSourcePlan
from eql_automation.g2_safety_provider import GameWindowIdentity
from eql_automation.motion_calibration import PROBES
from eql_automation.native_region_policy import encoded
from eql_automation.owner_camp_probe import CampProbePlan
from eql_automation.route_geometry import RouteMotionBounds
from eql_automation.source_itinerary import SourceItineraryGuide,SourceWalkHint
from eql_automation.supervised_route import SupervisedRouteDeclaration
from eql_automation.supervised_source import SupervisedSourcePolicy
from test_owner_camp_probe import SyntheticCampPolicy
from test_owner_camp_position import camp
from test_camp_floor_checkpoint import checkpoint
from test_source_motion import f
from test_route_floor_commit import legacy
from test_motion_collection import retained
from test_owner_journey_runtime import h
from test_route_step_sender import after_down


def standard_execution(h,monkeypatch,legacy,*,policy_provider=None,source_veto_provider=None):
    import eql_automation.camp_probe_runtime as probes
    import eql_automation.camp_source_runtime as route
    e=h.engine;h.game_x=4.;h.game_y=2.;h.game_heading=0.;h.receipts=[]

    def simulate(receipt):
        # Game dynamics for this fixture only; reducer sees the printed log.
        seconds=(receipt.maximum_held_seconds+receipt.up_started_at-receipt.down_completed_at)/2
        if receipt.key_code==103:
            h.game_x+=math.sin(math.radians(h.game_heading))*10.*seconds
            h.game_y+=math.cos(math.radians(h.game_heading))*10.*seconds
        else:
            h.game_heading=(h.game_heading+(1 if receipt.key_code==106 else -1)*170.*max(0.,seconds-.03))%360
        h.receipts.append(receipt)

    actual_probe=probes.send_camp_probe
    def probe(*args,**kwargs):
        sent=actual_probe(*args,**kwargs);simulate(sent.seal.receipt);return sent
    monkeypatch.setattr(probes,'send_camp_probe',probe)
    actual_route=route.run_checked_source_step
    def movement(*args,**kwargs):
        seal=actual_route(*args,**kwargs);simulate(seal.receipt);return seal
    monkeypatch.setattr(route,'run_checked_source_step',movement)

    def reply():
        p=e.camp_position
        if p is None:return
        active=p.route_runtime if p.route_runtime is not None else p.runtime
        if active is not None and active.input_kind=='location':
            h.position_reply(x=round(h.game_x,2),y=round(h.game_y,2))
    after_down(monkeypatch,reply)

    def plan(p):
        bounds=RouteMotionBounds('standard-sequence-fixture','synthetic-probe-hypotheses',
            .01,.15,.18,10.,.02,.01,1.,.01,.1,6.)
        guide=SourceItineraryGuide('crushbone',p.floor._terrain.wld_sha256,
            p.floor._static.inventory_sha256,'f'*64,.1,6.,(5.,8.),
            (SourceWalkHint((4.,2.),(5.,8.)),))
        def execution(runtime,calibration):
            assert runtime is p.runtime and runtime.probes==PROBES
            assert calibration['status']=='conditional',calibration
            fit=calibration['estimate']['estimate'];h.used_fit=fit
            onward=replace(bounds,record_id='standard-fixture-onward',maximum_requested_hold=.1)
            def policy(ledger,current):
                veto=p.probe_log_veto if source_veto_provider is None else source_veto_provider(p)
                declaration=SupervisedRouteDeclaration('synthetic-standard-camp-route',
                    ledger.observer.itinerary.sha256,onward.calibration_record_id,onward.record_id,
                    # This guide reconnects to its old start before travelling
                    # onward; reserve all declared steps at their actual-hold
                    # bound, including turns, rather than nominal key times.
                    True,90.,64,6.,64*onward.maximum_actual_hold,'destination_travel')
                return SupervisedSourcePolicy(ledger,declaration=declaration,gate=e.gate,
                    owner_input=p.monitor.observer,log_veto=veto,expected_window=GameWindowIdentity(*p.window),
                    topology_generation=p.monitor.topology,check_current=current)
            return CampSourcePlan(onward,legacy,
                legacy.Motion(run_speed=fit['run_speed'],turn_rate=fit['turn_rate'],
                    right_sign=fit['right_sign'],turn_latency=fit['turn_latency'],back_speed=0.),
                fit['final_heading'],.25,policy)
        return CampProbePlan(bounds,encoded({'kind':'synthetic-seven-probe-fixture'}),
            (lambda tx:SyntheticCampPolicy(tx,e,p)) if policy_provider is None else policy_provider(h,p,bounds),
            PROBES,120.,guide,execution)
    e._camp_probe_plan=plan


def finish_standard(h,*,camp_handoff=False):
    e=h.engine;h.recovered();p=e.camp_position
    deadline=time.monotonic()+125.
    while e.camp_position is not None and time.monotonic()<deadline:
        h.tick();h.drain();time.sleep(.01)
    h.drain();record=e.camp_position_last_result or {}
    reason=(record.get('route',{}).get('route') or {}).get('movement_reason')
    assert e.camp_position is None,'\n'.join(h.notices)
    assert record.get('outcome')=='route_complete','\n'.join(h.notices)+'\n'+str(reason)+'; completed receipts='+str(len(h.receipts))
    assert [(v.key_code,v.requested_seconds) for v in h.receipts[:7]]==[(v.key_code,v.seconds) for v in PROBES]
    assert len(h.receipts)>7 and record['probe']['completed_probes']==7
    calibration=record['probe']['calibration']['estimate']
    assert len(calibration['retained_evidence'])==7 and calibration['verified_speed_upper_bound'] is None
    assert not calibration['input_authorized'] and not calibration['current_heading_verified']
    assert p.route_runtime.plan.motion.run_speed==h.used_fit['run_speed']
    assert p.route_runtime.plan.heading==h.used_fit['final_heading']
    assert p.route_runtime.lease is p.lease and p.route_runtime.probe is p.runtime
    assert record['route']['route']['completed_movements']==len(h.receipts)-7
    assert not record['real_client_accepted'] and not e.sender.held and not h.commands
    assert e.live_zone_tracker.lease is None
    if camp_handoff:
        assert record['continuation']['camp_started']
        assert e.camp_session is not None and e.camp_session is not p.camp
        assert e.camp_session.preparation_due and e.journey is p.journey
        assert p.monitor.closed and e.journey.camp_motion.observer is p.monitor.observer
        assert not h.observer_closed and e.journey.camp_motion.valid
        assert not p.floor.valid and e.journey.arrival_floor.valid
    else:assert e.camp_session is None and e.journey is None
    return p


@pytest.mark.parametrize('f',['compact_long'],indirect=True)
def test_standard_holds_fit_current_motion_and_complete_source_route(camp,monkeypatch,legacy):
    h=camp;standard_execution(h,monkeypatch,legacy);finish_standard(h)
