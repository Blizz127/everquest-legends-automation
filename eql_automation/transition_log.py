"""Read-only, non-replaying evidence of a client-reported zone change.

The first /loc after entering a zone is an observed position, never an exact
spawn point: the character might have moved before the command was logged.
This module sends no command or game input and never accepts a travel edge.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from pathlib import Path
import re
import time

from .location_log import (
    NonReplayingLogTail, parse_client_log_line, parse_raw_location,
    unique_client_zone_ids,
)


_ENTERED = re.compile(r"^You have entered (.+)\.$")
_LOADING = "LOADING, PLEASE WAIT..."


@dataclass(frozen=True)
class TransitionFix:
    zone_id: int
    zone: str
    raw_location: tuple[float, float, float]
    log_time: datetime
    received_monotonic: float
    line_seq: int
    log_epoch: int
    zone_generation: int


@dataclass(frozen=True)
class ObservedTransition:
    source_fix: TransitionFix
    destination_fix: TransitionFix
    loading_time: datetime
    entered_time: datetime
    loading_line_seq: int
    entered_line_seq: int
    log_epoch: int
    route_accepted: bool = False
    spawn_coordinate_verified: bool = False
    real_client_movement_accepted: bool = False


class TransitionTracker:
    """Consume only ordered new log lines from one trusted character file."""

    def __init__(self, zone_ids: dict[str, int], *,
                 max_source_fix_age: float = 30.0,
                 max_destination_fix_delay: float = 30.0,
                 max_loading_seconds: float = 60.0) -> None:
        if (not isinstance(zone_ids, dict) or
                any(not isinstance(name, str) or not name or
                    not isinstance(identifier, int) or isinstance(identifier, bool) or
                    identifier < 0 for name, identifier in zone_ids.items()) or
                any(not isinstance(value, (int, float)) or isinstance(value, bool) or
                    not isfinite(value) or value <= 0 for value in
                    (max_source_fix_age, max_destination_fix_delay,
                     max_loading_seconds))):
            raise ValueError("Transition tracker requires exact zone IDs and finite windows")
        self.zone_ids = dict(zone_ids)
        self.max_source_fix_age = float(max_source_fix_age)
        self.max_destination_fix_delay = float(max_destination_fix_delay)
        self.max_loading_seconds = float(max_loading_seconds)
        self.log_epoch: int | None = None
        self.line_seq = 0
        self.zone_generation = 0
        self.zone: str | None = None
        self.latest_fix: TransitionFix | None = None
        self.last_log_time: datetime | None = None
        self.last_received_monotonic: float | None = None
        self.pending_source: TransitionFix | None = None
        self.loading_time: datetime | None = None
        self.loading_line_seq: int | None = None
        self.entered_time: datetime | None = None
        self.entered_line_seq: int | None = None

    def invalidate(self) -> None:
        self.zone_generation += 1
        self.zone = None
        self.latest_fix = None
        self.pending_source = None
        self.loading_time = None
        self.loading_line_seq = None
        self.entered_time = None
        self.entered_line_seq = None
        self.last_log_time = None

    def consume(self, line: str, *, received_monotonic: float,
                log_epoch: int) -> ObservedTransition | None:
        if (not isinstance(received_monotonic, (int, float)) or
                isinstance(received_monotonic, bool) or
                not isfinite(received_monotonic) or
                not isinstance(log_epoch, int) or isinstance(log_epoch, bool) or
                log_epoch < 0):
            self.invalidate()
            raise ValueError("Transition log clock and epoch must be valid")
        if (self.last_received_monotonic is not None and
                received_monotonic < self.last_received_monotonic):
            self.invalidate()
            self.last_received_monotonic = received_monotonic
            return None
        self.last_received_monotonic = received_monotonic
        if self.log_epoch != log_epoch:
            self.invalidate()
            self.log_epoch = log_epoch
        self.line_seq += 1
        parsed = parse_client_log_line(line)
        if parsed is None:
            if any(token in line for token in (_LOADING, "You have entered ",
                                              "Your Location is ")):
                self.invalidate()
            return None
        at, body = parsed
        if self.last_log_time is not None and at < self.last_log_time:
            self.invalidate()
            return None
        self.last_log_time = at
        if body == _LOADING:
            source = self.latest_fix
            fresh = (source is not None and self.zone == source.zone and
                     0 <= (at - source.log_time).total_seconds() <= self.max_source_fix_age)
            self.pending_source = source if fresh else None
            self.loading_time = at if fresh else None
            self.loading_line_seq = self.line_seq if fresh else None
            self.entered_time = None
            self.entered_line_seq = None
            self.zone = None
            self.latest_fix = None
            self.zone_generation += 1
            return None
        if body.startswith("LOADING, PLEASE WAIT"):
            self.invalidate()
            return None
        entered = _ENTERED.fullmatch(body)
        if entered is not None:
            name = entered.group(1)
            valid = (name in self.zone_ids and self.pending_source is not None and
                     self.loading_time is not None and
                     name != self.pending_source.zone and
                     0 <= (at - self.loading_time).total_seconds() <= self.max_loading_seconds)
            self.zone = name if name in self.zone_ids else None
            self.latest_fix = None
            self.zone_generation += 1
            if valid:
                self.entered_time = at
                self.entered_line_seq = self.line_seq
            else:
                self.pending_source = None
                self.loading_time = None
                self.loading_line_seq = None
                self.entered_time = None
                self.entered_line_seq = None
            return None
        if body.startswith("You have entered "):
            self.invalidate()
            return None
        raw = parse_raw_location(body)
        if raw is None:
            if body.startswith("Your Location is "):
                self.invalidate()
            return None
        if self.zone is None:
            self.invalidate()  # A location during loading breaks event pairing.
            return None
        fix = TransitionFix(self.zone_ids[self.zone], self.zone, raw, at,
                            float(received_monotonic), self.line_seq,
                            log_epoch, self.zone_generation)
        self.latest_fix = fix
        if self.pending_source is None or self.entered_time is None:
            return None
        source = self.pending_source
        loading_time = self.loading_time
        loading_line_seq = self.loading_line_seq
        entered_time = self.entered_time
        entered_line_seq = self.entered_line_seq
        self.pending_source = None  # Only the first destination fix can pair.
        self.loading_time = self.loading_line_seq = None
        self.entered_time = self.entered_line_seq = None
        if (fix.zone == source.zone or
                not 0 <= (at - entered_time).total_seconds() <=
                self.max_destination_fix_delay):
            return None
        return ObservedTransition(source, fix, loading_time, entered_time,
                                  loading_line_seq, entered_line_seq, log_epoch)


class TransitionLogReader:
    """Tail one expected character log; existing bytes are history."""

    def __init__(self, log_path: Path, zone_names_path: Path, *,
                 expected_character: str, expected_server: str,
                 fresh_test_character: bool = False) -> None:
        if log_path.name != f"eqlog_{expected_character}_{expected_server}.txt":
            raise ValueError("Transition log does not match expected character/server")
        if not isinstance(fresh_test_character, bool):
            raise ValueError("Fresh test-character option must be boolean")
        zone_ids, _ambiguous = unique_client_zone_ids(zone_names_path)
        self.tracker = TransitionTracker(zone_ids)
        self.tail = NonReplayingLogTail(
            log_path, include_first_created_file=fresh_test_character)
        self.tail.poll()  # Never treat a pre-existing log as fresh traversal.

    def poll(self, *, now: float | None = None) -> list[ObservedTransition]:
        received = time.monotonic() if now is None else now
        if (not isinstance(received, (int, float)) or isinstance(received, bool) or
                not isfinite(received) or
                self.tracker.last_received_monotonic is not None and
                received < self.tracker.last_received_monotonic):
            self.tracker.invalidate()
            raise ValueError("Transition poll clock must be finite and monotonic")
        try:
            lines, reset = self.tail.poll()
        except (OSError, ValueError):
            self.tracker.invalidate()
            raise
        if reset:
            self.tracker.invalidate()
        observations = []
        for line in lines:
            transition = self.tracker.consume(
                line, received_monotonic=received, log_epoch=self.tail.epoch)
            if transition is not None:
                observations.append(transition)
        return observations
