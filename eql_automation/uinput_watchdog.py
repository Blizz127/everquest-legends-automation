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
from dataclasses import dataclass
import json
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


@dataclass(frozen=True)
class PulseSelection:
    """One key and duration selected after READY under the shared stop lock."""
    key_code: int
    seconds: float
    expires_at: float


@dataclass(frozen=True)
class PulseReceipt:
    """Child monotonic timestamps around complete DOWN/UP event writes.

    These bound writes to the existing descriptor, not when a game consumes
    them. In particular, parent return time is never a key-release timestamp.
    """
    key_code: int
    requested_seconds: float
    down_started_at: float
    down_completed_at: float
    up_started_at: float
    up_completed_at: float
    completion: str

    @property
    def held_seconds(self):
        # Preserve the original float API's DOWN-complete → UP-complete span.
        return self.up_completed_at - self.down_completed_at

    @property
    def maximum_held_seconds(self):
        return self.up_completed_at - self.down_started_at


def _valid_key_duration(key, seconds):
    return (isinstance(key, int) and not isinstance(key, bool) and 1 <= key <= 255
            and isinstance(seconds, (int, float)) and not isinstance(seconds, bool)
            and math.isfinite(seconds) and 0 < seconds <= _MAX_PULSE)


def _parse_receipt(result, key, seconds, sent_at, received_at):
    try:
        if not result.startswith("UP "):
            raise ValueError("missing UP receipt")
        receipt = PulseReceipt(**json.loads(result[3:]))
        stamps = (receipt.down_started_at, receipt.down_completed_at,
                  receipt.up_started_at, receipt.up_completed_at)
        if (not _valid_key_duration(receipt.key_code, receipt.requested_seconds)
                or receipt.key_code != key or receipt.requested_seconds != seconds
                or receipt.completion != "elapsed"
                or not all(isinstance(v, (int, float)) and not isinstance(v, bool)
                           and math.isfinite(v) for v in stamps)
                or not sent_at <= stamps[0] <= stamps[1] <= stamps[2] <= stamps[3] <= received_at
                or not 0 < receipt.maximum_held_seconds <= _MAX_PULSE + .05):
            raise ValueError("invalid child timestamp or key binding")
        return receipt
    except (ValueError, TypeError, KeyError) as error:
        raise PulseError("Invalid release watchdog timing receipt") from error


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
    """Compatibility API: return duration for G0 and existing G2 callers."""
    return timed_key_pulse_receipt(device_fd, key_code, seconds,
                                   before_down=before_down, pump=pump,
                                   should_stop=should_stop, go_lock=go_lock).held_seconds


def timed_key_pulse_receipt(device_fd: int, key_code: int, seconds: float, *,
                          before_down=None, pump=None, should_stop=None,
                          go_lock=None) -> PulseReceipt:
    """Hold one known key through the inherited device, returning child times.

    The child writes both DOWN and UP. It attempts to release on its own
    deadline even if the caller stalls or dies. STOP/EOF releases early. The parent writes
    an extra UP after the child exits, so an uncertain child outcome is not
    treated as a successful pulse.
    """
    if not _valid_key_duration(key_code, seconds):
        raise ValueError("Invalid same-device pulse parameters")
    return _run_pulse(device_fd, key_code, seconds, before_down=before_down,
                      pump=pump, should_stop=should_stop, go_lock=go_lock)


def selected_key_pulse_receipt(device_fd: int, select_after_ready, *,
                             pump=None, should_stop=None, go_lock=None) -> PulseReceipt | None:
    """Arm first, then select one key/duration under the caller's stop lock.

    The selector performs fresh mode, scene and swept-motion checks and
    returns PulseSelection, or None for no input. It must not send input.
    Startup delay therefore precedes the proposal rather than ageing it.
    """
    if not callable(select_after_ready) or go_lock is None:
        raise ValueError("Selected pulse requires a selector and shared stop lock")
    return _run_pulse(device_fd, None, None, select_after_ready=select_after_ready,
                      pump=pump, should_stop=should_stop, go_lock=go_lock)


def _run_pulse(device_fd, key_code, seconds, *, before_down=None, select_after_ready=None,
               pump=None, should_stop=None, go_lock=None):
    if (_EVENT.size != 24 or not isinstance(device_fd, int) or isinstance(device_fd, bool)
            or device_fd < 0):
        raise ValueError("Invalid same-device descriptor")
    os.fstat(device_fd)
    dynamic = select_after_ready is not None
    command = [sys.executable, "-m", "eql_automation.uinput_watchdog", "--child"]
    if dynamic:
        command.append("--select")
    command.extend([str(device_fd), str(key_code or 0), repr(float(seconds or 0))])
    child = subprocess.Popen(
        command,
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
            if dynamic:
                selection = select_after_ready()
                if selection is None:
                    return None
                if not isinstance(selection, PulseSelection) or not _valid_key_duration(selection.key_code, selection.seconds):
                    raise PulseError("Invalid selected watchdog pulse")
                key_code, seconds, expires_at = selection.key_code, selection.seconds, selection.expires_at
            else:
                expires_at = before_down() if before_down is not None else None
            if expires_at is not None and (not isinstance(expires_at, (int, float)) or
                                           isinstance(expires_at, bool) or not math.isfinite(expires_at)):
                raise PulseError("Invalid key-down permit deadline")
            if dynamic and expires_at is None:
                raise PulseError("Selected pulse requires a key-down deadline")
            if should_stop is not None and should_stop():
                raise PulseError("Pulse cancelled before GO")
            command = (f"GO2 {key_code} {seconds!r} {expires_at!r}\n".encode("ascii") if dynamic else
                       b"GO\n" if expires_at is None else f"GO:{expires_at:.9f}\n".encode("ascii"))
            try:
                sent_at = time.monotonic()
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
        receipt = _parse_receipt(result, key_code, seconds, sent_at, time.monotonic())
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
        if key_code is not None and (started or child.returncode != 0):
            _key(device_fd, key_code, 0)
        child.stdin.close()
        child.stdout.close()
    if should_stop is not None and should_stop():
        raise PulseError("Pulse cancelled after release")
    return receipt


def _child_main(device_fd: int, key_code: int, seconds: float, *, dynamic=False) -> int:
    if _EVENT.size != 24 or (not dynamic and not _valid_key_duration(key_code, seconds)):
        return 2
    down = False
    expires_at = None
    try:
        os.write(1, b"READY\n")
        ready, _, _ = select.select([0], [], [], 2.0)
        if not ready:
            return 1
        command = os.read(0, 256).strip()
        if dynamic:
            try:
                verb, raw_key, raw_seconds, raw_deadline = command.split()
                key_code, seconds, expires_at = int(raw_key), float(raw_seconds), float(raw_deadline)
            except (ValueError, TypeError):
                return 1
            if verb != b"GO2" or not _valid_key_duration(key_code, seconds) or not math.isfinite(expires_at):
                return 1
            if time.monotonic() > expires_at:
                os.write(1, b"EXPIRED\n")
                return 1
        elif command == b"GO":
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
        down_started_at = time.monotonic()
        if expires_at is not None and down_started_at > expires_at:
            os.write(1, b"EXPIRED\n")
            return 1
        down = True
        _key(device_fd, key_code, 1)
        began = time.monotonic()
        deadline = began + seconds
        os.write(1, b"DOWN\n")
        completion = "elapsed"
        while time.monotonic() < deadline:
            ready, _, _ = select.select([0], [], [], max(0, deadline - time.monotonic()))
            if ready:
                # STOP, EOF, or any unexpected command all release the key.
                os.read(0, 32)
                completion = "interrupted"
                break
        up_started_at = time.monotonic()
        _key(device_fd, key_code, 0)
        up_completed_at = time.monotonic()
        down = False
        receipt = dict(key_code=key_code, requested_seconds=seconds,
                       down_started_at=down_started_at, down_completed_at=began,
                       up_started_at=up_started_at, up_completed_at=up_completed_at,
                       completion=completion)
        os.write(1, ("UP " + json.dumps(receipt, separators=(",", ":")) + "\n").encode("ascii"))
        return 0
    finally:
        if down:
            _key(device_fd, key_code, 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--select", action="store_true")
    parser.add_argument("fd", type=int)
    parser.add_argument("key", type=int)
    parser.add_argument("seconds", type=float)
    args = parser.parse_args()
    if not args.child:
        return 2
    return _child_main(args.fd, args.key, args.seconds, dynamic=args.select)


if __name__ == "__main__":
    raise SystemExit(main())
