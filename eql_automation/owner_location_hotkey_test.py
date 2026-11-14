"""Owner-started stationary hotbutton test in the existing measurement helper."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from uuid import uuid4

from .location_hotkey import HOTKEY_CODES, OwnerLocationHotkey, send_location_hotkey
from .owner_input_observer import OwnerInputObserver
from .owner_navigation_preflight import settings_identity, window_identity
from .owner_position_adapter import make_owner_nov12_engine as position_engine
from .unbound_location_log import UnboundLocationReader


HOTKEY_TEST_JOB = 'test_location_hotkey'
DEFAULT_OUTPUT = Path.home()/'.local/share/eql-automation/location-hotkey-tests'


def configuration_paths(game, character, server):
    """Use the actual saved character INI; never invent the _LO suffix."""
    exact = game/f'{character}_{server}.ini'
    candidates = [exact] if exact.is_file() else sorted(game.glob(f'{character}_{server}_*.ini'))
    if len(candidates) != 1:
        raise ValueError('Exactly one saved character configuration is required')
    return game/'eqclient.ini', candidates[0]


def make_owner_nov12_engine(base_engine, *, clock=time.monotonic,
                           observer_factory=OwnerInputObserver, output=DEFAULT_OUTPUT):
    class HotkeyTestEngine(position_engine(base_engine, clock=clock)):
        def __init__(self, *args, **kwargs):
            self.hotkey_test = None
            self.hotkey_test_epoch = 0
            self.last_hotkey_test = self.last_hotkey_test_path = None
            super().__init__(*args, **kwargs)

        def post(self, name, value=None):
            self.hotkey_test_epoch += 1
            if name == HOTKEY_TEST_JOB:
                value = dict(selection=value, generation=self.cancel_generation,
                             epoch=self.hotkey_test_epoch, settings=settings_identity(self.settings))
            return super().post(name, value)

        def _hotkey_idle(self):
            return (self.measurement_only is True and not self.active and not self.preparing
                and not self.stopping and not self.command_recovery_pending
                and not any(getattr(self, name, None) is not None for name in
                    ('autopilot', 'deferred', 'loc_request', 'loc_wanted', 'recorder', 'pointer',
                     'position_observation', 'navigation_preflight', 'route_session_driver',
                     'motion_collection_driver')))

        def _cancel_hotkey_test(self, reason):
            if self.hotkey_test is not None:
                self.hotkey_test['cancelled'] = str(reason)

        def stop_action(self, reason, *, keep_autopilot=False):
            self._cancel_hotkey_test(reason)
            return super().stop_action(reason, keep_autopilot=keep_autopilot)

        def stop_autopilot(self, reason):
            self._cancel_hotkey_test(reason)
            return super().stop_autopilot(reason)

        def _hotkey_current(self, pending, *, focused=False, initializing=False):
            if (self.hotkey_test is not pending or pending['cancelled']
                    or pending['epoch'] != self.hotkey_test_epoch
                    or pending['generation'] != self.cancel_generation
                    or pending['settings'] != settings_identity(self.settings)
                    or not self._hotkey_idle() or not self.jobs.empty()
                    or self.gate is not pending['gate']
                    or window_identity(self.gate, require_focus=focused) != pending['window']
                    or (not initializing and (self.cancelled or self.sender is not pending['sender']))):
                raise ValueError('Hotbutton test cancelled or helper/game binding changed')

        def _observe_hotkey_zone(self, pending):
            return None  # Route-capable wrappers may inspect the visible map.

        def _finish_hotkey_test(self, outcome, reason):
            pending, self.hotkey_test = self.hotkey_test, None
            if pending is None:
                return
            observer = pending.get('observer')
            if observer is not None:
                try:
                    observer.close()
                except Exception as error:
                    outcome, reason = 'refused', str(reason)+'; observer close failed: '+str(error)
            # All test outcomes are stopped; only another explicit owner action
            # may start work. No Escape, attack-off or command cleanup is sent.
            self.cancelled = True
            raw = None if pending.get('fix') is None else asdict(pending['fix'])
            if raw is not None:
                raw['log_local_time'] = pending['fix'].log_local_time.isoformat()
            binding = pending.get('binding')
            record = dict(format='eql-owner-location-hotkey-test-v1', outcome=outcome, reason=str(reason),
                recorded_utc=datetime.now(timezone.utc).isoformat(), record_id=pending['id'],
                expected_character=pending['character'], expected_server=pending['server'],
                window_identity=pending['window'],
                owner_setup=None if binding is None else asdict(binding),
                configured_command='/location', macro_contents_mechanically_verified=False,
                location=raw, input_events=pending['events'],
                game_key_attempted=pending['fired'], chat_keys_sent=False,
                movement_requested=False, real_route_accepted=False,
                request_correlation_verified=False)
            if pending.get('current_zone_observation') is not None:
                record['current_zone_observation'] = pending['current_zone_observation']
            self.last_hotkey_test, self.last_hotkey_test_path = record, None
            note = ''
            try:
                root = Path(output).expanduser().resolve()
                if (root.is_relative_to(Path(self.settings.game_dir).resolve())
                        or root.is_relative_to((Path.home()/'Games/everquest-legends').resolve())):
                    raise ValueError('Test evidence must stay outside the game/prefix')
                root.mkdir(parents=True, exist_ok=True, mode=0o700)
                path = root/(pending['id']+'.json')
                with path.open('x') as stream:
                    json.dump(record, stream, indent=2, sort_keys=True, allow_nan=False)
                    stream.write('\n')
                path.chmod(0o600)
                self.last_hotkey_test_path = path
                note = ' · saved '+str(path)
            except (OSError, ValueError, TypeError) as error:
                note = ' · report retained in memory; save failed: '+str(error)
            self.trace('location_hotkey_test_result', **record,
                       saved_path=None if self.last_hotkey_test_path is None else str(self.last_hotkey_test_path))
            self.emit('Location hotbutton: '+str(reason)+note+' · stopped; movement remains disabled.')

        def handle_job(self, name, value):
            if name != HOTKEY_TEST_JOB:
                self._cancel_hotkey_test('another helper job requested')
                return super().handle_job(name, value)
            if self.hotkey_test is not None:
                self._cancel_hotkey_test('another hotbutton test requested')
                self.emit('Current test cancelled. Wait for it to stop before starting another.')
                return
            if (not isinstance(value, dict) or set(value) != {'selection', 'generation', 'epoch', 'settings'}
                    or value['epoch'] != self.hotkey_test_epoch or value['generation'] != self.cancel_generation
                    or value['settings'] != settings_identity(self.settings)):
                return
            choice = value['selection']
            if (not isinstance(choice, dict) or set(choice) != {'key_name', 'confirmed'}
                    or choice['confirmed'] is not True or choice['key_name'] not in HOTKEY_CODES):
                self.emit('Choose your configured key and confirm its single /location hotbutton first.')
                return
            if not self._hotkey_idle() or (self.sender is not None and
                    (self.sender.held or self.sender.unfinished or self.sender.dismissed)):
                self.emit('Stop other helper work and close any game chat draft before this test.')
                return
            try:
                pending = dict(value, id='location-hotkey-'+uuid4().hex, gate=self.gate,
                    window=window_identity(self.gate, require_focus=False), cancelled=None,
                    stage='initializing', fired=False, busy=False, events=[], observer=None, fix=None,
                    character=self.settings.character, server=self.settings.server)
                self.hotkey_test = pending
                paths = configuration_paths(Path(self.settings.game_dir), self.settings.character, self.settings.server)
                pending['binding'] = OwnerLocationHotkey.configured(choice['key_name'],
                    confirmation_id=pending['id'], configuration_paths=paths)
                pending['sender'] = self.ensure_sender()
                self.pump()  # Consume F9 during the sender's discovery delay.
                self._hotkey_current(pending, initializing=True)
                if pending['sender'] is not self.sender or self.sender.held or self.sender.unfinished:
                    raise ValueError('Sender changed or retained unfinished input')
                pending['observer'] = observer_factory(helper_ui=self.sender.ui, clock=clock)
                pending['observer'].sample()  # Baseline before the focus countdown.
                self._hotkey_current(pending, initializing=True)
                # This explicit owner job may rearm after a previous Stop, but
                # never after a changed request/generation during initialization.
                self.cancelled = False
                pending.update(stage='countdown', due=clock()+4., expires=clock()+8.)
                pending['reader'] = UnboundLocationReader(self.log_path(),
                    expected_character=self.settings.character, expected_server=self.settings.server)
                self.emit('Location hotbutton test in 4 seconds: focus EverQuest, close chat, '
                          'stand still and release keys. One '+choice['key_name']+
                          ' press only; F9/F11 cancel. No movement or fallback typing.')
            except Exception as error:
                self._finish_hotkey_test('refused', str(error))
                if self.hotkey_test is None and self.last_hotkey_test is None:
                    self.emit('Location hotbutton test unavailable: '+str(error))

        def _service_hotkey_test(self):
            pending = self.hotkey_test
            if pending is None:
                return
            if pending['busy']:
                self._hotkey_current(pending, focused=True)
                return
            try:
                focused = pending['stage'] != 'countdown' or clock() >= pending['due']
                self._hotkey_current(pending, focused=focused)
                pending['binding'].check()
                if clock() > pending['expires']:
                    raise ValueError('No single fresh location reply before the test timeout')
                replies = pending['reader'].poll(now=clock())
                if pending['reader'].tail.partial:
                    raise ValueError('Incomplete log line during hotbutton test')
                if pending['stage'] == 'countdown':
                    if replies:
                        raise ValueError('Location arrived before the test key; not attributable')
                    sample = pending['observer'].sample()  # Focus changes are allowed before due.
                    if clock() < pending['due']:
                        return
                    if not sample.clear_at(clock()):
                        raise ValueError('Release keys and mouse before the test countdown ends')
                    pending['stage'], pending['busy'], pending['fired'] = 'sending', True, True
                    try:
                        receipt = send_location_hotkey(pending['sender'], binding=pending['binding'],
                            owner_input=pending['observer'], lock=self.g0_stop_lock, clock=clock,
                            expires_at=clock()+2.5,
                            ensure_current=lambda: self._hotkey_current(pending, focused=True),
                            cancel=self._cancel_hotkey_test, pump=self.pump,
                            record_event=pending['events'].append)
                    finally:
                        pending['busy'] = False
                    self._hotkey_current(pending, focused=True)
                    pending.update(stage='reply', receipt=receipt, expires=receipt.released_at+2.5)
                    self.emit('Location key released; waiting for one fresh position reply. F9/F11 cancel.')
                    return
                sample = pending['observer'].sample()
                if not sample.clear_at(clock()):
                    raise ValueError('Owner activity while waiting for the location reply')
                self._hotkey_current(pending, focused=True)
                if replies:
                    if len(replies) != 1 or pending['fix'] is not None:
                        raise ValueError('Multiple location replies; test is ambiguous')
                    fix = replies[0]
                    if (abs((datetime.now()-fix.log_local_time).total_seconds()) > 3
                            or fix.received_monotonic < pending['receipt'].released_at):
                        raise ValueError('Location reply timestamp is not fresh')
                    pending.update(stage='settling', fix=fix, settle_until=clock()+.35)
                if pending['stage'] == 'settling' and clock() >= pending['settle_until']:
                    pending['busy'] = True
                    try:
                        pending['current_zone_observation'] = self._observe_hotkey_zone(pending)
                        self._hotkey_current(pending, focused=True)
                    finally:
                        pending['busy'] = False
                    self._finish_hotkey_test('observed_location', 'One fresh location reply observed')
            except Exception as error:
                self._finish_hotkey_test('refused', str(error))

        def autopilot_tick(self, now):
            result = super().autopilot_tick(now)
            self._service_hotkey_test()
            return result

        def run(self):
            try:
                return super().run()
            finally:
                self._finish_hotkey_test('cancelled', 'helper exited')

    return HotkeyTestEngine
