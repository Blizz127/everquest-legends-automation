"""The provisional geometry writer must omit pass-through and zero-area faces."""
from io import StringIO

import pytest

from eql_automation.candidate_scene import _append_solid_mesh
from eql_automation.material_audit import FaceMaterial
from eql_automation.mesh_geometry import MeshGeometry, Triangle


def test_candidate_writer_keeps_only_solid_nonzero_faces():
    mesh = MeshGeometry(0, "TRIANGLE", 0x18003, (10.0, 20.0, 30.0), 0,
                        ((0, 0, 0), (1, 0, 0), (0, 1, 0), (2, 0, 0)),
                        (Triangle(0, 0, 1, 2), Triangle(0x10, 0, 2, 3),
                         Triangle(0, 0, 1, 3)), 0)
    output = StringIO()
    counts = _append_solid_mesh(output, mesh, None, 0)
    assert counts == (3, 1, 1, 1, 0)
    assert output.getvalue().splitlines() == [
        "v 10 20 30", "v 11 20 30", "v 10 21 30", "f 3 2 1"]


def test_boundary_faces_can_be_excluded_without_promoting_passable_faces():
    mesh = MeshGeometry(0, "WALL", 0x18003, (0.0, 0.0, 0.0), 0,
                        ((0, 0, 0), (1, 0, 0), (0, 1, 0)),
                        (Triangle(0, 0, 1, 2), Triangle(0x10, 0, 1, 2)), 0)
    materials = (FaceMaterial(0, 0, "WALL_MDF"),
                 FaceMaterial(0x10, 0x80000001, "WATER_MDF"))
    output = StringIO()
    assert _append_solid_mesh(output, mesh, None, 0, materials) == (0, 0, 1, 0, 1)
    assert output.getvalue() == ""


def test_boundary_exclusion_preserves_diffuse_face_and_rejects_misaligned_materials():
    mesh = MeshGeometry(0, "MIXED", 0x18003, (0.0, 0.0, 0.0), 0,
                        ((0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)),
                        (Triangle(0, 0, 1, 2), Triangle(0, 1, 3, 2)), 0)
    materials = (FaceMaterial(0, 0, "BOUNDARY_MDF"),
                 FaceMaterial(0, 1, "FLOOR_MDF"))
    output = StringIO()
    assert _append_solid_mesh(output, mesh, None, 0, materials) == (3, 1, 0, 0, 1)
    assert output.getvalue().splitlines() == [
        "v 1 0 0", "v 0 1 0", "v 1 1 0", "f 2 3 1"]
    with pytest.raises(ValueError, match="material count"):
        _append_solid_mesh(StringIO(), mesh, None, 0, materials[:1])
