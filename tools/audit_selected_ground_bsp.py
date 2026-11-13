#!/usr/bin/env python3
"""Trace a hash-bound selected ground route through copied client BSP labels.

This checks only a static centerline at two heights. It does not verify
collision, dynamic objects, zone transitions, camp safety or client movement.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from eql_automation.bsp_probe import BspPointLookup  # noqa: E402
from eql_automation.ground_bsp_route import (audit_ground_bsp_route,
                                             verify_helper_bsp_frame)  # noqa: E402
from eql_automation.pfs_archive import PFSArchive  # noqa: E402
from eql_automation.wld_inventory import WLDInventory  # noqa: E402

DATA_ROOT = Path.home() / ".local/share/eql-automation"
SOURCES = {
    # zone: archive, mesh, manifest; copied from owner install / retained helper
    "gfaydark": (
        "ea95f51a2d4645410223d24cc7da9eb0e7095310c6e9f8756e8c51d67df13d9f",
        "5f8e16c5bcd2221ba273f681750ca480349780524d23609c059a3e817df6abd9",
        "ac9591eb63e1394363ad37d7d0ca6609a1ebe11fd8786bedb5b165b833e2eb82",
    ),
    "butcher": (
        "af504e71d3f3497b5eef037d86475ba96985b261d96f6469915e058e05308839",
        "4e450cdbca7ab6cc44a7973eca11929d7b920db49f6c51ad00a6337b5ee58bde",
        "64f3b3d8673a61424268172b3b9c6989921c77e49d5b0f4d55fa034f2d8ef792",
    ),
    "crushbone": (
        "a2591482aac0a478caec1d79bf662a3f0f93d4ef2dc423be8f7591fe6d45e36f",
        "bee5a1893ab0e2ffd9c83d0d64a1d7392993b21661f59095b0e2e304b0588793",
        "dd15b27c8acb221987780b013e9f0c4a9a14f4df389414a33b9ecf6fcc94979d",
    ),
}
HELPER_HASHES = {
    "eqnav/__init__.py": "717e253506fa07148160efd0679373ae0d430611d9146b73bc9feca02f5258b0",
    "eqnav/mesh.py": "89682ac2f6ee6ad4fc4e4530d946e4d7d883d860573a958d45f7cd7a074fef85",
    "eqnav/world.py": "6441467623a49950af2549496ddb27c3c8c5e3889829d833293a604d9209cfb2",
    "eqnav/zonegeom.py": "bffd21c5767b111f9516180377838d180bf31e3af8e2bc427258c987d6609a60",
}


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def private_file(path: Path, root: Path, *, max_bytes: int) -> Path:
    path = path.expanduser()
    resolved = path.resolve()
    if (path.is_symlink() or not resolved.is_relative_to(root.resolve()) or
            not resolved.is_file() or not 0 < resolved.stat().st_size <= max_bytes):
        raise ValueError(f"expected a bounded regular file under {root}")
    return resolved


def inspect(*, zone: str, source: Path, selection: Path, final_strip: Path | None,
            output: Path, mesh_store: Path, helper_root: Path) -> dict:
    if zone not in SOURCES:
        raise ValueError("zone has no pinned copied-client BSP source")
    candidates = DATA_ROOT / "nav-candidates"
    source = private_file(source, candidates, max_bytes=10 * 1024 * 1024)
    selection = private_file(selection, candidates, max_bytes=10 * 1024 * 1024)
    if final_strip is not None:
        final_strip = private_file(final_strip, candidates, max_bytes=10 * 1024 * 1024)
    output = output.expanduser().resolve()
    mesh_store = mesh_store.expanduser().resolve()
    helper_root = helper_root.expanduser().resolve()
    if (not output.is_relative_to(candidates.resolve()) or
            output.suffix != ".json" or output.exists() or
            not mesh_store.is_relative_to((DATA_ROOT / "navmesh").resolve()) or
            not helper_root.is_relative_to((DATA_ROOT / "owner-assist").resolve())):
        raise ValueError("output, copied mesh or helper is outside the private store")
    for name, expected in HELPER_HASHES.items():
        path = helper_root / name
        if not path.is_file() or path.is_symlink() or digest(path) != expected:
            raise ValueError(f"reviewed helper source changed: {name}")
    route_raw, selected_raw = source.read_bytes(), selection.read_bytes()
    strip_raw = final_strip.read_bytes() if final_strip is not None else None
    route, selected = json.loads(route_raw), json.loads(selected_raw)
    strip = json.loads(strip_raw) if strip_raw is not None else None
    source_hash, selection_hash = (sha256(raw).hexdigest() for raw in
                                   (route_raw, selected_raw))
    strip_hash = sha256(strip_raw).hexdigest() if strip_raw is not None else None
    polygons = route.get("polygons", route.get("path_polygons"))
    points = selected.get("unverified_points") if strip is not None else selected.get("points")
    if (not isinstance(polygons, list) or not 1 <= len(polygons) <= 512 or
            any(not isinstance(poly, int) or isinstance(poly, bool) or poly < 0
                for poly in polygons) or
            not isinstance(points, list) or len(points) != len(polygons) + 1 or
            any(not isinstance(point, list) or len(point) != 2 or
                any(not isinstance(v, (int, float)) or isinstance(v, bool) or
                    not math.isfinite(v) for v in point) for point in points) or
            route.get("offline_only") is not True or route.get("route_accepted") is not False or
            selected.get("format") != "eql-copied-ground-selector-v1" or
            selected.get("zone") != zone or selected.get("source_sha256") != source_hash or
            selected.get("route_accepted") is not False or
            selected.get("real_client_accepted") is not False):
        raise ValueError("selected route lacks a bound, complete offline strip audit")
    if strip is not None:
        if (selected.get("reason") != "portal_sequence_selected_final_audit_required" or
                selected.get("candidate") is not False or selected.get("points") != [] or
                strip.get("format") != "eql-copied-ground-final-strip-v1" or
                strip.get("zone") != zone or strip.get("source_sha256") != source_hash or
                strip.get("selection_sha256") != selection_hash or
                strip.get("candidate") is not True or
                strip.get("reason") != "sampled_strip_candidate_only" or
                strip.get("checked_segments") != len(polygons) or
                strip.get("route_accepted") is not False or
                strip.get("real_client_accepted") is not False):
            raise ValueError("separate full-strip audit is missing or unbound")
    elif (selected.get("candidate") is not True or
          selected.get("reason") != "sampled_ground_approach_candidate_only" or
          selected.get("ground_polygons") != len(polygons) or
          not isinstance(selected.get("strip_checks"), int) or
          selected["strip_checks"] < len(polygons) or
          selected.get("limits", {}).get("final_recheck") is False):
        raise ValueError("integrated selected route has no complete strip evidence")
    archive_root = DATA_ROOT / "client-data/retail-full/assets"
    archive = private_file(archive_root / f"{zone}.s3d", archive_root,
                           max_bytes=100 * 1024 * 1024)
    mesh_path = private_file(mesh_store / f"{zone}.npz", mesh_store,
                             max_bytes=512 * 1024 * 1024)
    manifest_path = private_file(mesh_store / f"{zone}.json", mesh_store,
                                 max_bytes=1024 * 1024)
    archive_hash, mesh_hash, manifest_hash = (digest(path) for path in
                                               (archive, mesh_path, manifest_path))
    if ((archive_hash, mesh_hash, manifest_hash) != SOURCES[zone] or
            route.get("mesh_sha256") != mesh_hash or
            selected.get("mesh_sha256") != mesh_hash or
            selected.get("manifest_sha256") not in
            ((manifest_hash,) if strip is not None else (None, manifest_hash)) or
            (strip is not None and (strip.get("mesh_sha256") != mesh_hash or
                                    strip.get("manifest_sha256") != manifest_hash))):
        raise ValueError("copied client archive or mesh provenance changed")
    # The full helper loader builds unrelated wall/link grids and can take
    # minutes on this copied Butcher mesh. This pinned, validated view mirrors
    # its stable detail-face ordering for this narrow BSP-only operation.
    from eql_automation.bsp_detail_view import BspDetailMeshView
    mesh = BspDetailMeshView.load(mesh_path, zone=zone)
    if any(int(mesh.area[poly]) != 63 for poly in polygons):
        raise ValueError("selected route has a non-ground copied polygon")
    lookup = BspPointLookup(WLDInventory(PFSArchive(archive).read_member(f"{zone}.wld")))
    frame_control = verify_helper_bsp_frame(
        lookup, json.loads(manifest_path.read_text(encoding="utf-8")))
    result = audit_ground_bsp_route(mesh, lookup, tuple(polygons),
                                    tuple(tuple(point) for point in points),
                                    max_segments=len(polygons))
    if (digest(source) != source_hash or digest(selection) != selection_hash or
            (final_strip is not None and digest(final_strip) != strip_hash) or
            (digest(archive), digest(mesh_path), digest(manifest_path)) !=
            (archive_hash, mesh_hash, manifest_hash)):
        raise ValueError("copied route or client source changed during BSP audit")
    record = {
        "format": "eql-copied-selected-bsp-v2",
        "mesh_package_to_bsp_wld": "swap_xy_keep_z",
        "frame_positive_control": frame_control,
        "zone": zone,
        "source_sha256": source_hash,
        "selection_sha256": selection_hash,
        "final_strip_sha256": strip_hash,
        "strip_evidence": "separate_full_strip" if strip is not None else "integrated_selection",
        "archive_sha256": archive_hash,
        "mesh_sha256": mesh_hash,
        "manifest_sha256": manifest_hash,
        "audit": result.to_dict(),
        "offline_only": True,
        "route_accepted": False,
        "real_client_accepted": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with NamedTemporaryFile("w", encoding="utf-8", dir=output.parent,
                            prefix=output.name + ".", suffix=".tmp", delete=False) as stream:
        os.fchmod(stream.fileno(), 0o600)
        json.dump(record, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
        temporary = Path(stream.name)
    try:
        os.link(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return {"artifact": str(output), "sha256": digest(output),
            "candidate": result.candidate, "reason": result.reason,
            "segments": result.segments, "bsp_spans": result.bsp_spans,
            "labelled": len(result.labelled), "unknown": len(result.unknown),
            "unsupported_height": len(result.unsupported_height),
            "route_accepted": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zone", required=True, choices=tuple(SOURCES))
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--final-strip", type=Path,
                        help="required for select-only results; omit for an integrated passed selector")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mesh-store", type=Path,
                        default=DATA_ROOT / "navmesh/nov12-7e3cd28-store")
    parser.add_argument("--helper-root", type=Path,
                        default=DATA_ROOT / "owner-assist/0.39.4")
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(zone=args.zone, source=args.source,
                                 selection=args.selection, final_strip=args.final_strip,
                                 output=args.output, mesh_store=args.mesh_store,
                                 helper_root=args.helper_root)))
    except (OSError, ValueError, TypeError, ImportError, IndexError,
            json.JSONDecodeError) as error:
        parser.exit(1, f"Copied BSP audit refused: {error}\n")


if __name__ == "__main__":
    main()
