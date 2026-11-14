from dataclasses import replace
from copy import deepcopy

from eql_automation.source_step import check_source_step
from eql_automation.source_step_bsp import check_source_step_bsp
from test_bsp_volume import leaf,view
from test_source_step import setup,check,face


def context():
    args = setup()
    transition,continued = check(args)
    assert transition.candidate
    return args,transition,continued


def test_all_phases_bind_to_source_step_and_do_not_enable_input():
    args,transition,_ = context()
    result = check_source_step_bsp(transition,args[3],args[4],view((leaf(1),)))
    assert result.candidate and result.transition_sha256==transition.transition_sha256
    assert set(p['phase'] for p in result.pieces)=={'lift','settle','transfer'}
    assert all(p['traversal']['exact_closed_clipping'] for p in result.pieces)
    assert not result.input_authorized and not result.real_client_accepted
    assert not result.below_endpoint_floor_classified


def test_transfer_only_interior_hazard_is_checked():
    args,transition,_ = context()
    # Thin X interval between the disjoint departure/landing squares. Helper
    # X is raw WLD Y, so neither endpoint can see this transfer-only hazard.
    tree = view(((0.,1.,0.,.25,0,2,5),(0.,-1.,0.,.25,0,3,5),
                 (0.,0.,1.,-1.,0,4,5),leaf(1),leaf(2)),{0:{'water'}})
    result = check_source_step_bsp(transition,args[3],args[4],tree)
    assert result.reason=='transfer_labelled_bsp_volume'
    assert all(p['traversal']['candidate'] for p in result.pieces[:-1])


def test_lift_upper_body_and_unknown_below_support_are_distinguished():
    args,transition,_ = context()
    upper_hazard = view(((0.,0.,1.,-6.25,0,2,3),leaf(1),leaf(2)),{0:{'water'}})
    result = check_source_step_bsp(transition,args[3],args[4],upper_hazard)
    assert result.reason=='lift_labelled_bsp_volume'
    assert set(p['phase'] for p in result.pieces)=={'lift','settle','transfer'}
    below = view(((0.,0.,1.,.00001,0,2,0),leaf(1)))
    assert check_source_step_bsp(transition,args[3],args[4],below).candidate
    touching = view(((0.,0.,1.,0.,0,2,0),leaf(1)))
    assert check_source_step_bsp(transition,args[3],args[4],touching).reason=='lift_missing_bsp_child'


def test_changed_transfer_geometry_and_zone_cannot_reuse_acceptance():
    args,transition,_ = context(); tree = view((leaf(1),))
    changed = deepcopy(transition.evidence); changed['radius']=.5
    assert check_source_step_bsp(replace(transition,evidence=changed),args[3],args[4],tree).reason=='source_step_evidence_changed'
    assert not check_source_step_bsp(replace(transition,candidate=False),args[3],args[4],tree).candidate
    tree.wld_sha256='c'*64
    assert check_source_step_bsp(transition,args[3],args[4],tree).reason=='source_step_inventory_changed'
    tree.wld_sha256='a'*64
    args[4].faces_for_footprint=lambda _:(face(((0.,0.,0.),(1.,0.,0.),(0.,1.,0.)),0,99),)
    assert check_source_step_bsp(transition,args[3],args[4],tree).reason=='source_step_geometry_changed'


def test_downstep_uses_actual_departure_and_landing_phases():
    args,up,upper = context()
    down,_ = check_source_step(upper,args[2],args[1],args[3],args[4],
        landing_seed_ids=((1,0),),radius=1.,max_step_height=.5,max_lift=1.)
    result = check_source_step_bsp(down,args[3],args[4],view((leaf(1),)))
    assert result.candidate
    lifts = {tuple(p['selected_id']) for p in result.pieces if p['phase']=='lift'}
    settles = {tuple(p['selected_id']) for p in result.pieces if p['phase']=='settle'}
    assert all(i in ((1,2),(1,3)) for i in lifts)
    assert all(i in ((1,0),(1,1)) for i in settles)


def test_changed_endpoint_query_is_not_hidden_by_unchanged_sweep_inventory():
    args,transition,_ = context()
    sources = args[3].source_faces_for_footprint(())
    sweep = transition.evidence['footprint']
    args[3].source_faces_for_footprint=lambda fp: sources if fp==sweep else (
        replace(sources[0],flag=16),*sources[1:])
    result = check_source_step_bsp(transition,args[3],args[4],view((leaf(1),)))
    assert result.reason=='source_step_endpoint_geometry_changed'
