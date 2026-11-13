"""Strict offline rotation proposal for the owner's current target.

This module never sends input or changes target, attack state, movement,
spells, or gems. Each proposed action retains a cancellable mode permit.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from math import isfinite

from .control import ControlPlane, QueuedAction
from .modes import Action, Mode, action_from_prior_rotation
from .prior_rotation_core import Catalog, Rotation, SLOTS, Action as RotationAction
from .screen_observer import GaugeReading


class TargetRelation(str, Enum):
    UNKNOWN = "unknown"
    SELF = "self"
    FRIENDLY = "friendly"
    HOSTILE_NPC = "hostile_npc"
    HOSTILE_PLAYER = "hostile_player"


ABILITY_ROLES = {
    "/doability Bash": "bash",
    "/doability Smite": "smite_ability",
    "/alt activate 6001": "lay_hands",
}


@dataclass(frozen=True)
class AssistObservation:
    observed_at: float
    character_name: str
    class_name: str
    level: int
    game_focused: bool
    chat_open: bool
    current_target_verified: bool
    target_token: str | None
    hp: float | None
    mana: float | None
    memorized: dict[int, int] | None
    available_abilities: frozenset[str] = frozenset()
    target_relation: TargetRelation = TargetRelation.UNKNOWN
    target_is_undead: bool | None = None

    @classmethod
    def from_gauges(cls, reading: GaugeReading, *, character_name: str,
                    class_name: str, level: int, game_focused: bool,
                    chat_open: bool, current_target_verified: bool,
                    target_token: str | None,
                    memorized: dict[int, int] | None,
                    available_abilities: frozenset[str] = frozenset(),
                    target_relation: TargetRelation = TargetRelation.UNKNOWN,
                    target_is_undead: bool | None = None) -> "AssistObservation":
        return cls(observed_at=reading.observed_at,
                   character_name=character_name, class_name=class_name,
                   level=level, game_focused=game_focused, chat_open=chat_open,
                   current_target_verified=current_target_verified,
                   target_token=target_token, hp=reading.hp, mana=reading.mana,
                   memorized=memorized, available_abilities=available_abilities,
                   target_relation=target_relation,
                   target_is_undead=target_is_undead)


@dataclass(frozen=True)
class AssistProposal:
    source: RotationAction
    queued: QueuedAction
    target_token: str
    target_relation: TargetRelation
    target_is_undead: bool | None
    proposed_observed_at: float


class AssistAdvisor:
    def __init__(self, catalog: Catalog, *, character_name: str,
                 class_name: str, level: int,
                 known_spells: set[int], control: ControlPlane,
                 verified_self_heal_spell_ids: frozenset[int] = frozenset(),
                 verified_self_buff_spell_ids: frozenset[int] = frozenset(),
                 verified_self_lay_hands: bool = False) -> None:
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
        # Empty by default: the copied spell table alone does not establish
        # how target type 51 or class abilities behave in the live client.
        self.verified_self_heal_spell_ids = frozenset(verified_self_heal_spell_ids)
        self.verified_self_buff_spell_ids = frozenset(verified_self_buff_spell_ids)
        self.verified_self_lay_hands = verified_self_lay_hands

    def _spell_allowed(self, role: str, observation: AssistObservation) -> bool:
        spell = self.rotation.profile[role]
        relation = observation.target_relation
        if role in {"nuke", "stun"}:
            return spell.target_type == 5 and relation == TargetRelation.HOSTILE_NPC
        if role == "undead":
            return (spell.target_type == 10 and
                    relation == TargetRelation.HOSTILE_NPC and
                    observation.target_is_undead is True)
        if role in {"quick_heal", "heal", "hot"}:
            return (spell.target_type == 51 and relation == TargetRelation.SELF and
                    spell.id in self.verified_self_heal_spell_ids)
        if role in {"yaulp", "proc"}:
            return (spell.target_type == 6 and
                    relation in {TargetRelation.SELF, TargetRelation.HOSTILE_NPC} and
                    spell.id in self.verified_self_buff_spell_ids)
        return False

    def _ability_allowed(self, role: str, observation: AssistObservation) -> bool:
        if role in {"bash", "smite_ability"}:
            return observation.target_relation == TargetRelation.HOSTILE_NPC
        if role == "lay_hands":
            return (observation.target_relation == TargetRelation.SELF and
                    self.verified_self_lay_hands)
        return False

    def _source_allowed(self, source: RotationAction,
                        observation: AssistObservation) -> bool:
        if source.role in self.rotation.profile:
            spell = self.rotation.profile[source.role]
            return (source.command == f"/cast {SLOTS[source.role]}" and
                    observation.memorized is not None and
                    observation.memorized.get(SLOTS[source.role]) == spell.id and
                    self._spell_allowed(source.role, observation))
        if source.role in {"bash", "smite_ability", "lay_hands"}:
            return (ABILITY_ROLES.get(source.command) == source.role and
                    source.command in observation.available_abilities and
                    self._ability_allowed(source.role, observation))
        return False

    def _ready(self, observation: AssistObservation, now: float) -> bool:
        if self.control.controller.mode != Mode.ASSIST:
            return False
        if (not isinstance(now, (int, float)) or isinstance(now, bool) or
                not isinstance(observation.observed_at, (int, float)) or
                isinstance(observation.observed_at, bool) or
                not isfinite(now) or not isfinite(observation.observed_at) or
                not 0 <= now - observation.observed_at <= 1.0):
            return False
        if (not isinstance(observation.character_name, str) or
                not isinstance(observation.class_name, str) or
                observation.character_name.casefold() != self.character_name or
                observation.class_name.casefold() != self.class_name or
                observation.level != self.rotation.level):
            return False
        if not observation.game_focused or observation.chat_open:
            return False
        if (not observation.current_target_verified or
                not isinstance(observation.target_token, str) or
                not observation.target_token.strip()):
            return False
        if (not isinstance(observation.target_relation, TargetRelation) or
                observation.target_relation == TargetRelation.UNKNOWN or
                observation.target_is_undead is not None and
                not isinstance(observation.target_is_undead, bool)):
            return False
        if any(not isinstance(value, (int, float)) or isinstance(value, bool) or
               not isfinite(value) or not 0 <= value <= 1
               for value in (observation.hp, observation.mana)):
            return False
        if not isinstance(observation.memorized, dict):
            return False
        return True

    def propose(self, observation: AssistObservation, now: float) -> AssistProposal | None:
        if not self._ready(observation, now):
            return None
        # Low self health with somebody else selected requires the owner to
        # change target or heal manually; assist never retargets for a heal.
        if observation.hp <= 0.65 and observation.target_relation != TargetRelation.SELF:
            return None
        profile = {role: spell for role, spell in self.rotation.profile.items()
                   if observation.memorized.get(SLOTS[role]) == spell.id and
                   self._spell_allowed(role, observation)}
        abilities = {command for command in observation.available_abilities
                     if self._ability_allowed(ABILITY_ROLES.get(command, ""), observation)}
        if observation.hp <= 0.65:
            profile = {role: spell for role, spell in profile.items()
                       if role in {"quick_heal", "heal", "hot"}}
            abilities.intersection_update({"/alt activate 6001"})
        source = replace(self.rotation, profile=profile).choose(
            now, observation.hp, observation.mana, abilities)
        if source is None:
            return None
        if not self._source_allowed(source, observation):
            return None
        action: Action = action_from_prior_rotation(source.role, source.command)
        permit = self.control.controller.permit()
        if not self.control.controller.allows(permit, action):
            return None
        return AssistProposal(source, QueuedAction(permit, action),
                              observation.target_token,
                              observation.target_relation,
                              observation.target_is_undead,
                              observation.observed_at)

    def still_allowed(self, proposal: AssistProposal,
                      observation: AssistObservation, now: float) -> bool:
        """A future sender must refresh observations and check before each key."""
        if not self._ready(observation, now):
            return False
        if observation.observed_at <= proposal.proposed_observed_at:
            return False
        if observation.target_token != proposal.target_token:
            return False
        if (observation.target_relation != proposal.target_relation or
                observation.target_is_undead != proposal.target_is_undead):
            return False
        if not self._source_allowed(proposal.source, observation):
            return False
        if proposal.queued.action != action_from_prior_rotation(
                proposal.source.role, proposal.source.command):
            return False
        return self.control.allows(proposal.queued)

    def committed(self, proposal: AssistProposal,
                  observation: AssistObservation, now: float) -> bool:
        """Advance cooldowns only after a confirmed send while permit is live."""
        if not self.still_allowed(proposal, observation, now):
            return False
        self.rotation.committed(proposal.source, now)
        return True
