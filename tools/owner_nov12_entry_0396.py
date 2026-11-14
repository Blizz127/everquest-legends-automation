#!/usr/bin/env python3
"""Pinned, owner-run entry for the isolated November assist preview.

Copy this file beside the three pinned November helper modules and the
``eql_automation.owner_nov12_adapter`` package. The owner launches it; this
entry never starts EverQuest or logs in on its own.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys


EXPECTED = {
    "rotation_core.py": "9f05379c407f7c9042b38dc7f39c72c0b603bc24d6e754330746f805211a3113",
    "rotation_engine.py": "d6ec143920a6748364eb27fa6e279aaf45763b8345fe8e81d7c171648561927f",
    "eql_rotation.py": "baa9ba1400cd4bbe995b97ecb68d9d1757ab40bcf14d5475d1c03998c09fbff3",
    "uilayout.py": "d79ec2ae32a31fa642f4b64952996c28d7905efc15fce1d816fc671e552b733a",
    "eql_automation/hp_layout.py": "3866414c8e3dfff41744ff7ba39e4996ae1ac645e2712ecf79a1836dcca1481f",
    "eql_automation/owner_nov12_adapter.py": "26a62fa0d1d30966dd19ad9ab578d2b81d38d48181c2d01de98a5839defcf49a",
    "eql_automation/owner_nov12_recovery.py": "efdf13c8b63efc31154be0c889d7be85ea6f8736a340334a99c3486c9a1a5a34",
}


def verify_snapshot(directory: Path) -> None:
    for name, expected in EXPECTED.items():
        path = directory / name
        try:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            raise RuntimeError(f"Owner preview missing {name}: {exc}") from exc
        if actual != expected:
            raise RuntimeError(f"Owner preview source mismatch: {name}; refusing input")


def main() -> int:
    directory = Path(__file__).resolve().parent
    try:
        verify_snapshot(directory)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 2
    # The isolated snapshot is on sys.path when this file is invoked directly.
    import rotation_engine
    from eql_automation.owner_nov12_recovery import make_owner_nov12_engine
    rotation_engine.Engine = make_owner_nov12_engine(rotation_engine.Engine)
    from eql_rotation import main as helper_main
    helper_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
