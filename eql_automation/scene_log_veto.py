"""Positive movement vetoes from appended client log lines, never permission.

Construct once per owner-started measurement generation. Existing history is
skipped; new positive hazards or lost continuity latch until a new owner-started
scope. A quiet log cannot prove a target absent, combat clear, or an area safe.
The recognized formats are a subset observed in retained owner logs. This
module neither reads game memory nor sends input.
"""
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from pathlib import Path
import re
import time

from .location_log import NonReplayingLogTail, parse_client_log_line, is_logging_boundary


_HIT = re.compile(r".+ YOU for [0-9]+ points? of damage\.(?: \(Riposte\))?")
_MISS = re.compile(r".+ tries to .+ YOU, but (?:misses|YOU are INVULNERABLE)!(?: \(Riposte\))?")
_DOT = re.compile(r"You have taken [0-9]+ damage from .+\.")
_NON_MELEE = re.compile(r"You were hit by non-melee for [0-9]+ damage\.")
_DEATH = re.compile(r"You have been slain by .+!")


def classify_log_veto(body: str) -> str | None:
    """Match complete system-message bodies, not keywords inside player chat."""
    if is_logging_boundary(body):
        return "logging_continuity_changed"
    if any(pattern.fullmatch(body) for pattern in (_HIT, _MISS, _DOT, _NON_MELEE)):
        return "incoming_attack"
    if body in {"You are stunned!", "YOU are drowning!", "YOU were injured by falling."}:
        return "player_hazard"
    if _DEATH.fullmatch(body):
        return "death"
    if body == "Auto attack is on.":
        return "native_melee_on"
    if body == "LOADING, PLEASE WAIT..." or re.fullmatch(r"You have entered .+\.", body):
        return "zone_transition"
    if body.startswith("Targeted "):
        # No entity identity or supported target-kind inference is necessary.
        return "target_selection"
    if (body.startswith(("LOADING, PLEASE WAIT", "You have entered "))
            or (body.startswith("Auto attack is ") and body != "Auto attack is off.")):
        return "unrecognized_safety_message"
    return None


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


@dataclass(frozen=True)
class LogVetoObservation:
    started_at: float | None
    finished_at: float | None
    cancel_generation: int
    log_epoch: int
    log_line_seq: int
    continuity_available: bool
    reason: str | None
    log_local_time: datetime | None = None

    @property
    def input_authorized(self):
        return False


class SceneLogVeto:
    """One non-replaying, latched supplement to independent current UI evidence.

    ``reason is None`` means only that this poll found no recognized veto.
    ``continuity_available`` covers bytes since the baseline, not whether the
    client is logging every event or still writing. Source timestamps are local
    seconds, not evidence freshness. The owning provider must separately bind
    the active game window/process and enforce cancellation and UI evidence.
    """
    def __init__(self, log_path: Path, *, expected_character: str,
                 expected_server: str, cancel_generation: int,
                 clock=time.monotonic, max_bytes: int = 512 * 1024):
        if (not expected_character or not expected_server
                or log_path.name != f"eqlog_{expected_character}_{expected_server}.txt"
                or not isinstance(cancel_generation, int) or isinstance(cancel_generation, bool)
                or cancel_generation < 0 or not callable(clock)):
            raise ValueError("Log veto needs the expected character/server and measurement generation")
        self.cancel_generation = cancel_generation
        self.clock = clock
        self.tail = NonReplayingLogTail(log_path, max_bytes=max_bytes)
        self._last_finished = None
        self._last_log_time = None
        self._line_seq = 0
        self._latched = None
        self._poll(baseline=True)

    def poll(self) -> LogVetoObservation:
        return self._poll(baseline=False)

    def _poll(self, *, baseline):
        if self._latched is not None:
            return self._latched
        began = ended = None
        reason = None
        continuity = True
        try:
            began = self.clock()
            if (not _finite(began) or (self._last_finished is not None
                                      and began < self._last_finished)):
                raise ValueError("invalid or backward observation clock")
            lines, reset = self.tail.poll()
            if self.tail.identity is None:
                reason = "log unavailable"
            elif reset and not baseline:
                reason = "log continuity reset"
            elif self.tail.partial or (baseline and self.tail.anchor
                                      and not self.tail.anchor.endswith(b"\n")):
                reason = "incomplete log line"
            if reason is not None:
                continuity = False
            else:
                for line in lines:
                    self._line_seq += 1
                    parsed = None if "\ufffd" in line else parse_client_log_line(line)
                    if parsed is None:
                        reason, continuity = "unparsed log line", False
                        break
                    log_time, body = parsed
                    if self._last_log_time is not None and log_time < self._last_log_time:
                        reason, continuity = "log time moved backward", False
                        break
                    self._last_log_time = log_time
                    reason = classify_log_veto(body)
                    if reason is not None:
                        break
            ended = self.clock()
            if not _finite(ended) or ended < began:
                raise ValueError("invalid or backward observation clock")
        except Exception:
            reason, continuity = "log read or observation clock failed", False
        observation = LogVetoObservation(
            began if _finite(began) else None, ended if _finite(ended) else None,
            self.cancel_generation, self.tail.epoch, self._line_seq, continuity,
            reason, self._last_log_time)
        if reason is not None:
            self._latched = observation
        else:
            self._last_finished = ended
        return observation
