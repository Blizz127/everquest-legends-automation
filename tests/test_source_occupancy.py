"""Conditional source-floor occupancy; synthetic geometry, no client input."""
from dataclasses import replace

import pytest

from eql_automation.portal_precision import SourceFace
from eql_automation.source_occupancy import check_selected_floor_clearance,clip_xyz

FOOTPRINT=((-0.5,-0.5),(0.5,-0.5),(0.5,0.5),(-0.5,0.5))


def face(points,index,material='Diffuse'):
    return SourceFace(tuple((y,x,z) for x,y,z in points),0,material,1,index)


FLOOR=(face(((-2.,-2.,0.),(2.,-2.,0.),(2.,2.,0.)),1),
       face(((-2.,-2.,0.),(2.,2.,0.),(-2.,2.,0.)),2))


def check(*extra,selected=((1,1),(1,2)),floors=FLOOR,**changes):
    options=dict(selected_ids=selected,selection_evidence_sha256='a'*64,body_height=8.)
    options.update(changes)
    return check_selected_floor_clearance(FOOTPRINT,(*floors,*extra),**options)


def horizontal(z,index=3,material='Diffuse'):
    return face(((-2.,-2.,z),(2.,-2.,z),(0.,2.,z)),index,material)


def test_high_masked_surface_and_lower_floor_are_classified_without_live_authority():
    result=check(horizontal(70.,material='TransparentMasked'),horizontal(-2.,index=4))
    assert result.candidate
    assert [f.classification for f in result.faces]==['overhead','below']
    assert not result.supporting_floor_selection_verified
    assert not result.full_collision_inventory_verified
    assert not result.real_client_accepted and not result.input_authorized


@pytest.mark.parametrize('height',(8.01,-.11,0.,4.))
def test_touching_or_inside_body_band_is_refused(height):
    assert not check(horizontal(height)).candidate


def test_clearance_values_are_explicit_hypotheses():
    assert check(horizontal(7.),body_height=6.).candidate
    assert not check(horizontal(7.),body_height=8.).candidate
    assert check(horizontal(-.12)).candidate
    assert not check(horizontal(-.12),below_clearance=.2).candidate


def test_complete_face_limit_stays_128_and_is_distinct_from_invalid_body():
    overhead=tuple(horizontal(70.,index=i) for i in range(3,130))
    assert check(*overhead[:126]).candidate  # Two floor faces plus 126 overhead.
    result=check(*overhead)
    assert not result.candidate and result.reason=='complete_source_budget_exceeded'
    assert check(*overhead,body_height=-1.).reason=='invalid_floor_selection_or_body_hypothesis'


def test_vertical_zero_xy_area_wall_is_not_discarded():
    wall=face(((0.,-2.,-1.),(0.,2.,-1.),(0.,0.,10.)),3)
    result=check(wall)
    assert result.reason=='other_source_surface_intersects_body_band'
    assert result.faces[0].minimum_above_floor<0
    assert result.faces[0].maximum_above_floor>8


def test_sloping_surface_crossing_band_is_tested_after_3d_clipping():
    ramp=face(((-2.,-2.,-20.),(2.,-2.,20.),(0.,2.,0.)),3)
    assert not check(ramp).candidate


def test_missing_anchor_duplicate_inventory_and_unsupported_selected_material_refuse():
    assert not check(selected=((1,9),)).candidate
    assert not check(selection_evidence_sha256='').candidate
    assert not check(FLOOR[0]).candidate
    assert not check(floors=(replace(FLOOR[0],material_class='Water'),FLOOR[1])).candidate


def test_selected_floor_partition_must_cover_entire_expanded_footprint():
    assert not check(selected=((1,1),)).candidate
    stepped=replace(FLOOR[1],vertices_wld=tuple((x,y,z+.2) for x,y,z in FLOOR[1].vertices_wld))
    assert not check(floors=(FLOOR[0],stepped)).candidate


def test_coplanar_unselected_duplicate_remains_ambiguous():
    assert not check(replace(FLOOR[0],face=3)).candidate


def test_clipping_retains_lines_points_and_never_accepts_an_empty_boundary():
    line=((0.,-2.,0.),(0.,2.,0.),(0.,0.,10.))
    clipped=clip_xyz(line,FOOTPRINT)
    assert clipped and all(-.5<=p[1]<=.5 for p in clipped)
    assert max(p[2] for p in clipped)==10.
    assert clip_xyz(line,())==()


def test_subtolerance_floor_gap_cannot_hide_a_body_band_intersection():
    # The floating ground area check tolerates this 2e-8-wide gap. The
    # triangle is overhead on supported ground but its tip drops into the
    # unclassified gap; exact partition coverage must refuse before labelling.
    left,right=.25,.25000002
    floors=(face(((-2.,-2.,0.),(left,-2.,0.),(left,2.,0.)),1),
            face(((-2.,-2.,0.),(left,2.,0.),(-2.,2.,0.)),2),
            face(((right,-2.,0.),(2.,-2.,0.),(2.,2.,0.)),4),
            face(((right,-2.,0.),(2.,2.,0.),(right,2.,0.)),5))
    other=face(((.249999999,-.4,9.),(.25000001,0.,0.),(.249999999,.4,9.)),3)
    result=check(other,floors=floors,selected=((1,1),(1,2),(1,4),(1,5)))
    assert not result.candidate
    assert result.reason=='selected_floor_exact_partition_failed'
