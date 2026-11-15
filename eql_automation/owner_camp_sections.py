"""Ordered walking sections after a genuine camp-level advance.

The initial camp probe scope stays intact. After its actual stopped arrival,
the camp is retired and ordinary SectionContinuation owns each later section.
No source-job dictionary, saved resume or intermediate camp is manufactured.
"""
from hashlib import sha256

from .flat_record import flat_record_state
from .journey_input_budget import JourneyBudgetDeclaration, JourneyInputBudget
from .native_region_policy import encoded
from .owner_navigation_preflight import settings_identity
from .owner_route_trial import zone_binding
from .section_continuation import SectionContinuation, capture_section_arrival
from .source_arrival import assert_retained_arrival
from .source_destinations import destination_spec
from .source_section_manifest import BoundWalkingSection, WalkingSections
from .supervised_route import scope_limits


class CampWalkingJourney:
    def __init__(self,p,*,epochs):
        plan=p.probe_plan;sections=plan.route_sections
        if type(sections) is not WalkingSections or sections.original is not plan.route_guide:
            raise ValueError('Actual camp plan and matching walking partition required')
        sections.check()
        self.pending=p;self.journey=p.journey;self.camp=p.camp;self.plan=plan
        self.sections=sections;self.destination_id=plan.destination_id
        self.plan_owner_state=plan.owner_state();self.plan_state=p.probe_plan_state
        self.sender=p.sender;self.ui=p.ui;self.gate=p.gate
        self.observer=p.monitor.observer;self.hotkey=p.hotkey;self.veto=p.probe_log_veto
        self.tracker=p.tracker;self.reader=p.reader;self.window=p.window
        self.zone=zone_binding(p.reader);self.generation=p.generation;self.settings=p.settings
        self.journey_settings=p.journey.settings
        self.from_destination=p.journey.destination_assets;self.from_id=p.journey.destination_id
        self.level_advance=p.level_advance;self.advance_state=p.level_advance_state
        self.epochs=epochs
        self.monitor=self._monitor=p.monitor
        self.budget=self._budget=self.runtime=self._runtime=None
        self.index=self._index=self.guard=self._guard=None
        self.stage=self._stage='initial'
        self._state=self.context()

    def context(self):
        return (id(self.pending),id(self.journey),id(self.camp),id(self.plan),id(self.sections),
            self.destination_id,id(self.plan_owner_state),id(self.plan_state),id(self.sender),id(self.ui),id(self.gate),id(self.observer),
            id(self.hotkey),id(self.veto),id(self.tracker),id(self.reader),self.window,self.zone,
            self.generation,self.settings,self.journey_settings,id(self.from_destination),self.from_id,
            id(self.level_advance),self.epochs,
            self.advance_state)

    def check(self,*,content=True):
        if (self.context()!=self._state or self.budget is not self._budget
                or self.runtime is not self._runtime or self.monitor is not self._monitor
                or self.index!=self._index or self.guard is not self._guard
                or self.stage!=self._stage or self.plan is not self.pending.probe_plan
                or self.sections is not self.plan.route_sections
                or self.plan.route_guide is not self.sections.original
                or self.camp.last_level_advance is not self.level_advance
                or flat_record_state(self.level_advance)!=self.advance_state
                or self.plan.destination_id!=self.destination_id
                or self.pending.probe_plan_state is not self.plan_state
                or self.plan.owner_state()!=self.plan_owner_state):
            raise ValueError('Camp walking trip lost its original owner or selected destination')
        if self.guard is None:self.sections.check()
        elif content:self.guard.check(self.index)
        else:self.guard.check_structure(self.index)

    def select(self,index):
        if self.index is not None:raise ValueError('Initial camp section cannot be selected twice')
        self.index=self._index=index
        self.guard=self._guard=BoundWalkingSection(self.sections,index)

    def advance(self):
        self.guard=self._guard=BoundWalkingSection(self.sections,self.index+1)
        self.index=self._index=self.guard.index

    def set_runtime(self,runtime):self.runtime=self._runtime=runtime
    def set_monitor(self,monitor):self.monitor=self._monitor=monitor
    def set_stage(self,stage):self.stage=self._stage=stage


def make_camp_sections_engine(base,*,section_provider,clock):
    if not callable(section_provider):raise ValueError('Explicit camp section loader required')

    class CampSectionsEngine(base):
        def __init__(self,*args,**kwargs):
            self.camp_walking=None;self.camp_section_run=None
            super().__init__(*args,**kwargs)

        def _load_camp_sections(self,destination_id,guide,*,root):
            return section_provider(destination_id,guide,root=root)

        def _camp_trip_binding(self,w,*,content=True):
            w.check(content=content);j=w.journey;p=w.pending
            if (self.camp_walking is not w or self.journey is not j or j.walking is not None
                    or j.generation!=w.generation or self.cancel_generation!=w.generation
                    or j.settings!=w.journey_settings or settings_identity(self.settings)!=w.settings
                    or (self.supervised_epoch,self.route_session_epoch)!=w.epochs
                    or j.continue_camps is not True or j._continue_camps is not True
                    or j.destination_assets is not w.from_destination or j.destination_id!=w.from_id
                    or j.camp_motion is not w.monitor or j.arrival_floor is not w.monitor.floor
                    or j.location_binding is not w.hotkey or p.cancelled
                    or self.sender is not w.sender or self.sender.ui is not w.ui or self.gate is not w.gate
                    or self.live_zone_tracker is not w.tracker or w.tracker.reader is not w.reader
                    or zone_binding(w.reader)!=w.zone or not self.jobs.empty()
                    or self.active or self.target_ready or self.preparing or self.stopping or self.cancelled
                    or self._camp_command is not None or w.sender.unfinished or w.sender.dismissed):
                raise ValueError('Camp walking owner, generation, sender or zone changed')
            if w.stage=='initial':
                if (j.phase!='camp' or self.camp_position is not p or self.camp_session is not w.camp
                        or self.autopilot is not w.camp or not w.camp.running
                        or w.camp.phase!='probe_measurement'):
                    raise ValueError('Camp probes lost their real originating camp')
            elif w.stage=='sections':
                if (j.phase not in ('camp_section_handoff','camp_walking_sections')
                        or self.camp_position is not None or self.camp_session is not None
                        or self.autopilot is not None or w.camp.running or not p.runtime.closed):
                    raise ValueError('Camp sections lost exclusive ownership after camp retirement')
            else:raise ValueError('Camp walking stage ended')
            # Value-only public binding; the internal flat-record state also
            # contains class objects and is checked separately above.
            return w._state[:-1]

        def _camp_trip_budget_binding(self,w):
            c=self.camp_section_run
            active=(type(c) is SectionContinuation and c is w.runtime
                    and not c.closed and c.phase not in ('complete','stopped'))
            return self._camp_trip_binding(w,content=not active)

        def _camp_probe_started(self,p):
            if p.probe_plan.route_sections is None:return super()._camp_probe_started(p)
            if self.camp_walking is not None:raise ValueError('A camp trip already owns navigation')
            w=CampWalkingJourney(p,epochs=(self.supervised_epoch,self.route_session_epoch));self.camp_walking=w
            n=len(w.sections.guides)
            seconds,pulses,distance,hold=scope_limits('destination_travel')
            spec=destination_spec(w.destination_id)
            declaration=JourneyBudgetDeclaration(sha256(encoded(w.sections.original.record())).hexdigest(),
                spec.identifier,spec.arrival_mode,n,n*seconds,n*pulses,n*hold,n*distance)
            binding=self._camp_trip_binding(w)
            budget=JourneyInputBudget(declaration,clock=clock,stop_lock=self.g0_stop_lock,
                owner_binding=binding,binding_reader=lambda:self._camp_trip_budget_binding(w))
            w.budget=w._budget=budget;budget.check()
            self.trace('camp_walking_sections_started',destination_id=w.destination_id,
                section_count=n,budget=budget.snapshot(),initial_section=None,real_client_accepted=False)
            budget.check()

        def _camp_sections_budget(self,p):
            w=self.camp_walking
            if w is None or w.pending is not p:raise ValueError('No original camp trip budget')
            self._camp_trip_binding(w);w.budget.check()
            return w.budget

        def _camp_source_prepared(self,p):
            if p.probe_plan.route_sections is None:return super()._camp_source_prepared(p)
            w=self.camp_walking;self._camp_trip_binding(w)
            prepared=p.runtime.route_preparation
            if (w.pending is not p or prepared.sections is not w.sections
                    or prepared.full_itinerary is None):
                raise ValueError('Initial camp route lost its actual-position section selection')
            prepared.check_start(p.runtime.route_start)
            w.select(prepared.section_index);w.budget.check()

        def _check_camp_section_arrival(self,w,arrival):
            self._camp_trip_binding(w);w.budget.check();w.sections.check()
            guide=w.sections.guides[w.index]
            if (arrival.budget is not w.budget or arrival._claim!=[False]
                    or arrival.guide_sha256!=sha256(encoded(guide.record())).hexdigest()
                    or tuple(arrival.runtime.driver.plan.record()['goal'])!=guide.goal):
                raise ValueError('Camp section receipt differs from the ordered partition')
            assert_retained_arrival(arrival.runtime,arrival.receipt,arrival.checkpoint,clock())

        def _capture_finished_camp_source(self,p):
            if p.probe_plan.route_sections is None:return super()._capture_finished_camp_source(p)
            w=self.camp_walking
            self._camp_position_current(p);self._camp_trip_binding(w)
            if w.pending is not p or w.index is None:raise ValueError('No measured initial camp section')
            token=capture_section_arrival(p.route_runtime,w.budget)
            try:
                self._check_camp_section_arrival(w,token)
                p.route_record=p.route_runtime.snapshot();p.route_record['arrival']=token.checkpoint.snapshot()
                p.route_complete=True
                return token.checkpoint,token
            except BaseException as error:
                token.checkpoint.invalidate(error);raise

        def _continue_finished_camp_source(self,p,token):
            if p.probe_plan.route_sections is None:return super()._continue_finished_camp_source(p,token)
            w=self.camp_walking
            with self.g0_stop_lock:
                # The real initial camp scope has released its reader. Retire
                # the camp without stop_action or a new cancellation generation.
                if (w is None or w.pending is not p or self.journey is not w.journey
                        or self.camp_position is not None or not p.runtime.closed
                        or p.lease.active or p.tracker.lease is not None
                        or self.camp_session is not p.camp or self.autopilot is not p.camp
                        or p.sender.held or p.sender.unfinished):
                    raise ValueError('Initial camp section did not release its actual owner scope')
                p.camp.stop('Walking to the next camp',now=clock())
                self.camp_last_result=p.camp.snapshot()
                self.camp_session=self.autopilot=self._camp_binding=self._camp_posture=None
                self._camp_progress_report=None
                w.set_stage('sections');w.journey.phase='camp_section_handoff'
                return self._advance_camp_section(w,token)

        def _advance_camp_section(self,w,arrival):
            old=self.camp_section_run
            try:
                with self.g0_stop_lock:
                    self._check_camp_section_arrival(w,arrival)
                    if old is not None:
                        if old is not w.runtime or old.completed_arrival is not arrival or old.busy:
                            raise ValueError('Camp continuation no longer owns this completion')
                        old.release();self.camp_section_run=None;w.set_runtime(None)
                    if w.tracker.lease is not None or arrival.runtime.lease.active:
                        raise ValueError('Camp section reader must be released before handoff')
                    if w.index==len(w.sections.guides)-1:
                        from .owner_camp_section_arrival import finish_camp_sections
                        return finish_camp_sections(self,w,arrival,clock)
                    w.journey.phase='camp_section_handoff';w.advance()
                    lease=w.tracker.acquire()
                    try:
                        import navigation
                        from eqnav import steer
                        binding=self._camp_trip_binding(w)
                        def pump():self.pump();self.autopilot_tick(clock())
                        successor=SectionContinuation(arrival,lease,w.sections.guides[w.index],
                            owner_binding=binding,binding_reader=lambda:self._camp_trip_binding(w),
                            generation_reader=lambda:self.cancel_generation,fit_library=navigation,
                            steering_library=steer,pump=pump,
                            command_state_clear=lambda:self._route_idle() and not self.cancelled and self.jobs.empty())
                        self.camp_section_run=successor;w.set_runtime(successor)
                        successor._check();successor.monitor.check(successor._monitor_binding())
                        w.monitor.transfer_to(successor.monitor)
                        w.set_monitor(successor.monitor)
                        w.journey.camp_motion=successor.monitor;w.journey.arrival_floor=arrival.checkpoint
                        w.journey.phase='camp_walking_sections'
                        self._camp_trip_binding(w);w.sections.check()
                        return dict(phase='camp_walking_sections',section=w.index+1,
                            section_count=len(w.sections.guides),camp_started=False,real_client_accepted=False)
                    except BaseException:
                        lease.release();raise
            except BaseException as error:
                arrival.checkpoint.invalidate(error)
                if old is not None and old.closed and not old.monitor.closed:old.monitor.close(str(error))
                raise

        def _owner_navigation_active(self):
            w=self.camp_walking
            if w is not None and w.stage=='sections':
                try:self._camp_trip_binding(w)
                except (ValueError,AttributeError):return False
                return True
            return super()._owner_navigation_active()

        def _navigation_busy(self):
            return self.camp_section_run is not None or super()._navigation_busy()

        def _cleanup_camp_section(self):
            c=self.camp_section_run
            if c is not None and not c.busy and c.phase=='stopped':
                c.release();self.camp_section_run=None

        def stop_action(self,reason,*,keep_autopilot=False):
            w,self.camp_walking=self.camp_walking,None
            if w is not None and w.budget is not None:w.budget.cancel(reason)
            if self.camp_section_run is not None:self.camp_section_run.cancel(reason)
            try:return super().stop_action(reason,keep_autopilot=keep_autopilot)
            finally:self._cleanup_camp_section()

        def autopilot_tick(self,now):
            self._cleanup_camp_section()
            w=self.camp_walking;c=self.camp_section_run
            if w is None or w.stage=='initial':return super().autopilot_tick(now)
            # Camp has genuinely retired; do not run base camp or travel ticks
            # while a section owns the reader, including nested sender pumps.
            if c is None or c.busy:return
            try:
                c.tick()
                if c.phase=='complete':
                    result=self._advance_camp_section(w,c.completed_arrival)
                    self.trace('camp_walking_section_completed',continuation=result,
                        runtime=c.snapshot(),probes=c.runtime.snapshot(),route=c.route_runtime.snapshot(),
                        real_client_accepted=False)
                    if self.camp_section_run is not None:
                        self.emit(f'Next camp section {w.index+1}/{len(w.sections.guides)} · fresh measurement · F9 stop')
            except BaseException as error:
                if self.journey is w.journey:self.stop_action(str(error))
                else:c.cancel(str(error))
                self.emit('Next camp travel stopped: '+str(error))
            finally:self._cleanup_camp_section()

        def autopilot_payload(self):
            data=super().autopilot_payload();w=self.camp_walking
            if w is not None:
                data.update(journey_next_destination_id=w.destination_id,
                    journey_section=None if w.index is None else w.index+1,
                    journey_sections=len(w.sections.guides))
                if w.stage=='sections':
                    data.update(state='running',phase=f'Next camp section {w.index+1}/{len(w.sections.guides)}')
            return data

    return CampSectionsEngine
