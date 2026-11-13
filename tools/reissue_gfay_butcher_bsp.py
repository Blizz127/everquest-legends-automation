#!/usr/bin/env python3
"""Reissue the saved GFay→Butcher ground BSP scan in raw WLD coordinates.

Only the historical, hash-pinned 52-ground-polygon approach is supported.
This is a static diagnostic and never permits a live zone crossing or F11.
"""
from __future__ import annotations

import argparse
import json
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
from tools.audit_selected_ground_bsp import (DATA_ROOT, HELPER_HASHES, SOURCES,
                                             digest, private_file)  # noqa: E402


ROUTE_NAME = "gfay-butcher-dry-route-20261113T2108Z.json"
ROUTE_SHA256 = "5761ec6d3a9b8676a6ca676d302276c0c28cff0351c9c7ffe0614727b6466bc0"
SELECTION_NAME = "gfay-butcher-selector-extended-20261113T2110Z.json"
SELECTION_SHA256 = "a32246bd1a848e62329fb8372102b638734144094b2893ac5d1eb6fbabfce4b4"
ZONE = "gfaydark"
GROUND_POLYGONS = 52


def inspect(output: Path, *, mesh_store: Path, helper_root: Path) -> dict:
    candidates = DATA_ROOT / "nav-candidates"
    route_path = private_file(candidates / ROUTE_NAME, candidates,
                              max_bytes=10 * 1024 * 1024)
    selected_path = private_file(candidates / SELECTION_NAME, candidates,
                                 max_bytes=10 * 1024 * 1024)
    output = output.expanduser().resolve()
    mesh_store = mesh_store.expanduser().resolve()
    helper_root = helper_root.expanduser().resolve()
    if (not output.is_relative_to(candidates.resolve()) or output.suffix != ".json" or
            output.exists() or not mesh_store.is_relative_to((DATA_ROOT / "navmesh").resolve()) or
            not helper_root.is_relative_to((DATA_ROOT / "owner-assist").resolve())):
        raise ValueError("output, mesh or helper is outside the private EQL store")
    for name, expected in HELPER_HASHES.items():
        path = private_file(helper_root / name, helper_root, max_bytes=1024 * 1024)
        if digest(path) != expected:
            raise ValueError(f"reviewed helper source changed: {name}")
    archive_root = DATA_ROOT / "client-data/retail-full/assets"
    archive = private_file(archive_root / "gfaydark.s3d", archive_root,
                           max_bytes=100 * 1024 * 1024)
    mesh_path = private_file(mesh_store / "gfaydark.npz", mesh_store,
                             max_bytes=512 * 1024 * 1024)
    manifest_path = private_file(mesh_store / "gfaydark.json", mesh_store,
                                 max_bytes=1024 * 1024)
    hashes = {"route": digest(route_path), "selection": digest(selected_path),
              "archive": digest(archive), "mesh": digest(mesh_path),
              "manifest": digest(manifest_path)}
    if (hashes["route"] != ROUTE_SHA256 or hashes["selection"] != SELECTION_SHA256 or
            tuple(hashes[name] for name in ("archive", "mesh", "manifest")) != SOURCES[ZONE]):
        raise ValueError("saved GFay route or copied source provenance changed")
    route = json.loads(route_path.read_text(encoding="utf-8"))
    selected = json.loads(selected_path.read_text(encoding="utf-8"))
    polygons = route.get("path_polygons")
    points = selected.get("points")
    if (route.get("mesh_sha256") != hashes["mesh"] or
            route.get("manifest_sha256") != hashes["manifest"] or
            route.get("offline_only") is not True or route.get("route_accepted") is not False or
            route.get("real_client_accepted") is not False or
            selected.get("source_artifact_sha256") != hashes["route"] or
            selected.get("mesh_sha256") != hashes["mesh"] or
            selected.get("candidate") is not True or
            selected.get("reason") != "sampled_ground_approach_candidate_only" or
            selected.get("ground_polygons") != GROUND_POLYGONS or
            selected.get("strip_checks", 0) < GROUND_POLYGONS or
            selected.get("route_accepted") is not False or
            selected.get("real_client_accepted") is not False or
            not isinstance(polygons, list) or len(polygons) != GROUND_POLYGONS + 3 or
            not isinstance(points, list) or len(points) != GROUND_POLYGONS + 1):
        raise ValueError("saved GFay ground prefix is not bound to its selector")
    ground = tuple(polygons[:GROUND_POLYGONS])
    from eql_automation.bsp_detail_view import BspDetailMeshView
    mesh = BspDetailMeshView.load(mesh_path, zone=ZONE)
    if any(not isinstance(poly, int) or isinstance(poly, bool) or
           poly < 0 or int(mesh.area[poly]) != 63 for poly in ground):
        raise ValueError("GFay prefix contains a missing or non-ground polygon")
    lookup = BspPointLookup(WLDInventory(PFSArchive(archive).read_member("gfaydark.wld")))
    frame_control = verify_helper_bsp_frame(
        lookup, json.loads(manifest_path.read_text(encoding="utf-8")))
    audit = audit_ground_bsp_route(mesh, lookup, ground, points,
                                   max_segments=GROUND_POLYGONS)
    if any(digest(path) != hashes[name] for name, path in
           (("route", route_path), ("selection", selected_path),
            ("archive", archive), ("mesh", mesh_path), ("manifest", manifest_path))):
        raise ValueError("saved GFay source changed during BSP audit")
    record = {"format": "eql-copied-legacy-gfay-bsp-v2", "zone": ZONE,
              "mesh_package_to_bsp_wld": "swap_xy_keep_z",
              "frame_source_sha256": HELPER_HASHES["eqnav/zonegeom.py"],
              "frame_positive_control": frame_control,
              "route_sha256": hashes["route"], "selection_sha256": hashes["selection"],
              "archive_sha256": hashes["archive"], "mesh_sha256": hashes["mesh"],
              "manifest_sha256": hashes["manifest"], "ground_polygons": len(ground),
              "audit": audit.to_dict(), "offline_only": True,
              "route_accepted": False, "real_client_accepted": False}
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
            "ground_polygons": len(ground), "bsp_spans": audit.bsp_spans,
            "labelled": len(audit.labelled), "unknown": len(audit.unknown),
            "unsupported_height": len(audit.unsupported_height),
            "candidate": audit.candidate, "route_accepted": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mesh-store", type=Path,
                        default=DATA_ROOT / "navmesh/nov12-7e3cd28-store")
    parser.add_argument("--helper-root", type=Path,
                        default=DATA_ROOT / "owner-assist/0.39.4")
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.output, mesh_store=args.mesh_store,
                                 helper_root=args.helper_root)))
    except (OSError, ValueError, TypeError, IndexError, json.JSONDecodeError) as error:
        parser.exit(1, f"GFay BSP reissue refused: {error}\n")


if __name__ == "__main__":
    main()
