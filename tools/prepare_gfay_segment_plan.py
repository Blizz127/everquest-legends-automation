#!/usr/bin/env python3
"""Export the audited GFay corridor as explicit per-polygon 3D segments.

This preserves the chosen portals and copied height on each side of a seam.
It performs no path search, shortcut, controller action or game input. The
historical G0 start still needs current live position/route acceptance.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys
import time

PROJECT = Path(__file__).resolve().parents[1]
ROOT = Path.home() / ".local/share/eql-automation"
CANDIDATES = ROOT / "nav-candidates"
SELECTION = CANDIDATES / "gfay-g0-to-orc-camp-selector-20261113T2150Z.json"
ROUTE = CANDIDATES / "gfay-g0-to-orc-camp-repair-20261113T2145Z.json"
BSP = CANDIDATES / "gfay-g0-to-orc-camp-bsp-wldframe-pinned-0.41.40.json"
MESH = ROOT / "navmesh/nov12-7e3cd28-store/gfaydark.npz"
MANIFEST = MESH.with_suffix(".json")
PINS = {
    SELECTION: "ecc62e51b9b16a2fee2e0050bda864e77ab73d74a6bdcd18f347a477c148b36f",
    ROUTE: "18fdc7d2b051d0920bd25259fea259acf7034816d5547cf2d3dec460ed47e20a",
    BSP: "2ed1de243e26aa927ff164677d6251b765e3e3ea468836ea68887298e36a9f33",
    MESH: "5f8e16c5bcd2221ba273f681750ca480349780524d23609c059a3e817df6abd9",
    MANIFEST: "ac9591eb63e1394363ad37d7d0ca6609a1ebe11fd8786bedb5b165b833e2eb82",
}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def verify(pins):
    for path, expected in pins.items():
        if path.is_symlink() or not path.is_file() or digest(path) != expected:
            raise ValueError(f"source pin changed: {path}")


def run(output):
    began = time.monotonic()
    pins = dict(PINS)
    for path in [Path(__file__), PROJECT / "eql_automation/bsp_detail_view.py",
                 PROJECT / "eql_automation/portal_surface_audit.py"]:
        pins[path] = digest(path)
    verify(pins)
    sys.path.insert(0, str(PROJECT))
    from eql_automation.bsp_detail_view import BspDetailMeshView
    from eql_automation.portal_surface_audit import _supported_detail_height

    selected = json.loads(SELECTION.read_text())
    route = json.loads(ROUTE.read_text())
    bsp = json.loads(BSP.read_text())
    if (selected["candidate"] is not True or selected["route_accepted"] is not False
            or selected["source_sha256"] != PINS[ROUTE]
            or selected["mesh_sha256"] != PINS[MESH]
            or bsp["selection_sha256"] != PINS[SELECTION]
            or bsp["mesh_sha256"] != PINS[MESH]
            or bsp["mesh_package_to_bsp_wld"] != "swap_xy_keep_z"
            or bsp["audit"]["candidate"] is not True):
        raise ValueError("selected route or corrected BSP proof is not bound")
    polygons, points = route["polygons"], selected["points"]
    if len(polygons) != 155 or len(points) != len(polygons) + 1:
        raise ValueError("unexpected selected corridor shape")
    mesh = BspDetailMeshView.load(MESH, zone="gfaydark")
    segments, seams = [], []
    for index, polygon in enumerate(polygons):
        if int(mesh.area[polygon]) != 63:
            raise ValueError("selected corridor contains non-ground polygon")
        endpoints = []
        for point in points[index:index + 2]:
            if len(point) != 2 or not all(math.isfinite(v) for v in point):
                raise ValueError("selected portal coordinate is invalid")
            height = _supported_detail_height(mesh, polygon, *point)
            if height is None or not math.isfinite(height):
                raise ValueError(f"selected portal has no detail height in polygon {polygon}")
            endpoints.append([*point, height])
        if math.dist(endpoints[0][:2], endpoints[1][:2]) <= 1e-6:
            raise ValueError("zero-length selected segment needs explicit handling")
        if segments:
            step = abs(segments[-1]["points"][1][2] - endpoints[0][2])
            if step > 0.5:
                raise ValueError("selected portal has unsupported height disagreement")
            seams.append(step)
        segments.append({"index": index, "polygon": polygon, "points": endpoints})
    verify(pins)
    record = {"format": "eql-fixed-segment-plan-v1", "zone": "gfaydark",
              "frame": "helper_package_WLD_Y_X_Z", "offline_only": True,
              "game_input_sent": False, "route_accepted": False, "real_client_accepted": False,
              "origin": "historical_owner_G0_position", "goal": "unverified_orc_camp_guide_marker",
              "half_width": selected["limits"]["half_width"],
              "maximum_grade": selected["limits"]["maximum_grade"],
              "pins": {str(p): h for p, h in pins.items()}, "segments": segments,
              "maximum_seam_height_difference": max(seams),
              "runtime_requirements": ["current_aligned_start", "fresh_scene_and_speed",
                                       "one_segment_per_follower", "no_automatic_probe_or_replan",
                                       "bounded_swept_control_guard", "stopped_raw_fix_at_portal"],
              "seconds": time.monotonic() - began}
    with output.open("x") as destination:
        json.dump(record, destination, indent=2, sort_keys=True)
        destination.write("\n")
    with output.with_suffix(".executed.py").open("x") as source:
        source.write(Path(__file__).read_text())
    return {"artifact": str(output), "sha256": digest(output), "segments": len(segments),
            "maximum_seam_height_difference": max(seams), "route_accepted": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.expanduser()
    if (output.parent.resolve() != CANDIDATES.resolve() or output.suffix != ".json"
            or output.exists() or output.is_symlink() or output.with_suffix(".executed.py").exists()):
        parser.error("use a new JSON output directly under the private nav-candidates store")
    os.umask(0o077)
    os.nice(15)
    try:
        print(json.dumps(run(output), sort_keys=True))
    except (OSError, ValueError, ImportError, KeyError) as error:
        parser.exit(1, f"Segment plan refused: {error}\n")


if __name__ == "__main__":
    main()
