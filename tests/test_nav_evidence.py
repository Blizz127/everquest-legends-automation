from hashlib import sha256
from pathlib import Path
import json

import pytest

from eql_automation.nav_evidence import audit_butcherblock


def snapshot(store: Path, *, verified: bool = False) -> None:
    directory = store / "snapshots" / "synthetic"
    directory.mkdir(parents=True)
    summary = directory / "summary.json"
    source = store.parent / "client-data"
    (source / "maps").mkdir(parents=True)
    for name in ("butcher", "butcher_1", "crushbone", "crushbone_1"):
        (source / "maps" / f"{name}.txt").write_text("synthetic map line\n")
    source_hash = sha256(b"synthetic map line\n").hexdigest()
    summary.write_text(json.dumps({
        "snapshot_id": "synthetic",
        "source_dir": str(source),
        "maps": [{"name": name, "source_sha256": source_hash,
                  "line_count": 1, "label_count": 0,
                  "navigability_verified": verified}
                 for name in ("butcher", "butcher_1", "crushbone", "crushbone_1")],
    }))
    (store / "current.json").write_text(json.dumps({"summary_path": str(summary)}))


def test_map_drawings_and_hash_match_do_not_accept_real_navigation(tmp_path: Path):
    store = tmp_path / "approved" / "map-store"
    snapshot(store)
    empty = audit_butcherblock(store=store, allowed_root=tmp_path / "approved")
    assert not empty.historical_mesh_hash_match
    assert not empty.actual_client_acceptance_ready
    assert all(item.source_hash_verified for item in empty.maps)
    mesh = tmp_path / "approved" / "retained-mesh.bin"
    mesh.write_bytes(b"synthetic navmesh")
    matched = audit_butcherblock(
        store=store, allowed_root=tmp_path / "approved", mesh_path=mesh,
        expected_mesh_sha256=sha256(mesh.read_bytes()).hexdigest())
    assert matched.historical_mesh_hash_match
    assert not matched.mesh_provenance_verified
    assert not matched.conservative_clearance_verified
    assert not matched.real_client_movement_verified
    assert not matched.actual_client_acceptance_ready


def test_audit_refuses_artifact_outside_approved_store(tmp_path: Path):
    store = tmp_path / "approved" / "map-store"
    snapshot(store)
    outside = tmp_path / "outside-approved-store.bin"
    outside.write_bytes(b"synthetic")
    with pytest.raises(ValueError, match="approved EQL data store"):
        audit_butcherblock(store=store, allowed_root=tmp_path / "approved",
                           mesh_path=outside)
    link = tmp_path / "approved" / "outside-link.bin"
    link.symlink_to(outside)
    with pytest.raises(ValueError, match="approved EQL data store"):
        audit_butcherblock(store=store, allowed_root=tmp_path / "approved",
                           mesh_path=link)


def test_audit_refuses_to_treat_map_geometry_as_verified(tmp_path: Path):
    store = tmp_path / "approved" / "map-store"
    snapshot(store, verified=True)
    with pytest.raises(ValueError, match="unverified"):
        audit_butcherblock(store=store, allowed_root=tmp_path / "approved")


def test_changed_client_map_source_fails_hash_check(tmp_path: Path):
    store = tmp_path / "approved" / "map-store"
    snapshot(store)
    (tmp_path / "approved" / "client-data" / "maps" / "butcher.txt").write_text("changed\n")
    result = audit_butcherblock(store=store, allowed_root=tmp_path / "approved")
    assert not next(item for item in result.maps if item.name == "butcher").source_hash_verified
    assert "copied client map source hashes" in result.missing


def test_audit_refuses_copied_map_symlink_outside_store(tmp_path: Path):
    store = tmp_path / "approved" / "map-store"
    snapshot(store)
    outside = tmp_path / "outside-map.txt"
    outside.write_text("synthetic\n")
    source_path = tmp_path / "approved" / "client-data" / "maps" / "butcher.txt"
    source_path.unlink()
    source_path.symlink_to(outside)
    with pytest.raises(ValueError, match="Copied map path escapes"):
        audit_butcherblock(store=store, allowed_root=tmp_path / "approved")
