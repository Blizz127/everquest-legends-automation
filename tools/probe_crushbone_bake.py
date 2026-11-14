#!/usr/bin/env python3
"""Compare two bounded copied-client Crushbone bakes; never send game input.

The full ordered triangle set preserves the original grid origin. A repeated
baseline must reproduce the retained mesh's local heights before cell-size
or detail-sampling sensitivity is attempted. Every product stays private.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path.home() / ".local/share/eql-automation"
HELPER = ROOT / "owner-assist/0.39.4"
ASSETS = ROOT / "client-data/retail-full/assets"
BAKER = ROOT / "nav-candidates/trainer-sensitivity-20261113T1557Z/eqlnav_bake"
REFERENCE = ROOT / "navmesh/crushbone-detail025-cut-v1/crushbone.npz"
PINS = {
    HELPER / "eqnav/bake.py": "206ea4295be00a6489409a28fe39d61afa83b3c294638f161e54fe439a80734f",
    HELPER / "eqnav/mesh.py": "89682ac2f6ee6ad4fc4e4530d946e4d7d883d860573a958d45f7cd7a074fef85",
    HELPER / "eqnav/zonegeom.py": "bffd21c5767b111f9516180377838d180bf31e3af8e2bc427258c987d6609a60",
    HELPER / "eqnav/pfs.py": "34c5ece6bf25ebb0ac4c61b42019e5855057b22e96661f3b749e212a881be4a4",
    HELPER / "eqnav/wld.py": "523115475bdaead95568ae6a9b42fbb20c54ceaed290f28c21aeefd2a0c524bf",
    ASSETS / "crushbone.s3d": "a2591482aac0a478caec1d79bf662a3f0f93d4ef2dc423be8f7591fe6d45e36f",
    ASSETS / "crushbone_obj.s3d": "d80521fdb69c53497d3070b4869dd33ecbdeafdca9ee5f6a3010a93e228f14a5",
    BAKER: "072f9b06935ef76d870219e4e2812146006d0c86fdca4bb6c78b70eed4383d44",
    REFERENCE: "ba544e96700b51777d81c522c3dd6eba27c4d4a1af387852bf70729086158e56",
}
CENTER = (-180.14373779296875, 98.74378967285156, 0.35)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def check_sources() -> None:
    for path, expected in PINS.items():
        if path.is_symlink() or not path.is_file() or digest(path) != expected:
            raise ValueError(f"copied source pin mismatch: {path}")


def checkpoint(output: Path, record: dict) -> None:
    temporary = output / "report.json.tmp"
    temporary.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    temporary.replace(output / "report.json")


def sample_ground(mesh) -> dict:
    from eql_automation.lateral_strip_audit import _ground_height
    located = mesh.locate(CENTER, radius=0.1)
    if located is None:
        raise ValueError("fixed probe point is off mesh")
    poly, point = located
    if math.hypot(point[0] - CENTER[0], point[1] - CENTER[1]) > 0.0005 or int(mesh.area[poly]) != 63:
        raise ValueError("fixed probe point snapped away or is not ground")
    center_z = float(point[2])
    component = int(mesh.component[poly])
    if component < 0:
        raise ValueError("fixed probe component is unknown")
    rings = []
    previous = [center_z] * 32
    previous_radius = 0.0
    for radius in (0.6, 1.2):
        heights = []
        for direction in range(32):
            angle = 2 * math.pi * direction / 32
            x, y = CENTER[0] + radius * math.cos(angle), CENTER[1] + radius * math.sin(angle)
            reason, z = _ground_height(mesh, x, y, center_z, component, 24, radius * 1.2 + 0.5)
            if z is None:
                raise ValueError(f"fixed ground probe unsupported: {radius}/{direction}: {reason}")
            heights.append(float(z))
        radial_grade = max(max(abs(z - center_z) / radius,
                               abs(z - prior) / (radius - previous_radius))
                           for z, prior in zip(heights, previous))
        chord = 2 * radius * math.sin(math.pi / 32)
        angular_grade = max(abs(z - heights[(index + 1) % 32]) / chord
                            for index, z in enumerate(heights))
        rings.append({"radius": radius, "heights": heights,
                      "minimum_z": min(heights), "maximum_z": max(heights),
                      "maximum_radial_grade": radial_grade,
                      "maximum_angular_grade": angular_grade})
        previous, previous_radius = heights, radius
    return {"polygon": int(poly), "center_z": center_z, "rings": rings}


def run(output: Path, comparison: str = "cell") -> dict:
    variants = {
        "cell": (("baseline", {}), ("half_cell", {"cell_size": 0.3})),
        "detail": (("baseline", {}), ("half_detail_distance", {"detail_sample_dist": 3})),
    }
    if comparison not in variants:
        raise ValueError("comparison must be cell or detail")
    check_sources()
    project = Path(__file__).resolve().parents[1]
    local_sources = {path: digest(path) for path in
                     (Path(__file__).resolve(), project / "eql_automation/lateral_strip_audit.py",
                      project / "eql_automation/portal_surface_audit.py")}
    sys.path.insert(0, str(HELPER))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from eqnav import bake
    from eqnav.mesh import NavMesh
    from eqnav.zonegeom import load_zone_geometry, LAVA, WATER, ZONELINE

    geometry = load_zone_geometry(ASSETS, "crushbone")
    if len(geometry.triangles) != 26570 or geometry.rejected:
        raise ValueError("copied triangle inventory differs from retained baseline")
    def area_of(code, line):
        # Reproduce the retained helper classifier exactly, including its
        # existing normal/other-region mapping; this is not area acceptance.
        if code == LAVA:
            return 0
        if code == WATER:
            return 1
        if code == ZONELINE and line is not None and line < 61:
            return 2 + line
        return 63
    nodes = bake.classifier_nodes(*geometry.regions.area_classifier(area_of))
    if len(nodes) != 5586:
        raise ValueError("copied classifier inventory differs from retained baseline")
    output.mkdir(mode=0o700)
    (output / "probe-source.py").write_bytes(Path(__file__).read_bytes())
    eqtr = output / "crushbone.eqtr"
    bake.write_eqtr(eqtr, geometry.triangles, nodes)
    reference = sample_ground(NavMesh.load(REFERENCE))
    record = {"format": "eql-crushbone-bake-probe-v1", "offline_only": True,
              "comparison": comparison,
              "game_input_sent": False, "route_accepted": False,
              "real_client_accepted": False, "probe_frame": "helper_package_WLD_Y_X_Z",
              "center": list(CENTER), "pins": {str(p): h for p, h in PINS.items()},
              "project_sources": {str(p): h for p, h in local_sources.items()},
              "tool_sha256": digest(Path(__file__)), "eqtr_sha256": digest(eqtr),
              "triangles": len(geometry.triangles), "classifier_nodes": len(nodes),
              "reference": reference, "variants": {}, "baseline_reproduced": False,
              "completed": False}
    checkpoint(output, record)
    params = dict(bake.DEFAULT_PARAMS, cell_size=0.6, detail_sample_max_error=0.25)
    for name, overrides in variants[comparison]:
        variant_params = dict(params, **overrides)
        product = output / f"{name}.eqnm"
        command = [str(BAKER), str(eqtr), str(product), "--threads", "1"]
        for key, value in variant_params.items():
            command += ["--" + key.replace("_", "-"), str(value)]
        entry = {"status": "running", "command": command,
                 "requested_params": variant_params}
        record["variants"][name] = entry
        checkpoint(output, record)
        began = time.monotonic()
        try:
            completed = subprocess.run(command, stdin=subprocess.DEVNULL,
                                       capture_output=True, timeout=90, check=False)
        except subprocess.TimeoutExpired as error:
            (output / f"{name}.stdout").write_bytes(error.stdout or b"")
            (output / f"{name}.stderr").write_bytes(error.stderr or b"")
            entry.update(status="timeout", limit_seconds=90,
                         seconds=time.monotonic() - began,
                         partial_product_sha256=digest(product) if product.is_file() else None)
            checkpoint(output, record)
            break
        (output / f"{name}.stdout").write_bytes(completed.stdout)
        (output / f"{name}.stderr").write_bytes(completed.stderr)
        entry.update(seconds=time.monotonic() - began, returncode=completed.returncode)
        if completed.returncode:
            entry["status"] = "baker_failed"
            break
        try:
            meta, arrays = bake.read_eqnm(product)
            entry.update(eqnm_sha256=digest(product), baker_metadata=meta)
            mesh = NavMesh(bake.from_recast(arrays["poly_verts"]), arrays["poly_nv"],
                           arrays["poly_area"], arrays["link_a"], arrays["link_b"],
                           bake.from_recast(arrays["link_pts"]),
                           bake.from_recast(arrays["detail_tris"]), arrays["detail_poly"], {})
            entry.update(status="sampled", ground=sample_ground(mesh))
        except (OSError, ValueError, RuntimeError) as error:
            entry.update(status="sample_failed", reason=str(error))
            checkpoint(output, record)
            break
        if name == "baseline":
            differences = [abs(reference["center_z"] - entry["ground"]["center_z"])]
            for before, after in zip(reference["rings"], entry["ground"]["rings"]):
                differences.extend(abs(a - b) for a, b in zip(before["heights"], after["heights"]))
            record["baseline_maximum_height_difference"] = max(differences)
            record["baseline_reproduced"] = max(differences) <= 0.0001
            checkpoint(output, record)
            if not record["baseline_reproduced"]:
                break
        checkpoint(output, record)
    check_sources()
    if any(digest(path) != expected for path, expected in local_sources.items()):
        raise ValueError("project probe code changed during comparison")
    for name, entry in record["variants"].items():
        for stream in ("stdout", "stderr"):
            path = output / f"{name}.{stream}"
            if path.is_file():
                entry[stream + "_sha256"] = digest(path)
    record["completed"] = all(record["variants"].get(name, {}).get("status") == "sampled"
                              for name, _ in variants[comparison])
    report = output / "report.json"
    checkpoint(output, record)
    print(json.dumps({"report": str(report), "sha256": digest(report),
                      "baseline_reproduced": record["baseline_reproduced"],
                      "variants": {k: v["status"] for k, v in record["variants"].items()}}))
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--comparison", choices=("cell", "detail"), default="cell",
                        help="change only horizontal cell size or detail sample distance")
    args = parser.parse_args()
    output = args.output.expanduser()
    if (output.exists() or output.is_symlink() or
            output.parent.resolve() != (ROOT / "nav-candidates").resolve()):
        parser.error("output must be a new directory directly under the private nav-candidates store")
    os.umask(0o077)
    os.nice(15)
    try:
        run(output, args.comparison)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f"Offline bake probe refused: {error}\n")


if __name__ == "__main__":
    main()
