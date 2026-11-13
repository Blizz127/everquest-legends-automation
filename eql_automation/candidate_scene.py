"""Compose a provisional WLD-XYZ solid-flag mesh outside git.

This can filter faces carrying the copied client's Boundary material label.
That label does not establish collision, water, door, or walkability behavior.
The output is a reproducible geometry input, not an accepted route.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TextIO
import os

from .instance_geometry import projected_vertex
from .material_audit import FaceMaterial, mesh_face_materials
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
    boundary_faces_skipped: int
    boundary_mode: str
    geometry_composed: bool = True
    collision_materials_verified: bool = False
    dynamic_obstacles_verified: bool = False
    navigability_verified: bool = False


def _append_solid_mesh(output: TextIO, mesh: MeshGeometry,
                       location: ObjectLocation | None,
                       base_vertex: int,
                       material_faces: tuple[FaceMaterial, ...] | None = None) -> tuple[int, int, int, int, int]:
    if any(face.flag not in (0, 0x10) for face in mesh.triangles):
        raise ValueError("Unknown WLD polygon flag in candidate scene")
    if material_faces is not None and len(material_faces) != len(mesh.triangles):
        raise ValueError("Candidate mesh material count does not match faces")
    pass_through = sum(face.flag == 0x10 for face in mesh.triangles)
    degenerate = sum(face.flag == 0 and mesh.is_degenerate(face)
                     for face in mesh.triangles)
    boundary = sum(face.flag == 0 and not mesh.is_degenerate(face) and
                   material_faces is not None and material_faces[index].material_class == "Boundary"
                   for index, face in enumerate(mesh.triangles))
    faces = [face for index, face in enumerate(mesh.triangles)
             if face.flag == 0 and not mesh.is_degenerate(face) and
             (material_faces is None or material_faces[index].material_class != "Boundary")]
    used = sorted({index for face in faces for index in (face.a, face.b, face.c)})
    if base_vertex + len(used) > MAX_OUTPUT_VERTICES:
        raise ValueError("Candidate scene exceeds vertex safety limit")
    mapping = {source: base_vertex + position + 1 for position, source in enumerate(used)}
    for source in used:
        vertex = mesh.vertex(source) if location is None else projected_vertex(mesh, location, source)
        output.write("v {:.9g} {:.9g} {:.9g}\n".format(*vertex))
    for face in faces:
        # The client WLD face order points most ground normals downward;
        # LanternExtractor's OBJ writer emits vertex3, vertex2, vertex1.
        output.write("f {} {} {}\n".format(mapping[face.c], mapping[face.b], mapping[face.a]))
    return len(used), len(faces), pass_through, degenerate, boundary


def write_candidate_scene(directory: Path, terrain: WLDInventory,
                          objects: WLDInventory,
                          libraries: tuple[WLDInventory, ...],
                          *, include_boundary: bool = True,
                          zone_name: str = "Butcherblock",
                          filename_prefix: str = "butcher") -> CandidateScene:
    if not zone_name.isalpha() or not filename_prefix.isalpha():
        raise ValueError("Candidate scene zone name and prefix must be alphabetic")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    terrain_meshes = read_meshes(terrain)
    links = combine_model_links(libraries)
    model_meshes = {library.sha256: {mesh.fragment_index: mesh for mesh in read_meshes(library)}
                    for library in libraries}
    locations = read_object_locations(objects)
    vertex_count = face_count = terrain_faces = object_faces = pass_through = degenerate = dropped = boundary = 0
    temp_path: Path | None = None
    try:
        with NamedTemporaryFile("w", encoding="ascii", prefix=f"{filename_prefix}-candidate-",
                                suffix=".obj.tmp", dir=directory, delete=False) as output:
            temp_path = Path(output.name)
            output.write(f"# Provisional {zone_name} geometry in WLD XYZ (Z up)\n")
            output.write("# Solid flag 0 only; materials, doors, water and movement unverified\n")
            if not include_boundary:
                output.write("# Boundary material faces excluded; collision remains unverified\n")
            for mesh in terrain_meshes:
                materials = None if include_boundary else mesh_face_materials(
                    terrain, terrain.fragments[mesh.fragment_index])
                vertices, faces, skipped, zero_area, excluded_boundary = _append_solid_mesh(
                    output, mesh, None, vertex_count, materials)
                vertex_count += vertices
                face_count += faces
                terrain_faces += faces
                pass_through += skipped
                degenerate += zero_area
                boundary += excluded_boundary
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
                materials = None if include_boundary else mesh_face_materials(
                    library, library.fragments[link.mesh_fragment_index])
                vertices, faces, skipped, zero_area, excluded_boundary = _append_solid_mesh(
                    output, mesh, location, vertex_count, materials)
                vertex_count += vertices
                face_count += faces
                object_faces += faces
                pass_through += skipped
                degenerate += zero_area
                boundary += excluded_boundary
                if face_count > MAX_OUTPUT_FACES:
                    raise ValueError("Candidate scene exceeds face safety limit")
            output.flush()
            os.fsync(output.fileno())
        digest = sha256(temp_path.read_bytes()).hexdigest()
        final = directory / f"{filename_prefix}-solid-candidate-{digest[:16]}.obj"
        if final.exists():
            if sha256(final.read_bytes()).hexdigest() != digest:
                raise ValueError("Existing candidate filename has different content")
            temp_path.unlink()
        else:
            os.replace(temp_path, final)
        temp_path = None
        return CandidateScene(str(final), digest, "WLD XYZ, Z up", vertex_count,
                              face_count, terrain_faces, object_faces,
                              pass_through, degenerate, dropped, boundary,
                              "included" if include_boundary else "excluded")
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
