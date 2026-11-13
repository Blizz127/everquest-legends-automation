"""Recording-only action dispatch boundary for synthetic runtime exercises.

This module has no game input transport. A future sender must recheck its
permit and fresh observations before every emitted key, not only per action.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Callable

from .campaign import WorldSnapshot
from .control import ControlPlane, QueuedAction
from .modes import Action, ActionKind, Permit


@dataclass(frozen=True)
class DispatchObservation:
    observed_at: float
    state: WorldSnapshot
    zone: str
    node: str
    target_token: str | None
    game_focused: bool
    chat_open: bool


@dataclass(frozen=True)
class DispatchPlan:
    queued: QueuedAction
    planned_observed_at: float
    state: WorldSnapshot
    zone: str
    node: str
    target_token: str | None


class DryRunDispatcher:
    """Recheck mode and scene before a recording sink accepts an intent."""

    def __init__(self, control: ControlPlane,
                 emit: Callable[[Action, Permit], bool]) -> None:
        self.control = control
        self.emit = emit

    def _safe(self, action: Action, observation: DispatchObservation,
              now: float) -> bool:
        state = observation.state
        if (not isinstance(now, (int, float)) or isinstance(now, bool) or
                not isinstance(observation.observed_at, (int, float)) or
                isinstance(observation.observed_at, bool) or
                not isfinite(now) or not isfinite(observation.observed_at) or
                not 0 <= now - observation.observed_at <= 1):
            return False
        if (not observation.game_focused or observation.chat_open or
                not isinstance(observation.zone, str) or not observation.zone or
                not isinstance(observation.node, str) or not observation.node or
                not isinstance(state.level, int) or isinstance(state.level, bool) or
                not 1 <= state.level <= 50 or state.gm_present):
            return False
        if any(not isinstance(value, (int, float)) or isinstance(value, bool) or
               not isfinite(value) or not 0 <= value <= 1
               for value in (state.hp, state.mana, state.bag_fullness)):
            return False
        if (state.target_present and
                (not isinstance(observation.target_token, str) or
                 not observation.target_token.strip())):
            return False
        if (state.under_attack and not state.target_present or
                state.disconnected and action.kind != ActionKind.LOGIN or
                state.dead and action.kind != ActionKind.RECOVER):
            return False
        if (action.kind == ActionKind.LOGIN and not state.disconnected or
                action.kind == ActionKind.RECOVER and not state.dead or
                action.kind == ActionKind.LOOT and
                (not state.loot_available or state.under_attack or
                 state.loot_space_warning is not False or
                 state.food_status in {"low", "out"} or
                 state.drink_status in {"low", "out"}) or
                action.kind in {ActionKind.MOVE, ActionKind.ZONE,
                                ActionKind.CAMP, ActionKind.VENDOR,
                                ActionKind.REST} and state.under_attack or
                action.kind == ActionKind.CAST and not state.target_present):
            return False
        return True

    def plan(self, action: Action, observation: DispatchObservation,
             now: float) -> DispatchPlan | None:
        if not self._safe(action, observation, now):
            return None
        queued = QueuedAction(self.control.controller.permit(), action)
        if not self.control.allows(queued):
            return None
        return DispatchPlan(queued, observation.observed_at,
                            observation.state, observation.zone,
                            observation.node, observation.target_token)

    def dispatch(self, plan: DispatchPlan, observation: DispatchObservation,
                 now: float) -> bool:
        """Requires a newer stable scene; the emitter still receives old permit."""
        action = plan.queued.action
        if (not self._safe(action, observation, now) or
                observation.observed_at <= plan.planned_observed_at or
                observation.state != plan.state or
                observation.zone != plan.zone or observation.node != plan.node or
                observation.target_token != plan.target_token or
                not self.control.allows(plan.queued)):
            return False
        return self.emit(action, plan.queued.permit)
