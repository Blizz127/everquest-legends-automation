"""Recording-only spell-gem click seam for rotation assist.

The copied UI defines gem widgets, but supplies no live screen coordinates.
Only a separate, fresh, externally verified hitbox observation can authorize
one symbolic mouse click. This module never captures a screen or sends input.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
import re
from typing import Callable

from .assist import AssistAdvisor, AssistObservation, AssistProposal
from .control import ControlPlane
from .modes import ActionKind, Mode


@dataclass(frozen=True)
class GemHitboxObservation:
    """Evidence from a future observer, not a claim derived from static XML."""

    observed_at: float
    window_size: tuple[int, int]
    layout_fingerprint: str
    gem_slot: int
    gem_spell_id: int
    box: tuple[int, int, int, int]
    gem_visible: bool
    unobstructed: bool
    game_focused: bool


@dataclass(frozen=True)
class MouseTransition:
    x: int
    y: int
    down: bool
    permit_generation: int


@dataclass(frozen=True)
class RecordedClickResult:
    recorded_complete: bool
    reason: str


def _gem_slot(proposal: AssistProposal) -> int | None:
    action = proposal.queued.action
    if action.kind not in {ActionKind.CAST, ActionKind.HEAL, ActionKind.BUFF}:
        return None
    match = re.fullmatch(r"/cast ([1-8])", action.detail)
    if match is None or proposal.source.command != action.detail:
        return None
    return int(match.group(1))


def _valid_hitbox(evidence: GemHitboxObservation, *, slot: int,
                  spell_id: int, now: float, after: float,
                  layout_fingerprint: str,
                  scene_observed_at: float) -> bool:
    if (not isinstance(evidence, GemHitboxObservation) or
            not isinstance(now, (int, float)) or isinstance(now, bool) or
            not isinstance(evidence.observed_at, (int, float)) or
            isinstance(evidence.observed_at, bool) or
            not isfinite(now) or not isfinite(evidence.observed_at) or
            not after < evidence.observed_at <= now or
            evidence.observed_at != scene_observed_at or
            now - evidence.observed_at > 1 or
            evidence.game_focused is not True or
            evidence.gem_visible is not True or
            evidence.unobstructed is not True or
            evidence.layout_fingerprint != layout_fingerprint or
            not isinstance(evidence.layout_fingerprint, str) or
            not evidence.layout_fingerprint.strip() or
            not isinstance(evidence.gem_slot, int) or
            isinstance(evidence.gem_slot, bool) or
            not isinstance(evidence.gem_spell_id, int) or
            isinstance(evidence.gem_spell_id, bool) or
            evidence.gem_slot != slot or evidence.gem_spell_id != spell_id):
        return False
    size, box = evidence.window_size, evidence.box
    return (isinstance(size, (tuple, list)) and len(size) == 2 and
            isinstance(box, (tuple, list)) and len(box) == 4 and
            all(isinstance(value, int) and not isinstance(value, bool)
                for value in (*size, *box)) and
            0 < size[0] <= 16384 and 0 < size[1] <= 16384 and
            0 <= box[0] < box[2] <= size[0] and
            0 <= box[1] < box[3] <= size[1])


class RecordingGemClickBridge:
    """Record one click only while the original assist permit remains valid."""

    def __init__(self, control: ControlPlane,
                 record: Callable[[MouseTransition], None]) -> None:
        self.control = control
        self.record = record

    def send(self, advisor: AssistAdvisor, proposal: AssistProposal, *,
             observe: Callable[[], tuple[AssistObservation, GemHitboxObservation]],
             clock: Callable[[], float], layout_fingerprint: str) -> RecordedClickResult:
        if advisor.control is not self.control:
            raise ValueError("Assist advisor and gem bridge must share one control plane")
        if proposal.queued.permit.mode != Mode.ASSIST:
            raise ValueError("A genuine assist permit is required")
        slot = _gem_slot(proposal)
        if slot is None:
            return RecordedClickResult(False, "Only a spell-gem cast can be clicked")
        if not self.control.acquire_key_channel():
            return RecordedClickResult(False, "Another assist input is in flight")
        try:
            if self.control.command_draft_uncertain:
                return RecordedClickResult(False, "Uncleared chat command draft")
            try:
                observation, hitbox = observe()
                now = clock()
                allowed = (isinstance(observation, AssistObservation) and
                           advisor.still_allowed(proposal, observation, now) and
                           _valid_hitbox(hitbox, slot=slot,
                                         spell_id=observation.memorized[slot],
                                         now=now,
                                         after=proposal.proposed_observed_at,
                                         layout_fingerprint=layout_fingerprint,
                                         scene_observed_at=observation.observed_at))
            except Exception:
                allowed = False
            if not allowed:
                self.control.emergency_stop("Spell-gem observation changed or failed")
                return RecordedClickResult(False, "Fresh assist or gem observation failed")
            x = (hitbox.box[0] + hitbox.box[2]) // 2
            y = (hitbox.box[1] + hitbox.box[3]) // 2
            down = MouseTransition(x, y, True, proposal.queued.permit.generation)
            up = MouseTransition(x, y, False, proposal.queued.permit.generation)
            try:
                emitted = self.control.record_key_if_allowed(
                    proposal.queued, lambda: self.record(down))
            except Exception:
                try:
                    self.record(up)
                except Exception:
                    pass  # A future native sink also needs release-all.
                try:
                    self.control.emergency_stop("Spell-gem mouse down failed")
                except Exception:
                    pass  # Preserve the original recorder error.
                raise
            if not emitted:
                return RecordedClickResult(False, "Assist mode switched OFF")
            try:
                self.record(up)
            except Exception:
                try:
                    self.control.emergency_stop("Spell-gem mouse release failed")
                except Exception:
                    pass
                raise
            if not self.control.allows(proposal.queued):
                return RecordedClickResult(False, "Assist mode switched during click")
            return RecordedClickResult(True, "Symbolic spell-gem click recorded")
        finally:
            self.control.release_key_channel()
