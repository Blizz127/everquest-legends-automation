from dataclasses import replace

import pytest

from eql_automation.camp_route_preparation import CampRoutePreparation
from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_itinerary import SourceItineraryGuide, SourceWalkHint
from eql_automation.source_section_manifest import parse_walking_sections
from eql_automation.source_walk_sections import plan_walk_sections
from test_camp_probe_continuation import confirmed, new_height, next_preparation, finish_probe
from test_camp_probe_preparation import probe
from test_camp_floor_checkpoint import checkpoint
from test_source_motion import f
from test_route_floor_commit import legacy
from test_camp_probe_transaction import pair


def make_route(h, later=False):
    tx, result=confirmed(h)
    reference=tx.retain_endpoint(result)
    guide=SourceItineraryGuide('crushbone',reference._terrain.wld_sha256,
        reference._static.inventory_sha256,'f'*64,h.probe.bounds.body_radius,
        h.probe.bounds.body_height,(6.,2.),
        (SourceWalkHint((4.5,2.),(5.,2.)),SourceWalkHint((5.,2.),(6.,2.))))
    bounds=replace(h.probe.bounds,maximum_requested_hold=.15,maximum_actual_hold=.2,
        forward_speed_upper_bound=.2,pivot_displacement_upper_bound=.001,post_release_drift=.001)
    record=plan_walk_sections(reference.fork(),guide,h.planner,bounds=bounds,
        maximum_length=1.1,minimum_length=.4,candidate_spacing=.1,
        maximum_seconds=3.,check_context=lambda:None,clock=h.clock)
    sections=parse_walking_sections(guide,record)
    assert len(sections.guides)==2
    if later:
        prep=next_preparation(h,reference,kind='forward')
        tx,result=finish_probe(h,prep,tx.lock,x=5.)
        reference=tx.retain_endpoint(result)
    height=new_height(h,reference)
    route=CampRoutePreparation(reference,height,h.lease,guide=guide,sections=sections,
        bounds=h.probe.bounds,owner_binding=h.camp_binding,binding_reader=h.probe.binding_reader,
        clock=h.clock,local_wall_clock=h.wall)
    return route


@pytest.mark.parametrize('later',(False,True))
def test_initial_and_later_entry_share_actual_reached_prefix_and_need_fresh_start(probe,monkeypatch,later):
    import eql_automation.camp_route_preparation as module
    h=probe;p=make_route(h,later)
    before=_chain_snapshot(p.checkpoint._chain)
    expiry=h.checkpoint._calibration.valid_until_monotonic
    original=module.plan_source_itinerary;calls=[]
    def capture(prefix,start,guide,*args,**kwargs):
        calls.append((prefix,start,guide,kwargs['max_seconds']))
        return original(prefix,start,guide,*args,**kwargs)
    monkeypatch.setattr(module,'plan_source_itinerary',capture)
    p.prepare(maximum_seconds=3.)
    assert p.section_index==int(later)
    assert p.full_itinerary.record()['goal']==[6.,2.]
    assert p.itinerary.record()['goal']==list(p.sections.guides[int(later)].goal)
    assert len(calls)==2 and calls[0][0] is calls[1][0] is p._prefix
    assert calls[0][1]==calls[1][1]==p.height.package_xyz[:2]
    assert calls[0][2] is p.guide and calls[1][2] is p.sections.guides[int(later)]
    assert p.itinerary.record()['guide_entry']+p.sections.ranges[int(later)][0]==p.full_itinerary.record()['guide_entry']
    for itinerary in (p.full_itinerary,p.itinerary):
        data=itinerary.record()
        assert data['initial_proof_sha256']==p.checkpoint._chain.previous.proof_sha256
        assert data['initial_seed_sha256']==p.checkpoint._chain.seed_evidence_sha256
    assert _chain_snapshot(p.checkpoint._chain)==before
    with pytest.raises(ValueError):p._prefix.floor_at(p.itinerary.record()['goal'])
    assert p.phase=='prepared' and p.start is None
    with pytest.raises(ValueError,match='Exact current'):p.check_start(None)
    released=h.now;a,b,baseline=pair(h,x=p.height.package_xyz[0])
    start=p.observe_start(a,b,minimum_log_seq=baseline,released_at=released)
    assert start.height.first.log_line_seq>p.height.second.log_line_seq
    assert p.check_start(start) is p.itinerary
    assert h.checkpoint._calibration.valid_until_monotonic==expiry
    assert not start.input_authorized and h.drain_events()==()


def test_planning_pair_cannot_be_used_as_start(probe):
    h=probe;p=make_route(h);p.prepare(maximum_seconds=3.)
    with pytest.raises(ValueError):
        p.observe_start(p.height.first,p.height.second,
            minimum_log_seq=p.height.second.log_line_seq,released_at=h.now)
    assert p.phase=='stopped' and p.checkpoint.valid and h.drain_events()==()


@pytest.mark.parametrize('expire',(False,True))
def test_two_pass_planning_shares_one_deadline(probe,monkeypatch,expire):
    import eql_automation.camp_route_preparation as module
    h=probe;p=make_route(h);original=module.plan_source_itinerary;limits=[]
    expiry=p.height.expires_at
    def delayed(*args,**kwargs):
        limits.append(kwargs['max_seconds']);result=original(*args,**kwargs)
        if len(limits)==1:h.now+=.8
        return result
    monkeypatch.setattr(module,'plan_source_itinerary',delayed)
    if expire:
        with pytest.raises(ValueError,match='deadline expired'):p.prepare(maximum_seconds=.5)
        assert limits==[.5] and p.phase=='stopped' and p.itinerary is None
    else:
        p.prepare(maximum_seconds=2.)
        assert limits[0]==2. and limits[1]==pytest.approx(1.2)
        assert h.now>expiry and p.height.expires_at==expiry and p.start is None
        released=h.now;a,b,baseline=pair(h)
        start=p.observe_start(a,b,minimum_log_seq=baseline,released_at=released)
        assert p.check_start(start) is p.itinerary and start.height is not p.height
    assert h.drain_events()==()


@pytest.mark.parametrize('fault',('section', 'partition', 'index', 'full_plan'))
def test_prepared_section_cannot_outlive_changed_selection(probe,fault):
    h=probe;p=make_route(h);p.prepare(maximum_seconds=3.)
    if fault=='section':object.__setattr__(p.sections.guides[0].operations[0],'end',(9.,2.))
    elif fault=='partition':p.sections=replace(p.sections,record_sha256='a'*64)
    elif fault=='index':p.section_index=1
    else:p.full_itinerary=replace(p.full_itinerary,payload=b'{}')
    with pytest.raises(ValueError):p.check()
    assert p.phase=='stopped' and h.drain_events()==()
