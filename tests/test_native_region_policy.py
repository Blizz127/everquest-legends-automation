"""Explicit planning/height continuation; no game input or movement waiver."""
from dataclasses import replace
from hashlib import sha256
import json
from types import SimpleNamespace

import pytest

from eql_automation.bsp_volume import BspVolumeView
from eql_automation.current_route_start import CurrentStartPlanner
from eql_automation.native_region_policy import (
    NativeZeroRegionTrialPolicy, NativeRegionPlanningEvidence, encoded)
from eql_automation.observed_height import measure_current_height, current_height_allowed
from test_client_classification import view, leaf
from test_current_route_start import fixture, WLD
from test_floor_bootstrap import fresh, add_boundary


MISSING = ((1., 0., 0., 0., 0, 0, 2), leaf(1))


def setup(tmp_path, *, native_nodes=MISSING, policy=True, zone='crushbone', old_water=False,
          wall=False, boundary=False):
    f = fixture(tmp_path, wall=wall)
    if boundary:
        add_boundary(f)
        f.options['allow_overhead_boundary'] = True
    old = f.planner
    bsp = BspVolumeView(SimpleNamespace(nodes=(leaf(1),) if old_water else MISSING,
        labels_by_region={0:{'water'}} if old_water else {}), region_count=3, wld_sha256=WLD)
    classifier = view(native_nodes, wld_pin=WLD)
    region_policy = NativeZeroRegionTrialPolicy(*old.pins, bsp.inventory_sha256,
        classifier.inventory_sha256, classifier) if policy else None
    f.planner = CurrentStartPlanner(mesh=old.mesh, ground=old.ground, source=old.source,
        static=old.static, bsp=bsp, zone_short_name=zone, expected_zone_id=58,
        expected_zone_name=old.zone_name, mesh_sha256=old.pins[0], source_archive_sha256=old.pins[1],
        source_wld_sha256=old.pins[2], static_inventory_sha256=old.pins[3], region_policy=region_policy)
    f.reader.zone_id = 58
    f.a = replace(f.a, zone_id=58); f.b = replace(f.b, zone_id=58); f.reader.latest = f.b
    f.plan = lambda: f.planner.plan(f.reader, f.a, f.b, **f.options)
    return f


def validate(plan):
    record = json.loads(plan.evidence_bytes)
    return plan.region_policy.validate(plan.native_region_evidence,
        **{k:record[k] for k in ('terrain', 'static', 'bsp')})


def test_explicit_policy_preserves_old_refusal_and_accepts_only_planning(tmp_path):
    f = setup(tmp_path, policy=False)
    with pytest.raises(ValueError, match='missing_bsp_child'): f.plan()
    enabled = tmp_path/'enabled'; enabled.mkdir()
    f = setup(enabled, boundary=True); plan = f.plan(); record = json.loads(plan.evidence_bytes)
    assert record['format'] == 'eql-current-start-geometry-v2'
    assert not record['bsp']['candidate'] and record['bsp']['reason'] == 'missing_bsp_child'
    assert record['terrain']['candidate'] and record['static']['candidate']
    assert record['native_region']['native_body']['possible_flags'] == [0]
    assert validate(plan)
    assert not plan.input_authorized and not plan.real_client_accepted
    assert not record['native_region']['policy']['installed_binary_match_verified']
    a, b, options = fresh(f, plan)
    cal = measure_current_height(plan.observer, f.reader, a, b, **options)
    assert cal.raw_z_minus_source_z == 2.5 and not cal.live_verified
    assert current_height_allowed(cal, mode='measurement')
    for mode in ('assist', 'full_auto', 'off'):
        assert not current_height_allowed(cal, mode=mode)


@pytest.mark.parametrize('nodes', [(leaf(2),), (leaf(3),),
    ((0.,0.,0.,0.,0,1,1),), (),
    ((0.,1.,0.,-4.,0,2,3), leaf(1), leaf(2))])
def test_water_transition_incomplete_empty_and_mixed_classification_refuse(tmp_path, nodes):
    f = setup(tmp_path, native_nodes=nodes)
    with pytest.raises(ValueError, match='Native-zero|Every native'): f.plan()


def test_old_hazard_and_static_collision_are_not_waived(tmp_path):
    f = setup(tmp_path, old_water=True, native_nodes=(leaf(1),))
    with pytest.raises(ValueError, match='Native-zero'): f.plan()
    other = tmp_path/'wall'; other.mkdir()
    f = setup(other, wall=True)
    with pytest.raises(ValueError, match='static geometry'): f.plan()


def test_other_zone_and_replaced_policy_refuse(tmp_path):
    with pytest.raises(ValueError, match='Crushbone'): setup(tmp_path, zone='gfaydark')
    f = setup(tmp_path); f.planner.region_policy = replace(f.planner.region_policy)
    with pytest.raises(ValueError, match='policy changed'): f.plan()


@pytest.mark.parametrize('change', ['flags', 'empty', 'duplicate', 'incomplete', 'floor', 'static', 'policy'])
def test_resealed_nested_evidence_must_still_match_complete_zero_policy(tmp_path, change):
    f = setup(tmp_path); plan = f.plan()
    saved = plan.native_region_evidence.record()
    native = saved['native_body']
    if change == 'flags': native['pieces'][0]['classification']['possible_classes'][0]['flags'] = 1 << 31
    elif change == 'empty': native['pieces'] = []
    elif change == 'duplicate': native['pieces'].append(native['pieces'][0])
    elif change == 'incomplete': native['pieces'][0]['classification']['complete'] = False
    elif change == 'floor': native['floor_proof_sha256'] = 'f'*64
    elif change == 'static': saved['static_sha256'] = 'f'*64
    elif change == 'policy': saved['policy']['scope'] = 'full_auto'
    payload = encoded(saved)
    altered = replace(plan, native_region_evidence=NativeRegionPlanningEvidence(payload,sha256(payload).hexdigest()))
    with pytest.raises(ValueError): validate(altered)
    assert validate(plan)  # Returned dictionaries cannot mutate the sealed bytes.


@pytest.mark.parametrize('change', ['seal', 'missing_policy', 'missing_evidence', 'classifier', 'seed'])
def test_changed_policy_or_evidence_cannot_supply_height(tmp_path, change):
    f = setup(tmp_path); plan = f.plan()
    if change == 'seal':
        plan = replace(plan, native_region_evidence=replace(plan.native_region_evidence, sha256='f'*64))
    elif change == 'missing_policy': plan = replace(plan, region_policy=None)
    elif change == 'missing_evidence': plan = replace(plan, native_region_evidence=None)
    elif change == 'classifier': plan.region_policy.classifier.inventory_sha256 = 'f'*64
    elif change == 'seed': plan.floor_chain.seed_evidence_sha256 = 'f'*64
    a,b,options = fresh(f, plan)
    with pytest.raises(ValueError): measure_current_height(plan.observer,f.reader,a,b,**options)


def test_classifier_change_during_height_callback_refuses(tmp_path):
    f = setup(tmp_path); plan = f.plan(); a,b,options = fresh(f,plan)
    original = plan.floor_chain.floor_at
    def lookup(xy):
        value = original(xy)
        plan.region_policy.classifier.inventory_sha256 = 'f'*64
        return value
    plan.floor_chain.floor_at = lookup
    with pytest.raises(ValueError): measure_current_height(plan.observer,f.reader,a,b,**options)


def test_destination_does_not_drop_native_initial_policy(tmp_path):
    from eql_automation.destination_route import plan_destination
    f = setup(tmp_path)
    with pytest.raises(ValueError, match='destination execution is not wired'):
        plan_destination(f.planner,None,f.reader,f.a,f.b,goal_xy=(4.,5.),
                         **{k:v for k,v in f.options.items() if k != 'length'})


def test_final_native_validation_time_is_included_in_height_freshness(tmp_path):
    f = setup(tmp_path); plan = f.plan(); a,b,options = fresh(f,plan)
    classifier = plan.region_policy.classifier; original = classifier._check; calls = []
    def delayed():
        original(); calls.append(1)
        # Initial binding, first height check, two source lookups, final check.
        if len(calls) == 5: f.now += .6
    classifier._check = delayed
    with pytest.raises(ValueError, match='expired'):
        measure_current_height(plan.observer,f.reader,a,b,**options)
    assert len(calls) == 5
