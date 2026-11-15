from dataclasses import replace
from types import SimpleNamespace

import pytest

from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_itinerary import plan_source_itinerary
from eql_automation.source_transit_graph import SourceTransitGraph
from tools.source_transit_centers import filter_transit_centers
from tools.source_transit_connections import filter_transit_connections
from tools.source_transit_departures import filter_transit_departures
from test_source_itinerary import fixture
from test_source_step import face


def downstream_corridor():
    """3x2 shared-edge grid where start departure and all face centers are clear,
    while the downstream north-lane shared edge at x=6 is blocked by a static wall.
    """
    _, _, terrain, static, bsp, policy = fixture()
    xs = (-18., -6., 6., 18.)
    ys = (-14., 0., 12.)
    tris = []
    for col in range(3):
        x0, x1 = xs[col], xs[col + 1]
        for row in (1, 0):  # north row first, then south row
            y0, y1 = ys[row], ys[row + 1]
            a, b, c, d = (x0, y0, 0.), (x1, y0, 0.), (x1, y1, 0.), (x0, y1, 0.)
            tris.append((a, b, c))
            tris.append((a, c, d))
    sources = tuple(face(v, i) for i, v in enumerate(tris))
    terrain.source_faces_for_footprint = lambda _: sources
    # Block the downstream north shared edge x=6, y in [1.5, 10.5] (midpoint (6, 6)).
    # Face centers are at x in {-14, -10, -2, 2, 10, 14} (> 4 units from x=6),
    # and the start departure is at x=-6, so both center and departure filters miss it!
    wall_a = face(((6.0, 1.5, .5), (6.0, 10.5, .5), (6.0, 10.5, 8.)), 0, 7)
    wall_b = face(((6.0, 1.5, .5), (6.0, 10.5, 8.), (6.0, 1.5, 8.)), 1, 7)
    static.faces_for_footprint = lambda _: (wall_a, wall_b)
    start, goal = (-14., 4.), (14., 4.)
    prefix = SourceFloorChain(
        inventory_sha256='a' * 64,
        seed_evidence_sha256='b' * 64,
        seed_ids=((1, 1),),
        body_height=6.,
    )
    assert prefix.advance(swept_square(start, start, 1.2), sources).candidate
    graph = SourceTransitGraph(sources, inventory_sha256='a' * 64, radius=1.2)
    planner = SimpleNamespace(source=terrain, static=static, bsp=bsp, region_policy=policy)
    return prefix, start, goal, graph, planner


def test_downstream_blocked_connection_is_pruned_when_centers_and_departures_pass():
    prefix, start, goal, graph, planner = downstream_corridor()
    before = _chain_snapshot(prefix)

    # Both existing filters accept the obstructed north lane because all face centers
    # and the initial departure out of (1, 1) are clear:
    center_prop = filter_transit_centers(
        graph, prefix, start, goal, planner,
        rounds=3, start_via_edges=True, check=lambda: None, progress=lambda *_: None,
    )
    departure_prop = filter_transit_departures(
        graph, prefix, start, goal, planner, check_context=lambda: None,
    )
    for unverified in (center_prop, departure_prop):
        bad_guide = unverified.guide(static_inventory_sha256='d' * 64, radius=1.2, body_height=6.)
        with pytest.raises(ValueError, match='static'):
            plan_source_itinerary(
                prefix, start, bad_guide,
                planner.source, planner.static, planner.bsp, planner.region_policy,
                check_context=lambda: None, max_connect_distance=0, max_connect_attempts=1,
            )

    snapshots = []
    proposal = filter_transit_connections(
        graph, prefix, start, goal, planner,
        rounds=6, start_via_edges=True,
        check_context=lambda: None, progress=snapshots.append,
    )
    evidence = snapshots[-1]
    assert evidence['attempts'][-1]['candidate']
    assert evidence['excluded_count'] >= 1
    assert not evidence['physical_disconnection_proven']
    assert not evidence['input_authorized'] and not evidence['real_client_accepted']
    assert _chain_snapshot(prefix) == before

    guide = proposal.guide(static_inventory_sha256='d' * 64, radius=1.2, body_height=6.)
    checked = plan_source_itinerary(
        prefix, start, guide,
        planner.source, planner.static, planner.bsp, planner.region_policy,
        check_context=lambda: None, max_connect_distance=0, max_connect_attempts=1,
    ).record()
    assert checked['goal'] == list(goal)
    assert all(c['native']['possible_flags'] == [0] for c in checked['cells'])
    assert _chain_snapshot(prefix) == before


@pytest.mark.parametrize('reason', (
    'Source query changed',
    'Source motion terrain: floor_patch_budget_exceeded',
    'Source itinerary contains nonzero or unresolved native regions',
))
def test_non_geometric_carried_failures_are_not_connection_exclusions(monkeypatch, reason):
    import tools.source_transit_connections as module
    prefix, start, goal, graph, planner = downstream_corridor()
    planner.static.faces_for_footprint = lambda _: ()
    snapshots = []

    def refused(*args, **kwargs):
        raise ValueError(reason)

    monkeypatch.setattr(module, 'check_source_footprint', refused)
    with pytest.raises(ValueError, match=reason):
        filter_transit_connections(
            graph, prefix, start, goal, planner,
            check_context=lambda: None, progress=snapshots.append,
        )
    assert not snapshots[-1]['excluded_identities']
    assert not snapshots[-1]['attempts'][-1]['carried_refusal']['geometric_exclusion']


def test_independent_non_geometric_query_failure_refuses_immediately():
    prefix, start, goal, graph, planner = downstream_corridor()

    def broken(_):
        raise ValueError('Source inventory changed')

    planner.source.source_faces_for_footprint = broken
    with pytest.raises(ValueError, match='Source inventory changed'):
        filter_transit_connections(
            graph, prefix, start, goal, planner, check_context=lambda: None,
        )


def test_connection_budgets_and_prefix_immutability():
    prefix, start, goal, graph, planner = downstream_corridor()
    before = _chain_snapshot(prefix)
    with pytest.raises(TimeoutError, match='edge query count exhausted'):
        filter_transit_connections(
            graph, prefix, start, goal, planner,
            maximum_edge_queries=1, check_context=lambda: None,
        )
    with pytest.raises(TimeoutError, match='cell query count exhausted'):
        filter_transit_connections(
            graph, prefix, start, goal, planner,
            maximum_cell_queries=2, check_context=lambda: None,
        )
    assert _chain_snapshot(prefix) == before

    def mutate(_):
        prefix.index += 1

    with pytest.raises(ValueError, match='source prefix|No committed'):
        filter_transit_connections(
            graph, prefix, start, goal, planner,
            check_context=lambda: None, progress=mutate,
        )


def test_layer_mismatch_on_carried_replay_refuses(monkeypatch):
    prefix, start, goal, graph, planner = downstream_corridor()
    planner.static.faces_for_footprint = lambda _: ()
    original = graph.propose(prefix, start, goal, start_via_edges=True)
    changed = replace(
        original,
        edges=(replace(original.edges[0], destination=(1, 6)), *original.edges[1:]),
    )
    monkeypatch.setattr(graph, 'propose', lambda *a, **k: changed)
    snapshots = []
    before = _chain_snapshot(prefix)
    with pytest.raises(ValueError, match='actual carried source layer'):
        filter_transit_connections(
            graph, prefix, start, goal, planner,
            check_context=lambda: None, progress=snapshots.append,
        )
    assert not snapshots[-1]['excluded_identities']
    assert _chain_snapshot(prefix) == before
