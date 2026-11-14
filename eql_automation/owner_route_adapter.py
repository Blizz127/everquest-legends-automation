"""Attach an explicit route driver to the retained helper's measurement ticks.

No job or hotkey creates the driver. Assist helpers reject attachment; their
manual movement contract is unchanged. Live dependencies must be assembled
separately before this integration can be enabled for an owner route test.
"""
import json
from pathlib import Path
from uuid import uuid4

from .navigation_phase import navigation_active
from .fixed_route_follower import RouteHalt
from .route_session import RouteSessionDriver
from .owner_zone_tracker import make_zone_tracking_engine


def make_route_session_engine(base_engine, *, output_root=None, zone_observer=None):
    output_root = Path(output_root) if output_root is not None else (
        Path.home()/'.local/share/eql-automation/route-sessions')

    class RouteSessionEngine(make_zone_tracking_engine(base_engine, zone_observer=zone_observer)):
        def __init__(self,*args,**kwargs):
            self.route_session_driver = None
            self.route_session_epoch = 0
            self.last_route_session_result = self.last_route_session_path = None
            super().__init__(*args,**kwargs)

        def _route_idle(self):
            return (navigation_active(self) and not self.active and not self.preparing
                and not self.stopping and not self.command_recovery_pending
                and not any(getattr(self,name,None) is not None for name in
                    ('autopilot','deferred','loc_request','loc_wanted','recorder','pointer',
                     'position_observation','navigation_preflight','motion_collection_driver',
                     'hotkey_test','supervised_motion')))

        def attach_route_session(self,driver):
            epoch = self.route_session_epoch
            if (not isinstance(driver,RouteSessionDriver) or self.route_session_driver is not None
                    or not self._route_idle() or not self.jobs.empty() or self.cancelled
                    or driver.session.mode != 'measurement'
                    or driver.session.lock is not getattr(self,'g0_stop_lock',None)
                    or self.sender is not driver.sender):
                raise ValueError('Idle measurement helper, same sender/stop lock and explicit route driver required')
            driver.session._check()
            tracker = self.live_zone_tracker
            if (tracker is not None and tracker.lease is not None
                    and driver.session.zone_lease is not tracker.lease):
                raise ValueError('Route must consume the exclusive current-zone lease')
            self.route_session_driver = driver
            if epoch != self.route_session_epoch or not self.jobs.empty():
                driver.session.cancel('helper job raced route attachment')
                self.route_session_driver = None
                raise ValueError('helper job raced route attachment')

        def _cancel_route(self,reason):
            if self.route_session_driver is not None:
                self.route_session_driver.session.cancel(reason)

        def post(self,name,value=None):
            self.route_session_epoch += 1
            self._cancel_route('another helper job requested')
            return super().post(name,value)

        def stop_action(self,reason,*,keep_autopilot=False):
            self._cancel_route(reason)
            return super().stop_action(reason,keep_autopilot=keep_autopilot)

        def stop_autopilot(self,reason):
            self._cancel_route(reason)
            return super().stop_autopilot(reason)

        def _finish_route(self,reason):
            driver,self.route_session_driver = self.route_session_driver,None
            if driver is None:return
            if driver.session.phase != 'arrived':driver.session.cancel(reason)
            self._revoke_zone_lease()
            if driver.session.zone_lease is not None:
                driver.session.zone_lease.release()
            record = driver.session.snapshot()
            self.last_route_session_result = record
            self.last_route_session_path = None
            try:
                root = output_root.expanduser().resolve()
                game = Path(self.settings.game_dir).resolve()
                protected = (Path.home()/'Games/everquest-legends').resolve()
                if root.is_relative_to(game) or root.is_relative_to(protected):
                    raise ValueError('Route evidence output must be outside the game/prefix')
                root.mkdir(parents=True,exist_ok=True,mode=0o700)
                path = root/('route-'+uuid4().hex+'.json')
                payload = json.dumps(record,indent=2,allow_nan=False)+'\n'
                with path.open('x') as out:out.write(payload)
                path.chmod(0o600)
                self.last_route_session_path = path
                persistence = 'saved '+str(path)
            except (OSError,ValueError,TypeError) as error:
                persistence = 'save unavailable; retained in memory: '+str(error)
            self.trace('route_session_result',record=record,
                saved_path=None if self.last_route_session_path is None else str(self.last_route_session_path),
                real_client_accepted=False)
            self.emit('Route session: '+record['outcome']+' · '+reason+' · '+persistence)

        def autopilot_tick(self,now):
            driver = self.route_session_driver
            if driver is not None and (not self._route_idle() or self.cancelled
                    or self.sender is not driver.sender or not self.jobs.empty()):
                driver.session.cancel('helper has competing work, recovery or changed sender')
                if driver.busy:raise RouteHalt('helper changed during checked route operation')
                self._finish_route('helper has competing work, recovery or changed sender')
            result = super().autopilot_tick(now)
            driver = self.route_session_driver
            if driver is None:return result
            if driver.busy:
                driver.tick()  # Propagate cancellation to the outer release/finally.
                return result
            try:driver.tick()
            except Exception as error:self._finish_route(str(error))
            else:
                if driver.session.phase == 'arrived':
                    self._finish_route('fixed route observed at endpoint; client acceptance remains separate')
            return result

        def run(self):
            try:return super().run()
            finally:self._finish_route('helper exited')

    return RouteSessionEngine
