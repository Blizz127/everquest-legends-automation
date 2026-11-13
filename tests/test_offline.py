from pathlib import Path
from math import nan

import pytest

from eql_automation.modes import Action, ActionKind, Mode, ModeController, action_from_prior_rotation
from eql_automation.nav import NavGraph, Point, ProgressMonitor, RouteNotFound
from eql_automation.navigator import NavigationObservation
from eql_automation.sim import run_demo, synthetic_graph
from eql_automation.spells import SpellPlanner, SpellSpec
from eql_automation.campaign import Camp, CampaignPlanner, WorldSnapshot
from eql_automation.telemetry import ClientLogReader, RunState, StatusWriter, render_status
from eql_automation.world_nav import WorldNav, ZoneTransition
from eql_automation.synthetic_run import SyntheticEnvironment, run_synthetic_1_50


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


def test_invalid_mode_preserves_current_permit_and_spoofed_command_is_denied():
    controller = ModeController()
    assist = controller.switch(Mode.ASSIST)
    with pytest.raises(ValueError):
        controller.switch("bad-mode")
    assert controller.allows(assist, Action(ActionKind.CAST, "/cast 1"))
    assert not controller.allows(assist, Action(ActionKind.CAST, "/target arbitrary"))
    assert not controller.allows(assist, Action(ActionKind.CAST, "/attack on"))
    with pytest.raises(ValueError):
        action_from_prior_rotation("nuke", "/cast 1; /target arbitrary")


def test_route_avoids_water_and_replans_around_blocked_edge(tmp_path: Path):
    graph = synthetic_graph()
    assert graph.route("start", "camp") == ["start", "safe", "camp"]
    with pytest.raises(RouteNotFound):
        graph.route("start", "camp", blocked={frozenset(("start", "safe"))})
    assert graph.route("start", "camp", avoid_water=False,
                       blocked={frozenset(("start", "safe"))}) == ["start", "water", "camp"]
    saved = graph.save("synthetic", tmp_path)
    assert NavGraph.load(saved).route("start", "camp") == ["start", "safe", "camp"]


def test_navigation_rejects_duplicate_or_nonfinite_geometry():
    graph = NavGraph()
    graph.add_point("start", Point(0, 0))
    with pytest.raises(ValueError, match="already exists"):
        graph.add_point("start", Point(100, 0))
    with pytest.raises(ValueError, match="finite"):
        graph.add_point("bad", Point(nan, 0))
    graph.add_point("end", Point(1, 0))
    with pytest.raises(ValueError, match="Invalid edge"):
        graph.connect("start", "end", aggro=nan)
    graph.connect("start", "end")
    with pytest.raises(ValueError, match="Risk constraints"):
        graph.route("start", "end", risk_weight=nan)


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
    reader = ClientLogReader(log, state, fresh_test_character=True)
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


def test_log_created_after_reader_start_keeps_first_event(tmp_path: Path):
    log = tmp_path / "new.log"
    state = RunState()
    reader = ClientLogReader(log, state, fresh_test_character=True)
    log.write_text("[now] You have gained a level! Welcome to level 2!\n")
    assert len(reader.poll()) == 1
    assert state.level == 2


def test_new_log_without_fresh_character_opt_in_skips_first_bytes(tmp_path: Path):
    log = tmp_path / "new.log"
    state = RunState()
    reader = ClientLogReader(log, state)
    log.write_text("[old] You have gained a level! Welcome to level 30!\n")
    assert reader.poll() == []
    assert state.level is None
    with log.open("a") as stream:
        stream.write("[now] You have gained a level! Welcome to level 2!\n")
    assert len(reader.poll()) == 1 and state.level == 2


def test_replaced_log_skips_history_and_invalidates_run_metrics(tmp_path: Path):
    log = tmp_path / "synthetic.log"
    log.write_text("")
    state = RunState()
    reader = ClientLogReader(log, state)
    with log.open("a") as stream:
        stream.write("[now] You have gained a level! Welcome to level 2!\n")
        stream.write("[now] You have been slain by a synthetic mob.\n")
    assert len(reader.poll()) == 2
    state.camp = "synthetic camp"
    state.observe_xp(100, now=10)
    replacement = tmp_path / "replacement.log"
    replacement.write_text("[old] You have gained a level! Welcome to level 40!\n"
                           "[old] You have been slain by an old mob.\n")
    replacement.replace(log)
    assert reader.poll() == []
    assert (state.level, state.xp, state.deaths, state.camp, state.zone) == (
        None, None, None, None, None)
    assert "Deaths: n/a" in render_status(state)
    with log.open("a") as stream:
        stream.write("[new] You have gained a level! Welcome to level 3!\n")
    assert len(reader.poll()) == 1 and state.level == 3
    assert state.deaths is None  # Run continuity still needs independent proof.


def test_truncate_and_partial_log_cannot_replay_old_events(tmp_path: Path):
    log = tmp_path / "synthetic.log"
    log.write_text("")
    state = RunState()
    reader = ClientLogReader(log, state)
    with log.open("a") as stream:
        stream.write("[now] You have gained a level! Welcome to level 2!\n")
    reader.poll()
    with log.open("a") as stream:
        stream.write("[partial] You have been slain")
    assert reader.poll() == []
    log.write_text("[old] You have been slain by a prior mob.\n")
    assert reader.poll() == []
    assert state.level is None and state.deaths is None


def test_excessive_log_backlog_is_skipped_and_state_invalidated(tmp_path: Path):
    log = tmp_path / "synthetic.log"
    log.write_text("")
    state = RunState()
    reader = ClientLogReader(log, state)
    with log.open("a") as stream:
        stream.write("[now] You have gained a level! Welcome to level 2!\n")
    reader.poll()
    with log.open("a") as stream:
        stream.write("[old] You have been slain by a prior mob.\n" * 14000)
    assert reader.poll() == []
    assert state.level is None and state.deaths is None


def test_raw_xp_rate_discards_nonmonotonic_sample_times():
    state = RunState()
    state.observe_xp(100, now=10)
    state.observe_xp(130, now=70)
    assert state.xp_per_hour == 1800
    state.observe_xp(140, now=20)
    assert state.xp == 140 and state.xp_per_hour is None
    with pytest.raises(ValueError, match="sample time"):
        state.observe_xp(150, now=float("nan"))


def test_current_level_progress_is_not_raw_xp_and_resets_on_level_or_drop():
    state = RunState(level=5)
    assert state.observe_level_progress(level=5, fraction=0.20,
                                        normal_xp_allocation_verified=True, now=0)
    assert state.observe_level_progress(level=5, fraction=0.35,
                                        normal_xp_allocation_verified=True, now=1800)
    assert state.level_progress_percent_per_hour == pytest.approx(30.0)
    assert state.xp is None and state.xp_per_hour is None
    with pytest.raises(ValueError, match="Cumulative raw XP"):
        state.observe_xp(0.35, now=1800)
    assert "Current-level progress/hour: 30.0 percentage points/hour" in render_status(state)
    assert state.observe_level_progress(level=5, fraction=0.10,
                                        normal_xp_allocation_verified=True, now=1900)
    assert state.level_progress_percent_per_hour is None
    state.observe_log("[now] You have gained a level! Welcome to level 6!")
    assert state.level == 6 and state.level_progress_fraction is None
    assert not state.observe_level_progress(level=5, fraction=0.5,
                                            normal_xp_allocation_verified=True, now=2000)
    assert not state.observe_level_progress(level=6, fraction=0.5,
                                            normal_xp_allocation_verified=False, now=2100)
    assert state.observe_level_progress(level=6, fraction=0.4,
                                        normal_xp_allocation_verified=True, now=2200)
    state.level = 7  # A different trusted level adapter may update directly.
    assert state.level_progress_percent_per_hour is None
    assert "Current-level XP progress: n/a" in render_status(state)


def test_demo_is_offline_and_exercises_prior_rotation():
    result = run_demo()
    assert result["simulation_only"] is True
    assert result["prior_rotation_role"] == "quick_heal"
    assert all(result[key] for key in (
        "assist_heal_allowed", "assist_move_denied",
        "off_invalidates_queued_action", "full_move_allowed",
        "unknown_health_stops_full_mode"))
    assert "zone" in result["zone_route_kinds"]


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
                         camp="crowded", observed_xp_hour=20,
                         verified_reachable_camps=frozenset({"crowded", "clear"}))
    assert planner.decide(base) == Action(ActionKind.CAMP, "clear")
    assert planner.decide(WorldSnapshot(level=5, hp=1, mana=1,
                                        bag_fullness=0, dead=True)).kind == ActionKind.RECOVER
    assert planner.decide(WorldSnapshot(level=5, hp=0.4, mana=1,
                                        bag_fullness=0)).kind == ActionKind.REST
    leveled = CampaignPlanner([Camp("old", 1, 5, 100), Camp("new", 6, 10, 80)])
    assert leveled.decide(WorldSnapshot(level=6, hp=1, mana=1, bag_fullness=0,
                                        camp="old", verified_reachable_camps=frozenset({"new"}))) == Action(ActionKind.CAMP, "new")


def test_campaign_filters_unreachable_camps_and_pauses_without_route_evidence():
    planner = CampaignPlanner([Camp("high", 1, 10, 100), Camp("reachable", 1, 10, 40)])
    base = WorldSnapshot(level=7, hp=1, mana=1, bag_fullness=0,
                         camp="high", verified_reachable_camps=frozenset({"reachable"}))
    assert planner.select_camp(base).name == "reachable"
    assert planner.decide(base) == Action(ActionKind.CAMP, "reachable")
    assert planner.decide(WorldSnapshot(level=7, hp=1, mana=1, bag_fullness=0,
                                        verified_reachable_camps=frozenset())).kind == ActionKind.PAUSE
    assert planner.decide(WorldSnapshot(level=7, hp=1, mana=1,
                                        bag_fullness=0)).kind == ActionKind.PAUSE


def test_campaign_pauses_on_unknown_or_unsafe_state_and_loots_only_when_safe():
    planner = CampaignPlanner([Camp("synthetic", 1, 10, 100)])
    base = dict(level=5, hp=1.0, mana=1.0, bag_fullness=0.0,
                camp="synthetic", target_present=True)
    assert planner.decide(WorldSnapshot(**{**base, "hp": None})).kind == ActionKind.PAUSE
    assert planner.decide(WorldSnapshot(**{**base, "gm_present": True})).kind == ActionKind.PAUSE
    assert planner.decide(WorldSnapshot(**{**base, "under_attack": True,
                                          "target_present": False})).kind == ActionKind.PAUSE
    assert planner.decide(WorldSnapshot(**{**base, "loot_available": True})).kind == ActionKind.LOOT
    assert planner.decide(WorldSnapshot(**{**base, "loot_available": True,
                                          "under_attack": True})) is None
    assert planner.decide(WorldSnapshot(**{**base, "bag_fullness": 1.0,
                                          "under_attack": True})) is None
    assert planner.decide(WorldSnapshot(**{**base, "dead": True,
                                          "disconnected": True})).kind == ActionKind.LOGIN


def test_world_route_crosses_verified_zone_line_and_replans():
    start = NavGraph()
    for name, x in (("spawn", 0), ("exit", 10), ("water", 5)):
        start.add_point(name, Point(x, 0))
    start.connect("spawn", "exit")
    start.connect("spawn", "water", water=True)
    start.connect("water", "exit", water=True)
    destination = NavGraph()
    destination.add_point("entry", Point(0, 0))
    destination.add_point("camp", Point(4, 0))
    destination.connect("entry", "camp")
    world = WorldNav()
    world.add_zone("one", start)
    world.add_zone("two", destination)
    world.add_transition(ZoneTransition("one", "exit", "two", "entry", min_level=2))
    with pytest.raises(RouteNotFound):
        world.route("one", "spawn", "two", "camp", level=1)
    route = world.route("one", "spawn", "two", "camp", level=2)
    assert [step.kind for step in route] == ["move", "zone", "move"]
    with pytest.raises(RouteNotFound):
        world.route("one", "spawn", "two", "camp", level=2,
                    blocked_edges={("one", "spawn", "exit")})
    alternate = world.route("one", "spawn", "two", "camp", level=2,
                            avoid_water=False, blocked_edges={("one", "spawn", "exit")})
    assert [step.to_node for step in alternate[:2]] == ["water", "exit"]
    world.transitions.clear()
    world.add_transition(ZoneTransition("one", "exit", "two", "entry", risk=1))
    with pytest.raises(RouteNotFound):
        world.route("one", "spawn", "two", "camp", level=2)
    assert any(step.kind == "zone" for step in world.route(
        "one", "spawn", "two", "camp", level=2, max_aggro=1))


def test_closed_loop_synthetic_level_50_exercises_required_planners(tmp_path: Path):
    result = run_synthetic_1_50(tmp_path)
    assert result["simulation_only"] is True
    assert result["real_client_level_verified"] is False
    assert result["synthetic_level_reached"] == 50
    assert result["counts"]["recover"] == 1
    assert result["counts"]["login"] == 1
    assert result["counts"]["zone"] >= 4
    assert result["counts"]["spell_memorize"] == 5
    assert result["assist_denied_nonrotation"] is True
    assert result["assist_cast_allowed"] is True
    assert result["off_cancels_assist"] is True
    assert "simulation_only" in (tmp_path / "trace-synthetic.jsonl").read_text()
    assert "Synthetic simulation only" in (tmp_path / "STATUS-synthetic.md").read_text()


def test_synthetic_gm_pause_latches_off():
    env = SyntheticEnvironment()
    unsafe = WorldSnapshot(level=1, hp=1, mana=1, bag_fullness=0,
                           gm_present=True)
    decision = env.campaign.decide(unsafe)
    assert decision is not None and decision.kind == ActionKind.PAUSE
    with pytest.raises(RuntimeError, match="latched OFF"):
        env.apply_intent(1, decision)
    assert env.controller.mode == Mode.OFF
    assert not env.sink.submit(Action(ActionKind.CAST, "/cast 3"))


def test_synthetic_camp_waits_for_observed_waypoint_and_zone_arrival():
    env = SyntheticEnvironment()
    env.observe_route_arrival = lambda _directive, now: NavigationObservation(
        "synthetic_zone_1", Point(0, 0), now)
    with pytest.raises(RuntimeError, match="navigation paused"):
        env.move_to_camp(1, "synthetic_camp_1")
    assert env.camp is None and (env.zone, env.node) == ("synthetic_zone_1", "entry")
    assert env.controller.mode == Mode.OFF

    env = SyntheticEnvironment()
    env.zone, env.node, env.level = "synthetic_zone_1", "camp", 11
    def wrong_zone_entry(directive, now):
        if directive.kind == "WAIT_FOR_ZONE":
            return NavigationObservation("synthetic_zone_2", Point(999, 999), now)
        return NavigationObservation(directive.zone, directive.point, now)
    env.observe_route_arrival = wrong_zone_entry
    with pytest.raises(RuntimeError, match="navigation paused"):
        env.move_to_camp(1, "synthetic_camp_2")
    assert env.camp is None and (env.zone, env.node) == ("synthetic_zone_1", "camp")
    assert env.controller.mode == Mode.OFF


def test_synthetic_camp_requires_start_adapter_observation():
    env = SyntheticEnvironment()
    env.observe_route_start = lambda zone, point, now: NavigationObservation(
        zone, Point(999, 999), now)
    with pytest.raises(RuntimeError, match="navigation paused"):
        env.move_to_camp(1, "synthetic_camp_1")
    assert env.camp is None and env.counts["move"] == 0
    assert env.controller.mode == Mode.OFF

    env = SyntheticEnvironment()
    env.observe_route_start = lambda zone, point, now: NavigationObservation(
        zone, point, now - 0.01)
    with pytest.raises(RuntimeError, match="missing or stale"):
        env.move_to_camp(1, "synthetic_camp_1")
    assert env.camp is None and env.counts["move"] == 0
    assert env.controller.mode == Mode.OFF


def test_synthetic_zone_transition_issues_once_while_waiting():
    env = SyntheticEnvironment()
    env.zone, env.node, env.level = "synthetic_zone_1", "camp", 11
    observed_times = []
    original_plan = env.dispatcher.plan
    def tracked_plan(action, observation, now):
        observed_times.append(now)
        return original_plan(action, observation, now)
    env.dispatcher.plan = tracked_plan
    polls = 0
    def delayed_zone(directive, now):
        nonlocal polls
        observed_times.append(now)
        if directive.kind == "WAIT_FOR_ZONE" and polls < 3:
            polls += 1
            return NavigationObservation("synthetic_zone_1", Point(10, 0), now)
        return NavigationObservation(directive.zone, directive.point, now)
    env.observe_route_arrival = delayed_zone
    env.move_to_camp(1, "synthetic_camp_2")
    assert env.camp == "synthetic_camp_2"
    assert env.counts["zone"] == 1
    assert observed_times == sorted(observed_times)


def test_synthetic_navigation_callback_failure_latches_off():
    env = SyntheticEnvironment()
    def lost_sensor(_directive, _now):
        raise RuntimeError("sensor lost")
    env.observe_route_arrival = lost_sensor
    with pytest.raises(RuntimeError, match="sensor lost"):
        env.move_to_camp(1, "synthetic_camp_1")
    assert env.camp is None and env.controller.mode == Mode.OFF


def test_synthetic_navigation_rejects_stale_arrival_observation():
    env = SyntheticEnvironment()
    env.observe_route_arrival = lambda directive, now: NavigationObservation(
        directive.zone, directive.point, now - 0.01)
    with pytest.raises(RuntimeError, match="missing or stale"):
        env.move_to_camp(1, "synthetic_camp_1")
    assert env.camp is None and env.controller.mode == Mode.OFF
