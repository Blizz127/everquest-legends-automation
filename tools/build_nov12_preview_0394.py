#!/usr/bin/env python3
"""Build isolated owner preview 0.39.4 from the pinned November source.

The original 0.39.3 builder remains reproducible. This builder adds only a
diagnostic UI patch after the pinned 0.39.3 source and patch checks pass.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from build_nov12_preview import build as build_0393, sha256


PROJECT = Path(__file__).resolve().parents[1]
PATCH = PROJECT / "patches/nov12-7e3cd28-hp-reason-preview.patch"
EXPECTED = {
    "rotation_core.py": "9f05379c407f7c9042b38dc7f39c72c0b603bc24d6e754330746f805211a3113",
    "rotation_engine.py": "d6ec143920a6748364eb27fa6e279aaf45763b8345fe8e81d7c171648561927f",
    "eql_rotation.py": "7e4fbfc9af11e5090cac9a43f6538551cfc8b359b1140e8ea223075f7749948b",
}


def build(source: Path, output: Path) -> None:
    if output.exists():
        raise ValueError("Refusing to replace an existing owner preview")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="eql-preview-0394-", dir=output.parent) as temp:
        work = Path(temp) / "snapshot"
        build_0393(source, work)
        subprocess.run(["patch", "--batch", "--forward", "-p1", "-i", str(PATCH)],
                       cwd=work, check=True, capture_output=True, text=True)
        for name, expected in EXPECTED.items():
            if sha256(work / name) != expected:
                raise ValueError(f"0.39.4 owner preview hash mismatch: {name}")
        shutil.copy2(PROJECT / "tools/owner_nov12_entry_0394.py", work / "owner_nov12_entry.py")
        shutil.copy2(PROJECT / "tools/owner_nov12_smoke_0394.py", work / "owner_nov12_smoke.py")
        info_path = work / "BUILD_INFO.json"
        info = json.loads(info_path.read_text())
        info.update({"version": "0.39.4", "preview_hashes": EXPECTED,
                     "patch_sha256": [*info["patch_sha256"], sha256(PATCH)],
                     "change": "Show HP gauge rejection reason in owner UI; no input policy change"})
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
