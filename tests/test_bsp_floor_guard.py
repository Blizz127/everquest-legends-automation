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


def test_source_step_entry_keeps_full_prism_and_exact_cell_binding():
    from eql_automation.bsp_floor_guard import check_source_bsp_floor
    data,accepted,sources=context();tree=view((leaf(1),))
    direct=check_source_bsp_floor(accepted.floor_step,data[2],sources,tree)
    assert direct==check_bsp_floor(accepted,data[2],sources,tree)
    assert not direct.input_authorized
    assert not check_source_bsp_floor(replace(accepted.floor_step,candidate=False),data[2],sources,tree).candidate
    assert not check_source_bsp_floor(accepted.floor_step,tuple((x+1,y) for x,y in data[2]),sources,tree).candidate


def test_source_body_classifies_above_floor_without_waiving_terrain_margin():
    from eql_automation.bsp_floor_guard import check_source_body_bsp
    data,accepted,sources=context()
    tree=view(((0.,0.,1.,.000015,0,2,0),leaf(1)))
    assert check_bsp_floor(accepted,data[2],sources,tree).reason=='missing_bsp_child'
    direct=check_source_body_bsp(accepted.floor_step,data[2],sources,tree)
    assert direct.candidate and not direct.below_floor_bsp_classified
    assert direct.terrain_collision_margins_unchanged and not direct.input_authorized
    assert not check_source_body_bsp(replace(accepted.floor_step,candidate=False),data[2],sources,tree).candidate
    assert not check_source_body_bsp(accepted.floor_step,tuple((x+1,y) for x,y in data[2]),sources,tree).candidate


def test_source_body_rejects_water_in_upper_body():
    from eql_automation.bsp_floor_guard import check_source_body_bsp
    data,accepted,sources=context()
    tree=view(((0.,0.,1.,-7.,0,2,3),leaf(1),leaf(2)),{0:{'water'}})
    result=check_source_body_bsp(accepted.floor_step,data[2],sources,tree)
    assert not result.candidate and result.reason=='labelled_bsp_volume'


def test_source_body_follows_a_sloped_patch_with_exact_floor_contact():
    from eql_automation.bsp_floor_guard import check_source_body_bsp
    footprint=((-0.5,-0.5),(0.5,-0.5),(0.5,0.5),(-0.5,0.5))
    source=SourceFace(tuple((y,x,.5*x) for x,y in ((-100.,-100.),(100.,-100.),(0.,100.))),0,'Diffuse',9,0)
    chain=SourceFloorChain(inventory_sha256='a'*64,seed_evidence_sha256='b'*64,seed_ids=((9,0),),body_height=6.)
    step=chain.advance(footprint,(source,));assert step.candidate
    tree=view(((0.,-.5,1.,.000015,0,2,0),leaf(1)))
    result=check_source_body_bsp(step,footprint,(source,),tree)
    assert result.candidate and result.selected_ids==((9,0),)
    assert result.grounded_body_assumed and result.geometry_sha256==step.geometry_sha256
    # An actually unknown halfspace touching the floor is still visited.
    touching=view(((0.,-.5,1.,0.,0,2,0),leaf(1)))
    assert check_source_body_bsp(step,footprint,(source,),touching).reason=='missing_bsp_child'


def test_clipped_duplicate_corners_keep_exact_volume_and_boundary_contacts():
    from eql_automation.bsp_floor_guard import check_source_body_bsp
    from eql_automation.ground_sweep import area,clip,hull
    from eql_automation.source_floor_chain import rational
    from test_source_step import face
    a,b,c,d=(-10.,-10.,0.),(10.,-10.,0.),(10.,10.,0.),(-10.,10.,0.)
    sources=(face((a,b,c),0),face((a,c,d),1))
    footprint=((-1.,-1.),(1.,-1.),(1.,1.),(-1.,1.))
    prefix=SourceFloorChain(inventory_sha256='a'*64,seed_evidence_sha256='b'*64,
        seed_ids=((1,0),),body_height=6.)
    step=prefix.advance(footprint,sources);assert step.candidate
    boundary=rational(hull((x+dx,y+dy) for x,y in footprint
        for dx in (-.002,.002) for dy in (-.002,.002)))
    patch=clip(boundary,rational(tuple(p[:2] for p in (a,b,c))))
    assert len(patch)>len(hull(patch)) and area(patch)==area(hull(patch))
    result=check_source_body_bsp(step,footprint,sources,view((leaf(1),)),clip_branches=True)
    assert result.candidate and {p['vertex_count'] for p in result.pieces}=={6}
    assert result.geometry_sha256==step.geometry_sha256 and not result.input_authorized
    # The labelled halfspace touches only the closed outside boundary.
    tree=view(((1.,0.,0.,-(1.+.002),0,2,3),leaf(1),leaf(2)),{0:{'water'}})
    refused=check_source_body_bsp(step,footprint,sources,tree,clip_branches=True)
    assert not refused.candidate and refused.reason=='labelled_bsp_volume'
