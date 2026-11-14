"""Exercise the owner G0 adapter using pipes, never game input devices."""
import os
import struct
from types import SimpleNamespace

import pytest

from eql_automation.owner_g0_watchdog import make_owner_nov12_engine
import eql_automation.uinput_watchdog as watchdog


EVENT = struct.Struct("@llHHi")


class Sender:
    def __init__(self, fd):
        self.ui = SimpleNamespace(fileno=lambda: fd)
        self.codes = SimpleNamespace(KEY_UP=103)
        self.held = set()
        self.unfinished = False
        self.fail_release = False

    def check(self):
        pass

    def release(self, key):
        if self.fail_release:
            raise OSError("key-up failed")
        os.write(self.ui.fileno(), EVENT.pack(0, 0, 1, key, 0))
        os.write(self.ui.fileno(), EVENT.pack(0, 0, 0, 0, 0))
        self.held.discard(key)

    def release_all(self):
        for key in tuple(self.held):
            self.release(key)


class Base:
    def __init__(self, fd):
        self.sender = Sender(fd)
        self.measurement_only = True
        self.active = self.preparing = self.stopping = self.cancelled = False
        self.command_recovery_pending = False
        self.cancel_generation = 0
        self.autopilot = SimpleNamespace(mode="stop_check", running=True)
        self.logs = []
        self.ensure_calls = 0
        self.pump_hook = lambda: None

    def ensure_sender(self):
        self.ensure_calls += 1
        return self.sender

    def pump(self):
        self.pump_hook()

    def trace(self, event, **values):
        self.logs.append((event, values))

    def stop_action(self, *_args, **_kwargs):
        self.cancel_generation += 1
        self.cancelled = True
        self.autopilot.running = False
        self.sender.release_all()

    def stop_autopilot(self, reason):
        self.stop_action(reason)


def frames(rd, wr):
    os.close(wr)
    data = bytearray()
    while chunk := os.read(rd, 4096):
        data.extend(chunk)
    os.close(rd)
    return [(kind, key, value) for _, _, kind, key, value in EVENT.iter_unpack(data)]


def test_existing_g0_uses_watchdog_and_clears_held_keys():
    rd, wr = os.pipe()
    engine = make_owner_nov12_engine(Base)(wr)
    held = engine.hold("forward", 0.15)
    sent = frames(rd, wr)
    assert 0 < held <= 0.20
    assert sent[:4] == [(1, 103, 1), (0, 0, 0), (1, 103, 0), (0, 0, 0)]
    assert len([x for x in sent if x[0] == 1 and x[2] == 1]) == 1
    assert not engine.sender.held
    assert engine.logs[-1][1]["release"] == "same_device_watchdog"


@pytest.mark.parametrize("field,value", [("measurement_only", False), ("active", True),
                                         ("preparing", True), ("autopilot", None)])
def test_assist_and_invalid_modes_never_reach_sender(field, value):
    rd, wr = os.pipe()
    engine = make_owner_nov12_engine(Base)(wr)
    setattr(engine, field, value)
    with pytest.raises(InterruptedError, match="Only"):
        engine.hold("forward", 0.15)
    assert engine.ensure_calls == 0 and frames(rd, wr) == []


@pytest.mark.parametrize("key,seconds,jump", [("left", .15, None), ("forward", .16, None),
                                            ("forward", .15, .05), ("forward", True, None)])
def test_only_exact_existing_forward_pulse_is_allowed(key, seconds, jump):
    rd, wr = os.pipe()
    engine = make_owner_nov12_engine(Base)(wr)
    with pytest.raises(InterruptedError, match="Only"):
        engine.hold(key, seconds, jump_at=jump)
    assert engine.ensure_calls == 0 and frames(rd, wr) == []


def test_reentrant_f9_before_go_does_not_deadlock_or_press(monkeypatch):
    rd, wr = os.pipe()
    engine = make_owner_nov12_engine(Base)(wr)
    # The real before_down pump runs inside the shared lock. A physical F9
    # handled there reenters stop_action on the same engine thread.
    engine.pump_hook = lambda: engine.stop_action("F9") if engine.g0_stop_lock._is_owned() else None
    with pytest.raises(InterruptedError):
        engine.hold("forward", 0.15)
    assert engine.cancel_generation == 1
    assert all(value != 1 for kind, _, value in frames(rd, wr) if kind == 1)


@pytest.mark.parametrize("stop_method", ["stop_action", "stop_autopilot"])
def test_f9_or_f11_after_down_releases_and_rejects_result(monkeypatch, stop_method):
    rd, wr = os.pipe()
    engine = make_owner_nov12_engine(Base)(wr)
    down = False
    original = watchdog._read_status

    def observe(*args, **kwargs):
        nonlocal down
        result = original(*args, **kwargs)
        down |= result == "DOWN"
        return result

    monkeypatch.setattr(watchdog, "_read_status", observe)
    engine.pump_hook = lambda: getattr(engine, stop_method)("owner stop") if down else None
    with pytest.raises(InterruptedError):
        engine.hold("forward", 0.15)
    sent = frames(rd, wr)
    assert (1, 103, 1) in sent and (1, 103, 0) in sent
    assert not engine.sender.held and engine.stopped_mid_command


def test_failed_sender_release_remains_visible_for_cleanup():
    rd, wr = os.pipe()
    engine = make_owner_nov12_engine(Base)(wr)
    engine.sender.fail_release = True
    with pytest.raises(OSError, match="key-up failed"):
        engine.hold("forward", 0.15)
    assert (1, 103, 0) in frames(rd, wr)  # Independent child already attempted UP.
    assert engine.sender.held == {103}


def test_gui_stop_after_child_up_cannot_accept_the_result(monkeypatch):
    rd, wr = os.pipe()
    engine = make_owner_nov12_engine(Base)(wr)
    original = watchdog._read_status

    def observe(*args, **kwargs):
        result = original(*args, **kwargs)
        if result.startswith("UP "):
            engine.cancelled = True  # GUI STOP sets this before its worker job.
        return result

    monkeypatch.setattr(watchdog, "_read_status", observe)
    with pytest.raises(InterruptedError, match="after release"):
        engine.hold("forward", 0.15)
    sent = frames(rd, wr)
    assert (1, 103, 1) in sent and (1, 103, 0) in sent
    assert not engine.sender.held
    assert not any(event == "hold" for event, _ in engine.logs)
