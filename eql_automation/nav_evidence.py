"""Scoped audit of historical Butcherblock navmesh claims.

This never creates graph edges. A historical mesh hash match is provenance,
not collision clearance or real-client movement acceptance. Optional artifacts
must reside inside the current approved EQL data store, never an old workspace.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json

from .client_ingest import sha256_file
from .nav import MAP_STORE
from .poi_index import current_summary


DATA_ROOT = Path.home() / ".local/share/eql-automation"
HISTORICAL_BUTCHER_MESH_SHA256 = (
    "d1b57d2dab7b975e8d62821725bf992634136774720707fa103af10e238aad85"
)


@dataclass(frozen=True)
class MapEvidence:
    name: str
    source_sha256: str
    source_hash_verified: bool
    drawing_lines: int
    labels: int
    navigability_verified: bool


@dataclass(frozen=True)
class ButcherblockAudit:
    snapshot_id: str
    maps: tuple[MapEvidence, ...]
    mesh_path: str | None
    mesh_sha256: str | None
    historical_mesh_hash_match: bool
    mesh_provenance_verified: bool
    conservative_clearance_verified: bool
    gfay_height_alignment_verified: bool
    dynamic_world_verified: bool
    real_client_movement_verified: bool
    actual_client_acceptance_ready: bool
    missing: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def _map_evidence(item: dict, source: Path, allowed_root: Path) -> MapEvidence:
    path = source / "maps" / f"{item['name']}.txt"
    if not path.resolve().is_relative_to(allowed_root.resolve()):
        raise ValueError("Copied map path escapes the approved EQL data store")
    source_hash_verified = path.is_file() and sha256_file(path) == item["source_sha256"]
    return MapEvidence(item["name"], item["source_sha256"], source_hash_verified,
                       item["line_count"], item["label_count"],
                       item["navigability_verified"])


def audit_butcherblock(*, store: Path = MAP_STORE,
                       allowed_root: Path = DATA_ROOT,
                       mesh_path: Path | None = None,
                       expected_mesh_sha256: str = HISTORICAL_BUTCHER_MESH_SHA256) -> ButcherblockAudit:
    summary = json.loads(current_summary(store).read_text())
    source = Path(summary["source_dir"]).resolve()
    if not source.is_relative_to(allowed_root.resolve()):
        raise ValueError("Copied client maps must be inside the approved EQL data store")
    names = {"butcher", "butcher_1", "crushbone", "crushbone_1"}
    maps = tuple(_map_evidence(item, source, allowed_root)
                 for item in summary["maps"] if item["name"] in names)
    if {item.name for item in maps} != names or any(item.navigability_verified for item in maps):
        raise ValueError("Expected unverified Butcherblock/Crushbone map snapshot is missing")
    digest = None
    path_text = None
    if mesh_path is not None:
        resolved = mesh_path.resolve()
        if not resolved.is_relative_to(allowed_root.resolve()):
            raise ValueError("Mesh path must be inside the approved EQL data store")
        path_text = str(resolved)
        if resolved.is_file():
            digest = sha256_file(resolved)
    hash_match = digest == expected_mesh_sha256.lower() if digest else False
    missing = []
    if any(not item.source_hash_verified for item in maps):
        missing.append("copied client map source hashes")
    if not hash_match:
        missing.append("retained mesh matching the historical serialized hash")
    missing.extend((
        "terrain/object placement inputs and bake provenance",
        "conservative clearance for (8,5,2,45)",
        "Greater Faydark vertical alignment",
        "dynamic doors, water and traversed zone transitions",
        "private-target client movement with a fresh test character",
    ))
    return ButcherblockAudit(
        summary["snapshot_id"], maps, path_text, digest, hash_match,
        mesh_provenance_verified=False,
        conservative_clearance_verified=False,
        gfay_height_alignment_verified=False,
        dynamic_world_verified=False,
        real_client_movement_verified=False,
        actual_client_acceptance_ready=False,
        missing=tuple(missing))
