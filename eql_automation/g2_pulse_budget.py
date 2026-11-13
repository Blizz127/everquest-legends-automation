"""Recording-only bounds for a future supervised straight movement check.

This policy neither observes EverQuest nor sends input. Its caller must supply
fresh, independently verified scenes, a current-position geometry check and a
same-device timed key sender. A pass here never accepts full route following.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


PULSE_SECONDS = 0.15
MAX_ACTUAL_HOLD = 0.20
MAX_PULSES = 3
MAX_TOTAL_HOLD = 0.75
MAX_WINDOW = 15.0
MAX_HOLD_REPORT_AGE = 0.30
MAX_FIX_INTERVAL = 2.5
STILL_INTERVAL = 0.4
STILL_TOLERANCE = 0.25
MAX_VERTICAL_CHANGE = 2.0
MAX_DISPLACEMENT = 18.0
MIN_SPEED_UPPER_BOUND = 60.0  # Still requires a fresh, externally verified upper bound.


class G2Halt(RuntimeError):
    pass


@dataclass(frozen=True)
class G2Scene:
    at: float
    zone: str
    raw_location: tuple[float, float, float]
    log_epoch: int
    fix_seq: int
    zone_generation: int
    focused: bool = False
    owner_keys_clear: bool = False
    chat_clear: bool = False
    target_absent: bool = False
    combat_clear: bool = False
    no_transition: bool = False
    no_incoming_attack: bool = False


@dataclass(frozen=True)
class G2Result:
    pulses: int
    total_held: float
    displacement: float
    post_release_drift: float
    real_client_accepted: bool = False


@dataclass(frozen=True)
class G2Permit:
    seconds: float
    generation: int
    issued_at: float


def _distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


class G2PulseBudget:
    """Allow at most three short forward pulses, one fresh fix after each."""

    def __init__(self, first: G2Scene, second: G2Scene, *,
                 geometry_candidate: bool, owner_confirmed_g0: bool,
                 clear_radius: float, measured_speed: float,
                 verified_speed_upper_bound: float,
                 speed_bound_observed_at: float) -> None:
        self.stage = "halted"
        self.pulses = 0
        self.total_held = 0.0
        self.last_held = 0.0
        self.reserved_at = None
        self.generation = 0
        self.permit: G2Permit | None = None
        if (geometry_candidate is not True or owner_confirmed_g0 is not True or
                not isinstance(clear_radius, (int, float)) or not math.isfinite(clear_radius) or
                not 0 < clear_radius <= MAX_DISPLACEMENT or
                not isinstance(measured_speed, (int, float)) or
                not math.isfinite(measured_speed) or not 0 < measured_speed <= 100 or
                not isinstance(verified_speed_upper_bound, (int, float)) or
                not math.isfinite(verified_speed_upper_bound) or
                verified_speed_upper_bound < max(MIN_SPEED_UPPER_BOUND, measured_speed * 1.5) or
                not isinstance(speed_bound_observed_at, (int, float)) or
                not math.isfinite(speed_bound_observed_at) or
                not isinstance(second, G2Scene) or
                not isinstance(second.at, (int, float)) or
                not speed_bound_observed_at <= second.at or
                second.at - speed_bound_observed_at > 60.0):
            raise G2Halt("Missing current geometry, owner G0 or bounded calibration")
        self.zone = first.zone
        self.log_epoch = first.log_epoch
        self.zone_generation = first.zone_generation
        self.started_at = first.at
        self.last_at = first.at
        self._check(first)
        self._check(second)
        if (second.fix_seq <= first.fix_seq or
                second.at - first.at < STILL_INTERVAL or
                second.at - first.at > 2.5 or
                _distance(first.raw_location, second.raw_location) > STILL_TOLERANCE or
                abs(first.raw_location[2] - second.raw_location[2]) > STILL_TOLERANCE):
            raise G2Halt("Preflight location was not stationary and fresh")
        self.origin = second.raw_location
        self.latest = second.raw_location
        self.latest_fix_seq = second.fix_seq
        self.clear_radius = float(clear_radius)
        self.speed = float(measured_speed)
        self.speed_upper_bound = float(verified_speed_upper_bound)
        self.stage = "ready"

    def _fail(self, reason: str):
        self.stage = "halted"
        self.generation += 1
        self.permit = None
        raise G2Halt(reason)

    def cancel(self) -> None:
        """Invalidate a queued pulse on OFF or any external interruption."""
        self.stage = "halted"
        self.generation += 1
        self.permit = None

    def _check(self, scene: G2Scene) -> None:
        if not isinstance(scene, G2Scene):
            self._fail("Missing structured scene observation")
        loc = scene.raw_location
        if (not isinstance(scene.at, (int, float)) or not math.isfinite(scene.at) or
                not isinstance(scene.zone, str) or not scene.zone or scene.zone != self.zone or
                not isinstance(scene.log_epoch, int) or scene.log_epoch != self.log_epoch or
                not isinstance(scene.fix_seq, int) or scene.fix_seq < 1 or
                not isinstance(scene.zone_generation, int) or
                isinstance(scene.zone_generation, bool) or
                scene.zone_generation < 1 or
                scene.zone_generation != self.zone_generation or
                not isinstance(loc, tuple) or len(loc) != 3 or
                any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in loc) or
                not all(value is True for value in
                        (scene.focused, scene.owner_keys_clear, scene.chat_clear,
                         scene.target_absent, scene.combat_clear, scene.no_transition,
                         scene.no_incoming_attack)) or
                scene.at < self.last_at or scene.at - self.started_at > MAX_WINDOW):
            self._fail("Scene became unsafe, stale or out of the movement window")
        self.last_at = scene.at

    def reserve_forward(self, scene: G2Scene) -> G2Permit:
        if self.stage != "ready":
            self._fail("Forward pulse requested in the wrong phase")
        self._check(scene)
        if (self.pulses >= MAX_PULSES or
                self.total_held + MAX_ACTUAL_HOLD > MAX_TOTAL_HOLD or
                _distance(self.latest, scene.raw_location) > STILL_TOLERANCE or
                abs(self.latest[2] - scene.raw_location[2]) > STILL_TOLERANCE or
                _distance(self.origin, self.latest) + self.speed_upper_bound * MAX_ACTUAL_HOLD > self.clear_radius or
                _distance(self.origin, self.latest) + self.speed_upper_bound * MAX_ACTUAL_HOLD > MAX_DISPLACEMENT):
            self._fail("Forward pulse would exceed its count, time or clear-radius budget")
        self.stage = "reserved"
        self.reserved_at = scene.at
        self.generation += 1
        self.permit = G2Permit(PULSE_SECONDS, self.generation, scene.at)
        return self.permit

    def confirm_keydown(self, scene: G2Scene, permit: G2Permit) -> float:
        """Recheck a reserved pulse immediately before the sender's key-down."""
        if (self.stage != "reserved" or permit is not self.permit or
                permit.generation != self.generation):
            self._fail("Queued forward pulse was cancelled or superseded")
        self._check(scene)
        if (scene.at - permit.issued_at > 0.05 or
                _distance(self.latest, scene.raw_location) > STILL_TOLERANCE or
                abs(self.latest[2] - scene.raw_location[2]) > STILL_TOLERANCE):
            self._fail("Queued forward pulse is stale or position changed")
        self.stage = "keydown_authorized"
        return permit.seconds

    def still_authorized(self, scene: G2Scene, permit: G2Permit) -> bool:
        """Check a pulse lease while the same-device child may hold the key."""
        if (self.stage != "keydown_authorized" or permit is not self.permit or
                permit.generation != self.generation):
            self._fail("Forward pulse was cancelled while held")
        self._check(scene)
        if _distance(self.origin, scene.raw_location) > self.clear_radius:
            self._fail("Forward pulse left the checked radius")
        return True

    def record_hold(self, scene: G2Scene, actual_seconds: float) -> None:
        if self.stage != "keydown_authorized":
            self._fail("Hold reported without a current key-down permit")
        self._check(scene)
        if (not isinstance(actual_seconds, (int, float)) or
                not math.isfinite(actual_seconds) or
                not 0 < actual_seconds <= MAX_ACTUAL_HOLD or
                scene.at - self.reserved_at + 1e-6 < actual_seconds or
                scene.at - self.reserved_at > MAX_HOLD_REPORT_AGE or
                _distance(self.latest, scene.raw_location) > STILL_TOLERANCE or
                abs(self.latest[2] - scene.raw_location[2]) > STILL_TOLERANCE or
                self.total_held + actual_seconds > MAX_TOTAL_HOLD):
            self._fail("Pulse duration was missing or exceeded its budget")
        self.pulses += 1
        self.total_held += actual_seconds
        self.last_held = actual_seconds
        self.permit = None
        self.stage = "await_fix"

    def record_fix(self, scene: G2Scene) -> None:
        if self.stage != "await_fix":
            self._fail("Position fix reported outside a completed pulse")
        previous_at = self.last_at
        self._check(scene)
        moved = _distance(self.latest, scene.raw_location)
        if (scene.fix_seq <= self.latest_fix_seq or
                scene.at <= previous_at or scene.at - previous_at > MAX_FIX_INTERVAL or
                moved < 0.5 or moved > self.speed_upper_bound * self.last_held + 2.0 or
                _distance(self.origin, scene.raw_location) > min(self.clear_radius, MAX_DISPLACEMENT) or
                abs(scene.raw_location[2] - self.origin[2]) > MAX_VERTICAL_CHANGE):
            self._fail("Pulse position was missing, implausible or outside the clear area")
        self.latest = scene.raw_location
        self.latest_fix_seq = scene.fix_seq
        self.stage = "await_still"

    def record_still(self, scene: G2Scene) -> None:
        if self.stage != "await_still":
            self._fail("Stillness check reported outside a completed pulse")
        previous_at = self.last_at
        self._check(scene)
        if (scene.fix_seq <= self.latest_fix_seq or
                scene.at - previous_at < STILL_INTERVAL or
                scene.at - previous_at > MAX_FIX_INTERVAL or
                _distance(self.latest, scene.raw_location) > STILL_TOLERANCE or
                abs(self.latest[2] - scene.raw_location[2]) > STILL_TOLERANCE or
                _distance(self.origin, scene.raw_location) > self.clear_radius):
            self._fail("Movement continued after release; no further pulse permitted")
        self.latest = scene.raw_location
        self.latest_fix_seq = scene.fix_seq
        self.stage = "ready"

    def finish(self, first: G2Scene, second: G2Scene) -> G2Result:
        if self.stage != "ready" or self.pulses < 1:
            self._fail("No completed pulse to assess")
        prior_at = self.last_at
        self._check(first)
        self._check(second)
        drift = _distance(first.raw_location, second.raw_location)
        if (first.fix_seq <= self.latest_fix_seq or
                second.fix_seq <= first.fix_seq or
                first.at - prior_at < STILL_INTERVAL or
                first.at - prior_at > MAX_FIX_INTERVAL or
                second.at - first.at < STILL_INTERVAL or
                second.at - first.at > MAX_FIX_INTERVAL or
                _distance(self.latest, first.raw_location) > STILL_TOLERANCE or
                abs(self.latest[2] - first.raw_location[2]) > STILL_TOLERANCE or
                drift > STILL_TOLERANCE or
                abs(first.raw_location[2] - second.raw_location[2]) > STILL_TOLERANCE or
                abs(second.raw_location[2] - self.origin[2]) > MAX_VERTICAL_CHANGE or
                _distance(self.origin, second.raw_location) > self.clear_radius):
            self._fail("Position did not remain stopped after release")
        self.stage = "done"
        return G2Result(self.pulses, self.total_held,
                        _distance(self.origin, second.raw_location), drift)
