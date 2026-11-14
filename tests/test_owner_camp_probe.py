"""Retained engine F8/F9 handoff with real pipe writes and synthetic admission."""
from dataclasses import replace
import time

import pytest

from eql_automation.camp_probe_sender import CampProbeInputPolicy,CampProbeAuthorization
from eql_automation.motion_calibration import Probe
from eql_automation.native_region_policy import encoded
from eql_automation.owner_camp_probe import CampProbePlan
from eql_automation.owner_zone_tracker import ZoneReaderLease
from eql_automation.route_geometry import RouteMotionBounds
from test_owner_camp_position import camp
from test_camp_floor_checkpoint import checkpoint
from test_source_motion import f
from test_route_floor_commit import legacy
from test_motion_collection import retained
from test_owner_journey_runtime import h
from test_route_step_sender import after_down


class SyntheticCampPolicy(CampProbeInputPolicy):
    def __init__(self,transaction,engine,scope):
        super().__init__(transaction);self.engine=engine;self.scope=scope;self.authorization=None

    def check(self):
        self.engine._camp_position_current(self.scope)
        return True  # Explicit synthetic test admission, never a production default.

    def authorize(self,ticket):
        self.check()
        self.authorization=CampProbeAuthorization(ticket,time.monotonic(),
            ticket.proposed_at+.05,'synthetic-retained-engine-probe')
        return self.authorization

    def still_authorized(self,authorization):return authorization is self.authorization and self.check()


def configure(h,monkeypatch,*,probes=(Probe('forward',103,.02),)):
    import eql_automation.camp_probe_runtime as runtime_module
    e=h.engine;h.probe_x=4.;h.probe_scope=None
    def plan(p):
        h.probe_scope=p
        bounds=RouteMotionBounds('engine-probe-hypotheses','synthetic-current-measurement',
            .01,.02,.15,3.,.02,.01,1.,.01,.1,6.)
        return CampProbePlan(bounds,encoded({'kind':'synthetic-engine-probe-hypotheses'}),
            lambda tx:SyntheticCampPolicy(tx,e,p),probes,120.)
    e._camp_probe_plan=plan
    def reply():
        p=e.camp_position
        if p is not None and p.runtime is not None and p.runtime.input_kind=='location':
            h.position_reply(x=h.probe_x)
    after_down(monkeypatch,reply)
    original=runtime_module.send_camp_probe
    def movement(*args,**kwargs):
        sent=original(*args,**kwargs)
        if sent.seal.receipt.key_code==103:h.probe_x+=.2
        return sent
    monkeypatch.setattr(runtime_module,'send_camp_probe',movement)


def finish(h):
    deadline=time.monotonic()+30.
    while h.engine.camp_position is not None and time.monotonic()<deadline:
        h.tick();h.drain();time.sleep(.01)
    h.drain()
    assert h.engine.camp_position is None,h.notices


def test_real_camp_collection_hands_same_scope_to_probes_then_stops(camp,monkeypatch):
    h=camp;e=h.engine
    configure(h,monkeypatch,probes=(Probe('forward',103,.02),Probe('right',106,.02)))
    h.recovered();scope=e.camp_position;lease=scope.lease;floor=scope.floor;sender=e.sender
    finish(h)
    assert h.probe_scope is scope and scope.runtime.lease is lease and scope.runtime.sender is sender
    assert scope.runtime.root.checkpoint is floor
    record=e.camp_position_last_result
    assert record['outcome']=='probe_complete',h.notices
    assert record['probe']['completed_probes']==2 and len(record['probe']['results'])==2
    assert [k for kind,k,v in h.events if kind==1 and v==1 and k!=62]==[103,106]
    assert not h.commands and not e.sender.held and scope.runtime.closed
    assert e.live_zone_tracker.lease is None and e.camp_session is None and e.journey is None
    assert not e.active and not h.scope_journey.height_check_done
    assert not record['real_client_accepted'] and not floor.valid


@pytest.mark.parametrize('mode',('F8','F9'))
def test_retained_engine_stop_after_movement_down_precedes_lease_and_assist(camp,monkeypatch,mode):
    h=camp;e=h.engine;configure(h,monkeypatch)
    e.prepared=True;e.prepared_level=7;stopped=[];released=[]
    release=ZoneReaderLease.release
    def check_release(lease):
        if stopped and lease is stopped[0].lease:
            assert not stopped[0].runtime.busy and not e.sender.held
            assert getattr(e.sender,'_eql_route_operation',None) is None
            h.drain();at=h.events.index((1,103,1));assert (1,103,0) in h.events[at+1:]
            released.append(lease)
        return release(lease)
    monkeypatch.setattr(ZoneReaderLease,'release',check_release)
    def stop():
        p=e.camp_position
        if p is not None and p.runtime is not None and p.runtime.input_kind=='movement':
            stopped.append(p)
            if mode=='F8':e.handle_job('arm',e.cancel_generation)
            else:e.stop_action('F9 during camp probe DOWN')
            assert p.runtime.busy and p.busy and e._navigation_busy()
            assert not e.active and not p.lease.active and p.tracker.lease is p.lease
    after_down(monkeypatch,stop)
    h.recovered();finish(h)
    assert len(stopped)==1 and released==[stopped[0].lease],h.notices
    assert e.camp_session is None and e.journey is None and not e.sender.held
    assert e.camp_position_last_result['outcome']=='stopped'
    assert e.camp_position_last_result['probe']['completed_probes']==0
    if mode=='F8':
        assert e._journey_assist is not None
        before=list(h.events);h.tick();h.drain()
        assert e.active and h.events==before and not h.commands
    else:assert e._journey_assist is None and not e.active


@pytest.mark.parametrize('change',('F9_plan','F9_started','invalid_plan','invalid_probes','missing_policy','policy_error'))
def test_handoff_failure_never_sends_movement_or_resumes_camp(camp,monkeypatch,change):
    h=camp;e=h.engine;configure(h,monkeypatch);provider=e._camp_probe_plan
    if change=='F9_plan':
        def stopped(p):
            plan=provider(p);e.stop_action('F9 in probe plan provider');return plan
        e._camp_probe_plan=stopped
    elif change=='F9_started':
        original=e.trace
        def trace(kind,**values):
            original(kind,**values)
            if kind=='camp_probe_started':e.stop_action('F9 at probe handoff')
        e.trace=trace
    elif change=='invalid_plan':e._camp_probe_plan=lambda p:object()
    elif change=='invalid_probes':e._camp_probe_plan=lambda p:replace(provider(p),probes=(object(),))
    elif change=='missing_policy':e._camp_probe_plan=lambda p:replace(provider(p),policy_factory=lambda tx:None)
    else:
        def broken(tx):raise TypeError('Synthetic policy construction failure')
        e._camp_probe_plan=lambda p:replace(provider(p),policy_factory=broken)
    h.recovered();finish(h)
    assert not [(kind,k,v) for kind,k,v in h.events if kind==1 and v==1 and k!=62]
    assert not h.commands and not e.sender.held and e.camp_session is None
    assert e.live_zone_tracker.lease is None and e.camp_position_last_result['outcome']=='stopped'


def test_probe_branch_does_not_admit_unrequested_input(camp,monkeypatch):
    h=camp;e=h.engine;configure(h,monkeypatch);h.recovered()
    deadline=time.monotonic()+8.
    while e.camp_position is not None and e.camp_position.runtime is None and time.monotonic()<deadline:
        h.tick();h.drain();time.sleep(.01)
    p=e.camp_position;assert p is not None and p.runtime is not None,h.notices
    assert not e.allowed() and not e._camp_probe_input_permitted()
    with pytest.raises(InterruptedError):e.send('/target orc fixture')
    e.stop_action('F9 before probe work');assert e.camp_position is None
    assert not [(kind,k,v) for kind,k,v in h.events if kind==1 and v==1 and k!=62]
