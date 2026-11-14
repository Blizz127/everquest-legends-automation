"""One bounded key pulse with an independent release on the *same* uinput fd.

This creates no input device. The isolated owner G0 adapter can supply its
existing device; pipe tests alone do not prove release in the real client.
The caller supplies an already-created uinput file descriptor, owns that key
exclusively, and must still check focus, owner input, target and game state
before and during a pulse. Deadlines depend on OS scheduling, not real time.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import math
import os
import select
import struct
import subprocess
import sys
import time
from typing import Callable


_EVENT = struct.Struct("@llHHi")  # Linux input_event on the 64-bit target.
_EV_SYN, _EV_KEY, _SYN_REPORT = 0, 1, 0
_MAX_PULSE = 0.20


class PulseError(RuntimeError):
    pass


def _write_event(fd: int, kind: int, code: int, value: int) -> None:
    packet = _EVENT.pack(0, 0, kind, code, value)
    if os.write(fd, packet) != len(packet):
        raise OSError("Incomplete input event")


def _key(fd: int, code: int, value: int) -> None:
    _write_event(fd, _EV_KEY, code, value)
    _write_event(fd, _EV_SYN, _SYN_REPORT, 0)


def _read_status(pipe, deadline: float, *, pump: Callable[[], None] | None = None,
                 should_stop: Callable[[], bool] | None = None) -> str:
    while time.monotonic() < deadline:
        if pump is not None:
            pump()
        if should_stop is not None and should_stop():
            return "STOP"
        ready, _, _ = select.select([pipe], [], [], min(0.01, max(0, deadline - time.monotonic())))
        if ready:
            line = pipe.readline()
            if not line:
                raise PulseError("Release watchdog exited without an acknowledgment")
            return line.decode("ascii", "strict").strip()
    raise PulseError("Release watchdog acknowledgment timed out")


def timed_key_pulse(device_fd: int, key_code: int, seconds: float, *,
                    before_down: Callable[[], float | None] | None = None,
                    pump: Callable[[], None] | None = None,
                    should_stop: Callable[[], bool] | None = None,
                    go_lock=None) -> float:
    """Hold one key through the inherited device, or fail closed.

    The child writes both DOWN and UP. It attempts to release on its own
    deadline even if the caller stalls or dies. STOP/EOF releases early. The parent writes
    an extra UP after the child exits, so an uncertain child outcome is not
    treated as a successful pulse.
    """
    if (_EVENT.size != 24 or not isinstance(device_fd, int) or device_fd < 0
            or not isinstance(key_code, int) or not 1 <= key_code <= 255
            or not isinstance(seconds, (int, float)) or not 0 < seconds <= _MAX_PULSE):
        raise ValueError("Invalid same-device pulse parameters")
    os.fstat(device_fd)
    child = subprocess.Popen(
        [sys.executable, "-m", "eql_automation.uinput_watchdog", "--child",
         str(device_fd), str(key_code), repr(float(seconds))],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        pass_fds=(device_fd,), bufsize=0, start_new_session=True,
    )
    started = False
    try:
        if _read_status(child.stdout, time.monotonic() + 2.0,
                        pump=pump, should_stop=should_stop) != "READY":
            raise PulseError("Release watchdog did not arm")
        if should_stop is not None and should_stop():
            raise PulseError("Pulse cancelled before key down")
        with (go_lock if go_lock is not None else nullcontext()):
            expires_at = before_down() if before_down is not None else None
            if expires_at is not None and (not isinstance(expires_at, (int, float)) or
                                           not math.isfinite(expires_at)):
                raise PulseError("Invalid key-down permit deadline")
            command = b"GO\n" if expires_at is None else f"GO:{expires_at:.9f}\n".encode("ascii")
            try:
                child.stdin.write(command)
                # No reentrant stop here: once GO is queued, OFF must not
                # return until DOWN is acknowledged or the child is killed
                # and UP written. READY and UP waits still pump owner input.
                if _read_status(child.stdout, time.monotonic() + 0.30) != "DOWN":
                    raise PulseError("Release watchdog did not confirm key down")
                started = True
            except BaseException:
                # OFF shares this lock. Do not let it return while GO could
                # still be queued for a child that has not acknowledged DOWN.
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=0.5)
                _key(device_fd, key_code, 0)
                raise
        result = _read_status(child.stdout, time.monotonic() + 1.0,
                              pump=pump, should_stop=should_stop)
        if result == "STOP":
            raise PulseError("Pulse interrupted")
        if not result.startswith("UP "):
            raise PulseError("Release watchdog did not confirm key up")
        held = float(result[3:])
        if not 0 < held <= _MAX_PULSE + 0.05:
            raise PulseError("Release watchdog exceeded the pulse limit")
        return held
    finally:
        if child.poll() is None:
            try:
                child.stdin.write(b"STOP\n")
            except (BrokenPipeError, OSError):
                pass
            try:
                child.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=0.5)
        if started or child.returncode != 0:
            _key(device_fd, key_code, 0)
        child.stdin.close()
        child.stdout.close()


def _child_main(device_fd: int, key_code: int, seconds: float) -> int:
    if _EVENT.size != 24 or not 1 <= key_code <= 255 or not 0 < seconds <= _MAX_PULSE:
        return 2
    down = False
    try:
        os.write(1, b"READY\n")
        ready, _, _ = select.select([0], [], [], 2.0)
        if not ready:
            return 1
        command = os.read(0, 64).strip()
        if command == b"GO":
            pass
        elif command.startswith(b"GO:"):
            try:
                expires_at = float(command[3:])
            except ValueError:
                return 1
            if not math.isfinite(expires_at) or time.monotonic() > expires_at:
                os.write(1, b"EXPIRED\n")
                return 1
        else:
            return 1
        down = True
        _key(device_fd, key_code, 1)
        began = time.monotonic()
        deadline = began + seconds
        os.write(1, b"DOWN\n")
        while time.monotonic() < deadline:
            ready, _, _ = select.select([0], [], [], max(0, deadline - time.monotonic()))
            if ready:
                # STOP, EOF, or any unexpected command all release the key.
                os.read(0, 32)
                break
        _key(device_fd, key_code, 0)
        down = False
        os.write(1, f"UP {time.monotonic() - began:.6f}\n".encode("ascii"))
        return 0
    finally:
        if down:
            _key(device_fd, key_code, 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", action="store_true")
    parser.add_argument("fd", type=int)
    parser.add_argument("key", type=int)
    parser.add_argument("seconds", type=float)
    args = parser.parse_args()
    if not args.child:
        return 2
    return _child_main(args.fd, args.key, args.seconds)


if __name__ == "__main__":
    raise SystemExit(main())
