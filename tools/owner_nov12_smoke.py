#!/usr/bin/env python3
"""No-device smoke for the staged owner assist preview."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from owner_nov12_entry import verify_snapshot
from rotation_core import bar_fraction


def main() -> None:
    verify_snapshot(Path(__file__).resolve().parent)
    image = Image.new("RGB", (338, 51), (20, 20, 20))
    image.paste((150, 0, 0), (0, 9, 203, 15))
    image.paste((0, 0, 150), (0, 45, 200, 51))
    measured = bar_fraction(image, "red")
    if measured is None or abs(measured - 203 / 338) > 0.01:
        raise AssertionError(f"Thin HP band was not measured: {measured}")
    from rotation_engine import Engine
    from eql_automation.owner_nov12_adapter import make_owner_nov12_engine
    adapted = make_owner_nov12_engine(Engine)
    engine = adapted.__new__(adapted)  # No devices or game session are opened.
    notices = []
    engine.emit = notices.append
    assert engine.send("/attack on") is None
    assert engine.send("/attack off") is None
    engine.handle_job("autopilot_start", 1)
    if not notices or "disabled" not in notices[-1]:
        raise AssertionError("F11 did not fail closed")
    print("PASS: pinned source, thin HP band, no melee command, F11 disabled; no game input")


if __name__ == "__main__":
    main()
