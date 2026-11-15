"""Finite walking sections in the existing owner travel job, without camps between.

The original destination and pending job remain provenance. Only a healthy
in-memory stopped receipt advances the section; cancellation never restarts it.
"""
from dataclasses import dataclass
from hashlib import sha256

from .current_source_itinerary import plan_current_source_itinerary
from .journey_input_budget import JourneyBudgetDeclaration, JourneyInputBudget
from .native_region_policy import encoded
from .owner_navigation_preflight import settings_identity, window_identity
from .owner_route_trial import SOURCE_JOB, zone_binding
from .section_continuation import SectionContinuation, capture_section_arrival
from .source_arrival import assert_retained_arrival
from .source_destinations import destination_spec
from .source_section_manifest import BoundWalkingSection, WalkingSections
from .supervised_route import scope_limits


@dataclass(frozen=True)
class WalkingHandoff:
    journey: object
    walking: object
    arrival: object


class WalkingJourney:
    def __init__(self,journey,pending,sections,index):
        self.journey,self.pending,self.sections=journey,pending,sections
        self.section_guard=self._section_guard=BoundWalkingSection(sections,index)
        self.index=self._index=index
        self.initial_index=index
        self.budget=self._budget=None
        self.runtime=self._runtime=None
        self.sender=pending['sender'];self.ui=self.sender.ui
        self.observer=pending['observer'];self.veto=pending['veto']
        self.hotkey=pending['binding'];self.topology=pending['topology']
        self.tracker=pending['continuation']['tracker'];self.reader=self.tracker.reader
        self.destination=pending['continuation']['destination']
        self.window=pending['window'];self.zone=zone_binding(self.reader)
        self.generation=journey.generation;self.settings=journey.settings
        self.epochs=pending['epoch'],pending['continuation']['route_epoch']
        self._state=self._context()

    def _context(self):
        return (id(self.journey),id(self.pending),id(self.sections),self.initial_index,
            id(self.sender),id(self.ui),id(self.observer),id(self.veto),id(self.hotkey),self.topology,
            id(self.tracker),id(self.reader),id(self.destination),self.window,self.zone,
            self.generation,self.settings,self.epochs)

    def check(self,*,current_content=True):
        if self.section_guard is not self._section_guard:
            raise ValueError('Active section guard changed')
        if current_content:self.section_guard.check(self.index)
        else:self.section_guard.check_structure(self.index)
        p=self.pending
        if (self._context()!=self._state or self.index!=self._index
                or not self.initial_index<=self.index<len(self.sections.guides)
                or self.budget is not self._budget or self.runtime is not self._runtime
                or p['observer'] is not self.observer or p['veto'] is not self.veto
                or p['binding'] is not self.hotkey or p['topology']!=self.topology
                or p['continuation']['destination'] is not self.destination
                or p['continuation']['tracker'] is not self.tracker):
            raise ValueError('Walking journey lost its original guide, index or owner context')

    def set_runtime(self,runtime):self.runtime=self._runtime=runtime

    def advance(self):
        guard=BoundWalkingSection(self.sections,self.index+1)
        self.index=self._index=guard.index
        self.section_guard=self._section_guard=guard


def make_walking_sections_engine(base,*,section_provider,clock):
    if not callable(section_provider):raise ValueError('Explicit walking-section provider required')

    class WalkingSectionsEngine(base):
        def __init__(self,*args,**kwargs):
            self.section_run=None
            super().__init__(*args,**kwargs)

        def _walking_partition(self,destination):
            return section_provider(self,destination)

        def _plan_source_start(self,p,planner,collector,destination,options):
            sections=self._walking_partition(destination)
            self._trial_current(p)
            if sections is None:return super()._plan_source_start(p,planner,collector,destination,options)
            if type(sections) is not WalkingSections or sections.original is not destination.guide:
                raise ValueError('Destination provider must retain the exact full guide')
            result=plan_current_source_itinerary(planner,p['lease'].reader,collector.first,collector.second,
                guide=destination.guide,sections=sections,
                maximum_seconds=min(240.,p['expires']-clock()),**options)
            self._trial_current(p)
            j=self.journey
            if j is None or j.phase!='travel' or j.walking is not None:
                raise ValueError('No unchanged initial journey for walking sections')
            j.walking=WalkingJourney(j,p,sections,result.section_index)
            self._section_binding(j.walking)
            return result

        def _section_binding(self,w,*,current_content=True):
            w.check(current_content=current_content);j=w.journey
            if (self.journey is not j or j.walking is not w
                    or j.generation!=w.generation or self.cancel_generation!=w.generation
                    or j.settings!=w.settings or settings_identity(self.settings)!=w.settings
                    or (self.supervised_epoch,self.route_session_epoch)!=w.epochs
                    or j.continue_camps is not j._continue_camps
                    or j.destination_assets is not w.destination
                    or j.destination_id!=w.destination.destination_id
                    or self.sender is not w.sender or self.sender.ui is not w.ui
                    or self.gate is not w.pending['gate'] or self.live_zone_tracker is not w.tracker
                    or w.tracker.reader is not w.reader or zone_binding(w.reader)!=w.zone
                    or self.stopping or not self.jobs.empty() or self.camp_session is not None
                    or j.phase not in ('travel','section_handoff','walking_sections')):
                raise ValueError('Walking journey owner, destination, generation or zone changed')
            return (id(j),w.generation,w.settings,id(w.destination),id(w.sender),id(w.ui),
                    id(self.gate),id(w.tracker),id(w.reader),id(w.observer),id(w.veto),w.zone,w.window)

        def _section_budget_binding(self,w):
            c=self.section_run
            # The active child checks the complete current guide after its
            # final budget callback. Budget accounting only needs the pinned
            # owner/partition structure inside that child; all other phases
            # retain full current-section validation.
            active=(type(c) is SectionContinuation and c is w.runtime
                and not c.closed and c.phase not in ('complete','stopped'))
            return self._section_binding(w,current_content=not active)

        def _section_parent_budget(self,p):
            return None

        def _source_journey_budget(self,p):
            j=self.journey;w=None if j is None else j.walking
            if w is None:return super()._source_journey_budget(p)
            self._section_binding(w)
            w.sections.check()
            if w.pending is not p or w.budget is not None:
                raise ValueError('Whole-journey budget cannot be reset')
            n=len(w.sections.guides)-w.initial_index
            seconds,pulses,distance,hold=scope_limits('destination_travel')
            spec=destination_spec(j.destination_id)
            limits=JourneyBudgetDeclaration(sha256(encoded(w.sections.original.record())).hexdigest(),
                spec.identifier,spec.arrival_mode,n,n*seconds,n*pulses,n*hold,n*distance)
            binding=self._section_binding(w)
            budget=JourneyInputBudget(limits,clock=clock,stop_lock=self.g0_stop_lock,
                owner_binding=binding,binding_reader=lambda:self._section_budget_binding(w),
                parent_budget=self._section_parent_budget(p))
            w.budget=w._budget=budget
            budget.check()
            self.trace('journey_sections_started',destination_id=j.destination_id,
                initial_section=w.index+1,section_count=len(w.sections.guides),budget=budget.snapshot(),
                real_client_accepted=False)
            budget.check()
            return budget

        def _owner_navigation_active(self):
            j=self.journey
            if j is not None and j.phase in ('section_handoff','walking_sections'):
                try:self._section_binding(j.walking)
                except (ValueError,AttributeError):return False
                return True
            return super()._owner_navigation_active()

        def _navigation_busy(self):
            return self.section_run is not None or super()._navigation_busy()

        def _capture_trial_continuation(self,p):
            j=self.journey;w=None if j is None else j.walking
            if w is None:return super()._capture_trial_continuation(p)
            r=p.get('source_runtime')
            if r is None or r.phase!='complete':return None
            with self.g0_stop_lock:
                self._section_binding(w);w.budget.check()
                if w.pending is not p or p['job']!=SOURCE_JOB or p['busy']:
                    raise ValueError('Initial walking section is not idle')
                token=capture_section_arrival(r,w.budget)
                try:
                    self._check_section_arrival(w,token)
                    j.phase='section_handoff'
                    return WalkingHandoff(j,w,token)
                except BaseException as error:
                    token.checkpoint.invalidate(error);w.budget.cancel(error);raise

        def _check_section_arrival(self,w,token):
            self._section_binding(w);w.budget.check()
            w.sections.check()
            expected=sha256(encoded(w.sections.guides[w.index].record())).hexdigest()
            if (token.budget is not w.budget or token.guide_sha256!=expected
                    or token._claim!=[False]
                    or tuple(token.runtime.driver.plan.record()['goal'])!=w.sections.guides[w.index].goal):
                raise ValueError('Section receipt differs from the next ordered guide')
            assert_retained_arrival(token.runtime,token.receipt,token.checkpoint,clock())

        def _continue_finished_trial(self,p,token):
            if type(token) is not WalkingHandoff:return super()._continue_finished_trial(p,token)
            try:return self._advance_walking_section(token.walking,token.arrival)
            except BaseException as error:
                if self.journey is token.journey:self.stop_action(str(error))
                raise

        def _advance_walking_section(self,w,arrival):
            old=self.section_run
            try:return self._advance_walking_section_owned(w,arrival)
            except BaseException as error:
                # The old lease may already be released, including when a
                # subsequent acquire/freshness check fails before construction.
                arrival.checkpoint.invalidate(error)
                if old is not None and old.closed and not old.monitor.closed:
                    old.monitor.close(str(error))
                raise

        def _advance_walking_section_owned(self,w,arrival):
            from .owner_journey_runtime import Arrival
            old=self.section_run;j=w.journey
            with self.g0_stop_lock:
                self._check_section_arrival(w,arrival)
                if old is not None:
                    if old is not w.runtime or old.completed_arrival is not arrival or old.busy:
                        raise ValueError('Section completion lost the current continuation')
                    old.release();self.section_run=None;w.set_runtime(None)
                if w.tracker.lease is not None or arrival.runtime.lease.active:
                    raise ValueError('Completed section must release its reader before handoff')
                if w.index==len(w.sections.guides)-1:
                    # This is the already captured final receipt, never a new
                    # checkpoint from a retired runtime or a fabricated camp.
                    now=clock();self._check_section_arrival(w,arrival)
                    arrival._claim[0]=True
                    token=Arrival(j,w.pending,arrival.runtime,arrival.receipt,w.tracker,w.zone,w.window,
                        w.sender,self.gate,now,j.destination_id,w.destination,w.destination.source_evidence,
                        arrival.motion_basis,arrival.checkpoint)
                    j.arrival_floor=arrival.checkpoint;j.phase='handoff';j.walking=None
                    w.budget.cancel('Walking destination reached; navigation budget retired')
                    try:
                        result=self._continue_source_journey(w.pending,token)
                        w.sections.check()
                        if old is not None and self.journey is j and j.phase in ('camp','source_crossing'):
                            successor=(j.camp_motion if j.phase=='camp' else self.source_crossing_run.monitor)
                            prior=old.monitor.last_observed_at
                            if prior is not None and (successor.last_observed_at is None or prior>successor.last_observed_at):
                                successor.last_observed_at=prior
                            successor.check(self._camp_motion_binding() if j.phase=='camp'
                                            else self.source_crossing_run._monitor_binding())
                            old.monitor.transfer_to(successor)
                        w.sections.check()
                        return result
                    finally:
                        if old is not None and not old.monitor.closed:
                            old.monitor.close('Final walking handoff ended')
                j.phase='section_handoff'
                self._section_binding(w)
                w.advance()
                self.cancelled=False  # Same owner generation; no new job or budget.
                lease=w.tracker.acquire()
                try:
                    binding=self._section_binding(w)
                    w.sections.check()
                    def pump():self.pump();self.autopilot_tick(clock())
                    import navigation
                    from eqnav import steer
                    successor=SectionContinuation(arrival,lease,w.sections.guides[w.index],
                        owner_binding=binding,binding_reader=lambda:self._section_binding(w),
                        generation_reader=lambda:self.cancel_generation,fit_library=navigation,
                        steering_library=steer,pump=pump,
                        command_state_clear=lambda:self._route_idle() and not self.cancelled and self.jobs.empty())
                    self.section_run=successor;w.set_runtime(successor)
                    successor._check()
                    if old is not None:
                        successor.monitor.check(successor._monitor_binding())
                        old.monitor.transfer_to(successor.monitor)
                    w.sections.check()
                    j.phase='walking_sections'
                    self._section_binding(w)
                    return dict(phase='walking_sections',section=w.index+1,
                        section_count=len(w.sections.guides),camp_started=False,real_client_accepted=False)
                except BaseException:
                    lease.release()
                    if old is not None and not old.monitor.closed:old.monitor.close('Section handoff failed')
                    raise

        def _finish_trial_input_observer(self,p):
            c=self.section_run
            if c is not None and c.owner_input is p['observer']:
                c._check();return
            return super()._finish_trial_input_observer(p)

        def _cleanup_section(self):
            c=self.section_run
            if c is None or c.busy:return
            if c.phase=='stopped':
                c.release();self.section_run=None

        def stop_action(self,reason,*,keep_autopilot=False):
            j=self.journey;w=None if j is None else j.walking
            if w is not None and w.budget is not None:w.budget.cancel(reason)
            if self.section_run is not None:self.section_run.cancel(reason)
            try:return super().stop_action(reason,keep_autopilot=keep_autopilot)
            finally:self._cleanup_section()

        def autopilot_payload(self):
            data=super().autopilot_payload();j=self.journey
            w=None if j is None else j.walking
            if w is not None:
                data['journey_section']=w.index+1;data['journey_sections']=len(w.sections.guides)
            if self.section_run is not None:
                label=('Stopping travel' if w is None else
                    f'Travel section {w.index+1}/{len(w.sections.guides)}')
                data.update(state='running',phase=label+' · '+self.section_run.phase)
            return data

        def autopilot_tick(self,now):
            self._cleanup_section()
            result=super().autopilot_tick(now)
            c=self.section_run
            if c is None:return result
            journey=self.journey
            try:
                if c.busy:return result
                c.tick()
                if c.phase=='complete':
                    w=self.journey.walking
                    continuation=self._advance_walking_section(w,c.completed_arrival)
                    self.trace('journey_section_completed',section=continuation,
                        runtime=c.snapshot(),probes=c.runtime.snapshot(),route=c.route_runtime.snapshot(),
                        real_client_accepted=False)
                    if self.section_run is not None:
                        self.emit(f'Travel section {w.index+1}/{len(w.sections.guides)} · fresh movement measurement · F9 stop')
            except BaseException as error:
                # F8 can run after the old controller was released but before
                # the successor is published. Its phase then stays complete;
                # owner identity, not that phase, decides who still owns stop.
                if journey is not None and self.journey is journey:self.stop_action(str(error))
                else:c.cancel(str(error))
                self.emit('Travel stopped: '+str(error))
            finally:self._cleanup_section()
            return result

    return WalkingSectionsEngine
