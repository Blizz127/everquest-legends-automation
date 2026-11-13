"""Bounded copied-BSP audit for a selected ground corridor.

This checks static water/zoneline labels at strict detail-triangle heights.
It is an offline diagnostic, never a movement permit or live route acceptance.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import hypot, isfinite
from typing import Sequence

from .portal_surface_audit import _supported_detail_height


@dataclass(frozen=True)
class GroundBspRouteAudit:
    candidate: bool
    reason: str
    segments: int
    bsp_spans: int
    labelled: tuple[dict, ...] = ()
    unknown: tuple[dict, ...] = ()
    unsupported_height: tuple[dict, ...] = ()
    route_accepted: bool = False
    real_client_accepted: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def audit_ground_bsp_route(mesh, lookup, polygons: Sequence[int],
                           points: Sequence[Sequence[float]], *,
                           height_offsets: tuple[float, ...] = (0.0, 1.0),
                           max_segments: int = 220,
                           max_total_spans: int = 8192) -> GroundBspRouteAudit:
    """Trace each ground segment at copied-mesh height and selected offsets.

    A point at a portal is evaluated separately in each adjoining polygon.
    Unknown BSP intervals, labelled regions, unsupported detail heights and
    non-ground polygons all reject the static candidate. Even a clean result
    says nothing about live obstacles, movement or a zone trigger beyond the
    supplied polygon chain.
    """
    if (not isinstance(max_segments, int) or isinstance(max_segments, bool) or
            not 1 <= max_segments <= 512 or
            not isinstance(max_total_spans, int) or isinstance(max_total_spans, bool) or
            not 1 <= max_total_spans <= 32768 or
            not isinstance(height_offsets, tuple) or
            not 1 <= len(height_offsets) <= 4 or
            any(not isinstance(offset, (int, float)) or isinstance(offset, bool) or
                not isfinite(offset) or not 0 <= offset <= 10
                for offset in height_offsets)):
        raise ValueError("Ground BSP audit limits are invalid")
    if (not isinstance(polygons, (list, tuple)) or
            not 1 <= len(polygons) <= max_segments or
            not isinstance(points, (list, tuple)) or
            len(points) != len(polygons) + 1):
        raise ValueError("Ground BSP route needs one more point than polygons")
    if any(not isinstance(poly, int) or isinstance(poly, bool) or poly < 0
           for poly in polygons):
        raise ValueError("Ground BSP route has an invalid polygon index")
    if any(not isinstance(point, (list, tuple)) or len(point) != 2 or
           any(not isinstance(axis, (int, float)) or isinstance(axis, bool) or
               not isfinite(axis) for axis in point)
           for point in points):
        raise ValueError("Ground BSP route needs finite XY points")
    if any(hypot(end[0] - start[0], end[1] - start[1]) <= 1e-9
           for start, end in zip(points, points[1:])):
        raise ValueError("Ground BSP route has an empty segment")

    labelled: list[dict] = []
    unknown: list[dict] = []
    unsupported: list[dict] = []
    spans_seen = 0
    for offset in height_offsets:
        for index, poly in enumerate(polygons):
            try:
                area = int(mesh.area[poly])
            except (AttributeError, IndexError, KeyError, TypeError):
                area = None
            if area != 63:
                unsupported.append({"offset": offset, "index": index,
                                    "polygon": poly, "reason": "non_ground_polygon"})
                continue
            start_xy, end_xy = points[index:index + 2]
            start_z = _supported_detail_height(mesh, poly, *start_xy)
            end_z = _supported_detail_height(mesh, poly, *end_xy)
            if start_z is None or end_z is None:
                unsupported.append({"offset": offset, "index": index,
                                    "polygon": poly, "reason": "unsupported_detail_height"})
                continue
            start = (float(start_xy[0]), float(start_xy[1]), start_z + offset)
            end = (float(end_xy[0]), float(end_xy[1]), end_z + offset)
            spans = lookup.trace_segment(start, end)
            cursor = 0.0
            partition_valid = bool(spans)
            for span in spans:
                if (not isinstance(span.start_fraction, (int, float)) or
                        not isinstance(span.end_fraction, (int, float)) or
                        not isfinite(span.start_fraction) or
                        not isfinite(span.end_fraction) or
                        abs(span.start_fraction - cursor) > 1e-6 or
                        not cursor < span.end_fraction <= 1.0 + 1e-6):
                    partition_valid = False
                    break
                cursor = span.end_fraction
            if abs(cursor - 1.0) > 1e-6:
                partition_valid = False
            if not partition_valid:
                unknown.append({"offset": offset, "index": index,
                                "polygon": poly, "reason": "invalid_bsp_partition"})
                continue
            spans_seen += len(spans)
            if spans_seen > max_total_spans:
                return GroundBspRouteAudit(False, "bsp_span_budget_exceeded",
                                           len(polygons), spans_seen,
                                           tuple(labelled), tuple(unknown),
                                           tuple(unsupported))
            for span in spans:
                detail = {"offset": offset, "index": index,
                          "polygon": poly, "start_fraction": span.start_fraction,
                          "end_fraction": span.end_fraction,
                          "reason": span.reason}
                if span.region_id is None or "unknown" in span.labels:
                    unknown.append(detail)
                if span.labels:
                    labelled.append({**detail, "region_id": span.region_id,
                                     "labels": span.labels})
    if unsupported:
        reason = "unsupported_ground_height_or_area"
    elif unknown:
        reason = "unknown_bsp_interval"
    elif labelled:
        reason = "labelled_bsp_interval"
    else:
        reason = "copied_static_bsp_candidate_only"
    return GroundBspRouteAudit(not (unsupported or unknown or labelled), reason,
                               len(polygons), spans_seen, tuple(labelled),
                               tuple(unknown), tuple(unsupported))
