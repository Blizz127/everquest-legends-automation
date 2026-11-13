"""Read-only bridge from fresh client log locations to a G2 probe scene.

The client does not echo a /location request ID. A log line can therefore
prove only that a location was printed recently, not which request produced
it. This observer never sends a command or authorizes movement on its own.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import math
import time

from .g2_pulse_budget import G2Scene
from .location_log import LocationLogReader, RawLocationFix


MAX_FIX_AGE = 0.50
MAX_SAFETY_AGE = 0.10
MAX_LOG_CLOCK_SKEW = 2.0


class G2ObservationUnavailable(RuntimeError):
    """A current, unambiguous scene cannot be constructed."""


@dataclass(frozen=True)
class G2SafetyObservation:
    """Independent, current UI/device checks supplied by the eventual caller."""

    observed_at: float
    focused: bool = False
    owner_keys_clear: bool = False
    chat_clear: bool = False
    target_absent: bool = False
    combat_clear: bool = False
    no_transition: bool = False
    no_incoming_attack: bool = False


class G2ReadOnlySceneObserver:
    """Accept a single fresh /location line in the expected zone.

    The supplied safety observer must make fresh, independent checks; this
    class cannot infer focus, target or combat state from /location. Multiple
    location lines arriving in one poll are ambiguous and stay rejected until
    a later single line arrives. These scenes remain measurement-only.
    """

    def __init__(self, reader: LocationLogReader, *,
                 zone_short_name: str, zone_display_name: str, zone_id: int,
                 safety_provider: Callable[[], G2SafetyObservation],
                 monotonic_clock: Callable[[], float] = time.monotonic,
                 local_wall_clock: Callable[[], datetime] = datetime.now) -> None:
        if (not isinstance(reader, LocationLogReader) or
                not isinstance(zone_short_name, str) or not zone_short_name or
                not isinstance(zone_display_name, str) or not zone_display_name or
                not isinstance(zone_id, int) or isinstance(zone_id, bool) or zone_id < 0 or
                not callable(safety_provider) or not callable(monotonic_clock) or
                not callable(local_wall_clock)):
            raise ValueError("G2 scene observer needs an exact zone and independent checks")
        self.reader = reader
        self.zone_short_name = zone_short_name
        self.zone_display_name = zone_display_name
        self.zone_id = zone_id
        self.safety_provider = safety_provider
        self.monotonic_clock = monotonic_clock
        self.local_wall_clock = local_wall_clock
        self.trusted_fix: RawLocationFix | None = None

    def __call__(self) -> G2Scene:
        poll_at = self.monotonic_clock()
        if (not isinstance(poll_at, (int, float)) or isinstance(poll_at, bool) or
                not math.isfinite(poll_at)):
            self.trusted_fix = None
            raise G2ObservationUnavailable("Invalid monotonic observation clock")
        try:
            fixes = self.reader.poll(now=poll_at)
        except (OSError, ValueError) as error:
            self.trusted_fix = None
            raise G2ObservationUnavailable("Location log poll failed") from error
        if len(fixes) > 1:
            self.trusted_fix = None
            raise G2ObservationUnavailable("Batched location lines have no request identity")
        if fixes:
            self.trusted_fix = fixes[0]
        fix = self.trusted_fix
        if (fix is None or self.reader.latest is not fix or
                fix.zone_id != self.zone_id or
                fix.zone_display_name != self.zone_display_name or
                self.reader.zone_id != self.zone_id or
                self.reader.zone_display_name != self.zone_display_name or
                fix.log_epoch != self.reader.tail.epoch or
                fix.zone_generation != self.reader.zone_generation):
            self.trusted_fix = None
            raise G2ObservationUnavailable("No fresh single-zone location fix")
        safety = self.safety_provider()
        now = self.monotonic_clock()
        if (not isinstance(now, (int, float)) or isinstance(now, bool) or
                not math.isfinite(now) or now < poll_at):
            self.trusted_fix = None
            raise G2ObservationUnavailable("Invalid monotonic observation clock")
        try:
            intervening = self.reader.poll(now=now)
        except (OSError, ValueError) as error:
            self.trusted_fix = None
            raise G2ObservationUnavailable("Location log changed during scene check") from error
        if (intervening or self.reader.latest is not fix or
                fix.log_epoch != self.reader.tail.epoch or
                fix.zone_generation != self.reader.zone_generation or
                not 0 <= now - fix.received_monotonic <= MAX_FIX_AGE):
            self.trusted_fix = None
            raise G2ObservationUnavailable("No fresh single-zone location fix")
        wall_now = self.local_wall_clock()
        if (not isinstance(wall_now, datetime) or wall_now.tzinfo is not None or
                abs((wall_now - fix.log_local_time).total_seconds()) > MAX_LOG_CLOCK_SKEW):
            self.trusted_fix = None
            raise G2ObservationUnavailable("Location log timestamp is stale or clock is unsynchronized")
        if (not isinstance(safety, G2SafetyObservation) or
                not isinstance(safety.observed_at, (int, float)) or
                isinstance(safety.observed_at, bool) or
                not math.isfinite(safety.observed_at) or
                not 0 <= now - safety.observed_at <= MAX_SAFETY_AGE or
                not all(value is True for value in
                        (safety.focused, safety.owner_keys_clear, safety.chat_clear,
                         safety.target_absent, safety.combat_clear,
                         safety.no_transition, safety.no_incoming_attack))):
            raise G2ObservationUnavailable("Independent scene checks are stale or unsafe")
        return G2Scene(now, self.zone_short_name, fix.raw_coordinates,
                       fix.log_epoch, fix.log_line_seq, fix.zone_generation,
                       focused=True, owner_keys_clear=True, chat_clear=True,
                       target_absent=True, combat_clear=True, no_transition=True,
                       no_incoming_attack=True)
