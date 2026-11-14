#!/usr/bin/env python3
"""Build the isolated owner chat-recovery preview; never modify an old preview."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from build_nov12_preview_0395 import build as build_0395
from build_nov12_preview import sha256

PROJECT = Path(__file__).resolve().parents[1]
PATCH = PROJECT / "patches/nov12-7e3cd28-chat-recovery-preview.patch"
EXPECTED = {
    "rotation_core.py": "9f05379c407f7c9042b38dc7f39c72c0b603bc24d6e754330746f805211a3113",
    "rotation_engine.py": "d6ec143920a6748364eb27fa6e279aaf45763b8345fe8e81d7c171648561927f",
    "eql_rotation.py": "baa9ba1400cd4bbe995b97ecb68d9d1757ab40bcf14d5475d1c03998c09fbff3",
    "uilayout.py": "d79ec2ae32a31fa642f4b64952996c28d7905efc15fce1d816fc671e552b733a",
    "eql_automation/hp_layout.py": "3866414c8e3dfff41744ff7ba39e4996ae1ac645e2712ecf79a1836dcca1481f",
    "eql_automation/owner_nov12_adapter.py": "26a62fa0d1d30966dd19ad9ab578d2b81d38d48181c2d01de98a5839defcf49a",
    "eql_automation/owner_nov12_recovery.py": "efdf13c8b63efc31154be0c889d7be85ea6f8736a340334a99c3486c9a1a5a34",
}


def build(source: Path, output: Path) -> None:
    if output.exists():
        raise ValueError("Refusing to replace an existing owner preview")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="eql-preview-0396-", dir=output.parent) as temp:
        work = Path(temp) / "snapshot"
        build_0395(source, work)
        shutil.copy2(PROJECT / "eql_automation/owner_nov12_recovery.py", work / "eql_automation/owner_nov12_recovery.py")
        subprocess.run(["patch", "--batch", "--forward", "-p1", "-i", str(PATCH)],
                       cwd=work, check=True, capture_output=True, text=True)
        for name, expected in EXPECTED.items():
            if sha256(work / name) != expected:
                raise ValueError(f"0.39.6 owner preview hash mismatch: {name}")
        shutil.copy2(PROJECT / "tools/owner_nov12_entry_0396.py", work / "owner_nov12_entry.py")
        (work / "owner_nov12_smoke.py").rename(work / "owner_nov12_smoke_base.py")
        shutil.copy2(PROJECT / "tools/owner_nov12_smoke_0396.py", work / "owner_nov12_smoke.py")
        info_path = work / "BUILD_INFO.json"
        info = json.loads(info_path.read_text())
        info.update(version="0.39.6", preview_hashes=EXPECTED,
                    patch_sha256=[*info["patch_sha256"], sha256(PATCH)],
                    change="F9 invalidates queued Prepare; explicit local chat recovery stays off; accurate assist controls")
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
