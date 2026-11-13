"""Read-only geometry preflight for a supervised straight movement probe.

When facing direction is unknown, require a short clear ray in every tested
direction before the first pulse. This does not observe dynamic obstacles,
other players, the current game position or movement-stop behavior.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class RadialAreaCheck:
    candidate: bool
    reason: str
    center: tuple[float, float, float] | None = None
    clearance_lower_bound: float | None = None
    samples: int = 0
    real_client_accepted: bool = False


def check_radial_area(mesh, start: tuple[float, float, float], *,
                      radius: float = 8.0, directions: int = 36,
                      sample_spacing: float = 1.0,
                      minimum_clearance: float = 3.0,
                      maximum_z_change: float = 2.0,
                      maximum_slope: float = 45.0,
                      max_samples: int = 512) -> RadialAreaCheck:
    """Reject a point unless every short dry direction has conservative clearance."""
    if (len(start) != 3 or any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in start)
            or any(not math.isfinite(v) or v <= 0 for v in
                   (radius, sample_spacing, minimum_clearance, maximum_z_change, maximum_slope))
            or not isinstance(directions, int) or directions < 4
            or not isinstance(max_samples, int) or max_samples < 1):
        return RadialAreaCheck(False, "invalid_probe_limits")
    steps = math.ceil(radius / sample_spacing)
    if directions * (steps + 1) > max_samples:
        return RadialAreaCheck(False, "sample_budget_exceeded")
    origin = mesh.locate(start, radius=1.0)
    if origin is None:
        return RadialAreaCheck(False, "start_off_mesh")
    poly, center = origin
    center = tuple(float(v) for v in center)
    if (int(mesh.area[poly]) != 63 or float(mesh.slope[poly]) > maximum_slope
            or math.hypot(center[0] - start[0], center[1] - start[1]) > 1
            or abs(center[2] - start[2]) > maximum_z_change):
        return RadialAreaCheck(False, "start_not_safe_ground")
    lowest = math.inf
    for direction in range(directions):
        angle = 2 * math.pi * direction / directions
        requested = (center[0] + radius * math.cos(angle),
                     center[1] + radius * math.sin(angle), center[2])
        reached, endpoint = mesh.raycast(center, requested, water=False, zone_lines=())
        if not reached or abs(endpoint[2] - center[2]) > maximum_z_change:
            return RadialAreaCheck(False, "ray_blocked_or_steep", center)
        for index in range(steps + 1):
            t = index / steps
            x = center[0] + (endpoint[0] - center[0]) * t
            y = center[1] + (endpoint[1] - center[1]) * t
            z = center[2] + (endpoint[2] - center[2]) * t
            located = mesh.locate((x, y, z), radius=0.5)
            if located is None:
                return RadialAreaCheck(False, "sample_off_mesh", center)
            sample_poly, sample_point = located
            if (int(mesh.area[sample_poly]) != 63 or float(mesh.slope[sample_poly]) > maximum_slope
                    or abs(sample_point[2] - center[2]) > maximum_z_change):
                return RadialAreaCheck(False, "sample_not_flat_ground", center)
            clearance = float(mesh.clearance(x, y, z, limit=minimum_clearance + 1))
            if not math.isfinite(clearance) or clearance < minimum_clearance:
                return RadialAreaCheck(False, "insufficient_clearance", center, clearance)
            lowest = min(lowest, clearance)
    return RadialAreaCheck(True, "offline_open_area_candidate", center,
                           lowest, directions * (steps + 1))
