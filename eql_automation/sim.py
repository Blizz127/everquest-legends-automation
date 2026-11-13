"""Synthetic, offline exercises for the mode and planning contracts."""
from __future__ import annotations

from dataclasses import dataclass, field

from .modes import Action, ActionKind, Mode, ModeController, action_from_prior_rotation
from .nav import NavGraph, Point
from .prior_rotation_core import Rotation, Spell
from .world_nav import WorldNav, ZoneTransition
from .campaign import Camp, CampaignPlanner, WorldSnapshot
from .navigator import NavigationObservation, WorldNavigator
from .assist import AssistAdvisor, AssistObservation
from .control import ControlPlane
from .prior_rotation_core import Catalog
from .screen_observer import GaugeCalibration, GaugeReader


@dataclass
class SimSink:
    controller: ModeController
    accepted: list[Action] = field(default_factory=list)
    rejected: list[Action] = field(default_factory=list)

    def submit(self, action: Action, permit=None) -> bool:
        permit = self.controller.permit() if permit is None else permit
        if self.controller.allows(permit, action):
            self.accepted.append(action)
            return True
        self.rejected.append(action)
        return False


def synthetic_graph() -> NavGraph:
    graph = NavGraph()
    graph.add_point("start", Point(0, 0))
    graph.add_point("safe", Point(0, 10))
    graph.add_point("camp", Point(10, 10))
    graph.add_point("water", Point(5, 0))
    graph.connect("start", "safe")
    graph.connect("safe", "camp")
    graph.connect("start", "water", water=True)
    graph.connect("water", "camp", water=True)
    return graph


def synthetic_world() -> WorldNav:
    first = synthetic_graph()
    second = NavGraph()
    second.add_point("entry", Point(0, 0))
    second.add_point("next_camp", Point(5, 0))
    second.connect("entry", "next_camp")
    world = WorldNav()
    world.add_zone("synthetic_one", first)
    world.add_zone("synthetic_two", second)
    world.add_transition(ZoneTransition("synthetic_one", "camp",
                                        "synthetic_two", "entry"))
    return world


def run_demo() -> dict:
    controller = ModeController()
    sink = SimSink(controller)
    prior_spell = Spell(200, "Synthetic Heal", 1, 1, 1500, 500, 0, 10, 0, 0)
    rotation = Rotation({"quick_heal": prior_spell}, level=1)
    choice = rotation.choose(now=10.0, hp=0.5, mana=1.0)
    if choice is None:
        raise AssertionError("Prior rotation supplied no synthetic heal")
    heal = action_from_prior_rotation(choice.role, choice.command)
    move = Action(ActionKind.MOVE, "synthetic waypoint")
    assist_permit = controller.switch(Mode.ASSIST)
    assist_heal = sink.submit(heal, assist_permit)
    assist_move = sink.submit(move, assist_permit)
    controller.switch(Mode.OFF)
    off_rejects_old_permit = not sink.submit(heal, assist_permit)
    full_permit = controller.switch(Mode.FULL_AUTO)
    full_route = synthetic_graph().route("start", "camp")
    zone_route = synthetic_world().route("synthetic_one", "start",
                                         "synthetic_two", "next_camp", level=1)
    full_move = sink.submit(move, full_permit)
    planner = CampaignPlanner([Camp("synthetic_camp", 1, 10, 100)])
    pause = planner.decide(WorldSnapshot(level=1, hp=None, mana=1,
                                        bag_fullness=0))
    if pause is None or pause.kind != ActionKind.PAUSE:
        raise AssertionError("Unknown health did not pause the campaign")
    controller.switch(Mode.OFF)
    return {
        "simulation_only": True,
        "prior_rotation_role": choice.role,
        "assist_heal_allowed": assist_heal,
        "assist_move_denied": not assist_move,
        "off_invalidates_queued_action": off_rejects_old_permit,
        "full_move_allowed": full_move,
        "safe_route": full_route,
        "zone_route_kinds": [step.kind for step in zone_route],
        "unknown_health_stops_full_mode": controller.mode == Mode.OFF,
    }


def run_assist_demo() -> dict:
    """Show strict current-target rotation gating without sending any input."""

    catalog = Catalog([
        Spell(14, "Strike", 1, 1, 1000, 500, 0, 10, 0, 0),
        Spell(200, "Minor Healing", 1, 1, 1500, 500, 0, 10, 0, 0),
        Spell(210, "Yaulp", 1, 9, 1000, 500, 0, 1, 0, 0),
    ])
    control = ControlPlane()
    advisor = AssistAdvisor(catalog, character_name="SyntheticTester",
                            class_name="Paladin", level=1,
                            known_spells={14, 200, 210}, control=control)
    observation = AssistObservation(
        observed_at=10.0, character_name="SyntheticTester",
        class_name="Paladin", level=1, game_focused=True, chat_open=False,
        current_target_verified=True, hp=1.0, mana=1.0,
        memorized={1: 200, 3: 14})
    control.handle_command("mode assist")
    proposal = advisor.propose(observation, now=10.0)
    if proposal is None:
        raise AssertionError("Synthetic assist supplied no action")
    allowed_before_stop = advisor.still_allowed(proposal, observation, now=10.0)
    control.handle_command("stop")
    return {"simulation_only": True, "no_game_input": True,
            "mode_after_stop": control.indicator.mode.value,
            "proposed_action": proposal.queued.action.detail,
            "paladin_level_1_yaulp_excluded": "yaulp" not in advisor.rotation.profile,
            "allowed_before_stop": allowed_before_stop,
            "old_proposal_allowed_after_stop": advisor.still_allowed(
                proposal, observation, now=10.0)}


def run_gauge_demo() -> dict:
    """Read fabricated colored bars, never a game-window screenshot."""

    from PIL import Image

    full = Image.new("RGB", (120, 30), (20, 20, 20))
    full.paste((200, 20, 20), (0, 0, 100, 8))
    full.paste((20, 20, 200), (0, 12, 100, 20))
    calibration = GaugeCalibration.from_full_frame(
        full, hp_box=(0, 0, 100, 8), mana_box=(0, 12, 100, 20),
        layout_fingerprint="synthetic-layout")
    reader = GaugeReader(calibration)
    half = full.copy()
    half.paste((20, 20, 20), (50, 0, 100, 8))
    reading = reader.read(half, observed_at=10.0,
                          focused_game_window=True,
                          layout_fingerprint="synthetic-layout")
    unfocused = reader.read(half, observed_at=10.1,
                            focused_game_window=False,
                            layout_fingerprint="synthetic-layout")
    return {"simulation_only": True, "no_game_input": True,
            "hp": reading.hp, "mana": reading.mana,
            "unfocused_values_unknown": not unfocused.complete}


def run_navigation_demo() -> dict:
    """Show a stalled synthetic edge being quarantined and replanned."""

    graph = NavGraph()
    for name, point in {"start": Point(0, 0), "short": Point(2, 0),
                        "alternate": Point(0, 3), "goal": Point(4, 0)}.items():
        graph.add_point(name, point)
    for left, right in (("start", "short"), ("short", "goal"),
                        ("start", "alternate"), ("alternate", "goal")):
        graph.connect(left, right)
    world = WorldNav()
    world.add_zone("synthetic", graph)
    verified = {("synthetic", name, edge.target)
                for name, edges in graph.edges.items() for edge in edges}
    navigator = WorldNavigator(
        world, start_zone="synthetic", start_node="start",
        goal_zone="synthetic", goal_node="goal", level=1,
        verified_moves=verified, verified_zones=set(),
        stall_timeout=5, arrival_radius=0.25, min_progress=0.2)
    original = navigator.observe(NavigationObservation("synthetic", Point(0, 0), 0)).node
    alternate = navigator.observe(NavigationObservation("synthetic", Point(0, 0), 5)).node
    navigator.observe(NavigationObservation("synthetic", Point(0, 3), 6))
    final = navigator.observe(NavigationObservation("synthetic", Point(4, 0), 7))
    return {"simulation_only": True, "no_game_input": True,
            "initial_waypoint": original, "replanned_waypoint": alternate,
            "quarantined_directed_edges": len(navigator.quarantined),
            "final_directive": final.kind}
