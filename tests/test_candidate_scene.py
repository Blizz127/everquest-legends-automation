"""The provisional geometry writer must omit pass-through and zero-area faces."""
from io import StringIO

from eql_automation.candidate_scene import _append_solid_mesh
from eql_automation.mesh_geometry import MeshGeometry, Triangle


def test_candidate_writer_keeps_only_solid_nonzero_faces():
    mesh = MeshGeometry(0, "TRIANGLE", 0x18003, (10.0, 20.0, 30.0), 0,
                        ((0, 0, 0), (1, 0, 0), (0, 1, 0), (2, 0, 0)),
                        (Triangle(0, 0, 1, 2), Triangle(0x10, 0, 2, 3),
                         Triangle(0, 0, 1, 3)), 0)
    output = StringIO()
    counts = _append_solid_mesh(output, mesh, None, 0)
    assert counts == (3, 1, 1, 1)
    assert output.getvalue().splitlines() == [
        "v 10 20 30", "v 11 20 30", "v 10 21 30", "f 1 2 3"]
