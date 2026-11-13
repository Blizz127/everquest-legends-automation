"""Sample provisional Detour straight paths against copied WLD BSP labels.

This catches some labelled water/zoneline candidates. Missing labels, narrow
volumes, doors, aggro, collision and client/server differences remain unknown.
No result from this module accepts a route or authorizes movement.
"""
from __future__ import annotations

from collections import Counter
from math import ceil, dist, isfinite
from typing import Sequence

from .bsp_probe import BspPointLookup


MAX_PATH_POINTS = 256
MAX_SAMPLES = 20000


def audit_path_hazards(lookup: BspPointLookup,
                       path: Sequence[Sequence[float]], *,
                       requested_start: Sequence[float],
                       requested_end: Sequence[float],
                       spacing: float = 5.0,
                       query_complete: bool = False,
                       start_snap_distance: float | None = None,
                       end_snap_distance: float | None = None) -> dict:
    if (not isinstance(spacing, (int, float)) or isinstance(spacing, bool) or
            not isfinite(spacing) or not 1 <= spacing <= 20):
        raise ValueError("Path sample spacing is outside bounds")
    if not isinstance(query_complete, bool):
        raise ValueError("Query completion must be boolean")
    if not isinstance(path, (list, tuple)) or not 2 <= len(path) <= MAX_PATH_POINTS:
        raise ValueError("Straight path point count is outside bounds")
    def point(row: Sequence[float]) -> tuple[float, float, float]:
        if (not isinstance(row, (list, tuple)) or len(row) != 3 or
                not all(isinstance(value, (int, float)) and
                        not isinstance(value, bool) and isfinite(value)
                        for value in row)):
            raise ValueError("Path endpoint has invalid WLD XYZ")
        return tuple(float(value) for value in row)

    points = [point(row) for row in path]
    requested_first = point(requested_start)
    requested_last = point(requested_end)
    for value in (start_snap_distance, end_snap_distance):
        if value is not None and (not isinstance(value, (int, float)) or
                                  isinstance(value, bool) or not isfinite(value) or value < 0):
            raise ValueError("Endpoint snap distance is invalid")
    start_connector = dist(requested_first, points[0])
    end_connector = dist(points[-1], requested_last)
    if not isfinite(start_connector) or not isfinite(end_connector):
        raise ValueError("Endpoint connector length is nonfinite")
    if (start_snap_distance is not None and
            abs(start_connector - start_snap_distance) > max(0.05, 0.05 * start_snap_distance)):
        raise ValueError("Start snap distance disagrees with path endpoint")
    if (end_snap_distance is not None and
            abs(end_connector - end_snap_distance) > max(0.05, 0.05 * end_snap_distance)):
        raise ValueError("End snap distance disagrees with path endpoint")
    sampled_points = ([requested_first] if start_connector > 1e-6 else []) + points + (
        [requested_last] if end_connector > 1e-6 else [])
    segment_steps = []
    for start, end in zip(sampled_points, sampled_points[1:]):
        length = dist(start, end)
        if not isfinite(length):
            raise ValueError("Straight path length is nonfinite")
        segment_steps.append(max(1, ceil(length / spacing)))
    sample_count = 1 + sum(segment_steps)
    if sample_count > MAX_SAMPLES:
        raise ValueError("Straight path sampling exceeds cap")

    label_counts: Counter[str] = Counter()
    unknown = 0
    labelled = 0
    first_labelled = None
    first_unknown = None
    for segment_index, (start, end) in enumerate(zip(sampled_points, sampled_points[1:])):
        steps = segment_steps[segment_index]
        for step in range(0 if segment_index == 0 else 1, steps + 1):
            fraction = step / steps
            point = tuple(start[index] + (end[index] - start[index]) * fraction
                          for index in range(3))
            probe = lookup.probe(*point)
            if probe.region_id is None or "unknown" in probe.labels:
                unknown += 1
                if first_unknown is None:
                    first_unknown = {"wld_xyz": point, "reason": probe.reason}
            if probe.labels:
                labelled += 1
                label_counts.update(probe.labels)
                if first_labelled is None:
                    first_labelled = {"wld_xyz": point, "region_id": probe.region_id,
                                      "labels": probe.labels}
    return {
        "straight_path_points": len(points),
        "sampled_polyline_points": len(sampled_points),
        "requested_start_connector_length": round(start_connector, 6),
        "requested_end_connector_length": round(end_connector, 6),
        "sample_spacing_max": spacing,
        "sample_count": sample_count,
        "query_complete": query_complete,
        "start_snap_distance": start_snap_distance,
        "end_snap_distance": end_snap_distance,
        "label_sample_counts": dict(sorted(label_counts.items())),
        "labelled_region_sample_count": labelled,
        "unknown_region_sample_count": unknown,
        "first_labelled_sample": first_labelled,
        "first_unknown_sample": first_unknown,
        "route_accepted": False,
        "movement_verified": False,
        "collision_verified": False,
    }
