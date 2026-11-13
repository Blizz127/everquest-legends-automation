"""Read-only target hints from the client's text log.

The November helper recognizes ``Targeted (NPC): name`` lines, but the log
does not contain a unique entity ID and some automatic retargets emit no such
line. Hints from this module must never become a strict-assist target token.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from pathlib import Path
import re
import time

from .location_log import NonReplayingLogTail, parse_client_log_line


_TARGETED = re.compile(r"Targeted \(([^)]+)\):\s*(.+)", re.IGNORECASE)
_NO_TARGET = re.compile(
    r"(?:Consider whom\?|You no longer have a target|"
    r"You must first (?:select|click).+|You do not have a target)",
    re.IGNORECASE,
)
_DEATH = re.compile(r"(?:You have been slain .+|You died|You die[.!])")


@dataclass(frozen=True)
class TargetLogHint:
    kind: str
    display_name: str
    explicit_selection_count: int
    log_epoch: int
    log_local_time: datetime
    received_monotonic: float

    @property
    def uniquely_verified(self) -> bool:
        """A log display name cannot distinguish same-name entities."""
        return False


class TargetLogMonitor:
    """Track explicit log target hints without granting targeting permission.

    Existing log history, resets, zoning, death and targetless messages cannot
    bootstrap a target. ``explicit_selection_count`` changes on every logged
    selection, including two consecutive selections with the same name, but
    it is not a complete selection epoch because unlogged retargets exist.
    """

    def __init__(self, log_path: Path, *, expected_character: str,
                 expected_server: str, max_bytes: int = 512 * 1024) -> None:
        if log_path.name != f"eqlog_{expected_character}_{expected_server}.txt":
            raise ValueError("Target log does not match expected character/server")
        self.tail = NonReplayingLogTail(log_path, max_bytes=max_bytes)
        self.last_logged_hint: TargetLogHint | None = None
        self.explicit_selection_count = 0
        self.last_log_local_time: datetime | None = None
        self.last_received_monotonic: float | None = None
        self.last_invalidation = "startup"
        self.tail.poll()  # Never read an existing character's historical log.

    def _invalidate(self, reason: str) -> None:
        self.last_logged_hint = None
        self.last_invalidation = reason

    def poll(self, *, now: float | None = None) -> TargetLogHint | None:
        """Return only a newly logged selection hint, never a current target."""
        received_at = time.monotonic() if now is None else now
        if (not isinstance(received_at, (int, float)) or
                isinstance(received_at, bool) or not isfinite(received_at)):
            self._invalidate("invalid observation time")
            raise ValueError("Observation time must be finite")
        if (self.last_received_monotonic is not None and
                received_at < self.last_received_monotonic):
            self._invalidate("observation time moved backward")
            raise ValueError("Observation time moved backward")
        self.last_received_monotonic = received_at
        try:
            lines, reset = self.tail.poll()
        except Exception:
            self._invalidate("log read failed")
            raise
        if reset:
            self._invalidate("log reset")
            self.last_log_local_time = None
            return None
        newest: TargetLogHint | None = None
        for line in lines:
            parsed = parse_client_log_line(line)
            if parsed is None:
                self._invalidate("unparsed log line")
                newest = None
                continue
            log_time, body = parsed
            if (self.last_log_local_time is not None and
                    log_time < self.last_log_local_time):
                self._invalidate("log time moved backward")
                self.last_log_local_time = None
                return None
            self.last_log_local_time = log_time
            if (body.startswith("LOADING, PLEASE WAIT") or
                    body.startswith("You have entered ")):
                self._invalidate("zone transition")
                newest = None
                continue
            if _DEATH.fullmatch(body):
                self._invalidate("death")
                newest = None
                continue
            if _NO_TARGET.fullmatch(body):
                self._invalidate("no target")
                newest = None
                continue
            targeted = _TARGETED.fullmatch(body)
            if targeted is None:
                if body.startswith("Targeted "):
                    self._invalidate("malformed target selection")
                    newest = None
                continue
            name = targeted.group(2).strip()
            kind = targeted.group(1).casefold()
            if not name or kind not in {"npc", "pc", "corpse"}:
                self._invalidate("unsupported or empty target selection")
                newest = None
                continue
            self.explicit_selection_count += 1
            newest = TargetLogHint(
                kind=kind, display_name=name,
                explicit_selection_count=self.explicit_selection_count,
                log_epoch=self.tail.epoch, log_local_time=log_time,
                received_monotonic=received_at,
            )
            self.last_logged_hint = newest
            self.last_invalidation = ""
        return newest
