from pathlib import Path

import pytest

from eql_automation.modes import Action, ActionKind, Mode, ModeController
from eql_automation.nav import NavGraph, Point, ProgressMonitor, RouteNotFound
from eql_automation.sim import run_demo, synthetic_graph
from eql_automation.spells import SpellPlanner, SpellSpec
from eql_automation.campaign import Camp, CampaignPlanner, WorldSnapshot
from eql_automation.telemetry import ClientLogReader, RunState, StatusWriter


def test_mode_boundary_and_immediate_stop():
    controller = ModeController()
    move = Action(ActionKind.MOVE, "waypoint")
    cast = Action(ActionKind.CAST, "spell")
    assert not controller.allows(controller.permit(), cast)
    assist = controller.switch(Mode.ASSIST)
    assert controller.allows(assist, cast)
    assert not controller.allows(assist, move)
    controller.switch(Mode.OFF)
    assert assist.cancelled.is_set()
    assert not controller.allows(assist, cast)
    full = controller.switch(Mode.FULL_AUTO)
    assert controller.allows(full, move)
    assert not controller.allows(assist, cast)


def test_route_avoids_water_and_replans_around_blocked_edge(tmp_path: Path):
    graph = synthetic_graph()
    assert graph.route("start", "camp") == ["start", "safe", "camp"]
    with pytest.raises(RouteNotFound):
        graph.route("start", "camp", blocked={frozenset(("start", "safe"))})
    assert graph.route("start", "camp", avoid_water=False,
                       blocked={frozenset(("start", "safe"))}) == ["start", "water", "camp"]
    saved = graph.save("synthetic", tmp_path)
    assert NavGraph.load(saved).route("start", "camp") == ["start", "safe", "camp"]


def test_progress_monitor_flags_stall():
    monitor = ProgressMonitor(Point(10, 0), timeout=5)
    assert not monitor.observe(Point(0, 0), now=0)
    assert not monitor.observe(Point(0, 0), now=4)
    assert monitor.observe(Point(0, 0), now=5)
    assert not monitor.observe(Point(2, 0), now=6)


def test_log_tail_ignores_history_and_status_tracks_only_new_events(tmp_path: Path):
    log = tmp_path / "synthetic.log"
    log.write_text("[old] You have gained a level! Welcome to level 30!\n")
    state = RunState()
    reader = ClientLogReader(log, state)
    assert reader.poll() == []
    assert state.level is None
    with log.open("a") as stream:
        stream.write("[now] You have gained a level! Welcome to level 2!\n")
        stream.write("[now] You have been slain by a synthetic mob.\n")
    assert len(reader.poll()) == 2
    assert state.level == 2
    assert state.deaths == 1
    state.observe_xp(100, now=10)
    state.observe_xp(130, now=70)
    output = tmp_path / "STATUS.md"
    writer = StatusWriter(output)
    assert writer.maybe_write(state, now=70)
    assert "XP/hour: 1800.0" in output.read_text()
    assert not writer.maybe_write(state, now=71)


def test_demo_is_offline_and_exercises_prior_rotation():
    result = run_demo()
    assert result["simulation_only"] is True
    assert result["prior_rotation_role"] == "quick_heal"
    assert all(result[key] for key in (
        "assist_heal_allowed", "assist_move_denied",
        "off_invalidates_queued_action", "full_move_allowed"))


def test_spell_progression_orders_acquisition_from_supplied_facts():
    planner = SpellPlanner([
        SpellSpec(1, "Synthetic Heal", {"cleric": 1}),
        SpellSpec(2, "Synthetic Nuke", {"wizard": 5}),
    ])
    tasks = planner.plan(class_names={"Cleric"}, level=1, desired_slots={1: 1},
                         learned=set(), owned_scrolls=set(), vendor_stock={1},
                         memorized={})
    assert [task.operation for task in tasks] == ["buy", "scribe", "memorize"]
    assert planner.plan(class_names={"Cleric"}, level=1, desired_slots={1: 1},
                        learned={1}, owned_scrolls=set(), vendor_stock=set(),
                        memorized={1: 1}) == []
    with pytest.raises(ValueError):
        planner.plan(class_names={"Cleric"}, level=1, desired_slots={2: 2},
                     learned=set(), owned_scrolls=set(), vendor_stock={2}, memorized={})


def test_campaign_prioritizes_recovery_and_switches_poor_camp():
    planner = CampaignPlanner([
        Camp("crowded", 1, 10, 100, crowd=0.5),
        Camp("clear", 1, 10, 90),
    ])
    base = WorldSnapshot(level=5, hp=1, mana=1, bag_fullness=0,
                         camp="crowded", observed_xp_hour=20)
    assert planner.decide(base) == Action(ActionKind.CAMP, "clear")
    assert planner.decide(WorldSnapshot(level=5, hp=1, mana=1,
                                        bag_fullness=0, dead=True)).kind == ActionKind.RECOVER
    assert planner.decide(WorldSnapshot(level=5, hp=0.4, mana=1,
                                        bag_fullness=0)).kind == ActionKind.REST
