"""Action permissions and synchronous cancellation for offline planning.

The prior October tool's rotation chooses spells and abilities. This module
defines the separate authority boundary needed before any future input bridge.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from threading import Event, Lock
import re


class Mode(str, Enum):
    OFF = "off"
    ASSIST = "assist"
    FULL_AUTO = "full"


class ActionKind(str, Enum):
    CAST = "cast"
    ABILITY = "ability"
    HEAL = "heal"
    BUFF = "buff"
    ATTACK = "attack"
    MOVE = "move"
    TARGET = "target"
    LOOT = "loot"
    VENDOR = "vendor"
    CAMP = "camp"
    REST = "rest"
    ZONE = "zone"
    LOGIN = "login"
    RECOVER = "recover"
    PAUSE = "pause"
    SCRIBE = "scribe"
    MEMORIZE = "memorize"


ASSIST_ACTIONS = frozenset({
    ActionKind.CAST, ActionKind.ABILITY, ActionKind.HEAL, ActionKind.BUFF,
})

COMMAND_KINDS = (
    (re.compile(r"/cast [1-8]"), frozenset({ActionKind.CAST, ActionKind.HEAL, ActionKind.BUFF})),
    (re.compile(r"/doability (?:Bash|Smite)"), frozenset({ActionKind.ABILITY})),
    (re.compile(r"/alt activate 6001"), frozenset({ActionKind.ABILITY, ActionKind.HEAL})),
    (re.compile(r"/attack (?:on|off)"), frozenset({ActionKind.ATTACK})),
)


@dataclass(frozen=True)
class Action:
    kind: ActionKind
    detail: str


@dataclass(frozen=True)
class Permit:
    """A mode snapshot. Old permits cancel when the mode changes."""

    mode: Mode
    generation: int
    cancelled: Event


class ModeController:
    def __init__(self) -> None:
        self._lock = Lock()
        self._mode = Mode.OFF
        self._generation = 0
        self._cancelled = Event()
        self._cancelled.set()

    @property
    def mode(self) -> Mode:
        with self._lock:
            return self._mode

    def switch(self, mode: Mode) -> Permit:
        mode = Mode(mode)  # An invalid request must not cancel the current mode.
        # Signal the old permit before waiting for the short metadata lock.
        self._cancelled.set()
        with self._lock:
            self._generation += 1
            self._mode = Mode(mode)
            self._cancelled = Event()
            if mode == Mode.OFF:
                self._cancelled.set()
            return Permit(self._mode, self._generation, self._cancelled)

    def permit(self) -> Permit:
        with self._lock:
            return Permit(self._mode, self._generation, self._cancelled)

    def allows(self, permit: Permit, action: Action) -> bool:
        if permit.cancelled.is_set():
            return False
        # Command strings are never accepted merely because their claimed kind
        # is permitted. A live bridge would also recheck per emitted key.
        if action.detail.startswith("/") and not any(
                pattern.fullmatch(action.detail) and action.kind in kinds
                for pattern, kinds in COMMAND_KINDS):
            return False
        with self._lock:
            if permit.generation != self._generation or permit.mode != self._mode:
                return False
            if self._mode == Mode.FULL_AUTO:
                return True
            return self._mode == Mode.ASSIST and action.kind in ASSIST_ACTIONS


def action_from_prior_rotation(role: str, command: str) -> Action:
    """Classify one action from the October Paladin/Cleric rotation planner."""

    if re.fullmatch(r"/cast [1-8]", command):
        if role in {"quick_heal", "heal", "hot", "lay_hands"}:
            return Action(ActionKind.HEAL, command)
        if role in {"yaulp", "proc"}:
            return Action(ActionKind.BUFF, command)
        return Action(ActionKind.CAST, command)
    if re.fullmatch(r"/(?:doability (?:Bash|Smite)|alt activate 6001)", command):
        return Action(ActionKind.ABILITY, command)
    if re.fullmatch(r"/attack (?:on|off)", command):
        return Action(ActionKind.ATTACK, command)
    raise ValueError(f"Unknown prior rotation command: {command!r}")
