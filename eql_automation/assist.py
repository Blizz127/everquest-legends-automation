"""Strict offline rotation proposal for the owner's current target.

This module never sends input or changes target, attack state, movement,
spells, or gems. Each proposed action retains a cancellable mode permit.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .control import ControlPlane, QueuedAction
from .modes import Action, ActionKind, Mode, action_from_prior_rotation
from .prior_rotation_core import Catalog, Rotation, SLOTS, Action as RotationAction
from .screen_observer import GaugeReading


@dataclass(frozen=True)
class AssistObservation:
    observed_at: float
    character_name: str
    class_name: str
    level: int
    game_focused: bool
    chat_open: bool
    current_target_verified: bool
    hp: float | None
    mana: float | None
    memorized: dict[int, int] | None
    available_abilities: frozenset[str] = frozenset()

    @classmethod
    def from_gauges(cls, reading: GaugeReading, *, character_name: str,
                    class_name: str, level: int, game_focused: bool,
                    chat_open: bool, current_target_verified: bool,
                    memorized: dict[int, int] | None,
                    available_abilities: frozenset[str] = frozenset()) -> "AssistObservation":
        return cls(reading.observed_at, character_name, class_name, level,
                   game_focused, chat_open, current_target_verified,
                   reading.hp, reading.mana, memorized, available_abilities)


@dataclass(frozen=True)
class AssistProposal:
    source: RotationAction
    queued: QueuedAction


class AssistAdvisor:
    def __init__(self, catalog: Catalog, *, character_name: str,
                 class_name: str, level: int,
                 known_spells: set[int], control: ControlPlane) -> None:
        if not character_name.strip():
            raise ValueError("Character identity is required")
        if not known_spells:
            raise ValueError("A freshly verified spellbook is required")
        profile = catalog.profile(level, class_name=class_name, known=known_spells)
        if not profile:
            raise ValueError("No known class-eligible rotation spells")
        self.rotation = Rotation(profile, level)
        self.control = control
        self.character_name = character_name.casefold()
        self.class_name = class_name.casefold()

    def _ready(self, observation: AssistObservation, now: float) -> bool:
        if self.control.controller.mode != Mode.ASSIST:
            return False
        if (not isfinite(now) or not isfinite(observation.observed_at) or
                not 0 <= now - observation.observed_at <= 1.0):
            return False
        if (observation.character_name.casefold() != self.character_name or
                observation.class_name.casefold() != self.class_name or
                observation.level != self.rotation.level):
            return False
        if not observation.game_focused or observation.chat_open:
            return False
        if not observation.current_target_verified:
            return False
        if any(value is None or not isfinite(value) or not 0 <= value <= 1
               for value in (observation.hp, observation.mana)):
            return False
        if observation.memorized is None or any(
                observation.memorized.get(SLOTS[role]) != spell.id
                for role, spell in self.rotation.profile.items()):
            return False
        return True

    def propose(self, observation: AssistObservation, now: float) -> AssistProposal | None:
        if not self._ready(observation, now):
            return None
        source = self.rotation.choose(now, observation.hp, observation.mana,
                                      set(observation.available_abilities))
        if source is None:
            return None
        action: Action = action_from_prior_rotation(source.role, source.command)
        permit = self.control.controller.permit()
        if not self.control.controller.allows(permit, action):
            return None
        return AssistProposal(source, QueuedAction(permit, action))

    def still_allowed(self, proposal: AssistProposal,
                      observation: AssistObservation, now: float) -> bool:
        """A future sender must refresh observations and check before each key."""
        if not self._ready(observation, now):
            return False
        if (proposal.queued.action.kind == ActionKind.ABILITY and
                proposal.source.command not in observation.available_abilities):
            return False
        return self.control.allows(proposal.queued)

    def committed(self, proposal: AssistProposal,
                  observation: AssistObservation, now: float) -> bool:
        """Advance cooldowns only after a confirmed send while permit is live."""
        if not self.still_allowed(proposal, observation, now):
            return False
        self.rotation.committed(proposal.source, now)
        return True
