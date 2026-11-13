"""Read-only log event tracking and hourly status rendering.

The incremental file reader and level-message parser come from the October
Paladin/Cleric tool. XP, camp, and position require explicit trusted telemetry;
this module never invents those values from unrelated log text.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
    blocker: str = "No authorized live automation path"
    next_step: str = "Continue offline validation; obtain Daybreak authorization for live tests"
    xp_samples: deque[tuple[float, int]] = field(default_factory=deque)

    def observe_log(self, line: str) -> None:
        level = level_from_message(line)
        if level is not None:
            self.level = level
        body = message_body(line)
        if DEATH.match(body):
            self.deaths += 1
        if ZONE.match(body):
            self.zone = body

    def observe_xp(self, total_xp: int, now: float | None = None) -> None:
        """Accept a verified cumulative XP value supplied by an adapter."""

        if total_xp < 0:
            raise ValueError("XP must be nonnegative")
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
    return (
        f"# STATUS\n\nUpdated {updated}.\n\n"
        f"- Level: {state.level if state.level is not None else 'n/a'}\n"
        f"- XP: {state.xp if state.xp is not None else 'n/a'}\n"
        f"- XP/hour: {f'{rate:.1f}' if rate is not None else 'n/a'}\n"
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
