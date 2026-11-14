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

from eql_automation.uinput_watchdog import PulseError, PulseInterrupted, timed_key_pulse
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


def test_stop_after_down_releases_and_does_not_report_success(monkeypatch):
    read_fd, write_fd = os.pipe()
    down = False
    original = watchdog._read_status

    def observe_ack(*args, **kwargs):
        nonlocal down
        result = original(*args, **kwargs)
        down |= result == "DOWN"
        return result

    monkeypatch.setattr(watchdog, "_read_status", observe_ack)
    with pytest.raises(PulseInterrupted, match="interrupted") as caught:
        timed_key_pulse(write_fd, 17, 0.15, should_stop=lambda: down)
    receipt=caught.value.receipt
    assert receipt.key_code==17 and receipt.requested_seconds==.15
    assert receipt.completion in ('interrupted','elapsed')
    assert receipt.down_started_at<=receipt.down_completed_at<=receipt.up_started_at<=receipt.up_completed_at
    sent = frames(write_fd, read_fd)
    assert sent[0] == (1, 17, 1)
    assert (1, 17, 0) in sent


def test_stop_after_elapsed_release_retains_receipt_but_never_returns_success(monkeypatch):
    read_fd,write_fd=os.pipe();released=False
    original=watchdog._read_status
    def observe(*args,**kwargs):
        nonlocal released
        result=original(*args,**kwargs)
        released|=result.startswith('UP ')
        return result
    monkeypatch.setattr(watchdog,'_read_status',observe)
    with pytest.raises(PulseInterrupted,match='after release') as caught:
        timed_key_pulse(write_fd,17,.03,should_stop=lambda:released)
    assert caught.value.receipt.completion=='elapsed'
    sent=frames(write_fd,read_fd)
    assert sent[0]==(1,17,1) and sent[-2:]==[(1,17,0),(0,0,0)]


def test_late_stop_reads_queued_up_even_after_child_exited(monkeypatch):
    read_fd,write_fd=os.pipe();down=False
    original=watchdog._read_status
    def observe(*args,**kwargs):
        nonlocal down
        result=original(*args,**kwargs)
        if result=='DOWN':
            down=True;time.sleep(.1)
        return result
    monkeypatch.setattr(watchdog,'_read_status',observe)
    with pytest.raises(PulseInterrupted) as caught:
        timed_key_pulse(write_fd,17,.02,should_stop=lambda:down)
    assert caught.value.receipt.completion=='elapsed'
    sent=frames(write_fd,read_fd)
    assert sent[0]==(1,17,1) and sent[-2:]==[(1,17,0),(0,0,0)]


def test_ready_wait_pumps_stop_without_sending_down():
    read_fd, write_fd = os.pipe()
    stopped = False

    def pump():
        nonlocal stopped
        stopped = True

    with pytest.raises(PulseError, match="did not arm"):
        timed_key_pulse(write_fd, 17, 0.15, pump=pump, should_stop=lambda: stopped)
    assert all(value != 1 for kind, _, value in frames(write_fd, read_fd) if kind == 1)


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

    with pytest.raises(watchdog.PulsePermitExpired, match="expired key-down permit") as caught:
        timed_key_pulse(write_fd, 17, 0.10, before_down=stale_permit)
    timing=caught.value.timing
    assert timing['selection_returned_at']>timing['permit_expires_at']
    assert timing['selection_returned_at']<=timing['stop_checked_at']<=timing['go_sent_at']<=timing['reply_received_at']
    sent = frames(write_fd, read_fd)
    assert all(not (kind == 1 and value == 1) for kind, _, value in sent)


def test_final_stop_check_expiry_is_distinct_from_missing_down_ack():
    read_fd,write_fd=os.pipe();selected=False
    def choose():
        nonlocal selected
        selected=True
        return watchdog.PulseSelection(17,.1,time.monotonic()+.05)
    def stop():
        if selected:time.sleep(.15)
        return False
    with pytest.raises(watchdog.PulsePermitExpired) as caught:
        watchdog.selected_key_pulse_receipt(write_fd,choose,should_stop=stop,go_lock=threading.RLock())
    timing=caught.value.timing
    assert timing['stop_checked_at']>timing['permit_expires_at']
    assert timing['stop_checked_at']-timing['selection_returned_at']>=.15
    sent=frames(write_fd,read_fd)
    assert all(not (kind==1 and value==1) for kind,_,value in sent)


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
