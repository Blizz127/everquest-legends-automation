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

from .navigation_phase import navigation_active
from .current_route_start import CurrentStartPlanner
from .destination_route import plan_destination
from .fixed_route_follower import FixedRouteFollower
from .g2_safety_provider import GameWindowIdentity
from .location_hotkey import send_location_hotkey
from .motion_collection import CommandReceipt, LocationRequest
from .observed_height import measure_current_height
from .owner_input_observer import OwnerInputObserver
from .owner_destination_assets import DestinationRouteAssets
from .owner_crossing_assets import CrossingDestinationAssets
from .owner_source_assets import SourceDestinationAssets
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
CROSSING_JOB = 'supervised_crushbone_crossing'
SOURCE_JOB = 'supervised_crushbone_source_travel'


def zone_binding(reader):
    return (reader.zone_id,reader.zone_display_name,reader.tail.identity,
            reader.tail.epoch,reader.zone_generation)


def make_owner_route_trial_engine(base_engine, *, planner_loader, destination_loader=None, crossing_loader=None,
        source_loader=None,
        observer_factory=OwnerInputObserver, clock=time.monotonic,
        local_wall_clock=datetime.now, output_root=None, motion_output=None, hotkey_output=None,
        zone_observer=None):
    if (not callable(planner_loader) or (destination_loader is not None and not callable(destination_loader))
            or (crossing_loader is not None and not callable(crossing_loader))
            or (source_loader is not None and not callable(source_loader))):
        raise ValueError('Pinned current-zone geometry loader required')
    output_root=Path(output_root) if output_root is not None else (
        Path.home()/'.local/share/eql-automation/route-trials')
    base=make_route_session_engine(motion_engine(base_engine,clock=clock,
        observer_factory=observer_factory,output_root=motion_output,hotkey_output=hotkey_output),
        output_root=output_root/'routes', zone_observer=zone_observer)

    class TrialEngine(base):
        def __init__(self,*args,**kwargs):
            self.route_trial=None
            self.last_route_trial_result=self.last_route_trial_path=None
            super().__init__(*args,**kwargs)

        def _supervised_job_names(self):
            return (MOTION_JOB,TRIAL_JOB,DESTINATION_JOB,CROSSING_JOB,SOURCE_JOB)

        def _supervised_current(self,p,*,active):
            super()._supervised_current(p,active=active)
            if p['job'] in (TRIAL_JOB,DESTINATION_JOB,CROSSING_JOB,SOURCE_JOB):
                recipe=p['continuation']
                self._check_region_model(recipe)
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
                elif p.get('corridor_runtime') is not None:
                    corridor=p['corridor_runtime'].corridor
                    data['phase']+=' · '+corridor.phase.replace('_',' ')
                    if corridor.phase=='ready':data['phase']+=' · segment '+str(corridor.runner.index+1)
                elif p.get('source_runtime') is not None:
                    runtime=p['source_runtime']
                    data['phase']+=' · '+runtime.phase+' · cell '+str(runtime.driver.index+1)
            elif motion is not None:
                trial=motion['job'] in (TRIAL_JOB,DESTINATION_JOB,CROSSING_JOB,SOURCE_JOB)
                label=motion['continuation']['label'] if trial else 'Motion measurement'
                data.update(state='running',phase=(label+' · ')
                    +motion['stage'],trial_stage=motion['stage'] if trial else None)
            elif self.last_route_trial_result is not None and self.autopilot is None:
                # Let the GUI show the latest emitted status, including a
                # subsequent hotbutton/setup refusal, instead of stale prose.
                data.update(state='halted',trial_stage='stopped')
            return data

        def _prepare_supervised_job(self,name):
            if name not in (TRIAL_JOB,DESTINATION_JOB,CROSSING_JOB,SOURCE_JOB):return super()._prepare_supervised_job(name)
            if name==DESTINATION_JOB and destination_loader is None:
                raise ValueError('This helper has no destination travel loader')
            if name==CROSSING_JOB and crossing_loader is None:
                raise ValueError('This helper has no expected-zone crossing loader')
            if name==SOURCE_JOB and source_loader is None:
                raise ValueError('This helper has no source-guide loader')
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
            destination=(source_loader(self) if name==SOURCE_JOB else
                         crossing_loader(self) if name==CROSSING_JOB else
                         destination_loader(self) if name==DESTINATION_JOB else None)
            if name==DESTINATION_JOB and not isinstance(destination,DestinationRouteAssets):
                raise ValueError('Destination travel requires pinned map and mesh assets')
            if name==CROSSING_JOB and type(destination) is not CrossingDestinationAssets:
                raise ValueError('Crossing requires pinned native line and expected destination')
            if name==SOURCE_JOB and type(destination) is not SourceDestinationAssets:
                raise ValueError('Source travel requires a pinned same-zone guide')
            planner=destination.planner if destination is not None else planner_loader(self)
            if not isinstance(planner,CurrentStartPlanner):
                raise ValueError('Pinned current-zone planner required')
            region_model = getattr(planner, 'installed_region_model', None)
            if planner.region_policy is not None:
                from .installed_region_model import InstalledRegionModel
                if type(region_model) is not InstalledRegionModel:
                    raise ValueError('Native trial needs installed executable verification')
                region_model.check_policy(planner.region_policy)
            tracker.poll()  # Loading may take seconds; consume any intervening transition.
            if (not isinstance(planner,CurrentStartPlanner)
                    or zone[:2]!=(planner.zone_id,planner.zone_name)
                    or tracker is not self.live_zone_tracker or zone_binding(tracker.reader)!=zone
                    or epoch!=(self.cancel_generation,self.supervised_epoch,self.route_session_epoch,
                              settings_identity(self.settings)) or not self.jobs.empty()):
                raise ValueError('Current-zone geometry or owner job changed during preparation')
            return dict(planner=planner,destination=destination, region_model=region_model,
                        region_policy=planner.region_policy,
                        scope=('zone_crossing_corridor' if name==CROSSING_JOB else
                               'destination_travel' if destination is not None else 'local_trial'),
                        label=destination.target_name if destination is not None else 'Supervised route trial',
                        zone=zone,tracker=tracker,route_epoch=self.route_session_epoch,
                        started=clock(),maximum_seconds=180.)

        def _check_region_model(self, recipe):
            planner = recipe['planner']; policy = recipe['region_policy']; model = recipe['region_model']
            if planner.region_policy is not policy:
                raise ValueError('Owner native region policy changed')
            if policy is not None:
                if (getattr(planner, 'installed_region_model', None) is not model
                        or model.game_dir != str(Path(self.settings.game_dir).resolve())):
                    raise ValueError('Owner installed region-model binding changed')
                model.check_policy(policy)

        def _cancel_trial(self,reason):
            p=self.route_trial
            if p is None:return
            p['cancelled']=str(reason)
            if p.get('collector') is not None:p['collector'].cancel(reason)
            if p.get('policy') is not None:p['policy'].cancel(reason)
            if p.get('driver') is not None:p['driver'].session.cancel(reason)
            if p.get('corridor_runtime') is not None:p['corridor_runtime'].cancel(reason)
            if p.get('source_runtime') is not None:p['source_runtime'].cancel(reason)
            if p.get('source_prepared') is not None:p['source_prepared'].cancel(reason)

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

        def _trial_scope_current(self,p):
            # Read callback-bearing window/idle providers first, then compare
            # the volatile owner tokens. Source observation binding needs this
            # identity check, not a nested physical-input/model observation.
            idle=self._route_idle()
            window=window_identity(self.gate,require_focus=True)
            now=clock()
            if (self.route_trial is not p or p['cancelled'] or self.cancelled
                        or self.supervised_motion is not None or self.motion_collection_driver is not None
                        or self.supervised_epoch!=p['epoch'] or self.cancel_generation!=p['generation']
                        or self.route_session_epoch!=p['continuation']['route_epoch']
                        or settings_identity(self.settings)!=p['settings'] or not idle
                        or not self.jobs.empty() or self.sender is not p['sender'] or self.gate is not p['gate']
                        or window!=p['window']
                        or not p['continuation']['started']<=now<=p['expires']
                        or self.live_zone_tracker is not p['continuation']['tracker']
                        or (p.get('driver') is not None and self.route_session_driver is not p['driver'])):
                raise ValueError('Owner route trial cancelled or helper/game scope changed')

        def _trial_common_current(self,p):
            def bound():
                self._check_region_model(p['continuation'])
                self._trial_scope_current(p)
            # These providers only read state. Retain the model precheck and
            # validate the complete owner scope after their last callback;
            # an extra window/root query before them adds no input boundary.
            self._check_region_model(p['continuation'])
            if p['continuation']['destination'] is not None:
                p['continuation']['destination'].check()
            p['binding'].check()
            sample=p['observer'].sample()
            if not sample.clear_at(clock()) or sample.topology_generation!=p['topology']:
                raise ValueError('Owner input or coverage changed during trial')
            lease=p.get('lease')
            if lease is not None:
                lease.check()
            bound()

        def _trial_current(self,p):
            runtime=p.get('corridor_runtime')
            if runtime is None:runtime=p.get('source_runtime')
            if runtime is not None:
                runtime.check_current()
                return
            self._trial_common_current(p)
            veto=p['veto'].poll()
            if not veto.continuity_available or veto.reason is not None:
                raise ValueError('Log hazard or coverage changed during trial')
            lease=p.get('lease')
            if lease is not None and zone_binding(lease.reader)!=p['continuation']['zone']:
                raise ValueError('Trial zone/log identity changed')
            self._trial_common_current(p)

        def _trial_binding(self,p):
            runtime=p.get('source_runtime')
            if runtime is not None:
                binding=runtime.observation_binding()
                # observation_binding reads the exclusive lease/descriptor.
                # Recheck job, window and root after all of those callbacks.
                self._trial_scope_current(p)
                return binding
            self._trial_current(p)
            return p['lease'].check()

        def _handoff_completed_motion(self,p,session,record):
            if p['job'] not in (TRIAL_JOB,DESTINATION_JOB,CROSSING_JOB,SOURCE_JOB):return super()._handoff_completed_motion(p,session,record)
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
            p.update(stage='startup_plan',busy=False,collector=None,lease=None,driver=None,policy=None,corridor_runtime=None,
                source_runtime=None,source_prepared=None,
                trial_id=('owner-source-' if p['job']==SOURCE_JOB else 'owner-crossing-' if p['job']==CROSSING_JOB else
                          'owner-destination-' if p['job']==DESTINATION_JOB else 'owner-local-trial-')+uuid4().hex,
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

        def _source_input_release_deadline(self,p):
            return None

        def _startup_hotkey(self,p,request):
            collector=p['collector']
            def current():
                self._trial_current(p);collector.check()
                if (p['collector'] is not collector or not p['busy']
                        or collector.pending is not request or collector.phase!='requesting'):
                    raise ValueError('Startup hotbutton request changed')
            def pump():
                self.pump();self.autopilot_tick(clock())
            release_deadline=self._source_input_release_deadline(p)
            deadline={} if release_deadline is None else dict(release_deadline=release_deadline)
            receipt=send_location_hotkey(p['sender'],binding=p['binding'],owner_input=p['observer'],
                lock=self.g0_stop_lock,clock=clock,expires_at=request.expires_at,ensure_current=current,
                cancel=lambda reason:self._cancel_trial(reason),pump=pump,record_event=p['events'].append,**deadline)
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
                if p['stage']=='startup_corridor':
                    runner,geometry=p['crossing_prepared']
                    fixes=tuple(v for v in (collector.first,collector.second) if v is not None)
                    if len(fixes)>len(p['crossing_observations']):
                        if len(fixes)!=len(p['crossing_observations'])+1:
                            raise ValueError('Crossing startup skipped a position reply')
                        p['crossing_observations'].append(p['plan'].observer.observe(fixes[-1],
                            route=runner.route,segment_index=0,height_calibration=runner.height_calibration,
                            motion_calibration_record_id=runner.calibration,now=clock(),
                            floor_chain=geometry.ledger.chain,mode='measurement'))
                elif p['stage']=='startup_source':
                    ledger=p['source_prepared']
                    fixes=tuple(v for v in (collector.first,collector.second) if v is not None)
                    if len(fixes)>len(p['source_observations']):
                        if len(fixes)!=len(p['source_observations'])+1:
                            raise ValueError('Source startup skipped a position reply')
                        p['source_observations'].append(ledger.observer.observe(fixes[-1],checked_chain=ledger.chain))
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
                        record_id=p['trial_id']+'-start',clock=clock,local_wall_clock=local_wall_clock,
                        allow_overhead_boundary=planner.region_policy is not None)
                    destination=p['continuation']['destination']
                    if type(destination) is SourceDestinationAssets:
                        destination.check()
                        p['plan']=self._plan_source_start(p,planner,collector,destination,options)
                    elif destination is None:
                        p['plan']=planner.plan(p['lease'].reader,collector.first,collector.second,length=2.,**options)
                    else:
                        destination.check()
                        p['plan']=plan_destination(planner,destination.navigation_mesh,p['lease'].reader,
                            collector.first,collector.second,goal_xy=destination.goal_xy,
                            expected_zone_line=(destination.expected_zone_line
                                if type(destination) is CrossingDestinationAssets else None),**options)
                    self._trial_current(p)
                    p['stage']='startup_height'
                    self._new_startup_pair(p)
                elif p['stage']=='startup_height':
                    if p['job']==SOURCE_JOB:self._prepare_source_runtime(p,collector)
                    else:self._attach_trial_driver(p,collector)
                elif p['stage']=='startup_source':
                    self._attach_source_runtime(p,collector)
                else:
                    self._attach_crossing_runtime(p,collector)
            finally:p['busy']=False

        def _plan_source_start(self,p,planner,collector,destination,options):
            from .current_source_itinerary import plan_current_source_itinerary
            return plan_current_source_itinerary(planner,p['lease'].reader,
                collector.first,collector.second,guide=destination.guide,
                maximum_seconds=min(240.,p['expires']-clock()),**options)

        def _source_journey_budget(self,p):
            return None

        def _prepare_source_runtime(self,p,pair):
            from eqnav import steer
            from .source_motion import SourceReceiptLedger
            from .source_observer import SourceItineraryObserver
            source_plan=p['plan'];plan=source_plan.initial
            self._trial_current(p)
            if plan.region_policy is not p['continuation']['region_policy']:
                raise ValueError('Source plan and owner region policy differ')
            seconds=scope_limits(p['continuation']['scope'])[0]
            def height_binding():
                value=self._trial_binding(p)
                if p['plan'] is not source_plan or p['collector'] is not pair:
                    raise ValueError('Active source plan or height collector changed')
                return value
            cal=measure_current_height(plan.observer,p['lease'].reader,pair.first,pair.second,
                route=plan.route,segment_index=0,owner_binding=p['lease'].owner_binding,
                binding_reader=height_binding,clock=clock,record_id=p['trial_id']+'-height',
                released_at=pair.released_at,local_wall_clock=local_wall_clock,
                valid_for=seconds+60.,floor_plan=plan)
            fit=p['motion_fit'];planner=p['continuation']['planner']
            motion=steer.Motion(run_speed=fit['run_speed'],turn_rate=fit['turn_rate'],
                right_sign=fit['right_sign'],turn_latency=fit['turn_latency'],back_speed=0.)
            def source_binding():
                value=self._trial_binding(p)
                if p['plan'] is not source_plan:
                    raise ValueError('Active source itinerary changed')
                return value
            observer=SourceItineraryObserver(source_plan,p['lease'].reader,height_calibration=cal,
                binding_reader=source_binding,mode_reader=lambda:'measurement' if navigation_active(self) else 'off',
                generation_reader=lambda:self.cancel_generation,generation=p['generation'],clock=clock)
            ledger=SourceReceiptLedger(observer,terrain=planner.source,static=planner.static,bsp=planner.bsp,
                bounds=p['bounds'],installed_model=p['continuation']['region_model'],
                legacy=steer,motion=motion,heading=fit['final_heading'],stop_lock=self.g0_stop_lock)
            self._trial_current(p)
            p.update(stage='startup_source',source_prepared=ledger,source_observations=[])
            self._new_startup_pair(p)

        def _attach_source_runtime(self,p,pair):
            from .owner_source_runtime import OwnerSourceRuntime
            from .source_walk_driver import SourceWalkDriver
            self._trial_current(p)
            ledger=p['source_prepared']
            ledger.start(*p['source_observations'],released_at=pair.released_at)
            budget=self._source_journey_budget(p)
            p['expires']=clock()+scope_limits(p['continuation']['scope'])[0]
            if budget is not None:
                budget.check()
                p['expires']=min(p['expires'],budget.expires_at)
            release_deadline=self._source_input_release_deadline(p)
            if release_deadline is not None:p['expires']=min(p['expires'],release_deadline)
            runtime=OwnerSourceRuntime(self,p,SourceWalkDriver(ledger),
                clock=clock,local_wall_clock=local_wall_clock,startup_released_at=pair.released_at,
                journey_budget=budget)
            p.update(stage='source_route',source_runtime=runtime,collector=None)
            self._trial_current(p)
            self.emit(p['continuation']['label']+' active · movement only · F9/F11 stop.')

        def _attach_trial_driver(self,p,pair):
            from eqnav import steer
            plan=p['plan'];self._trial_current(p)
            if plan.region_policy is not p['continuation']['region_policy']:
                raise ValueError('Owner plan and native region policy differ')
            scope=p['continuation']['scope']
            seconds,steps,distance,hold=scope_limits(scope)
            if scope=='local_trial':distance=3.
            def height_binding():
                value=self._trial_binding(p)
                if p['plan'] is not plan or p['collector'] is not pair:
                    raise ValueError('Active route plan or height collector changed')
                return value
            cal=measure_current_height(plan.observer,p['lease'].reader,pair.first,pair.second,
                route=plan.route,segment_index=0,owner_binding=p['lease'].owner_binding,
                binding_reader=height_binding,clock=clock,
                record_id=p['trial_id']+'-height',released_at=pair.released_at,
                local_wall_clock=local_wall_clock,valid_for=seconds+60. if scope!='local_trial' else 300.,
                floor_plan=plan)
            fit=p['motion_fit']
            motion=steer.Motion(run_speed=fit['run_speed'],turn_rate=fit['turn_rate'],
                right_sign=fit['right_sign'],turn_latency=fit['turn_latency'],back_speed=0.)
            runner=FixedRouteFollower(plan.route,legacy=steer,motion=motion,
                heading=fit['final_heading'],calibration_record_id=p['session'].record_id,
                height_calibration=cal,geometry_evidence=plan.observer.geometry,
                generation=p['generation'],generation_reader=lambda:self.cancel_generation,
                mode_reader=lambda:'measurement' if navigation_active(self) else 'off',max_steps=steps)
            if scope=='zone_crossing_corridor':
                from .provisional_floor_commit import ProvisionalRouteFloorCommit
                def source_context():
                    self._trial_common_current(p)
                    lease=p['lease'];line=p['continuation']['destination'].expected_zone_line
                    if zone_binding(lease.reader)!=p['continuation']['zone']:
                        raise ValueError('Crossing source zone/log binding changed')
                    return (lease.check(),id(lease.reader),zone_binding(lease.reader),line.sha256)
                ledger=ProvisionalRouteFloorCommit(runner,plan.floor_chain,stop_lock=self.g0_stop_lock,
                    clock=clock,context_reader=source_context)
            else:ledger=RouteFloorCommit(runner,plan.floor_chain,stop_lock=self.g0_stop_lock,clock=clock)
            planner=p['continuation']['planner']
            geometry=RouteGeometryPreparer(ledger,ground=planner.ground,source=planner.source,
                static=planner.static,bsp=planner.bsp,bounds=p['bounds'],
                static_inventory_sha256=planner.pins[3],vertical_window=3.,maximum_source_z_difference=2.,
                precision_policy=plan.precision_policy,
                region_policy=plan.region_policy,
                expected_zone_line=(p['continuation']['destination'].expected_zone_line
                    if scope=='zone_crossing_corridor' else None))
            if scope=='zone_crossing_corridor':
                p.update(stage='startup_corridor',crossing_prepared=(runner,geometry),crossing_observations=[])
                self._new_startup_pair(p)
                return
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
                check_current=lambda:self._trial_current(p),
                installed_region_model=p['continuation']['region_model'])
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

        def _attach_crossing_runtime(self,p,pair):
            from .owner_crossing_runtime import OwnerCrossingRuntime
            self._trial_current(p)
            runner,geometry=p['crossing_prepared']
            runner.observe_stopped(*p['crossing_observations'],released_at=pair.released_at,now=clock())
            seconds=scope_limits('zone_crossing_corridor')[0]
            p['expires']=clock()+seconds+90.
            runtime=OwnerCrossingRuntime(self,p,geometry,p['crossing_observations'][-1],
                clock=clock,local_wall_clock=local_wall_clock)
            p.update(stage='crossing',corridor_runtime=runtime,collector=None)
            self._trial_current(p)
            self.emit('Travel into Crushbone active · stops after observed arrival · F9/F11 stop.')

        def zone_changed(self,body,now):
            p=self.route_trial
            runtime=None if p is None else p.get('corridor_runtime')
            if runtime is not None and not p['cancelled'] and not self.cancelled:
                expected='You have entered '+runtime.corridor.arrival.destination+'.'
                if body in ('LOADING, PLEASE WAIT...',expected):
                    self.zone_loading_until=now+(2. if body==expected else 120.)
                    self.trace('owner_crossing_transition_seen',line=body,
                        exclusive_arrival_reader=True,real_client_accepted=False)
                    return
            return super().zone_changed(body,now)

        def _capture_trial_continuation(self, pending):
            return None

        def _continue_finished_trial(self, pending, arrival):
            return None

        def _finish_trial_input_observer(self,pending):
            pending['observer'].close()

        def _finish_trial(self,reason):
            p=self.route_trial
            if p is None:return
            driver=p.get('driver')
            if p['busy'] or (driver is not None and driver.busy):return
            runtime=p.get('corridor_runtime')
            source_runtime=p.get('source_runtime')
            destination_evidence=(None if p['continuation']['destination'] is None else
                p['continuation']['destination'].source_evidence)
            arrival=None; continuation=None
            try:arrival=self._capture_trial_continuation(p)
            except Exception as error:reason=str(reason)+'; continuation refused: '+str(error)
            self.route_trial=None
            self.cancelled=True
            try:
                if p.get('lease') is not None:p['lease'].release()
                # Consume the live arrival before serializing a potentially large
                # route report. The input observer remains open through handoff.
                if arrival is not None:continuation=self._continue_finished_trial(p,arrival)
            except Exception as error:
                reason=str(reason)+'; continuation stopped: '+str(error)
                if not self.cancelled:self.stop_action(str(error))
            finally:
                try:self._finish_trial_input_observer(p)
                except Exception as error:
                    reason=str(reason)+'; input observer cleanup: '+str(error)
                    self.stop_action(str(error))
            plan=p.get('plan')
            initial=None if plan is None else plan.initial if p['job']==SOURCE_JOB else plan
            record=dict(format=('eql-owner-source-travel-v1' if p['job']==SOURCE_JOB else
                                'eql-owner-crossing-travel-v1' if p['job']==CROSSING_JOB else
                                'eql-owner-destination-travel-v1' if p['job']==DESTINATION_JOB
                                else 'eql-owner-local-route-trial-v1'),record_id=p['trial_id'],
                scope=p['continuation']['scope'],
                destination=None if destination_evidence is None else json.loads(destination_evidence),
                outcome='arrived' if ((driver is not None and driver.session.phase=='arrived')
                    or (runtime is not None and runtime.corridor.phase=='complete')
                    or (source_runtime is not None and source_runtime.phase=='complete')) else 'stopped',
                reason=str(reason),motion_record=p['motion_record'],startup_pairs=p['startup_pairs'],
                incomplete_pair=None if p.get('collector') is None else p['collector'].snapshot(),
                startup_events=p['events'],route=None if driver is None else driver.session.snapshot(),
                crossing=None if runtime is None else runtime.snapshot(),
                source_route=None if source_runtime is None else source_runtime.snapshot(),
                source_itinerary=None if plan is None or p['job']!=SOURCE_JOB else plan.itinerary.record(),
                plan=None if initial is None else json.loads(initial.plan_bytes),
                geometry=None if initial is None else json.loads(initial.evidence_bytes),
                installed_region_model=(None if p['continuation']['region_model'] is None
                    else p['continuation']['region_model'].record()),
                owner_supervised=True,real_client_accepted=False,continuation=continuation)
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
            self.emit('Route trial '+record['outcome']+' · movement stopped · '+str(reason))

        def autopilot_tick(self,now):
            p=self.route_trial
            try:
                if p is not None:self._trial_current(p)
                result=super().autopilot_tick(now)
                p=self.route_trial
                if p is None:return result
                if p['stage'].startswith('startup_'):self._startup_tick(p)
                elif p.get('source_runtime') is not None:
                    p['source_runtime'].tick()
                    if p['source_runtime'].phase=='complete':
                        self._finish_trial('Fresh stopped position reached the source destination')
                elif p.get('corridor_runtime') is not None:
                    p['corridor_runtime'].tick()
                    if p['corridor_runtime'].corridor.phase=='complete':
                        self._finish_trial('Fresh expected destination pair observed; movement stopped')
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
