"""Offline shortcuts preserve steps, source layers and full validation."""
from dataclasses import replace

import pytest

from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_detour import swept_square
from eql_automation.source_itinerary import SourceWalkHint, SourceStepHint, plan_source_itinerary
from tools.source_walk_shortcuts import shortcut_walks
from test_source_itinerary import fixture
from test_source_step import rectangle, face


def test_shortcuts_keep_every_step_and_rebuild_from_the_original_prefix():
    prefix, guide, terrain, static, bsp, policy = fixture()
    before = _chain_snapshot(prefix)
    shortened, evidence = shortcut_walks(prefix, guide, terrain, static, check_context=lambda: None)
    assert len(shortened.operations) < len(guide.operations)
    assert tuple(o for o in shortened.operations if type(o) is SourceStepHint) == tuple(
        o for o in guide.operations if type(o) is SourceStepHint)
    result = plan_source_itinerary(prefix, (-2., 0.), shortened, terrain, static, bsp,
        policy, check_context=lambda: None).record()
    assert result['goal_floor_height'] == 0 and result['goal'] == [-2.5, 0.]
    assert len([c for c in result['cells'] if c['kind'] == 'step']) == 2
    assert _chain_snapshot(prefix) == before and not evidence['input_authorized']


def test_static_wall_cannot_be_shortcut_and_no_partial_branch_is_committed():
    _, guide, terrain, static, _, _ = fixture()
    sources = rectangle(-5., 5., 0., 0)
    terrain.source_faces_for_footprint = lambda _: sources
    static.faces_for_footprint = lambda _: (face(((0., -20., -1.), (0., 20., -1.), (0., 0., 20.)), 0, 7),)
    prefix = SourceFloorChain(inventory_sha256='a'*64, seed_evidence_sha256='b'*64,
        seed_ids=((1, 1),), body_height=6.)
    assert prefix.advance(swept_square((-2., 0.), (-2., 0.), .25), sources).candidate
    guide = replace(guide, radius=.25, goal=(2., 0.),
                    operations=(SourceWalkHint((-2., 0.), (2., 0.)),))
    before = _chain_snapshot(prefix)
    with pytest.raises(ValueError, match='No checked walking'):
        shortcut_walks(prefix, guide, terrain, static, check_context=lambda: None)
    assert _chain_snapshot(prefix) == before


def test_claimed_start_must_be_inside_the_supplied_floor_footprint():
    prefix, guide, terrain, static, _, _ = fixture()
    guide = replace(guide, operations=(SourceWalkHint((-4.5, 0.), (-1.5, 0.)),
                                     *guide.operations[1:]))
    before = _chain_snapshot(prefix)
    with pytest.raises(ValueError):
        shortcut_walks(prefix, guide, terrain, static, check_context=lambda: None)
    assert _chain_snapshot(prefix) == before


def test_shortcut_keeps_upstairs_floor_over_a_coincident_downstairs_path():
    _, guide, terrain, static, bsp, policy = fixture()
    sources = (*rectangle(-5., 5., 0., 0), *rectangle(-5., 5., 20., 10))
    terrain.source_faces_for_footprint = lambda _: sources
    prefix = SourceFloorChain(inventory_sha256='a'*64, seed_evidence_sha256='b'*64,
        seed_ids=((1, 11),), body_height=6.)
    assert prefix.advance(swept_square((-2., 0.), (-2., 0.), .25), sources).candidate
    guide = replace(guide, radius=.25, goal=(2., 0.), operations=(
        SourceWalkHint((-2., 0.), (-1., 1.)), SourceWalkHint((-1., 1.), (2., 0.))))
    before = _chain_snapshot(prefix)
    short, _ = shortcut_walks(prefix, guide, terrain, static, check_context=lambda: None)
    result = plan_source_itinerary(prefix, (-2., 0.), short, terrain, static, bsp,
        policy, check_context=lambda: None).record()
    assert result['goal_floor_height'] == 20 and _chain_snapshot(prefix) == before


@pytest.mark.parametrize('kind', ['cancel', 'query_budget'])
def test_shortcut_context_and_budget_failures_never_publish_a_partial_guide(kind):
    prefix, guide, terrain, static, _, _ = fixture()
    before = _chain_snapshot(prefix)
    def check():
        if kind == 'cancel':
            raise ValueError('owner fixture cancelled')
    with pytest.raises((ValueError, TimeoutError), match='cancelled|budget'):
        shortcut_walks(prefix, guide, terrain, static, check_context=check,
                       maximum_queries=1 if kind == 'query_budget' else 1000)
    assert _chain_snapshot(prefix) == before
