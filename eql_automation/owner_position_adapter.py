"""Owner-invoked position/UI collection inside the retained rotation helper.

The helper stays disarmed. Manual chat entry is observed, never typed. Every
saved position remains unbound and cannot become a navigation permit.
"""
from pathlib import Path
import time

from .owner_navigation_preflight import make_owner_nov12_engine as preflight_engine
from .owner_navigation_preflight import settings_identity, window_identity
from .owner_ui_observation import DEFAULT_OUTPUT, capture_focused_ui
from .position_observation import StationaryPositionSession

POSITION_JOB = 'observe_position'


def capture_with_helper(**kwargs):
    from uilayout import UiLayout
    return capture_focused_ui(layout_loader=UiLayout.load, include_chat=False, **kwargs)


def make_owner_nov12_engine(base_engine, *, capture_fn=capture_with_helper,
                           clock=time.monotonic, output=DEFAULT_OUTPUT,
                           private_root=DEFAULT_OUTPUT):
    class PositionObservationEngine(preflight_engine(base_engine, clock=clock)):
        def __init__(self, *args, **kwargs):
            self.position_observation = None
            self.position_epoch = 0
            self.position_chat_stop = None
            super().__init__(*args, **kwargs)

        def post(self, name, value=None):
            self.position_epoch += 1
            if name == POSITION_JOB and value is None:
                value = {'generation': self.cancel_generation, 'epoch': self.position_epoch,
                         'settings': settings_identity(self.settings)}
            return super().post(name, value)

        def _position_idle(self):
            # Ordinary owner typing is expected. A sender is forbidden so the
            # inherited chat-stop cleanup cannot write even key releases.
            return (self.measurement_only is True and not self.active and not self.preparing
                    and not self.stopping and self.sender is None and self.pointer is None
                    and self.autopilot is None and self.deferred is None
                    and self.loc_request is None and self.loc_wanted is None
                    and self.recorder is None and not self.command_recovery_pending)

        def _position_current(self, pending):
            if (self.position_observation is not pending or not self._position_idle()
                    or self.position_epoch != pending['epoch']
                    or self.cancel_generation != pending['generation']
                    or settings_identity(self.settings) != pending['settings']
                    or self.gate is not pending['gate']
                    or window_identity(self.gate, require_focus=False) != pending['window']):
                raise ValueError('Position collection cancelled or helper/game binding changed')

        def _end_position(self, outcome, reason, *, path=None, emit=True):
            pending, self.position_observation = self.position_observation, None
            if pending is None: return
            if pending.get('session') is not None:
                pending['session'].cancel()
            self.trace('position_observation_result', outcome=outcome, reason=reason,
                       output_path=None if path is None else str(path), game_input_sent=False,
                       movement_authorized=False, real_client_accepted=False)
            if emit: self.emit('Position observation: '+reason+' · movement unavailable.')

        def handle_job(self, name, value):
            if name != POSITION_JOB:
                self.position_epoch += 1
                self._end_position('cancelled', 'another helper job requested', emit=False)
                return super().handle_job(name, value)
            self._end_position('cancelled', 'superseded', emit=False)
            self._finish_preflight('cancelled', 'position collection requested', emit=False)
            if (not isinstance(value, dict) or set(value) != {'generation','epoch','settings'}
                    or type(value['generation']) is not int or type(value['epoch']) is not int
                    or value['epoch'] != self.position_epoch
                    or value['generation'] != self.cancel_generation
                    or value['settings'] != settings_identity(self.settings)):
                return
            if not self._position_idle():
                self.emit('Position observation requires a fresh, stopped measurement helper; '
                          'close other helpers and relaunch before collecting.')
                return
            try:
                pending = {**value, 'gate': self.gate,
                           'window': window_identity(self.gate, require_focus=False), 'session': None}
                self.position_observation = pending
                settings = self.settings
                pending['session'] = StationaryPositionSession(gate=self.gate,
                    game=Path(settings.game_dir), character=settings.character, server=settings.server,
                    output=output, private_root=private_root, capture_fn=capture_fn, clock=clock,
                    still_current=lambda: self._position_current(pending))
                self.trace('position_observation_started', game_input_sent=False,
                           movement_authorized=False, timeout_seconds=60)
                self.emit('Observe position: stand still, select Current Zone on the map, then '
                          'type /location once in EverQuest and close chat. Keep game focused. '
                          'F9/F11 cancel; no input is sent. Waiting up to 60 seconds.')
            except Exception as error:
                self._end_position('refused', str(error))

        def chat_input_opened(self):
            # Explicit pinned-engine hook, not a reason-string exception.
            # Inherited stop still disarms rotation and invalidates queued work.
            pending = self.position_observation
            self.position_chat_stop = (pending if pending is not None
                and pending.get('session') is not None
                and pending['session'].phase in ('waiting','settling') else None)
            try:
                return super().chat_input_opened()
            finally:
                self.position_chat_stop = None

        def stop_action(self, reason, *, keep_autopilot=False):
            pending = self.position_observation
            preserve = pending is not None and self.position_chat_stop is pending
            if preserve:
                try: self._position_current(pending)
                except ValueError: preserve = False
            if not preserve:
                self.position_epoch += 1
                self._end_position('cancelled', 'stopped', emit=False)
            try:
                result = super().stop_action(reason, keep_autopilot=keep_autopilot)
            except Exception:
                self._end_position('cancelled', 'stop cleanup failed', emit=False)
                raise
            if preserve:
                # Only the exact, synchronous owner-chat stop may rebind this
                # input-free diagnostic. Other jobs/stops keep their old token.
                if self.position_observation is pending and self.position_epoch == pending['epoch']:
                    pending['generation'] = self.cancel_generation
                    try: self._position_current(pending)
                    except ValueError: self._end_position('cancelled', 'binding changed during chat stop', emit=False)
                    else:
                        self.emit('Rotation remains OFF. Position observation is waiting for '
                                  'your /location; close chat and keep the map visible. F9/F11 cancel.')
                else:
                    self._end_position('cancelled', 'request revoked during chat stop', emit=False)
            return result

        def stop_autopilot(self, reason):
            self.position_epoch += 1
            self._end_position('cancelled', 'measurement stopped', emit=False)
            return super().stop_autopilot(reason)

        def autopilot_tick(self, now):
            result = super().autopilot_tick(now)
            pending = self.position_observation
            if pending is not None:
                try:
                    self._position_current(pending)
                    phase = pending['session'].phase
                    path = pending['session'].tick()
                    if path is not None:
                        self._position_current(pending)
                        self._end_position('saved', 'saved '+str(path), path=path)
                    elif phase == 'waiting' and pending['session'].phase == 'settling':
                        self.emit('Location received. Stay still with chat closed and the '
                                  'Current Zone map visible; collecting in two seconds. F9/F11 cancel.')
                except Exception as error:
                    self._end_position('refused', str(error))
            return result

        def run(self):
            try: return super().run()
            finally: self._end_position('cancelled', 'helper exited', emit=False)

    PositionObservationEngine.__name__ = 'PositionObservationEngine'
    return PositionObservationEngine
