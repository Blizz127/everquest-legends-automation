"""Owner-started relative calibration using the existing helper and finite probes."""
from dataclasses import asdict
import time
from uuid import uuid4

from .navigation_phase import navigation_active
from .location_hotkey import OwnerLocationHotkey
from .motion_collection import MotionExperimentSession, MotionExperimentDriver
from .owner_input_observer import OwnerInputObserver
from .owner_location_hotkey_test import make_owner_nov12_engine as hotkey_engine, DEFAULT_OUTPUT
from .owner_motion_adapter import make_motion_collection_engine
from .owner_navigation_preflight import settings_identity, window_identity
from .scene_log_veto import SceneLogVeto
from .supervised_motion import SupervisedMotionExecutors
from .unbound_location_log import UnboundLocationReader


MOTION_JOB = 'supervised_motion_measurement'


def make_owner_nov12_engine(base_engine, *, clock=time.monotonic,
                           observer_factory=OwnerInputObserver, output_root=None, hotkey_output=None):
    base = make_motion_collection_engine(hotkey_engine(base_engine, clock=clock,
        observer_factory=observer_factory,
        output=DEFAULT_OUTPUT if hotkey_output is None else hotkey_output), output_root=output_root)

    class SupervisedMotionEngine(base):
        def __init__(self, *args, **kwargs):
            self.supervised_motion = None
            self.supervised_epoch = 0
            super().__init__(*args, **kwargs)

        def post(self, name, value=None):
            self.supervised_epoch += 1
            if name in self._supervised_job_names():
                value = dict(declaration=value, epoch=self.supervised_epoch,
                    generation=self.cancel_generation, settings=settings_identity(self.settings))
            return super().post(name, value)

        def _supervised_job_names(self):
            return (MOTION_JOB,)

        def _prepare_supervised_job(self, name):
            return None

        def _handoff_completed_motion(self, pending, session, record):
            # Ordinary motion measurement always finishes stopped. A concrete
            # route wrapper may adopt only its separate explicit owner job.
            return False

        def _cancel_supervised(self, reason):
            if self.supervised_motion is not None:
                self.supervised_motion['cancelled'] = str(reason)

        def stop_action(self, reason, *, keep_autopilot=False):
            self._cancel_supervised(reason)
            return super().stop_action(reason, keep_autopilot=keep_autopilot)

        def stop_autopilot(self, reason):
            self._cancel_supervised(reason)
            return super().stop_autopilot(reason)

        def _supervised_current(self, p, *, active):
            if (self.supervised_motion is not p or p['cancelled']
                    or self.supervised_epoch != p['epoch'] or self.cancel_generation != p['generation']
                    or settings_identity(self.settings) != p['settings'] or not self._motion_idle()
                    or self.sender is not p['sender'] or self.gate is not p['gate']
                    or window_identity(self.gate, require_focus=active) != p['window']
                    or not self.jobs.empty() or (active and self.cancelled)):
                raise ValueError('Supervised measurement cancelled or owner/game binding changed')
            p['binding'].check()
            veto = p['veto'].poll()
            if not veto.continuity_available or veto.reason is not None:
                raise ValueError('Measurement log veto: '+str(veto.reason))
            sample = p['observer'].sample()
            if active and (not sample.clear_at(clock()) or sample.topology_generation != p['topology']):
                raise ValueError('Owner activity or input topology changed during measurement')
            # Do not let observation callbacks restore or replace the request.
            if (p['epoch'] != self.supervised_epoch or p['generation'] != self.cancel_generation
                    or self.supervised_motion is not p or p['cancelled']
                    or self.sender is not p['sender'] or self.gate is not p['gate']
                    or settings_identity(self.settings) != p['settings']
                    or not self._motion_idle() or not self.jobs.empty()
                    or window_identity(self.gate, require_focus=active) != p['window']):
                raise ValueError('Measurement revoked during observation')

        def _close_supervised(self, reason):
            p, self.supervised_motion = self.supervised_motion, None
            if p is None:
                return
            observer = p.get('observer')
            if observer is not None:
                try:
                    observer.close()
                except Exception as error:
                    reason = str(reason)+'; observer cleanup: '+str(error)
            self.cancelled = True
            self.trace('supervised_motion_finished', reason=str(reason),
                setup_record_id=p.get('setup_record_id'), movement_clearance='owner_declared',
                zone_binding_verified=False, route_accepted=False)
            self.emit('Motion measurement stopped: '+str(reason)+' · no route enabled.')

        def handle_job(self, name, value):
            if name not in self._supervised_job_names():
                self._cancel_supervised('another helper job requested')
                return super().handle_job(name, value)
            if self.supervised_motion is not None or self.motion_collection_driver is not None:
                self._cancel_supervised('another measurement requested')
                self._cancel_motion('another measurement requested')
                self.emit('Wait for the current measurement to stop before starting another.')
                return
            if (not isinstance(value, dict) or set(value) != {'declaration', 'epoch', 'generation', 'settings'}
                    or value['epoch'] != self.supervised_epoch or value['generation'] != self.cancel_generation
                    or value['settings'] != settings_identity(self.settings)):
                return
            declaration = value['declaration']
            if (not isinstance(declaration, dict) or set(declaration) != {'open_flat_clear'}
                    or declaration['open_flat_clear'] is not True or not self._motion_idle()):
                self.emit('Motion measurement requires stopped measurement mode and your open-ground confirmation.')
                return
            try:
                continuation = self._prepare_supervised_job(name)
                record = self.last_hotkey_test
                window = window_identity(self.gate, require_focus=False)
                if (not isinstance(record, dict) or record.get('outcome') != 'observed_location'
                        or tuple(record['window_identity']) != window
                        or record['expected_character'] != self.settings.character
                        or record['expected_server'] != self.settings.server):
                    raise ValueError('Run Test /location hotbutton successfully in this helper/session first')
                binding = OwnerLocationHotkey(**record['owner_setup'])
                binding.check()
                sender = self.sender
                if sender is None or sender.held or sender.unfinished or sender.dismissed:
                    raise ValueError('Idle tested hotbutton sender required')
                p = dict(value, binding=binding, sender=sender, gate=self.gate, window=window,
                    setup_record_id=record['record_id'], cancelled=None, observer=None,
                    stage='countdown', due=clock()+4., job=name, continuation=continuation)
                self.supervised_motion = p
                p['observer'] = observer_factory(helper_ui=sender.ui, clock=clock)
                p['topology'] = p['observer'].sample().topology_generation
                p['veto'] = SceneLogVeto(self.log_path(), expected_character=self.settings.character,
                    expected_server=self.settings.server, cancel_generation=self.cancel_generation, clock=clock)
                self._supervised_current(p, active=False)
                self.cancelled = False  # Only this fresh, unchanged explicit owner job rearms.
                self.emit('Motion measurement in 4 seconds: focus EverQuest on wide open flat ground, '
                          'close chat, clear target, turn melee off and release keys. '
                          'Four short forward presses and three turns; F9/F11 cancel.')
            except Exception as error:
                self._close_supervised(str(error))
                self.emit('Motion measurement unavailable: '+str(error))

        def _start_supervised(self, p):
            self._supervised_current(p, active=True)
            import navigation  # Actual retained bearing and calibration fitter.
            reader = UnboundLocationReader(self.log_path(), expected_character=self.settings.character,
                                          expected_server=self.settings.server)
            session = MotionExperimentSession(reader, zone_id=None, zone_display_name=None,
                zone_short_name=None, relative=True, generation=self.cancel_generation,
                generation_reader=lambda: self.cancel_generation,
                mode_reader=lambda: 'measurement' if navigation_active(self) else 'off',
                binding_reader=lambda: (*settings_identity(self.settings),
                                       *window_identity(self.gate, require_focus=False)),
                record_id='owner-relative-motion-'+uuid4().hex, horizontal_error=.01,
                legacy=navigation, clock=clock, stop_lock=self.g0_stop_lock)
            session.executor_events.append(dict(kind='owner_supervised_setup',
                location_test_record_id=p['setup_record_id'], owner_declaration=dict(p['declaration']),
                hotkey=asdict(p['binding']), independent_clearance_verified=False,
                horizontal_error_assumed=.01, movement_clearance='owner_declared_open_flat_ground'))
            executors = SupervisedMotionExecutors(self, session, hotkey=p['binding'], owner_input=p['observer'],
                check_current=lambda: self._supervised_current(p, active=True))
            driver = MotionExperimentDriver(session, request_location=executors.request_location,
                                            run_pulse=executors.run_pulse)
            self.attach_motion_collection(driver)
            p['session'] = session
            p['stage'] = 'active'
            self.emit('Supervised motion measurement active · seven bounded pulses · F9/F11 stop.')

        def autopilot_tick(self, now):
            p = self.supervised_motion
            if p is not None:
                try:
                    self._supervised_current(p, active=p['stage'] == 'active' or clock() >= p['due'])
                    if p['stage'] == 'countdown' and clock() >= p['due']:
                        self._start_supervised(p)
                except Exception as error:
                    self._cancel_motion(str(error))
                    if self.motion_collection_driver is not None and self.motion_collection_driver.busy:
                        raise
                    self._finish_motion(str(error))
                    self._close_supervised(str(error))
            result = super().autopilot_tick(now)
            if self.supervised_motion is not None and self.supervised_motion['stage'] == 'active' and self.motion_collection_driver is None:
                with self.g0_stop_lock:
                    p = self.supervised_motion
                    session, record = p.get('session'), self.last_motion_collection_result
                    adopted = False
                    try:
                        if (isinstance(session,MotionExperimentSession) and session.phase=='complete'
                                and isinstance(record,dict) and record.get('outcome')=='complete'
                                and record.get('record_id')==session.record_id
                                and record.get('estimate') is session.result):
                            self._supervised_current(p,active=True)
                            session._check()
                            adopted = self._handoff_completed_motion(p,session,record)
                            if adopted and self.supervised_motion is p:
                                raise ValueError('Motion continuation did not adopt its observation scope')
                    except Exception as error:
                        self._close_supervised('Continuation unavailable: '+str(error))
                        self.emit('Motion continuation stopped: '+str(error))
                    if not adopted:
                        self._close_supervised('finite experiment finished; see saved result')
            return result

        def run(self):
            try:
                return super().run()
            finally:
                self._close_supervised('helper exited')

    return SupervisedMotionEngine

