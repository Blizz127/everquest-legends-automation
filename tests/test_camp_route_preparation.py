"""Onward planning from genuine retained probe floors with synthetic log samples."""
from dataclasses import replace

import pytest

from eql_automation.camp_route_preparation import CampRoutePreparation
from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_itinerary import SourceItineraryGuide,SourceWalkHint
from test_camp_probe_continuation import confirmed,new_height
from test_camp_probe_preparation import probe
from test_camp_probe_transaction import pair
from test_camp_floor_checkpoint import checkpoint
from test_source_motion import f
from test_route_floor_commit import legacy


@pytest.fixture
def route(probe):
    h=probe;tx,result=confirmed(h);reference=tx.retain_endpoint(result)
    height=new_height(h,reference)
    guide=SourceItineraryGuide('crushbone',reference._terrain.wld_sha256,
        reference._static.inventory_sha256,'f'*64,h.probe.bounds.body_radius,
        h.probe.bounds.body_height,(6.,2.),(SourceWalkHint((4.5,2.),(6.,2.)),))
    options=dict(guide=guide,bounds=h.probe.bounds,owner_binding=h.camp_binding,
        binding_reader=h.probe.binding_reader,clock=h.clock,local_wall_clock=h.wall)
    p=CampRoutePreparation(reference,height,h.lease,**options)
    h.route=p;h.route_options=options;h.route_tx=tx
    return h


def fresh(h,*,x=4.5):
    released=h.now;a,b,baseline=pair(h,x=x)
    return h.route.observe_start(a,b,minimum_log_seq=baseline,released_at=released)


def test_next_route_extends_exact_reached_floor_without_adopting_future_branch(route):
    h=route;p=h.route;reference=p.checkpoint;original=_chain_snapshot(reference._chain)
    expiry=h.checkpoint._calibration.valid_until_monotonic
    p.prepare();record=p.itinerary.record()
    assert record['start']==[4.5,2.] and record['goal']==[6.,2.]
    assert record['initial_proof_sha256']==reference._chain.previous.proof_sha256
    assert record['initial_seed_sha256']==reference._chain.seed_evidence_sha256
    assert _chain_snapshot(reference._chain)==original
    with pytest.raises(ValueError):p._prefix.floor_at((6.,2.))
    start=fresh(h);assert p.check_start(start) is p.itinerary
    assert start.height.first.log_line_seq>p.height.second.log_line_seq
    assert start.expires_at==start.height.second.received_monotonic+.5
    assert not start.input_authorized and not p.snapshot()['source_execution_wired']
    assert h.checkpoint._calibration.valid_until_monotonic==expiry
    assert h.drain_events()==()


def test_slow_planning_requires_new_pair_without_renewing_old_observations(route,monkeypatch):
    import eql_automation.camp_route_preparation as module
    h=route;p=h.route;actual=module.plan_source_itinerary;expiry=p.height.expires_at
    def slow(*args,**kwargs):
        result=actual(*args,**kwargs);h.now+=.8;return result
    monkeypatch.setattr(module,'plan_source_itinerary',slow)
    p.prepare()
    assert h.now>expiry and p.height.expires_at==expiry
    assert p.snapshot(include_evidence=True)['evidence']['planning_expires_at']==expiry
    start=fresh(h)
    assert p.check_start(start) is p.itinerary and start.height is not p.height
    h.now=start.expires_at+.01
    with pytest.raises(ValueError,match='fresh'):p.check_start(start)


def test_changed_position_after_planning_requires_replan(route):
    h=route;h.route.prepare()
    with pytest.raises(ValueError,match='replan'):fresh(h,x=4.51)
    assert h.route.phase=='stopped' and h.route.checkpoint.valid


@pytest.mark.parametrize('fault',('ancestor','lease','guide','prefix','height','itinerary','binding'))
def test_plan_cannot_outlive_changed_floor_or_owner_scope(route,fault):
    h=route;p=h.route;p.prepare()
    if fault=='ancestor':h.route_tx.cancel('F9 during planning handoff')
    elif fault=='lease':h.lease.release()
    elif fault=='guide':p.guide=replace(p.guide,goal=(8.,2.))
    elif fault=='prefix':p._prefix.seed_evidence_sha256='a'*64
    elif fault=='height':object.__setattr__(p.height.second,'raw_coordinates',(9.,9.,2.7))
    elif fault=='itinerary':p.itinerary=replace(p.itinerary,payload=b'{}')
    else:h.camp_binding=('changed',2)
    with pytest.raises(ValueError):p.check()
    assert p.phase=='stopped'


def test_stop_callback_during_geometry_never_publishes_a_ready_plan(route):
    h=route;p=h.route
    def stop():
        if p.phase=='planning':p.cancel('F9 in route geometry')
    h.binding_hook=stop
    with pytest.raises(ValueError):p.prepare()
    assert p.phase=='stopped' and p.itinerary is None and h.drain_events()==()


@pytest.mark.parametrize('fault',('body','source'))
def test_guide_must_match_retained_body_and_source(route,fault):
    h=route;p=h.route
    guide=replace(p.guide,body_height=5.) if fault=='body' else replace(p.guide,wld_sha256='a'*64)
    with pytest.raises(ValueError,match='differs'):
        CampRoutePreparation(p.checkpoint,p.height,p.lease,**dict(h.route_options,guide=guide))
