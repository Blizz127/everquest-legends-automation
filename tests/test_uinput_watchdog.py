"""The watchdog writes only to a test pipe, never an input device."""
import os
import select
import signal
import struct
import subprocess
import sys
import time

import pytest

from eql_automation.uinput_watchdog import PulseError, timed_key_pulse


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
