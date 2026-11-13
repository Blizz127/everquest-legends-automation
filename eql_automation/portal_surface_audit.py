"""Bounded true-surface check of one portal-to-portal segment.

This is an offline diagnostic for copied client navmeshes. It reports only a
centerline geometry candidate. It neither moves a character nor validates a
whole route, adjacent polygon seams, dynamic objects or follower error.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class PortalSurfaceCheck:
    candidate: bool
    reason: str
    samples: int = 0
    min_clearance: float | None = None
    max_local_grade: float | None = None
    real_client_accepted: bool = False


@dataclass(frozen=True)
class PortalSeamCheck:
    candidate: bool
    reason: str
    source_height: float | None = None
    target_height: float | None = None
    min_clearance: float | None = None
    real_client_accepted: bool = False


_DETAIL_EDGE_TOLERANCE = 5e-4  # WLD units; copied GFay float32 edges differ by 0.000324.
_DETAIL_HEIGHT_AGREEMENT = 0.01  # Conflicting overlapping surfaces stay unknown.


def _contains_with_physical_tolerance(mesh, poly: int, x: float, y: float) -> bool:
    """Check a CCW Recast ring with a distance, not raw cross-product, slack.

    ``NavMesh.contains`` applies its slack to an unnormalized cross product.
    On a long edge, a tiny float-quantized portal displacement can therefore
    fail despite being closer than the detail-edge tolerance above.
    """
    try:
        ring = mesh.polys[poly]
    except (AttributeError, IndexError, KeyError, TypeError):
        return False
    if len(ring) < 3:
        return False
    nonzero_edges = 0
    for index, start in enumerate(ring):
        end = ring[(index + 1) % len(ring)]
        dx, dy = float(end[0] - start[0]), float(end[1] - start[1])
        length = math.hypot(dx, dy)
        if not math.isfinite(length):
            return False
        if length <= 1e-12:
            continue
        nonzero_edges += 1
        signed_distance = (dx * (y - start[1]) - dy * (x - start[0])) / length
        if signed_distance < -_DETAIL_EDGE_TOLERANCE:
            return False
    return nonzero_edges >= 3


def _supported_detail_height(mesh, poly: int, x: float, y: float) -> float | None:
    """Return a height on a Recast detail triangle, allowing tiny edge gaps.

    ``NavMesh.height`` also interpolates polygon corners, or extrapolates a
    nearby detail triangle, when none covers the query. A portal edge can be
    displaced by less than a milliworld unit through float conversion, so this
    routine projects at most 5e-4 world units onto a detail edge. Wider extrapolation
    and corner interpolation remain insufficient for a local slope check.
    """
    try:
        first = int(mesh._detail_start[poly])
        last = int(mesh._detail_start[poly + 1])
        triangles = mesh._detail[first:last]
    except (AttributeError, IndexError, KeyError, TypeError):
        return None
    supported = []
    for triangle in triangles:
        a, b, c = triangle
        e1x, e1y = float(b[0] - a[0]), float(b[1] - a[1])
        e2x, e2y = float(c[0] - a[0]), float(c[1] - a[1])
        det = e1x * e2y - e1y * e2x
        if not math.isfinite(det) or abs(det) <= 1e-12:
            continue
        px, py = x - float(a[0]), y - float(a[1])
        u = (px * e2y - py * e2x) / det
        v = (e1x * py - e1y * px) / det
        if min(u, v, 1.0 - u - v) >= -1e-12:
            z = float(a[2]) + u * float(b[2] - a[2]) + v * float(c[2] - a[2])
            if math.isfinite(z):
                supported.append((0.0, z))
            continue
        nearest_gap = math.inf
        nearest_z = None
        for start, end in ((a, b), (b, c), (c, a)):
            dx, dy = float(end[0] - start[0]), float(end[1] - start[1])
            length2 = dx * dx + dy * dy
            if not math.isfinite(length2) or length2 <= 1e-12:
                continue
            t = max(0.0, min(1.0,
                             ((x - start[0]) * dx + (y - start[1]) * dy) / length2))
            gap = math.hypot(x - (start[0] + t * dx),
                             y - (start[1] + t * dy))
            if gap < nearest_gap:
                nearest_gap = gap
                nearest_z = float(start[2] + t * (end[2] - start[2]))
        if nearest_gap <= _DETAIL_EDGE_TOLERANCE and math.isfinite(nearest_z):
            supported.append((nearest_gap, nearest_z))
    if not supported:
        return None
    heights = [z for _, z in supported]
    if max(heights) - min(heights) > _DETAIL_HEIGHT_AGREEMENT:
        return None
    return min(supported)[1]


def audit_portal_seam(mesh, source_poly: int, target_poly: int,
                      crossing_xy: tuple[float, float], *,
                      maximum_step: float = 0.5,
                      required_clearance: float = 3.0,
                      allowed_areas: frozenset[int] = frozenset({63})) -> PortalSeamCheck:
    """Require an actual shared portal and supported detail heights on both sides.

    A positive result concerns this one crossing only. The adjoining travel
    strips, zone transitions and moving client still need independent checks.
    """
    if (any(not isinstance(p, int) or isinstance(p, bool) or p < 0
            for p in (source_poly, target_poly)) or source_poly == target_poly or
            not isinstance(crossing_xy, tuple) or len(crossing_xy) != 2 or
            any(not isinstance(v, (int, float)) or not math.isfinite(v)
                for v in crossing_xy) or
            any(not isinstance(v, (int, float)) or isinstance(v, bool) or
                not math.isfinite(v) or v <= 0
                for v in (maximum_step, required_clearance))):
        return PortalSeamCheck(False, "invalid_seam_limits")
    try:
        if (int(mesh.area[source_poly]) not in allowed_areas or
                int(mesh.area[target_poly]) not in allowed_areas):
            return PortalSeamCheck(False, "forbidden_area")
        links = mesh.links[source_poly]
    except (AttributeError, IndexError, KeyError, TypeError):
        return PortalSeamCheck(False, "unknown_polygon")
    x, y = crossing_xy
    on_portal = False
    for neighbor, left, right in links:
        if neighbor != target_poly:
            continue
        dx, dy = float(right[0] - left[0]), float(right[1] - left[1])
        length2 = dx * dx + dy * dy
        if not math.isfinite(length2) or length2 <= 1e-12:
            continue
        along = ((x - left[0]) * dx + (y - left[1]) * dy) / length2
        gap = abs((x - left[0]) * dy - (y - left[1]) * dx) / math.sqrt(length2)
        endpoint_margin = _DETAIL_EDGE_TOLERANCE / math.sqrt(length2)
        if -endpoint_margin <= along <= 1 + endpoint_margin and gap <= _DETAIL_EDGE_TOLERANCE:
            on_portal = True
            break
    if not on_portal:
        return PortalSeamCheck(False, "crossing_outside_shared_portal")
    source_z = _supported_detail_height(mesh, source_poly, x, y)
    target_z = _supported_detail_height(mesh, target_poly, x, y)
    if source_z is None or target_z is None:
        return PortalSeamCheck(False, "unsupported_detail_surface", source_z, target_z)
    if abs(source_z - target_z) > maximum_step:
        return PortalSeamCheck(False, "height_step_too_large", source_z, target_z)
    source_clear = float(mesh.clearance(x, y, source_z, limit=required_clearance + 1))
    target_clear = float(mesh.clearance(x, y, target_z, limit=required_clearance + 1))
    minimum = min(source_clear, target_clear)
    if not math.isfinite(minimum):
        return PortalSeamCheck(False, "invalid_clearance", source_z, target_z)
    if minimum < required_clearance:
        return PortalSeamCheck(False, "clearance_below_budget",
                               source_z, target_z, minimum)
    return PortalSeamCheck(True, "seam_geometry_candidate_only",
                           source_z, target_z, minimum)


def audit_portal_surface(mesh, poly: int, entry_xy: tuple[float, float],
                         exit_xy: tuple[float, float], *,
                         required_clearance: float = 3.0,
                         maximum_grade: float = 1.0,
                         sample_spacing: float = 0.5,
                         max_samples: int = 512,
                         allowed_areas: frozenset[int] = frozenset({63})) -> PortalSurfaceCheck:
    """Sample the mesh's own detail surface inside one polygon.

    Polygon-wide ``slope`` and centroid clearance are intentionally not used:
    they may describe a different part of a large polygon. A later route
    audit must also check the travel strip, cross-polygon height continuity,
    dynamic obstacles and actual client motion before accepting movement.
    """
    if (not isinstance(poly, int) or isinstance(poly, bool) or poly < 0 or
            not isinstance(entry_xy, tuple) or not isinstance(exit_xy, tuple) or
            len(entry_xy) != 2 or len(exit_xy) != 2 or
            any(not isinstance(v, (int, float)) or not math.isfinite(v)
                for v in (*entry_xy, *exit_xy)) or
            any(not isinstance(v, (int, float)) or isinstance(v, bool) or
                not math.isfinite(v) or v <= 0
                for v in (required_clearance, maximum_grade, sample_spacing)) or
            not isinstance(max_samples, int) or isinstance(max_samples, bool) or max_samples < 2):
        return PortalSurfaceCheck(False, "invalid_audit_limits")
    try:
        if int(mesh.area[poly]) not in allowed_areas:
            return PortalSurfaceCheck(False, "forbidden_area")
    except (IndexError, KeyError, TypeError):
        return PortalSurfaceCheck(False, "unknown_polygon")
    distance = math.hypot(exit_xy[0] - entry_xy[0], exit_xy[1] - entry_xy[1])
    if not math.isfinite(distance) or distance <= 1e-6:
        return PortalSurfaceCheck(False, "degenerate_segment")
    steps = math.ceil(distance / sample_spacing)
    if steps + 1 > max_samples:
        return PortalSurfaceCheck(False, "sample_budget_exceeded")
    lowest = math.inf
    highest_grade = 0.0
    previous_z = None
    step_distance = distance / steps
    # A wall-distance sample can overstate the minimum between two samples by
    # at most half their planar separation, provided the same wall set applies.
    # The result remains diagnostic because height-band filtering and a
    # piecewise detail surface still need an exact travel-strip review.
    sampled_clearance_floor = required_clearance + step_distance / 2
    for index in range(steps + 1):
        fraction = index / steps
        x = entry_xy[0] + (exit_xy[0] - entry_xy[0]) * fraction
        y = entry_xy[1] + (exit_xy[1] - entry_xy[1]) * fraction
        if not _contains_with_physical_tolerance(mesh, poly, x, y):
            return PortalSurfaceCheck(False, "sample_left_polygon", index)
        z = _supported_detail_height(mesh, poly, x, y)
        if z is None:
            return PortalSurfaceCheck(False, "unsupported_detail_surface", index)
        clearance = float(mesh.clearance(x, y, z, limit=required_clearance + 1))
        if not math.isfinite(clearance):
            return PortalSurfaceCheck(False, "invalid_clearance", index)
        lowest = min(lowest, clearance)
        if lowest < sampled_clearance_floor:
            return PortalSurfaceCheck(False, "clearance_below_budget", index + 1,
                                      lowest, highest_grade)
        if previous_z is not None:
            grade = abs(z - previous_z) / step_distance
            highest_grade = max(highest_grade, grade)
            if grade > maximum_grade:
                return PortalSurfaceCheck(False, "local_grade_too_steep", index + 1,
                                          lowest, highest_grade)
        previous_z = z
    return PortalSurfaceCheck(True, "centerline_geometry_candidate_only",
                              steps + 1, lowest, highest_grade)
