#!/usr/bin/env python3
"""Recheck a saved, unverified copied-ground selection's entire strip.

This consumes diagnostic points left by a bounded portal selector after its
final pass ran out of work. The result is offline geometry evidence only.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile
import time

from select_copied_ground_route import DATA_ROOT, digest, private_file, xy

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from eql_automation.strip_route_audit import audit_route_strips  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zone", required=True,
                        choices=("gfaydark", "butcher", "crushbone"))
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mesh-store", required=True, type=Path)
    parser.add_argument("--helper-root", required=True, type=Path)
    parser.add_argument("--max-seconds", type=float, default=240.0)
    parser.add_argument("--max-segment-seconds", type=float, default=30.0)
    args = parser.parse_args()
    try:
        source = private_file(args.source, "nav-candidates", limit=10 * 1024 * 1024)
        selected = private_file(args.selection, "nav-candidates", limit=10 * 1024 * 1024)
        store = args.mesh_store.expanduser().resolve()
        helper = args.helper_root.expanduser().resolve()
        output = args.output.expanduser().resolve()
        if (not store.is_relative_to((DATA_ROOT / "navmesh").resolve()) or
                not helper.is_relative_to((DATA_ROOT / "owner-assist").resolve()) or
                not (helper / "eqnav/world.py").is_file() or
                not output.is_relative_to((DATA_ROOT / "nav-candidates").resolve()) or
                output.suffix != ".json" or output.exists()):
            raise ValueError("mesh, helper or output path is outside the approved private store")
        if (not math.isfinite(args.max_seconds) or not 0 < args.max_seconds <= 600 or
                not math.isfinite(args.max_segment_seconds) or
                not 0 < args.max_segment_seconds <= 60):
            raise ValueError("final strip time limits are invalid")
        source_hash, selection_hash = digest(source), digest(selected)
        route = json.loads(source.read_text(encoding="utf-8"))
        selection = json.loads(selected.read_text(encoding="utf-8"))
        if (not isinstance(route, dict) or not isinstance(selection, dict) or
                selection.get("format") != "eql-copied-ground-selector-v1" or
                selection.get("zone") != args.zone or
                selection.get("source_sha256") != source_hash or
                route.get("offline_only") is not True or
                route.get("route_accepted") is not False or
                route.get("real_client_accepted") is not False or
                selection.get("candidate") is not False or
                selection.get("route_accepted") is not False or
                selection.get("real_client_accepted") is not False or
                selection.get("points") != []):
            raise ValueError("selection is not a bound, unverified portal result")
        raw_polys = route.get("polygons", route.get("path_polygons"))
        points_raw = selection.get("unverified_points")
        fractions_raw = selection.get("unverified_fractions")
        if (not isinstance(raw_polys, list) or not raw_polys or
                any(not isinstance(p, int) or isinstance(p, bool) or p < 0
                    for p in raw_polys) or
                not isinstance(points_raw, list) or
                len(points_raw) != len(raw_polys) + 1 or
                not isinstance(fractions_raw, list) or
                len(fractions_raw) != len(raw_polys) - 1 or
                any(not isinstance(f, (int, float)) or isinstance(f, bool) or
                    not math.isfinite(f) or not 0 < f < 1 for f in fractions_raw) or
                not isinstance(selection.get("turn_checks"), int) or
                isinstance(selection.get("turn_checks"), bool) or
                selection["turn_checks"] < len(raw_polys) - 1 or
                not isinstance(selection.get("strip_checks"), int) or
                isinstance(selection.get("strip_checks"), bool) or
                selection["strip_checks"] < len(raw_polys)):
            raise ValueError("selection has no complete unverified portal sequence")
        points = tuple(xy(point) for point in points_raw)
        start = route.get("start_wld_xyz")
        goal = route.get("snapped_goal_wld_xyz")
        if start is None or goal is None or points[0] != xy(start) or points[-1] != xy(goal):
            raise ValueError("unverified points do not bind route endpoints")
        limits = selection.get("limits")
        if (not isinstance(limits, dict) or
                not isinstance(limits.get("half_width"), (int, float)) or
                isinstance(limits.get("half_width"), bool) or
                not isinstance(limits.get("maximum_grade"), (int, float)) or
                isinstance(limits.get("maximum_grade"), bool) or
                not math.isfinite(limits["half_width"]) or
                not math.isfinite(limits["maximum_grade"]) or
                limits["half_width"] <= 0 or limits["maximum_grade"] <= 0):
            raise ValueError("selection lacks bounded width and grade provenance")
        sys.path.append(str(helper))
        from eqnav.mesh import AREA_GROUND
        from eqnav.world import MeshStore
        mesh = MeshStore(store).load(args.zone)
        mesh_path = store / f"{args.zone}.npz"
        manifest_path = store / f"{args.zone}.json"
        mesh_hash, manifest_hash = digest(mesh_path), digest(manifest_path)
        if (route.get("mesh_sha256") != mesh_hash or
                selection.get("mesh_sha256") != mesh_hash or
                selection.get("manifest_sha256") != manifest_hash):
            raise ValueError("route, selection and copied mesh hashes disagree")
        polys = tuple(raw_polys)
        if (any(p >= mesh.count or int(mesh.area[p]) != AREA_GROUND for p in polys) or
                selection.get("ground_polygons") != len(polys)):
            raise ValueError("selected corridor is not the supplied ground corridor")
        began = time.monotonic()
        result = audit_route_strips(
            mesh, polys, points, max_segments=len(polys),
            max_total_samples=100000, max_seconds=args.max_seconds,
            max_segment_samples=2048,
            max_segment_seconds=args.max_segment_seconds,
            sample_spacing=1.0, half_width=float(limits["half_width"]),
            maximum_grade=float(limits["maximum_grade"]))
        if (digest(source) != source_hash or digest(selected) != selection_hash or
                digest(mesh_path) != mesh_hash or
                digest(manifest_path) != manifest_hash):
            raise ValueError("a copied route or mesh source changed during recheck")
        record = {
            "format": "eql-copied-ground-final-strip-v1", "zone": args.zone,
            "source_sha256": source_hash, "selection_sha256": selection_hash,
            "mesh_sha256": mesh_hash, "manifest_sha256": manifest_hash,
            "ground_polygons": len(polys), "sample_spacing": 1.0,
            "half_width": float(limits["half_width"]),
            "maximum_grade": float(limits["maximum_grade"]),
            "max_seconds": args.max_seconds,
            "max_segment_seconds": args.max_segment_seconds,
            "elapsed_seconds": round(time.monotonic() - began, 3),
            "candidate": result.candidate, "reason": result.reason,
            "checked_segments": result.checked_segments,
            "samples": result.samples,
            "failed_segment": result.failed_segment,
            "failed_polygon": result.failed_polygon,
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
                          "checked_segments": result.checked_segments,
                          "failed_polygon": result.failed_polygon,
                          "elapsed_seconds": record["elapsed_seconds"]}))
    except (OSError, TypeError, ValueError, IndexError, json.JSONDecodeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
