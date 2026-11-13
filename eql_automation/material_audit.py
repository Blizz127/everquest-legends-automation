"""Bounded WLD material chain audit for provisional collision geometry.

0x36 polygon groups resolve through 0x31 lists to 0x30 materials. The
byte layout was checked against copied Butcherblock WLDs and EQEmu/Lantern
format sources. Material labels do not prove game collision or water state.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from struct import unpack_from

from .model_links import combine_model_links
from .placement_audit import read_object_locations
from .wld_inventory import WLDFragment, WLDInventory


MATERIAL_CLASSES = {
    0x0: "Boundary",
    0x1: "Diffuse",
    0x553: "Diffuse6",
    0xB: "TransparentAdditiveUnlit",
    0x13: "TransparentMasked",
}


@dataclass(frozen=True)
class FaceMaterial:
    polygon_flag: int
    raw_material_params: int
    material_name: str | None

    @property
    def material_class(self) -> str:
        return MATERIAL_CLASSES.get(self.raw_material_params & 0x7FFFFFFF,
                                    f"Unknown:0x{self.raw_material_params:08x}")


def _fragment_ref(wld: WLDInventory, number: int, expected_type: int) -> WLDFragment:
    if number < 1 or number > len(wld.fragments):
        raise ValueError("WLD material fragment reference is out of range")
    fragment = wld.fragments[number - 1]
    if fragment.type_code != expected_type:
        raise ValueError("WLD material fragment reference has wrong type")
    return fragment


def mesh_face_materials(wld: WLDInventory,
                        mesh: WLDFragment) -> tuple[FaceMaterial, ...]:
    if mesh.type_code != 0x36:
        raise ValueError("Fragment is not a 0x36 mesh")
    body = wld.body(mesh)
    if len(body) < 92:
        raise ValueError("WLD mesh material header is truncated")
    texture_list_number = unpack_from("<I", body, 4)[0]
    texture_list = _fragment_ref(wld, texture_list_number, 0x31)
    list_body = wld.body(texture_list)
    if len(list_body) < 8:
        raise ValueError("WLD 0x31 material list is truncated")
    material_count = unpack_from("<I", list_body, 4)[0]
    if material_count > (len(list_body) - 8) // 4:
        raise ValueError("WLD 0x31 material references exceed fragment bounds")
    material_numbers = unpack_from(f"<{material_count}I", list_body, 8)
    material_fragments = tuple(_fragment_ref(wld, number, 0x30)
                               for number in material_numbers)
    (vertex_count, uv_count, normal_count, color_count, polygon_count,
     piece_count, polygon_texture_count, _vertex_texture_count,
     _data9_count, _scale) = unpack_from("<10H", body, 72)
    polygon_start = 92 + 6 * vertex_count + 4 * uv_count + 3 * normal_count + 4 * color_count
    groups_start = polygon_start + 8 * polygon_count + 4 * piece_count
    if groups_start + 4 * polygon_texture_count > len(body):
        raise ValueError("WLD polygon material groups exceed fragment bounds")
    result = []
    polygon_cursor = 0
    for group_index in range(polygon_texture_count):
        group_count, material_index = unpack_from("<2H", body, groups_start + 4 * group_index)
        if material_index >= len(material_fragments) or polygon_cursor + group_count > polygon_count:
            raise ValueError("WLD polygon material group is invalid")
        material = material_fragments[material_index]
        material_body = wld.body(material)
        if len(material_body) < 8:
            raise ValueError("WLD 0x30 material is truncated")
        raw_params = unpack_from("<I", material_body, 4)[0]
        for polygon_index in range(polygon_cursor, polygon_cursor + group_count):
            flag = unpack_from("<H", body, polygon_start + 8 * polygon_index)[0]
            result.append(FaceMaterial(flag, raw_params, material.name))
        polygon_cursor += group_count
    if polygon_cursor != polygon_count:
        raise ValueError("WLD polygon material groups do not cover all faces")
    return tuple(result)


def summarize_butcher_materials(terrain: WLDInventory, objects: WLDInventory,
                                libraries: tuple[WLDInventory, ...]) -> dict:
    terrain_counts: Counter[tuple[int, str]] = Counter()
    model_counts: Counter[tuple[int, str]] = Counter()
    model_faces = {}
    mesh_count = 0
    for fragment in terrain.fragments:
        if fragment.type_code != 0x36:
            continue
        for face in mesh_face_materials(terrain, fragment):
            terrain_counts[(face.polygon_flag, face.material_class)] += 1
        mesh_count += 1
    for library in libraries:
        for fragment in library.fragments:
            if fragment.type_code != 0x36:
                continue
            faces = mesh_face_materials(library, fragment)
            model_faces[(library.sha256, fragment.index)] = Counter(
                (face.polygon_flag, face.material_class) for face in faces)
            mesh_count += 1
    links = combine_model_links(libraries)
    locations = read_object_locations(objects)
    for location in locations:
        if location.dropped_tree_sentinel:
            continue
        library, link = links[location.actor_name]
        model_counts.update(model_faces[(library.sha256, link.mesh_fragment_index)])
    def printable(counts: Counter[tuple[int, str]]) -> dict[str, int]:
        return {f"flag=0x{flag:x}|{material}": count
                for (flag, material), count in sorted(counts.items())}
    return {
        "mesh_material_chains_checked": mesh_count,
        "terrain_face_material_counts": printable(terrain_counts),
        "instanced_object_face_material_counts": printable(model_counts),
        "terrain_boundary_flag_zero_faces": terrain_counts[(0, "Boundary")],
        "instanced_object_boundary_flag_zero_faces": model_counts[(0, "Boundary")],
        "material_references_verified": True,
        "collision_classification_verified": False,
        "water_regions_verified": False,
        "navigability_verified": False,
    }
