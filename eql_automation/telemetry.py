"""Read-only log event tracking and hourly status rendering.

The level-message parser comes from the October Paladin/Cleric tool. The
incremental reader now skips replacement history instead of replaying it.
XP, camp, and position require explicit trusted telemetry; this module never
invents those values from unrelated log text.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
import re
import time

from .location_log import NonReplayingLogTail
from .prior_rotation_core import level_from_message, message_body


DEATH = re.compile(r"^(?:You have been slain |You died|You die[.!])")
ZONE = re.compile(r"^(?:LOADING, PLEASE WAIT|You have entered )")
# Observed owner log suffix; bonus/penalty and level-loss templates are in
# the installed eqstr_us.txt (138, 14541/14542, 442/443). These are awards,
# not total XP, current-level fraction, net progress or allocation evidence.
LOG_GAIN = re.compile(r"You gain experience(?: \(with a (?:bonus|penalty)\))?! \(([0-9]{1,6}(?:\.[0-9]{1,6})?)%\)")
LEVEL_LOSS = re.compile(r"You LOST (?:a level|[0-9]+ levels)! You are now level ([0-9]+)!")
GAIN_SCALE = 1_000_000
# Exact client messages also recognized by the pinned November inventory tool.
# One failed loot item does not prove that every bag slot is full.
LOOT_NO_ROOM = frozenset({
    "You cannot loot this item no room in your inventory.",
    "You cannot loot this entire stack of items, no room in your inventory.",
})
FOOD_DRINK_WARNINGS = {
    "You are thirsty.": (None, "low"),
    "You and your mount are thirsty.": (None, "low"),
    "You are hungry.": ("low", None),
    "You and your mount are hungry.": ("low", None),
    "You are out of food.": ("out", None),
    "You are low on food.": ("low", None),
    "You are out of drink.": (None, "out"),
    "You are out of food and drink.": ("out", "out"),
    "You are out of drink and low on food.": ("low", "out"),
    "You are low on drink.": (None, "low"),
    "You are out of food and low on drink.": ("out", "low"),
    "You are low on food and drink.": ("low", "low"),
}


@dataclass
class RunState:
    level: int | None = None
    xp: int | None = None
    deaths: int | None = 0
    camp: str | None = None
    zone: str | None = None
    blocker: str = "Private server endpoint/client configuration not verified"
    next_step: str = "Continue offline validation; verify private target before client input"
    xp_samples: deque[tuple[float, int]] = field(default_factory=deque)
    level_progress_level: int | None = None
    level_progress_fraction: float | None = None
    level_progress_samples: deque[tuple[float, float]] = field(default_factory=deque)
    loot_space_warning: bool | None = None
    food_status: str | None = None
    drink_status: str | None = None
    log_gain_started_at: float | None = None
    log_gain_as_of: float | None = None
    log_gain_level: int | None = None
    log_gain_camp: str | None = None
    log_gain_zone: str | None = None
    log_gain_micropoints: int = 0
    log_gain_events: int = 0

    def clear_log_gain_window(self) -> None:
        self.log_gain_started_at = self.log_gain_as_of = None
        self.log_gain_level = None
        self.log_gain_camp = None
        self.log_gain_zone = None
        self.log_gain_micropoints = self.log_gain_events = 0

    def advance_log_clock(self, now: float | None = None) -> None:
        """Advance the continuous receipt window even when no new lines arrive."""
        now = time.monotonic() if now is None else now
        if (not isinstance(now,(int,float)) or isinstance(now,bool) or not isfinite(now)):
            self.clear_log_gain_window()
            raise ValueError('Log gain window time must be finite')
        if type(self.level) is not int or not 1 <= self.level <= 50:
            self.clear_log_gain_window()
            return
        if (self.log_gain_started_at is None or self.log_gain_level != self.level
                or self.log_gain_camp != self.camp or self.log_gain_zone != self.zone
                or (self.log_gain_as_of is not None and now < self.log_gain_as_of)):
            self.clear_log_gain_window()
            self.log_gain_started_at = now
            self.log_gain_level = self.level
            self.log_gain_camp = self.camp
            self.log_gain_zone = self.zone
        self.log_gain_as_of = now

    @property
    def client_reported_gain_percent_per_hour(self) -> float | None:
        """Gross awards per receipt-window hour; no inferred event timestamps."""
        if (self.log_gain_level != self.level or self.log_gain_camp != self.camp or self.log_gain_zone != self.zone
                or self.log_gain_started_at is None or self.log_gain_as_of is None):
            return None
        elapsed = self.log_gain_as_of - self.log_gain_started_at
        return self.log_gain_micropoints / GAIN_SCALE * 3600 / elapsed if elapsed > 0 else None

    def observe_log(self, line: str, *, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        self.advance_log_clock(now)
        body = message_body(line)
        level = level_from_message(line)
        loss = LEVEL_LOSS.fullmatch(body)
        if loss:
            level = int(loss[1]) if 1 <= int(loss[1]) <= 50 else None
            self.level = None  # An unsupported loss cannot retain the old level.
            self.level_progress_level = self.level_progress_fraction = None
            self.level_progress_samples.clear()
        if level is not None:
            if level != self.level:
                self.level_progress_level = None
                self.level_progress_fraction = None
                self.level_progress_samples.clear()
            self.level = level
        if ZONE.match(body):
            self.zone = body
        if level is not None or loss or DEATH.match(body) or ZONE.match(body):
            self.clear_log_gain_window()
            self.advance_log_clock(now)
        if DEATH.match(body) and self.deaths is not None:
            self.deaths += 1
        gain = LOG_GAIN.fullmatch(body)
        if gain and self.log_gain_started_at is not None:
            whole,_,fraction = gain[1].partition('.')
            self.log_gain_micropoints += int(whole)*GAIN_SCALE + int(fraction.ljust(6,'0'))
            self.log_gain_events += 1
        if body in LOOT_NO_ROOM:
            self.loot_space_warning = True
        food, drink = FOOD_DRINK_WARNINGS.get(body, (None, None))
        for kind, warning in (("food", food), ("drink", drink)):
            if warning is not None:
                previous = getattr(self, f"{kind}_status")
                if warning == "out" or previous != "out":
                    setattr(self, f"{kind}_status", warning)

    def observe_supply_check(self, *, verified: bool,
                             loot_item_fits: bool | None = None,
                             food_count: int | None = None,
                             drink_count: int | None = None) -> None:
        """Accept an explicit, fresh inventory observation; log events cannot clear warnings."""
        if verified is not True or (loot_item_fits is None and
                                    food_count is None and drink_count is None):
            raise ValueError("A verified supply observation is required")
        if loot_item_fits is not None and not isinstance(loot_item_fits, bool):
            raise ValueError("Loot fit must be boolean")
        for count in (food_count, drink_count):
            if count is not None and (not isinstance(count, int) or
                                      isinstance(count, bool) or count < 0):
                raise ValueError("Supply count must be a nonnegative integer")
        if loot_item_fits is not None:
            self.loot_space_warning = not loot_item_fits
        if food_count is not None:
            self.food_status = "sufficient" if food_count > 0 else "out"
        if drink_count is not None:
            self.drink_status = "sufficient" if drink_count > 0 else "out"

    def invalidate_log_session(self) -> None:
        """Unknown continuity cannot retain level, XP, camp, or death count."""
        self.level = None
        self.xp = None
        self.xp_samples.clear()
        self.level_progress_level = None
        self.level_progress_fraction = None
        self.level_progress_samples.clear()
        self.zone = None
        self.camp = None
        self.deaths = None
        self.clear_log_gain_window()
        self.loot_space_warning = None
        self.food_status = None
        self.drink_status = None
        self.blocker = "Client log reset or backlog; run identity is unverified"
        self.next_step = "Reconfirm the fresh character and current client state"

    def observe_xp(self, total_xp: int, now: float | None = None) -> None:
        """Accept a verified cumulative XP value supplied by an adapter."""

        if (not isinstance(total_xp, int) or isinstance(total_xp, bool) or
                total_xp < 0):
            raise ValueError("Cumulative raw XP must be a nonnegative integer")
        now = time.monotonic() if now is None else now
        if (not isinstance(now, (int, float)) or isinstance(now, bool) or
                not isfinite(now)):
            raise ValueError("Cumulative XP sample time must be finite")
        if self.xp_samples and now <= self.xp_samples[-1][0]:
            self.xp_samples.clear()
        if self.xp is not None and total_xp < self.xp:
            self.xp_samples.clear()  # A reset or changed character needs a new rate window.
            self.clear_log_gain_window()
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
    reported_rate = state.client_reported_gain_percent_per_hour
    level_progress = (state.level_progress_fraction
                      if state.level_progress_level == state.level else None)
    return (
        f"# STATUS\n\nUpdated {updated}.\n\n"
        f"- Level: {state.level if state.level is not None else 'n/a'}\n"
        f"- XP: {state.xp if state.xp is not None else 'n/a'}\n"
        f"- XP/hour: {f'{rate:.1f}' if rate is not None else 'n/a'}\n"
        f"- Current-level XP progress: {f'{level_progress * 100:.1f}%' if level_progress is not None else 'n/a'}\n"
        f"- Current-level progress/hour: {f'{level_rate:.1f} percentage points/hour' if level_rate is not None else 'n/a'}\n"
        f"- Client-reported gross XP gain: {f'{reported_rate:.3f} percentage points/hour' if reported_rate is not None else 'n/a'} (since this observed level/log window began; not net XP)\n"
        f"- Deaths: {state.deaths if state.deaths is not None else 'n/a'}\n"
        f"- Camp: {state.camp or 'none'}\n"
        f"- Zone: {state.zone or 'unknown'}\n"
        f"- Loot space warning: {state.loot_space_warning if state.loot_space_warning is not None else 'unknown'}\n"
        f"- Food status: {state.food_status or 'unknown'}\n"
        f"- Drink status: {state.drink_status or 'unknown'}\n"
        f"- Current blocker: {state.blocker}\n"
        f"- Next step: {state.next_step}\n"
    )


class ClientLogReader:
    """Tail complete new lines; never replay replacement or truncated history."""

    def __init__(self, path: Path, state: RunState, *,
                 fresh_test_character: bool = False, now: float | None = None) -> None:
        if not isinstance(fresh_test_character, bool):
            raise ValueError("Fresh test character flag must be boolean")
        self.tail = NonReplayingLogTail(
            path, include_first_created_file=fresh_test_character)
        self.state = state
        self.tail.poll()  # Existing bytes are history.
        self.state.clear_log_gain_window()
        if self.tail.identity is not None:
            self.state.advance_log_clock(now)

    def poll(self, *, now: float | None = None) -> list[str]:
        now = time.monotonic() if now is None else now
        if (not isinstance(now,(int,float)) or isinstance(now,bool) or not isfinite(now)):
            self.state.clear_log_gain_window()
            raise ValueError('Log gain window time must be finite')
        lines, reset = self.tail.poll()
        if reset:
            self.state.invalidate_log_session()
        if self.tail.identity is None:
            self.state.clear_log_gain_window()
        else:
            self.state.advance_log_clock(now)
        for line in lines:
            self.state.observe_log(line,now=now)
        return lines
