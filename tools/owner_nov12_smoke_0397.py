#!/usr/bin/env python3
"""Smoke actual owner intent dispatch with a pipe replacing the input device."""
import os
import struct
from types import SimpleNamespace

from owner_nov12_smoke_recovery import main as recovery_smoke


def main():
    recovery_smoke()
    from rotation_core import Settings
    from rotation_engine import Engine
    from autopilot import Hold
    from eql_automation.owner_g0_watchdog import make_owner_nov12_engine

    engine = make_owner_nov12_engine(Engine)(Settings(), lambda _: None, lambda *_: None,
                                            measurement_only=True)
    assert engine.sender is None and not engine.selector.get_map()
    engine.trace_path = None
    engine.pump = lambda: None
    engine.autopilot = SimpleNamespace(mode="stop_check", running=True,
                                       hold_should_stop=lambda _: False)
    rd, wr = os.pipe()
    event = struct.Struct("@llHHi")
    held_keys = set()

    def release(key):
        os.write(wr, event.pack(0, 0, 1, key, 0))
        os.write(wr, event.pack(0, 0, 0, 0, 0))
        held_keys.discard(key)

    sender = SimpleNamespace(ui=SimpleNamespace(fileno=lambda: wr), held=held_keys,
                             codes=SimpleNamespace(KEY_UP=103), unfinished=False,
                             check=lambda: None, release=release)
    engine.ensure_sender = lambda: sender
    try:
        held = engine.execute_intent(Hold("forward", 0.15))
        assert 0 < held <= 0.20 and not held_keys
        engine.measurement_only = False
        try:
            engine.hold("forward", 0.15)
        except InterruptedError:
            pass
        else:
            raise AssertionError("Assist allowed movement")
    finally:
        engine.selector.close()
        os.close(wr)
    data = bytearray()
    while chunk := os.read(rd, 4096):
        data.extend(chunk)
    os.close(rd)
    sent = [(kind, key, value) for _, _, kind, key, value in event.iter_unpack(data)]
    assert sent[:4] == [(1, 103, 1), (0, 0, 0), (1, 103, 0), (0, 0, 0)]
    assert sum(kind == 1 and value == 1 for kind, _, value in sent) == 1
    print("PASS: actual G0 intent dispatch uses watchdog pipe; one DOWN and released; assist hold refused; no input device or game input")


if __name__ == "__main__":
    main()
