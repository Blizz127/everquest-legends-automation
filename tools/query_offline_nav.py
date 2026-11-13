#!/usr/bin/env python3
"""Run a local Detour query and bind its JSON to one approved nav artifact.

No client or server input. The zone is a local asset-name check, not proof
that the private server uses the same geometry or that movement will work.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from math import isfinite
import os
from pathlib import Path
import subprocess
from tempfile import NamedTemporaryFile


ROOT = Path.home() / ".local/share/eql-automation"


def digest(path: Path) -> str:
    result = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zone", choices=("butcher", "crushbone", "gfaydark",
                                         "kaladima", "kaladimb"))
    parser.add_argument("nav", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("start_x", type=float)
    parser.add_argument("start_y", type=float)
    parser.add_argument("start_z", type=float)
    parser.add_argument("end_x", type=float)
    parser.add_argument("end_y", type=float)
    parser.add_argument("end_z", type=float)
    args = parser.parse_args()
    nav = args.nav.resolve()
    output = args.output.resolve()
    candidate_root = (ROOT / "nav-candidates").resolve()
    if (not nav.is_relative_to(candidate_root) or
            not output.is_relative_to(candidate_root) or
            not nav.name.startswith(args.zone + "-") or
            nav.suffix != ".nav" or output.suffix != ".json"):
        parser.error("Nav and query JSON must be zone-matched files in the approved EQL store")
    if not nav.is_file() or not 0 < nav.stat().st_size <= 100 * 1024 * 1024:
        parser.error("Provisional nav data is missing or too large")
    coordinates = (args.start_x, args.start_y, args.start_z,
                   args.end_x, args.end_y, args.end_z)
    if not all(isfinite(value) for value in coordinates):
        parser.error("Query coordinates must be finite WLD XYZ")
    executable = ROOT / "toolchains/eql-query-local"
    if not executable.is_file():
        parser.error("Build the pinned local Detour query tool first")
    nav_sha_before = digest(nav)
    command = [str(executable), str(nav), *(str(value) for value in coordinates)]
    query = json.loads(subprocess.run(command, check=True, capture_output=True,
                                      text=True).stdout)
    if digest(nav) != nav_sha_before:
        parser.error("Provisional nav data changed during the query")
    if (query.get("real_client_accepted") is not False or
            not isinstance(query.get("straight_path_wld_xyz"), list)):
        parser.error("Local query tool did not return provisional straight points")
    query.update({"format": "eql-offline-nav-query-v1", "zone": args.zone,
                  "nav_path": str(nav), "nav_sha256": nav_sha_before,
                  "query_tool_sha256": digest(executable)})
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with NamedTemporaryFile("w", encoding="utf-8", dir=output.parent,
                            prefix=output.name + ".", suffix=".tmp",
                            delete=False) as stream:
        os.fchmod(stream.fileno(), 0o600)
        json.dump(query, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
        temporary = Path(stream.name)
    temporary.replace(output)
    print(json.dumps({"query_path": str(output), "query_sha256": digest(output),
                      "nav_sha256": query["nav_sha256"],
                      "offline_path_complete": query["offline_path_complete"],
                      "real_client_accepted": False}, indent=2))


if __name__ == "__main__":
    main()
