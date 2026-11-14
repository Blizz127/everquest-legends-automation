from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace
import pytest

from eql_automation.native_region_policy import NativeZeroRegionTrialPolicy
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain
from tools.source_contact_envelope import declare_contact_hypothesis, audit_contact_envelope, audit_contact_walks
from eql_automation.source_itinerary import SourceWalkHint, SourceStepHint
from eql_automation.route_floor_commit import _chain_snapshot
from test_source_step import face, rectangle
from test_bsp_volume import view as bsp_view, leaf
from test_client_classification import view as native_view


def setup(*,height=.09459114074707031,other=(),terrain_extra=(),region=None):
    terrain=(*rectangle(-5.,5.,0.,0),*terrain_extra)
    rug=tuple(replace(s,material_class='TransparentMasked') for s in rectangle(-2.,2.,height,0,7))
    sources=(*rug,*other)
    static=SimpleNamespace(inventory_sha256='d'*64,sources=sources,
        identities={7:dict(placement_fragment=110,model_wld_sha256='e'*64,
                           transform_sha256='f'*64)},faces_for_footprint=lambda _:sources)
    chain=SourceFloorChain(inventory_sha256='a'*64,seed_evidence_sha256='b'*64,
        seed_ids=((1,0),),body_height=6.)
    footprint=swept_square((-1.,0.),(1.,0.),.5)
    step=chain.advance(footprint,terrain);assert step.candidate
    bsp=bsp_view((leaf(1),));native=native_view((leaf(1),),wld_pin='a'*64)
    if region=='native_water':
        native=native_view((leaf(2),),wld_pin='a'*64)
    elif region=='upper_bsp':
        bsp=bsp_view(((0.,0.,1.,-6.1,0,2,3),leaf(1),leaf(2)),{0:{'water'}})
    policy=NativeZeroRegionTrialPolicy('e'*64,'c'*64,'a'*64,'d'*64,
        bsp.inventory_sha256,native.inventory_sha256,native)
    hypothesis=declare_contact_hypothesis(static,((7,0),(7,1)))
    return step,footprint,terrain,static,hypothesis,bsp,policy,chain


def audit(args,**changes):
    step,footprint,terrain,static,hypothesis,bsp,policy,_=args
    return audit_contact_envelope(step,footprint,terrain,static,hypothesis,
        source_wld_sha256='a'*64,bsp=bsp,region_policy=policy,**changes)


def test_exact_sheet_is_retained_as_hypothesis_not_ordinary_collision_or_route_success():
    args=setup();before=args[-1].previous
    record=audit(args)
    assert record['envelope_clear']
    assert not record['ordinary_static_clearance']
    assert record['ordinary_static']['reason']=='other_source_surface_intersects_body_band'
    assert {tuple(row['identifier']) for row in record['contact_faces']}=={(7,0),(7,1)}
    assert all(row['raw_face']['material_class']=='TransparentMasked' for row in record['contact_faces'])
    assert tuple(F(v) for v in record['region_body_band_exact'])==(0,F(6)+F(.125)+F(.01))
    assert not any(record[k] for k in ('route_candidate','contact_semantics_verified',
        'transition_kinematics_verified','input_authorized','real_client_accepted'))
    assert args[-1].previous is before


@pytest.mark.parametrize('height',[0.,-.01,.126])
def test_sheet_must_stay_strictly_above_reference_and_within_declared_small_rise(height):
    record=audit(setup(height=height))
    assert not record['envelope_clear']
    assert record['reason']=='declared_sheet_outside_bounded_contact_band'


@pytest.mark.parametrize('other',[
    (face(((0.,-4.,0.),(0.,4.,0.),(0.,0.,10.)),0,8),),
    rectangle(-5.,5.,6.1,0,8),
])
def test_wall_and_ceiling_still_block_enlarged_body(other):
    record=audit(setup(other=other))
    assert not record['envelope_clear'] and record['reason'].startswith('enlarged_body_')


def test_contact_cannot_hide_missing_inventory_or_changed_placement():
    args=setup();static=args[3]
    static.faces_for_footprint=lambda _:static.sources[:1]
    assert audit(args)['reason']=='complete_static_query_omitted_or_changed_geometry'
    args=setup();args[3].identities[7]['placement_fragment']=111
    assert audit(args)['reason']=='declared_contact_geometry_or_placement_changed'


def test_source_limit_is_checked_before_removing_declared_contact_faces():
    extras=tuple(replace(face(((-3.,-3.,20.),(3.,-3.,20.),(0.,3.,20.)),i,8),face=i)
                 for i in range(125))
    record=audit(setup(other=extras))
    assert not record['envelope_clear'] and record['reason']=='complete_contact_inventory_budget_or_duplicate'


def test_nonflat_sheet_and_bad_seal_cannot_reclassify_sources():
    args=setup();static=args[3]
    changed=replace(static.sources[0],vertices_wld=((0.,0.,.1),(1.,0.,.1),(0.,1.,.2)))
    static.sources=(changed,*static.sources[1:])
    with pytest.raises(ValueError,match='flat nondegenerate'):
        declare_contact_hypothesis(static,((7,0),(7,1)))
    with pytest.raises(ValueError,match='seal changed'):
        replace(args[4],payload=args[4].payload+b' ').record()


@pytest.mark.parametrize('region',['native_water','upper_bsp'])
def test_native_hazard_and_bsp_hazard_only_in_extra_height_still_refuse(region):
    record=audit(setup(region=region))
    assert not record['envelope_clear']
    assert record['reason'].startswith('contact_envelope_')


def test_contact_walks_keep_original_reference_and_require_exact_goal_no_steps():
    args=setup();_,_,sources,static,hypothesis,bsp,policy,chain=args
    terrain=SimpleNamespace(wld_sha256='a'*64,sources=sources,source_faces_for_footprint=lambda _:sources)
    operations=(SourceWalkHint((-1.,0.),(1.,0.)),)
    before=_chain_snapshot(chain)
    result=audit_contact_walks(chain,operations,(1.,0.),terrain,static,bsp,policy,hypothesis,
        radius=.5,check_context=lambda:None)
    assert result['exit_envelopes_clear'] and len(result['accepted_envelopes'])==1
    assert not result['route_candidate'] and _chain_snapshot(chain)==before
    for invalid,goal in ((operations,(2.,0.)),
        ((SourceStepHint((-1.,0.),(1.,0.),((1,0),),.5,1.),),(1.,0.)),
        ((operations[0],SourceWalkHint((2.,0.),(3.,0.))),(3.,0.))):
        with pytest.raises(ValueError,match='exact goal'):
            audit_contact_walks(chain,invalid,goal,terrain,static,bsp,policy,hypothesis,
                radius=.5,check_context=lambda:None)
    assert _chain_snapshot(chain)==before
