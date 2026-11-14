from dataclasses import replace
from fractions import Fraction as F

import pytest

from eql_automation.source_step_links import (
    candidate_component_path, candidate_step_path, discover_step_links, propose_step_caps,
)
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_step import check_source_step
from test_source_step import face, setup


def discover(sources, **kwargs):
    return discover_step_links(tuple(sources), inventory_sha256='a'*64,
                               max_step_height=kwargs.pop('max_step_height', .5), **kwargs)


def test_generated_caps_feed_existing_checker_without_manual_points():
    args = setup()
    sources = args[3].source_faces_for_footprint(())
    links = discover(sources)
    link = next(v for v in links if v.from_component == (1,0))
    proposal = propose_step_caps(link, radius=1.)[0]
    chain = SourceFloorChain(inventory_sha256='a'*64, seed_evidence_sha256='b'*64,
                            seed_ids=(link.from_face,), body_height=6.)
    assert chain.advance(swept_square(proposal.start,proposal.start,1.),sources).candidate
    result, landing = check_source_step(chain,proposal.start,proposal.end,args[3],args[4],
        landing_seed_ids=proposal.landing_seed_ids,radius=1.,max_step_height=.5,max_lift=1.)
    assert result.candidate and landing is not None
    assert link.discovery_only and not link.source_occupancy_checked and not link.input_authorized
    path = candidate_component_path(links, link.from_component, [link.to_component])
    assert len(path) == 1 and path[0] == link
    assert candidate_component_path(links, link.from_component, [(99,99)]) is None
    # Discovery never substitutes for a complete riser/collision check.
    missing = setup(riser=False)
    refused, _ = check_source_step(chain,proposal.start,proposal.end,missing[3],missing[4],
        landing_seed_ids=proposal.landing_seed_ids,radius=1.,max_step_height=.5,max_lift=1.)
    assert not refused.candidate


def test_affine_gap_splits_at_zero_and_bounds_exactly():
    # Boundary y=0; a flat south face and sloped north face share XY only.
    sources = (face(((0.,0.,0.),(10.,0.,0.),(0.,-10.,0.)),0),
               face(((0.,0.,-2.),(10.,0.,2.),(0.,10.,-2.)),1))
    links = [v for v in discover(sources,max_step_height=1.) if v.from_face == (1,0)]
    assert [(v.along_interval,v.height_differences) for v in links] == [
        (('5/2','5'),('-1','0')), (('5','15/2'),('0','1'))]
    # A valid clipped interval must survive an over-limit endpoint elsewhere.
    assert all(v.to_face == (1,1) for v in links)
    flat = replace(sources[1], vertices_wld=tuple((x,y,0.) for x,y,z in sources[1].vertices_wld))
    assert discover((sources[0], flat)) == ()


def test_reversed_edges_preserve_crossings_and_reverse_directions():
    args = setup();sources = args[3].source_faces_for_footprint(())
    reversed_sources = tuple(replace(s,vertices_wld=tuple(reversed(s.vertices_wld))) for s in sources)
    original = next(v for v in discover(sources) if v.from_component == (1,0))
    flipped = next(v for v in discover(reversed_sources) if v.from_component == (1,0))
    assert original.along_interval == flipped.along_interval
    assert propose_step_caps(original,radius=1.) == propose_step_caps(flipped,radius=1.)
    back = next(v for v in discover(sources) if v.from_component == original.to_component)
    forward_caps = propose_step_caps(original,radius=1.)
    backward_caps = propose_step_caps(back,radius=1.)
    assert [(c.start,c.end) for c in forward_caps] == [(c.end,c.start) for c in backward_caps]


def test_same_side_faces_are_not_step_neighbors():
    sources = (face(((0.,0.,0.),(10.,0.,0.),(0.,10.,0.)),0),
               face(((0.,0.,.25),(10.,0.,.25),(0.,10.,.25)),1))
    assert discover(sources) == ()


def test_diagonal_erodes_for_whole_expanded_square_and_rejects_narrow_span():
    sources = (face(((0.,0.,0.),(30.,40.,0.),(40.,-30.,0.)),0),
               face(((0.,0.,.25),(30.,40.,.25),(-40.,30.,.25)),1))
    link = next(v for v in discover(sources) if v.from_face == (1,0))
    proposals = propose_step_caps(link,radius=1.2)
    assert proposals
    # Each expanded corner is strictly on its declared side of the boundary.
    R = 1.202
    for proposal in proposals:
        for point,sign in ((proposal.start,-1),(proposal.end,1)):
            assert all(sign*(30*(point[1]+dy)-40*(point[0]+dx)) > 0
                       for dx in (-R,R) for dy in (-R,R))
        s = F(proposal.crossing_exact[1])
        h = (F(1.2)+F(.002))*70*40/2500
        assert 0 < s-h < s+h < 40
    narrow = replace(link,along_interval=('0','2'))
    assert propose_step_caps(narrow,radius=1.2) == ()


def test_pair_budget_fails_explicitly_instead_of_returning_incomplete_graph():
    sources = setup()[3].source_faces_for_footprint(())
    with pytest.raises(ValueError,match='pair budget'):
        discover(sources,max_pairs=1)


def test_distance_ranking_retains_goal_layers_and_rejects_long_approaches():
    sources = setup()[3].source_faces_for_footprint(())
    links = discover(sources)
    forward = next(v for v in links if v.from_component == (1,0))
    # Same target XY can belong to multiple components. Retain all; choose
    # the reachable proposal without manufacturing a vertical floor match.
    route = candidate_step_path(links,(1,0),(-2.,0.),[(1,2),(99,0)],(2.,0.),radius=1.)
    assert len(route)==1 and route[0][0]==forward
    assert candidate_step_path(links,(1,0),(-100.,0.),[(1,2)],(2.,0.),radius=1.) is None
    assert candidate_step_path(links,(1,0),(-2.,0.),[(1,0)],(-1.5,0.),radius=1.) == ()

    def shift(edge):
        return tuple((x,str(F(y)+30),z) for x,y,z in edge)
    far = replace(forward,edge_from=shift(forward.edge_from),edge_to=shift(forward.edge_to),
                  along_interval=tuple(str(F(s)+30) for s in forward.along_interval),
                  to_component=(9,9),to_face=(9,9))
    # Input order and equal link counts must not choose the remote crossing.
    ranked = candidate_step_path((far,forward),(1,0),(-2.,0.),[(9,9),(1,2)],(2.,0.),radius=1.)
    assert ranked[0][0] == forward
