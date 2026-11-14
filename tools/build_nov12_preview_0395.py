#!/usr/bin/env python3
"""Build the isolated owner HP-layout preview; never modify an old preview."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from build_nov12_preview_0394 import build as build_0394
from build_nov12_preview import sha256

PROJECT = Path(__file__).resolve().parents[1]
PATCH = PROJECT / "patches/nov12-7e3cd28-hp-layout-preview.patch"
EXPECTED = {
    "rotation_core.py": "9f05379c407f7c9042b38dc7f39c72c0b603bc24d6e754330746f805211a3113",
    "rotation_engine.py": "d6ec143920a6748364eb27fa6e279aaf45763b8345fe8e81d7c171648561927f",
    "eql_rotation.py": "cd59576a50ba353c6f47f03f04ebf7b92c4407785e7fdbd3a50e13df4a35ea17",
    "uilayout.py": "d79ec2ae32a31fa642f4b64952996c28d7905efc15fce1d816fc671e552b733a",
    "eql_automation/hp_layout.py": "3866414c8e3dfff41744ff7ba39e4996ae1ac645e2712ecf79a1836dcca1481f",
}


def build(source: Path, output: Path) -> None:
    if output.exists():
        raise ValueError("Refusing to replace an existing owner preview")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="eql-preview-0395-", dir=output.parent) as temp:
        work = Path(temp) / "snapshot"
        build_0394(source, work)
        shutil.copy2(PROJECT / "eql_automation/hp_layout.py", work / "eql_automation/hp_layout.py")
        subprocess.run(["patch", "--batch", "--forward", "-p1", "-i", str(PATCH)],
                       cwd=work, check=True, capture_output=True, text=True)
        for name, expected in EXPECTED.items():
            if sha256(work / name) != expected:
                raise ValueError(f"0.39.5 owner preview hash mismatch: {name}")
        shutil.copy2(PROJECT / "tools/owner_nov12_entry_0395.py", work / "owner_nov12_entry.py")
        # The existing no-input HP/rotation smoke remains applicable; the
        # new calibration-dialog smoke is exposed by the explicit GUI flag.
        info_path = work / "BUILD_INFO.json"
        info = json.loads(info_path.read_text())
        info.update(version="0.39.5", preview_hashes=EXPECTED,
                    patch_sha256=[*info["patch_sha256"], sha256(PATCH)],
                    change="Propose HP crop from saved client UI; explicit owner Save; no input policy change")
        info_path.write_text(json.dumps(info, indent=2) + "\n")
        work.rename(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    build(args.source, args.output)
    print(args.output)


if __name__ == "__main__":
    main()
