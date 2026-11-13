"""Synthetic map/WLD frame and overlapping-surface checks."""
from eql_automation.client_ingest import MapDocument, MapLabel, MapLine
from eql_automation.map_alignment import audit_map_alignment
from eql_automation.mesh_geometry import MeshGeometry, Triangle
from eql_automation.nav import Point


def test_map_transform_and_label_surface_remain_offline_candidates():
    lines = [MapLine(Point(-2, -1, 0), Point(-2, -3, 0), (0, 0, 0)),
             MapLine(Point(-2, -3, 0), Point(-4, -1, 0), (0, 0, 0))]
    labels = MapDocument([], [MapLabel(Point(-2.2, -1.2, 0.7), (0, 0, 0),
                                      0, "to_other_zone")])
    vertices = ((1, 2, 0), (3, 2, 0), (1, 4, 0))
    floor = MeshGeometry(0, "FLOOR", 0, (0, 0, 0), 0, vertices,
                         (Triangle(0, 0, 1, 2),), 0)
    upper = MeshGeometry(1, "UPPER", 0, (0, 0, 10), 0, vertices,
                         (Triangle(0, 0, 1, 2),), 0)
    result = audit_map_alignment(MapDocument(lines, []), (floor, upper), labels)
    assert result["best_map_to_wld_xy_transform"] == "-y,-x"
    assert result["best_match_count"] == 3
    assert result["frame_supported_by_rounded_vertex_matches"] is True
    assert result["matching_vertices_by_transform"]["x,y"] == 0
    surface = result["label_surface_candidates"][0]
    assert surface["wld_xy"] == [1.2, 2.2]
    assert surface["flag_zero_surface_height_count"] == 2
    assert surface["nearest_surface_z"] == 0
    assert surface["nearest_abs_z_offset"] == 0.7
    assert result["zone_labels_actionable"] is False
    assert result["live_client_alignment_verified"] is False

    sparse = audit_map_alignment(MapDocument(lines[:1], []), (floor, upper), labels)
    assert sparse["best_match_count"] == 2
    assert sparse["frame_supported_by_rounded_vertex_matches"] is False
    assert sparse["label_surface_candidates"] == []
