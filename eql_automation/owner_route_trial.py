"""One explicit owner action: measure motion, start here, run a finite trial.

The normal motion job still stops. This wrapper needs a pinned geometry loader;
it does not choose a server, log in, guess a zone or create another sender.
"""
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import time
from uuid import uuid4

from .current_route_start import CurrentStartPlanner
from .destination_route import plan_destination
from .fixed_route_follower import FixedRouteFollower
from .g2_safety_provider import GameWindowIdentity
from .location_hotkey import send_location_hotkey
from .motion_collection import CommandReceipt, LocationRequest
from .observed_height import measure_current_height
from .owner_input_observer import OwnerInputObserver
from .owner_destination_assets import DestinationRouteAssets
from .owner_navigation_preflight import settings_identity, window_identity
from .owner_route_adapter import make_route_session_engine
from .owner_supervised_motion import MOTION_JOB, make_owner_nov12_engine as motion_engine
from .route_floor_commit import RouteFloorCommit
from .route_geometry import RouteGeometryPreparer, RouteMotionBounds
from .route_location_hotkey import RouteLocationHotkeyExecutor
from .route_session import RouteSession, RouteSessionDriver
from .stopped_location_pair import StoppedLocationPair
from .supervised_route import SupervisedRouteDeclaration, SupervisedRoutePolicy, scope_limits

TRIAL_JOB = 'supervised_local_route_trial'
DESTINATION_JOB = 'supervised_destination_travel'


def zone_binding(reader):
    return (reader.zone_id,reader.zone_display_name,reader.tail.identity,
            reader.tail.epoch,reader.zone_generation)


def make_owner_route_trial_engine(base_engine, *, planner_loader, destination_loader=None,
        observer_factory=OwnerInputObserver, clock=time.monotonic,
        local_wall_clock=datetime.now, output_root=None, motion_output=None, hotkey_output=None):
    if not callable(planner_loader) or (destination_loader is not None and not callable(destination_loader)):
        raise ValueError('Pinned current-zone geometry loader required')
    output_root=Path(output_root) if output_root is not None else (
        Path.home()/'.local/share/eql-automation/route-trials')
    base=make_route_session_engine(motion_engine(base_engine,clock=clock,
        observer_factory=observer_factory,output_root=motion_output,hotkey_output=hotkey_output),
        output_root=output_root/'routes')

    class TrialEngine(base):
        def __init__(self,*args,**kwargs):
            self.route_trial=None
            self.last_route_trial_result=self.last_route_trial_path=None
            super().__init__(*args,**kwargs)

        def _supervised_job_names(self):
            return (MOTION_JOB,TRIAL_JOB,DESTINATION_JOB)

        def _supervised_current(self,p,*,active):
            super()._supervised_current(p,active=active)
            if p['job'] in (TRIAL_JOB,DESTINATION_JOB):
                recipe=p['continuation']
                if not recipe['started']<=clock()<=recipe['started']+recipe['maximum_seconds']:
                    raise ValueError('Owner route startup time budget exhausted')

        def autopilot_payload(self):
            data=super().autopilot_payload()
            tracker=self.live_zone_tracker
            data['zone']=None if tracker is None or tracker.closed else tracker.reader.zone_display_name
            p=self.route_trial
            motion=self.supervised_motion
            if p is not None:
                stage=p['stage']
                label=p['continuation']['label']
                data.update(state='running',phase=label+' · '+stage.replace('_',' '),
                            trial_stage=stage)
                if p.get('driver') is not None:
                    runner=p['driver'].session.runner
                    data['phase']+=' · segment '+str(min(runner.index+1,len(runner.route.segments)))+'/'+str(len(runner.route.segments))
            elif motion is not None:
                trial=motion['job'] in (TRIAL_JOB,DESTINATION_JOB)
                label=motion['continuation']['label'] if trial else 'Motion measurement'
                data.update(state='running',phase=(label+' · ')
                    +motion['stage'],trial_stage=motion['stage'] if trial else None)
            elif self.last_route_trial_result is not None:
                # Let the GUI show the latest emitted status, including a
                # subsequent hotbutton/setup refusal, instead of stale prose.
                data.update(state='halted',trial_stage='stopped')
            return data

        def _prepare_supervised_job(self,name):
            if name not in (TRIAL_JOB,DESTINATION_JOB):return super()._prepare_supervised_job(name)
            if name==DESTINATION_JOB and destination_loader is None:
                raise ValueError('This helper has no destination travel loader')
            if self.route_trial is not None or not self._route_idle():
                raise ValueError('Finish the current helper action before starting a route trial')
            epoch=(self.cancel_generation,self.supervised_epoch,self.route_session_epoch,
                   settings_identity(self.settings))
            self._service_zone_tracker()
            tracker=self.live_zone_tracker
            if tracker is None or tracker.reader.zone_id is None:
                raise ValueError('Route trial needs a zone entry observed in this helper session')
            tracker.check_binding()
            zone=zone_binding(tracker.reader)
            destination=destination_loader(self) if name==DESTINATION_JOB else None
            if name==DESTINATION_JOB and not isinstance(destination,DestinationRouteAssets):
                raise ValueError('Destination travel requires pinned map and mesh assets')
            planner=destination.planner if destination is not None else planner_loader(self)
            tracker.poll()  # Loading may take seconds; consume any intervening transition.
            if (not isinstance(planner,CurrentStartPlanner)
                    or zone[:2]!=(planner.zone_id,planner.zone_name)
                    or tracker is not self.live_zone_tracker or zone_binding(tracker.reader)!=zone
                    or epoch!=(self.cancel_generation,self.supervised_epoch,self.route_session_epoch,
                              settings_identity(self.settings)) or not self.jobs.empty()):
                raise ValueError('Current-zone geometry or owner job changed during preparation')
            return dict(planner=planner,destination=destination,
                        scope='destination_travel' if destination is not None else 'local_trial',
                        label=destination.target_name if destination is not None else 'Supervised route trial',
                        zone=zone,tracker=tracker,route_epoch=self.route_session_epoch,
                        started=clock(),maximum_seconds=180.)

        def _cancel_trial(self,reason):
            p=self.route_trial
            if p is None:return
            p['cancelled']=str(reason)
            if p.get('collector') is not None:p['collector'].cancel(reason)
            if p.get('policy') is not None:p['policy'].cancel(reason)
            if p.get('driver') is not None:p['driver'].session.cancel(reason)

        def post(self,name,value=None):
            self._cancel_trial('another owner job requested')
            return super().post(name,value)

        def stop_action(self,reason,*,keep_autopilot=False):
            self._cancel_trial(reason)
            return super().stop_action(reason,keep_autopilot=keep_autopilot)

        def stop_autopilot(self,reason):
            self._cancel_trial(reason)
            return super().stop_autopilot(reason)

        def handle_job(self,name,value):
            if self.route_trial is not None:
                self._cancel_trial('another owner job requested')
                # Direct queue.put calls also land here. Do not allow another
                # operation while a startup/route sender may own the descriptor.
                self.emit('Route trial stopping; wait for its stopped result before another action.')
                return
            return super().handle_job(name,value)

        def _trial_current(self,p):
            def bound():
                if (self.route_trial is not p or p['cancelled'] or self.cancelled
                        or self.supervised_motion is not None or self.motion_collection_driver is not None
                        or self.supervised_epoch!=p['epoch'] or self.cancel_generation!=p['generation']
                        or self.route_session_epoch!=p['continuation']['route_epoch']
                        or settings_identity(self.settings)!=p['settings'] or not self._route_idle()
                        or not self.jobs.empty() or self.sender is not p['sender'] or self.gate is not p['gate']
                        or window_identity(self.gate,require_focus=True)!=p['window']
                        or not p['continuation']['started']<=clock()<=p['expires']
                        or self.live_zone_tracker is not p['continuation']['tracker']
                        or (p.get('driver') is not None and self.route_session_driver is not p['driver'])):
                    raise ValueError('Owner route trial cancelled or helper/game scope changed')
            bound()
            if p['continuation']['destination'] is not None:
                p['continuation']['destination'].check()
            p['binding'].check()
            veto=p['veto'].poll();sample=p['observer'].sample()
            if (not veto.continuity_available or veto.reason is not None
                    or not sample.clear_at(clock()) or sample.topology_generation!=p['topology']):
                raise ValueError('Owner input, coverage or log hazard changed during trial')
            lease=p.get('lease')
            if lease is not None:
                lease.check()
                if zone_binding(lease.reader)!=p['continuation']['zone']:
                    raise ValueError('Trial zone/log identity changed')
            bound()

        def _trial_binding(self,p):
            self._trial_current(p)
            return p['lease'].check()

        def _handoff_completed_motion(self,p,session,record):
            if p['job'] not in (TRIAL_JOB,DESTINATION_JOB):return super()._handoff_completed_motion(p,session,record)
            recipe=p['continuation']
            if (not isinstance(recipe,dict) or not isinstance(recipe.get('planner'),CurrentStartPlanner)
                    or self.route_trial is not None or self.sender.held
                    or getattr(self.sender,'_eql_route_operation',None) is not None
                    or session.result is not record.get('estimate')):
                raise ValueError('Missing current completed measurement for route handoff')
            # This method runs under the shared stop lock, after motion release
            # and result persistence. It never queues or rearms another job.
            self.supervised_motion=None
            self.route_trial=p
            p.update(stage='startup_plan',busy=False,collector=None,lease=None,driver=None,policy=None,
                trial_id=('owner-destination-' if p['job']==DESTINATION_JOB else 'owner-local-trial-')+uuid4().hex,
                motion_record=record,plan=None,
                startup_pairs=[],events=[],expires=recipe['started']+recipe['maximum_seconds'])
            try:
                self._trial_current(p)
                p['lease']=self.lease_current_zone()
                self._trial_current(p)
                fit=session.result['estimate']
                speed_upper=session.result['conditional_intervals']['speed'][1]*1.25
                if not 0<speed_upper<=150:
                    raise ValueError('Conditional speed exceeds finite trial planning range')
                p['motion_fit']=dict(fit)
                p['bounds']=RouteMotionBounds(p['trial_id']+'-planning',session.record_id,
                    .01,.1,.2,speed_upper,.4,.01,2.,.1,1.2,6.)
                p['bounds'].validate_values(calibration_record_id=session.record_id,maximum_step_seconds=.2)
                p['last_release']=session.releases[-1]['final_release_at']
                self._new_startup_pair(p)
                self.trace('route_trial_motion_handoff',trial_id=p['trial_id'],
                    motion_record_id=session.record_id,observer_retained=True,
                    bounds_assumptions=asdict(p['bounds']),real_client_accepted=False)
                self._trial_current(p)
                self.emit('Motion measured · collecting current position for '+recipe['label']+' · F9/F11 stop.')
            except BaseException as error:
                self._cancel_trial(str(error));self._finish_trial(str(error));raise
            return True

        def _new_startup_pair(self,p):
            p['collector']=StoppedLocationPair(p['lease'],released_at=p['last_release'],
                check_current=lambda:self._trial_current(p),clock=clock,local_wall_clock=local_wall_clock)

        def _startup_hotkey(self,p,request):
            collector=p['collector']
            def current():
                self._trial_current(p);collector.check()
                if (p['collector'] is not collector or not p['busy']
                        or collector.pending is not request or collector.phase!='requesting'):
                    raise ValueError('Startup hotbutton request changed')
            def pump():
                self.pump();self.autopilot_tick(clock())
            receipt=send_location_hotkey(p['sender'],binding=p['binding'],owner_input=p['observer'],
                lock=self.g0_stop_lock,clock=clock,expires_at=request.expires_at,ensure_current=current,
                cancel=lambda reason:self._cancel_trial(reason),pump=pump,record_event=p['events'].append)
            p['last_release']=receipt.released_at
            return CommandReceipt(receipt.pulse.down_started_at,receipt.released_at)

        def _startup_tick(self,p):
            if p['busy']:
                self._trial_current(p);p['collector'].check();return
            p['busy']=True
            try:
                collector=p['collector']
                action=collector.tick()
                if isinstance(action,LocationRequest):
                    collector.command_sent(action,self._startup_hotkey(p,action))
                if collector.phase!='complete':return
                self._trial_current(p)
                p['startup_pairs'].append(collector.snapshot())
                planner=p['continuation']['planner']
                if p['stage']=='startup_plan':
                    options=dict(
                        heading=p['motion_fit']['final_heading'],motion_record_id=p['session'].record_id,
                        bounds=p['bounds'],half_width=.3,vertical_window=3.,
                        maximum_source_z_difference=2.,owner_binding=p['lease'].owner_binding,
                        binding_reader=lambda:self._trial_binding(p),released_at=collector.released_at,
                        record_id=p['trial_id']+'-start',clock=clock,local_wall_clock=local_wall_clock)
                    destination=p['continuation']['destination']
                    if destination is None:
                        p['plan']=planner.plan(p['lease'].reader,collector.first,collector.second,length=2.,**options)
                    else:
                        destination.check()
                        p['plan']=plan_destination(planner,destination.navigation_mesh,p['lease'].reader,
                            collector.first,collector.second,goal_xy=destination.goal_xy,**options)
                    self._trial_current(p)
                    p['stage']='startup_height'
                    self._new_startup_pair(p)
                else:
                    self._attach_trial_driver(p,collector)
            finally:p['busy']=False

        def _attach_trial_driver(self,p,pair):
            from eqnav import steer
            plan=p['plan'];self._trial_current(p)
            scope=p['continuation']['scope']
            seconds,steps,distance,hold=scope_limits(scope)
            if scope=='local_trial':distance=3.
            cal=measure_current_height(plan.observer,p['lease'].reader,pair.first,pair.second,
                route=plan.route,segment_index=0,owner_binding=p['lease'].owner_binding,
                binding_reader=lambda:self._trial_binding(p),clock=clock,
                record_id=p['trial_id']+'-height',released_at=pair.released_at,
                local_wall_clock=local_wall_clock,valid_for=seconds+60. if scope=='destination_travel' else 300.)
            fit=p['motion_fit']
            motion=steer.Motion(run_speed=fit['run_speed'],turn_rate=fit['turn_rate'],
                right_sign=fit['right_sign'],turn_latency=fit['turn_latency'],back_speed=0.)
            runner=FixedRouteFollower(plan.route,legacy=steer,motion=motion,
                heading=fit['final_heading'],calibration_record_id=p['session'].record_id,
                height_calibration=cal,geometry_evidence=plan.observer.geometry,
                generation=p['generation'],generation_reader=lambda:self.cancel_generation,
                mode_reader=lambda:'measurement' if self.measurement_only else 'off',max_steps=steps)
            ledger=RouteFloorCommit(runner,plan.floor_chain,stop_lock=self.g0_stop_lock,clock=clock)
            planner=p['continuation']['planner']
            geometry=RouteGeometryPreparer(ledger,ground=planner.ground,source=planner.source,
                static=planner.static,bsp=planner.bsp,bounds=p['bounds'],
                static_inventory_sha256=planner.pins[3],vertical_window=3.,maximum_source_z_difference=2.,
                precision_policy=plan.precision_policy)
            session=RouteSession(ledger,p['lease'].reader,plan.observer,
                initial_release_at=p['last_release'],binding_reader=lambda:self._trial_binding(p),
                record_id=p['trial_id'],max_seconds=seconds,local_wall_clock=local_wall_clock,zone_lease=p['lease'])
            # A destination has a separate finite travel phase after bounded
            # startup. The local experiment keeps its original whole-job cap.
            if scope=='destination_travel':p['expires']=clock()+seconds
            declaration=SupervisedRouteDeclaration(p['trial_id'],plan.route.artifact_sha256,
                runner.calibration,p['bounds'].record_id,True,seconds,steps,distance,hold,scope)
            policy=SupervisedRoutePolicy(geometry,declaration=declaration,gate=self.gate,
                owner_input=p['observer'],log_veto=p['veto'],expected_log_path=self.log_path(),
                expected_window=GameWindowIdentity(*p['window']),topology_generation=p['topology'],
                check_current=lambda:self._trial_current(p))
            executor=RouteLocationHotkeyExecutor(self,session,hotkey=p['binding'],owner_input=p['observer'])
            driver=RouteSessionDriver(session,self.sender,request_location=executor.request_location,
                sample_scene=policy.observe,prepare_step=geometry,authorize_step=policy.authorize,
                still_authorized=policy.still_authorized,
                command_state_clear=lambda:self._route_idle() and not self.cancelled and self.jobs.empty(),
                pump=self.pump,supervised_policy=policy)
            self._trial_current(p)
            self.attach_route_session(driver)
            p.update(stage='route',driver=driver,policy=policy)
            session.executor_events.append(dict(kind='same_action_motion_and_startup',
                motion_record_id=p['session'].record_id,trial_id=p['trial_id'],
                observer_retained=True,geometry_sha256=plan.observer.geometry.same_floor_evidence_sha256))
            self._trial_current(p)
            self.emit(p['continuation']['label']+' active · movement only · F9/F11 stop.')

        def _finish_trial(self,reason):
            p=self.route_trial
            if p is None:return
            driver=p.get('driver')
            if p['busy'] or (driver is not None and driver.busy):return
            self.route_trial=None
            if p.get('lease') is not None:p['lease'].release()
            try:p['observer'].close()
            except Exception as error:reason=str(reason)+'; input observer cleanup: '+str(error)
            self.cancelled=True
            plan=p.get('plan')
            record=dict(format=('eql-owner-destination-travel-v1' if p['job']==DESTINATION_JOB
                                else 'eql-owner-local-route-trial-v1'),record_id=p['trial_id'],
                scope=p['continuation']['scope'],
                destination=None if p['continuation']['destination'] is None else
                    json.loads(p['continuation']['destination'].source_evidence),
                outcome='arrived' if driver is not None and driver.session.phase=='arrived' else 'stopped',
                reason=str(reason),motion_record=p['motion_record'],startup_pairs=p['startup_pairs'],
                incomplete_pair=None if p.get('collector') is None else p['collector'].snapshot(),
                startup_events=p['events'],route=None if driver is None else driver.session.snapshot(),
                plan=None if plan is None else json.loads(plan.plan_bytes),
                geometry=None if plan is None else json.loads(plan.evidence_bytes),
                owner_supervised=True,real_client_accepted=False)
            self.last_route_trial_result=record;self.last_route_trial_path=None
            try:
                root=output_root.expanduser().resolve()
                if (root.is_relative_to(Path(self.settings.game_dir).resolve())
                        or root.is_relative_to((Path.home()/'Games/everquest-legends').resolve())):
                    raise ValueError('Trial evidence must be outside the game/prefix')
                root.mkdir(parents=True,exist_ok=True,mode=0o700)
                path=root/(p['trial_id']+'.json')
                with path.open('x') as out:out.write(json.dumps(record,indent=2,allow_nan=False)+'\n')
                path.chmod(0o600);self.last_route_trial_path=path
            except (OSError,ValueError,TypeError) as error:
                reason=str(reason)+'; save unavailable: '+str(error)
            self.trace('owner_route_trial_finished',record=record,
                saved_path=None if self.last_route_trial_path is None else str(self.last_route_trial_path))
            self.emit('Route trial '+record['outcome']+' · stopped · '+str(reason))

        def autopilot_tick(self,now):
            p=self.route_trial
            try:
                if p is not None:self._trial_current(p)
                result=super().autopilot_tick(now)
                p=self.route_trial
                if p is None:return result
                if p['stage'].startswith('startup_'):self._startup_tick(p)
                elif self.route_session_driver is None:
                    self._finish_trial(p['driver'].session.reason or 'destination reached')
                return result
            except Exception as error:
                p=self.route_trial
                self._cancel_trial(str(error))
                if p is not None and (p['busy'] or (p.get('driver') is not None and p['driver'].busy)):
                    raise
                self._finish_route(str(error))
                self._finish_trial(str(error))

        def run(self):
            try:return super().run()
            finally:self._cancel_trial('helper exited');self._finish_trial('helper exited')

    return TrialEngine
