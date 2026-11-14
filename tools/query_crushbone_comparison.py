#!/usr/bin/env python3
"""Query a pinned bake comparison at retained guide endpoints, offline only.

The endpoint artifact's old WLD labels actually denote the helper's Y,X,Z
frame. They are historical guide points, never a current player observation.
An optional bounded width/grade selector checks the newly computed corridor.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys
import time

ROOT = Path.home() / ".local/share/eql-automation"
PROJECT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "owner-assist/0.39.4"
BAKE_DIR = ROOT / "nav-candidates/crushbone-lower-climb-0.41.46"
ENDPOINTS = ROOT / "nav-candidates/crushbone-detail025-avoid-658-623-route-0.41.39.json"
PINS = {
    BAKE_DIR / "report.json": "17e2b9fda8d2dc25aa10f78fc51ba5d201e69211fce6fe654f98ba21682ab32d",
    ENDPOINTS: "5762a13cf23d5b3a957d7e896662ff114700a1711c3d42cbe644f1a4eb15d9ad",
    HELPER / "eqnav/bake.py": "206ea4295be00a6489409a28fe39d61afa83b3c294638f161e54fe439a80734f",
    HELPER / "eqnav/mesh.py": "89682ac2f6ee6ad4fc4e4530d946e4d7d883d860573a958d45f7cd7a074fef85",
}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def verify(pins):
    for path, expected in pins.items():
        if path.is_symlink() or not path.is_file() or digest(path) != expected:
            raise ValueError(f"source pin mismatch: {path}")


def run(output, variant, select):
    verify(PINS)
    product = BAKE_DIR / (variant + ".eqnm")
    parent = json.loads((BAKE_DIR / "report.json").read_text())
    if not parent["baseline_reproduced"] or parent["variants"][variant]["returncode"] != 0:
        raise ValueError("comparison baseline or native bake did not pass")
    pins = dict(PINS)
    pins[product] = parent["variants"][variant]["eqnm_sha256"]
    local_sources = [Path(__file__), *sorted((PROJECT / "eql_automation").glob("*audit.py")),
                     PROJECT / "eql_automation/portal_selector.py"]
    pins.update({p: digest(p) for p in local_sources})
    verify(pins)
    # Check the NumPy runtime before creating an evidence directory.
    sys.path[:0] = [str(PROJECT), str(HELPER)]
    from eqnav import bake
    from eqnav.mesh import NavMesh, NavMeshError
    from eql_automation.portal_selector import select_ground_portals

    output.mkdir(mode=0o700)
    (output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    report = {"format": "eql-crushbone-comparison-query-v1", "offline_only": True,
              "game_input_sent": False, "route_accepted": False,
              "real_client_accepted": False, "variant": variant,
              "frame": "helper_package_WLD_Y_X_Z", "endpoint_kind": "historical_guide",
              "pins": {str(p): h for p, h in pins.items()}, "completed": False,
              "status": "loading"}
    started = time.monotonic()

    def save():
        report["elapsed_seconds"] = time.monotonic() - started
        temporary = output / "report.json.tmp"
        temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        temporary.replace(output / "report.json")

    save()
    meta, arrays = bake.read_eqnm(product)
    mesh = NavMesh(bake.from_recast(arrays["poly_verts"]), arrays["poly_nv"],
                   arrays["poly_area"], arrays["link_a"], arrays["link_b"],
                   bake.from_recast(arrays["link_pts"]),
                   bake.from_recast(arrays["detail_tris"]), arrays["detail_poly"], {})
    report["baker_metadata"] = meta
    endpoints = json.loads(ENDPOINTS.read_text())
    requested = [tuple(endpoints[k]) for k in ("start_wld_xyz", "goal_wld_xyz")]
    snaps = []
    for name, point in zip(("start", "goal"), requested):
        located = mesh.locate(point, radius=1.0, up=1.0, down=1.0)
        if located is None:
            raise ValueError(f"{name} guide not within one unit of new surface")
        poly, snap = located
        if int(mesh.area[poly]) != 63:
            raise ValueError(f"{name} guide snapped outside plain ground")
        snaps.append(tuple(float(v) for v in snap))
        report[name] = {"requested": point, "snapped": snaps[-1], "polygon": int(poly),
                        "area": 63, "xy_drift": math.dist(point[:2], snap[:2]),
                        "z_drift": float(snap[2] - point[2])}
    report["status"] = "querying_graph"
    save()
    try:
        path = mesh.find_path(*snaps, water_cost=None, locate_radius=1.0, max_expansions=30000)
    except NavMeshError as error:
        report.update(status="graph_refused", reason=str(error))
    else:
        if path.areas != frozenset({63}):
            raise ValueError("query crossed a non-ground area")
        report.update(status="graph_connected", polygons=[int(p) for p in path.polys],
                      points=[list(map(float, p)) for p in path.points],
                      planar_length=float(path.length), cost=float(path.cost))
        save()
        if select:
            report["status"] = "selecting_footprint"
            report["selector_limits"] = {"half_width": 1.2, "maximum_grade": 1.2,
                                         "max_seconds": 60.0, "max_polygons": 220}
            save()
            result = select_ground_portals(
                mesh, tuple(int(p) for p in path.polys), snaps[0][:2], snaps[1][:2],
                half_width=1.2, maximum_grade=1.2, max_seconds=60,
                max_turn_seconds=5.0, max_segment_seconds=10.0)
            report.update(status="footprint_checked", selection=asdict(result))
    verify(pins)
    report["completed"] = True
    save()
    return {"report": str(output / "report.json"), "sha256": digest(output / "report.json"),
            "status": report["status"], "reason": report.get("reason"),
            "polygon_count": len(report.get("polygons", [])),
            "selection": report.get("selection"), "game_input_sent": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--variant", choices=("baseline", "lower_climb"), default="lower_climb")
    parser.add_argument("--select", action="store_true")
    args = parser.parse_args()
    output = args.output.expanduser()
    if output.exists() or output.is_symlink() or output.parent.resolve() != (ROOT / "nav-candidates").resolve():
        parser.error("output must be new and directly under the private nav-candidates store")
    os.umask(0o077)
    os.nice(15)
    try:
        print(json.dumps(run(output, args.variant, args.select), sort_keys=True))
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        parser.exit(1, f"Offline query refused: {error}\n")


if __name__ == "__main__":
    main()
