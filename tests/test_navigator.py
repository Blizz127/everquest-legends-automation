from eql_automation.modes import Action, ActionKind, Mode, ModeController
from eql_automation.nav import NavGraph, Point
from eql_automation.navigator import NavigationObservation, WorldNavigator
from eql_automation.world_nav import WorldNav, ZoneTransition
from eql_automation.sim import run_navigation_demo


def _verified_moves(world: WorldNav) -> set[tuple[str, str, str]]:
    return {(zone, start, edge.target)
            for zone, graph in world.zones.items()
            for start, edges in graph.edges.items() for edge in edges}


def _alternate_world() -> WorldNav:
    graph = NavGraph()
    for name, point in {"start": Point(0, 0), "a": Point(2, 0),
                        "b": Point(0, 3), "goal": Point(4, 0)}.items():
        graph.add_point(name, point)
    for left, right in (("start", "a"), ("a", "goal"),
                        ("start", "b"), ("b", "goal")):
        graph.connect(left, right)
    world = WorldNav()
    world.add_zone("synthetic", graph)
    return world


def test_stall_at_confirmed_node_quarantines_edge_and_replans():
    world = _alternate_world()
    navigator = WorldNavigator(
        world, start_zone="synthetic", start_node="start",
        goal_zone="synthetic", goal_node="goal", level=1,
        verified_moves=_verified_moves(world), verified_zones=set(),
        stall_timeout=5, arrival_radius=0.25, min_progress=0.2)
    assert navigator.directive().kind == "WAIT_FOR_START"
    first = navigator.observe(NavigationObservation("synthetic", Point(0, 0), 0))
    assert first.kind == "MOVE_TOWARD" and first.node == "a"
    changed = navigator.observe(NavigationObservation("synthetic", Point(0, 0), 5))
    assert changed.node == "b"
    assert ("synthetic", "start", "a") in navigator.quarantined
    assert ("synthetic", "a", "start") in navigator.quarantined
    assert navigator.observe(NavigationObservation("synthetic", Point(0, 3), 6)).node == "goal"
    assert navigator.observe(NavigationObservation("synthetic", Point(4, 0), 7)).kind == "ARRIVED"


def test_mid_edge_stall_pauses_without_assuming_teleport_to_source():
    world = _alternate_world()
    navigator = WorldNavigator(
        world, start_zone="synthetic", start_node="start",
        goal_zone="synthetic", goal_node="goal", level=1,
        verified_moves=_verified_moves(world), verified_zones=set(),
        stall_timeout=5, arrival_radius=0.25, min_progress=0.2)
    navigator.observe(NavigationObservation("synthetic", Point(0, 0), 0))
    navigator.observe(NavigationObservation("synthetic", Point(1, 0), 1))
    paused = navigator.observe(NavigationObservation("synthetic", Point(1, 0), 6))
    assert paused.kind == "PAUSE"
    assert "mid-edge" in paused.reason


def test_unverified_shortcut_is_never_planned_and_assist_denies_move():
    world = _alternate_world()
    verified = {move for move in _verified_moves(world)
                if "a" not in move[1:]}
    navigator = WorldNavigator(
        world, start_zone="synthetic", start_node="start",
        goal_zone="synthetic", goal_node="goal", level=1,
        verified_moves=verified, verified_zones=set())
    assert navigator.observe(NavigationObservation("synthetic", Point(0, 0), 0)).node == "b"
    modes = ModeController()
    permit = modes.switch(Mode.ASSIST)
    assert not modes.allows(permit, Action(ActionKind.MOVE, "synthetic waypoint"))
    assert not modes.allows(permit, Action(ActionKind.ZONE, "synthetic zone line"))


def test_zone_change_requires_verified_entry_and_times_out():
    first = NavGraph()
    first.add_point("start", Point(0, 0))
    first.add_point("exit", Point(1, 0))
    first.connect("start", "exit")
    second = NavGraph()
    second.add_point("entry", Point(0, 0))
    second.add_point("goal", Point(1, 0))
    second.connect("entry", "goal")
    world = WorldNav()
    world.add_zone("one", first)
    world.add_zone("two", second)
    world.add_transition(ZoneTransition("one", "exit", "two", "entry"))
    key = ("one", "exit", "two", "entry")
    navigator = WorldNavigator(
        world, start_zone="one", start_node="start",
        goal_zone="two", goal_node="goal", level=1,
        verified_moves=_verified_moves(world), verified_zones={key},
        zone_timeout=5, arrival_radius=0.25)
    assert navigator.observe(NavigationObservation("one", Point(0, 0), 0)).kind == "MOVE_TOWARD"
    assert navigator.observe(NavigationObservation("one", Point(1, 0), 1)).kind == "WAIT_FOR_ZONE"
    assert navigator.observe(NavigationObservation("two", Point(0, 0), 2)).kind == "MOVE_TOWARD"
    assert navigator.observe(NavigationObservation("two", Point(1, 0), 3)).kind == "ARRIVED"
    blocked = WorldNavigator(
        world, start_zone="one", start_node="start",
        goal_zone="two", goal_node="goal", level=1,
        verified_moves=_verified_moves(world), verified_zones=set())
    assert blocked.directive().kind == "PAUSE"
    waiting = WorldNavigator(
        world, start_zone="one", start_node="start",
        goal_zone="two", goal_node="goal", level=1,
        verified_moves=_verified_moves(world), verified_zones={key},
        zone_timeout=5, arrival_radius=0.25)
    waiting.observe(NavigationObservation("one", Point(0, 0), 0))
    waiting.observe(NavigationObservation("one", Point(1, 0), 1))
    assert waiting.observe(NavigationObservation("one", Point(1, 0), 6)).kind == "PAUSE"


def test_start_position_must_be_observed_before_movement():
    world = _alternate_world()
    navigator = WorldNavigator(
        world, start_zone="synthetic", start_node="start",
        goal_zone="synthetic", goal_node="goal", level=1,
        verified_moves=_verified_moves(world), verified_zones=set())
    assert navigator.directive().kind == "WAIT_FOR_START"
    assert navigator.observe(NavigationObservation("synthetic", Point(3, 3), 0)).kind == "PAUSE"


def test_navigation_demo_is_synthetic_and_reaches_goal():
    result = run_navigation_demo()
    assert result == {
        "simulation_only": True, "no_game_input": True,
        "initial_waypoint": "short", "replanned_waypoint": "alternate",
        "quarantined_directed_edges": 2, "final_directive": "ARRIVED"}
