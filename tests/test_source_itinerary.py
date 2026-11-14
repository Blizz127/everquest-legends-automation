from dataclasses import replace

import pytest

from eql_automation.native_region_policy import NativeZeroRegionTrialPolicy
from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_itinerary import (SourceItineraryGuide, SourceWalkHint,
    SourceStepHint, plan_source_itinerary)
from test_bsp_volume import view as bsp_view, leaf
from test_client_classification import view as native_view
from test_source_step import setup, rectangle


def fixture():
    prefix, _, _, terrain, static = setup()
    terrain.archive_sha256 = 'c'*64
    bsp = bsp_view((leaf(1),))
    native = native_view((leaf(1),), wld_pin=terrain.wld_sha256)
    policy = NativeZeroRegionTrialPolicy('e'*64, 'c'*64, terrain.wld_sha256,
        static.inventory_sha256, bsp.inventory_sha256, native.inventory_sha256, native)
    # The final connector returns to an exact goal different from the last guide.
    ops = (SourceWalkHint((-2.,0.),(-1.5,0.)),
           SourceStepHint((-1.5,0.),(1.5,0.),((1,2),),.5,1.),
           SourceWalkHint((1.5,0.),(2.5,0.)),
           SourceWalkHint((2.5,0.),(1.5,0.)),
           SourceStepHint((1.5,0.),(-1.5,0.),((1,0),),.5,1.),
           SourceWalkHint((-1.5,0.),(-2.,0.)))
    guide = SourceItineraryGuide('crushbone', 'a'*64, 'd'*64, 'f'*64,
                                1., 6., (-2.5,0.), ops)
    return prefix, guide, terrain, static, bsp, policy


def run(args, start=(-2.,0.), **kwargs):
    prefix, guide, terrain, static, bsp, policy = args
    return plan_source_itinerary(prefix, start, guide, terrain, static, bsp, policy,
        **{'check_context':lambda:None, **kwargs})


def test_walk_up_walk_down_exact_destination_rebuilds_without_committing_prefix():
    args = fixture(); prefix = args[0]; before = _chain_snapshot(prefix)
    result = run(args).record()
    assert _chain_snapshot(prefix) == before
    assert result['initial_proof_sha256'] == prefix.previous.proof_sha256
    assert result['final_proof_sha256'] != prefix.previous.proof_sha256
    steps = [c for c in result['cells'] if c['kind']=='step']
    assert [c['transfer']['evidence']['direction'] for c in steps] == ['up','down']
    assert all(c['native']['possible_flags']==[0] for c in result['cells'])
    assert result['goal'] == [-2.5,0.] and result['goal_floor_height']==0
    assert result['cells'][-2]['origin']=='exact_destination_connector'
    assert result['cells'][-1]['origin']=='exact_destination_cap'
    assert not result['client_step_capability_verified'] and not result['input_authorized']
    assert result['requires_fresh_start_pair'] and not result['real_client_accepted']


def test_new_start_connects_from_its_current_floor_not_a_retained_seed():
    args = fixture(); prefix = args[0]
    result = run(args, start=(-2.1,.1)).record()
    assert result['start'] == [-2.1,.1]
    assert result['initial_seed_sha256'] == prefix.seed_evidence_sha256
    assert result['cells'][0]['start'] == [-2.1,.1]
    assert result['cells'][0]['terrain']['previous_sha256'] == prefix.previous.proof_sha256
    assert result['goal'] == [-2.5,0.]


def test_saved_guides_cannot_override_the_current_floor_or_claim_acceptance():
    args = fixture(); data = args[1].record()
    data.update(real_client_accepted=True, seed_ids=[[999,99]])
    guide = SourceItineraryGuide.from_record(data)
    assert guide == args[1]
    result = run((args[0], guide, *args[2:])).record()
    assert not result['real_client_accepted']


def test_same_xy_upstairs_connector_does_not_jump_to_downstairs_guide():
    args = fixture(); _, guide, terrain, static, bsp, policy = args
    floors = (*rectangle(-5.,5.,0.,0), *rectangle(-5.,5.,20.,10))
    terrain.source_faces_for_footprint = lambda _: floors
    prefix = SourceFloorChain(inventory_sha256='a'*64,seed_evidence_sha256='9'*64,
        seed_ids=((1,10),),body_height=6.)
    assert prefix.advance(swept_square((-2.,0.),(-2.,0.),1.),floors).candidate
    before = _chain_snapshot(prefix)
    with pytest.raises(ValueError, match='step'):
        run((prefix,guide,terrain,static,bsp,policy))
    assert _chain_snapshot(prefix)==before


def test_hazard_in_transfer_only_refuses_without_publishing_partial_itinerary():
    args = fixture()
    model = native_view(((0.,1.,0.,.25,0,2,5), (0.,-1.,0.,.25,0,3,5),
        (0.,0.,1.,-1.,0,4,5), leaf(2), leaf(1)),wld_pin='a'*64)
    policy = replace(args[-1], classifier=model, classification_inventory_sha256=model.inventory_sha256)
    before = _chain_snapshot(args[0])
    with pytest.raises(ValueError,match='native regions'):
        run((*args[:-1],policy))
    assert _chain_snapshot(args[0])==before


def test_native_refused_connector_tries_the_next_entry_without_leaking_its_cells():
    args=fixture();_,guide,terrain,static,bsp,policy=args
    floors=rectangle(-5.,5.,0.,0)
    terrain.source_faces_for_footprint=lambda _:floors
    prefix=SourceFloorChain(inventory_sha256='a'*64,seed_evidence_sha256='8'*64,
        seed_ids=((1,1),),body_height=6.)
    assert prefix.advance(swept_square((-2.,0.),(-2.,0.),.25),floors).candidate
    model=native_view(((0.,1.,0.,.25,0,2,5),(0.,-1.,0.,.25,0,3,5),
        (0.,0.,1.,-1.,0,4,5),leaf(2),leaf(1)),wld_pin='a'*64)
    policy=replace(policy,classifier=model,classification_inventory_sha256=model.inventory_sha256)
    guide=replace(guide,radius=.25,goal=(-1.,3.),operations=(
        SourceWalkHint((1.,0.),(-2.,3.)),SourceWalkHint((-2.,3.),(-1.,3.))))
    data=run((prefix,guide,terrain,static,bsp,policy)).record()
    assert data['guide_entry']==1
    assert [r['candidate'] for r in data['connector_attempts']]==[False,True]
    assert all(row['native']['possible_flags']==[0] for row in data['cells'])
    assert all(row['end']!=[1.,0.] for row in data['cells'])


@pytest.mark.parametrize('kind',('cancel','clock','prefix'))
def test_context_cancellation_expiry_and_changed_live_floor_abort(kind):
    args = fixture(); count=0; now=[0.]
    def context():
        nonlocal count
        count+=1
        if count==6:
            if kind=='cancel':raise ValueError('Owner stopped')
            if kind=='clock':now[0]=301.
            if kind=='prefix':args[0].index+=1
    with pytest.raises(ValueError):
        run(args,check_context=context,clock=lambda:now[0])


def test_final_connector_cannot_silently_accept_the_old_guide_endpoint():
    args=fixture(); guide=replace(args[1],goal=(6.,0.))
    with pytest.raises(ValueError,match='terrain'):
        run((args[0],guide,*args[2:]))


def test_guide_gap_limits_and_plan_seal_are_checked():
    args=fixture()
    with pytest.raises(ValueError,match='gap'):
        replace(args[1],operations=(SourceWalkHint((-2.,0.),(-1.5,0.)),
            SourceWalkHint((3.,0.),(4.,0.)))).validate()
    with pytest.raises(ValueError):run(args,max_connect_distance=float('nan'))
    with pytest.raises(ValueError,match='connector'):
        run(args,start=(-2.1,0.),max_connect_distance=0)
    plan=run(args)
    with pytest.raises(ValueError,match='changed'):
        replace(plan,payload=plan.payload+b' ').record()
