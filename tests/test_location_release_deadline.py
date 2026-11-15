"""Real pipe cleanup plus deterministic hotkey admission/receipt boundaries."""
import os
import threading
import time
from types import SimpleNamespace

import pytest

import eql_automation.location_hotkey as hotkey
import eql_automation.uinput_watchdog as watchdog
from eql_automation.owner_input_observer import OwnerInputObservation


@pytest.fixture
def h(tmp_path):
    rd, wr = os.pipe()
    h = SimpleNamespace(rd=rd, wr=wr, clock=time.monotonic, stopped=False,
                        reasons=[], records=[], selections=[], events=[])
    configuration = tmp_path/'synthetic-hotbutton.ini'
    configuration.write_text('synthetic single location command\n')
    h.binding = hotkey.OwnerLocationHotkey.configured('F4', confirmation_id='synthetic-only',
                                                    configuration_paths=[configuration])
    h.sender = SimpleNamespace(ui=SimpleNamespace(fileno=lambda:wr), held=set(),
        unfinished=False, dismissed=False, check=lambda:None,
        gate=SimpleNamespace(controls_ready=lambda:True))
    def sample():
        now = h.clock()
        return OwnerInputObservation(now, now, 1, True, 1, 0, False, 0, 'synthetic input')
    def current():
        if h.stopped:raise hotkey.HotkeyStopped('owner stopped')
    def cancel(reason):
        h.stopped = True
        h.reasons.append(str(reason))
    h.cancel = cancel
    def run(**overrides):
        options = dict(binding=h.binding, owner_input=SimpleNamespace(sample=sample),
            lock=threading.RLock(), clock=h.clock, expires_at=h.clock()+2.,
            ensure_current=current, cancel=cancel, pump=lambda:None, record_event=h.records.append)
        options.update(overrides)
        return hotkey.send_location_hotkey(h.sender, **options)
    h.run = run
    def drain():
        os.set_blocking(rd, False)
        try:
            while True:
                try:data = os.read(rd, 65536)
                except BlockingIOError:break
                if not data:break
                h.events.extend(row[2:] for row in watchdog._EVENT.iter_unpack(data))
        finally:
            os.set_blocking(rd, True)
        return h.events
    h.drain = drain
    yield h
    os.close(wr)
    os.close(rd)


def precise_pulse(h, monkeypatch, *, receipt_down=None, receipt_up=None):
    """Replace child timing only; selection and final cleanup still use a pipe."""
    h.now = 10.
    h.clock = lambda:h.now
    def selected(fd, selector, *, should_stop, go_lock, pump):
        with go_lock:
            selection = selector()
            h.selections.append(selection)
            assert should_stop() is False
            assert h.now <= selection.expires_at
            for event in ((1, selection.key_code, 1), (0, 0, 0)):
                os.write(fd, watchdog._EVENT.pack(0, 0, *event))
        down = h.now if receipt_down is None else receipt_down
        up = down+selection.seconds if receipt_up is None else receipt_up
        h.now = up
        for event in ((1, selection.key_code, 0), (0, 0, 0)):
            os.write(fd, watchdog._EVENT.pack(0, 0, *event))
        return watchdog.PulseReceipt(selection.key_code, selection.seconds,
                                      down, down, up, up, 'elapsed')
    monkeypatch.setattr(hotkey, 'selected_key_pulse_receipt', selected)


def test_real_hotkey_pipe_reserves_hold_margin_and_releases(h):
    deadline = h.clock()+2.
    result = h.run(release_deadline=deadline)
    assert result.pulse.up_completed_at <= deadline
    assert 0 < result.pulse.maximum_held_seconds <= hotkey.MAXIMUM_ACCEPTED_HOTKEY_HOLD == .25
    assert result.pulse.down_started_at <= deadline-hotkey.MAXIMUM_ACCEPTED_HOTKEY_HOLD
    assert (1,62,1) in h.drain() and (1,62,0) in h.events
    assert not h.sender.held and h.sender._eql_route_operation is None
    assert h.records[-1]['release_deadline'] == deadline
    assert h.records[-1]['maximum_accepted_hold'] == .25


@pytest.mark.parametrize('deadline', (float('nan'), float('inf'), float('-inf'), True, '12', object()))
def test_nonfinite_or_untyped_deadline_refuses_before_claiming_sender(h, deadline):
    with pytest.raises(ValueError):h.run(release_deadline=deadline)
    assert not h.drain() and not h.sender.held
    assert not getattr(h.sender, '_eql_route_operation', None) and not h.records


def test_insufficient_margin_refuses_before_watchdog_or_down(h, monkeypatch):
    def forbidden(*args, **kwargs):raise AssertionError('Watchdog must not be armed')
    monkeypatch.setattr(hotkey, 'selected_key_pulse_receipt', forbidden)
    with pytest.raises(hotkey.HotkeyStopped, match='hold margin'):
        h.run(release_deadline=h.clock()+.249)
    assert not h.drain() and not h.sender.held and h.stopped
    assert h.sender._eql_route_operation is None


def test_exact_full_accepted_hold_boundary_is_not_extended(h, monkeypatch):
    precise_pulse(h, monkeypatch, receipt_up=10.25)
    result = h.run(release_deadline=10.25)
    assert h.selections[0].expires_at == 10.
    assert result.pulse.maximum_held_seconds == .25
    assert result.pulse.up_completed_at == 10.25
    assert (1,62,0) in h.drain() and not h.sender.held


def test_down_permit_uses_earlier_original_expiry(h, monkeypatch):
    precise_pulse(h, monkeypatch)
    h.run(expires_at=10.05, release_deadline=11.)
    assert h.selections[0].expires_at == 10.05


def test_down_permit_uses_earlier_release_margin(h, monkeypatch):
    precise_pulse(h, monkeypatch)
    h.run(release_deadline=10.30)
    assert h.selections[0].expires_at == pytest.approx(10.05)


@pytest.mark.parametrize('receipt_down, receipt_up, deadline', (
    (10., 10.251, 11.),     # Faulty child reports more than the accepted hold.
    (10.29, 10.31, 10.30), # Even a short reported hold cannot finish past expiry.
))
def test_bad_child_release_receipt_is_refused_after_mandatory_up(h, monkeypatch,
                                                              receipt_down, receipt_up, deadline):
    precise_pulse(h, monkeypatch, receipt_down=receipt_down, receipt_up=receipt_up)
    with pytest.raises(hotkey.HotkeyStopped, match='release receipt'):
        h.run(release_deadline=deadline)
    assert (1,62,1) in h.drain()
    assert h.events.count((1,62,0)) == 2  # Child UP and mandatory parent cleanup.
    assert h.stopped and not h.sender.held and h.sender._eql_route_operation is None
    assert h.records[-1]['receipt']['up_completed_at'] == receipt_up
    assert h.records[-1]['error'] is not None and h.records[-1]['cleanup_error'] is None


def test_owner_stop_after_real_down_still_releases(h, monkeypatch):
    original = watchdog._read_status
    def stopped(*args, **kwargs):
        result = original(*args, **kwargs)
        if result == 'DOWN':h.cancel('owner F9')
        return result
    monkeypatch.setattr(watchdog, '_read_status', stopped)
    with pytest.raises(RuntimeError):h.run(release_deadline=h.clock()+2.)
    assert (1,62,1) in h.drain() and (1,62,0) in h.events
    assert not h.sender.held and h.sender._eql_route_operation is None


def test_omitted_release_deadline_preserves_existing_admission(h, monkeypatch):
    precise_pulse(h, monkeypatch)
    h.run(expires_at=10.03)
    assert h.selections[0].expires_at == 10.03
    assert not h.stopped and not h.sender.held
    assert 'release_deadline' not in h.records[-1]
