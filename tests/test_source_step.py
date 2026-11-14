from dataclasses import replace
from types import SimpleNamespace

import pytest

from eql_automation.portal_precision import SourceFace
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_step import check_source_step


def face(points,index,fragment=1):
    return SourceFace(tuple((y,x,z) for x,y,z in points),0,'Diffuse',fragment,index)


def rectangle(x0,x1,z,index,fragment=1):
    value=z if callable(z) else lambda _:z
    a,b,c,d=((x0,-5.,value(x0)),(x1,-5.,value(x1)),
             (x1,5.,value(x1)),(x0,5.,value(x0)))
    return (face((a,b,c),index,fragment),face((a,c,d),index+1,fragment))


def setup(*,gap=0.,riser=True,static=(),upper_width=5.,ramps=False):
    low=(lambda x:-.05*x) if ramps else 0.
    high=(lambda x:.3125-.2*x) if ramps else .3125
    sources=(*rectangle(-5.,0.,low,0),*rectangle(gap,upper_width,high,2))
    if riser:
        sources+= (face(((0.,-5.,0.),(0.,5.,0.),(0.,5.,.3125)),4),
                   face(((0.,-5.,0.),(0.,5.,.3125),(0.,-5.,.3125)),5))
    view=SimpleNamespace(wld_sha256='a'*64,source_faces_for_footprint=lambda _:sources)
    objects=SimpleNamespace(inventory_sha256='d'*64,faces_for_footprint=lambda _:static)
    start=(-2.,0.);end=(2.,0.)
    chain=SourceFloorChain(inventory_sha256='a'*64,seed_evidence_sha256='b'*64,
                           seed_ids=((1,0),),body_height=6.)
    assert chain.advance(swept_square(start,start,1.),sources).candidate
    return chain,start,end,view,objects


def check(args,**changes):
    return check_source_step(*args,landing_seed_ids=((1,2),),
                             **dict(radius=1.,max_step_height=.5,max_lift=1.,**changes))


def test_full_step_certificate_links_old_floor_to_explicit_landing_and_suffix():
    args=setup();prefix=args[0];before=prefix.previous
    result,continued=check(args)
    assert result.candidate and result.evidence['riser']['rises']==['5/16','5/16']
    assert continued.previous.reason=='conditional_step_landing_only'
    assert continued.previous.previous_sha256==before.proof_sha256
    assert continued.previous.proof_sha256==result.landing_proof_sha256
    assert not continued.previous.carried_ids and not continued.previous.joins
    assert continued.index==prefix.index+1 and prefix.previous is before and not prefix.halted
    assert result.transition_sha256 and not result.bsp_classified and not result.input_authorized
    assert result.conditional_kinematic_hypothesis and not result.client_step_capability_verified
    next_step=continued.advance(swept_square((2.,0.),(2.5,0.),1.),args[3].source_faces_for_footprint(()))
    assert next_step.candidate and next_step.previous_sha256==result.landing_proof_sha256


def test_ramp_endpoints_use_conservative_lift_and_settle_envelopes():
    result,_=check(setup(ramps=True))
    assert result.candidate
    assert result.evidence['lift']['hypothetical_body_height']>6.
    assert result.evidence['settle']['hypothetical_body_height']>6.


@pytest.mark.parametrize('options',({'gap':.01},{'riser':False},{'upper_width':2.5}))
def test_missing_support_wall_or_landing_is_not_replaced_by_a_flat_floor(options):
    args=setup(**options);result,continued=check(args)
    assert not result.candidate and continued is None
    assert not args[0].halted and args[0].index==1


def test_wall_intersecting_only_the_transfer_is_not_exempted_as_a_riser():
    wall=face(((0.,-4.,.5),(0.,4.,.5),(0.,0.,12.)),0,7)
    result,_=check(setup(static=(wall,)))
    assert not result.candidate and result.reason=='step_transfer_body_band_intersection'
    assert result.evidence['lift']['candidate'] and result.evidence['settle']['candidate']


@pytest.mark.parametrize('phase,ceiling',(('lift',(-5.,-.5,6.2)),('settle',(.5,5.,6.38))))
def test_low_ceiling_blocks_the_phase_even_when_standing_is_clear(phase,ceiling):
    result,_=check(setup(static=rectangle(*ceiling,0,7)))
    assert not result.candidate and result.reason==phase+'_other_source_surface_intersects_body_band'


def test_downward_transfer_is_explicit_and_keeps_the_riser_in_geometry():
    args=setup();up,upper=check(args)
    down,lower=check_source_step(upper,args[2],args[1],args[3],args[4],landing_seed_ids=((1,0),),
                                 radius=1.,max_step_height=.5,max_lift=1.)
    assert down.candidate and down.evidence['direction']=='down'
    assert down.evidence['riser']['rises']==['5/16','5/16']
    assert lower.previous.previous_sha256==up.landing_proof_sha256
    assert not down.client_step_capability_verified


def test_height_limits_source_changes_and_uncommitted_start_refuse():
    args=setup()
    result,_=check_source_step(*args,landing_seed_ids=((1,2),),radius=1.,max_step_height=.35,max_lift=.4)
    assert result.reason=='step_lift_bound_exceeded'
    result,_=check_source_step(*args,landing_seed_ids=((1,2),),radius=1.,max_step_height=.2,max_lift=1.)
    assert result.reason=='complete_bounded_source_riser_not_found'
    result,_=check_source_step(args[0],(-2.1,0.),args[2],args[3],args[4],landing_seed_ids=((1,2),),
                              radius=1.,max_step_height=.5,max_lift=1.)
    assert result.reason=='source_step_needs_committed_start_cap'
    sources=args[3].source_faces_for_footprint(())
    args[3].source_faces_for_footprint=lambda _:(replace(sources[0],material_class='Water'),*sources[1:])
    result,_=check(args)
    assert not result.candidate and not args[0].halted
