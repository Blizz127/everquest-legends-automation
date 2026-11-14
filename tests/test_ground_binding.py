"""Ground identity and height regressions using analytic, offline fixtures."""
from dataclasses import replace

import pytest

from eql_automation.ground_binding import validate_ground_binding
import ground_binding_fixture as ground


def check(value, **changes):
    options = dict(height_calibration=ground.HEIGHT, geometry_evidence=ground.GEOMETRY,
        mesh_sha256=ground.MESH, zone_short_name='gfaydark', now=100.1,
        motion_calibration_record_id=ground.MOTION)
    options.update(changes)
    return validate_ground_binding(value, **options)


def rebound(value, **changes):
    raw = replace(value.raw_fix, **changes)
    return replace(value, raw_fix=raw,
        source_floor=replace(value.source_floor, raw_fix=raw),
        mesh_projection=replace(value.mesh_projection, raw_fix=raw))


def test_distinct_ground_heights_keep_exact_xy_and_do_not_grant_input():
    value = ground.aligned((2., 1., 1.2), source_z=.5)
    result = check(value)
    assert result.candidate and result.height_residual == 0
    assert result.source_baked_z_difference == pytest.approx(.7)
    assert not result.input_authorized and not result.real_client_accepted
    assert value.raw_fix.raw_coordinates == (1., 2., 3.)
    assert value.source_floor.ground_wld_xyz == (1., 2., .5)


def test_raw_jump_does_not_disappear_into_mesh_projection():
    value = ground.aligned()
    raw = value.raw_fix.raw_coordinates
    changed = rebound(value, raw_coordinates=(*raw[:2], raw[2]+.3))
    assert check(changed).reason == 'raw_height_does_not_match_calibrated_source_floor'


def test_self_reported_large_bake_tolerance_or_proof_cannot_replace_expected_context():
    value = ground.aligned()
    changed = replace(value, mesh_projection=replace(value.mesh_projection,
        package_xyz=(0., 0., 1000.), maximum_source_baked_z_difference=1001.))
    assert check(changed).reason == 'ground_geometry_context_mismatch'
    changed = replace(value, mesh_projection=replace(value.mesh_projection,
        same_floor_evidence_sha256='f'*64))
    assert check(changed).reason == 'ground_geometry_context_mismatch'
    changed = replace(value, mesh_projection=replace(value.mesh_projection, package_xyz=(0., 0., 1.)))
    assert check(changed).reason == 'source_mesh_same_floor_bound_exceeded'


@pytest.mark.parametrize('field,change', [
    ('source_floor', {'ground_wld_xyz':(.0001, 0., -.3)}),
    ('mesh_projection', {'package_xyz':(0., .0001, 0.)}),
    ('source_floor', {'floor_count':2}),
    ('mesh_projection', {'area':1}),
    ('mesh_projection', {'component':True}),
    ('source_floor', {'geometry_verified':False}),
    ('mesh_projection', {'same_floor_verified':False}),
    ('mesh_projection', {'projection_verified':False}),
    ('source_floor', {'source_wld_sha256':'f'*64}),
    ('mesh_projection', {'source_surface_ids':('other-floor',)}),
    ('mesh_projection', {'verified_neighbor_polygons':(3,)}),
    ('mesh_projection', {'verified_neighbor_polygons':(1,)}),
])
def test_conflicting_coordinates_floor_material_or_provenance_refuse(field, change):
    value = ground.aligned()
    assert not check(replace(value, **{field:replace(getattr(value, field), **change)})).candidate


def test_current_calibration_identity_and_raw_object_are_required():
    value = ground.aligned()
    assert not check(value, height_calibration=replace(ground.HEIGHT)).candidate
    assert not check(replace(value, raw_fix=replace(value.raw_fix))).candidate
    assert not check(replace(value, calibration_record_id=ground.HEIGHT.record_id)).candidate


@pytest.mark.parametrize('changes', [
    {'zone_id':55}, {'zone_display_name':'Other'}, {'log_epoch':2},
    {'zone_generation':2}, {'log_line_seq':0}, {'received_monotonic':100.2},
])
def test_calibration_cannot_cross_session_or_newer_log_boundary(changes):
    assert not check(rebound(ground.aligned(), **changes)).candidate


def test_calibration_lifetime_and_independent_motion_record():
    cal = replace(ground.HEIGHT, valid_from_monotonic=99., valid_until_monotonic=100.2)
    value = ground.aligned(height_calibration=cal)
    assert check(value, height_calibration=cal).candidate
    assert not check(value, height_calibration=cal, now=100.21).candidate
    assert value.calibration_record_id != cal.record_id


def test_both_xy_frames_must_be_exactly_same_raw_location():
    value = ground.aligned((2., 1., .4))
    swapped = replace(value, mesh_projection=replace(value.mesh_projection, package_xyz=(1., 2., .4)))
    assert check(swapped).reason == 'ground_projection_changed_raw_xy'


def test_oversized_integer_time_refuses_without_numeric_exception():
    assert not check(ground.aligned(), now=10**1000).candidate
