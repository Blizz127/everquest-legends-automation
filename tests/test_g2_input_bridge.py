"""G2 bridge tests use a pipe as the descriptor, never a uinput device."""
import os
import struct
import threading
import time
from types import SimpleNamespace

import pytest

from eql_automation.g2_input_bridge import run_g2_forward
from eql_automation.g2_pulse_budget import G2Halt, G2PulseBudget, G2Scene
from eql_automation.uinput_watchdog import PulseError
import eql_automation.uinput_watchdog as watchdog


EVENT = struct.Struct("@llHHi")


class FakeSender:
    def __init__(self, fd, *, fail_at=None, fail_release=False, on_check=None):
        self.ui = SimpleNamespace(fileno=lambda: fd)
        self.codes = SimpleNamespace(KEY_UP=103)
        self.held = set()
        self.checks = 0
        self.fail_at = fail_at
        self.fail_release = fail_release
        self.on_check = on_check

    def check(self):
        self.checks += 1
        if self.on_check is not None:
            self.on_check()
        if self.fail_at == self.checks:
            raise InterruptedError("Owner stopped the check")

    def release(self, code):
        if self.fail_release:
            raise OSError("simulated final key-up failure")
        os.write(self.ui.fileno(), EVENT.pack(0, 0, 1, code, 0))
        os.write(self.ui.fileno(), EVENT.pack(0, 0, 0, 0, 0))
        self.held.discard(code)


def scene(*, target_absent=True):
    return G2Scene(time.monotonic(), "gfaydark", (0.0, 0.0, 10.0),
                   log_epoch=1, fix_seq=2, zone_generation=1, focused=True,
                   owner_keys_clear=True, chat_clear=True,
                   target_absent=target_absent, combat_clear=True,
                   no_transition=True, no_incoming_attack=True)


def budget():
    now = time.monotonic()
    # Stay inside the stationary interval, not on a subtraction-sensitive
    # exact 0.4-second boundary at large monotonic uptime values.
    first = G2Scene(now - 0.6, "gfaydark", (0.0, 0.0, 10.0),
                    log_epoch=1, fix_seq=1, zone_generation=1, focused=True,
                    owner_keys_clear=True, chat_clear=True,
                    target_absent=True, combat_clear=True,
                    no_transition=True, no_incoming_attack=True)
    second = G2Scene(now - 0.1, "gfaydark", (0.0, 0.0, 10.0),
                     log_epoch=1, fix_seq=2, zone_generation=1, focused=True,
                     owner_keys_clear=True, chat_clear=True,
                     target_absent=True, combat_clear=True,
                     no_transition=True, no_incoming_attack=True)
    return G2PulseBudget(first, second, geometry_candidate=True,
                         owner_confirmed_g0=True, clear_radius=18,
                         measured_speed=20, verified_speed_upper_bound=60,
                         speed_bound_observed_at=now - 0.2)


def events(read_fd, write_fd):
    os.close(write_fd)
    data = bytearray()
    while chunk := os.read(read_fd, 4096):
        data.extend(chunk)
    os.close(read_fd)
    return [(kind, code, value) for _, _, kind, code, value in EVENT.iter_unpack(data)]


def test_bridged_pulse_uses_existing_descriptor_then_requires_new_fixes():
    read_fd, write_fd = os.pipe()
    sender = FakeSender(write_fd)
    policy = budget()
    try:
        held = run_g2_forward(sender, policy, scene, lambda: None, threading.RLock())
    except G2Halt as error:
        # OS scheduling can make the watchdog's measured hold exceed the
        # strict 0.20-second budget. That must halt, with key-up still sent.
        assert "duration" in str(error)
        held = None
    sent = events(read_fd, write_fd)
    assert sent[:4] == [(1, 103, 1), (0, 0, 0), (1, 103, 0), (0, 0, 0)]
    assert not sender.held
    if held is None:
        assert policy.stage == "halted"
    else:
        assert 0 < held <= 0.20 and policy.stage == "await_fix"


def test_changed_target_before_down_sends_no_key():
    read_fd, write_fd = os.pipe()
    sender = FakeSender(write_fd)
    policy = budget()
    calls = 0

    def changed_scene():
        nonlocal calls
        calls += 1
        return scene(target_absent=calls == 1)

    with pytest.raises(RuntimeError):
        run_g2_forward(sender, policy, changed_scene, lambda: None, threading.RLock())
    sent = events(read_fd, write_fd)
    assert all(value != 1 for kind, _code, value in sent if kind == 1)
    assert policy.stage == "halted" and not sender.held


def test_owner_stop_during_pulse_releases_and_halts(monkeypatch):
    read_fd, write_fd = os.pipe()
    down = False
    original = watchdog._read_status

    def observe_ack(*args, **kwargs):
        nonlocal down
        result = original(*args, **kwargs)
        down |= result == "DOWN"
        return result

    def owner_check():
        if down:
            raise InterruptedError("Owner stopped after DOWN")

    monkeypatch.setattr(watchdog, "_read_status", observe_ack)
    sender = FakeSender(write_fd, on_check=owner_check)
    policy = budget()
    with pytest.raises(PulseError, match="interrupted"):
        run_g2_forward(sender, policy, scene, lambda: None, threading.RLock())
    sent = events(read_fd, write_fd)
    assert (1, 103, 1) in sent and (1, 103, 0) in sent
    assert policy.stage == "halted" and not sender.held


def test_failed_final_release_preserves_sender_held_record():
    read_fd, write_fd = os.pipe()
    sender = FakeSender(write_fd, fail_release=True)
    policy = budget()
    with pytest.raises(OSError, match="final key-up failure"):
        run_g2_forward(sender, policy, scene, lambda: None, threading.RLock())
    sent = events(read_fd, write_fd)
    assert (1, 103, 0) in sent  # Child watchdog and parent fallback still tried UP.
    assert 103 in sender.held  # Do not erase the cleanup evidence.
    assert policy.stage == "halted"


def test_off_winning_shared_lock_invalidates_pulse_before_go():
    read_fd, write_fd = os.pipe()
    checked = threading.Event()
    sender = FakeSender(write_fd, on_check=checked.set)
    policy = budget()
    stop_lock = threading.RLock()
    errors = []

    def run():
        try:
            run_g2_forward(sender, policy, scene, lambda: None, stop_lock)
        except Exception as exc:
            errors.append(exc)

    stop_lock.acquire()
    worker = threading.Thread(target=run)
    try:
        worker.start()
        assert checked.wait(2.0)
        policy.cancel()  # OFF holds the same lock that protects GO.
    finally:
        stop_lock.release()
    worker.join(2.0)
    assert not worker.is_alive() and errors
    sent = events(read_fd, write_fd)
    assert all(value != 1 for kind, _code, value in sent if kind == 1)
    assert policy.stage == "halted"
