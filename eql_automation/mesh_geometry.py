"""Decode old-format WLD 0x36 mesh vertices and triangle records.

Reference: https://docs.eqemu.dev/client/guides/file-formats/wld-by-windcatcher/
Only the copied client's 0x00015500 format and meshes without Data9 are
supported. This creates geometry evidence, not a collision bake or navmesh.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import isfinite
from struct import unpack_from

from .wld_inventory import WLDFragment, WLDInventory


OLD_WLD_VERSION = 0x00015500
MAX_SCALE = 15


@dataclass(frozen=True)
class Triangle:
    flag: int
    a: int
    b: int
    c: int


@dataclass(frozen=True)
class MeshGeometry:
    fragment_index: int
    name: str | None
    flags: int
    center: tuple[float, float, float]
    scale: int
    raw_vertices: tuple[tuple[int, int, int], ...]
    triangles: tuple[Triangle, ...]
    padding_bytes: int

    def vertex(self, index: int) -> tuple[float, float, float]:
        raw = self.raw_vertices[index]
        factor = 1 << self.scale
        return tuple(self.center[axis] + raw[axis] / factor for axis in range(3))

    def degenerate_count(self) -> int:
        count = 0
        for triangle in self.triangles:
            a, b, c = (self.raw_vertices[index] for index in
                       (triangle.a, triangle.b, triangle.c))
            u = tuple(b[axis] - a[axis] for axis in range(3))
            v = tuple(c[axis] - a[axis] for axis in range(3))
            if (u[1] * v[2] - u[2] * v[1] == 0 and
                    u[2] * v[0] - u[0] * v[2] == 0 and
                    u[0] * v[1] - u[1] * v[0] == 0):
                count += 1
        return count


@dataclass(frozen=True)
class MeshSummary:
    mesh_count: int
    vertex_count: int
    polygon_count: int
    solid_flag_zero_count: int
    pass_through_flag_0x10_count: int
    other_polygon_flags: dict[str, int]
    degenerate_polygon_count: int
    geometry_decoded: bool = True
    collision_composed: bool = False
    navigability_verified: bool = False


def read_mesh(wld: WLDInventory, fragment: WLDFragment) -> MeshGeometry:
    if fragment.type_code != 0x36:
        raise ValueError("Fragment is not a 0x36 mesh")
    if wld.version != OLD_WLD_VERSION:
        raise ValueError("Only old-format WLD meshes are supported")
    body = wld.body(fragment)
    if len(body) < 92:
        raise ValueError("WLD mesh header is truncated")
    flags = unpack_from("<I", body)[0]
    center = unpack_from("<3f", body, 20)
    if not all(map(isfinite, center)):
        raise ValueError("WLD mesh center is nonfinite")
    (vertex_count, uv_count, normal_count, color_count, polygon_count,
     piece_count, polygon_texture_count, vertex_texture_count,
     data9_count, scale) = unpack_from("<10H", body, 72)
    if data9_count or scale > MAX_SCALE:
        raise ValueError("Unsupported WLD mesh Data9 or scale")
    vertex_end = 92 + vertex_count * 6
    polygon_start = (vertex_end + uv_count * 4 + normal_count * 3 +
                     color_count * 4)
    expected_end = (polygon_start + polygon_count * 8 + piece_count * 4 +
                    polygon_texture_count * 4 + vertex_texture_count * 4)
    if expected_end > len(body) or len(body) - expected_end > 3:
        raise ValueError("WLD mesh arrays exceed fragment bounds")
    vertices = tuple(unpack_from("<3h", body, 92 + index * 6)
                     for index in range(vertex_count))
    triangles = []
    for index in range(polygon_count):
        flag, a, b, c = unpack_from("<4H", body, polygon_start + index * 8)
        if max(a, b, c) >= vertex_count:
            raise ValueError("WLD mesh polygon references missing vertex")
        triangles.append(Triangle(flag, a, b, c))
    return MeshGeometry(fragment.index, fragment.name, flags, center, scale,
                        vertices, tuple(triangles), len(body) - expected_end)


def read_meshes(wld: WLDInventory) -> tuple[MeshGeometry, ...]:
    return tuple(read_mesh(wld, fragment) for fragment in wld.fragments
                 if fragment.type_code == 0x36)


def summarize_meshes(meshes: tuple[MeshGeometry, ...]) -> MeshSummary:
    flags = Counter(triangle.flag for mesh in meshes for triangle in mesh.triangles)
    return MeshSummary(
        mesh_count=len(meshes),
        vertex_count=sum(len(mesh.raw_vertices) for mesh in meshes),
        polygon_count=sum(len(mesh.triangles) for mesh in meshes),
        solid_flag_zero_count=flags[0],
        pass_through_flag_0x10_count=flags[0x10],
        other_polygon_flags={f"0x{flag:x}": count for flag, count in sorted(flags.items())
                             if flag not in (0, 0x10)},
        degenerate_polygon_count=sum(mesh.degenerate_count() for mesh in meshes),
    )
