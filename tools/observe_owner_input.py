#!/usr/bin/env python3
"""Brief read-only device check: counts only, no keys, grabs or game input."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import time

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from eql_automation.owner_input_observer import OwnerInputObserver


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=3, choices=range(1, 21))
    args = parser.parse_args()
    root = Path.home() / ".local/share/eql-automation/owner-input-observations"
    if root.resolve().is_relative_to((Path.home() / "Games/everquest-legends").resolve()):
        parser.error("observation store must remain outside the protected game prefix")
    os.umask(0o077)
    sources = [Path(__file__), PROJECT / "eql_automation/owner_input_observer.py",
               PROJECT / "eql_automation/input_contacts.py"]
    pins = {str(p): sha256(p.read_bytes()).hexdigest() for p in sources}
    try:
        observer = OwnerInputObserver()
    except (ImportError, OSError) as error:
        parser.exit(1, f"Read-only input observer unavailable: {error}\n")
    observations, profiles = [], {}
    try:
        for index in range(args.samples):
            observation = observer.sample()
            observations.append(asdict(observation))
            profiles = dict(Counter(d.absolute_profile for d in observer.devices.values()))
            if index + 1 < args.samples:
                time.sleep(0.05)
    finally:
        observer.close()
    if pins != {str(p): sha256(p.read_bytes()).hexdigest() for p in sources}:
        parser.exit(1, "Observer source changed during collection\n")
    record = {"format": "eql-owner-input-observation-v1", "read_only": True,
              "game_input_sent": False, "movement_authorized": False,
              "raw_key_codes_recorded": False, "completed": True,
              "observed_at_utc": datetime.now(timezone.utc).isoformat(),
              "source_sha256": pins, "device_profiles": profiles,
              "observations": observations}
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = root / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                   + f"-{time.time_ns()}.json")
    with path.open("x") as target:
        json.dump(record, target, indent=2, sort_keys=True)
        target.write("\n")
    print(json.dumps({"artifact": str(path), "sha256": sha256(path.read_bytes()).hexdigest(),
                      "profiles": profiles,
                      "coverage_complete_samples": sum(o["coverage_complete"] for o in observations),
                      "reasons": [o["reason"] for o in observations],
                      "game_input_sent": False, "movement_authorized": False}))


if __name__ == "__main__":
    main()
