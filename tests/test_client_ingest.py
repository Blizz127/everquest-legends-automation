from pathlib import Path

import pytest

from eql_automation import client_ingest
from eql_automation.client_ingest import (import_retail_copy, load_map, parse_map,
                                          parse_zone_names, save_map)
from eql_automation.prior_rotation_core import Catalog


def test_map_geometry_is_preserved_without_claiming_walkability(tmp_path: Path):
    document = parse_map(
        "L 0, 0, 0, 10, 0, 0, 255, 0, 0\n"
        "P 5, 2, 0, 0, 0, 240, 2, to_Synthetic_Zone\n")
    assert len(document.lines) == 1
    assert document.lines[0].end.x == 10
    assert document.find_labels("synthetic")[0].text == "to_Synthetic_Zone"
    assert document.bounds()["x"] == (0.0, 10.0)
    path = tmp_path / "sample.json.gz"
    save_map(document, path)
    assert load_map(path) == document


def test_malformed_map_fails_closed_and_zone_names_keep_source_fields():
    with pytest.raises(ValueError):
        parse_map("L 0, 0, NaN, 10, 0, 0, 255, 0, 0\n")
    with pytest.raises(ValueError):
        parse_map("P 1, 2, 3, 0, 0, 300, 2, Bad\n")
    with pytest.raises(ValueError, match="Unknown record"):
        parse_map("X 1, 2, 3\n")
    assert len(parse_map("L\t0, 0, 0, 1, 0, 0, 0, 0, 0\n").lines) == 1
    assert parse_zone_names("9^West Freeport^12^60\n") == [
        {"id": 9, "name": "West Freeport", "client_fields": ["12", "60"]}]


def test_import_snapshot_is_atomic_and_source_change_creates_new_version(
        tmp_path: Path, monkeypatch):
    source = tmp_path / "source"
    maps = source / "maps"
    resources = source / "Resources"
    maps.mkdir(parents=True)
    resources.mkdir()
    (source / "spells_us.txt").write_text("synthetic spell fixture\n")
    (resources / "ZoneNames.txt").write_text("1^Synthetic Zone^0^0\n")
    first = maps / "a.txt"
    second = maps / "b.txt"
    first.write_text("L 0, 0, 0, 1, 0, 0, 0, 0, 0\n")
    second.write_text("X unexpected\n")
    monkeypatch.setattr(client_ingest.Catalog, "load",
                        classmethod(lambda cls, path: Catalog([])))
    store = tmp_path / "store"
    with pytest.raises(ValueError):
        import_retail_copy(source, store)
    assert not (store / "current.json").exists()
    assert not list((store / "snapshots").glob(".staging-*"))
    second.write_text("P 0, 0, 0, 0, 0, 0, 2, Synthetic\n")
    original = import_retail_copy(source, store)
    assert len(original["maps"]) == 2
    assert len(list((store / "snapshots" / original["snapshot_id"] / "geometry").glob("*.gz"))) == 2
    first.write_text("L 0, 0, 0, 2, 0, 0, 0, 0, 0\n")
    changed = import_retail_copy(source, store)
    assert changed["snapshot_id"] != original["snapshot_id"]
    assert Path(original["summary_path"]).exists()
    assert changed["snapshot_id"] in (store / "current.json").read_text()
