from pathlib import Path
import json

import pytest

from eql_automation.client_ingest import MapDocument, MapLabel, save_map
from eql_automation.nav import Point
from eql_automation.zone_candidates import build_zone_candidates


def test_zone_name_cross_reference_stays_unverified(tmp_path: Path):
    store = tmp_path / "store"
    snapshot = store / "snapshots" / "abc123"
    geometry = snapshot / "geometry" / "start.json.gz"
    save_map(MapDocument([], [
        MapLabel(Point(0, 0), (0, 0, 0), 2, "to_East_Cabilis"),
        MapLabel(Point(1, 0), (0, 0, 0), 2, "West_Freeport"),
        MapLabel(Point(2, 0), (0, 0, 0), 2, "to_Unknown"),
        MapLabel(Point(3, 0), (0, 0, 0), 2, "Bank"),
    ]), geometry)
    zones = snapshot / "zone-names.json"
    zones.write_text(json.dumps([
        {"id": 42, "name": "Cabilis East"},
        {"id": 9, "name": "West Freeport"},
    ]))
    summary = snapshot / "summary.json"
    summary.write_text(json.dumps({"snapshot_id": "abc123",
                                   "zone_names_store": str(zones),
                                   "maps": [{"name": "start",
                                             "geometry_store": str(geometry)}]}))
    index, output = build_zone_candidates(summary, store)
    assert output.is_file()
    assert index.counts() == {"label_exact": 1, "to_prefix_token_order": 1,
                              "to_prefix_unmatched": 1}
    assert len(index.candidates) == 3
    assert index.search("east cabilis")[0].client_zone_ids == (42,)
    assert index.search("unknown")[0].client_zone_ids == ()
    assert all(not item.verified for item in index.candidates)
    assert build_zone_candidates(summary, store)[0].candidates == index.candidates


def test_zone_name_path_cannot_escape_snapshot(tmp_path: Path):
    snapshot = tmp_path / "store" / "snapshots" / "abc123"
    snapshot.mkdir(parents=True)
    outside = tmp_path / "outside.json"
    outside.write_text("[]")
    summary = snapshot / "summary.json"
    summary.write_text(json.dumps({"snapshot_id": "abc123",
                                   "zone_names_store": str(outside),
                                   "maps": []}))
    with pytest.raises(ValueError, match="escapes"):
        build_zone_candidates(summary, tmp_path / "store")
