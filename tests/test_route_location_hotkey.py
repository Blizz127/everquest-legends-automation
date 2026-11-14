"""Real retained helper/watchdog and fixture log; no game or input devices."""
from dataclasses import replace
import os
from types import SimpleNamespace
import time

import pytest

from eql_automation.owner_input_observer import OwnerInputObservation
from eql_automation.route_location_hotkey import OwnerLocationHotkey, RouteLocationHotkeyExecutor
from test_motion_collection import retained
from test_motion_executors import PipeUI
from test_route_floor_commit import legacy
from test_route_location_executor import setup
from test_route_step_sender import after_down


@pytest.fixture
def h(tmp_path, retained, legacy):
    h = setup(tmp_path, retained, legacy)
    h.configuration = tmp_path/'owner-hotbutton.ini'
    h.configuration.write_text('synthetic single /location binding, not client acceptance\n')
    h.binding = OwnerLocationHotkey.configured('F4', confirmation_id='synthetic-owner-confirmation',
                                             configuration_paths=[h.configuration])
    h.on_sample = lambda: None
    def sample():
        h.on_sample()
        now = h.clock()
        return OwnerInputObservation(now, now, 1, True, 1, 0, False, 0, 'synthetic input')
    h.input = SimpleNamespace(sample=sample)
    h.executor = RouteLocationHotkeyExecutor(h.engine, h.session, hotkey=h.binding, owner_input=h.input)
    yield h
    h.close()


def test_one_actual_key_and_release_without_chat_or_command_journal(h):
    receipt = h.first_command()
    assert receipt.started_at <= receipt.completed_at <= h.clock()
    assert [code for kind, code, value in h.events if kind == 1 and value == 1] == [62]
    assert (1, 62, 0) in h.events and not h.sender.held and not h.sender.unfinished
    assert all(code in (0, 62) for _, code, _ in h.events)
    record = h.session.executor_events[-1]
    assert record['kind'] == 'location_hotbutton_result'
    assert not record['chat_keys_sent'] and not record['client_effect_verified']
    assert record['receipt']['key_code'] == 62
    assert record['released_at'] >= record['receipt']['up_completed_at']
    assert record['error'] is None and record['cleanup_error'] is None
    assert h.sender._eql_route_operation is None


@pytest.mark.parametrize('key', ['F6', 'F8', 'F9', 'F11', 'F12', 'UP', 'ENTER', 'ESC', 'A', '4'])
def test_no_default_printable_movement_or_helper_key(h, key):
    with pytest.raises(ValueError):
        OwnerLocationHotkey.configured(key, confirmation_id='owner', configuration_paths=[h.configuration])
    assert not h.events


@pytest.mark.parametrize('reason', ['source', 'focus', 'f9', 'assist', 'draft', 'activity', 'driver'])
def test_changed_state_before_down_never_sends_a_key(h, reason):
    if reason == 'source': h.configuration.write_text('changed')
    elif reason == 'focus': h.focus = False
    elif reason == 'f9': h.on_sample = lambda: h.engine.stop_action('owner F9')
    elif reason == 'assist': h.engine.measurement_only = False
    elif reason == 'draft': h.sender.unfinished = True
    elif reason == 'driver': h.engine.route_session_driver = None
    elif reason == 'activity':
        sample = h.input.sample
        h.input.sample = lambda: replace(sample(), activity=True)
    with pytest.raises((RuntimeError, InterruptedError)): h.first_command()
    assert not any(event[0] == 1 and event[2] == 1 for event in h.events)
    assert h.session.phase == 'stopped' and not h.sender.held


@pytest.mark.parametrize('change', ['device', 'focus'])
def test_reentrant_change_during_input_observation_never_sends_down(h, change):
    rd, wr = os.pipe()
    h.on_sample = (lambda: setattr(h.sender, 'ui', PipeUI(wr))) if change == 'device' else (
        lambda: setattr(h, 'focus', False))
    try:
        with pytest.raises(RuntimeError): h.first_command()
        assert not h.events and not h.sender.held
        os.set_blocking(rd, False)
        with pytest.raises(BlockingIOError): os.read(rd, 4096)
    finally:
        os.close(rd); os.close(wr)


def test_f9_during_down_always_releases_without_enter_or_escape(h, monkeypatch):
    after_down(monkeypatch, lambda: h.engine.stop_action('owner F9 during hotbutton'))
    with pytest.raises(RuntimeError): h.first_command()
    assert (1, 62, 1) in h.events and (1, 62, 0) in h.events
    assert not h.sender.held and not h.sender.unfinished and h.session.phase == 'stopped'
    assert all(code in (0, 62) for _, code, _ in h.events)


def test_replacement_during_down_releases_only_the_pinned_original(h, monkeypatch):
    rd, wr = os.pipe()
    after_down(monkeypatch, lambda: setattr(h.sender, 'ui', PipeUI(wr)))
    try:
        with pytest.raises(RuntimeError): h.first_command()
        assert (1, 62, 1) in h.events and (1, 62, 0) in h.events
        os.set_blocking(rd, False)
        with pytest.raises(BlockingIOError): os.read(rd, 4096)
        assert h.session.phase == 'stopped'
    finally:
        os.close(rd); os.close(wr)


def test_request_expiry_never_refreshes_timestamp_or_sends_down(h):
    h.session.deadline = h.clock()-.01
    with pytest.raises(RuntimeError): h.first_command()
    assert not h.events


@pytest.mark.parametrize('reply', ['missing', 'duplicate'])
def test_bad_log_reply_stops_route_without_another_trigger(h, reply):
    def location(request):
        result = h.executor.request_location(request)
        if reply == 'duplicate':
            for _ in range(2): h.append('Your Location is 1.00, 1.00, 2.30')
        return result
    h.driver.request_location = location
    deadline = time.monotonic()+4
    while h.engine.route_session_driver is not None and time.monotonic() < deadline:
        h.tick(); h.drain()
    assert h.session.phase == 'stopped' and not h.runner.steps
    assert [code for kind, code, value in h.events if kind == 1 and value == 1] == [62]
    assert not h.sender.held


def test_reply_before_up_stays_buffered_until_driver_receipt(h, monkeypatch):
    def reply():
        x, y, z = h.point
        h.append('Your Location is %.2f, %.2f, %.2f' % (y, x, z+2.1))
    after_down(monkeypatch, reply)
    h.driver.request_location = h.executor.request_location
    deadline = time.monotonic()+2
    while len(h.session.raw_fixes) == 0 and time.monotonic() < deadline:
        h.tick(); h.drain()
    assert len(h.session.requests) == 1 and len(h.session.raw_fixes) == 1
    assert h.session.phase == 'need_location' and not h.sender.held


def test_actual_route_driver_completes_with_hotbutton_and_fixture_feedback(h):
    deadline = time.monotonic()+25
    while h.engine.route_session_driver is not None and time.monotonic() < deadline:
        h.tick(); h.drain()
    record = h.engine.last_route_session_result
    assert record is not None and record['outcome'] == 'arrived', record
    assert record['segment_index'] == 2 and len(record['steps']) >= 2
    assert len(record['command_requests']) == 2*(len(record['steps'])+1)
    results = [row for row in record['executor_events'] if row['kind'] == 'location_hotbutton_result']
    assert len(results) == len(record['command_requests'])
    assert all(row['error'] is None and row['cleanup_error'] is None for row in results)
    assert not any(row['client_effect_verified'] or row['chat_keys_sent'] for row in results)
    assert {code for kind, code, value in h.events if kind == 1 and value == 1} == {62, 103}
    assert not h.sender.held and not record['real_client_accepted']
