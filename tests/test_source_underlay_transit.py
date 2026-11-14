"""Retained underlay geometry must lead to a checked step, not a low tunnel."""
from types import SimpleNamespace
import pytest

from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_step_links import discover_step_links
from eql_automation.source_transit_graph import SourceTransitGraph
from eql_automation.source_itinerary import plan_source_itinerary
from tools import audit_crushbone_throne_transit as audit
from tools.source_covered_floors import covered_floor_exclusions, propose_above_covered_floors
from test_source_itinerary import fixture
from test_source_step import face, rectangle


def test_internal_edge_discovery_and_center_filter_choose_the_raised_floor(monkeypatch):
    prefix, _, terrain, static, bsp, policy = fixture()
    sources = (*terrain.source_faces_for_footprint(()), *rectangle(0., 5., 0., 10))
    terrain.source_faces_for_footprint = lambda _: sources
    links = discover_step_links(sources, inventory_sha256=terrain.wld_sha256,
        max_step_height=.5, include_internal_edges=True)
    graph = SourceTransitGraph(sources, inventory_sha256=terrain.wld_sha256,
        step_links=links, radius=1.2, max_step_height=.5, max_lift=1.)
    start, goal = (-2., 0.), (2., 0.)
    monkeypatch.setattr(audit, 'START', start)
    monkeypatch.setattr(audit, 'GOAL', goal)
    before = _chain_snapshot(prefix)
    layers = graph.components.goal(prefix, goal).goal_components
    assert set(layers) == {(1, 0), (1, 2)}
    snapshots = []
    proposal = audit.filter_centers(graph, prefix, SimpleNamespace(source=terrain, static=static),
        rounds=4, check=lambda: None,
        progress=lambda attempts, cache, count: snapshots.append((dict(cache), count)))
    cache, exclusions = snapshots[-1]
    visited_underlay = set(cache) & {(1, 10), (1, 11)}
    assert exclusions and visited_underlay
    assert all(cache[k]['excluded_center'] for k in visited_underlay)
    assert all(cache[k]['positive_height_body_blocker']['minimum_above_floor'] == .3125
               for k in visited_underlay)
    assert any(edge.step is not None for edge in proposal.edges)
    guide = proposal.guide(static_inventory_sha256=static.inventory_sha256, radius=1.2, body_height=6.)
    result = plan_source_itinerary(prefix, start, guide, terrain, static, bsp, policy,
        check_context=lambda: None).record()
    assert result['goal_floor_height'] == .3125
    assert len([c for c in result['cells'] if c['kind'] == 'step']) == 1
    assert graph.components.goal(prefix, goal).goal_components == layers
    assert _chain_snapshot(prefix) == before and not result['input_authorized']


def test_whole_triangle_filter_keeps_the_upper_layer_and_rebuilds_its_step():
    prefix, _, terrain, static, bsp, policy = fixture()
    sources = (*terrain.source_faces_for_footprint(()), *rectangle(0., 5., 0., 10))
    terrain.source_faces_for_footprint = lambda _: sources
    links = discover_step_links(sources, inventory_sha256=terrain.wld_sha256,
        max_step_height=.5, include_internal_edges=True)
    graph = SourceTransitGraph(sources, inventory_sha256=terrain.wld_sha256,
        step_links=links, radius=1.2, max_step_height=.5, max_lift=1.)
    excluded, record = covered_floor_exclusions(graph, body_height=6.)
    assert {tuple(r['lower_face']) for r in record['exclusions']} == {(1, 10), (1, 11)}
    assert {tuple(r['covering_face']) for r in record['exclusions']} == {(1, 2), (1, 3)}
    proposal = graph.propose(prefix, (-2., 0.), (2., 0.), excluded=excluded)
    assert proposal is not None
    guide = proposal.guide(static_inventory_sha256=static.inventory_sha256, radius=1.2, body_height=6.)
    result = plan_source_itinerary(prefix, (-2., 0.), guide, terrain, static, bsp, policy,
        check_context=lambda: None).record()
    assert result['goal_floor_height'] == .3125 and not result['input_authorized']


def test_whole_triangle_filter_does_not_exclude_a_floor_with_headroom():
    sources = (*rectangle(-5., 5., 0., 0), *rectangle(-5., 5., 20., 10))
    graph = SourceTransitGraph(sources, inventory_sha256='a'*64)
    excluded, record = covered_floor_exclusions(graph, body_height=6.)
    assert not excluded and not record['exclusions']


def test_opposite_diagonals_replan_onto_upper_floor_and_keep_actual_step():
    prefix, _, terrain, static, bsp, policy = fixture()
    # Lower rectangle uses the other diagonal, as in the copied client platform.
    a, b, c, d = (0., -5., 0.), (5., -5., 0.), (5., 5., 0.), (0., 5., 0.)
    sources = (*terrain.source_faces_for_footprint(()), face((a, b, d), 10), face((b, c, d), 11))
    terrain.source_faces_for_footprint = lambda _: sources
    links = discover_step_links(sources, inventory_sha256=terrain.wld_sha256,
        max_step_height=.5, include_internal_edges=True)
    graph = SourceTransitGraph(sources, inventory_sha256=terrain.wld_sha256,
        step_links=links, radius=1.2, max_step_height=.5, max_lift=1.)
    before = _chain_snapshot(prefix)
    layers = graph.components.goal(prefix, (2., 0.)).goal_faces
    evidence = []
    proposal = propose_above_covered_floors(graph, prefix, (-2., 0.), (2., 0.),
        body_height=6., progress=evidence.append)
    rejected = [r for audit in evidence[-1]['audits'] for r in audit['exclusions']]
    assert rejected and {tuple(r['lower_face']) for r in rejected} <= {(1, 10), (1, 11)}
    assert all(set(r['covering_faces']) == {(1, 2), (1, 3)} for r in rejected)
    all_faces = covered_floor_exclusions(graph, body_height=6.)[1]['exclusions']
    assert {tuple(r['lower_face']) for r in all_faces} == {(1, 10), (1, 11)}
    assert len(evidence[-1]['attempts']) >= 2
    guide = proposal.guide(static_inventory_sha256=static.inventory_sha256, radius=1.2, body_height=6.)
    result = plan_source_itinerary(prefix, (-2., 0.), guide, terrain, static, bsp, policy,
        check_context=lambda: None).record()
    assert result['goal_floor_height'] == .3125
    assert len([c for c in result['cells'] if c['kind'] == 'step']) == 1
    assert graph.components.goal(prefix, (2., 0.)).goal_faces == layers
    assert _chain_snapshot(prefix) == before and not result['input_authorized']


@pytest.mark.parametrize('height,covered', [(.11, False), (.110001, True),
    (6., True), (6.000001, False), (lambda x: 6.+.1*x, False)])
def test_height_bounds_apply_to_every_exact_patch_vertex(height, covered):
    sources = (*rectangle(-5., 5., 0., 0), *rectangle(-5., 5., height, 10))
    graph = SourceTransitGraph(sources, inventory_sha256='a'*64)
    _, record = covered_floor_exclusions(graph, body_height=6., face_ids=((1, 0), (1, 1)))
    assert bool(record['exclusions']) is covered


def test_tiny_uncovered_slit_and_overlapping_half_cannot_prove_coverage():
    lower = rectangle(-5., 5., 0., 0)
    slit = (*rectangle(-5., 0., 1., 10), *rectangle(.0000001, 5., 1., 20))
    graph = SourceTransitGraph((*lower, *slit), inventory_sha256='a'*64)
    assert not covered_floor_exclusions(graph, body_height=6.)[1]['exclusions']
    lower = face(((0., 0., 0.), (2., 0., 0.), (0., 2., 0.)), 0)
    half = ((0., 0., 1.), (2., 0., 1.), (0., 1., 1.))
    graph = SourceTransitGraph((lower, face(half, 10), face(half, 11)), inventory_sha256='a'*64)
    assert not covered_floor_exclusions(graph, body_height=6.)[1]['exclusions']


def test_pair_budget_exhaustion_returns_no_partial_exclusions():
    sources = (*rectangle(-5., 5., 0., 0), *rectangle(-5., 5., 1., 10))
    graph = SourceTransitGraph(sources, inventory_sha256='a'*64)
    with pytest.raises(ValueError, match='pair budget exceeded; no exclusions returned'):
        covered_floor_exclusions(graph, body_height=6., maximum_pairs=1)
