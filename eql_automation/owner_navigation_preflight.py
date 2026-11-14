"""Read-only measurement preflight in the existing restricted owner helper.

This attaches real input observation to the helper lifecycle. It neither
constructs a movement permit nor claims that live UI/zone/ground providers
exist. No sender is created and no game command, capture or hold is requested.
"""
from __future__ import annotations

from dataclasses import asdict
import math
import time

from .owner_g0_watchdog import make_owner_nov12_engine as restricted_engine
from .owner_input_observer import OwnerInputObservation, OwnerInputObserver


PREFLIGHT_JOB = 'nav_preflight_later'
MISSING_PROVIDERS = ('calibrated_ui_scene', 'current_zone_binding',
                     'aligned_ground_and_height', 'measured_speed_and_drift',
                     'checked_live_route_sender')


def window_identity(gate, *, require_focus):
    windows = gate.windows()
    session = gate.game_session()
    if (len(windows) != 1 or not isinstance(session, dict)
            or set(session) != {'pid', 'start_ticks'}
            or type(windows[0].id) is not int or windows[0].id <= 0
            or type(session['pid']) is not int or session['pid'] <= 0
            or not isinstance(session['start_ticks'], str)
            or not session['start_ticks'].isascii() or not session['start_ticks'].isdigit()
            or int(session['start_ticks']) <= 0):
        raise ValueError('one identifiable game window/process required')
    if require_focus:
        focused = gate.focused_window()
        if (focused is None or focused.id != windows[0].id or gate.controls_ready() is not True):
            raise ValueError('game focus or helper hotkey readiness missing')
    return (windows[0].id, session['pid'], int(session['start_ticks']))


def settings_identity(settings):
    return (id(settings), settings.game_dir, settings.character, settings.server, settings.level)


def make_owner_nov12_engine(base_engine, *, observer_factory=OwnerInputObserver,
                           clock=time.monotonic):
    class NavigationPreflightEngine(restricted_engine(base_engine)):
        def __init__(self, *args, **kwargs):
            self.navigation_preflight = None
            self.navigation_preflight_epoch = 0
            super().__init__(*args, **kwargs)

        def post(self, name, value=None):
            # GUI thread only revokes a token. Descriptor work stays on the
            # engine thread, including when a post races an input scan.
            self.navigation_preflight_epoch += 1
            if name == PREFLIGHT_JOB and value is None:
                value = {'generation': self.cancel_generation,
                         'epoch': self.navigation_preflight_epoch,
                         'settings': settings_identity(self.settings)}
            return super().post(name, value)

        def _preflight_idle(self):
            return (self.measurement_only is True and not self.active and not self.preparing
                    and not self.stopping and self.autopilot is None and self.pointer is None
                    and self.deferred is None and self.loc_request is None and self.loc_wanted is None
                    and self.recorder is None and not self.keys and not self.command_recovery_pending
                    and (self.sender is None or not self.sender.held and not self.sender.unfinished))

        def _finish_preflight(self, outcome, reason, *, sample=None, input_clear=False, emit=True):
            pending, self.navigation_preflight = self.navigation_preflight, None
            if pending is None:
                return
            observer = pending.get('observer')
            if observer is not None:
                try:
                    observer.close()
                except Exception as error:
                    outcome, reason, input_clear = 'refused', 'input cleanup failed: '+str(error), False
            if outcome == 'observed' and (
                    self.navigation_preflight_epoch != pending['epoch']
                    or self.cancel_generation != pending['generation']
                    or self.stopping or settings_identity(self.settings) != pending['settings']):
                outcome, reason, input_clear = 'cancelled', 'request revoked before result', False
            self.trace('nav_preflight_result', outcome=outcome, reason=reason,
                       request_generation=pending['generation'], request_epoch=pending['epoch'],
                       window_identity=pending['window'],
                       baseline=None if pending.get('baseline') is None else asdict(pending['baseline']),
                       input_observation=None if sample is None else asdict(sample),
                       input_sample_clear=input_clear, missing_providers=MISSING_PROVIDERS,
                       game_input_sent=False, movement_authorized=False, real_client_accepted=False)
            if emit:
                self.emit('Read-only navigation check: '+reason+
                          ' · movement unavailable: live UI, zone/ground and speed observations still missing.')

        def stop_action(self, reason, *, keep_autopilot=False):
            self.navigation_preflight_epoch += 1
            self._finish_preflight('cancelled', 'stopped', emit=False)
            return super().stop_action(reason, keep_autopilot=keep_autopilot)

        def stop_autopilot(self, reason):
            self.navigation_preflight_epoch += 1
            self._finish_preflight('cancelled', 'measurement stopped', emit=False)
            return super().stop_autopilot(reason)

        def handle_job(self, name, value):
            if name != PREFLIGHT_JOB:
                self.navigation_preflight_epoch += 1
                self._finish_preflight('cancelled', 'another helper job requested', emit=False)
                return super().handle_job(name, value)
            self._finish_preflight('cancelled', 'superseded by another preflight', emit=False)
            if (not isinstance(value, dict) or set(value) != {'generation', 'epoch', 'settings'}
                    or any(type(value[k]) is not int for k in ('generation','epoch'))
                    or value['generation'] != self.cancel_generation
                    or value['epoch'] != self.navigation_preflight_epoch
                    or value['settings'] != settings_identity(self.settings)):
                return
            if not self._preflight_idle():
                self.emit('Read-only navigation check requires stopped measurement mode with no pending work.')
                return
            try:
                now = clock()
                if not math.isfinite(now):
                    raise ValueError('invalid observation clock')
                identity = window_identity(self.gate, require_focus=False)
                self.navigation_preflight = {
                    **value, 'window': identity, 'settings': settings_identity(self.settings),
                    'sender': self.sender, 'helper_ui': None if self.sender is None else self.sender.ui,
                    'observer': None, 'baseline': None,
                    'due': now + 4., 'expires': now + 6., 'last_at': now,
                }
                self.trace('nav_preflight_queued', generation=value['generation'], epoch=value['epoch'],
                           game_input_sent=False, movement_authorized=False)
                self.emit('Read-only navigation check in 4 seconds: focus EverQuest, then release keys. '
                          'F9/F11 cancel; this check does not move or cast.')
            except (ValueError, OSError, RuntimeError) as error:
                self.emit('Read-only navigation check unavailable: '+str(error))

        def _preflight_binding(self, pending, now, *, focused):
            if (not math.isfinite(now) or not pending['last_at'] <= now <= pending['expires']
                    or self.navigation_preflight is not pending or not self._preflight_idle()
                    or self.cancel_generation != pending['generation']
                    or self.navigation_preflight_epoch != pending['epoch']
                    or self.sender is not pending['sender']
                    or (self.sender is not None and self.sender.ui is not pending['helper_ui'])
                    or settings_identity(self.settings) != pending['settings']
                    or window_identity(self.gate, require_focus=focused) != pending['window']):
                raise ValueError('observation expired or helper/game binding changed')
            pending['last_at'] = now

        def _service_preflight(self):
            pending = self.navigation_preflight
            if pending is None:
                return
            try:
                now = clock()
                self._preflight_binding(pending, now, focused=now >= pending['due'])
                if now < pending['due']:
                    return
                if pending['observer'] is None:
                    # Never ensure_sender(): observing must not create a virtual device.
                    ui = None if self.sender is None else self.sender.ui
                    pending['observer'] = observer_factory(helper_ui=ui, clock=clock)
                observation = pending['observer'].sample()
                finished = clock()
                self._preflight_binding(pending, finished, focused=True)
                if (not isinstance(observation, OwnerInputObservation)
                        or not now <= observation.started_at <= observation.finished_at <= finished):
                    raise ValueError('input observation timing or type invalid')
                if pending['baseline'] is None:
                    pending['baseline'] = observation
                    pending['due'] = finished + .025
                    return
                stable = observation.topology_generation == pending['baseline'].topology_generation
                clear = stable and observation.clear_at(finished)
                self._finish_preflight('observed', 'input sample clear' if clear else
                                       'input coverage or activity requires review: '+observation.reason,
                                       sample=observation, input_clear=clear)
            except Exception as error:
                self._finish_preflight('refused', str(error))

        def autopilot_tick(self, now):
            # The real engine calls this after draining queued jobs. No sleep,
            # recursive pump or inherited deferred-generation restamping.
            result = super().autopilot_tick(now)
            self._service_preflight()
            return result

        def run(self):
            try:
                return super().run()
            finally:
                self._finish_preflight('cancelled', 'helper exited', emit=False)

    NavigationPreflightEngine.__name__ = 'NavigationPreflightEngine'
    return NavigationPreflightEngine
