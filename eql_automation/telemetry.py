"""Read-only log event tracking and hourly status rendering.

The incremental file reader and level-message parser come from the October
Paladin/Cleric tool. XP, camp, and position require explicit trusted telemetry;
this module never invents those values from unrelated log text.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
import re
import time

from .prior_rotation_core import LogTail, level_from_message, message_body


DEATH = re.compile(r"^(?:You have been slain |You died|You die[.!])")
ZONE = re.compile(r"^(?:LOADING, PLEASE WAIT|You have entered )")


@dataclass
class RunState:
    level: int | None = None
    xp: int | None = None
    deaths: int = 0
    camp: str | None = None
    zone: str | None = None
    blocker: str = "Private server endpoint/client configuration not verified"
    next_step: str = "Continue offline validation; verify private target before client input"
    xp_samples: deque[tuple[float, int]] = field(default_factory=deque)
    level_progress_level: int | None = None
    level_progress_fraction: float | None = None
    level_progress_samples: deque[tuple[float, float]] = field(default_factory=deque)

    def observe_log(self, line: str) -> None:
        level = level_from_message(line)
        if level is not None:
            if level != self.level:
                self.level_progress_level = None
                self.level_progress_fraction = None
                self.level_progress_samples.clear()
            self.level = level
        body = message_body(line)
        if DEATH.match(body):
            self.deaths += 1
        if ZONE.match(body):
            self.zone = body

    def observe_xp(self, total_xp: int, now: float | None = None) -> None:
        """Accept a verified cumulative XP value supplied by an adapter."""

        if (not isinstance(total_xp, int) or isinstance(total_xp, bool) or
                total_xp < 0):
            raise ValueError("Cumulative raw XP must be a nonnegative integer")
        now = time.monotonic() if now is None else now
        if self.xp is not None and total_xp < self.xp:
            self.xp_samples.clear()  # A reset or changed character needs a new rate window.
        self.xp = total_xp
        self.xp_samples.append((now, total_xp))
        while len(self.xp_samples) > 1 and now - self.xp_samples[0][0] > 3600:
            self.xp_samples.popleft()

    @property
    def xp_per_hour(self) -> float | None:
        if len(self.xp_samples) < 2:
            return None
        start_time, start_xp = self.xp_samples[0]
        end_time, end_xp = self.xp_samples[-1]
        elapsed = end_time - start_time
        return max(0.0, (end_xp - start_xp) * 3600 / elapsed) if elapsed > 0 else None

    def observe_level_progress(self, *, level: int, fraction: float | None,
                               normal_xp_allocation_verified: bool,
                               now: float | None = None) -> bool:
        """Track percent of this level; never substitute it for cumulative XP."""
        if not isinstance(level, int) or isinstance(level, bool) or not 1 <= level <= 50:
            raise ValueError("Confirmed level must be 1–50")
        if fraction is not None and (
                not isinstance(fraction, (int, float)) or isinstance(fraction, bool) or
                not isfinite(fraction) or not 0 <= fraction <= 1):
            raise ValueError("Level progress fraction must be between 0 and 1")
        now = time.monotonic() if now is None else now
        if not isinstance(now, (int, float)) or isinstance(now, bool) or not isfinite(now):
            raise ValueError("Progress sample time must be finite")
        if (self.level != level or fraction is None or
                normal_xp_allocation_verified is not True):
            self.level_progress_level = None
            self.level_progress_fraction = None
            self.level_progress_samples.clear()
            return False
        if self.level_progress_samples:
            previous_time, previous_fraction = self.level_progress_samples[-1]
            if now <= previous_time:
                self.level_progress_level = None
                self.level_progress_fraction = None
                self.level_progress_samples.clear()
                return False
            if fraction < previous_fraction:
                self.level_progress_samples.clear()
        self.level_progress_level = level
        self.level_progress_fraction = fraction
        self.level_progress_samples.append((now, fraction))
        while (len(self.level_progress_samples) > 1 and
               now - self.level_progress_samples[0][0] > 3600):
            self.level_progress_samples.popleft()
        return True

    @property
    def level_progress_percent_per_hour(self) -> float | None:
        if self.level_progress_level != self.level or len(self.level_progress_samples) < 2:
            return None
        start_time, start_fraction = self.level_progress_samples[0]
        end_time, end_fraction = self.level_progress_samples[-1]
        elapsed = end_time - start_time
        return (max(0.0, end_fraction - start_fraction) * 360000 / elapsed
                if elapsed > 0 else None)

class StatusWriter:
    def __init__(self, path: Path, interval: float = 3600.0) -> None:
        self.path = path
        self.interval = interval
        self.last_write: float | None = None

    def maybe_write(self, state: RunState, now: float | None = None,
                    force: bool = False) -> bool:
        now = time.monotonic() if now is None else now
        if not force and self.last_write is not None and now - self.last_write < self.interval:
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(render_status(state))
        temporary.replace(self.path)
        self.last_write = now
        return True


def render_status(state: RunState) -> str:
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    rate = state.xp_per_hour
    level_rate = state.level_progress_percent_per_hour
    level_progress = (state.level_progress_fraction
                      if state.level_progress_level == state.level else None)
    return (
        f"# STATUS\n\nUpdated {updated}.\n\n"
        f"- Level: {state.level if state.level is not None else 'n/a'}\n"
        f"- XP: {state.xp if state.xp is not None else 'n/a'}\n"
        f"- XP/hour: {f'{rate:.1f}' if rate is not None else 'n/a'}\n"
        f"- Current-level XP progress: {f'{level_progress * 100:.1f}%' if level_progress is not None else 'n/a'}\n"
        f"- Current-level progress/hour: {f'{level_rate:.1f} percentage points/hour' if level_rate is not None else 'n/a'}\n"
        f"- Deaths: {state.deaths}\n"
        f"- Camp: {state.camp or 'none'}\n"
        f"- Zone: {state.zone or 'unknown'}\n"
        f"- Current blocker: {state.blocker}\n"
        f"- Next step: {state.next_step}\n"
    )


class ClientLogReader:
    """Tail only new lines, preserving the prior tool's no-history behavior."""

    def __init__(self, path: Path, state: RunState) -> None:
        self.tail = LogTail(path)
        self.state = state
        # If the file does not exist yet, its first content is new activity,
        # not historical content to skip. The prior LogTail defaults to
        # skipping on its first successful stat().
        if not path.exists():
            self.tail.initialized = True
        self.tail.poll()

    def poll(self) -> list[str]:
        lines = self.tail.poll()
        for line in lines:
            self.state.observe_log(line)
        return lines
