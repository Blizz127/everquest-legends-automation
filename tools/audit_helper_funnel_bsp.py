#!/usr/bin/env python3
"""Recheck a copied helper-frame funnel against raw client WLD BSP.

The result covers only its saved straight segments at two heights. It cannot
accept a route, a full walking strip, a zone transition or client movement.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from eql_automation.bsp_probe import BspPointLookup  # noqa: E402
from eql_automation.ground_bsp_route import (audit_helper_funnel_bsp,
                                             verify_helper_bsp_frame)  # noqa: E402
from eql_automation.pfs_archive import PFSArchive  # noqa: E402
from eql_automation.wld_inventory import WLDInventory  # noqa: E402


DATA_ROOT = Path.home() / ".local/share/eql-automation"
FRAME_SOURCE_SHA256 = "bffd21c5767b111f9516180377838d180bf31e3af8e2bc427258c987d6609a60"
SOURCES = {
    "cauldron": {
        "archive": "a035788d5df592e313d7b2a7998a3ceae300ebe68cf9e837c2509a2cd98b4409",
        "mesh": "884bb7c888aa25cfce2286053ab437facdd5e979fb5227da6c066208c8b77a29",
        "manifest": "7fa85bdeb68e8b1ab66b6cbd30ff53dd2702a1ac15580c4477ea001637f05146",
        "route_format": "eql-cauldron-butch-to-unrest-dry-v1",
    },
    "unrest": {
        "archive": "e34c4b636d731dbf67dcb5ac028a75ac4e68c9a45a4a6cabd1cdce0f6793df1f",
        "mesh": "2b8fdb3f54078a3977e04df46e69b53d41a72ab56c4783cfe28334e08d4bdace",
        "manifest": "8224bd5a1c6dbf721bd801a4310148fc6f472b9ee9cab687078a28f883f31786",
        "route_format": "eql-unrest-entry-to-yard-dry-v1",
    },
}


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def private_file(path: Path, root: Path, *, max_bytes: int) -> Path:
    path = path.expanduser()
    resolved = path.resolve()
    if (path.is_symlink() or not resolved.is_relative_to(root.resolve()) or
            not resolved.is_file() or not 0 < resolved.stat().st_size <= max_bytes):
        raise ValueError(f"expected a bounded regular file under {root}")
    return resolved


def inspect(*, zone: str, route_path: Path, output: Path,
            mesh_store: Path = DATA_ROOT / "navmesh/nov12-7e3cd28-store",
            helper_root: Path = DATA_ROOT / "owner-assist/0.39.4") -> dict:
    expected = SOURCES.get(zone)
    if expected is None:
        raise ValueError("zone has no pinned copied helper funnel")
    candidates = DATA_ROOT / "nav-candidates"
    route_path = private_file(route_path, candidates, max_bytes=10 * 1024 * 1024)
    output = output.expanduser().resolve()
    mesh_store = mesh_store.expanduser().resolve()
    helper_root = helper_root.expanduser().resolve()
    if (not output.is_relative_to(candidates.resolve()) or output.suffix != ".json" or
            output.exists() or not mesh_store.is_relative_to((DATA_ROOT / "navmesh").resolve()) or
            not helper_root.is_relative_to((DATA_ROOT / "owner-assist").resolve())):
        raise ValueError("output, mesh or helper is outside the private EQL store")
    frame_source = private_file(helper_root / "eqnav/zonegeom.py", helper_root,
                                max_bytes=1024 * 1024)
    if digest(frame_source) != FRAME_SOURCE_SHA256:
        raise ValueError("reviewed helper frame source changed")
    archive_root = DATA_ROOT / "client-data/retail-full/assets"
    archive = private_file(archive_root / f"{zone}.s3d", archive_root,
                           max_bytes=100 * 1024 * 1024)
    mesh = private_file(mesh_store / f"{zone}.npz", mesh_store,
                        max_bytes=512 * 1024 * 1024)
    manifest = private_file(mesh_store / f"{zone}.json", mesh_store,
                            max_bytes=1024 * 1024)
    hashes = {"route": digest(route_path), "archive": digest(archive),
              "mesh": digest(mesh), "manifest": digest(manifest)}
    if any(hashes[name] != expected[name] for name in ("archive", "mesh", "manifest")):
        raise ValueError("copied client archive or helper mesh provenance changed")
    route = json.loads(route_path.read_text(encoding="utf-8"))
    if (not isinstance(route, dict) or route.get("zone") != zone or
            route.get("format") != expected["route_format"] or
            route.get("mesh_sha256") != hashes["mesh"] or
            route.get("manifest_sha256") != hashes["manifest"] or
            route.get("offline_only") is not True or route.get("route_accepted") is not False or
            route.get("real_client_accepted") is not False):
        raise ValueError("saved helper funnel is not bound to the copied mesh")
    lookup = BspPointLookup(WLDInventory(PFSArchive(archive).read_member(f"{zone}.wld")))
    frame_control = verify_helper_bsp_frame(
        lookup, json.loads(manifest.read_text(encoding="utf-8")))
    audit = audit_helper_funnel_bsp(lookup, route.get("path_points"))
    if (digest(route_path) != hashes["route"] or digest(archive) != hashes["archive"] or
            digest(mesh) != hashes["mesh"] or digest(manifest) != hashes["manifest"] or
            digest(frame_source) != FRAME_SOURCE_SHA256):
        raise ValueError("copied funnel source changed during BSP audit")
    record = {
        "format": "eql-copied-helper-funnel-bsp-v2", "zone": zone,
        "mesh_package_to_bsp_wld": "swap_xy_keep_z",
        "frame_source_sha256": FRAME_SOURCE_SHA256,
        "frame_positive_control": frame_control,
        "route_sha256": hashes["route"], "archive_sha256": hashes["archive"],
        "mesh_sha256": hashes["mesh"], "manifest_sha256": hashes["manifest"],
        "wld_sha256": lookup_source_sha(archive, zone),
        "height_offsets": [0.0, 1.0], "audit": audit.to_dict(),
        "full_ground_strip_checked": False,
        "offline_only": True, "route_accepted": False, "real_client_accepted": False,
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
            "zone": zone, "segments": audit.segments, "bsp_spans": audit.bsp_spans,
            "labelled": len(audit.labelled), "unknown": len(audit.unknown),
            "candidate": audit.candidate, "route_accepted": False}


def lookup_source_sha(archive: Path, zone: str) -> str:
    return sha256(PFSArchive(archive).read_member(f"{zone}.wld")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zone", required=True, choices=tuple(SOURCES))
    parser.add_argument("--route", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mesh-store", type=Path,
                        default=DATA_ROOT / "navmesh/nov12-7e3cd28-store")
    parser.add_argument("--helper-root", type=Path,
                        default=DATA_ROOT / "owner-assist/0.39.4")
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(zone=args.zone, route_path=args.route,
                                 output=args.output, mesh_store=args.mesh_store,
                                 helper_root=args.helper_root)))
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        parser.exit(1, f"Copied helper funnel BSP audit refused: {error}\n")


if __name__ == "__main__":
    main()
