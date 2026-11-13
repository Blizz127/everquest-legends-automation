from pathlib import Path
import json

from eql_automation.client_ingest import MapDocument, MapLabel, save_map
from eql_automation.nav import Point
from eql_automation.poi_index import (build_poi_index, classify_hint,
                                      current_summary)


def test_poi_index_queries_only_unverified_map_labels(tmp_path: Path):
    store = tmp_path / "store"
    snapshot = store / "snapshots" / "abc123"
    geometry = snapshot / "geometry" / "zone.json.gz"
    save_map(MapDocument([], [
        MapLabel(Point(0, 0), (0, 0, 240), 2, "to_Synthetic_Zone"),
        MapLabel(Point(10, 0), (0, 0, 0), 3, "Amet_(Merchant)"),
        MapLabel(Point(20, 0), (0, 0, 0), 3, "Old_Portal"),
    ]), geometry)
    summary = snapshot / "summary.json"
    summary.write_text(json.dumps({"snapshot_id": "abc123",
                                   "maps": [{"name": "zone",
                                             "geometry_store": str(geometry)}]}))
    (store / "current.json").write_text(json.dumps({"summary_path": str(summary)}))
    assert current_summary(store) == summary
    index, path = build_poi_index(summary, store)
    assert path.is_file()
    assert index.counts() == {"merchant_hint": 1, "portal_hint": 1,
                              "zone_exit_hint": 1}
    assert [poi.text for poi in index.search("synthetic zone")] == ["to_Synthetic_Zone"]
    assert [poi.text for poi in index.nearest("zone", Point(9, 0), radius=2)] == [
        "Amet_(Merchant)"]
    assert all(not poi.verified for poi in index.pois)
    assert build_poi_index(summary, store)[0].pois == index.pois


def test_poi_classification_is_conservative():
    assert classify_hint("East_Freeport") == "landmark"
    assert classify_hint("to_East_Freeport") == "zone_exit_hint"
    assert classify_hint("Spell_Merchant") == "merchant_spell_hint"
