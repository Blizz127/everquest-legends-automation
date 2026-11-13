#!/usr/bin/env python3
"""Recheck a copied ground corridor offline; never send game input.

Input artifacts and the mesh must live in the private EQL data store. A
sampled candidate remains separate from a verified client route or F11 permit.
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
import time


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from eql_automation.portal_selector import select_ground_portals  # noqa: E402

DATA_ROOT = Path.home() / ".local/share/eql-automation"


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def private_file(path: Path, area: str, *, limit: int) -> Path:
    path = path.expanduser().resolve()
    if (not path.is_relative_to((DATA_ROOT / area).resolve()) or
            not path.is_file() or not 0 < path.stat().st_size <= limit):
        raise ValueError(f"expected a bounded file under {DATA_ROOT / area}")
    return path


def xy(value) -> tuple[float, float]:
    if (not isinstance(value, (list, tuple)) or len(value) < 2 or
            any(not isinstance(n, (int, float)) or isinstance(n, bool) or
                not math.isfinite(n) for n in value[:2])):
        raise ValueError("route endpoint is missing or nonfinite")
    return float(value[0]), float(value[1])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zone", required=True,
                        choices=("gfaydark", "butcher", "crushbone", "cauldron", "unrest"))
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--endpoints", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mesh-store", required=True, type=Path)
    parser.add_argument("--helper-root", required=True, type=Path,
                        help="Owner-assist bundle containing the copied eqnav reader")
    parser.add_argument("--ground-prefix", type=int)
    parser.add_argument("--max-seconds", type=float, default=240.0)
    parser.add_argument("--max-turn-seconds", type=float, default=10.0)
    parser.add_argument("--max-segment-seconds", type=float, default=20.0)
    parser.add_argument("--max-candidates-per-portal", type=int, default=6)
    parser.add_argument("--max-strip-repair-rounds", type=int, default=8)
    parser.add_argument("--repair-backtrack-depth", type=int, default=1)
    parser.add_argument("--half-width", type=float, default=1.2)
    parser.add_argument("--maximum-grade", type=float, default=1.0)
    parser.add_argument("--select-only", action="store_true",
                        help="Save unverified portal points for a separate full-strip recheck")
    args = parser.parse_args()
    try:
        source = private_file(args.source, "nav-candidates", limit=10 * 1024 * 1024)
        endpoints = private_file(args.endpoints, "nav-candidates", limit=10 * 1024 * 1024)
        store = args.mesh_store.expanduser().resolve()
        helper = args.helper_root.expanduser().resolve()
        output = args.output.expanduser().resolve()
        if (not store.is_relative_to((DATA_ROOT / "navmesh").resolve()) or
                not helper.is_relative_to((DATA_ROOT / "owner-assist").resolve()) or
                not (helper / "eqnav/world.py").is_file() or
                not output.is_relative_to((DATA_ROOT / "nav-candidates").resolve()) or
                output.suffix != ".json" or output.exists()):
            raise ValueError("mesh, helper or output path is outside the approved private store")
        source_hash = digest(source)
        endpoints_hash = digest(endpoints)
        route = json.loads(source.read_text(encoding="utf-8"))
        end = json.loads(endpoints.read_text(encoding="utf-8"))
        if not isinstance(route, dict) or not isinstance(end, dict):
            raise ValueError("route artifacts must be JSON objects")
        raw_polygons = route.get("polygons", route.get("path_polygons"))
        if (not isinstance(raw_polygons, list) or not raw_polygons or
                any(not isinstance(p, int) or isinstance(p, bool) or p < 0
                    for p in raw_polygons)):
            raise ValueError("source has no valid polygon corridor")
        if args.ground_prefix is not None:
            if not 1 <= args.ground_prefix <= len(raw_polygons):
                raise ValueError("ground prefix is outside corridor")
            raw_polygons = raw_polygons[:args.ground_prefix]
        start = route.get("start_wld_xyz") or end.get("start_wld_xyz")
        if start is None:
            start = route.get("path_points", [None])[0]
        goal = (end.get("standoff_xy") or end.get("snapped_goal_wld_xyz") or
                end.get("goal_wld_xyz"))
        if goal is None:
            goal = route.get("path_points", [None])[-1]
        start_xy, goal_xy = xy(start), xy(goal)
        limits = (args.max_seconds, args.max_turn_seconds,
                  args.max_segment_seconds, args.half_width, args.maximum_grade)
        if any(not math.isfinite(v) or v <= 0 for v in limits):
            raise ValueError("all selection limits must be positive and finite")
        if (not 1 <= args.max_candidates_per_portal <= 13 or
                not 0 <= args.max_strip_repair_rounds <= 32 or
                not 1 <= args.repair_backtrack_depth <= 8):
            raise ValueError("portal candidate or strip repair limit is outside bounds")
        sys.path.append(str(helper))
        from eqnav.mesh import AREA_GROUND
        from eqnav.world import MeshStore
        mesh = MeshStore(store).load(args.zone)
        mesh_path = store / f"{args.zone}.npz"
        manifest_path = store / f"{args.zone}.json"
        mesh_hash = digest(mesh_path)
        manifest_hash = digest(manifest_path)
        if route.get("mesh_sha256") != mesh_hash or (
                end.get("mesh_sha256") not in (None, mesh_hash)):
            raise ValueError("route artifact and copied mesh hashes disagree")
        polygons = tuple(raw_polygons)
        if any(p >= mesh.count or int(mesh.area[p]) != AREA_GROUND for p in polygons):
            raise ValueError("corridor contains a missing or non-ground polygon")
        began = time.monotonic()
        result = select_ground_portals(
            mesh, polygons, start_xy, goal_xy, max_polygons=len(polygons),
            max_seconds=args.max_seconds,
            max_turn_seconds=args.max_turn_seconds,
            max_segment_seconds=args.max_segment_seconds,
            max_candidates_per_portal=args.max_candidates_per_portal,
            max_strip_repair_rounds=args.max_strip_repair_rounds,
            repair_backtrack_depth=args.repair_backtrack_depth,
            half_width=args.half_width, maximum_grade=args.maximum_grade,
            final_recheck=not args.select_only)
        if (digest(source) != source_hash or digest(endpoints) != endpoints_hash or
                digest(mesh_path) != mesh_hash or
                digest(manifest_path) != manifest_hash):
            raise ValueError("a copied route or mesh source changed during selection")
        record = {
            "format": "eql-copied-ground-selector-v1", "zone": args.zone,
            "source_sha256": source_hash, "endpoints_sha256": endpoints_hash,
            "mesh_sha256": mesh_hash, "manifest_sha256": manifest_hash,
            "ground_polygons": len(polygons),
            "limits": {"max_seconds": args.max_seconds,
                       "max_turn_seconds": args.max_turn_seconds,
                       "max_segment_seconds": args.max_segment_seconds,
                       "max_candidates_per_portal": args.max_candidates_per_portal,
                       "max_strip_repair_rounds": args.max_strip_repair_rounds,
                       "repair_backtrack_depth": args.repair_backtrack_depth,
                       "half_width": args.half_width,
                       "maximum_grade": args.maximum_grade,
                       "final_recheck": not args.select_only},
            "elapsed_seconds": round(time.monotonic() - began, 3),
            "candidate": result.candidate, "reason": result.reason,
            "failed_polygon": result.failed_polygon,
            "turn_checks": result.turn_checks, "strip_checks": result.strip_checks,
            "fractions": result.fractions, "points": result.points,
            "unverified_fractions": result.unverified_fractions,
            "unverified_points": result.unverified_points,
            "offline_only": True, "route_accepted": False,
            "real_client_accepted": False,
        }
        output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with NamedTemporaryFile("w", encoding="utf-8", dir=output.parent,
                                prefix=output.name + ".", suffix=".tmp",
                                delete=False) as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(record, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
            temporary = Path(stream.name)
        temporary.replace(output)
        print(json.dumps({"artifact": str(output), "sha256": digest(output),
                          "candidate": result.candidate, "reason": result.reason,
                          "failed_polygon": result.failed_polygon,
                          "turn_checks": result.turn_checks,
                          "strip_checks": result.strip_checks,
                          "elapsed_seconds": record["elapsed_seconds"]}))
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
