"""Cross-check client map drawing coordinates against copied WLD terrain.

Matching vertices and label/triangle intersections are offline geometric
evidence only. They do not make map lines walkable or zone labels actionable.
"""
from __future__ import annotations

from math import ceil, isfinite

from .client_ingest import MapDocument
from .mesh_geometry import MeshGeometry
from .nav import Point


TRANSFORMS = ("x,y", "x,-y", "-x,y", "-x,-y",
              "y,x", "y,-x", "-y,x", "-y,-x")


def map_to_wld_xy(x: float, y: float, transform: str) -> tuple[float, float]:
    return {
        "x,y": (x, y), "x,-y": (x, -y), "-x,y": (-x, y),
        "-x,-y": (-x, -y), "y,x": (y, x), "y,-x": (y, -x),
        "-y,x": (-y, x), "-y,-x": (-y, -x),
    }[transform]


def _rounded(point: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(round(value, 1) for value in point)


def _triangle_height(x: float, y: float,
                     vertices: tuple[tuple[float, float, float], ...]) -> float | None:
    a, b, c = vertices
    if (x < min(a[0], b[0], c[0]) or x > max(a[0], b[0], c[0]) or
            y < min(a[1], b[1], c[1]) or y > max(a[1], b[1], c[1])):
        return None
    denominator = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    if abs(denominator) < 1e-8:
        return None
    alpha = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / denominator
    beta = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / denominator
    gamma = 1.0 - alpha - beta
    if min(alpha, beta, gamma) < -1e-6:
        return None
    height = alpha * a[2] + beta * b[2] + gamma * c[2]
    return height if isfinite(height) else None


def _label_surface(label: Point, triangles: list[tuple[tuple[float, float, float], ...]],
                   transform: str) -> dict:
    x, y = map_to_wld_xy(label.x, label.y, transform)
    heights = {round(height, 4)
               for triangle in triangles
               if (height := _triangle_height(x, y, triangle)) is not None}
    ordered = sorted(heights, key=lambda height: (abs(height - label.z), height))
    return {
        "map_xyz": [label.x, label.y, label.z],
        "wld_xy": [x, y],
        "flag_zero_surface_height_count": len(ordered),
        "nearest_surface_z": ordered[0] if ordered else None,
        "nearest_abs_z_offset": round(abs(ordered[0] - label.z), 4) if ordered else None,
        "nearest_surface_heights": ordered[:5],
    }


def audit_map_alignment(map_document: MapDocument,
                        meshes: tuple[MeshGeometry, ...],
                        label_document: MapDocument | None = None) -> dict:
    terrain_vertices = {_rounded(mesh.vertex(index))
                        for mesh in meshes for index in range(len(mesh.raw_vertices))}
    map_points = {_rounded((point.x, point.y, point.z))
                  for line in map_document.lines for point in (line.start, line.end)}
    scores = {transform: sum(_rounded((*map_to_wld_xy(x, y, transform), z))
                             in terrain_vertices for x, y, z in map_points)
              for transform in TRANSFORMS}
    ranked = sorted(scores, key=lambda transform: (-scores[transform], transform))
    best = ranked[0] if ranked and scores[ranked[0]] > 0 else None
    second = scores[ranked[1]] if len(ranked) > 1 else 0
    frame_supported = bool(best and scores[best] >= max(3, ceil(0.05 * len(map_points)))
                           and scores[best] >= 3 * (second + 1))
    triangles: list[tuple[tuple[float, float, float], ...]] = []
    if frame_supported and label_document is not None:
        for mesh in meshes:
            vertices = tuple(mesh.vertex(index) for index in range(len(mesh.raw_vertices)))
            triangles.extend((vertices[face.a], vertices[face.b], vertices[face.c])
                             for face in mesh.triangles if face.flag == 0)
    labels = []
    if frame_supported and label_document is not None:
        for label in label_document.labels:
            labels.append({"text": label.text,
                           **_label_surface(label.point, triangles, best)})
    return {
        "map_line_count": len(map_document.lines),
        "unique_map_points": len(map_points),
        "unique_terrain_vertices": len(terrain_vertices),
        "matching_vertices_by_transform": scores,
        "best_map_to_wld_xy_transform": best,
        "frame_supported_by_rounded_vertex_matches": frame_supported,
        "best_match_count": scores[best] if best else 0,
        "second_best_match_count": second,
        "label_surface_candidates": labels,
        "map_drawing_edges_walkable": False,
        "zone_labels_actionable": False,
        "live_client_alignment_verified": False,
    }
