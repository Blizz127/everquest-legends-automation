"""Focused checks for old-format 0x36 mesh geometry and collision flags."""
from struct import pack, pack_into

import pytest

from eql_automation.mesh_geometry import read_mesh, read_meshes, summarize_meshes
from eql_automation.wld_inventory import WLDInventory, XOR_KEY


def mesh_wld(*, polygon=(0x10, 0, 1, 2), scale=1) -> WLDInventory:
    names = b"\x00TRIANGLE\x00"
    encoded = bytes(value ^ XOR_KEY[index % len(XOR_KEY)]
                    for index, value in enumerate(names))
    body = bytearray(92)
    pack_into("<I", body, 0, 0x00018003)
    pack_into("<3f", body, 20, 10.0, 20.0, 30.0)
    pack_into("<10H", body, 72, 3, 0, 0, 0, 1, 0, 0, 0, 0, scale)
    body.extend(pack("<9h", 0, 0, 0, 2, 0, 0, 0, 2, 0))
    body.extend(pack("<4H", *polygon))
    header = pack("<7I", 0x54503D02, 0x00015500, 1, 0, 0, len(names), 0)
    fragment = pack("<IIi", len(body) + 4, 0x36, -1) + body
    return WLDInventory(header + encoded + fragment + b"\xff" * 4)


def test_mesh_vertices_polygons_and_pass_through_are_decoded():
    wld = mesh_wld()
    mesh = read_meshes(wld)[0]
    assert mesh.vertex(1) == (11.0, 20.0, 30.0)
    assert mesh.vertex(2) == (10.0, 21.0, 30.0)
    assert [(face.flag, face.a, face.b, face.c) for face in mesh.triangles] == [
        (0x10, 0, 1, 2)]
    summary = summarize_meshes((mesh,))
    assert summary.pass_through_flag_0x10_count == 1
    assert summary.degenerate_polygon_count == 0
    assert summary.collision_composed is False


def test_out_of_range_polygon_is_rejected():
    wld = mesh_wld(polygon=(0, 0, 1, 3))
    with pytest.raises(ValueError, match="missing vertex"):
        read_mesh(wld, wld.fragments[0])
