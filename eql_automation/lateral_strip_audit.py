"""Offline lateral clearance and grade check for one copied-mesh segment.

This checks a single straight segment's center and two lateral offsets. A
positive result does not validate turns, a whole route, dynamic obstacles,
follower error or client movement. It never sends game input.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import time

from .portal_surface_audit import (
    _contains_with_physical_tolerance, _supported_detail_height, audit_portal_surface,
)


@dataclass(frozen=True)
class LateralStripCheck:
    candidate: bool
    reason: str
    samples: int = 0
    sample_index: int | None = None
    side: int | None = None
    center_height: float | None = None
    side_height: float | None = None
    real_client_accepted: bool = False


def _ground_height(mesh, x: float, y: float, reference_z: float,
                   component: int, max_candidates: int,
                   vertical_window: float) -> tuple[str, float | None]:
    try:
        nearby = mesh._grid.near(x, y, 0.2)
        if len(nearby) > max_candidates:
            return "spatial_candidate_budget_exceeded", None
        candidates = [int(mesh._grid_ids[int(index)]) for index in nearby]
    except (AttributeError, IndexError, TypeError):
        return "spatial_index_unavailable", None
    surfaces = []
    for poly in candidates:
        poly = int(poly)
        if not _contains_with_physical_tolerance(mesh, poly, x, y):
            continue
        z = _supported_detail_height(mesh, poly, x, y)
        if z is None:
            if int(mesh.area[poly]) != 63 or int(mesh.component[poly]) != component:
                return "offset_in_forbidden_or_other_component", None
            return "offset_surface_unknown", None
        if abs(z - reference_z) > vertical_window:
            continue
        if int(mesh.area[poly]) != 63 or int(mesh.component[poly]) != component:
            return "offset_in_forbidden_or_other_component", None
        surfaces.append(z)
    if not surfaces:
        return "offset_surface_unknown", None
    if max(surfaces) - min(surfaces) > 0.01:
        return "offset_surface_ambiguous", None
    return "supported", min(surfaces, key=lambda z: abs(z - reference_z))


def audit_segment_strip(mesh, poly: int, start_xy: tuple[float, float],
                        end_xy: tuple[float, float], *,
                        half_width: float = 1.2,
                        center_clearance: float = 3.0,
                        sample_spacing: float = 0.5,
                        maximum_cross_grade: float = 1.0,
                        edge_clearance: float = 0.5,
                        max_samples: int = 512,
                        max_candidates: int = 24,
                        max_seconds: float = 3.0) -> LateralStripCheck:
    """Fail closed on unsupported ground, cross-grade, clearance or work cap."""
    coords = (*start_xy, *end_xy) if (isinstance(start_xy, tuple) and
                                       isinstance(end_xy, tuple)) else ()
    if (not isinstance(poly, int) or isinstance(poly, bool) or poly < 0 or
            len(coords) != 4 or
            any(not isinstance(v, (int, float)) or isinstance(v, bool) or
                not math.isfinite(v) for v in coords) or
            any(not isinstance(v, (int, float)) or isinstance(v, bool) or
                not math.isfinite(v) or v <= 0
                for v in (half_width, center_clearance, sample_spacing, maximum_cross_grade,
                          edge_clearance, max_seconds)) or
            any(not isinstance(v, int) or isinstance(v, bool) or v < 1
                for v in (max_samples, max_candidates))):
        return LateralStripCheck(False, "invalid_strip_limits")
    try:
        if int(mesh.area[poly]) != 63:
            return LateralStripCheck(False, "forbidden_center_area")
        component = int(mesh.component[poly])
        if component < 0:
            return LateralStripCheck(False, "unknown_center_component")
    except (AttributeError, IndexError, KeyError, TypeError):
        return LateralStripCheck(False, "unknown_center_polygon")
    dx, dy = end_xy[0] - start_xy[0], end_xy[1] - start_xy[1]
    distance = math.hypot(dx, dy)
    if not math.isfinite(distance) or distance <= 1e-6:
        return LateralStripCheck(False, "degenerate_segment")
    steps = math.ceil(distance / sample_spacing)
    # Each point is checked once along the centerline and again for polygon
    # containment in the strip pass; the already checked height is reused.
    # The two lateral positions are separately sampled.
    if 4 * (steps + 1) > max_samples:
        return LateralStripCheck(False, "strip_sample_budget_exceeded")
    nx, ny = -dy / distance, dx / distance
    vertical_window = half_width * maximum_cross_grade + 0.5
    started = time.monotonic()
    center = audit_portal_surface(mesh, poly, start_xy, end_xy,
                                  required_clearance=center_clearance,
                                  maximum_grade=maximum_cross_grade,
                                  sample_spacing=sample_spacing,
                                  max_samples=max_samples // 4)
    if not center.candidate:
        return LateralStripCheck(False, "centerline_" + center.reason,
                                 center.samples)
    if len(center.sampled_heights) != steps + 1:
        return LateralStripCheck(False, "centerline_profile_unavailable", center.samples)
    side_clearance_floor = edge_clearance + distance / steps / 2
    samples = center.samples
    for index in range(steps + 1):
        if time.monotonic() - started > max_seconds:
            return LateralStripCheck(False, "strip_time_budget_exceeded", samples, index)
        t = index / steps
        x, y = start_xy[0] + t * dx, start_xy[1] + t * dy
        samples += 1
        if not _contains_with_physical_tolerance(mesh, poly, x, y):
            return LateralStripCheck(False, "center_left_polygon", samples, index)
        center_z = center.sampled_heights[index]
        for side in (-1, 1):
            sx, sy = x + side * half_width * nx, y + side * half_width * ny
            reason, side_z = _ground_height(mesh, sx, sy, center_z,
                                            component, max_candidates, vertical_window)
            samples += 1
            if side_z is None:
                return LateralStripCheck(False, reason, samples, index, side, center_z)
            if abs(side_z - center_z) / half_width > maximum_cross_grade:
                return LateralStripCheck(False, "cross_grade_too_steep",
                                         samples, index, side, center_z, side_z)
            clearance = float(mesh.clearance(sx, sy, side_z, limit=edge_clearance + 1))
            if not math.isfinite(clearance) or clearance < side_clearance_floor:
                return LateralStripCheck(False, "side_clearance_below_budget",
                                         samples, index, side, center_z, side_z)
    if time.monotonic() - started > max_seconds:
        return LateralStripCheck(False, "strip_time_budget_exceeded", samples,
                                 steps)
    return LateralStripCheck(True, "one_segment_strip_candidate_only", samples)
