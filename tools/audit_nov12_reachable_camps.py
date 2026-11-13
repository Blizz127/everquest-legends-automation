#!/usr/bin/env python3
"""Offline camp progression audit against the November helper's copied mesh.

Run with PYTHONPATH pointing to an isolated November source snapshot patched
with ``nov12-7e3cd28-reachable-camps.patch``. This reads mesh and guide data;
it never launches EverQuest, moves a character or accepts a live route.
"""
from __future__ import annotations

import argparse
import json

from eqnav.world import MeshStore, World
from leveling_guide import default_guide


def audit(start_level: int, final_level: int, zone: str,
          loc: tuple[float, float, float], root: str) -> list[dict]:
    guide = default_guide()
    world = World(MeshStore(root))
    current = None
    results = []
    for level in range(start_level, final_level + 1):
        def eligible(camp):
            return (camp.loc is not None and
                    world.camp_reachable(camp.zone, camp.loc,
                                         from_zone=zone, from_loc=loc))

        camp, reason = guide.select_camp(
            level, zone=zone, current=current, indoor=False, eligible=eligible)
        if camp is None:
            results.append({"level": level, "camp": None, "reason": reason})
            break
        snapped = world.snap(camp.zone, camp.loc)
        if snapped is None:
            results.append({"level": level, "camp": None,
                            "reason": f"{camp.name}: no snapped camp point"})
            break
        results.append({"level": level, "camp": camp.id, "zone": camp.zone,
                        "reason": reason})
        current, zone, loc = camp, camp.zone, snapped
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh-root", required=True)
    parser.add_argument("--zone", required=True)
    parser.add_argument("--loc", required=True, nargs=3, type=float,
                        metavar=("Y", "X", "Z"))
    parser.add_argument("--start-level", required=True, type=int)
    parser.add_argument("--final-level", default=50, type=int)
    args = parser.parse_args()
    if not 1 <= args.start_level <= args.final_level <= 50:
        parser.error("levels must be ascending within 1 to 50")
    print(json.dumps({"simulation_only": True,
                      "real_client_route_verified": False,
                      "rows": audit(args.start_level, args.final_level, args.zone,
                                    tuple(args.loc), args.mesh_root)}, indent=2))


if __name__ == "__main__":
    main()
