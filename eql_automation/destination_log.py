"""Read-only evidence of the first timely /location after a named zone entry.

This works when a watcher starts while the owner is already in the source
zone. It does not infer the source zone, the crossing method, or exact spawn.
No game input is sent.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from pathlib import Path
import re
import time

from .location_log import (NonReplayingLogTail, parse_client_log_line,
                           parse_raw_location, unique_client_zone_ids)


_ENTERED = re.compile(r"^You have entered (.+)\.$")
_LOADING = "LOADING, PLEASE WAIT..."


@dataclass(frozen=True)
class DestinationArrival:
    zone_id: int
    zone_display_name: str
    raw_location: tuple[float, float, float]
    loading_log_time: datetime
    entered_log_time: datetime
    location_log_time: datetime
    received_monotonic: float
    loading_line_seq: int
    entered_line_seq: int
    location_line_seq: int
    log_epoch: int
    preloading_raw_location: tuple[float, float, float] | None = None
    preloading_log_time: datetime | None = None
    preloading_line_seq: int | None = None
    source_zone_verified: bool = False
    crossing_method_verified: bool = False
    spawn_coordinate_verified: bool = False
    route_accepted: bool = False
    real_client_movement_accepted: bool = False


class DestinationTracker:
    """Recognize loading, exact entry, then the first timely location line."""

    def __init__(self, destination: str, zone_id: int, *,
                 max_preloading_fix_age: float = 30.0,
                 max_loading_seconds: float = 60.0,
                 max_location_delay: float = 30.0) -> None:
        if (not isinstance(destination, str) or not destination or
                not isinstance(zone_id, int) or isinstance(zone_id, bool) or zone_id < 0 or
                not isinstance(max_preloading_fix_age, (int, float)) or
                isinstance(max_preloading_fix_age, bool) or
                not isfinite(max_preloading_fix_age) or max_preloading_fix_age <= 0 or
                not isinstance(max_loading_seconds, (int, float)) or
                isinstance(max_loading_seconds, bool) or
                not isfinite(max_loading_seconds) or max_loading_seconds <= 0 or
                not isinstance(max_location_delay, (int, float)) or
                isinstance(max_location_delay, bool) or
                not isfinite(max_location_delay) or max_location_delay <= 0):
            raise ValueError("Destination watcher needs an exact zone and finite windows")
        self.destination = destination
        self.zone_id = zone_id
        self.max_preloading_fix_age = float(max_preloading_fix_age)
        self.max_loading_seconds = float(max_loading_seconds)
        self.max_location_delay = float(max_location_delay)
        self.epoch: int | None = None
        self.seq = 0
        self.last_log_time: datetime | None = None
        self.loading_time: datetime | None = None
        self.loading_seq: int | None = None
        self.entered_time: datetime | None = None
        self.entered_seq: int | None = None
        self.latest_unzoned_location: tuple[tuple[float, float, float], datetime, int] | None = None
        self.preloading_location: tuple[tuple[float, float, float], datetime, int] | None = None

    def _clear_pending(self) -> None:
        self.loading_time = self.loading_seq = None
        self.entered_time = self.entered_seq = None
        self.latest_unzoned_location = None
        self.preloading_location = None

    def invalidate(self) -> None:
        self._clear_pending()
        self.last_log_time = None

    def consume(self, line: str, *, received_monotonic: float,
                log_epoch: int) -> DestinationArrival | None:
        if (not isinstance(received_monotonic, (int, float)) or
                isinstance(received_monotonic, bool) or
                not isfinite(received_monotonic) or
                not isinstance(log_epoch, int) or isinstance(log_epoch, bool) or
                log_epoch < 0):
            self.invalidate()
            raise ValueError("Destination log clock and epoch must be valid")
        if self.epoch != log_epoch:
            self.invalidate()
            self.epoch = log_epoch
        self.seq += 1
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
            previous = self.latest_unzoned_location
            self.preloading_location = (
                previous if previous is not None and
                0 <= (at - previous[1]).total_seconds() <= self.max_preloading_fix_age
                else None)
            self.latest_unzoned_location = None
            self.loading_time = at
            self.loading_seq = self.seq
            self.entered_time = self.entered_seq = None
            return None
        if body.startswith("LOADING, PLEASE WAIT"):
            self.invalidate()
            return None
        entered = _ENTERED.fullmatch(body)
        if entered is not None:
            valid = (entered.group(1) == self.destination and
                     self.loading_time is not None and
                     0 <= (at - self.loading_time).total_seconds() <=
                     self.max_loading_seconds)
            if valid:
                self.entered_time = at
                self.entered_seq = self.seq
            else:
                self._clear_pending()
            return None
        if body.startswith("You have entered "):
            self.invalidate()
            return None
        if body.startswith("Your Location is "):
            raw = parse_raw_location(body)
            if self.loading_time is None and self.entered_time is None:
                self.latest_unzoned_location = ((raw, at, self.seq)
                                                if raw is not None else None)
                return None
            loading_time, loading_seq = self.loading_time, self.loading_seq
            entered_time, entered_seq = self.entered_time, self.entered_seq
            preloading = self.preloading_location
            self._clear_pending()  # Only the first location after entry may count.
            if (raw is None or loading_time is None or loading_seq is None or
                    entered_time is None or entered_seq is None or
                    not 0 <= (at - entered_time).total_seconds() <=
                    self.max_location_delay):
                return None
            return DestinationArrival(self.zone_id, self.destination, raw,
                                      loading_time, entered_time, at,
                                      float(received_monotonic), loading_seq,
                                      entered_seq, self.seq, log_epoch,
                                      preloading[0] if preloading else None,
                                      preloading[1] if preloading else None,
                                      preloading[2] if preloading else None)
        return None


class DestinationLogReader:
    """Watch only newly appended lines in one exact owner-selected log."""

    def __init__(self, log_path: Path, zone_names_path: Path, *,
                 expected_character: str, expected_server: str,
                 destination: str) -> None:
        if log_path.name != f"eqlog_{expected_character}_{expected_server}.txt":
            raise ValueError("Destination log does not match expected character/server")
        zone_ids, _ambiguous = unique_client_zone_ids(zone_names_path)
        if destination not in zone_ids:
            raise ValueError("Destination name is not unique in copied client zone data")
        self.tracker = DestinationTracker(destination, zone_ids[destination])
        self.tail = NonReplayingLogTail(log_path)
        self.tail.poll()
        self.last_poll_monotonic: float | None = None

    def poll(self, *, now: float | None = None) -> list[DestinationArrival]:
        received = time.monotonic() if now is None else now
        if (not isinstance(received, (int, float)) or
                isinstance(received, bool) or not isfinite(received) or
                self.last_poll_monotonic is not None and
                received < self.last_poll_monotonic):
            self.tracker.invalidate()
            raise ValueError("Destination poll clock must be finite and monotonic")
        self.last_poll_monotonic = received
        try:
            lines, reset = self.tail.poll()
        except (OSError, ValueError):
            self.tracker.invalidate()
            raise
        if reset:
            self.tracker.invalidate()
        arrivals = []
        for line in lines:
            arrival = self.tracker.consume(
                line, received_monotonic=received, log_epoch=self.tail.epoch)
            if arrival is not None:
                arrivals.append(arrival)
        return arrivals
