"""Follow an exact copied corridor through bounded stop/observe cycles.

This controller reuses the owner's PathFollower and PoseEstimator. It owns no
input devices. Its proposals require an external scene/geometry check and
timed sender; a proposal is not an input permit. Only actual completed holds
are integrated. Each decision uses a new one-segment follower so no rejected
or shortened request can be predicted as movement on a later update.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path

from .ground_binding import GroundGeometryEvidence, HeightCalibration, validate_ground_binding


class RouteHalt(RuntimeError):
    pass


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def xyz(point):
    return isinstance(point, (list, tuple)) and len(point) == 3 and all(finite(v) for v in point)


@dataclass(frozen=True)
class FixedSegment:
    polygon: int
    start: tuple[float, float, float]
    end: tuple[float, float, float]

    @property
    def length(self):
        return math.dist(self.start[:2], self.end[:2])


@dataclass(frozen=True)
class FixedRoute:
    zone: str
    mesh_sha256: str
    artifact_sha256: str
    half_width: float
    segments: tuple[FixedSegment, ...]

    @classmethod
    def load(cls, path: Path, *, expected_sha256: str, mesh_sha256: str):
        """Load one explicitly pinned exported plan, never find a new path."""
        raw = path.read_bytes()
        if path.is_symlink() or sha256(raw).hexdigest() != expected_sha256:
            raise ValueError("Fixed route artifact changed")
        data = json.loads(raw)
        if (data["format"] != "eql-fixed-segment-plan-v1"
                or data["frame"] != "helper_package_WLD_Y_X_Z"
                or data["offline_only"] is not True
                or data["route_accepted"] is not False
                or data["real_client_accepted"] is not False
                or mesh_sha256 not in data["pins"].values()):
            raise ValueError("Unsupported fixed-route provenance")
        segments = []
        for index, item in enumerate(data["segments"]):
            if (item["index"] != index or len(item["points"]) != 2
                    or not all(xyz(p) for p in item["points"])):
                raise ValueError("Invalid fixed-route segment")
            segments.append(FixedSegment(item["polygon"], *(tuple(p) for p in item["points"])))
        return cls(data["zone"], mesh_sha256, expected_sha256, data["half_width"], tuple(segments))


@dataclass(frozen=True)
class RouteProposal:
    serial: int
    segment_index: int
    at: float
    forward: bool
    turn: str | None
    heading_target: float
    # The external swept-motion check determines permitted duration.
    # No /location typing, targeting, recovery or jump is requested here.


class FixedRouteFollower:
    """A measurement/full-auto decision layer; never an assist input source.

    ``legacy`` is the retained, hash-checked eqnav.steer module. ``motion``
    and heading must come from the caller's calibration, not default Motion().
    The caller retains responsibility for scene checks, release watchdog,
    swept geometry, timeouts during a held key, and cancellation release.
    """
    def __init__(self, route, *, legacy, motion, heading, calibration_record_id,
                 height_calibration, geometry_evidence,
                 generation, generation_reader, mode_reader, endpoint_radius=.25,
                 height_tolerance=.25, max_step_seconds=.2, max_steps=20000):
        if (not isinstance(route, FixedRoute) or not route.zone or not route.segments
                or len(route.segments) > 10000
                or not finite(route.half_width) or route.half_width <= 0
                or not finite(endpoint_radius) or not 0 < endpoint_radius <= .25
                or endpoint_radius >= route.half_width
                or not finite(height_tolerance) or not 0 < height_tolerance <= .25
                or not finite(heading) or not 0 <= heading < 360
                or not calibration_record_id or not isinstance(calibration_record_id, str)
                or not isinstance(height_calibration, HeightCalibration)
                or height_calibration.live_verified is not True
                or not isinstance(geometry_evidence, GroundGeometryEvidence)
                or geometry_evidence.geometry_verified is not True
                or not finite(max_step_seconds) or not 0 < max_step_seconds <= .2
                or not isinstance(max_steps, int) or isinstance(max_steps, bool) or max_steps < 1
                or not isinstance(generation, int) or isinstance(generation, bool) or generation < 0
                or not callable(generation_reader) or not callable(mode_reader)):
            raise ValueError("Fixed-route controller requires explicit calibration and limits")
        for index, segment in enumerate(route.segments):
            if (not isinstance(segment, FixedSegment) or not xyz(segment.start) or not xyz(segment.end)
                    or not isinstance(segment.polygon, int) or isinstance(segment.polygon, bool)
                    or segment.polygon < 0 or segment.length <= 2 * endpoint_radius):
                raise ValueError("Segment endpoint acceptance disks overlap or segment is invalid")
            if index:
                previous = route.segments[index - 1]
                if (previous.end[:2] != segment.start[:2]
                        or abs(previous.end[2] - segment.start[2]) > height_tolerance):
                    raise ValueError("Fixed segments have a gap or unsupported height step")
        if (not isinstance(motion, legacy.Motion)
                or not all(finite(v) and v > 0 for v in (motion.run_speed, motion.turn_rate))
                # This controller rejects backward/jump controls. Zero means
                # backward speed is explicitly unused, not an invented fit.
                or not finite(motion.back_speed) or motion.back_speed < 0
                or not finite(motion.turn_latency) or not 0 <= motion.turn_latency <= .2
                or motion.right_sign not in (-1, 1) or isinstance(motion.right_sign, bool)):
            raise ValueError("Explicit measured motion is invalid")
        self.route, self.legacy, self.motion = route, legacy, motion
        self.calibration = calibration_record_id
        self.height_calibration = height_calibration
        self.geometry_evidence = geometry_evidence
        self.generation, self.generation_reader, self.mode_reader = generation, generation_reader, mode_reader
        self.radius, self.height_tolerance = endpoint_radius, height_tolerance
        self.max_step_seconds, self.max_steps = max_step_seconds, max_steps
        self.pose = legacy.PoseEstimator(motion)
        self.pose.heading, self.pose.sign_verified = heading, True
        self.index, self.serial, self.steps = 0, 0, 0
        self.phase, self.reason, self.pending = "need_start", "", None
        self.binding = None
        self.component = None
        self.last_seq, self.last_at, self.released_at = 0, None, None
        self.last_fix_at = None
        self.step_started_at = None
        self.no_progress_steps = 0
        self.best_remaining = None

    def halt(self, reason):
        """Discard pending decisions. The external sender must release keys."""
        self.phase, self.reason, self.pending = "halted", reason, None
        raise RouteHalt(reason)

    def _check(self, now):
        if self.phase == "halted":
            raise RouteHalt(self.reason)
        try:
            generation, mode = self.generation_reader(), self.mode_reader()
        except Exception:
            self.halt("Route mode/cancellation observation failed")
        if (not isinstance(generation, int) or isinstance(generation, bool)
                or generation != self.generation or mode not in ("measurement", "full_auto")):
            self.halt("Route cancelled or mode changed to assist/off")
        if not finite(now) or (self.last_at is not None and now < self.last_at):
            self.halt("Route observation clock is invalid")

    def _point(self, aligned, now):
        check = validate_ground_binding(aligned, height_calibration=self.height_calibration,
            geometry_evidence=self.geometry_evidence,
            mesh_sha256=self.route.mesh_sha256, zone_short_name=self.route.zone,
            now=now, motion_calibration_record_id=self.calibration)
        if not check.candidate:
            self.halt("Current raw-fix ground binding refused: " + check.reason)
        raw = aligned.raw_fix
        binding = (raw.zone_id, raw.zone_display_name, raw.log_epoch, raw.zone_generation)
        if (not finite(raw.received_monotonic) or not 0 <= now - raw.received_monotonic <= 2.5
                or not isinstance(raw.log_line_seq, int) or isinstance(raw.log_line_seq, bool)
                or raw.log_line_seq <= self.last_seq
                or (self.binding is not None and binding != self.binding)):
            self.halt("Raw route fix is stale, repeated or from another zone/log generation")
        projection = aligned.mesh_projection
        point = projection.package_xyz
        if self.component is not None and projection.component != self.component:
            self.halt("Ground projection changed route component")
        segment = self.route.segments[self.index]
        if projection.polygon != segment.polygon:
            # A stopped pulse can cross an audited shared portal by less than
            # the endpoint radius. Only the adjacent selected route polygon
            # may supply ground there; this cannot authorize a segment skip.
            supported = False
            for other, portal in ((self.index - 1, segment.start),
                                  (self.index + 1, segment.end)):
                if (0 <= other < len(self.route.segments)
                        and projection.polygon == self.route.segments[other].polygon
                        and segment.polygon in projection.verified_neighbor_polygons
                        and math.dist(point[:2], portal[:2]) <= self.radius
                        and abs(point[2] - portal[2]) <= self.radius + self.height_tolerance):
                    supported = True
            if not supported:
                self.halt("Ground projection left the selected polygon or adjacent portal disk")
        return point, binding

    def observe_stopped(self, first, second, *, released_at, now):
        """Accept two new aligned raw fixes requested after key release/settle.

        Caller must exclude outstanding earlier moving /location requests.
        Stationary pairs cannot identify a request ID the client never echoes.
        """
        self._check(now)
        if self.phase not in ("need_start", "await_stopped"):
            self.halt("Stopped fixes arrived in the wrong controller phase")
        p1, b1 = self._point(first, now)
        p2, b2 = self._point(second, now)
        t1, t2 = first.raw_fix.received_monotonic, second.raw_fix.received_monotonic
        if (not finite(released_at) or released_at > t1 - .12
                or (self.released_at is not None and released_at != self.released_at)
                or b1 != b2 or second.raw_fix.log_line_seq <= first.raw_fix.log_line_seq
                or not .4 - 1e-9 <= t2 - t1 <= 2.5 or now - t2 > .5
                or math.dist(p1[:2], p2[:2]) > .25 or abs(p1[2] - p2[2]) > .25
                or abs(first.raw_fix.raw_coordinates[2] - second.raw_fix.raw_coordinates[2]) > .25
                or abs(first.source_floor.ground_wld_xyz[2] - second.source_floor.ground_wld_xyz[2]) > .25
                or first.mesh_projection.component != second.mesh_projection.component):
            self.halt("Route requires a fresh stationary pair after confirmed key release")
        segment = self.route.segments[self.index]
        target = segment.start if self.phase == "need_start" else segment.end
        at_endpoint = all(math.dist(p[:2], target[:2]) <= self.radius
                          and abs(p[2] - target[2]) <= self.height_tolerance for p in (p1, p2))
        if self.phase == "need_start" and not at_endpoint:
            self.halt("Observed start is not at the fixed route start")
        if self.phase == "await_stopped":
            self.pose.predict(max(0., t2 - released_at), self.legacy.STOP)
        report = self.pose.correct(*p2, age=0.)
        if (report.get("jumped") or self.pose.sign_conflict or self.pose.turn_dead
                or self.pose.heading is None or self.pose._sign_votes
                or self.pose.blocked_fixes >= 2):
            self.halt("Observed motion contradicted calibration or made no progress")
        if self.phase == "await_stopped" and at_endpoint:
            self.index += 1
            self.best_remaining, self.no_progress_steps = None, 0
        self.binding, self.last_seq, self.last_at = b2, second.raw_fix.log_line_seq, now
        self.component = second.mesh_projection.component
        self.last_fix_at = t2
        self.released_at = None
        if self.index == len(self.route.segments):
            self.phase = "arrived"
            return
        segment = self.route.segments[self.index]
        ax, ay = segment.start[:2]
        bx, by = segment.end[:2]
        along = ((p2[0] - ax) * (bx - ax) + (p2[1] - ay) * (by - ay)) / segment.length ** 2
        closest = (ax + min(1., max(0., along)) * (bx - ax), ay + min(1., max(0., along)) * (by - ay))
        if math.dist(p2[:2], closest) > self.route.half_width or along > 1 + self.radius / segment.length:
            self.halt("Observed position left the selected segment; no skip or replan")
        remaining = math.dist(p2[:2], segment.end[:2])
        if self.best_remaining is None or remaining < self.best_remaining - .05:
            self.best_remaining, self.no_progress_steps = remaining, 0
        elif self.step_started_at is not None:
            self.no_progress_steps += 1
            if self.no_progress_steps >= 30:
                self.halt("Fixed segment made no measured progress for 30 steps")
        self.phase = "ready"

    def propose(self, now):
        self._check(now)
        if self.phase != "ready" or now - self.last_fix_at > .5 or self.steps >= self.max_steps:
            self.halt("No fresh stopped route position or step budget")
        if (not xyz((self.pose.x, self.pose.y, self.pose.z)) or not finite(self.pose.heading)
                or self.pose._sign_votes or self.pose.sign_conflict or self.pose.turn_dead):
            self.halt("Unknown heading or contradictory motion cannot start an automatic probe")
        segment = self.route.segments[self.index]
        tuning = self.legacy.FollowTuning(arrive_radius=self.radius,
                    lookahead_min=min(1.2, self.route.half_width),
                    lookahead_max=2 * self.route.half_width, turn_start=1., turn_stop=.5)
        follower = self.legacy.PathFollower((segment.start, segment.end), self.motion,
                    estimator=self.pose, fix_mode="typed", last_fix_at=now,
                    tuning=tuning)
        # A fresh legacy follower projects only s±60 units. Seed s from the
        # measured pose on this exact segment so a long segment does not make
        # its lookahead point fall behind us after 60 units of actual progress.
        dx, dy = segment.end[0] - segment.start[0], segment.end[1] - segment.start[1]
        along = ((self.pose.x - segment.start[0]) * dx + (self.pose.y - segment.start[1]) * dy) / segment.length
        follower.s = min(segment.length, max(0., along))
        controls = follower.update(now)  # First update predicts dt=0; no unsent motion.
        if (follower._probe is not None or follower._sign_test is not None
                or follower.status not in ("running", "arrived") or controls.back or controls.jump):
            self.halt("Legacy recovery/probe is outside the fixed-route controller")
        # Pivot rather than combine turning and forward movement. The discarded
        # follower never predicts its request; record_release integrates only
        # the proposal actually sent. The external swept guard still applies.
        forward = bool(controls.forward and controls.turn is None)
        target = follower.path.at(follower.s + tuning.lookahead_max)
        if math.hypot(target[0] - self.pose.x, target[1] - self.pose.y) < .5:
            target = segment.end
        heading_target = self.legacy.bearing(self.pose.x, self.pose.y, *target[:2])
        self.serial += 1
        self.pending = RouteProposal(self.serial, self.index, now, forward, controls.turn, heading_target)
        self.phase, self.last_at = "proposed", now
        return self.pending

    def record_release(self, proposal, *, started_at, released_at):
        """Integrate a completed externally permitted hold, then require fixes.

        A watchdog expiry/cancel/error must halt instead of reporting success.
        A proposal rejected by the external guard must also halt; never retry
        it using the old controller state.
        """
        self._check(released_at)
        if (self.phase != "proposed" or proposal is not self.pending
                or not finite(started_at) or not 0 <= started_at - proposal.at <= .05
                or not 0 <= released_at - started_at <= self.max_step_seconds
                or (not proposal.forward and proposal.turn is None and released_at != started_at)):
            self.halt("Invalid, stale or excessive actual hold receipt")
        controls = self.legacy.Controls(forward=proposal.forward, turn=proposal.turn)
        self.pose.predict(released_at - started_at, controls)
        self.pending = None
        self.step_started_at, self.released_at = started_at, released_at
        self.last_at, self.phase = released_at, "await_stopped"
        self.steps += 1

    def suggest_hold(self, proposal, *, minimum_seconds, maximum_seconds):
        """Size a requested hold without leaving a sub-minimum final step.

        This uses the motion estimate, not an upper-bound geometry proof.
        The caller must still check the complete worst-case swept movement
        and actual sender timing. No duration here is an input permit.
        """
        if (self.phase != "proposed" or proposal is not self.pending
                or not finite(minimum_seconds) or not finite(maximum_seconds)
                or not 0 < minimum_seconds <= maximum_seconds <= self.max_step_seconds):
            self.halt("Missing current proposal or usable pulse timing limits")
        end = self.route.segments[self.index].end
        if proposal.turn:
            angle = abs(self.legacy.wrap180(proposal.heading_target - self.pose.heading))
            if maximum_seconds <= self.motion.turn_latency:
                self.halt("Available pulse cannot overcome measured turn latency")
            return min(maximum_seconds, max(minimum_seconds, self.motion.turn_latency + angle / self.motion.turn_rate))
        if not proposal.forward:
            return 0.
        remaining = math.hypot(end[0] - self.pose.x, end[1] - self.pose.y)
        speed = self.pose.speed
        if not finite(speed) or speed <= 0:
            self.halt("No valid measured speed for forward pulse sizing")
        count = max(1, math.ceil(remaining / (speed * maximum_seconds)))
        seconds = remaining / speed / count
        if seconds < minimum_seconds:
            if count != 1 or minimum_seconds * speed - remaining > self.radius:
                self.halt("Minimum pulse can overshoot the selected endpoint")
            seconds = minimum_seconds
        return seconds
