"""Conditional contact geometry only; no device or current game state."""
from dataclasses import replace
from fractions import Fraction as F
from hashlib import sha256
from types import SimpleNamespace

import pytest

from eql_automation.native_region_policy import encoded
from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.route_geometry import RouteMotionBounds
from eql_automation.source_contact_plan import SourceContactIndex,SourceContactPlan,plan_source_contact
from eql_automation.source_itinerary import SourceWalkHint
from test_source_contact_envelope import setup
from test_source_step import face


def build(*,check=lambda _:None,options=None,clock=lambda:10.,maximum_seconds=30.,goal=(1.,0.)):
    args=setup(**(options or {}));_,_,sources,static,hypothesis,bsp,policy,chain=args
    terrain=SimpleNamespace(wld_sha256='a'*64,sources=sources,source_faces_for_footprint=lambda _:sources)
    before=_chain_snapshot(chain)
    plan=plan_source_contact(chain,(SourceWalkHint((-1.,0.),goal),),goal,
        terrain,static,bsp,policy,hypothesis,body_radius=.2,checked_radius=.5,
        check_context=lambda:check(args),clock=clock,maximum_seconds=maximum_seconds)
    assert _chain_snapshot(chain)==before
    return plan,args


def bounds(**changes):
    value=RouteMotionBounds('contact-bounds','synthetic-calibration',.01,.02,.05,2.,.01,
        .01,1.,.01,.2,6.)
    return replace(value,**changes)


def test_contact_plan_keeps_real_terrain_reference_and_full_vertical_motion_band():
    plan,args=build(check=lambda _:None);index=SourceContactIndex(plan)
    before=_chain_snapshot(args[-1])
    data=index.cover_pulse((0.,0.),90.,'forward',bounds(),height_interval=(.09,.10)).record()
    assert [c['kind'] for c in data['compatible']]==['sheet_top']
    assert data['compatible'][0]['height_interval_exact']==[str(F(.09459114074707031))]*2
    assert data['possible_motion_height_interval_exact']==['0','1/8']
    assert data['full_motion_coverage_checked'] and data['terrain_reference_only']
    assert data['motion_bounds']['maximum_actual_hold']==.05
    assert not any(data[k] for k in ('input_authorized','real_client_accepted','source_execution_wired'))
    assert _chain_snapshot(args[-1])==before
    assert plan.record()['current_floor_unchanged']
    assert plan.record()['contact_walks']['accepted_envelopes'][0]['contact_envelope']['ordinary_static_clearance'] is False


@pytest.mark.parametrize('height',[(-.02,.01),(.09,.10),(.09,.13)])
def test_terrain_sheet_and_transition_height_intervals_remain_compatible(height):
    plan,_=build(check=lambda _:None)
    coverage=SourceContactIndex(plan).cover_pulse((0.,0.),0.,'left',bounds(),height_interval=height)
    assert coverage.record()['possible_motion_height_interval_exact']==['0','1/8']


@pytest.mark.parametrize('height',[(-.2,-.01),(.126,.15),(.2,.1),(float('nan'),.1)])
def test_uncovered_or_invalid_height_cannot_be_projected_to_terrain(height):
    plan,_=build(check=lambda _:None)
    with pytest.raises(ValueError,match='height interval|compatible local'):
        SourceContactIndex(plan).cover_pulse((0.,0.),90.,'forward',bounds(),height_interval=height)


def test_short_requested_hold_cannot_hide_full_hold_overrun():
    plan,_=build(check=lambda _:None);index=SourceContactIndex(plan)
    assert index.cover_pulse((.9,0.),90.,'forward',bounds(),height_interval=(0.,.1))
    with pytest.raises(ValueError,match='Whole maximum-hold'):
        index.cover_pulse((.9,0.),90.,'forward',bounds(forward_speed_upper_bound=20.),height_interval=(0.,.1))


@pytest.mark.parametrize('point,height',[
    ((3.,0.),(.09,.10)),  # Above terrain with no nearby declared sheet.
    ((0.,0.),(.12,.13)),  # Above the actual rug but below the .125 clearance bound.
    ((0.,0.),(.04,.06)),  # Neither terrain nor sheet top away from a sheet edge.
])
def test_unsupported_current_contact_height_is_not_an_envelope_assumption(point,height):
    plan,_=build(goal=(4.,0.))
    with pytest.raises(ValueError,match='compatible.*contact'):
        SourceContactIndex(plan).cover_pulse(point,90.,'forward',bounds(),height_interval=height)


def test_exact_height_intervals_keep_both_supports_and_only_local_edge_transitions():
    plan,_=build(goal=(4.,0.));index=SourceContactIndex(plan)
    interval=(F(-1,100),F(1,8))
    assert [c.kind for c in index.compatible((0.,0.),bounds(),height_interval=interval)]==['terrain','sheet_top']
    edge=index.compatible((1.9,0.),bounds(),height_interval=(F(4,100),F(6,100)))
    assert len(edge)==1 and edge[0].kind=='sheet_edge_transition'
    assert edge[0].height_interval==(F(4,100),F(6,100))
    assert index.cover_pulse((1.9,0.),90.,'forward',bounds(),height_interval=(F(4,100),F(6,100)))
    # Neither future translation toward the rug nor a future pivot admits
    # a currently unsupported elevated observation.
    for b in (bounds(forward_speed_upper_bound=40.),bounds(pivot_displacement_upper_bound=2.)):
        assert index.compatible((3.,0.),b,height_interval=(F(9,100),F(1,10)))==()
    assert index.compatible((0.,2.),bounds(),height_interval=interval)==()


@pytest.mark.parametrize('kind,changes',[
    ('left',dict(pivot_displacement_upper_bound=.4)),
    ('right',dict(position_error=.4)),
    ('forward',dict(post_release_drift=.4)),
    ('forward',dict(heading_error_degrees=180.,forward_speed_upper_bound=6.)),
])
def test_all_lateral_body_uncertainty_must_fit_corridor(kind,changes):
    plan,_=build(check=lambda _:None)
    with pytest.raises(ValueError,match='Whole maximum-hold'):
        SourceContactIndex(plan).cover_pulse((0.,0.),90.,kind,bounds(**changes),height_interval=(0.,.1))


def test_body_bounds_and_index_cannot_change_after_plan():
    plan,_=build(check=lambda _:None);index=SourceContactIndex(plan)
    with pytest.raises(ValueError,match='Matching contact body'):
        index.cover_pulse((0.,0.),0.,'left',bounds(body_radius=.1),height_interval=(0.,.1))
    index.height=(F(-1),F(1))
    with pytest.raises(ValueError,match='index changed'):index.check()
    with pytest.raises(ValueError,match='seal changed'):replace(plan,payload=plan.payload+b' ').record()


@pytest.mark.parametrize('options',[
    dict(region='native_water'),dict(region='upper_bsp'),dict(height=.126),
    dict(other=(face(((0.,-4.,0.),(0.,4.,0.),(0.,0.,10.)),0,8),)),
])
def test_complete_wall_sheet_and_region_checks_remain_mandatory(options):
    with pytest.raises(ValueError,match='No bounded contact-envelope'):
        build(check=lambda _:None,options=options)


@pytest.mark.parametrize('field',['clearance','region','lineage','hypothesis'])
def test_resealed_inconsistent_cell_cannot_issue_coverage(field):
    plan,_=build(check=lambda _:None);r=plan.record();cell=r['contact_walks']['accepted_envelopes'][0]
    if field=='clearance':cell['contact_envelope']['other_surface_occupancy']['hypothetical_body_height']=6.
    elif field=='region':cell['contact_envelope']['native']['possible_classes'][0]['flags']=1
    elif field=='lineage':cell['terrain']['proof_sha256']='f'*64
    else:cell['contact_envelope']['contact_hypothesis']['maximum_height_above_reference_terrain']=1.
    payload=encoded(r)
    with pytest.raises(ValueError,match='complete consistent'):
        SourceContactIndex(SourceContactPlan(payload,sha256(payload).hexdigest()))


def test_context_mutation_or_expiry_cannot_publish_plan():
    def mutate(args):args[3].identities[7]['placement_fragment']+=1
    with pytest.raises(ValueError,match='declaration changed'):build(check=mutate)
    ticks=iter((10.,10.,10.2))
    with pytest.raises(ValueError,match='deadline expired'):
        build(check=lambda _:None,clock=lambda:next(ticks),maximum_seconds=.1)


def test_legacy_tool_imports_are_same_runtime_geometry_functions():
    import tools.source_contact_envelope as tool
    import eql_automation.source_contact_envelope as runtime
    assert tool.ContactHypothesis is runtime.ContactHypothesis
    assert tool.audit_contact_envelope is runtime.audit_contact_envelope
    assert tool.audit_contact_walks is runtime.audit_contact_walks
