"""Live-format logs and the retained helper; no client/device operations."""
from types import SimpleNamespace

import pytest

from eql_automation.owner_zone_tracker import LiveZoneTracker
from eql_automation.owner_route_adapter import make_route_session_engine
from eql_automation.owner_position_adapter import make_owner_nov12_engine
from test_motion_collection import retained


def fixture(tmp_path):
    h = SimpleNamespace(binding=('game', 'Probe', 'private', 42, 10, 100), now=100.)
    h.game = tmp_path/'game'
    (h.game/'Logs').mkdir(parents=True)
    (h.game/'Resources').mkdir()
    h.log = h.game/'Logs/eqlog_Probe_private.txt'
    h.zones = h.game/'Resources/ZoneNames.txt'
    h.zones.write_text('1^Example One^0^0\n2^Example Two^0^0\n')
    h.log.touch()
    def append(body, second=1):
        with h.log.open('a') as out:
            out.write(f'[Sat Nov 14 06:00:{second:02d} 2026] {body}\n')
    h.append = append
    h.create = lambda: LiveZoneTracker(h.log, h.zones,
        expected_character='Probe', expected_server='private',
        binding_reader=lambda: h.binding, clock=lambda: h.now)
    return h


def test_existing_history_never_becomes_current_zone(tmp_path):
    h = fixture(tmp_path)
    h.append('You have entered Example One.')
    h.append('Your Location is 1, 2, 3')
    t = h.create()
    with pytest.raises(ValueError, match='live-observed'):
        t.acquire()
    h.append('Your Location is 4, 5, 6', 2)
    t.poll()
    assert t.reader.zone_id is None and t.reader.latest is None


def test_handoff_retains_zone_and_cursor_but_requires_new_position(tmp_path):
    h = fixture(tmp_path); t = h.create()
    h.append('You have entered Example One.')
    h.append('Your Location is 1, 2, 3')
    t.poll()
    reader, seq, generation = t.reader, t.reader.log_line_seq, t.reader.zone_generation
    lease = t.acquire()
    assert lease.reader is reader and reader.latest is None
    assert (reader.zone_id, reader.log_line_seq, reader.zone_generation) == (1, seq, generation)
    cursor = reader.tail.position
    h.append('Your Location is 4, 5, 6', 2)
    t.poll(); t.poll()  # Nested helper ticks must not steal the route reply.
    assert reader.tail.position == cursor and reader.log_line_seq == seq
    fix, = lease.reader.poll(now=101.)
    assert fix.raw_coordinates == (4., 5., 6.) and fix.zone_generation == generation
    assert lease.check() == h.binding
    with pytest.raises(ValueError, match='already leased'):
        t.acquire()
    lease.release(); lease.release()
    assert reader.latest is None and reader.zone_id == 1
    with pytest.raises(ValueError, match='lease ended'):
        lease.check()
    h.append('You have entered Example Two.', 3)
    h.now = 102.; t.poll()
    assert reader.zone_id == 2


@pytest.mark.parametrize('change', ['binding', 'close', 'revoke'])
def test_revocation_pauses_cursor_until_borrower_cleanup(tmp_path, change):
    h = fixture(tmp_path); t = h.create(); h.append('You have entered Example One.')
    lease = t.acquire(); cursor = lease.reader.tail.position
    h.append('Your Location is 4, 5, 6', 2)
    if change == 'binding':
        h.binding = ('changed-game',)
    elif change == 'close':
        t.close()
    else:
        t.revoke_lease(); t.poll()
    with pytest.raises(ValueError):
        lease.check()
    assert lease.reader.tail.position == cursor
    lease.release()  # Cleanup after cancellation must not raise a second error.
    assert not lease.active and t.lease is None


@pytest.mark.parametrize('body', ['LOADING, PLEASE WAIT...', 'You have entered Unknown.',
                                "Logging to 'eqlog.txt' is now *ON*.",
                                "Logging to 'eqlog.txt' is now *OFF*.",
                                '[malformed] You have entered Example One.'])
def test_transition_or_unknown_zone_prevents_handoff(tmp_path, body):
    h = fixture(tmp_path); t = h.create()
    h.append('You have entered Example One.'); t.poll()
    if body.startswith('[malformed]'):
        with h.log.open('a') as out: out.write(body+'\n')
    else: h.append(body, 2)
    with pytest.raises(ValueError, match='live-observed'):
        t.acquire()
    assert t.reader.zone_id is None


def test_partial_line_and_log_replacement_do_not_keep_zone(tmp_path):
    h = fixture(tmp_path); t = h.create(); h.append('You have entered Example One.')
    t.poll()
    with h.log.open('a') as out: out.write('[Sat Nov 14 06:00:02 2026] Your Location is 1,')
    with pytest.raises(ValueError, match='complete'):
        t.acquire()
    replacement = h.log.with_suffix('.replacement')
    replacement.write_text('[Sat Nov 14 06:00:03 2026] You have entered Example Two.\n')
    replacement.replace(h.log)
    with pytest.raises(ValueError, match='live-observed'):
        t.acquire()
    assert t.reader.zone_id is None


def test_binding_change_during_passive_poll_revokes_new_zone(tmp_path):
    h = fixture(tmp_path); t = h.create(); h.append('You have entered Example One.')
    original = t.reader.poll
    def changed(**kwargs):
        result = original(**kwargs); h.binding = ('changed',); return result
    t.reader.poll = changed
    with pytest.raises(ValueError, match='process'):
        t.poll()
    assert t.closed and t.reader.zone_id is None


def engine_fixture(tmp_path, retained):
    h = fixture(tmp_path)
    Engine, Settings, _ = retained
    e = make_route_session_engine(make_owner_nov12_engine(Engine))(
        Settings(game_dir=str(h.game), character='Probe', server='private'),
        lambda *_: None, lambda *_: None, measurement_only=True)
    e.selector.close()
    e.gate = SimpleNamespace(windows=lambda: [SimpleNamespace(id=42)],
        game_session=lambda: {'pid': 10, 'start_ticks': '100'})
    e.tail = e.make_tail(); e.tail.poll()
    h.traces = []; h.inherited_locations = []
    e.trace = lambda event, **values: h.traces.append((event, values))
    e.emit = lambda *_: None
    def forbidden(*args, **kwargs):
        pytest.fail('Zone tracking invoked a device, input or capture')
    e.send = e.hold = e.ensure_sender = e.ensure_pointer = forbidden
    e.gate.capture = forbidden
    e.location_reply = h.inherited_locations.append
    e.zone_changed = lambda *_: None  # Existing guide display is not new zone evidence.
    e.zone = 'Historical helper zone is untrusted'
    e.read_log()
    assert e.live_zone_tracker.reader.zone_id is None
    h.engine = e
    h.append('You have entered Example One.'); e.read_log()
    assert e.live_zone_tracker.reader.zone_id == 1
    return h


def test_actual_helper_handoff_survives_level_update_and_nested_log_pump(tmp_path, retained):
    h = engine_fixture(tmp_path, retained); e = h.engine
    tracker = e.live_zone_tracker
    e.settings.level += 1
    e.read_log()
    assert e.live_zone_tracker is tracker and tracker.reader.zone_id == 1
    lease = e.lease_current_zone(); cursor = lease.reader.tail.position
    h.append('Your Location is 4, 5, 6', 2); e.read_log()
    assert len(h.inherited_locations) == 1  # Base engine still receives its log.
    assert lease.reader.tail.position == cursor
    assert lease.reader.poll()[0].raw_coordinates == (4., 5., 6.)
    lease.release()
    assert e.sender is None and e.route_session_driver is None


@pytest.mark.parametrize('action', ['stop_action', 'stop_autopilot', 'post'])
def test_actual_helper_stop_before_driver_attachment_revokes_lease(tmp_path, retained, action):
    h = engine_fixture(tmp_path, retained); e = h.engine
    lease = e.lease_current_zone(); cursor = lease.reader.tail.position
    if action == 'post': e.post('settings', e.settings)
    else: getattr(e, action)('Owner stop')
    h.append('Your Location is 4, 5, 6', 2); e.read_log()
    assert lease.reader.tail.position == cursor
    with pytest.raises(ValueError, match='lease ended'): lease.check()
    lease.release()
    assert e.live_zone_tracker.reader.zone_id == 1 and e.sender is None


@pytest.mark.parametrize('competing', ['hotkey_test', 'supervised_motion', 'pointer',
                                    'route_session_driver', 'navigation_preflight'])
def test_actual_helper_refuses_competing_acquisition(tmp_path, retained, competing):
    h = engine_fixture(tmp_path, retained); e = h.engine
    setattr(e, competing, object())
    with pytest.raises(ValueError, match='Idle measurement'): e.lease_current_zone()
    assert e.live_zone_tracker.lease is None


def test_actual_helper_assist_and_changed_process_cannot_borrow_old_zone(tmp_path, retained):
    h = engine_fixture(tmp_path, retained); e = h.engine
    e.measurement_only = False
    with pytest.raises(ValueError, match='Idle measurement'): e.lease_current_zone()
    e.measurement_only = True
    lease = e.lease_current_zone()
    e.gate.game_session = lambda: {'pid': 10, 'start_ticks': '200'}
    e.read_log()
    assert not lease.active and e.live_zone_tracker.reader is not lease.reader
    assert e.live_zone_tracker.reader.zone_id is None
    lease.release()
