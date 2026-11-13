"""Compose a provisional WLD-XYZ solid-flag mesh outside git.

This intentionally does not classify shaders/materials, water, doors or
walkability. The output is a reproducible geometry input for later navmesh
work, not an accepted collision mesh or route.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TextIO
import os

from .instance_geometry import projected_vertex
from .mesh_geometry import MeshGeometry, read_meshes
from .model_links import combine_model_links
from .placement_audit import ObjectLocation, read_object_locations
from .wld_inventory import WLDInventory


MAX_OUTPUT_VERTICES = 2_000_000
MAX_OUTPUT_FACES = 2_000_000


@dataclass(frozen=True)
class CandidateScene:
    path: str
    sha256: str
    coordinate_system: str
    vertex_count: int
    face_count: int
    terrain_face_count: int
    object_face_count: int
    pass_through_faces_skipped: int
    degenerate_faces_skipped: int
    dropped_tree_instances_skipped: int
    geometry_composed: bool = True
    collision_materials_verified: bool = False
    dynamic_obstacles_verified: bool = False
    navigability_verified: bool = False


def _append_solid_mesh(output: TextIO, mesh: MeshGeometry,
                       location: ObjectLocation | None,
                       base_vertex: int) -> tuple[int, int, int, int]:
    if any(face.flag not in (0, 0x10) for face in mesh.triangles):
        raise ValueError("Unknown WLD polygon flag in candidate scene")
    pass_through = sum(face.flag == 0x10 for face in mesh.triangles)
    degenerate = sum(face.flag == 0 and mesh.is_degenerate(face)
                     for face in mesh.triangles)
    faces = [face for face in mesh.triangles
             if face.flag == 0 and not mesh.is_degenerate(face)]
    used = sorted({index for face in faces for index in (face.a, face.b, face.c)})
    if base_vertex + len(used) > MAX_OUTPUT_VERTICES:
        raise ValueError("Candidate scene exceeds vertex safety limit")
    mapping = {source: base_vertex + position + 1 for position, source in enumerate(used)}
    for source in used:
        vertex = mesh.vertex(source) if location is None else projected_vertex(mesh, location, source)
        output.write("v {:.9g} {:.9g} {:.9g}\n".format(*vertex))
    for face in faces:
        output.write("f {} {} {}\n".format(mapping[face.a], mapping[face.b], mapping[face.c]))
    return len(used), len(faces), pass_through, degenerate


def write_candidate_scene(directory: Path, terrain: WLDInventory,
                          objects: WLDInventory,
                          libraries: tuple[WLDInventory, ...]) -> CandidateScene:
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    terrain_meshes = read_meshes(terrain)
    links = combine_model_links(libraries)
    model_meshes = {library.sha256: {mesh.fragment_index: mesh for mesh in read_meshes(library)}
                    for library in libraries}
    locations = read_object_locations(objects)
    vertex_count = face_count = terrain_faces = object_faces = pass_through = degenerate = dropped = 0
    temp_path: Path | None = None
    try:
        with NamedTemporaryFile("w", encoding="ascii", prefix="butcher-candidate-",
                                suffix=".obj.tmp", dir=directory, delete=False) as output:
            temp_path = Path(output.name)
            output.write("# Provisional Butcherblock geometry in WLD XYZ (Z up)\n")
            output.write("# Solid flag 0 only; materials, doors, water and movement unverified\n")
            for mesh in terrain_meshes:
                vertices, faces, skipped, zero_area = _append_solid_mesh(
                    output, mesh, None, vertex_count)
                vertex_count += vertices
                face_count += faces
                terrain_faces += faces
                pass_through += skipped
                degenerate += zero_area
                if face_count > MAX_OUTPUT_FACES:
                    raise ValueError("Candidate scene exceeds face safety limit")
            for location in locations:
                if location.dropped_tree_sentinel:
                    dropped += 1
                    continue
                if location.actor_name not in links:
                    raise ValueError("Object location lacks exact model link")
                library, link = links[location.actor_name]
                if not link.exact_expected_mesh_name:
                    raise ValueError("Object mesh name does not match actor definition")
                mesh = model_meshes[library.sha256][link.mesh_fragment_index]
                vertices, faces, skipped, zero_area = _append_solid_mesh(
                    output, mesh, location, vertex_count)
                vertex_count += vertices
                face_count += faces
                object_faces += faces
                pass_through += skipped
                degenerate += zero_area
                if face_count > MAX_OUTPUT_FACES:
                    raise ValueError("Candidate scene exceeds face safety limit")
            output.flush()
            os.fsync(output.fileno())
        digest = sha256(temp_path.read_bytes()).hexdigest()
        final = directory / f"butcher-solid-candidate-{digest[:16]}.obj"
        if final.exists():
            if sha256(final.read_bytes()).hexdigest() != digest:
                raise ValueError("Existing candidate filename has different content")
            temp_path.unlink()
        else:
            os.replace(temp_path, final)
        temp_path = None
        return CandidateScene(str(final), digest, "WLD XYZ, Z up", vertex_count,
                              face_count, terrain_faces, object_faces,
                              pass_through, degenerate, dropped)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
