from dataclasses import replace
from types import SimpleNamespace

import pytest

from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_detour import swept_square
from eql_automation.source_itinerary import SourceWalkHint, plan_source_itinerary
from tools.source_walk_repairs import repair_walks
from test_source_itinerary import fixture
from test_source_step import rectangle, face


def context():
    _, guide, terrain, static, bsp, policy = fixture()
    sources = rectangle(-5., 5., 0., 0)
    terrain.source_faces_for_footprint = lambda _: sources
    static.faces_for_footprint = lambda _: (face(((0., -.5, -1.), (0., .5, -1.), (0., 0., 8.)), 0, 7),)
    prefix = SourceFloorChain(inventory_sha256='a'*64, seed_evidence_sha256='b'*64,
        seed_ids=((1, 1),), body_height=6.)
    assert prefix.advance(swept_square((-2., 0.), (-2., 0.), .25), sources).candidate
    guide = replace(guide, zone='butcher', radius=.25, goal=(2., 0.),
        operations=(SourceWalkHint((-2., 0.), (2., 0.)),))
    planner = SimpleNamespace(source=terrain, static=static, bsp=bsp, region_policy=replace(policy, zone='butcher'))
    return prefix, guide, planner


def test_automatic_static_detour_rebuilds_through_the_original_floor():
    prefix, guide, p = context(); before = _chain_snapshot(prefix)
    repaired, evidence = repair_walks(prefix, guide, p, check_context=lambda: None)
    assert len(repaired.operations) > 1 and evidence['repairs'][0]['adopted']
    result = plan_source_itinerary(prefix, (-2., 0.), repaired, p.source, p.static,
        p.bsp, p.region_policy, check_context=lambda: None).record()
    assert result['goal'] == [2., 0.] and result['zone'] == 'butcher'
    assert all(c['native']['possible_flags'] == [0] for c in result['cells'])
    assert _chain_snapshot(prefix) == before and not evidence['input_authorized']


def test_terrain_static_detour_cannot_bypass_region_refusal(monkeypatch):
    import tools.source_walk_repairs as module
    prefix, guide, p = context(); before = _chain_snapshot(prefix); seen = []
    original = module.check_source_footprint
    def region_check(prefix, footprint, **kwargs):
        result = original(prefix, footprint, **kwargs)
        if max(abs(y) for _, y in footprint) > 1.:
            raise ValueError('Source itinerary contains nonzero or unresolved native regions')
        return result
    monkeypatch.setattr(module, 'check_source_footprint', region_check)
    with pytest.raises(ValueError, match='native regions'):
        repair_walks(prefix, guide, p, check_context=lambda: None, progress=seen.append)
    assert seen[-1]['repairs'][0]['detour']['candidate']
    assert not seen[-1]['repairs'][0]['adopted'] and seen[-1]['completed_operations'] == 0
    assert _chain_snapshot(prefix) == before


def test_context_failure_never_becomes_an_obstacle_to_route_around(monkeypatch):
    import tools.source_walk_repairs as module
    prefix, guide, p = context(); before = _chain_snapshot(prefix)
    def forbidden(*a, **k): raise AssertionError('Must not search after context loss')
    monkeypatch.setattr(module, 'find_source_detour', forbidden)
    def lost(): raise ValueError('Owner source binding changed')
    with pytest.raises(ValueError, match='binding changed'):
        repair_walks(prefix, guide, p, check_context=lost)
    assert _chain_snapshot(prefix) == before


@pytest.mark.parametrize('reason', (
    'Source motion terrain: floor_patch_budget_exceeded',
    'Source motion terrain: source_identity_changed',
    'Source motion static: static_query_refused',
    'Source motion static: terrain_cell_changed_since_floor_trial',
))
def test_inventory_and_budget_failures_do_not_trigger_repairs(monkeypatch, reason):
    import tools.source_walk_repairs as module
    prefix, guide, p = context(); before = _chain_snapshot(prefix)
    def forbidden(*a, **k): raise AssertionError('Must not route around integrity/query failures')
    def refused(*a, **k): raise ValueError(reason)
    monkeypatch.setattr(module, 'find_source_detour', forbidden)
    monkeypatch.setattr(module, 'check_source_footprint', refused)
    with pytest.raises(ValueError, match=reason):
        repair_walks(prefix, guide, p, check_context=lambda: None)
    assert _chain_snapshot(prefix) == before
