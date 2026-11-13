"""Material chain checks distinguish a boundary face from an ordinary solid face."""
from struct import pack, pack_into

import pytest

from eql_automation.material_audit import mesh_face_materials
from eql_automation.wld_inventory import WLDInventory, XOR_KEY


def material_wld(material_ref=1, group_count=1) -> WLDInventory:
    names = b"\x00WALL_MDF\x00"
    encoded = bytes(value ^ XOR_KEY[index % len(XOR_KEY)]
                    for index, value in enumerate(names))
    material_body = pack("<II", 2, 0)  # Boundary material parameters.
    material = pack("<IIi", len(material_body) + 4, 0x30, -1) + material_body
    list_body = pack("<III", 0, 1, material_ref)
    materials = pack("<IIi", len(list_body) + 4, 0x31, 0) + list_body
    mesh_body = bytearray(92)
    pack_into("<I", mesh_body, 4, 2)  # 1-based 0x31 fragment number.
    pack_into("<10H", mesh_body, 72, 3, 0, 0, 0, 1, 0, 1, 0, 0, 1)
    mesh_body.extend(pack("<9h", 0, 0, 0, 2, 0, 0, 0, 2, 0))
    mesh_body.extend(pack("<4H", 0, 0, 1, 2))
    mesh_body.extend(pack("<2H", group_count, 0))
    mesh = pack("<IIi", len(mesh_body) + 4, 0x36, 0) + mesh_body
    header = pack("<7I", 0x54503D02, 0x00015500, 3, 0, 0, len(names), 0)
    return WLDInventory(header + encoded + material + materials + mesh + b"\xff" * 4)


def test_boundary_material_is_resolved_through_texture_group():
    wld = material_wld()
    faces = mesh_face_materials(wld, wld.fragments[2])
    assert len(faces) == 1
    assert faces[0].material_class == "Boundary"
    assert faces[0].material_name == "WALL_MDF"
    assert faces[0].polygon_flag == 0


def test_wrong_material_ref_and_uncovered_polygon_are_rejected():
    wld = material_wld(material_ref=3)
    with pytest.raises(ValueError, match="wrong type"):
        mesh_face_materials(wld, wld.fragments[2])
    wld = material_wld(group_count=0)
    with pytest.raises(ValueError, match="do not cover"):
        mesh_face_materials(wld, wld.fragments[2])
