"""Timing and late-selection contracts exercised with pipes, never uinput."""
from dataclasses import asdict, replace
import json
import os
import subprocess
import sys
import threading
import time

import pytest

import eql_automation.uinput_watchdog as watchdog
from eql_automation.uinput_watchdog import (
    PulseError, PulseReceipt, PulseSelection, selected_key_pulse_receipt,
    timed_key_pulse_receipt,
)


def close_events(read_fd, write_fd):
    os.close(write_fd)
    data = bytearray()
    while packet := os.read(read_fd, 4096):
        data.extend(packet)
    os.close(read_fd)
    return [(kind, key, value) for _, _, kind, key, value in watchdog._EVENT.iter_unpack(data)]


def test_child_timestamp_bounds_exclude_parent_stall():
    read_fd, write_fd = os.pipe()
    began = time.monotonic()
    receipt = timed_key_pulse_receipt(write_fd, 103, .04, pump=lambda: time.sleep(.25))
    ended = time.monotonic()
    assert began <= receipt.down_started_at <= receipt.down_completed_at <= receipt.up_started_at <= receipt.up_completed_at <= ended
    assert receipt.key_code == 103 and receipt.completion == "elapsed"
    assert .04 <= receipt.maximum_held_seconds < .2
    assert ended - receipt.up_completed_at > .1
    assert receipt.held_seconds <= receipt.maximum_held_seconds
    assert close_events(read_fd, write_fd)[:4] == [(1, 103, 1), (0, 0, 0), (1, 103, 0), (0, 0, 0)]


@pytest.mark.parametrize("key", [103, 105, 106])
def test_key_selected_only_after_ready_and_inside_stop_lock(monkeypatch, key):
    read_fd, write_fd = os.pipe()
    lock = threading.RLock()
    ready, selected = [], []
    original = watchdog._read_status
    def status(*args, **kwargs):
        reply = original(*args, **kwargs)
        if reply == "READY": ready.append(time.monotonic())
        return reply
    monkeypatch.setattr(watchdog, "_read_status", status)
    def choose():
        assert ready and lock._is_owned()
        selected.append(time.monotonic())
        return PulseSelection(key, .025, selected[-1] + .05)
    receipt = selected_key_pulse_receipt(write_fd, choose, go_lock=lock)
    assert len(selected) == 1 and ready[0] <= selected[0] <= receipt.down_started_at <= selected[0] + .05
    assert receipt.key_code == key and receipt.requested_seconds == .025
    assert close_events(read_fd, write_fd)[:4] == [(1, key, 1), (0, 0, 0), (1, key, 0), (0, 0, 0)]


def test_zero_input_selection_writes_no_events():
    read_fd, write_fd = os.pipe()
    assert selected_key_pulse_receipt(write_fd, lambda: None, go_lock=threading.RLock()) is None
    assert close_events(read_fd, write_fd) == []


@pytest.mark.parametrize("selection", [
    PulseSelection(True, .02, 1.), PulseSelection(103, float("nan"), 1.),
    PulseSelection(103, .21, 1.), PulseSelection(103, .02, float("inf")),
    PulseSelection(103, .02, None), {"key": 103},
])
def test_invalid_selection_never_presses(selection):
    read_fd, write_fd = os.pipe()
    with pytest.raises(PulseError):
        selected_key_pulse_receipt(write_fd, lambda: selection, go_lock=threading.RLock())
    assert all(value != 1 for kind, _, value in close_events(read_fd, write_fd) if kind == 1)


def test_slow_selector_does_not_refresh_its_expired_proposal():
    read_fd, write_fd = os.pipe()
    def choose():
        at = time.monotonic()
        time.sleep(.07)
        return PulseSelection(105, .02, at + .03)
    with pytest.raises(PulseError, match="expired key-down permit"):
        selected_key_pulse_receipt(write_fd, choose, go_lock=threading.RLock())
    assert all(value != 1 for kind, _, value in close_events(read_fd, write_fd) if kind == 1)


def test_cancel_inside_selector_is_rechecked_before_go():
    read_fd, write_fd = os.pipe()
    stopped = [False]
    def choose():
        stopped[0] = True
        return PulseSelection(106, .02, time.monotonic() + .05)
    with pytest.raises(PulseError, match="before GO"):
        selected_key_pulse_receipt(write_fd, choose, should_stop=lambda: stopped[0], go_lock=threading.RLock())
    assert all(value != 1 for kind, _, value in close_events(read_fd, write_fd) if kind == 1)


def test_cancel_after_up_receipt_still_cannot_report_success(monkeypatch):
    read_fd, write_fd = os.pipe()
    stopped = [False]
    original = watchdog._parse_receipt
    def parse(*args):
        receipt = original(*args)
        stopped[0] = True
        return receipt
    monkeypatch.setattr(watchdog, "_parse_receipt", parse)
    with pytest.raises(PulseError, match="after release"):
        timed_key_pulse_receipt(write_fd, 103, .02, should_stop=lambda: stopped[0])
    assert (1, 103, 0) in close_events(read_fd, write_fd)


@pytest.mark.parametrize("changes", [
    dict(key_code=105), dict(key_code=True), dict(requested_seconds=.1),
    dict(completion="interrupted"), dict(down_started_at=9.),
    dict(down_started_at=10.15), dict(down_completed_at=float("nan")),
    dict(up_started_at=10.09), dict(up_completed_at=11.),
])
def test_mismatched_reordered_nonfinite_or_interrupted_receipt_rejects(changes):
    receipt = PulseReceipt(103, .05, 10.10, 10.101, 10.151, 10.152, "elapsed")
    with pytest.raises(PulseError):
        watchdog._parse_receipt("UP " + json.dumps(asdict(replace(receipt, **changes))), 103, .05, 10., 10.2)


@pytest.mark.parametrize("payload", ["UP .05", "UP {", 'UP {"key_code": 103}', "DOWN", 'UP []'])
def test_partial_or_old_receipt_is_not_silently_accepted(payload):
    with pytest.raises(PulseError):
        watchdog._parse_receipt(payload, 103, .05, 10., 11.)


def test_child_stop_receipt_is_interrupted_even_when_key_up_succeeded():
    read_fd, write_fd = os.pipe()
    child = subprocess.Popen([sys.executable, '-m', 'eql_automation.uinput_watchdog',
                              '--child', str(write_fd), '105', '.15'],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             pass_fds=(write_fd,), bufsize=0)
    try:
        assert watchdog._read_status(child.stdout, time.monotonic() + 2) == 'READY'
        sent_at = time.monotonic()
        child.stdin.write(b'GO\n')
        assert watchdog._read_status(child.stdout, time.monotonic() + 1) == 'DOWN'
        child.stdin.write(b'STOP\n')
        result = watchdog._read_status(child.stdout, time.monotonic() + 1)
        assert json.loads(result[3:])['completion'] == 'interrupted'
        with pytest.raises(PulseError):
            watchdog._parse_receipt(result, 105, .15, sent_at, time.monotonic())
        assert child.wait(timeout=1) == 0
    finally:
        if child.poll() is None:
            child.kill(); child.wait(timeout=1)
        child.stdin.close(); child.stdout.close()
        sent = close_events(read_fd, write_fd)
    assert sent[:4] == [(1, 105, 1), (0, 0, 0), (1, 105, 0), (0, 0, 0)]


def test_receipt_brackets_slow_writes_in_child_not_parent_receive_time():
    read_fd, write_fd = os.pipe()
    script = '''import sys,time
import eql_automation.uinput_watchdog as w
original=w._key
def delayed(fd,key,value):
    time.sleep(.03)
    original(fd,key,value)
w._key=delayed
raise SystemExit(w._child_main(int(sys.argv[1]),103,.02))
'''
    child = subprocess.Popen([sys.executable, '-c', script, str(write_fd)],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             pass_fds=(write_fd,), bufsize=0)
    try:
        assert watchdog._read_status(child.stdout, time.monotonic() + 2) == 'READY'
        sent_at = time.monotonic()
        child.stdin.write(b'GO\n')
        assert watchdog._read_status(child.stdout, time.monotonic() + 1) == 'DOWN'
        result = watchdog._read_status(child.stdout, time.monotonic() + 1)
        receipt = watchdog._parse_receipt(result, 103, .02, sent_at, time.monotonic())
        assert receipt.down_completed_at - receipt.down_started_at >= .03
        assert receipt.up_completed_at - receipt.up_started_at >= .03
        assert receipt.maximum_held_seconds >= receipt.held_seconds + .03
        assert child.wait(timeout=1) == 0
    finally:
        if child.poll() is None:
            child.kill(); child.wait(timeout=1)
        child.stdin.close(); child.stdout.close()
        sent = close_events(read_fd, write_fd)
    assert sent[:4] == [(1, 103, 1), (0, 0, 0), (1, 103, 0), (0, 0, 0)]
