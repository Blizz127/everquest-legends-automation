"""Bounded offline search over sampled portals of one copied-mesh corridor.

The caller supplies an already chosen polygon sequence. Passing this audit
means only that sampled centerlines and seams connect in that sequence. It
does not authorize movement, establish a whole travel strip, or validate a
zone transition, current client position, dynamic obstacle or follower error.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import time

from .portal_surface_audit import audit_portal_seam, audit_portal_surface


@dataclass(frozen=True)
class PortalCorridorCheck:
    candidate: bool
    reason: str
    checked_segments: int = 0
    processed_polygons: int = 0
    failing_polygon: int | None = None
    points: tuple[tuple[float, float], ...] = ()
    reachable_entries: tuple[tuple[float, float], ...] = ()
    eligible_exits: tuple[tuple[float, float], ...] = ()
    real_client_accepted: bool = False


def audit_fixed_corridor(mesh, corridor: tuple[int, ...],
                         start_xy: tuple[float, float], goal_xy: tuple[float, float], *,
                         fractions: tuple[float, ...] = (0.1, 0.3, 0.5, 0.75, 0.9),
                         required_clearance: float = 3.0,
                         sample_spacing: float = 0.5,
                         maximum_grade: float = 1.0,
                         max_polygons: int = 160,
                         max_checks: int = 3000,
                         max_seconds: float = 20.0) -> PortalCorridorCheck:
    """Find one sampled portal-centerline chain, within strict work budgets."""
    coordinates = (*start_xy, *goal_xy) if (isinstance(start_xy, tuple) and
                                         isinstance(goal_xy, tuple)) else ()
    if (not isinstance(max_polygons, int) or isinstance(max_polygons, bool) or max_polygons < 1 or
            not isinstance(max_checks, int) or isinstance(max_checks, bool) or max_checks < 1 or
            not isinstance(corridor, tuple) or not corridor or
            any(not isinstance(p, int) or isinstance(p, bool) or p < 0 for p in corridor) or
            len(corridor) > max_polygons or
            len(coordinates) != 4 or
            any(not isinstance(v, (int, float)) or not math.isfinite(v)
                for v in coordinates) or
            not isinstance(fractions, tuple) or not fractions or len(fractions) > 16 or
            any(not isinstance(t, (int, float)) or not math.isfinite(t) or not 0 < t < 1
                for t in fractions) or
            any(not isinstance(v, (int, float)) or isinstance(v, bool) or
                not math.isfinite(v) or v <= 0
                for v in (required_clearance, sample_spacing, maximum_grade, max_seconds))):
        return PortalCorridorCheck(False, "invalid_corridor_limits")
    started = time.monotonic()
    seam_checks = 0
    portal_layers = []
    for source_poly, target_poly in zip(corridor, corridor[1:]):
        try:
            link = next((left, right) for neighbor, left, right
                        in mesh.links[source_poly] if neighbor == target_poly)
        except (AttributeError, IndexError, KeyError, TypeError, StopIteration):
            return PortalCorridorCheck(False, "missing_shared_portal",
                                       failing_polygon=source_poly)
        left, right = link
        candidates = []
        for fraction in fractions:
            if seam_checks >= max_checks or time.monotonic() - started > max_seconds:
                return PortalCorridorCheck(False, "corridor_work_budget_exceeded",
                                           failing_polygon=source_poly)
            seam_checks += 1
            x = (1 - fraction) * left[0] + fraction * right[0]
            y = (1 - fraction) * left[1] + fraction * right[1]
            point = (float(x), float(y))
            seam = audit_portal_seam(mesh, source_poly, target_poly, point,
                                     required_clearance=required_clearance)
            if seam.candidate and point not in candidates:
                candidates.append(point)
        if not candidates:
            return PortalCorridorCheck(False, "no_sampled_portal_crossing",
                                       failing_polygon=source_poly)
        portal_layers.append(tuple(candidates))
    # Keep only the cheapest known route to each crossing in the next layer.
    states = {start_xy: (0.0, (start_xy,))}
    checks = 0
    for index, poly in enumerate(corridor):
        exits = portal_layers[index] if index < len(portal_layers) else (goal_xy,)
        following = {}
        for entry, (cost, points) in states.items():
            for exit_xy in exits:
                if seam_checks + checks >= max_checks or time.monotonic() - started > max_seconds:
                    return PortalCorridorCheck(False, "corridor_work_budget_exceeded",
                                               checks, index, poly)
                checks += 1
                segment = audit_portal_surface(
                    mesh, poly, entry, exit_xy,
                    required_clearance=required_clearance,
                    sample_spacing=sample_spacing,
                    maximum_grade=maximum_grade)
                if not segment.candidate:
                    continue
                length = math.hypot(exit_xy[0] - entry[0], exit_xy[1] - entry[1])
                next_cost = cost + length
                if exit_xy not in following or next_cost < following[exit_xy][0]:
                    following[exit_xy] = (next_cost, points + (exit_xy,))
        if not following:
            return PortalCorridorCheck(False, "no_sampled_segment_through_polygon",
                                       checks, index + 1, poly,
                                       reachable_entries=tuple(states),
                                       eligible_exits=tuple(exits))
        states = following
    best = min(states.values(), key=lambda state: state[0])
    return PortalCorridorCheck(True, "fixed_corridor_geometry_candidate_only",
                               checks, len(corridor), points=best[1])
