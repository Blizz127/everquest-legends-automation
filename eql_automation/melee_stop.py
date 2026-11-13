"""Recording-only native melee stop gate for a future private-client trial.

The installed client describes ``/attack`` as a toggle. Never issue a toggle
from an unknown state or retry it without an observed OFF acknowledgment.
This module parses log observations and chooses an intent; it sends no input.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math

from .prior_rotation_core import message_body


class MeleeState(str, Enum):
    UNKNOWN = "unknown"
    ON = "on"
    OFF = "off"


class StopDecision(str, Enum):
    CONFIRMED = "confirmed_off"
    SEND_ONCE = "send_one_verified_toggle"
    WAIT = "await_off_acknowledgment"
    MANUAL = "halt_and_request_manual_stop"


@dataclass
class NativeMeleeStopGate:
    """Require an exact, continuously observed state before a stop command.

    A caller must invalidate on log rotation, unreadable polls, zoning, login,
    target/client uncertainty, or any input draft it cannot account for. It
    must only set ``toggle_verified`` after an owner-supervised client check.
    """

    toggle_verified: bool = False
    timeout_seconds: float = 3.0
    state: MeleeState = MeleeState.UNKNOWN
    pending_since: float | None = None
    failed: bool = False
    last_observed_at: float | None = None

    def invalidate(self) -> None:
        self.state = MeleeState.UNKNOWN
        self.pending_since = None
        self.failed = False
        self.last_observed_at = None

    def observe(self, log_line: str, observed_at: float) -> bool:
        """Record only exact client system messages; return True if accepted."""
        if not math.isfinite(observed_at):
            self.invalidate()
            return False
        if self.last_observed_at is not None and observed_at < self.last_observed_at:
            self.invalidate()
            return False
        body = message_body(log_line)
        next_state = {
            "Auto attack is on.": MeleeState.ON,
            "Auto attack is off.": MeleeState.OFF,
        }.get(body)
        if next_state is None:
            return False
        self.last_observed_at = observed_at
        self.state = next_state
        if self.pending_since is not None:
            if next_state is MeleeState.OFF and observed_at >= self.pending_since:
                self.pending_since = None
            elif next_state is MeleeState.ON and observed_at >= self.pending_since:
                # The one attempted toggle did not establish OFF. A second
                # toggle could turn melee back on, so require manual review.
                self.pending_since = None
                self.failed = True
        return True

    def request_stop(self, now: float) -> StopDecision:
        if not math.isfinite(now):
            self.invalidate()
            return StopDecision.MANUAL
        if self.pending_since is not None:
            if now < self.pending_since or now - self.pending_since > self.timeout_seconds:
                self.pending_since = None
                self.failed = True
                self.state = MeleeState.UNKNOWN
                return StopDecision.MANUAL
            return StopDecision.WAIT
        if self.failed:
            return StopDecision.MANUAL
        if self.state is MeleeState.OFF:
            return StopDecision.CONFIRMED
        if self.state is not MeleeState.ON or not self.toggle_verified:
            return StopDecision.MANUAL
        if self.last_observed_at is None or now < self.last_observed_at:
            self.invalidate()
            return StopDecision.MANUAL
        # Reserve the one permitted toggle before giving it to the caller.
        # If dispatch fails, the timeout ends in manual review, never a retry.
        self.pending_since = now
        return StopDecision.SEND_ONCE
