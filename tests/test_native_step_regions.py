from copy import deepcopy
from dataclasses import replace

from eql_automation.native_step_regions import classify_source_step_regions
from test_client_classification import view, leaf
from test_source_step_bsp import context
from test_source_step import face


def test_every_step_phase_keeps_independent_metadata_and_no_input():
    args, transition, _ = context()
    model = view((leaf(1),), wld_pin=args[3].wld_sha256)
    result = classify_source_step_regions(transition, args[3], args[4], model)
    assert result.complete and result.possible_flags == (0,)
    assert {p['phase'] for p in result.pieces} == {'lift','settle','transfer'}
    assert not result.input_authorized and not result.real_client_accepted
    assert not result.native_bounds_checked and not result.collision_behavior_verified


def test_transfer_interior_water_class_is_not_lost_between_clear_endpoints():
    args, transition, _ = context()
    model = view(((0.,1.,0.,.25,0,2,5), (0.,-1.,0.,.25,0,3,5),
                  (0.,0.,1.,-1.,0,4,5), leaf(2), leaf(1)), wld_pin=args[3].wld_sha256)
    result = classify_source_step_regions(transition, args[3], args[4], model)
    assert result.complete and result.possible_flags == (0,5)
    for p in result.pieces:
        flags = {v['flags'] for v in p['classification']['possible_classes']}
        assert (5 in flags) == (p['phase'] == 'transfer')


def test_changed_transition_source_and_geometry_cannot_reuse_step_classification():
    args, transition, _ = context()
    model = view((leaf(1),), wld_pin=args[3].wld_sha256)
    evidence = deepcopy(transition.evidence); evidence['radius'] = .5
    result = classify_source_step_regions(replace(transition,evidence=evidence),args[3],args[4],model)
    assert not result.complete and result.reason == 'source_step_evidence_changed'
    wrong = view((leaf(1),),wld_pin='f'*64)
    assert classify_source_step_regions(transition,args[3],args[4],wrong).reason == 'source_step_inventory_changed'
    args[4].faces_for_footprint = lambda _: (face(((0.,0.,0.),(1.,0.,0.),(0.,1.,0.)),0,99),)
    assert classify_source_step_regions(transition,args[3],args[4],model).reason == 'source_step_geometry_changed'


def test_unresolved_step_volume_is_not_a_zero_classification_result():
    args, transition, _ = context()
    model = view(((0.,0.,0.,0.,0,1,1),), wld_pin=args[3].wld_sha256)
    result = classify_source_step_regions(transition,args[3],args[4],model)
    assert not result.complete and result.reason == 'lift_model_cycle_refusal'
    assert result.possible_flags == ()
