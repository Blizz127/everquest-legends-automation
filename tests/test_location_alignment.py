from datetime import datetime

import pytest

from eql_automation.location_alignment import (
    HistoricalLocation, historical_zone_locations, score_location_transforms,
)
from eql_automation.mesh_geometry import MeshGeometry, Triangle


def line(second: int, body: str) -> str:
    return f"[Thu Nov 05 19:49:{second:02d} 2026] {body}\n"


def sample(x: float, y: float, z: float) -> HistoricalLocation:
    return HistoricalLocation((x, y, z), datetime(2026, 11, 5), "Example One")


def two_surface_mesh() -> MeshGeometry:
    vertices = ((9, 19, 0), (12, 19, 0), (9, 22, 0),
                (19, 29, 5), (22, 29, 5), (19, 32, 5))
    faces = (Triangle(0, 0, 1, 2), Triangle(0, 3, 4, 5))
    return MeshGeometry(1, "synthetic", 0, (0, 0, 0), 0, vertices, faces, 0)


def test_historical_samples_need_matching_entered_zone():
    lines = [line(1, "Your Location is 1, 2, 3"),
             line(2, "You have entered Example One."),
             line(3, "Your Location is 10, 20, 2.56"),
             line(4, "LOADING, PLEASE WAIT..."),
             line(5, "Your Location is 99, 99, 99"),
             line(6, "You have entered Example Two."),
             line(7, "Your Location is 88, 88, 88"),
             line(8, "You have entered Example One."),
             line(9, "Your Location is 20, 30, 7.56")]
    samples = historical_zone_locations(lines, "Example One")
    assert [item.raw_coordinates for item in samples] == [
        (10.0, 20.0, 2.56), (20.0, 30.0, 7.56)]
    with pytest.raises(ValueError, match="line budget"):
        historical_zone_locations(lines, "Example One", max_lines=4)
    with pytest.raises(ValueError, match="sample budget"):
        historical_zone_locations(lines, "Example One", max_samples=1)


def test_malformed_boundary_drops_historical_zone_until_new_entry():
    lines = [line(1, "You have entered Example One."),
             line(2, "Your Location is 10, 20, 2.56"),
             "[invalid] LOADING, PLEASE WAIT...\n",
             line(3, "Your Location is 11, 21, 2.56"),
             line(4, "You have entered Example One."),
             line(5, "Your Location is 12, 22, 2.56"),
             line(6, "You have entered Example Two"),
             line(7, "Your Location is 13, 23, 2.56"),
             line(8, "You have entered Example One."),
             line(9, "Your Location is 14, 24, 2.56"),
             line(10, "LOADING, PLEASE WAIT"),
             line(11, "Your Location is 15, 25, 2.56")]
    samples = historical_zone_locations(lines, "Example One")
    assert [item.raw_coordinates for item in samples] == [
        (10.0, 20.0, 2.56), (12.0, 22.0, 2.56),
        (14.0, 24.0, 2.56)]
    many = [line(1, "You have entered Example One.")] + [
        line(2, "Your Location is 10, 20, 2.56") for _ in range(65)]
    with pytest.raises(ValueError, match="sample budget"):
        historical_zone_locations(many, "Example One")


def test_timestamp_regression_drops_historical_zone_until_reentered():
    lines = [line(2, "You have entered Example One."),
             line(3, "Your Location is 10, 20, 2.56"),
             line(1, "Your Location is 11, 21, 2.56"),
             line(4, "Your Location is 12, 22, 2.56"),
             line(5, "You have entered Example One."),
             line(6, "Your Location is 13, 23, 2.56")]
    samples = historical_zone_locations(lines, "Example One")
    assert [item.raw_coordinates for item in samples] == [
        (10.0, 20.0, 2.56), (13.0, 23.0, 2.56)]


def test_terrain_score_ranks_candidate_but_accepts_no_transform():
    audit = score_location_transforms(
        (sample(10, 20, 2.56), sample(10, 20, 2.56),
         sample(20, 30, 7.56)),
        (two_surface_mesh(),))
    first = audit["candidate_scores"][0]
    assert first["transform"] == "x,y"
    assert first["surface_coverage_count"] == 2
    assert first["coherent_offset_count"] == 2
    assert first["median_raw_z_minus_terrain_z"] == 2.56
    assert audit["historical_sample_count"] == 3
    assert audit["distinct_raw_coordinate_count"] == 2
    assert audit["repeated_coordinate_count"] == 1
    assert audit["accepted_log_to_wld_transform"] is None
    assert audit["live_alignment_verified"] is False
    assert audit["navigation_edge_accepted"] is False


def test_alignment_audit_rejects_missing_or_excessive_geometry():
    with pytest.raises(ValueError, match="No flag-zero"):
        score_location_transforms((sample(10, 20, 2.56),), ())
    with pytest.raises(ValueError, match="triangle budget"):
        score_location_transforms((sample(10, 20, 2.56),),
                                  (two_surface_mesh(),), max_triangles=1)
