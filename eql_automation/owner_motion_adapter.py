"""Engine-tick attachment for an explicitly constructed measurement driver.

No owner job/hotkey constructs a driver and no default executors exist. This
attachment is for the current integration work; it does not enable calibration
in the staged assist/observation helpers or relax their input restrictions.
"""
from .motion_collection import MotionExperimentDriver, CollectionStopped
import json
from pathlib import Path
from uuid import uuid4


def make_motion_collection_engine(base_engine, *, output_root=None):
    output_root = Path(output_root) if output_root is not None else (
        Path.home()/'.local/share/eql-automation/motion-measurements')
    class MotionCollectionEngine(base_engine):
        def __init__(self, *args, **kwargs):
            self.motion_collection_driver = None
            self.motion_collection_epoch = 0
            self.last_motion_collection_result = None
            self.last_motion_collection_path = None
            super().__init__(*args, **kwargs)

        def attach_motion_collection(self, driver):
            epoch = self.motion_collection_epoch
            if (not isinstance(driver, MotionExperimentDriver)
                    or self.motion_collection_driver is not None
                    or not self._motion_idle() or not self.jobs.empty()
                    or driver.session.lock is not getattr(self, 'g0_stop_lock', None)):
                raise ValueError('A stopped measurement helper and explicit checked driver are required')
            driver.session._check()
            self.motion_collection_driver = driver
            if epoch != self.motion_collection_epoch or not self.jobs.empty():
                driver.session.cancel('helper job raced measurement attachment')
                self.motion_collection_driver = None
                raise ValueError('helper job raced measurement attachment')

        def _motion_idle(self):
            return (self.measurement_only is True and not self.active and not self.preparing
                    and not self.stopping and not self.command_recovery_pending
                    and not any(getattr(self, field, None) is not None for field in
                                ('autopilot', 'deferred', 'loc_request', 'loc_wanted', 'recorder',
                                 'position_observation', 'navigation_preflight')))

        def _cancel_motion(self, reason):
            if self.motion_collection_driver is not None:
                self.motion_collection_driver.session.cancel(reason)

        def post(self, name, value=None):
            self.motion_collection_epoch += 1
            self._cancel_motion('another helper job requested')
            return super().post(name, value)

        def stop_action(self, reason, *, keep_autopilot=False):
            self._cancel_motion(reason)
            return super().stop_action(reason, keep_autopilot=keep_autopilot)

        def stop_autopilot(self, reason):
            self._cancel_motion(reason)
            return super().stop_autopilot(reason)

        def _finish_motion(self, reason):
            driver, self.motion_collection_driver = self.motion_collection_driver, None
            if driver is None:
                return
            if driver.session.phase != 'complete':
                driver.session.cancel(reason)
            record = driver.session.snapshot()
            self.last_motion_collection_result = record
            self.last_motion_collection_path = None
            try:
                root = output_root.expanduser().resolve()
                game = Path(self.settings.game_dir).resolve()
                protected = (Path.home()/'Games/everquest-legends').resolve()
                if root.is_relative_to(game) or root.is_relative_to(protected):
                    raise ValueError('motion evidence output must be outside the game/prefix')
                root.mkdir(parents=True,exist_ok=True,mode=0o700)
                path = root/('motion-'+uuid4().hex+'.json')
                payload = json.dumps(record,indent=2,allow_nan=False)+'\n'
                with path.open('x') as output:
                    output.write(payload)
                path.chmod(0o600)
                self.last_motion_collection_path = path
                persistence = 'saved '+str(path)
            except (OSError,ValueError,TypeError) as error:
                persistence = 'save unavailable; record retained in memory: '+str(error)
            self.trace('motion_collection_result', record=record,
                       saved_path=None if self.last_motion_collection_path is None else str(self.last_motion_collection_path),
                       input_authorized=False,
                       real_client_accepted=False)
            self.emit('Motion collection: '+record['outcome']+' · '+reason+' · '+persistence)

        def autopilot_tick(self, now):
            driver = self.motion_collection_driver
            if driver is not None and not self._motion_idle():
                driver.session.cancel('measurement helper has competing work or recovery')
                if driver.busy:
                    raise CollectionStopped('measurement helper has competing work or recovery')
                self._finish_motion('measurement helper has competing work or recovery')
            result = super().autopilot_tick(now)
            driver = self.motion_collection_driver
            if driver is None:
                return result
            if driver.busy:
                # Let the outer executor run its finally/release before
                # publishing the result, including a cancelled attempt.
                driver.tick()
                return result
            try:
                if self.measurement_only is not True or self.active or self.preparing or self.stopping:
                    driver.session.cancel('measurement helper is no longer idle')
                driver.tick()
            except Exception as error:
                self._finish_motion(str(error))
            else:
                if driver.session.phase == 'complete':
                    self._finish_motion('conditional estimate collected; live motion remains unverified')
            return result

        def run(self):
            try:
                return super().run()
            finally:
                self._finish_motion('helper exited')

    return MotionCollectionEngine
