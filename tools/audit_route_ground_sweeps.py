#!/usr/bin/env python3
"""Check bounded GFay ground footprints using explicit hypothetical motion.

No client/device input. The bounds below are diagnostic assumptions, not
live speed, timing, body dimensions or permission to move a character.
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

PROJECT = Path(__file__).resolve().parents[1]
STORE = Path.home() / ".local/share/eql-automation"
PLAN = STORE / "nav-candidates/gfay-fixed-segment-plan-0.41.48.json"
MESH = STORE / "navmesh/nov12-7e3cd28-store/gfaydark.npz"
PINS = {
    PLAN: "145679ec15111cf2d319ca630c66da693cc69863bdef594f67a46989c18592a4",
    MESH: "5f8e16c5bcd2221ba273f681750ca480349780524d23609c059a3e817df6abd9",
    MESH.with_suffix(".json"): "ac9591eb63e1394363ad37d7d0ca6609a1ebe11fd8786bedb5b165b833e2eb82",
}


def run(output):
    began = time.monotonic()
    pins = dict(PINS)
    for p in (Path(__file__), PROJECT / "eql_automation/ground_sweep.py"):
        pins[p] = sha256(p.read_bytes()).hexdigest()
    def verify():
        if any(p.is_symlink() or sha256(p.read_bytes()).hexdigest() != h for p, h in pins.items()):
            raise ValueError("Copied ground sweep source changed")
    verify()
    import numpy as np
    sys.path.insert(0, str(PROJECT))
    from eql_automation.ground_sweep import GroundFace, check_ground_coverage, motion_footprint
    plan = json.loads(PLAN.read_text())
    assert plan["frame"] == "helper_package_WLD_Y_X_Z" and plan["route_accepted"] is False
    with np.load(MESH, allow_pickle=False) as data:
        triangles = np.asarray(data["detail_tris"], dtype=np.float64).reshape(-1, 3, 3)
        polys = np.asarray(data["detail_poly"], dtype=np.int64)
        areas = np.asarray(data["poly_area"], dtype=np.int64)
        components = np.asarray(data["component"], dtype=np.int64)
    minimum, maximum = triangles.min(axis=1), triangles.max(axis=1)
    records = []
    for index in (0, 26, 113):
        segment = plan["segments"][index]
        start, end = segment["points"]
        length = math.dist(start[:2], end[:2])
        heading = math.degrees(math.atan2(end[0] - start[0], end[1] - start[1])) % 360
        requested = min(.1, max(.02, length / 30.77))
        for key in ("pivot", "forward"):
            reach = 0. if key == "pivot" else 35. * (requested + .02)
            footprint = motion_footprint(tuple(start[:2]), heading, reach,
                position_error=.05, heading_error_degrees=2., post_release_drift=.05, extra_radius=.2)
            left = np.min(footprint, axis=0)
            right = np.max(footprint, axis=0)
            local = np.flatnonzero((minimum[:, 0] <= right[0]) & (maximum[:, 0] >= left[0])
                                  & (minimum[:, 1] <= right[1]) & (maximum[:, 1] >= left[1]))
            faces = tuple(GroundFace(tuple(tuple(float(v) for v in p) for p in triangles[i]),
                                     int(areas[polys[i]]), int(components[polys[i]])) for i in local)
            window = max(math.dist(start[:2], p) for p in footprint) + .05
            result = check_ground_coverage(footprint, faces, reference=tuple(start),
                component=int(components[segment["polygon"]]), vertical_window=window)
            records.append({"segment": index, "key": key, "polygon": segment["polygon"],
                            "requested_seconds": requested if key == "forward" else None,
                            "reach": reach, "footprint": footprint, "reference": start,
                            "vertical_window": window, "local_detail_ids": local.tolist(),
                            "result": asdict(result)})
    verify()
    record = {"format": "eql-continuous-ground-sweep-v1", "simulation_bounds_only": True,
              "game_input_sent": False, "real_client_accepted": False, "input_authorized": False,
              "assumptions": {"speed_upper": 35., "release_overrun_seconds": .02,
                              "heading_error_degrees": 2., "position_error": .05,
                              "post_release_drift": .05, "extra_radius": .2,
                              "extra_radius_is_verified_body_size": False},
              "not_checked": ["live_calibration", "source_collision_walls_and_headroom",
                              "continuous_BSP_hazards", "dynamic_obstacles", "client_movement"],
              "records": records, "pins": {str(p): h for p, h in pins.items()},
              "seconds": time.monotonic() - began}
    with output.open("x") as out:
        json.dump(record, out, indent=2); out.write("\n")
    print(json.dumps({"artifact": str(output), "sha256": sha256(output.read_bytes()).hexdigest(),
                      "results": [{"segment": r["segment"], "key": r["key"], **r["result"]} for r in records],
                      "seconds": record["seconds"]}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    output = parser.parse_args().output.expanduser()
    if output.parent.resolve() != (STORE / "nav-candidates").resolve() or output.exists() or output.is_symlink() or output.suffix != ".json":
        parser.error("use a new JSON directly under the private nav-candidates store")
    os.umask(0o077)
    os.nice(15)
    run(output)


if __name__ == "__main__":
    main()
