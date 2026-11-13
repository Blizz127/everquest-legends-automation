"""Bounded copied-BSP audit for a selected helper-mesh ground corridor.

This checks static water/zoneline labels at strict detail-triangle heights.
It is an offline diagnostic, never a movement permit or live route acceptance.
The owner helper stores mesh positions as (/loc X, /loc Y, Z), while the
copied WLD BSP expects raw (/loc Y, /loc X, Z): swap XY at that boundary.
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


def verify_helper_bsp_frame(lookup, manifest: dict) -> dict:
    """Require one copied helper trigger to resolve as a raw-WLD zone line."""
    if not isinstance(manifest, dict):
        raise ValueError("Helper mesh manifest is missing")
    lines = manifest.get("extra", {}).get("zone_lines", [])
    if not isinstance(lines, list):
        raise ValueError("Helper mesh has no usable zone-line list")
    for line in lines:
        if not isinstance(line, dict):
            continue
        point = line.get("point")
        if (not isinstance(point, (list, tuple)) or len(point) != 3 or
                any(not isinstance(value, (int, float)) or isinstance(value, bool) or
                    not isfinite(value) for value in point)):
            continue
        wld_point = (float(point[1]), float(point[0]), float(point[2]))
        probe = lookup.probe(*wld_point)
        if probe.zoneline_candidate:
            return {"helper_package_xyz": list(point),
                    "raw_wld_xyz": list(wld_point),
                    "copied_bsp_region_id": probe.region_id,
                    "to_zone_hint": line.get("to_zone"),
                    "labels": list(probe.labels)}
    raise ValueError("Helper-to-WLD frame positive control did not find a copied zone line")


def audit_helper_funnel_bsp(lookup, points: Sequence[Sequence[float]], *,
                            height_offsets: tuple[float, ...] = (0.0, 1.0),
                            max_segments: int = 512,
                            max_total_spans: int = 8192) -> GroundBspRouteAudit:
    """Classify a helper-frame funnel without claiming a ground strip pass."""
    if (not isinstance(points, (tuple, list)) or not 2 <= len(points) <= max_segments + 1 or
            any(not isinstance(point, (tuple, list)) or len(point) != 3 or
                any(not isinstance(value, (int, float)) or isinstance(value, bool) or
                    not isfinite(value) for value in point) for point in points) or
            not isinstance(height_offsets, tuple) or not 1 <= len(height_offsets) <= 4 or
            any(not isinstance(offset, (int, float)) or isinstance(offset, bool) or
                not isfinite(offset) or not 0 <= offset <= 10 for offset in height_offsets) or
            not isinstance(max_total_spans, int) or isinstance(max_total_spans, bool) or
            not 1 <= max_total_spans <= 32768):
        raise ValueError("Helper funnel BSP inputs exceed bounds")
    if any(hypot(b[0] - a[0], b[1] - a[1]) <= 1e-9
           for a, b in zip(points, points[1:])):
        raise ValueError("Helper funnel has an empty XY segment")
    labelled: list[dict] = []
    unknown: list[dict] = []
    span_count = 0
    for offset in height_offsets:
        for index, (a, b) in enumerate(zip(points, points[1:])):
            start = (float(a[1]), float(a[0]), float(a[2] + offset))
            end = (float(b[1]), float(b[0]), float(b[2] + offset))
            spans = lookup.trace_segment(start, end)
            cursor = 0.0
            valid = bool(spans)
            for span in spans:
                if (not isfinite(span.start_fraction) or
                        not isfinite(span.end_fraction) or
                        abs(span.start_fraction - cursor) > 1e-6 or
                        not cursor < span.end_fraction <= 1.0 + 1e-6):
                    valid = False
                    break
                cursor = span.end_fraction
            if abs(cursor - 1.0) > 1e-6:
                valid = False
            if not valid:
                unknown.append({"offset": offset, "index": index,
                                "reason": "invalid_bsp_partition"})
                continue
            span_count += len(spans)
            if span_count > max_total_spans:
                return GroundBspRouteAudit(False, "bsp_span_budget_exceeded",
                                           len(points) - 1, span_count,
                                           tuple(labelled), tuple(unknown))
            for span in spans:
                detail = {"offset": offset, "index": index,
                          "start_fraction": span.start_fraction,
                          "end_fraction": span.end_fraction,
                          "reason": span.reason}
                if span.region_id is None or "unknown" in span.labels:
                    unknown.append(detail)
                if span.labels:
                    labelled.append({**detail, "region_id": span.region_id,
                                     "labels": span.labels})
    reason = ("unknown_bsp_interval" if unknown else
              "labelled_bsp_interval" if labelled else
              "copied_funnel_bsp_candidate_only")
    return GroundBspRouteAudit(not (unknown or labelled), reason,
                               len(points) - 1, span_count,
                               tuple(labelled), tuple(unknown))


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
            # Mesh/detail heights are in the helper package frame; the raw
            # copied WLD BSP plane axes are the reverse XY order.
            start = (float(start_xy[1]), float(start_xy[0]), start_z + offset)
            end = (float(end_xy[1]), float(end_xy[0]), end_z + offset)
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
