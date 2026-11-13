#!/usr/bin/env python3
"""Build the pinned owner-run preview from a read-only November source copy.

The output contains Python source and an owner-run launcher, never client data
or character files. It refuses changed base files and an existing destination.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


PROJECT = Path(__file__).resolve().parents[1]
BASE_HASHES = {
    "rotation_core.py": "5632dbef84ae93b5ec3ec70d516cbc53c4b26593d78d99b55e1f7856bbdbd83a",
    "rotation_engine.py": "1e1e6e3e021619471f9d954e86c9af81363315a66a7b8771b766acea53ea4731",
    "eql_rotation.py": "c4fd21f59d0e6cfa2321f0c64826d8402d566a2ac0bde14b4614db4d5a49ac8e",
}
PREVIEW_HASHES = {
    "rotation_core.py": "9f05379c407f7c9042b38dc7f39c72c0b603bc24d6e754330746f805211a3113",
    "rotation_engine.py": "8ab73f40b9462f0d6a932614b524f2f1e687f41ee09823e8926981377648b487",
    "eql_rotation.py": "cd46cca8cd1c91b77486282d3a5f17c759802f0c24c56f48e36beb8dbfe864e9",
}
RUNTIME_FILES = (
    "rotation_core.py", "rotation_engine.py", "eql_rotation.py",
    "autopilot.py", "navigation.py", "leveling_guide.py",
    "leveling_guide.json", "inventory.py", "pointer.py", "uilayout.py",
    "ap_core.py", "ap_quests.py", "ap_vendor.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(source: Path, output: Path) -> None:
    if output.exists():
        raise ValueError("Refusing to replace an existing owner preview")
    for name, expected in BASE_HASHES.items():
        if sha256(source / name) != expected:
            raise ValueError(f"November source mismatch: {name}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="eql-preview-build-", dir=output.parent) as temp:
        work = Path(temp)
        for name in RUNTIME_FILES:
            shutil.copy2(source / name, work / name)
        (work / "eqnav").mkdir()
        for path in (source / "eqnav").glob("*.py"):
            shutil.copy2(path, work / "eqnav" / path.name)
        if not (work / "eqnav" / "__init__.py").exists():
            raise ValueError("November eqnav Python package is incomplete")
        patches = (
            PROJECT / "patches/nov12-7e3cd28-owner-assist.patch",
            PROJECT / "patches/nov12-7e3cd28-tight-hp-preview.patch",
        )
        for patch in patches:
            subprocess.run(["patch", "--batch", "--forward", "-p1", "-i", str(patch)],
                           cwd=work, check=True, capture_output=True, text=True)
        for name, expected in PREVIEW_HASHES.items():
            if sha256(work / name) != expected:
                raise ValueError(f"Patched owner preview mismatch: {name}")
        package = work / "eql_automation"
        package.mkdir()
        for name in ("__init__.py", "owner_nov12_adapter.py"):
            shutil.copy2(PROJECT / "eql_automation" / name, package / name)
        shutil.copy2(PROJECT / "tools/owner_nov12_entry.py", work / "owner_nov12_entry.py")
        shutil.copy2(PROJECT / "tools/owner_nov12_smoke.py", work / "owner_nov12_smoke.py")
        shutil.copy2(PROJECT / "tools/owner_nov12_launch.sh", work / "launch.sh")
        (work / "launch.sh").chmod(0o755)
        (work / "BUILD_INFO.json").write_text(json.dumps({
            "version": "0.39.3",
            "base_revision": "7e3cd28d24770299314fd9775cef7b460a94ee3d",
            "base_hashes": BASE_HASHES,
            "preview_hashes": PREVIEW_HASHES,
            "patch_sha256": [sha256(patch) for patch in patches],
            "mode": "owner-run attack-free assist with narrow HP calibration; G0 stop check in measurement mode; F11 travel/F12 disabled",
            "real_client_acceptance": False,
        }, indent=2) + "\n")
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
