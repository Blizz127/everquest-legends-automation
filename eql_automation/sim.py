"""Synthetic, offline exercises for the mode and planning contracts."""
from __future__ import annotations

from dataclasses import dataclass, field

from .modes import Action, ActionKind, Mode, ModeController, action_from_prior_rotation
from .nav import NavGraph, Point
from .prior_rotation_core import Rotation, Spell


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
    full_move = sink.submit(move, full_permit)
    return {
        "simulation_only": True,
        "prior_rotation_role": choice.role,
        "assist_heal_allowed": assist_heal,
        "assist_move_denied": not assist_move,
        "off_invalidates_queued_action": off_rejects_old_permit,
        "full_move_allowed": full_move,
        "safe_route": full_route,
    }
