from dataclasses import replace
from hashlib import sha256
import math

import pytest

from eql_automation.ground_sweep import motion_footprint
from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_itinerary import SourceStepHint
from eql_automation.source_step_approach import covered_by_union,plan_source_step_approach,source_step_supports
from test_source_itinerary import fixture
from test_source_step import rectangle,face
from test_client_classification import view,leaf


def run(args,**changes):
    prefix,guide,terrain,static,bsp,policy=args
    options=dict(footprint=motion_footprint((-2.,0.),90.,5.5,position_error=.01,
        heading_error_degrees=1.,post_release_drift=.01,extra_radius=1.),
        nominal_end=(3.5,0.),body_radius=1.,checked_radius=1.2,check_context=lambda:None)
    options.update(changes)
    return plan_source_step_approach(prefix,(-2.,0.),guide.operations[1],terrain,static,bsp,policy,
        **options)


def test_complete_maximum_envelope_rebuilds_step_and_exit_without_committing():
    args=fixture();prefix=args[0];before=_chain_snapshot(prefix)
    data=run(args).record()
    assert _chain_snapshot(prefix)==before
    assert data['full_motion_envelope_covered'] and not data['input_authorized']
    assert data['requires_fresh_observed_landing'] and not data['real_client_accepted']
    assert data['attempts'][0]['candidate']
    assert [r['phase'] for r in data['cells']]==['actual_start_cap','conditional_transfer','maximum_hold_exit']
    assert data['cells'][-1]['end']==[3.5,0.]
    assert all(r['native']['possible_flags']==[0] for r in data['cells'])
    assert data['cells'][1]['transfer']['evidence']['start']==[-2.,0.]


def test_split_approach_faces_use_a_compound_route_instead_of_a_foreign_seed():
    args=fixture();_,guide,terrain,static,bsp,policy=args
    sources=(*rectangle(-8.,-2.,0.,10),*rectangle(-2.,0.,0.,0),
        *rectangle(0.,6.,.3125,2),face(((0.,-5.,0.),(0.,5.,0.),(0.,5.,.3125)),4),
        face(((0.,-5.,0.),(0.,5.,.3125),(0.,-5.,.3125)),5))
    terrain.source_faces_for_footprint=lambda _:sources
    prefix=SourceFloorChain(inventory_sha256=terrain.wld_sha256,seed_evidence_sha256='e'*64,
        seed_ids=((1,10),),body_height=6.)
    assert prefix.advance(swept_square((-4.,0.),(-4.,0.),.5),sources).candidate
    before=_chain_snapshot(prefix)
    result=plan_source_step_approach(prefix,(-4.,0.),SourceStepHint((-1.,0.),(1.,0.),((1,3),),.5,1.),
        terrain,static,bsp,policy,footprint=swept_square((-4.,0.),(3.,0.),.55),
        nominal_end=(3.,0.),body_radius=.5,checked_radius=.6,check_context=lambda:None)
    data=result.record()
    assert [a['candidate'] for a in data['attempts']]==[False,True]
    assert data['attempts'][0]['reason']=='step_support_partition_failed'
    assert [c['phase'] for c in data['cells']]==['actual_start_cap','continuous_approach',
        'departure_cap','conditional_transfer','maximum_hold_exit']
    assert data['initial_seed']['sha256']=='e'*64 and _chain_snapshot(prefix)==before
    assert not data['client_step_capability_verified']


def test_overlapping_coverage_does_not_hide_even_a_tiny_gap():
    target=swept_square((0.,0.),(2.,0.),.5)
    assert covered_by_union(target,(swept_square((0.,0.),(1.,0.),.5),
                                    swept_square((1.,0.),(2.,0.),.5)))
    assert not covered_by_union(target,(swept_square((0.,0.),(.49,0.),.5),
                                       swept_square((1.49000001,0.),(2.,0.),.5)))
    assert not covered_by_union(target,(swept_square((0.,0.),(2.,0.),.49),))


@pytest.mark.parametrize('change',('corner','exit_hole','next_riser','static','native'))
def test_whole_envelope_and_added_area_are_checked(change):
    args=fixture();prefix,guide,terrain,static,bsp,policy=args
    if change=='corner':
        with pytest.raises(ValueError,match='full movement envelope'):
            run(args,footprint=swept_square((-2.,0.),(3.5,0.),1.21))
        return
    if change in ('exit_hole','next_riser'):
        current=terrain.source_faces_for_footprint(())
        sources=tuple(s for s in current if s.face not in (2,3))
        sources+=rectangle(0.,2.5,.3125,2)
        if change=='next_riser':
            sources+=(*rectangle(2.5,6.,.625,6),face(((2.5,-5.,.3125),(2.5,5.,.3125),(2.5,5.,.625)),8),
                face(((2.5,-5.,.3125),(2.5,5.,.625),(2.5,-5.,.625)),9))
        terrain.source_faces_for_footprint=lambda _:sources
    elif change=='static':
        static.faces_for_footprint=lambda _:(face(((3.,-4.,.4),(3.,4.,.4),(3.,0.,7.)),0,7),)
    else:
        model=view(((0.,1.,0.,-3.,0,2,3),leaf(2),leaf(1)),wld_pin=terrain.wld_sha256)
        policy=replace(policy,classifier=model,classification_inventory_sha256=model.inventory_sha256)
    before=_chain_snapshot(prefix)
    with pytest.raises(ValueError):run((prefix,guide,terrain,static,bsp,policy))
    assert _chain_snapshot(prefix)==before


@pytest.mark.parametrize('change',('cancel','clock','prefix','query'))
def test_cancellation_expiry_and_changed_context_discard_plan(change):
    args=fixture();calls=[0];now=[0.]
    def context():
        calls[0]+=1
        if calls[0]==5:
            if change=='cancel':raise ValueError('Owner OFF')
            if change=='clock':now[0]=11.
            if change=='prefix':args[0].index+=1
            if change=='query':args[2].source_faces_for_footprint=lambda _:()
    with pytest.raises(ValueError):run(args,check_context=context,clock=lambda:now[0])


def test_returned_dictionary_cannot_change_plan_and_resealed_bad_bytes_refuse():
    result=run(fixture());data=result.record();data['input_authorized']=True
    assert result.record()['input_authorized'] is False
    with pytest.raises(ValueError):replace(result,payload=result.payload+b' ').record()
    payload=result.payload+b' '
    with pytest.raises(ValueError):replace(result,payload=payload,sha256=sha256(payload).hexdigest()).record()


def test_geometric_support_selection_preserves_ambiguous_riser_edge():
    args=fixture();plan=run(args);terrain,static=args[2:4]
    def supports(point):return source_step_supports(plan,point,terrain,static,check_context=lambda:None)
    assert [s.height_exact for s in supports((-1.,0.))]==['0']
    assert [s.height_exact for s in supports((1.,0.))]==['5/16']
    edge=supports((0.,0.))
    assert [s.height_exact for s in edge]==['0','5/16']
    assert all(not s.complete_body_cap_verified and not s.observed_grounded and not s.input_authorized for s in edge)
    # Both are within .25 of 5/32: choosing the smaller residual would hide ambiguity.
    assert len(edge)==2 and abs(0.-5/32)<.25 and abs(5/16-5/32)<.25
    with pytest.raises(ValueError,match='outside'):supports((30.,0.))


def test_changed_geometry_cannot_supply_transition_support():
    args=fixture();plan=run(args);terrain,static=args[2:4]
    sources=terrain.source_faces_for_footprint(())
    terrain.source_faces_for_footprint=lambda _:tuple(replace(s,flag=1) for s in sources)
    with pytest.raises(ValueError,match='geometry changed'):
        source_step_supports(plan,(-1.,0.),terrain,static,check_context=lambda:None)


def test_diagonal_square_cap_growth_uses_projected_width():
    args=fixture();_,guide,terrain,static,bsp,policy=args
    scale=math.sqrt(.5)
    def rotate(p):return ((p[0]-p[1])*scale,(p[0]+p[1])*scale)
    sources=terrain.source_faces_for_footprint(())
    terrain.source_faces_for_footprint=lambda _:tuple(replace(s,vertices_wld=tuple(
        (*reversed(rotate((x,y))),z) for y,x,z in s.vertices_wld)) for s in sources)
    start=rotate((-2.8,0.));end=rotate((2.5,0.))
    chain=SourceFloorChain(inventory_sha256=terrain.wld_sha256,seed_evidence_sha256='e'*64,
        seed_ids=((1,0),),body_height=6.)
    assert chain.advance(swept_square(start,start,1.),terrain.source_faces_for_footprint(())).candidate
    hint=replace(guide.operations[1],start=rotate((-1.5,0.)),end=rotate((1.5,0.)))
    result=plan_source_step_approach(chain,start,hint,terrain,static,bsp,policy,
        footprint=motion_footprint(start,45.,5.3,position_error=.01,heading_error_degrees=1.,
            post_release_drift=.01,extra_radius=1.),nominal_end=end,body_radius=1.,checked_radius=1.5,
        check_context=lambda:None).record()
    landing=next(c['end'] for c in result['cells'] if c['kind']=='step')
    assert math.dist(landing,hint.end)==pytest.approx(.5*math.sqrt(2))
    assert result['full_motion_envelope_covered']
