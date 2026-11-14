"""Actual retained engine and shared hotkey sender, exclusively on a pipe."""
from dataclasses import replace
import json
import os
from pathlib import Path
import re
import time
from types import SimpleNamespace

import pytest

from eql_automation.owner_input_observer import OwnerInputObservation
from eql_automation.owner_location_hotkey_test import HOTKEY_TEST_JOB, make_owner_nov12_engine
from eql_automation.uinput_watchdog import _EVENT
from test_motion_collection import retained
from test_motion_executors import PipeUI
from test_route_step_sender import after_down


@pytest.fixture
def h(tmp_path, retained):
    Engine, Settings, _ = retained
    import rotation_engine
    game = tmp_path/'game'
    (game/'Logs').mkdir(parents=True)
    for name in ('eqclient.ini', 'Probe_private_LO1.ini'):
        (game/name).write_text('synthetic configuration\n')
    log = game/'Logs/eqlog_Probe_private.txt'
    log.write_text('old data must not become a result\n')
    h = SimpleNamespace(focused=True, events=[], traces=[], notices=[], observer_closed=False,
                        sample_hook=lambda: None, init_hook=lambda: None, pump_hook=lambda: None)
    window = SimpleNamespace(id=42)
    h.gate = SimpleNamespace(windows=lambda: [window], focused_window=lambda: window if h.focused else None,
        game_session=lambda: {'pid': 10, 'start_ticks': '100'}, focused=lambda: h.focused,
        controls_ready=lambda: h.focused)
    class Observer:
        def __init__(self, **kw):
            assert kw['helper_ui'] is h.sender.ui
        def sample(self):
            h.sample_hook()
            now = time.monotonic()
            return OwnerInputObservation(now, now, 1, True, 1, 0, False, 0, 'synthetic input')
        def close(self):
            h.observer_closed = True
    e = make_owner_nov12_engine(Engine, observer_factory=Observer, output=tmp_path/'reports')(
        Settings(game_dir=str(game), character='Probe', server='private'),
        lambda *_: None, lambda *_: None, measurement_only=True)
    e.selector.close()
    e.gate = h.gate
    e.trace = lambda event, **values: h.traces.append((event, values))
    e.emit = lambda value=None: h.notices.append(value)
    e.input_events = lambda: h.pump_hook()
    e.read_log = lambda: None
    e.blocked_keys = lambda: False
    codes = {name: int(value) for name, value in re.findall(r'^#define\s+(KEY_\w+|EV_KEY)\s+(\d+)\b',
        Path('/usr/include/linux/input-event-codes.h').read_text(), re.M)}
    rd, wr = os.pipe()
    sender = rotation_engine.KeySender.__new__(rotation_engine.KeySender)
    sender.ui = PipeUI(wr); sender.codes = SimpleNamespace(**codes)
    sender.held = set(); sender.unfinished = sender.dismissed = False
    sender.gate = h.gate; sender.allowed = e.allowed
    h.sender, h.engine, h.log, h.game = sender, e, log, game
    def ensure():
        e.sender = sender
        h.init_hook()
        return sender
    e.ensure_sender = ensure
    def forbidden(*args, **kwargs): raise AssertionError('No typing, movement or pointer allowed')
    e.send = e.hold = e.ensure_pointer = forbidden
    def start(selection=None):
        e.post(HOTKEY_TEST_JOB, selection if selection is not None else {'key_name': 'F4', 'confirmed': True})
        e.handle_job(*e.jobs.get_nowait())
    h.start = start
    h.tick = lambda: e.autopilot_tick(time.monotonic())
    def due():
        e.hotkey_test['due'] = time.monotonic()-.001
        h.tick()
    h.due = due
    def append(body='Your Location is 1, 2, 3'):
        from datetime import datetime
        with log.open('a') as out: out.write(datetime.now().strftime('[%a %b %d %H:%M:%S %Y] ')+body+'\n')
    h.append = append
    def drain():
        os.set_blocking(rd, False)
        try:
            data = os.read(rd, 65536)
        except BlockingIOError:
            return
        h.events.extend(row[2:] for row in _EVENT.iter_unpack(data))
    h.drain = drain
    yield h
    if e.hotkey_test is not None: e._finish_hotkey_test('cancelled', 'test teardown')
    h.drain(); os.close(wr); os.close(rd)


def finish(h):
    end = time.monotonic()+4
    while h.engine.hotkey_test is not None and time.monotonic() < end:
        h.tick(); time.sleep(.01)
    h.drain()
    return h.engine.last_hotkey_test


def test_owner_start_after_stop_sends_once_and_records_early_reply(h, monkeypatch):
    e = h.engine
    e.stop_action('previous owner stop')
    after_down(monkeypatch, h.append)
    h.start()
    assert e.hotkey_test['stage'] == 'countdown' and not e.cancelled
    h.due()
    result = finish(h)
    assert result['outcome'] == 'observed_location'
    assert result['location']['raw_coordinates'] == (1., 2., 3.)
    assert [code for kind, code, value in h.events if kind == 1 and value == 1] == [62]
    assert (1, 62, 0) in h.events and not h.sender.held
    assert e.cancelled and not e.active and h.observer_closed
    assert not result['macro_contents_mechanically_verified']
    assert not result['chat_keys_sent'] and not result['movement_requested'] and not result['real_route_accepted']
    saved = json.loads(e.last_hotkey_test_path.read_text())
    assert saved['owner_setup']['key_name'] == 'F4'
    assert saved['location']['raw_coordinates'] == [1., 2., 3.]


@pytest.mark.parametrize('selection', [{'key_name': 'F9', 'confirmed': True},
                                      {'key_name': 'F4', 'confirmed': False}, None])
def test_explicit_key_and_confirmation_required(h, selection):
    h.engine.post(HOTKEY_TEST_JOB, selection)
    h.engine.handle_job(*h.engine.jobs.get_nowait())
    assert h.engine.hotkey_test is None and h.engine.sender is None


@pytest.mark.parametrize('when', ['init', 'countdown', 'down'])
def test_f9_never_gets_cleared_and_always_releases(h, monkeypatch, when):
    stop = lambda: h.engine.stop_action('F9')
    if when == 'init': h.init_hook = stop
    if when == 'down': after_down(monkeypatch, stop)
    h.start()
    if when == 'countdown': stop(); h.tick()
    if when == 'down': h.due()
    h.drain()
    assert h.engine.hotkey_test is None and h.engine.cancelled and not h.sender.held
    assert h.engine.last_hotkey_test['outcome'] == 'refused'
    assert ((1, 62, 1) in h.events) == (when == 'down')
    if when == 'down': assert (1, 62, 0) in h.events


@pytest.mark.parametrize('change', ['f11', 'post', 'focus', 'source', 'assist', 'old_reply'])
def test_countdown_changes_refuse_without_key(h, change):
    h.start()
    if change == 'f11': h.engine.stop_autopilot('F11')
    elif change == 'post': h.engine.post('settings', h.engine.settings)
    elif change == 'focus': h.focused = False
    elif change == 'source': (h.game/'eqclient.ini').write_text('changed')
    elif change == 'assist': h.engine.measurement_only = False
    elif change == 'old_reply': h.append()
    h.due(); h.drain()
    assert h.engine.hotkey_test is None and not h.events


@pytest.mark.parametrize('reply', ['missing', 'duplicate', 'transition'])
def test_bad_replies_stop_without_retries(h, monkeypatch, reply):
    if reply == 'duplicate': after_down(monkeypatch, lambda: (h.append(), h.append()))
    elif reply == 'transition': after_down(monkeypatch, lambda: h.append('LOADING, PLEASE WAIT...'))
    h.start(); h.due()
    result = finish(h)
    assert result['outcome'] == 'refused' and not h.sender.held
    assert [code for kind, code, value in h.events if kind == 1 and value == 1] == [62]


def test_reentrant_tick_during_dispatch_cannot_fire_twice(h, monkeypatch):
    after_down(monkeypatch, lambda: (h.tick(), h.append()))
    h.start(); h.due()
    result = finish(h)
    assert result['outcome'] == 'observed_location'
    assert [code for kind, code, value in h.events if kind == 1 and value == 1] == [62]


def test_assist_cannot_start_hotbutton_test(h):
    h.engine.measurement_only = False
    h.start()
    assert h.engine.hotkey_test is None and h.engine.sender is None


def test_configuration_is_read_only_and_suffix_is_resolved(h, monkeypatch):
    before = {p: p.read_bytes() for p in h.game.glob('*.ini')}
    after_down(monkeypatch, h.append)
    h.start(); h.due(); result = finish(h)
    assert result['outcome'] == 'observed_location'
    assert {p: p.read_bytes() for p in before} == before
    assert any(path.endswith('Probe_private_LO1.ini') for path, _ in result['owner_setup']['configuration_sha256'])
