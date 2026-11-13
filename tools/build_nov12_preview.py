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
    "rotation_core.py": "2dc77712f070234a0beddd3b3472a6e47276d345009c23890af0cb08f041a002",
    "rotation_engine.py": BASE_HASHES["rotation_engine.py"],
    "eql_rotation.py": "244e707b2b8a1a94ca09b93c5bc7a2db7492b17c05e5f6401003a83f82fd83c6",
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
        patch = PROJECT / "patches/nov12-7e3cd28-owner-assist.patch"
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
            "version": "0.39.1",
            "base_revision": "7e3cd28d24770299314fd9775cef7b460a94ee3d",
            "base_hashes": BASE_HASHES,
            "preview_hashes": PREVIEW_HASHES,
            "patch_sha256": sha256(patch),
            "mode": "owner-run supervised attack-free assist; F11/F12 disabled",
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
