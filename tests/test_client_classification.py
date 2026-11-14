"""Exact float32 enclosures and metadata identity, not movement acceptance."""
from fractions import Fraction
from types import SimpleNamespace
import json
import random
import struct

import pytest

from eql_automation.client_bsp_probe import ClientBspTreeView
from eql_automation.client_region_labels import ClientRegionMap
from eql_automation.client_region_classification import (
    ClientBspClassificationView, _rn32, _rounded_interval, _mul, _plane_range,
    MIN_NORMAL, MIN_SUBNORMAL, MAX_FINITE)
from eql_automation.native_body_regions import classify_source_body_regions
from eql_automation.portal_precision import SourceFace
from test_region_audit import region_wld, point_wld
from test_current_route_start import fixture, WLD


def leaf(region): return (0., 0., 0., 0., region, 0, 0)


def view(nodes, *, water_id=1, wld_pin=None):
    labels = ClientRegionMap(region_wld(water_id=water_id))
    if wld_pin is not None: labels.wld_sha256 = wld_pin  # Explicit synthetic geometry identity.
    tree = ClientBspTreeView(nodes, region_count=3, wld_sha256=labels.wld_sha256)
    return ClientBspClassificationView(tree, labels)


def box(a=-1., b=1.):
    return tuple((x, y, z) for x in (a,b) for y in (0.,1.) for z in (0.,1.))


def test_exact_rounding_parities_and_double_rounding_counterexample():
    half = Fraction(1, 1 << 24)
    assert _rn32(1+half) == 1
    assert _rn32(1+3*half) == 1+4*half
    q = 1+half+Fraction(1, 1 << 54)
    assert struct.unpack('<f', struct.pack('<f', float(q)))[0] == 1.
    assert _rn32(q) == 1+2*half and _rn32(-q) == -1-2*half


def test_subnormal_ties_minimum_normal_carry_and_overflow():
    assert _rn32(MIN_SUBNORMAL/2) == 0
    assert _rn32(3*MIN_SUBNORMAL/2) == 2*MIN_SUBNORMAL
    assert _rn32(MIN_NORMAL-MIN_SUBNORMAL/2) == MIN_NORMAL
    assert _rn32(MAX_FINITE) == MAX_FINITE
    for sign in (-1, 1):
        with pytest.raises(ValueError, match='overflow'): _rn32(sign*(MAX_FINITE+(1 << 103)))


def test_representable_values_and_binary64_inputs_match_scalar_rounding():
    rng = random.Random(720)
    for _ in range(500):
        bits = rng.randrange(0, 0x7f7fffff)
        value = struct.unpack('<f', struct.pack('<I', bits))[0]
        assert _rn32(Fraction(value)) == Fraction(value)
        sample = rng.uniform(-10000., 10000.)
        expected = struct.unpack('<f', struct.pack('<f', sample))[0]
        assert float(_rn32(Fraction(sample))) == expected


def test_uncertain_daz_ftz_includes_zero_without_discarding_subnormals():
    assert _rounded_interval(MIN_SUBNORMAL, MIN_SUBNORMAL) == (0, MIN_SUBNORMAL)
    assert _rounded_interval(-MIN_SUBNORMAL, -MIN_SUBNORMAL) == (-MIN_SUBNORMAL, 0)
    assert _mul((MIN_NORMAL, MIN_NORMAL), Fraction(-1,2)) == (-MIN_NORMAL/2, 0)
    assert _rounded_interval(-MIN_NORMAL, MIN_NORMAL) == (-MIN_NORMAL, MIN_NORMAL)
    assert _rounded_interval(MIN_NORMAL, MIN_NORMAL) == (MIN_NORMAL, MIN_NORMAL)


def test_operation_order_preserves_binary32_cancellation_and_zero_positive():
    p = (-1., 1., 1.)
    plane = (1., 2.**25, -2.**25, 0.)
    assert _plane_range(tuple((Fraction(v), Fraction(v)) for v in p), plane) == (0,0)
    model = view(((*plane, 0, 2, 3), leaf(1), leaf(2)))
    classified = model.classify_convex_enclosure_after_bounds((p,)*4)
    assert classified.complete and {c.region_id for c in classified.possible_classes} == {0}


def test_missing_untyped_and_typed_default_zero_keep_distinct_origins():
    missing = view(((1.,0.,0.,0.,0,0,2), leaf(1)))
    p = missing.classify_point_after_bounds(1.,0.,0.)
    assert p.complete and p.classification.origin == 'missing_child'
    assert p.classification.flags == 0 and not p.classification.callback_invoked
    untyped = missing.classify_point_after_bounds(-1.,0.,0.)
    assert untyped.classification.origin == 'untyped_region' and untyped.classification.region_id == 0
    assert not untyped.classification.callback_invoked
    transition = view((leaf(3),), water_id=2).classify_point_after_bounds(0.,0.,0.)
    assert transition.classification.flags == 1 << 31 and transition.classification.class_id == 0
    assert transition.classification.callback_invoked and transition.classification.record_index == 1
    assert transition.classification.transition_write_kind == 'copy_complete_label'


def test_copied_wld_composition_preserves_precedence_and_full_flags():
    model = ClientBspClassificationView.from_wld(region_wld(water_id=2, tree_region_ref=3))
    result = model.classify_point_after_bounds(0.,0.,0.)
    assert result.classification.raw_label == 'DRNTP00255000001'
    assert result.classification.flags == 1 << 31
    other = ClientBspClassificationView.from_wld(region_wld())
    assert model.inventory_sha256 != other.inventory_sha256
    assert not result.bounds_checked and not result.collision_verified and not result.input_authorized


def test_volume_contains_point_classes_and_retains_water_inside_boundary():
    model = ClientBspClassificationView.from_wld(point_wld())
    vertices = tuple((x,y,z) for x in (-1.,1.) for y in (-1.,1.) for z in (0.,1.))
    result = model.classify_convex_enclosure_after_bounds(vertices)
    assert result.complete and {v.flags for v in result.possible_classes} == {0,5,1 << 31}
    for x in (-1.,-.001,0.,.001,1.):
        for y in (-1.,0.,1.):
            p = model.classify_point_after_bounds(x,y,.5)
            assert p.classification in result.possible_classes
    assert not result.ancestor_clipping_used and not result.collision_verified
    assert not result.bounds_checked and not result.input_authorized and not result.real_client_accepted


def test_subnormal_sign_uncertainty_visits_both_children():
    model = view(((-.5,0.,0.,0.,0,2,3), leaf(1), leaf(2)))
    vertices = tuple((MIN_NORMAL,y,z) for y in (0,1) for z in (0,1))
    result = model.classify_convex_enclosure_after_bounds(vertices)
    assert result.complete and {v.flags for v in result.possible_classes} == {0,5}


def test_tiny_exact_product_rounding_to_normal_still_encloses_ftz_zero():
    x = Fraction(1)-Fraction(1, 1 << 24)
    for sign in (-1, 1):
        point = (sign*x, Fraction(0), Fraction(0))
        actual = _plane_range(tuple((v,v) for v in point), (MIN_NORMAL,0,0,0))
        expected = (-MIN_NORMAL,0) if sign < 0 else (0,MIN_NORMAL)
        assert actual == expected
    model = view(((float(MIN_NORMAL),0.,0.,0.,0,2,3), leaf(1), leaf(2)))
    result = model.classify_convex_enclosure_after_bounds(((-x,0,0),)*4)
    assert result.complete and {v.flags for v in result.possible_classes} == {0,5}


@pytest.mark.parametrize('nodes,reason', [
    ((), 'null_root_special_return'),
    (((1.,0.,0.,0.,0,1,0),), 'model_cycle_refusal'),
    (((3e38,0.,0.,0.,0,0,0),), 'unsupported_arithmetic'),
])
def test_unresolved_volume_never_becomes_default_zero(nodes, reason):
    result = view(nodes).classify_convex_enclosure_after_bounds(box(2.,3e38))
    assert not result.complete and result.reason == reason


def test_nonzero_region_precedes_cycle_and_budgets_remain_unresolved():
    model = view(((1.,0.,0.,0.,2,1,1),))
    assert model.classify_convex_enclosure_after_bounds(box()).possible_classes[0].flags == 5
    model = view(((1.,0.,0.,0.,0,2,3), leaf(1), leaf(2)))
    assert not model.classify_convex_enclosure_after_bounds(box(), max_visits=1).complete
    assert not model.classify_convex_enclosure_after_bounds(box(), max_depth=1).complete
    assert not model.classify_point_after_bounds(1.,0.,0., max_visits=1).complete


def test_changed_classifier_snapshot_refuses():
    model = view((leaf(1),))
    model.mapping = (-1,-1,-1)
    with pytest.raises(ValueError, match='snapshot'): model.classify_point_after_bounds(0.,0.,0.)


def test_body_adapter_keeps_static_proof_and_hazard_metadata_separate(tmp_path):
    f = fixture(tmp_path); plan = f.plan(); step = plan.floor_chain.previous
    footprint = tuple(tuple(p) for p in json.loads(plan.evidence_bytes)['seed']['footprint'])
    sources = f.planner.source.source_faces_for_footprint(footprint)
    classifier = view((leaf(2),), wld_pin=WLD)
    call = lambda: classify_source_body_regions(step, footprint, sources, f.planner.static,
                                               classifier, source_wld_sha256=WLD)
    result = call()
    assert result.complete and result.possible_flags == (5,)
    assert not result.input_authorized and not result.collision_behavior_verified
    assert not result.below_floor_classified
    wrong = classify_source_body_regions(step, footprint, sources, f.planner.static,
                                         classifier, source_wld_sha256='f'*64)
    assert not wrong.complete and wrong.reason == 'native_classification_source_mismatch'
    wall = SourceFace(((2.,3.,0.),(2.,5.,0.),(2.,4.,8.)),0,'Diffuse',30,0)
    f.planner.static.faces_for_footprint = lambda _: (wall,)
    refused = call()
    assert not refused.complete and refused.reason.startswith('terrain_static_')
