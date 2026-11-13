"""Exporter-derived Butcherblock static-instance geometry candidate.

Transform follows LanternExtractor ObjectInstance and MeshObjWriter:
https://github.com/LanternEQ/LanternExtractor/blob/main/LanternExtractor/EQ/Wld/Fragments/ObjectInstance.cs
https://github.com/LanternEQ/LanternExtractor/blob/main/LanternExtractor/EQ/Wld/Exporters/MeshObjWriter.cs
The actual game's collision/material behavior and movement remain unverified.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import cos, isclose, isfinite, pi, sin

from .mesh_geometry import MeshGeometry, read_meshes
from .model_links import combine_model_links
from .placement_audit import ObjectLocation, read_object_locations
from .wld_inventory import WLDInventory


@dataclass(frozen=True)
class InstanceGeometrySummary:
    source_placement_count: int
    dropped_tree_sentinel_count: int
    instanced_model_count: int
    instanced_vertex_count: int
    instanced_polygon_count: int
    flag_zero_count: int
    pass_through_flag_0x10_count: int
    instanced_degenerate_polygon_count: int
    exact_model_name_links: bool
    exporter_transform_candidate: bool = True
    client_alignment_verified: bool = False
    collision_materials_verified: bool = False
    navigability_verified: bool = False


def projected_vertex(mesh: MeshGeometry, location: ObjectLocation,
                     index: int) -> tuple[float, float, float]:
    """Project one model vertex into WLD XYZ using Lantern's observed matrix."""
    if not isclose(location.scale_y, location.scale_x, rel_tol=0, abs_tol=1e-6):
        raise ValueError("Nonuniform object scale is not supported")
    if location.scale_y <= 0 or not isfinite(location.scale_y):
        raise ValueError("Object scale must be finite and positive")
    if location.rot_x != 0:
        raise ValueError("Object X rotation is not supported by this transform")
    if location.dropped_tree_sentinel:
        raise ValueError("Dropped-tree sentinel cannot be projected")
    raw = mesh.raw_vertices[index]
    factor = location.scale_y / (1 << mesh.scale)
    px, py, pz = (value * factor for value in raw)
    yaw = location.rot_z * 2 * pi / 512
    roll = location.rot_y * 2 * pi / 512
    cy, sy = cos(yaw), sin(yaw)
    cr, sr = cos(roll), sin(roll)
    x = cy * px - sy * cr * py + sy * sr * pz
    y = sy * px + cy * cr * py - cy * sr * pz
    z = sr * py + cr * pz
    result = (x + mesh.center[0] + location.x,
              y + mesh.center[1] + location.y,
              z + mesh.center[2] + location.z)
    if not all(map(isfinite, result)):
        raise ValueError("Projected object vertex is nonfinite")
    return result


def summarize_instances(objects: WLDInventory,
                        libraries: tuple[WLDInventory, ...]) -> InstanceGeometrySummary:
    locations = read_object_locations(objects)
    links = combine_model_links(libraries)
    meshes = {library.sha256: {mesh.fragment_index: mesh for mesh in read_meshes(library)}
              for library in libraries}
    vertex_count = polygon_count = solid_count = pass_count = degenerate_count = 0
    usable = 0
    for location in locations:
        if location.dropped_tree_sentinel:
            continue
        if location.actor_name not in links:
            raise ValueError("Object location has no exact static model link")
        library, link = links[location.actor_name]
        if not link.exact_expected_mesh_name:
            raise ValueError("Static actor mesh name does not match exactly")
        mesh = meshes[library.sha256][link.mesh_fragment_index]
        # Project a vertex to validate each instance's transform parameters.
        if mesh.raw_vertices:
            projected_vertex(mesh, location, 0)
        vertex_count += len(mesh.raw_vertices)
        polygon_count += len(mesh.triangles)
        solid_count += sum(face.flag == 0 for face in mesh.triangles)
        pass_count += sum(face.flag == 0x10 for face in mesh.triangles)
        degenerate_count += mesh.degenerate_count()
        usable += 1
    return InstanceGeometrySummary(
        source_placement_count=len(locations),
        dropped_tree_sentinel_count=len(locations) - usable,
        instanced_model_count=usable,
        instanced_vertex_count=vertex_count,
        instanced_polygon_count=polygon_count,
        flag_zero_count=solid_count,
        pass_through_flag_0x10_count=pass_count,
        instanced_degenerate_polygon_count=degenerate_count,
        exact_model_name_links=True,
    )
