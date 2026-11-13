#!/usr/bin/env python3
"""Summarize an owner-run November helper trace without printing character data.

This is read-only. A trace alone cannot prove an in-game cast, native melee
stop, movement stop, or level gain; those require game log/owner observation.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path


def _stamp(value: object) -> str | None:
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def summarize(path: Path) -> dict:
    digest = hashlib.sha256()
    counts: Counter[str] = Counter()
    gauges: dict[str, list[float]] = {"hp": [], "mana": []}
    missing: Counter[str] = Counter()
    first_time = last_time = None
    malformed = 0
    g0_outcomes: Counter[str] = Counter()
    keys: Counter[str] = Counter()
    with path.open("rb") as stream:
        for raw in stream:
            digest.update(raw)
            try:
                row = json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError):
                malformed += 1
                continue
            if not isinstance(row, dict):
                malformed += 1
                continue
            event = row.get("event")
            counts[str(event)] += 1
            when = row.get("time")
            if isinstance(when, (int, float)) and math.isfinite(when):
                first_time = when if first_time is None else min(first_time, when)
                last_time = when if last_time is None else max(last_time, when)
            if event == "gauges":
                for channel in gauges:
                    value = row.get(channel)
                    if isinstance(value, (int, float)) and math.isfinite(value) and 0 <= value <= 1:
                        gauges[channel].append(float(value))
                    else:
                        missing[channel] += 1
            elif event == "ap_stop_check_result":
                g0_outcomes[str(row.get("outcome", "unknown"))] += 1
            elif event == "key" and row.get("value") == 1:
                name = {65: "F7", 66: "F8", 67: "F9", 68: "F10", 87: "F11"}.get(row.get("code"))
                if name:
                    keys[name] += 1
    return {
        "scope": "helper trace only; game log and owner observations are separate",
        "trace_sha256": digest.hexdigest(),
        "first_utc": _stamp(first_time),
        "last_utc": _stamp(last_time),
        "malformed_lines": malformed,
        "events": dict(sorted(counts.items())),
        "hotkey_presses": dict(sorted(keys.items())),
        "gauges": {
            channel: {"known": len(values), "unknown": missing[channel],
                      "min": min(values) if values else None,
                      "max": max(values) if values else None}
            for channel, values in gauges.items()
        },
        "g0_trace_outcomes": dict(sorted(g0_outcomes.items())),
        "owner_visual_stop_confirmed": None,
        "native_melee_stop_confirmed": None,
        "level_50_run_confirmed": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(args.trace), indent=2))


if __name__ == "__main__":
    main()
