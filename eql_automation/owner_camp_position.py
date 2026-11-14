"""Collect one fresh post-recovery position pair on the reached camp floor.

This uses the existing sender, owner-tested location hotbutton and exclusive
reader. Ordinarily it sends no movement, target, chat or combat command.
An optional explicit plan may hand the same scope to a finite probe runtime;
no default plan or movement policy is provided.
"""
import json
import time
from types import SimpleNamespace

from .camp_stopped_height import measure_camp_stopped_height
from .camp_probe_preparation import CampProbePreparation
from .camp_probe_runtime import CampProbeRuntime
from .camp_probe_calibration import reduce_camp_probes
from .camp_source_runtime import CampSourcePlan,CampSourceRuntime
from .camp_floor_checkpoint import CampFloorCheckpoint
from .camp_session import CampLevelAdvance
from .owner_camp_arrival import capture_camp_arrival,continue_camp_arrival
from .flat_record import flat_record_state
from .motion_calibration import CalibrationUnavailable
from .native_region_policy import encoded
from .owner_camp_probe import CampProbePlan
from .ground_binding import finite
from .location_hotkey import HOTKEY_CODES, OwnerLocationHotkey, send_location_hotkey
from .motion_collection import CommandReceipt, LocationRequest
from .owner_navigation_preflight import settings_identity, window_identity
from .scene_log_veto import SceneLogVeto
from .stopped_location_pair import StoppedLocationPair


def make_camp_position_engine(base_engine,*,clock=time.monotonic,probe_plan_provider=None):
    if probe_plan_provider is not None and not callable(probe_plan_provider):
        raise ValueError('Camp probe plan provider must be explicit and callable')
    class CampPositionEngine(base_engine):
        def __init__(self,*args,**kwargs):
            self.camp_position=None
            self.camp_position_last_result=None
            super().__init__(*args,**kwargs)

        def _navigation_busy(self):
            return self.camp_position is not None or super()._navigation_busy()

        def _camp_location_lease(self):
            p=self.camp_position
            if (p is not None and not p.cancelled and self.journey is p.journey
                    and self.camp_session is p.camp and self.live_zone_tracker is p.tracker
                    and p.lease.active and p.tracker.lease is p.lease):
                return p.lease
            return None

        def _camp_position_current(self,p):
            if (self.camp_position is not p or p.cancelled or p.route_runtime is not p._route_runtime
                    or p.probe_log_veto is not p._probe_log_veto
                    or type(p.probe_log_veto) is not SceneLogVeto
                    or (p.probe_log_veto.tail,p.probe_log_veto.tail.path,p.probe_log_veto.clock,
                        p.probe_log_veto.cancel_generation)!=p._probe_veto_state):
                raise ValueError('Camp position collection ended')
            p.lease.check();p.hotkey.check()
            current=self._camp_current(observe_input=p.route_runtime is None)
            window=window_identity(self.gate,require_focus=True)
            now=clock()
            probing=p.probe_plan is not None
            if probing and type(p.probe_plan) is not CampProbePlan:
                raise ValueError('Camp probe plan changed')
            key=(p.route_runtime.current_input_key() if p.route_runtime is not None else
                 p.runtime.current_input_key() if p.runtime is not None else
                 HOTKEY_CODES[p.hotkey.key_name] if p.sending else None)
            deadline=(p.probe_started+p.probe_plan.maximum_seconds if probing else p.started+8)
            if (not current or self.camp_position is not p or p.cancelled
                    or self.journey is not p.journey or p.journey.phase!='camp'
                    or self.camp_session is not p.camp
                    or p.camp.phase!=('probe_measurement' if probing else 'position_check')
                    or not p.camp.running or self.cancelled or self.stopping
                    or self.cancel_generation!=p.generation or settings_identity(self.settings)!=p.settings
                    or self.live_zone_tracker is not p.tracker or p.tracker.reader is not p.reader
                    or p.tracker.lease is not p.lease or not p.lease.active
                    or self.sender is not p.sender or self.sender.ui is not p.ui or self.gate is not p.gate
                    or window!=p.window or self.active or self.target_ready or self.preparing
                    or self._camp_command is not None or self.sender.unfinished or self.sender.dismissed
                    or self.sender.held-({key} if key is not None else set())
                    or not self.jobs.empty() or p.journey.arrival_floor is not p.floor or not p.floor.valid
                    or p.journey.location_binding is not p.hotkey or p.journey.camp_motion is not p.monitor
                    or not p.monitor.valid or p.monitor.closed
                    or p.camp.recovery is not p.recovery or p.recovery.phase!='recovered'
                    or p.camp.last_level_advance is not p.level_advance
                    or (None if p.level_advance is None else flat_record_state(p.level_advance))
                        !=p.level_advance_state
                    or p.recovery.last_stand_completed_at!=p.released_at
                    or probing and p.probe_plan.state()!=p.probe_plan_state
                    or not finite(now) or not p.started<=now<=deadline
                    or now<max(self.command_pause_until,self.rotation.busy_until)):
                raise ValueError('Camp position owner, recovery or input scope changed')
            return p.owner_binding

        def _camp_location_input_permitted(self):
            p=self.camp_position
            if (p is None or not p.busy or not p.sending or p.request is None
                    or p.collector is None or p.collector.phase!='requesting'
                    or p.collector.pending is not p.request):return False
            try:
                self._camp_position_current(p)
                return (self.camp_position is p and not p.cancelled and p.sending
                    and p.collector.phase=='requesting' and p.collector.pending is p.request)
            except (OSError,ValueError,RuntimeError):return False

        def _camp_probe_input_permitted(self):
            p=self.camp_position
            if p is None:return False
            runtime=p.route_runtime if p.route_runtime is not None else p.runtime
            if (not p.busy or runtime is None or not runtime.busy
                    or getattr(p.sender,'_eql_route_operation',None) is None
                    or runtime.current_input_key() is None):return False
            try:
                self._camp_position_current(p)
                return (self.camp_position is p and not p.cancelled and runtime.busy
                        and runtime.current_input_key() is not None)
            except (OSError,ValueError,RuntimeError):return False

        def _camp_probe_plan(self,p):
            return None if probe_plan_provider is None else probe_plan_provider(self,p)

        def _camp_recovery_complete(self,camp,now):
            j=self.journey
            if j is None or j.phase!='camp' or camp.kills==0:
                return super()._camp_recovery_complete(camp,now)
            advance=camp.last_level_advance
            if j.height_check_done:
                # Ordinary stationary camping still checks once. A configured
                # continuation provider can reconsider only a new current-log
                # level increase, after automatic spell preparation finishes.
                if (probe_plan_provider is None or not j.continue_camps
                        or type(advance) is not CampLevelAdvance
                        or advance is j.last_considered_level_advance
                        or advance.generation!=camp.generation
                        or advance.generation!=j.generation or advance.generation!=self.cancel_generation
                        or advance.level!=camp.level or advance.level!=self.settings.level
                        or camp.level_source!='client_log' or camp.pending_level is not None
                        or camp.preparation_due or self.preparing):
                    return super()._camp_recovery_complete(camp,now)
            lease=None
            try:
                if (not self._camp_current() or self.camp_session is not camp
                        or self.camp_position is not None or self.journey is not j
                        or camp.phase!='recovery' or camp.recovery.phase!='recovered'
                        or j.arrival_floor is None or j.camp_motion is None
                        or not isinstance(j.location_binding,OwnerLocationHotkey)
                        or not finite(camp.recovery.last_stand_completed_at)
                        or self.sender.held or self.sender.unfinished
                        or getattr(self.sender,'_eql_route_operation',None) is not None):
                    raise ValueError('Reached camp, completed recovery and idle sender required')
                j.location_binding.check()
                tracker=self.live_zone_tracker
                lease=tracker.acquire()
                p=SimpleNamespace(journey=j,camp=camp,tracker=tracker,reader=tracker.reader,
                    lease=lease,baseline=tracker.reader.log_line_seq,floor=j.arrival_floor,
                    monitor=j.camp_motion,hotkey=j.location_binding,sender=self.sender,ui=self.sender.ui,
                    gate=self.gate,window=window_identity(self.gate,require_focus=True),
                    generation=self.cancel_generation,settings=settings_identity(self.settings),
                    recovery=camp.recovery,released_at=camp.recovery.last_stand_completed_at,
                    started=clock(),busy=False,sending=False,releasing=False,cancelled=False,reason='',
                    collector=None,request=None,result=None,events=[],runtime=None,route_runtime=None,_route_runtime=None,
                    route_record=None,route_complete=False,
                    probe_plan=None,probe_plan_state=None,probe_started=None,probe_record=None,
                    calibration_seal=None,
                    position_record=None,probe_complete=False,probe_log_veto=None,_probe_log_veto=None,
                    _probe_veto_state=None,level_advance=advance,
                    level_advance_state=None if advance is None else flat_record_state(advance))
                p.owner_binding=('camp-position',id(j),id(camp),id(p.sender),id(p.ui),
                    id(tracker),id(p.reader),p.generation,p.settings,p.window)
                self.camp_position=p;camp.phase='position_check'
                # Start once at recovery entry. A later probe/source policy
                # must not skip hazards while fresh positions are collected
                # or geometry is prepared. This separate reader grants no
                # movement permission and never consumes the location cursor.
                p.probe_log_veto=p._probe_log_veto=SceneLogVeto(p.reader.tail.path,
                    expected_character=p.reader.expected_character,expected_server=p.reader.expected_server,
                    cancel_generation=p.generation,clock=clock)
                p._probe_veto_state=(p.probe_log_veto.tail,p.probe_log_veto.tail.path,
                    p.probe_log_veto.clock,p.probe_log_veto.cancel_generation)
                p.collector=StoppedLocationPair(lease,released_at=p.released_at,
                    check_current=lambda:self._camp_position_current(p),clock=clock,
                    local_wall_clock=self.camp_wall)
                self._camp_position_current(p)
                self.trace('camp_position_started',minimum_log_seq=p.baseline,
                    floor_checkpoint_sha256=p.floor.sha256,stand_command_completed_at=p.released_at,
                    level=camp.level,level_advance_seq=None if advance is None else advance.camp_log_seq,
                    posture_observed=None,movement_sent=False)
                self.emit('Checking stopped position after recovery · F9 stops')
            except (OSError,ValueError,RuntimeError) as error:
                if self.journey is j and self.camp_session is camp:
                    self.stop_action('Camp position collection stopped: '+str(error))
                if lease is not None and self.camp_position is None:lease.release()

        def _stop_camp_position(self,p,reason):
            # F8 already cancelled the camp and queued assist after release.
            # Cleanup failures must not turn that same cancellation into a new
            # stop generation which silently loses the owner's F8 request.
            if not p.cancelled:self.stop_action('Camp position collection stopped: '+str(reason))

        def _camp_position_hotkey(self,p,request):
            collector=p.collector
            def current():
                self._camp_position_current(p);collector.check()
                if (not p.busy or not p.sending or p.collector is not collector
                        or p.request is not request or collector.pending is not request
                        or collector.phase!='requesting'):
                    raise ValueError('Camp location request changed')
            def pump():
                self.pump();self.autopilot_tick(clock())
            p.request=request;p.sending=True
            try:
                receipt=send_location_hotkey(p.sender,binding=p.hotkey,owner_input=p.monitor.observer,
                    lock=self.g0_stop_lock,clock=clock,expires_at=request.expires_at,
                    ensure_current=current,cancel=lambda reason:self._stop_camp_position(p,reason),
                    pump=pump,record_event=p.events.append)
                return CommandReceipt(receipt.pulse.down_started_at,receipt.released_at)
            finally:
                p.sending=False;p.request=None

        def _release_camp_position(self,p):
            if p.releasing:return
            p.releasing=True
            try:
                if p._route_runtime is not None and (p._route_runtime.busy or p.sender.held
                        or getattr(p.sender,'_eql_route_operation',None) is not None):
                    raise ValueError('Camp route still owns input or work')
                if p.runtime is not None:p.runtime.release()
                else:p.lease.release()
            finally:
                if self.camp_position is p and (p.runtime is None or p.runtime.closed):self.camp_position=None
                p.releasing=False
            if p.cancelled:
                self.camp_position_last_result=dict(outcome='stopped',reason=p.reason,
                    collection=None if p.collector is None else p.collector.snapshot(),
                    location_events=list(p.events),movement_sent=False,real_client_accepted=False)
                if p.runtime is not None:
                    if p.probe_record is not None and not p.probe_complete:
                        p.probe_record.update(p.runtime.snapshot())
                    self.camp_position_last_result.update(
                        outcome='probe_complete' if p.probe_complete else 'stopped',
                        initial_position=p.position_record,
                        probe=p.probe_record if p.probe_record is not None else p.runtime.snapshot(),
                        movement_sent=any(e['kind']=='camp_probe_pulse' and e['receipt'] is not None
                                          for e in p.runtime.events))
                if p._route_runtime is not None:
                    route=p.route_record if p.route_complete else p._route_runtime.snapshot()
                    self.camp_position_last_result.update(
                        outcome='route_complete' if p.route_complete else 'stopped',route=route,
                        movement_sent=self.camp_position_last_result['movement_sent'] or any(
                            e['kind']=='source_pulse' for e in p._route_runtime.events))
                self.trace('camp_position_stopped',**self.camp_position_last_result)

        def _start_camp_probe(self,p,record):
            plan=self._camp_probe_plan(p)
            self._camp_position_current(p)
            if plan is None:return False
            if type(plan) is not CampProbePlan:raise ValueError('Exact explicit camp probe plan required')
            state=plan.state()
            p.position_record=record;p.probe_plan=plan;p.probe_plan_state=state
            p.probe_started=clock();p.camp.phase='probe_measurement'
            p.collector=None
            preparation=CampProbePreparation(p.floor,p.result,p.lease,probe_kind=plan.probes[0].key,
                bounds=plan.bounds,bounds_basis=plan.bounds_basis,owner_binding=p.owner_binding,
                binding_reader=lambda:self._camp_position_current(p),clock=clock,local_wall_clock=self.camp_wall)
            def pump():self.pump();self.autopilot_tick(clock())
            p.runtime=CampProbeRuntime(preparation,sender=p.sender,hotkey=p.hotkey,
                owner_input=p.monitor.observer,stop_lock=self.g0_stop_lock,
                movement_policy_factory=plan.policy_factory,check_current=lambda:self._camp_position_current(p),
                command_state_clear=lambda:self._camp_command is None and not self.active and not self.target_ready,
                pump=pump,probes=plan.probes,maximum_seconds=plan.maximum_seconds,log_veto=p.probe_log_veto)
            self._camp_position_current(p)
            self.trace('camp_probe_started',initial_height_sha256=p.result.sha256,
                floor_checkpoint_sha256=p.floor.sha256,destination_id=plan.destination_id,
                real_client_accepted=False)
            self._camp_position_current(p)
            self.emit('Measuring camp movement · F8 assist · F9 stops')
            return True

        def _camp_probe_tick(self,p):
            if p.busy:
                self._camp_position_current(p)
                return
            p.busy=True
            try:
                self._camp_position_current(p);p.runtime.tick()
                if p.runtime.phase=='stopped':self._stop_camp_position(p,p.runtime.reason)
                elif p.runtime.phase=='complete':
                    self._camp_position_current(p)
                    p.probe_record=p.runtime.snapshot()
                    p.probe_record['results']=[json.loads(r.payload) for r in p.runtime.results]
                    p.probe_record['preparations']=[tx.preparation.snapshot() for tx in p.runtime.transactions]
                    import navigation  # Existing retained rotation tool's fitter.
                    try:
                        fit=reduce_camp_probes(p.runtime,legacy=navigation,
                            record_id='camp-'+p.runtime.results[-1].sha256)
                        calibration=dict(status='conditional',estimate=fit)
                    except CalibrationUnavailable as error:
                        calibration=dict(status='unavailable',reason=str(error))
                    self._camp_position_current(p)
                    p.probe_record['calibration']=calibration
                    # Freeze the actual reducer result before route planning
                    # advances the reader. Later travel must not substitute a
                    # saved fit or quietly edit its estimates during callbacks.
                    p.calibration_seal=(calibration,encoded(calibration),p.runtime.reference,
                        tuple(p.runtime.transactions),tuple(p.runtime.results))
                    if p.probe_plan.route_guide is not None:
                        p.runtime.prepare_route(p.probe_plan.route_guide)
                        self._camp_position_current(p)
                        self.emit('Planning next camp route · F8 assist · F9 stops')
                        return
                    p.probe_complete=True
                    # A later planner must explicitly adopt the reached reference.
                    # Do not resume the old stationary camp after movement.
                    self.stop_action('Camp probes complete · stopped before next route')
                elif p.runtime.phase=='route_ready':
                    self._camp_position_current(p)
                    p.runtime.route_preparation.check_start(p.runtime.route_start)
                    p.probe_record.update(p.runtime.snapshot())
                    p.probe_complete=True
                    factory=p.probe_plan.route_plan_factory
                    if factory is not None:
                        plan=factory(p.runtime,p.probe_record['calibration'])
                        self._camp_position_current(p)
                        if type(plan) is not CampSourcePlan:
                            raise ValueError('Explicit camp route execution plan required')
                        p.route_runtime=p._route_runtime=CampSourceRuntime(p.runtime,plan,
                            check_current=lambda:self._camp_position_current(p),
                            mode_reader=lambda:'camp_route' if not p.cancelled else 'off',
                            generation_reader=lambda:self.cancel_generation,generation=p.generation)
                        self._camp_position_current(p)
                        self.emit('Starting next camp route · F8 assist · F9 stops')
                        return
                    self.stop_action('Next camp route prepared · execution is not connected')
            except Exception as error:
                self._stop_camp_position(p,error)
            finally:
                p.busy=False
                if p.cancelled:self._release_camp_position(p)

        def _camp_source_tick(self,p):
            if p.busy:
                self._camp_position_current(p)
                return
            p.busy=True;token=None;reached=None
            try:
                self._camp_position_current(p);p.route_runtime.tick()
                if p.route_runtime.phase=='stopped':self._stop_camp_position(p,p.route_runtime.reason)
                elif p.route_runtime.phase=='complete':
                    self._camp_position_current(p)
                    # Capture the actual newly observed floor before stop closes
                    # the ancestor scope. Do not resume the camp we just left.
                    reached=CampFloorCheckpoint(p.route_runtime.ledger)
                    p.route_record=p.route_runtime.snapshot()
                    p.route_record['arrival']=reached.snapshot()
                    self._camp_position_current(p);p.route_complete=True
                    if p.probe_plan.destination_id is not None:
                        token=capture_camp_arrival(self,p,reached)
                    else:
                        self.stop_action('Next camp route reached · stopped before camp selection')
            except Exception as error:self._stop_camp_position(p,error)
            finally:
                p.busy=False
                if p.cancelled:self._release_camp_position(p)
                if reached is not None and token is None:reached.invalidate('No new camp adopted the reached floor')
            if token is None:return
            try:
                # No key or route operation remains. Return the reader before
                # the existing camp startup drains logs and prepares spells.
                self._release_camp_position(p)
                result=continue_camp_arrival(self,token,clock)
                self.camp_position_last_result=dict(outcome='route_complete',route=p.route_record,
                    probe=p.probe_record,initial_position=p.position_record,continuation=result,
                    movement_sent=any(e['kind']=='source_pulse' for e in p.route_runtime.events),
                    real_client_accepted=False)
                self.trace('camp_position_complete',**self.camp_position_last_result)
            except Exception as error:
                # A callback may already have consumed F8/F9. Never create a
                # second stop generation and erase that owner's assist request.
                if self.journey is p.journey:self._stop_camp_position(p,error)
                token.checkpoint.invalidate(str(error))

        def _camp_position_tick(self,p):
            if p.route_runtime is not None:return self._camp_source_tick(p)
            if p.runtime is not None:return self._camp_probe_tick(p)
            if p.busy:
                self._camp_position_current(p)
                if p.collector is not None:p.collector.check()
                return
            p.busy=True
            complete=False
            try:
                self._camp_position_current(p)
                request=p.collector.tick()
                if isinstance(request,LocationRequest):
                    p.collector.command_sent(request,self._camp_position_hotkey(p,request))
                if p.collector.phase=='complete':
                    p.result=measure_camp_stopped_height(p.floor,p.reader,p.collector.first,p.collector.second,
                        minimum_log_seq=p.baseline,released_at=p.released_at,owner_binding=p.owner_binding,
                        binding_reader=lambda:self._camp_position_current(p),clock=clock,
                        local_wall_clock=self.camp_wall)
                    self._camp_position_current(p)
                    complete=True
            except (OSError,ValueError,RuntimeError) as error:
                self._stop_camp_position(p,error)
            finally:
                p.busy=False
                if p.cancelled:self._release_camp_position(p)
            if not complete or p.cancelled:return
            record=dict(outcome='complete',collection=p.collector.snapshot(),
                height=json.loads(p.result.payload),height_sha256=p.result.sha256,
                location_events=p.events,movement_sent=False,real_client_accepted=False)
            try:
                if self._start_camp_probe(p,record):return
            except Exception as error:
                self._stop_camp_position(p,error)
                return
            self._release_camp_position(p)
            if (self.journey is not p.journey or self.camp_session is not p.camp
                    or not self._camp_current() or p.cancelled):return
            if (p.camp.last_level_advance is not p.level_advance
                    or (None if p.level_advance is None else flat_record_state(p.level_advance))
                        !=p.level_advance_state):
                self.stop_action('Camp level changed during position release');return
            p.journey.height_check_done=True
            p.journey.last_considered_level_advance=p.level_advance
            self.camp_position_last_result=record
            p.camp.record('stopped_height_checked',height_sha256=p.result.sha256)
            self.trace('camp_position_complete',**record)
            # Base hook rechecks the camp after trace callbacks before resuming.
            super()._camp_recovery_complete(p.camp,clock())

        def stop_action(self,reason,*,keep_autopilot=False):
            p=self.camp_position
            if p is not None:
                p.cancelled=True;p.reason=str(reason)
                if p._route_runtime is not None:p._route_runtime.cancel(reason)
                if p.runtime is not None:p.runtime.cancel(reason)
                if p.collector is not None:p.collector.cancel(reason)
                p.lease.active=False
                if not p.busy:self._release_camp_position(p)
            return super().stop_action(reason,keep_autopilot=keep_autopilot)

        def autopilot_tick(self,now):
            p=self.camp_position
            if p is not None:
                try:self._camp_position_tick(p)
                except (OSError,ValueError,RuntimeError) as error:
                    self._stop_camp_position(p,error)
                return
            return super().autopilot_tick(now)

        def autopilot_payload(self):
            result=super().autopilot_payload()
            if self.camp_position is not None:
                result['phase']='Checking stopped position after recovery'
                collector=self.camp_position.collector
                result['camp_position_phase']='starting' if collector is None else collector.phase
                if self.camp_position.runtime is not None:
                    result['phase']=('Planning next camp route' if self.camp_position.runtime.route_guide is not None
                                     else 'Measuring camp movement')
                    result['camp_probe_phase']=self.camp_position.runtime.phase
                    result['journey_next_destination_id']=self.camp_position.probe_plan.destination_id
                if self.camp_position.route_runtime is not None:
                    result['phase']='Traveling to next camp'
                    result['camp_route_phase']=self.camp_position.route_runtime.phase
            result['camp_position_last_result']=self.camp_position_last_result
            return result

    return CampPositionEngine
