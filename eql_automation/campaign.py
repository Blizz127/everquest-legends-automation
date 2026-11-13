"""Offline full-auto intent planner over supplied, synthetic-safe observations."""
from __future__ import annotations

from dataclasses import dataclass

from .modes import Action, ActionKind


@dataclass(frozen=True)
class Camp:
    name: str
    min_level: int
    max_level: int
    expected_xp_hour: float
    crowd: float = 0.0
    danger: float = 0.0

    def score(self) -> float:
        return self.expected_xp_hour * max(0.0, 1.0 - self.crowd) * max(0.0, 1.0 - self.danger)


@dataclass(frozen=True)
class WorldSnapshot:
    level: int
    hp: float
    mana: float
    bag_fullness: float
    dead: bool = False
    disconnected: bool = False
    target_present: bool = False
    camp: str | None = None
    observed_xp_hour: float | None = None


class CampaignPlanner:
    def __init__(self, camps: list[Camp]) -> None:
        self.camps = camps

    def select_camp(self, state: WorldSnapshot) -> Camp | None:
        eligible = [camp for camp in self.camps
                    if camp.min_level <= state.level <= camp.max_level and camp.score() > 0]
        return max(eligible, key=Camp.score, default=None)

    def decide(self, state: WorldSnapshot) -> Action | None:
        """Return one intent. No game commands are generated here."""

        if state.dead:
            return Action(ActionKind.RECOVER, "corpse recovery requires a verified route")
        if state.disconnected:
            return Action(ActionKind.LOGIN, "relogin requires authorized account access")
        if state.bag_fullness >= 0.9:
            return Action(ActionKind.VENDOR, "sell only after item/value review")
        if state.hp <= 0.5 or state.mana <= 0.25:
            return Action(ActionKind.REST, "recover health or mana")
        best = self.select_camp(state)
        if best is None:
            return None
        current = next((camp for camp in self.camps if camp.name == state.camp), None)
        poor_xp = (current is not None and state.observed_xp_hour is not None
                   and state.observed_xp_hour < 0.5 * current.expected_xp_hour)
        if state.camp is None or (state.camp != best.name and poor_xp):
            return Action(ActionKind.CAMP, best.name)
        if not state.target_present:
            return Action(ActionKind.TARGET, "select safe target from verified observations")
        return None  # The prior combat rotation chooses the next spell/ability.
