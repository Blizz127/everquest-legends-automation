#!/usr/bin/env python3
"""Build the isolated G0 watchdog candidate without replacing old previews."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import tempfile

from build_nov12_preview import sha256
from build_nov12_preview_0396 import build as build_0396
from owner_nov12_entry_0397 import EXPECTED


PROJECT = Path(__file__).resolve().parents[1]


def build(source: Path, output: Path) -> None:
    if output.exists():
        raise ValueError("Refusing to replace an existing owner preview")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="eql-preview-0397-", dir=output.parent) as temp:
        work = Path(temp) / "snapshot"
        build_0396(source, work)
        for name in ("owner_g0_watchdog.py", "uinput_watchdog.py"):
            shutil.copy2(PROJECT / "eql_automation" / name, work / "eql_automation" / name)
        for name, expected in EXPECTED.items():
            if sha256(work / name) != expected:
                raise ValueError(f"0.39.7 owner preview hash mismatch: {name}")
        shutil.copy2(PROJECT / "tools/owner_nov12_entry_0397.py", work / "owner_nov12_entry.py")
        (work / "owner_nov12_smoke.py").rename(work / "owner_nov12_smoke_recovery.py")
        shutil.copy2(PROJECT / "tools/owner_nov12_smoke_0397.py", work / "owner_nov12_smoke.py")
        info_path = work / "BUILD_INFO.json"
        info = json.loads(info_path.read_text())
        info.update(version="0.39.7", preview_hashes=EXPECTED,
                    change="Existing G0 forward pulse uses same-device independent release; no G2/F11",
                    real_watchdog_acceptance=False)
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
