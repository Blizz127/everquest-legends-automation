"""Owner-run, read-only watcher for a manual zone crossing.

Run this before walking across the zone line, then use /location immediately
after entering and stopping. It only reads the client's log and zone names.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time

from .destination_log import DestinationLogReader


def _payload(arrival, *, zone_names_sha256: str) -> dict:
    data = asdict(arrival)
    for key in ("loading_log_time", "entered_log_time", "location_log_time",
                "preloading_log_time"):
        if data[key] is not None:
            data[key] = data[key].isoformat()
    data.update({
        "format": 1,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "zone_names_sha256": zone_names_sha256,
        "loading_to_entry_seconds": (arrival.entered_log_time -
                                     arrival.loading_log_time).total_seconds(),
        "entry_to_location_seconds": (arrival.location_log_time -
                                      arrival.entered_log_time).total_seconds(),
        "raw_coordinates_aligned_to_wld": False,
    })
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--destination", default="Clan Crushbone")
    parser.add_argument("--game-root", type=Path, default=(
        Path.home() / "Games/everquest-legends/drive_c/users/Public/"
        "Daybreak Game Company/Installed Games/EverQuest Legends"))
    parser.add_argument("--seconds", type=float, default=900.0)
    parser.add_argument("--poll-seconds", type=float, default=0.2)
    args = parser.parse_args(argv)
    if (re.fullmatch(r"[A-Za-z0-9_]{1,48}", args.character) is None or
            re.fullmatch(r"[A-Za-z0-9_]{1,48}", args.server) is None or
            not 0 < args.seconds <= 3600 or
            not 0.05 <= args.poll_seconds <= 2.0):
        parser.error("Invalid watcher identity or bounded duration")
    game_root = args.game_root.expanduser()
    log_path = game_root / "Logs" / f"eqlog_{args.character}_{args.server}.txt"
    zone_names_path = game_root / "Resources" / "ZoneNames.txt"
    if not log_path.is_file() or not zone_names_path.is_file():
        parser.error("Expected client log or Resources/ZoneNames.txt is missing")
    zone_names_sha256 = hashlib.sha256(zone_names_path.read_bytes()).hexdigest()
    reader = DestinationLogReader(log_path, zone_names_path,
                                  expected_character=args.character,
                                  expected_server=args.server,
                                  destination=args.destination)
    output_dir = Path.home() / ".local/share/eql-automation/owner-traces"
    if output_dir.resolve().is_relative_to(game_root.resolve()):
        parser.error("Observation output cannot be inside the game install")
    output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    print(f"Watching new {args.destination} log lines. Cross manually and use /location within 30 seconds.",
          flush=True)
    deadline = time.monotonic() + args.seconds
    try:
        while time.monotonic() < deadline:
            arrivals = reader.poll()
            if arrivals:
                if len(arrivals) != 1:
                    print("Ambiguous batched arrivals; waiting for one fresh crossing.", flush=True)
                    continue
                arrival = arrivals[0]
                if abs((datetime.now() - arrival.location_log_time).total_seconds()) > 45.0:
                    print("Appended location has a stale client timestamp; waiting for a fresh crossing.",
                          flush=True)
                    continue
                if hashlib.sha256(zone_names_path.read_bytes()).hexdigest() != zone_names_sha256:
                    parser.error("Client zone-name data changed during observation")
                payload = _payload(arrival, zone_names_sha256=zone_names_sha256)
                suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                output = output_dir / f"destination-{args.character}-{suffix}.json"
                fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as target:
                    json.dump(payload, target, indent=2, sort_keys=True)
                    target.write("\n")
                print(json.dumps({"saved": str(output), "zone": arrival.zone_display_name,
                                  "raw_location": arrival.raw_location,
                                  "spawn_coordinate_verified": False,
                                  "route_accepted": False}, sort_keys=True), flush=True)
                return 0
            time.sleep(args.poll_seconds)
    except KeyboardInterrupt:
        print("Stopped; no new destination observation was written.", flush=True)
        return 130
    print("No timely destination /location was observed; no evidence file was written.",
          flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
