"""Read-only, non-replaying parser for client /loc and zone log messages.

Coordinates stay in the log's raw order. This module never sends /loc, maps
coordinates into WLD space, or supplies a live navigation observation.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from pathlib import Path
import os
import re
import stat
import time



_TIMESTAMPED = re.compile(r"^\[([^\]]+)\] (.+)$")
_NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
_LOCATION = re.compile(
    rf"^Your Location is ({_NUMBER}), ({_NUMBER}), ({_NUMBER})$")
_ENTERED = re.compile(r"^You have entered (.+)\.$")


def parse_client_log_line(line: str) -> tuple[datetime, str] | None:
    """Return a local, timezone-free client timestamp and exact message body."""
    match = _TIMESTAMPED.fullmatch(line.strip())
    if match is None:
        return None
    try:
        source_time = datetime.strptime(match.group(1), "%a %b %d %H:%M:%S %Y")
    except ValueError:
        return None
    return source_time, match.group(2)


def parse_raw_location(body: str) -> tuple[float, float, float] | None:
    """Parse the three printed numbers without assuming their WLD axes."""
    match = _LOCATION.fullmatch(body)
    if match is None:
        return None
    raw = tuple(float(value) for value in match.groups())
    return raw if all(isfinite(value) for value in raw) else None


def unique_client_zone_ids(zone_names_path: Path) -> tuple[dict[str, int], set[str]]:
    """Resolve only exact, unambiguous display names from copied client data."""
    return unique_zone_ids_from_text(zone_names_path.read_text(encoding="latin-1"))


def unique_zone_ids_from_text(text: str) -> tuple[dict[str, int], set[str]]:
    """Apply the same lookup to an already pinned immutable source snapshot."""
    from .client_ingest import parse_zone_names
    by_name: dict[str, set[int]] = defaultdict(set)
    rows = parse_zone_names(text)
    for row in rows:
        by_name[row["name"]].add(row["id"])
    unique = {name: next(iter(ids)) for name, ids in by_name.items() if len(ids) == 1}
    ambiguous = {name for name, ids in by_name.items() if len(ids) > 1}
    return unique, ambiguous


class NonReplayingLogTail:
    """Read appended complete lines; drop history after a reset or backlog."""

    def __init__(self, path: Path, *, max_bytes: int = 512 * 1024,
                 include_first_created_file: bool = False) -> None:
        if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        if not isinstance(include_first_created_file, bool):
            raise ValueError("First-created-file option must be boolean")
        self.path = path
        self.max_bytes = max_bytes
        self.include_first_created_file = include_first_created_file
        self.awaiting_first_creation = False
        self.initialized = False
        self.identity: tuple[int, int] | None = None
        self.position = 0
        self.partial = b""
        self.anchor = b""
        self.epoch = 0

    def _skip_to_end(self, source, size: int, identity: tuple[int, int]) -> None:
        self.identity = identity
        self.position = size
        self.partial = b""
        source.seek(max(0, size - 128))
        self.anchor = source.read(min(size, 128))
        self.epoch += 1

    def poll(self) -> tuple[list[str], bool]:
        """Return (new complete lines, reset); no replacement history is read."""
        try:
            source = self.path.open("rb")
        except FileNotFoundError:
            if not self.initialized and self.include_first_created_file:
                self.awaiting_first_creation = True
            reset = self.identity is not None
            self.identity = None
            self.position = 0
            self.partial = b""
            self.anchor = b""
            self.initialized = True
            if reset:
                self.epoch += 1
            return [], reset
        with source:
            metadata = os.fstat(source.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError("Location log source must be a regular file")
            identity = (metadata.st_dev, metadata.st_ino)
            # Only a path absent at first observation may begin at byte zero.
            # This is for a fresh test-character log created after startup;
            # replacements and an existing file always skip their history.
            first_created = self.awaiting_first_creation and self.identity is None
            self.awaiting_first_creation = False
            reset = (not self.initialized or identity != self.identity or
                     metadata.st_size < self.position or
                     metadata.st_size - self.position > self.max_bytes)
            if first_created and metadata.st_size <= self.max_bytes:
                reset = False
                self.identity = identity
                self.position = 0
                self.partial = b""
                self.anchor = b""
                self.epoch += 1
            self.initialized = True
            if not reset and self.anchor:
                source.seek(self.position - len(self.anchor))
                reset = source.read(len(self.anchor)) != self.anchor
            if reset:
                self._skip_to_end(source, metadata.st_size, identity)
                return [], True
            source.seek(self.position)
            data = source.read(self.max_bytes)
            self.position = source.tell()
            source.seek(max(0, self.position - 128))
            self.anchor = source.read(min(self.position, 128))
        lines = (self.partial + data).split(b"\n")
        self.partial = lines.pop()
        if len(self.partial) > self.max_bytes:
            self.partial = b""
            self.epoch += 1
            return [], True
        return [line.decode("utf-8", errors="replace") for line in lines], False


@dataclass(frozen=True)
class RawLocationFix:
    zone_id: int
    zone_display_name: str
    raw_coordinates: tuple[float, float, float]
    log_local_time: datetime
    received_monotonic: float
    log_epoch: int
    # These identify a new log line and zone observation, not the /location
    # command that caused it. The client does not echo a request ID here.
    log_line_seq: int = 0
    zone_generation: int = 0
    coordinates_aligned_to_wld: bool = False


class LocationLogReader:
    """Bind new /loc lines to an entered zone in one expected character log."""

    def __init__(self, log_path: Path, zone_names_path: Path, *,
                 expected_character: str, expected_server: str,
                 max_bytes: int = 512 * 1024) -> None:
        if log_path.name != f"eqlog_{expected_character}_{expected_server}.txt":
            raise ValueError("Location log does not match expected character/server")
        self.zone_ids, self.ambiguous_zone_names = unique_client_zone_ids(zone_names_path)
        self.tail = NonReplayingLogTail(log_path, max_bytes=max_bytes)
        self.zone_id: int | None = None
        self.zone_display_name: str | None = None
        self.latest: RawLocationFix | None = None
        self.last_log_local_time: datetime | None = None
        self.last_received_monotonic: float | None = None
        self.log_line_seq = 0
        self.zone_generation = 0
        self.tail.poll()  # Existing bytes are history; never bootstrap a zone.

    def _clear_zone(self) -> None:
        self.zone_generation += 1
        self.zone_id = None
        self.zone_display_name = None
        self.latest = None

    def poll(self, *, now: float | None = None) -> list[RawLocationFix]:
        received_at = time.monotonic() if now is None else now
        if (not isinstance(received_at, (int, float)) or
                isinstance(received_at, bool) or not isfinite(received_at)):
            self._clear_zone()
            raise ValueError("Poll time must be finite")
        if (self.last_received_monotonic is not None and
                received_at < self.last_received_monotonic):
            self._clear_zone()
            self.last_log_local_time = None
            raise ValueError("Poll time moved backward; zone must be observed again")
        self.last_received_monotonic = received_at
        try:
            lines, reset = self.tail.poll()
        except (OSError, ValueError):
            self._clear_zone()
            raise
        if reset:
            self._clear_zone()
            self.last_log_local_time = None
        fixes: list[RawLocationFix] = []
        for line in lines:
            parsed = parse_client_log_line(line)
            if parsed is None:
                if "LOADING, PLEASE WAIT" in line or "You have entered " in line:
                    self._clear_zone()
                    fixes.clear()
                continue
            log_time, body = parsed
            if self.last_log_local_time is not None and log_time < self.last_log_local_time:
                self._clear_zone()
                self.last_log_local_time = None
                fixes.clear()
                continue
            self.last_log_local_time = log_time
            if body == "LOADING, PLEASE WAIT...":
                self._clear_zone()
                fixes.clear()
                continue
            entered = _ENTERED.fullmatch(body)
            if entered is not None:
                self._clear_zone()
                fixes.clear()
                name = entered.group(1)
                zone_id = self.zone_ids.get(name)
                if zone_id is not None:
                    self.zone_id = zone_id
                    self.zone_display_name = name
                continue
            raw = parse_raw_location(body)
            if raw is None and body.startswith("Your Location is "):
                self.latest = None
                fixes.clear()
                continue
            if raw is None or self.zone_id is None or self.zone_display_name is None:
                continue
            self.log_line_seq += 1
            fix = RawLocationFix(self.zone_id, self.zone_display_name, raw,
                                 log_time, received_at, self.tail.epoch,
                                 self.log_line_seq, self.zone_generation)
            self.latest = fix
            fixes.append(fix)
        return fixes
