"""The watchdog writes only to a test pipe, never an input device."""
import os
import select
import signal
import struct
import subprocess
import sys
import threading
import time

import pytest

from eql_automation.uinput_watchdog import PulseError, timed_key_pulse
import eql_automation.uinput_watchdog as watchdog


EVENT = struct.Struct("@llHHi")


def frames(write_fd, read_fd):
    os.close(write_fd)
    chunks = []
    while chunk := os.read(read_fd, 4096):
        chunks.append(chunk)
    os.close(read_fd)
    data = b"".join(chunks)
    assert len(data) % EVENT.size == 0
    return [(kind, code, value) for _, _, kind, code, value in EVENT.iter_unpack(data)]


def test_short_pulse_uses_same_descriptor_and_releases():
    read_fd, write_fd = os.pipe()
    held = timed_key_pulse(write_fd, 17, 0.10)
    assert 0 < held <= 0.20
    assert frames(write_fd, read_fd) == [
        (1, 17, 1), (0, 0, 0), (1, 17, 0), (0, 0, 0),
        (1, 17, 0), (0, 0, 0),
    ]


def test_child_releases_while_caller_is_stalled():
    read_fd, write_fd = os.pipe()
    held = timed_key_pulse(write_fd, 17, 0.10, pump=lambda: time.sleep(0.30))
    assert 0 < held <= 0.20
    sent = frames(write_fd, read_fd)
    assert sent[:4] == [(1, 17, 1), (0, 0, 0), (1, 17, 0), (0, 0, 0)]


def test_stop_after_down_releases_and_does_not_report_success():
    read_fd, write_fd = os.pipe()
    checks = 0

    def stop():
        nonlocal checks
        checks += 1
        return checks >= 2

    with pytest.raises(PulseError, match="interrupted"):
        timed_key_pulse(write_fd, 17, 0.15, should_stop=stop)
    sent = frames(write_fd, read_fd)
    assert sent[0] == (1, 17, 1)
    assert (1, 17, 0) in sent


def test_refuses_overlong_hold_before_spawning():
    read_fd, write_fd = os.pipe()
    with pytest.raises(ValueError):
        timed_key_pulse(write_fd, 17, 0.21)
    assert frames(write_fd, read_fd) == []


def test_pre_keydown_gate_can_cancel_without_pressing():
    read_fd, write_fd = os.pipe()

    def reject():
        raise PulseError("Scene changed before key down")

    with pytest.raises(PulseError, match="Scene changed"):
        timed_key_pulse(write_fd, 17, 0.15, before_down=reject)
    sent = frames(write_fd, read_fd)
    assert all(not (kind == 1 and value == 1) for kind, _, value in sent)


def test_expired_child_deadline_never_presses_after_parent_stall():
    read_fd, write_fd = os.pipe()

    def stale_permit():
        expires_at = time.monotonic() + 0.05
        time.sleep(0.15)
        return expires_at

    with pytest.raises(PulseError, match="did not confirm key down"):
        timed_key_pulse(write_fd, 17, 0.10, before_down=stale_permit)
    sent = frames(write_fd, read_fd)
    assert all(not (kind == 1 and value == 1) for kind, _, value in sent)


def test_parent_kill_still_gets_same_device_key_up():
    read_fd, write_fd = os.pipe()
    code = ("import sys,time; from eql_automation.uinput_watchdog import timed_key_pulse; "
            "timed_key_pulse(int(sys.argv[1]),17,0.20,pump=lambda: time.sleep(1))")
    parent = subprocess.Popen([sys.executable, "-c", code, str(write_fd)],
                              pass_fds=(write_fd,), stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
    os.close(write_fd)
    packets = bytearray()
    deadline = time.monotonic() + 3.0
    try:
        while len(packets) < EVENT.size and time.monotonic() < deadline:
            ready, _, _ = select.select([read_fd], [], [], 0.05)
            if ready:
                packets.extend(os.read(read_fd, 4096))
        assert len(packets) >= EVENT.size
        assert EVENT.unpack_from(packets)[2:] == (1, 17, 1)
        os.kill(parent.pid, signal.SIGKILL)
        parent.wait(timeout=1)
        while time.monotonic() < deadline:
            ready, _, _ = select.select([read_fd], [], [], 0.05)
            if ready:
                chunk = os.read(read_fd, 4096)
                if not chunk:
                    break
                packets.extend(chunk)
        assert len(packets) % EVENT.size == 0
        events = [(kind, key, value) for _, _, kind, key, value in EVENT.iter_unpack(packets)]
        assert (1, 17, 0) in events
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait(timeout=1)
        os.close(read_fd)


def test_shared_stop_lock_stays_held_until_down_ack(monkeypatch):
    read_fd, write_fd = os.pipe()
    lock = threading.RLock()
    in_ack = threading.Event()
    continue_ack = threading.Event()
    off_acquired = threading.Event()
    calls = 0
    original = watchdog._read_status

    def delayed_ack(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            in_ack.set()
            assert continue_ack.wait(1.0)
        return original(*args, **kwargs)

    monkeypatch.setattr(watchdog, "_read_status", delayed_ack)
    errors = []

    def pulse():
        try:
            timed_key_pulse(write_fd, 17, 0.20, go_lock=lock)
        except Exception as exc:
            errors.append(exc)

    worker = threading.Thread(target=pulse)
    worker.start()
    assert in_ack.wait(2.0)

    def off():
        with lock:
            off_acquired.set()

    stopper = threading.Thread(target=off)
    stopper.start()
    assert not off_acquired.wait(0.02)
    continue_ack.set()
    worker.join(2.0)
    stopper.join(2.0)
    assert not worker.is_alive() and not stopper.is_alive()
    assert off_acquired.is_set() and not errors
    assert (1, 17, 0) in frames(write_fd, read_fd)
