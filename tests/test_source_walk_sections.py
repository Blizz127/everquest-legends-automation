from dataclasses import replace
from types import SimpleNamespace
import math

import pytest

from eql_automation.motion_calibration import PROBES
from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.route_geometry import RouteMotionBounds
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_itinerary import SourceWalkHint,SourceItineraryGuide
from eql_automation.source_walk_sections import measurement_reserve,plan_walk_sections
from test_source_itinerary import fixture
from test_source_step import rectangle,face


def context():
    _,guide,terrain,static,bsp,policy=fixture()
    sources=rectangle(-100.,100.,0.,0)
    terrain.source_faces_for_footprint=lambda _:sources
    static.faces_for_footprint=lambda _:()
    prefix=SourceFloorChain(inventory_sha256='a'*64,seed_evidence_sha256='b'*64,
        seed_ids=((1,1),),body_height=6.)
    assert prefix.advance(swept_square((-20.,0.),(-20.,0.),.25),sources).candidate
    operations=tuple(SourceWalkHint((float(x),0.),(float(x+1),0.)) for x in range(-20,20))
    guide=replace(guide,zone='butcher',radius=.25,goal=(20.,0.),operations=operations)
    planner=SimpleNamespace(source=terrain,static=static,bsp=bsp,region_policy=replace(policy,zone='butcher'))
    bounds=RouteMotionBounds('section-bounds','motion-hypothesis',.01,.15,.2,1.,.1,.01,2.,.01,.25,6.)
    return prefix,guide,planner,bounds


def plan(prefix,guide,planner,bounds,**kwargs):
    return plan_walk_sections(prefix,guide,planner,bounds=bounds,maximum_length=10.,minimum_length=6.,
        candidate_spacing=1.,check_context=lambda:None,**kwargs)


def test_sections_preserve_every_operation_and_never_adopt_reserve_floors():
    prefix,guide,p,bounds=context();before=_chain_snapshot(prefix)
    result=plan(prefix,guide,p,bounds)
    rows=result['sections']
    assert len(rows)==4 and [r['distance'] for r in rows]==[10.]*4
    assert tuple(op for r in rows for op in SourceItineraryGuide.from_record(r['guide']).operations)==guide.operations
    assert rows[-1]['final'] and rows[-1]['measurement_reserve'] is None
    assert all(tuple(r['measurement_reserve']['native']['possible_flags'])==(0,) for r in rows[:-1])
    assert _chain_snapshot(prefix)==before
    assert not result['input_authorized'] and not result['runtime_continuation_enabled']


def test_obstacle_outside_walk_selects_an_earlier_clear_measurement_waypoint():
    prefix,guide,p,bounds=context()
    p.static.faces_for_footprint=lambda _:(face(((-10.1,.8,-1.),(-9.9,.8,-1.),(-10.,.8,8.)),0,7),)
    result=plan(prefix,guide,p,bounds)
    assert result['sections'][0]['guide']['goal']==(-12.,0.)
    assert any(a.get('refusal')=='Source motion static: other_source_surface_intersects_body_band' for a in result['attempts'])
    assert max(r['distance'] for r in result['sections'])<=10.


def test_no_clear_reserve_does_not_extend_a_section():
    prefix,guide,p,bounds=context()
    p.static.faces_for_footprint=lambda _:(face(((-100.,.8,-1.),(100.,.8,-1.),(0.,.8,20.)),0,7),)
    with pytest.raises(ValueError,match='No checked measurement reserve'):
        plan(prefix,guide,p,bounds)


def test_query_or_context_failure_does_not_become_a_candidate_exclusion(monkeypatch):
    import eql_automation.source_walk_sections as module
    prefix,guide,p,bounds=context();original=module.check_source_footprint
    def failed(prefix,footprint,**kwargs):
        if max(y for _,y in footprint)>.3:raise ValueError('Source motion static: static_query_refused')
        return original(prefix,footprint,**kwargs)
    monkeypatch.setattr(module,'check_source_footprint',failed)
    with pytest.raises(ValueError,match='static_query_refused'):plan(prefix,guide,p,bounds)


@pytest.mark.parametrize('reason', (
    'Source motion terrain: floor_patch_budget_exceeded',
    'Source motion static: complete_source_budget_exceeded',
))
def test_local_reserve_patch_limit_stays_unresolved_without_poisoning_route_floor(monkeypatch,reason):
    import eql_automation.source_walk_sections as module
    prefix,guide,p,bounds=context();original=module.check_source_footprint;before=_chain_snapshot(prefix)
    baseline=plan(prefix,guide,p,bounds)
    queries=[]
    def limited(branch,footprint,**kwargs):
        if max(y for _,y in footprint)>.3:
            queries.append(branch.previous.proof_sha256)
            if len(queries)==1:raise ValueError(reason)
        return original(branch,footprint,**kwargs)
    monkeypatch.setattr(module,'check_source_footprint',limited)
    result=plan(prefix,guide,p,bounds)
    first=result['attempts'][0]
    assert first['status']=='unresolved' and not first['candidate'] and 'refusal' not in first
    assert len(result['sections'])==4 and _chain_snapshot(prefix)==before
    assert result['checked_route_proofs_sha256']==baseline['checked_route_proofs_sha256']
    assert all(r['measurement_reserve']['source_floor_proof_sha256']!=queries[0] for r in result['sections'][:-1])


def test_ordinary_route_patch_limit_remains_fatal(monkeypatch):
    import eql_automation.source_walk_sections as module
    prefix,guide,p,bounds=context()
    def refused(*args,**kwargs):raise ValueError('Source motion terrain: floor_patch_budget_exceeded')
    monkeypatch.setattr(module,'check_source_footprint',refused)
    with pytest.raises(ValueError,match='floor_patch_budget_exceeded'):
        plan(prefix,guide,p,bounds)


def test_candidate_resource_refusal_cannot_hide_a_mutated_carried_floor(monkeypatch):
    import eql_automation.source_walk_sections as module
    prefix,guide,p,bounds=context();original=module.check_source_footprint
    def changed(branch,footprint,**kwargs):
        if max(y for _,y in footprint)>.3:
            branch.seed_evidence_sha256='c'*64
            raise ValueError('Source motion terrain: floor_patch_budget_exceeded')
        return original(branch,footprint,**kwargs)
    monkeypatch.setattr(module,'check_source_footprint',changed)
    with pytest.raises(ValueError,match='changed the carried route floor'):
        plan(prefix,guide,p,bounds)


def test_finite_section_and_query_caps_are_not_renewed():
    prefix,guide,p,bounds=context()
    with pytest.raises(ValueError,match='section budget'):plan(prefix,guide,p,bounds,maximum_sections=2)
    with pytest.raises(ValueError,match='query budget'):plan(prefix,guide,p,bounds,maximum_queries=1)


def test_complete_probe_reserve_sums_all_maximum_displacements_and_drifts():
    _,_,_,bounds=context()
    footprint,evidence=measurement_reserve((0.,0.),bounds)
    expected=4*bounds.forward_speed_upper_bound*bounds.maximum_actual_hold+3*bounds.pivot_displacement_upper_bound
    assert evidence['maximum_center_travel']==pytest.approx(expected)
    assert evidence['maximum_accumulated_drift']==pytest.approx(len(PROBES)*bounds.post_release_drift)
    assert evidence['nominal_waypoint_only'] and not evidence['arrival_offset_covered']
    assert min(math.hypot(x,y) for x,y in footprint)>=bounds.body_radius+expected
    with pytest.raises(ValueError,match='complete measurement sequence'):
        measurement_reserve((0.,0.),replace(bounds,maximum_requested_hold=.1))


def test_mutated_source_or_elapsed_deadline_stops_before_any_result():
    prefix,guide,p,bounds=context();now=[0.]
    def clock():
        now[0]+=1.;return now[0]
    with pytest.raises(ValueError,match='budget expired'):
        plan(prefix,guide,p,bounds,clock=clock,maximum_seconds=2.)
    before=_chain_snapshot(prefix)
    def changed():object.__setattr__(bounds,'body_radius',.3)
    with pytest.raises(ValueError,match='context changed'):
        plan_walk_sections(prefix,guide,p,bounds=bounds,check_context=changed)
    assert _chain_snapshot(prefix)==before
