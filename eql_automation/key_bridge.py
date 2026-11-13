"""Recording-only assist command keys with a per-key safety recheck.

No evdev, Xlib, Wine or game input is imported here. The October helper's
typing pattern is represented as symbolic key down/up events for testing.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
import re
from typing import Callable

from .assist import AssistAdvisor, AssistObservation, AssistProposal
from .control import ControlPlane
from .modes import Action, ActionKind, Mode


@dataclass(frozen=True)
class KeyTransition:
    key: str
    down: bool
    permit_generation: int


@dataclass(frozen=True)
class RecordedSendResult:
    recorded_complete: bool
    key_down_count: int
    draft_uncertain: bool
    reason: str


def assist_command_keys(action: Action) -> tuple[str, ...]:
    """Allow only rotation commands, never attack, target or movement keys."""
    valid = (
        action.kind in {ActionKind.CAST, ActionKind.HEAL, ActionKind.BUFF}
        and re.fullmatch(r"/cast [1-8]", action.detail)
        or action.kind == ActionKind.ABILITY and
        re.fullmatch(r"/(?:doability (?:Bash|Smite)|alt activate 6001)",
                     action.detail)
        or action.kind == ActionKind.HEAL and
        action.detail == "/alt activate 6001"
    )
    if not valid:
        raise ValueError("Command is outside the assist key allowlist")
    return (*action.detail, "ENTER")


class RecordingAssistKeyBridge:
    """Keep the original assist permit and sample before each symbolic key."""

    def __init__(self, control: ControlPlane,
                 record: Callable[[KeyTransition], None]) -> None:
        self.control = control
        self.record = record

    @property
    def draft_uncertain(self) -> bool:
        return self.control.command_draft_uncertain

    def confirm_draft_cleared(self, observation: AssistObservation,
                              now: float, *, explicit_clear: bool) -> bool:
        """Require OFF and an explicit, fresh focused confirmation to resume."""
        if not self.control.acquire_key_channel():
            return False
        try:
            if (not explicit_clear or self.control.controller.mode != Mode.OFF or
                    not observation.game_focused or observation.chat_open or
                    not isinstance(now, (int, float)) or isinstance(now, bool) or
                    not isinstance(observation.observed_at, (int, float)) or
                    isinstance(observation.observed_at, bool) or
                    not isfinite(now) or not isfinite(observation.observed_at) or
                    not 0 <= now - observation.observed_at <= 1):
                return False
            self.control.set_command_draft_uncertain(False)
            return True
        finally:
            self.control.release_key_channel()

    def send(self, advisor: AssistAdvisor, proposal: AssistProposal, *,
             observe: Callable[[], AssistObservation],
             clock: Callable[[], float]) -> RecordedSendResult:
        if not self.control.acquire_key_channel():
            return RecordedSendResult(False, 0, self.draft_uncertain,
                                      "Another assist command is in flight")
        try:
            return self._send_one(advisor, proposal, observe=observe, clock=clock)
        finally:
            self.control.release_key_channel()

    def _send_one(self, advisor: AssistAdvisor, proposal: AssistProposal, *,
                  observe: Callable[[], AssistObservation],
                  clock: Callable[[], float]) -> RecordedSendResult:
        if advisor.control is not self.control:
            raise ValueError("Assist advisor and key bridge must share one control plane")
        if proposal.queued.permit.mode != Mode.ASSIST:
            raise ValueError("A genuine assist permit is required")
        keys = assist_command_keys(proposal.queued.action)
        if self.draft_uncertain:
            return RecordedSendResult(False, 0, True, "Previous command draft is uncleared")
        key_downs = 0
        last_observed_at = proposal.proposed_observed_at
        for key in keys:
            try:
                observation = observe()
                now = clock()
                fresh = (isinstance(observation, AssistObservation) and
                         isinstance(observation.observed_at, (int, float)) and
                         not isinstance(observation.observed_at, bool) and
                         isfinite(observation.observed_at) and
                         observation.observed_at > last_observed_at)
                allowed = (fresh and
                           advisor.still_allowed(proposal, observation, now))
            except Exception:
                allowed = False
                observation = None
            if not allowed:
                if self.control.controller.mode != Mode.OFF:
                    self.control.emergency_stop("Assist key observation changed or failed")
                return RecordedSendResult(False, key_downs, self.draft_uncertain,
                                          "Permit or fresh assist observation failed")
            last_observed_at = observation.observed_at
            transition = KeyTransition(key, True, proposal.queued.permit.generation)
            try:
                # A completed OFF transition cannot race a later key DOWN.
                emitted = self.control.record_key_if_allowed(
                    proposal.queued, lambda: self.record(transition))
            except Exception:
                self.control.set_command_draft_uncertain(True)
                try:
                    self.record(KeyTransition(key, False,
                                              proposal.queued.permit.generation))
                except Exception:
                    pass  # A future live sink also needs an independent release-all path.
                try:
                    self.control.emergency_stop("Assist key recorder failed")
                except Exception:
                    pass  # Preserve the original recorder failure after attempting OFF.
                raise
            if not emitted:
                return RecordedSendResult(False, key_downs, self.draft_uncertain,
                                          "Assist mode switched OFF")
            self.control.set_command_draft_uncertain(True)
            key_downs += 1
            try:
                # Release even if OFF was pressed during this key's DOWN.
                self.record(KeyTransition(key, False,
                                          proposal.queued.permit.generation))
            except Exception:
                try:
                    self.control.emergency_stop("Assist key release failed")
                except Exception:
                    pass
                raise
            if not self.control.allows(proposal.queued):
                return RecordedSendResult(False, key_downs, self.draft_uncertain,
                                          "Assist mode switched during key")
            if key == "ENTER":
                self.control.set_command_draft_uncertain(False)
        return RecordedSendResult(True, key_downs, False,
                                  "Symbolic key sequence recorded")
