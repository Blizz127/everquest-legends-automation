#!/usr/bin/env python3
"""No-device smoke for the staged owner assist preview."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from owner_nov12_entry import verify_snapshot
from rotation_core import bar_fraction


def main() -> None:
    verify_snapshot(Path(__file__).resolve().parent)
    image = Image.new("RGB", (338, 14), (20, 20, 20))
    image.paste((150, 0, 0), (0, 3, 203, 11))
    measured = bar_fraction(image, "red")
    if measured is None or abs(measured - 203 / 338) > 0.01:
        raise AssertionError(f"Thin HP band was not measured: {measured}")
    accent = Image.new("RGB", (338, 14), (20, 20, 20))
    accent.paste((150, 0, 0), (0, 3, 12, 6))
    if bar_fraction(accent, "red") is not None:
        raise AssertionError("Small red accent was mistaken for critical HP")
    critical = Image.new("RGB", (338, 14), (20, 20, 20))
    critical.paste((150, 0, 0), (0, 3, 20, 11))
    if bar_fraction(critical, "red") is not None:
        raise AssertionError("Untrusted sub-ten-percent HP was accepted")
    from rotation_engine import Engine, WindowGate
    gate = WindowGate.__new__(WindowGate)
    window = SimpleNamespace(get_geometry=lambda: SimpleNamespace(width=2560, height=1600))
    gate.focused_window = lambda: window
    gate.windows = lambda: [window]
    hp, _ = gate.read_gauges({"box": [1963, 661, 2301, 712],
                              "window_size": [2560, 1600]}, None)
    if hp is not None or gate.gauge_reason != ("hp_recalibrate_inner_bar", "uncalibrated"):
        raise AssertionError(f"Broad saved HP crop was not rejected: {hp}, {gate.gauge_reason}")
    from eql_rotation import gauge_label
    if gauge_label("HP", hp, gate.gauge_reason[0]) != "HP · recalibrate inner red bar (5–24px high)":
        raise AssertionError("Broad HP crop did not produce a useful owner instruction")
    if gauge_label("HP", None, "size_mismatch:1280x800") != "HP · game window size changed; recalibrate":
        raise AssertionError("A changed window size did not remain an unknown reading")
    states = []
    from rotation_engine import Engine
    payload_engine = Engine.__new__(Engine)
    payload_engine.status = "offline smoke"
    payload_engine.active = False
    payload_engine.preparing = False
    payload_engine.settings = SimpleNamespace(level=7, stance_keys_verified=False)
    payload_engine.profile = {}
    payload_engine.prepared = False
    payload_engine.known = None
    payload_engine.hp = None
    payload_engine.mana = None
    payload_engine.last_gauge_reason = gate.gauge_reason
    payload_engine.last_payload = None
    payload_engine.autopilot_payload = lambda: {}
    payload_engine.notify = states.append
    payload_engine.emit()
    if len(states) != 1 or states[0]["hp"] is not None or states[0]["gauge_reason"] != gate.gauge_reason:
        raise AssertionError("HP rejection reason was not forwarded to the UI as unknown")
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
    print("PASS: pinned source, HP reason in UI payload, unknown HP, no melee command, F11 disabled; no game input")


if __name__ == "__main__":
    main()
