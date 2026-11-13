#!/usr/bin/env python3
"""Inspect the November helper's proposed camp ring on copied meshes only.

Height changes and copied graph connectivity are diagnostics. No spot from
this command is accepted for camp movement, pulling or F11.
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


DATA_ROOT = Path.home() / ".local/share/eql-automation"
HELPER_HASHES = {
    "eqnav/__init__.py": "717e253506fa07148160efd0679373ae0d430611d9146b73bc9feca02f5258b0",
    "eqnav/mesh.py": "89682ac2f6ee6ad4fc4e4530d946e4d7d883d860573a958d45f7cd7a074fef85",
    "eqnav/world.py": "6441467623a49950af2549496ddb27c3c8c5e3889829d833293a604d9209cfb2",
    "rotation_core.py": "9f05379c407f7c9042b38dc7f39c72c0b603bc24d6e754330746f805211a3113",
    "leveling_guide.py": "9babe5213d4903f5c014f59bf38b1fa3c3167e22ecb6ff4af61e624cf342ca4c",
    "leveling_guide.json": "bfe936da1aec38b37a683af51f0ee4189cd86bcb4a1680deee613c4dfeba77b9",
}
ZONE_HASHES = {
    "gfaydark": (
        "5f8e16c5bcd2221ba273f681750ca480349780524d23609c059a3e817df6abd9",
        "ac9591eb63e1394363ad37d7d0ca6609a1ebe11fd8786bedb5b165b833e2eb82",
    ),
    "butcher": (
        "4e450cdbca7ab6cc44a7973eca11929d7b920db49f6c51ad00a6337b5ee58bde",
        "64f3b3d8673a61424268172b3b9c6989921c77e49d5b0f4d55fa034f2d8ef792",
    ),
}


def digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def inspect(camp_id: str, *, helper_root: Path, mesh_store: Path,
            output: Path, diagnostic_height_change: float = 6.0,
            candidate_leash: float | None = None,
            count: int = 6) -> dict:
    helper_root = helper_root.expanduser().resolve()
    mesh_store = mesh_store.expanduser().resolve()
    output = output.expanduser().resolve()
    if (not helper_root.is_relative_to((DATA_ROOT / "owner-assist").resolve()) or
            not mesh_store.is_relative_to((DATA_ROOT / "navmesh").resolve()) or
            not output.is_relative_to((DATA_ROOT / "nav-candidates").resolve()) or
            output.suffix != ".json" or output.exists()):
        raise ValueError("helper, copied mesh or new output is outside the private store")
    if (not isinstance(camp_id, str) or len(camp_id) > 64 or
            not camp_id.replace("-", "").isalnum() or
            not math.isfinite(diagnostic_height_change) or
            not 0 < diagnostic_height_change <= 25 or
            not isinstance(count, int) or isinstance(count, bool) or
            not 1 <= count <= 24):
        raise ValueError("invalid camp ID or diagnostic height limit")
    for name, expected in HELPER_HASHES.items():
        path = helper_root / name
        if not path.is_file() or path.is_symlink() or digest(path) != expected:
            raise ValueError(f"reviewed owner-helper source changed: {name}")
    sys.path.insert(0, str(helper_root))
    import eqnav.mesh as mesh_module
    import eqnav.world as world_module
    import leveling_guide as guide_module
    import rotation_core as core_module
    from eqnav.world import MeshStore, World
    from leveling_guide import default_guide
    for module, relative in ((mesh_module, "eqnav/mesh.py"),
                             (world_module, "eqnav/world.py"),
                             (guide_module, "leveling_guide.py"),
                             (core_module, "rotation_core.py")):
        if Path(module.__file__).resolve() != (helper_root / relative).resolve():
            raise ValueError("imported helper module differs from pinned source")

    guide = default_guide()
    camp = guide.camp(camp_id)
    if camp is None or camp.loc is None:
        raise ValueError("camp ID has no copied guide marker")
    expected_hashes = ZONE_HASHES.get(camp.zone)
    if expected_hashes is None:
        raise ValueError("this copied camp zone has no pinned mesh provenance")
    leash = camp.leash if candidate_leash is None else candidate_leash
    if (not isinstance(leash, (int, float)) or isinstance(leash, bool) or
            not math.isfinite(leash) or not 12 <= leash <= camp.leash):
        raise ValueError("candidate leash must be 12 or more and no greater than the guide leash")
    mesh_path = mesh_store / f"{camp.zone}.npz"
    manifest_path = mesh_store / f"{camp.zone}.json"
    if (not mesh_path.is_file() or not manifest_path.is_file() or
            mesh_path.is_symlink() or manifest_path.is_symlink() or
            not mesh_path.resolve().is_relative_to(mesh_store) or
            not manifest_path.resolve().is_relative_to(mesh_store)):
        raise ValueError("copied zone mesh or manifest is missing")
    mesh_hash, manifest_hash = digest(mesh_path), digest(manifest_path)
    if (mesh_hash, manifest_hash) != expected_hashes:
        raise ValueError("copied zone mesh provenance changed")
    world = World(MeshStore(mesh_store))
    anchor = world.snap(camp.zone, camp.loc)
    if anchor is None:
        raise ValueError("copied guide marker did not snap to a mesh anchor")
    spots = world.roam_points(camp.zone, anchor, leash, count=count)
    if any(len(point) != 3 or not all(math.isfinite(float(v)) for v in point)
           for point in spots):
        raise ValueError("copied helper produced an invalid ring point")
    if (digest(mesh_path) != mesh_hash or digest(manifest_path) != manifest_hash or
            any(digest(helper_root / name) != expected
                for name, expected in HELPER_HASHES.items())):
        raise ValueError("copied mesh or helper changed during ring inspection")
    rows = []
    for index, point in enumerate(spots):
        height_change = float(point[2] - anchor[2])
        rows.append({
            "returned_index": index,
            "location_yxz": [float(value) for value in point],
            "horizontal_distance": math.hypot(point[0] - anchor[0],
                                              point[1] - anchor[1]),
            "height_change": height_change,
            "large_height_change_needs_review": abs(height_change) > diagnostic_height_change,
            "strip_bsp_dynamic_and_client_movement_verified": False,
        })
    record = {
        "format": "eql-copied-roam-ring-v1",
        "camp_id": camp.id,
        "zone": camp.zone,
        "guide_marker_yxz": list(camp.loc),
        "copied_anchor_yxz": [float(value) for value in anchor],
        "guide_leash": camp.leash,
        "candidate_leash": leash,
        "requested_count": count,
        "diagnostic_height_change": diagnostic_height_change,
        "helper_source_sha256": HELPER_HASHES,
        "mesh_sha256": mesh_hash,
        "manifest_sha256": manifest_hash,
        "roam_points": rows,
        "offline_only": True,
        "route_accepted": False,
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
    try:
        os.link(temporary, output)  # Exclusive creation preserves another run's evidence.
    finally:
        temporary.unlink(missing_ok=True)
    return {"artifact": str(output), "sha256": digest(output),
            "camp_id": camp.id, "points": len(rows),
            "large_height_changes": sum(row["large_height_change_needs_review"]
                                        for row in rows),
            "offline_only": True, "route_accepted": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camp-id", required=True)
    parser.add_argument("--helper-root", type=Path, default=DATA_ROOT / "owner-assist/0.39.4")
    parser.add_argument("--mesh-store", type=Path,
                        default=DATA_ROOT / "navmesh/nov12-7e3cd28-store")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--diagnostic-height-change", type=float, default=6.0)
    parser.add_argument("--candidate-leash", type=float,
                        help="offline ring radius control, at most the guide leash")
    parser.add_argument("--count", type=int, default=6)
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.camp_id, helper_root=args.helper_root,
                                 mesh_store=args.mesh_store, output=args.output,
                                 diagnostic_height_change=args.diagnostic_height_change,
                                 candidate_leash=args.candidate_leash,
                                 count=args.count)))
    except (OSError, ValueError, TypeError, ImportError) as error:
        parser.exit(1, f"Copied ring inspection refused: {error}\n")


if __name__ == "__main__":
    main()
