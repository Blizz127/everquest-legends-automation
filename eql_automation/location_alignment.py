"""Score historical client /loc triples against copied WLD terrain offline.

This is a comparison tool, not a transform calibration or navigation source.
Raw log axes, character height, collision surfaces, and live alignment remain
unverified even when one candidate scores better than the others.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from statistics import median
from typing import Iterable

from .location_log import parse_client_log_line, parse_raw_location
from .map_alignment import TRANSFORMS, _triangle_height, map_to_wld_xy
from .mesh_geometry import MeshGeometry


@dataclass(frozen=True)
class HistoricalLocation:
    raw_coordinates: tuple[float, float, float]
    source_local_time: datetime
    zone_display_name: str


def historical_zone_locations(lines: Iterable[str], zone_display_name: str, *,
                              max_lines: int = 10000,
                              max_samples: int = 64) -> tuple[HistoricalLocation, ...]:
    """Select only explicit /loc lines after a matching entered-zone message."""
    if (not zone_display_name or not isinstance(max_lines, int) or
            not isinstance(max_samples, int) or max_lines <= 0 or
            not 1 <= max_samples <= 64):
        raise ValueError("Invalid historical location audit limits")
    current_zone: str | None = None
    last_source_time: datetime | None = None
    samples: list[HistoricalLocation] = []
    for line_number, line in enumerate(lines, 1):
        if line_number > max_lines:
            raise ValueError("Historical log line budget exceeded")
        parsed = parse_client_log_line(line)
        if parsed is None:
            if "LOADING, PLEASE WAIT" in line or "You have entered " in line:
                current_zone = None
            continue
        source_time, body = parsed
        if last_source_time is not None and source_time < last_source_time:
            current_zone = None
            last_source_time = None
            continue
        last_source_time = source_time
        if body.startswith("LOADING, PLEASE WAIT"):
            current_zone = None
            continue
        if body.startswith("You have entered "):
            current_zone = (body[len("You have entered "):-1]
                            if body.endswith(".") else None)
            continue
        if current_zone != zone_display_name:
            continue
        raw = parse_raw_location(body)
        if raw is None:
            if body.startswith("Your Location is "):
                current_zone = None
            continue
        if len(samples) >= max_samples:
            raise ValueError("Historical location sample budget exceeded")
        samples.append(HistoricalLocation(raw, source_time, current_zone))
    return tuple(samples)


def score_location_transforms(samples: tuple[HistoricalLocation, ...],
                              meshes: tuple[MeshGeometry, ...], *,
                              offset_tolerance: float = 0.5,
                              max_triangles: int = 100000) -> dict:
    """Compare all eight XY sign/swap candidates using flag-zero surfaces.

    The nearest terrain height is a geometric heuristic. A coherent vertical
    offset may reflect eye height, another surface, or unrelated geometry.
    """
    if (not 1 <= len(samples) <= 64 or
            not isinstance(offset_tolerance, (int, float)) or
            isinstance(offset_tolerance, bool) or
            not isfinite(offset_tolerance) or offset_tolerance <= 0 or
            not isinstance(max_triangles, int) or isinstance(max_triangles, bool) or
            not 1 <= max_triangles <= 100000):
        raise ValueError("Invalid location alignment audit limits")
    if any(not all(isfinite(value) for value in sample.raw_coordinates)
           for sample in samples):
        raise ValueError("Historical location contains nonfinite coordinate")
    distinct_coordinates = tuple(dict.fromkeys(
        sample.raw_coordinates for sample in samples))
    triangles: list[tuple[tuple[float, float, float], ...]] = []
    for mesh in meshes:
        vertices = tuple(mesh.vertex(index) for index in range(len(mesh.raw_vertices)))
        for face in mesh.triangles:
            if face.flag == 0:
                if len(triangles) >= max_triangles:
                    raise ValueError("Terrain triangle budget exceeded")
                triangles.append((vertices[face.a], vertices[face.b], vertices[face.c]))
    if not triangles:
        raise ValueError("No flag-zero terrain triangles")
    bounded = [(min(point[0] for point in triangle),
                max(point[0] for point in triangle),
                min(point[1] for point in triangle),
                max(point[1] for point in triangle), triangle)
               for triangle in triangles]
    scores = []
    for transform in TRANSFORMS:
        residuals: list[float | None] = []
        for raw_x, raw_y, raw_z in distinct_coordinates:
            x, y = map_to_wld_xy(raw_x, raw_y, transform)
            heights = (height for min_x, max_x, min_y, max_y, triangle in bounded
                       if min_x <= x <= max_x and min_y <= y <= max_y
                       if (height := _triangle_height(x, y, triangle)) is not None)
            nearest = min(heights, key=lambda height: abs(raw_z - height),
                          default=None)
            residuals.append(None if nearest is None else raw_z - nearest)
        covered = [value for value in residuals if value is not None]
        offset = median(covered) if covered else None
        coherent = (sum(abs(value - offset) <= offset_tolerance for value in covered)
                    if offset is not None else 0)
        deviation = (median(abs(value - offset) for value in covered)
                     if offset is not None else None)
        scores.append({
            "transform": transform,
            "surface_coverage_count": len(covered),
            "coherent_offset_count": coherent,
            "median_raw_z_minus_terrain_z": round(offset, 4) if offset is not None else None,
            "median_absolute_offset_deviation": round(deviation, 4) if deviation is not None else None,
            "raw_z_minus_nearest_terrain_z": [round(value, 4) if value is not None else None
                                                for value in residuals],
        })
    scores.sort(key=lambda item: (-item["coherent_offset_count"],
                                  -item["surface_coverage_count"],
                                  item["median_absolute_offset_deviation"]
                                  if item["median_absolute_offset_deviation"] is not None
                                  else float("inf"), item["transform"]))
    return {
        "historical_sample_count": len(samples),
        "distinct_raw_coordinate_count": len(distinct_coordinates),
        "repeated_coordinate_count": len(samples) - len(distinct_coordinates),
        "flag_zero_terrain_triangle_count": len(triangles),
        "offset_tolerance": offset_tolerance,
        "candidate_scores": scores,
        "accepted_log_to_wld_transform": None,
        "live_alignment_verified": False,
        "navigation_edge_accepted": False,
    }
