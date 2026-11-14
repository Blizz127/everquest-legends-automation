from dataclasses import replace
import math

import pytest

from eql_automation.ground_sweep import (
    GroundFace, check_ground_coverage, cross, motion_footprint,
)


SQUARE = ((-1., -1.), (1., -1.), (1., 1.), (-1., 1.))


def rectangle(x0, y0, x1, y1, height=lambda x, y: 0.):
    a, b, c, d = [(x, y, height(x, y)) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    return (GroundFace((a, b, c), 63, 1), GroundFace((a, c, d), 63, 1))


def check(faces, **changes):
    return check_ground_coverage(SQUARE, faces, reference=(-.5, 0., 0.), component=1, **changes)


def test_filled_flat_patch_is_ground_candidate_never_input_permission():
    result = check(rectangle(-2, -2, 2, 2))
    assert result.candidate and result.covered_area == pytest.approx(4.)
    assert not result.real_client_accepted and not result.input_authorized


def test_interior_hole_cannot_pass_from_perimeter_or_endpoint_samples():
    faces = (rectangle(-1, -1, -.1, 1) + rectangle(.1, -1, 1, 1)
             + rectangle(-.1, -1, .1, -.1) + rectangle(-.1, .1, .1, 1))
    result = check(faces)
    assert not result.candidate and result.reason == "uncovered_ground_area"
    assert result.covered_area == pytest.approx(3.96)


def test_duplicate_area_cannot_hide_missing_ground():
    left = rectangle(-1, -1, 0, 1)
    result = check(left + left)
    assert not result.candidate and result.reason == "overlapping_ground_faces"


def test_many_subtolerance_overlaps_cannot_compensate_for_a_hole():
    faces = ()
    for index in range(8):
        left = -1. + index * .25 - (1e-8 if index else 0.)
        right = -1. + (index + 1) * .25 - (7e-8 if index == 7 else 0.)
        faces += rectangle(left, -1., right, 1.)
    result = check(faces)
    assert not result.candidate and result.reason == "overlapping_ground_faces"


def test_overlapping_floors_are_ambiguous_even_when_both_are_ground():
    result = check(rectangle(-1, -1, 1, 1) + rectangle(-1, -1, 1, 1, lambda x, y: .1))
    assert not result.candidate and result.reason == "overlapping_ground_faces"


def test_shared_xy_seam_with_height_step_refuses():
    result = check(rectangle(-1, -1, 0, 1) + rectangle(0, -1, 1, 1, lambda x, y: .2))
    assert not result.candidate and result.reason == "discontinuous_ground_seam"


def test_plane_slope_checks_the_whole_clipped_face():
    result = check(rectangle(-1, -1, 1, 1, lambda x, y: 2 * x))
    assert not result.candidate and result.reason == "steep_detail_plane"
    assert result.max_grade == pytest.approx(2.)


@pytest.mark.parametrize("changes", [dict(area_id=1), dict(area_id=4), dict(component=2), dict(component=-1)])
def test_forbidden_area_or_other_component_cannot_supply_coverage(changes):
    result = check(tuple(replace(f, **changes) for f in rectangle(-1, -1, 1, 1)))
    assert not result.candidate and result.reason == "forbidden_area_or_other_component"


def test_reference_height_and_height_window_do_not_pick_an_unrelated_floor():
    assert check(rectangle(-1, -1, 1, 1, lambda x, y: 1.)).reason == "reference_ground_not_supported"
    assert check(rectangle(-1, -1, 1, 1, lambda x, y: 10.)).reason == "reference_ground_not_supported"
    # Far overhead surfaces are deliberately outside this ground-only check.
    assert check(rectangle(-1, -1, 1, 1) + rectangle(-1, -1, 1, 1, lambda x, y: 10.)).candidate


def test_face_budget_invalid_values_and_degenerate_footprint_refuse():
    assert check(rectangle(-1, -1, 1, 1), max_faces=1).reason == "invalid_footprint_or_face_budget"
    bad = GroundFace(((0., 0., float('nan')), (1., 0., 0.), (1., 1., 0.)), 63, 1)
    assert check((bad,)).reason == "invalid_detail_face"
    result = check_ground_coverage(((0., 0.), (1., 0.), (2., 0.)), (), reference=(0., 0., 0.), component=1)
    assert not result.candidate


def test_small_missing_strip_is_reported_with_explicit_area_tolerance():
    faces = rectangle(-1, -1, 0, 1) + rectangle(.0001, -1, 1, 1)
    result = check(faces)
    assert result.reason == "uncovered_ground_area"
    assert result.footprint_area - result.covered_area == pytest.approx(.0002)


@pytest.mark.parametrize("heading", [0., 37., 180., 359.])
def test_footprint_encloses_entire_uncertain_motion_not_just_endpoint(heading):
    origin, reach, error = (7., -12.), 5., 15.
    footprint = motion_footprint(origin, heading, reach, position_error=.2,
        heading_error_degrees=error, post_release_drift=.1, extra_radius=.3)
    for distance in (0., 1., 2.5, 5.):
        for offset in (-15., -7., 0., 9., 15.):
            direction = math.radians(heading + offset)
            for angle in range(0, 360, 15):
                p = (origin[0] + distance * math.sin(direction) + .6 * math.cos(math.radians(angle)),
                     origin[1] + distance * math.cos(direction) + .6 * math.sin(math.radians(angle)))
                assert all(cross(footprint[i], footprint[(i + 1) % len(footprint)], p) >= -1e-8 for i in range(len(footprint)))


def test_pivot_still_has_initial_error_and_release_drift_footprint():
    footprint = motion_footprint((0., 0.), 0., 0., position_error=.2,
                                heading_error_degrees=180., post_release_drift=.1)
    assert max(p[0] for p in footprint) >= .3
    assert check_ground_coverage(footprint, rectangle(-1, -1, 1, 1),
                                 reference=(0., 0., 0.), component=1).candidate


@pytest.mark.parametrize("changes", [dict(reach=float('inf')), dict(position_error=-1), dict(heading_error_degrees=181), dict(sides=3)])
def test_invalid_motion_bounds_do_not_create_a_footprint(changes):
    options = dict(origin=(0., 0.), heading_degrees=0., reach=1., position_error=.1,
                   heading_error_degrees=2., post_release_drift=.1)
    options.update(changes)
    with pytest.raises(ValueError): motion_footprint(**options)
