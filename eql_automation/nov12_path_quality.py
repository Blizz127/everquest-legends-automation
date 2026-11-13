"""Bounded, recording-only audit of a November helper mesh path.

This is a geometry gate for future navigation integration. Passing it does
not establish dynamic obstacle, aggro, zone-transition or real-client motion
safety. Missing follower error or incomplete geometry always rejects.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class PathQuality:
    geometrically_clear: bool
    reason: str
    samples: int = 0
    min_clearance: float | None = None
    required_clearance: float | None = None
    real_client_accepted: bool = False


def audit_path(mesh, path, *, agent_radius: float, follower_error: float | None,
               sample_spacing: float = 2.0, max_samples: int = 4000,
               allowed_areas: frozenset[int] = frozenset({63}),
               allowed_zone_lines: tuple[int, ...] = (),
               max_slope: float | None = 75.0) -> PathQuality:
    """Check a funnel polyline and its corridor without issuing any input.

    The half-spacing clearance term bounds unsampled positions because
    distance to a wall is 1-Lipschitz in the plane. ``follower_error`` must
    come from a bounded real-client follow trial; passing zero is appropriate
    only for an offline geometry diagnostic, never for live acceptance.
    """
    values = (agent_radius, sample_spacing)
    if (any(not math.isfinite(v) or v <= 0 for v in values) or
            not isinstance(max_samples, int) or max_samples < 2):
        return PathQuality(False, "invalid_audit_limits")
    if follower_error is None:
        return PathQuality(False, "follower_error_unmeasured")
    if not math.isfinite(follower_error) or follower_error < 0:
        return PathQuality(False, "invalid_follower_error")
    required = agent_radius + follower_error + sample_spacing / 2
    points = tuple(getattr(path, "points", ()))
    polys = tuple(getattr(path, "polys", ()))
    if len(points) < 2 or not polys or not all(
            len(p) == 3 and all(isinstance(v, (int, float)) and math.isfinite(v) for v in p)
            for p in points):
        return PathQuality(False, "invalid_path", required_clearance=required)
    allowed = set(allowed_areas) | set(allowed_zone_lines)
    if any(int(mesh.area[poly]) not in allowed for poly in polys):
        return PathQuality(False, "forbidden_corridor_area", required_clearance=required)
    if max_slope is not None and any(float(mesh.slope[poly]) > max_slope for poly in polys):
        return PathQuality(False, "steep_corridor_needs_review", required_clearance=required)
    segments = []
    sample_count = 0
    for a, b in zip(points, points[1:]):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        if not math.isfinite(length) or length <= 0:
            return PathQuality(False, "invalid_segment", required_clearance=required)
        steps = max(1, math.ceil(length / sample_spacing))
        sample_count += steps + 1
        if sample_count > max_samples:
            return PathQuality(False, "sample_budget_exceeded", required_clearance=required)
        segments.append((a, b, steps))
    minimum = math.inf
    for a, b, steps in segments:
        reached, _ = mesh.raycast(a, b, water=False, zone_lines=allowed_zone_lines)
        if not reached:
            return PathQuality(False, "segment_not_walkable", required_clearance=required)
        for index in range(steps + 1):
            t = index / steps
            x, y, z = (a[j] + (b[j] - a[j]) * t for j in range(3))
            located = mesh.locate((x, y, z), radius=0.25)
            if located is None or int(mesh.area[located[0]]) not in allowed:
                return PathQuality(False, "sample_off_allowed_mesh", required_clearance=required)
            clearance = float(mesh.clearance(x, y, z, limit=required + 1))
            if not math.isfinite(clearance):
                return PathQuality(False, "invalid_clearance", required_clearance=required)
            minimum = min(minimum, clearance)
    if minimum < required:
        return PathQuality(False, "clearance_below_budget", sample_count, minimum, required)
    return PathQuality(True, "geometry_candidate_only", sample_count, minimum, required)
