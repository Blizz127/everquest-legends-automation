from dataclasses import replace
from fractions import Fraction

from eql_automation.bsp_floor_guard import check_bsp_floor, outward_float
from eql_automation.floor_replay import FloorTrial
from eql_automation.ground_sweep import GroundCoverage
from eql_automation.portal_precision import SourceFace
from eql_automation.source_floor_chain import SourceFloorChain
from test_floor_replay import setup, trial
from test_bsp_volume import leaf, view


def context():
    data = setup(); _, accepted = trial(data)
    return data, accepted, data[1].source_faces_for_footprint(data[2])


def test_clean_volume_bound_to_same_cell_and_no_input_authority():
    data, accepted, sources = context()
    result = check_bsp_floor(accepted, data[2], sources, view((leaf(1),)))
    assert result.candidate and result.geometry_sha256 == accepted.floor_step.geometry_sha256
    assert result.floor_proof_sha256 == accepted.floor_step.proof_sha256
    assert result.floor_z_bounds == (0., 0.)
    assert result.prism_z_bounds[0] <= -.11 and result.prism_z_bounds[1] >= 8.01
    assert not result.input_authorized and not result.real_client_accepted


def test_package_xy_is_swapped_into_wld_and_refusal_preserves_prior_chain():
    data, accepted, sources = context(); before = data[0].previous
    # Fixture package X~32,Y~0 becomes WLD X~0,Y~32. Only Y>20 is labelled.
    tree = view(((0., 1., 0., -20., 0, 2, 3), leaf(1), leaf(2)), {0: {'water'}})
    result = check_bsp_floor(accepted, data[2], sources, tree)
    assert not result.candidate and result.reason == 'labelled_bsp_volume'
    assert data[0].previous is before and data[0].index == 1 and not data[0].halted


def test_below_floor_margin_is_part_of_the_hazard_volume():
    data, accepted, sources = context()
    tree = view(((0., 0., -1., -.05, 0, 2, 3), leaf(1), leaf(2)), {0: {'water'}})
    assert not check_bsp_floor(accepted, data[2], sources, tree).candidate


def test_changed_geometry_selection_or_failed_trial_cannot_reuse_a_cell():
    data, accepted, sources = context(); tree = view((leaf(1),))
    assert check_bsp_floor(accepted, tuple((x+.01, y) for x, y in data[2]), sources, tree).reason == 'terrain_cell_changed_since_floor_trial'
    changed = (replace(sources[0], flag=16), *sources[1:])
    assert check_bsp_floor(accepted, data[2], changed, tree).reason == 'terrain_cell_changed_since_floor_trial'
    altered = replace(accepted, floor_step=replace(accepted.floor_step, selected_ids=((99, 99),)))
    assert check_bsp_floor(altered, data[2], sources, tree).reason == 'terrain_selection_or_body_changed'
    assert check_bsp_floor(replace(accepted, candidate=False), data[2], sources, tree).reason == 'accepted_terrain_trial_required'


def test_sloped_floor_height_uses_clipped_local_patch_not_far_vertices():
    footprint = ((-.5, -.5), (.5, -.5), (.5, .5), (-.5, .5))
    # One very large source plane z=.5*packageX, covering the small cell.
    source = SourceFace(tuple((y, x, .5*x) for x, y in ((-100., -100.), (100., -100.), (0., 100.))),
                        0, 'Diffuse', 9, 0)
    chain = SourceFloorChain(inventory_sha256='a'*64, seed_evidence_sha256='b'*64,
                             seed_ids=((9,0),), body_height=8.)
    step = chain.advance(footprint, (source,))
    assert step.candidate
    accepted = FloorTrial(True, 'fixture', GroundCoverage(True, 'fixture'), step)
    result = check_bsp_floor(accepted, footprint, (source,), view((leaf(1),)))
    assert result.candidate and result.floor_z_bounds == (-.251, .251)
    assert result.prism_z_bounds[1] < 9


def test_report_rounding_always_encloses_exact_bounds():
    exact = Fraction(1, 3)
    assert Fraction(outward_float(exact, lower=True)) <= exact
    assert Fraction(outward_float(exact, lower=False)) >= exact
