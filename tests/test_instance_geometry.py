"""Check exporter-derived axis/scale order without accepting client movement."""
from math import isclose

import pytest

from eql_automation.instance_geometry import projected_vertex
from eql_automation.mesh_geometry import MeshGeometry
from eql_automation.placement_audit import ObjectLocation


def make_location(*, rot_z=0.0, rot_y=0.0, scale=2.0) -> ObjectLocation:
    return ObjectLocation(0, "SAMPLE_ACTORDEF", 814, 100.0, 200.0, 300.0,
                          rot_z, rot_y, 0.0, scale, scale, False)


def test_uniform_scale_then_yaw_then_center_and_position():
    mesh = MeshGeometry(0, "SAMPLE_DMSPRITEDEF", 0x14003,
                        (10.0, 20.0, 30.0), 1, ((2, 0, 0),), (), 0)
    result = projected_vertex(mesh, make_location(rot_z=128), 0)
    assert all(isclose(a, b, abs_tol=1e-6) for a, b in
               zip(result, (110.0, 222.0, 330.0)))


def test_raw_y_rotation_rolls_local_y_into_z():
    mesh = MeshGeometry(0, None, 0x14003, (0.0, 0.0, 0.0),
                        0, ((0, 1, 0),), (), 0)
    result = projected_vertex(mesh, make_location(rot_y=128, scale=1), 0)
    assert all(isclose(a, b, abs_tol=1e-6) for a, b in
               zip(result, (100.0, 200.0, 301.0)))


def test_nonuniform_scale_is_rejected():
    mesh = MeshGeometry(0, None, 0x14003, (0.0, 0.0, 0.0),
                        0, ((0, 0, 0),), (), 0)
    location = ObjectLocation(0, "SAMPLE_ACTORDEF", 814, 0.0, 0.0, 0.0,
                              0.0, 0.0, 0.0, 1.0, 2.0, False)
    with pytest.raises(ValueError, match="Nonuniform"):
        projected_vertex(mesh, location, 0)
