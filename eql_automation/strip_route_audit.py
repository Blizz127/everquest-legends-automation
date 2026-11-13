"""Bounded offline strip scan of one copied-mesh portal route.

This applies the single-segment strip diagnostic in route order and returns
the first failure. Even a pass is only a sampled geometry candidate: turns,
follower error, dynamic obstacles, zone arrival and client motion are not
certified here.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import time

from .lateral_strip_audit import LateralStripCheck, audit_segment_strip
from .portal_surface_audit import audit_portal_seam


@dataclass(frozen=True)
class StripRouteCheck:
    candidate: bool
    reason: str
    checked_segments: int = 0
    samples: int = 0
    failed_segment: int | None = None
    failed_polygon: int | None = None
    segment_result: LateralStripCheck | None = None
    real_client_accepted: bool = False


def audit_route_strips(mesh, polygons: tuple[int, ...],
                       points: tuple[tuple[float, float], ...], *,
                       max_segments: int = 200,
                       max_total_samples: int = 20000,
                       max_seconds: float = 20.0,
                       half_width: float = 1.2) -> StripRouteCheck:
    if (not isinstance(max_segments, int) or isinstance(max_segments, bool) or max_segments < 1 or
            not isinstance(max_total_samples, int) or isinstance(max_total_samples, bool) or
            max_total_samples < 1 or
            not isinstance(max_seconds, (int, float)) or isinstance(max_seconds, bool) or
            not math.isfinite(max_seconds) or max_seconds <= 0 or
            not isinstance(half_width, (int, float)) or isinstance(half_width, bool) or
            not math.isfinite(half_width) or half_width <= 0 or
            not isinstance(polygons, tuple) or not polygons or len(polygons) > max_segments or
            any(not isinstance(poly, int) or isinstance(poly, bool) or poly < 0
                for poly in polygons) or
            not isinstance(points, tuple) or len(points) != len(polygons) + 1 or
            any(not isinstance(point, tuple) or len(point) != 2 or
                any(not isinstance(v, (int, float)) or isinstance(v, bool) or
                    not math.isfinite(v) for v in point)
                for point in points)):
        return StripRouteCheck(False, "invalid_route_limits")
    started = time.monotonic()
    total_samples = 0
    for index, poly in enumerate(polygons):
        remaining = max_seconds - (time.monotonic() - started)
        if remaining <= 0 or total_samples >= max_total_samples:
            return StripRouteCheck(False, "route_work_budget_exceeded",
                                   index, total_samples, index, poly)
        if index:
            try:
                same_component = (int(mesh.component[polygons[index - 1]]) ==
                                  int(mesh.component[poly]) >= 0)
            except (AttributeError, IndexError, KeyError, TypeError):
                same_component = False
            if not same_component:
                return StripRouteCheck(False, "seam_component_unknown",
                                       index, total_samples, index, poly)
            seam = audit_portal_seam(mesh, polygons[index - 1], poly,
                                     points[index])
            if not seam.candidate:
                return StripRouteCheck(False, "seam_" + seam.reason,
                                       index, total_samples, index, poly)
        result = audit_segment_strip(mesh, poly, points[index], points[index + 1],
                                     half_width=half_width,
                                     max_seconds=min(remaining, 3.0))
        total_samples += result.samples
        if total_samples > max_total_samples:
            return StripRouteCheck(False, "route_work_budget_exceeded",
                                   index + 1, total_samples, index, poly, result)
        if not result.candidate:
            return StripRouteCheck(False, "segment_" + result.reason,
                                   index + 1, total_samples, index, poly, result)
    return StripRouteCheck(True, "sampled_strip_candidate_only",
                           len(polygons), total_samples)
