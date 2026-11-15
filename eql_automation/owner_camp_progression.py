"""Explicit camp progression attached to one real owner journey.

The initial Newbie trip uses the existing source job.  Only the controller's
recovered Goblin event opens the itinerary root; no second job or old motion
calibration is substituted for the camp's seven fresh probes.
"""
from copy import deepcopy
from dataclasses import dataclass, replace
import time

from .flat_record import flat_record_state
from .g2_safety_provider import GameWindowIdentity
from .motion_calibration import PROBES
from .native_region_policy import encoded
from .owner_camp_plan_provider import checked_fresh_fit, retained_probe_bounds
from .owner_camp_probe import CampProbePlan
from .owner_navigation_preflight import settings_identity, window_identity
from .owner_route_trial import SOURCE_JOB
from .route_step_sender import _fd_identity
from .supervised_camp_probe import SupervisedCampProbeDeclaration, SupervisedCampProbeScope
from .supervised_route import SupervisedRouteDeclaration, scope_limits
from .supervised_source import SupervisedSourcePolicy
from .zone_itinerary_budget import ZoneItineraryBudget


CAMP_PROGRESSION_JOB = 'camp_progression'


@dataclass(frozen=True)
class _OriginPreparation:
    controller: object
    origin: object
    pending: object
    metadata: object
    basis: bytes
    probe_plan: CampProbePlan


class _CampItineraryOwner:
    """Root binding for an actual camp origin, never an idle source request."""
    def __init__(self, engine, prepared, plan):
        p=prepared.pending
        self.engine=engine;self.prepared=prepared;self.plan=plan
        self.controller=prepared.controller;self.origin=prepared.origin
        self.request_bytes=self.controller.intent.request_bytes
        self.journey=p.journey;self.generation=p.generation;self.settings=p.settings
        self.epochs=(engine.supervised_epoch,engine.route_session_epoch)
        self.sender=p.sender;self.ui=p.ui;self.gate=p.gate
        self.tracker=p.tracker;self.reader=p.reader;self.window=p.window
        self.fd=self.ui.fileno();self.fd_identity=_fd_identity(self.fd)
        if (self.fd!=self.controller.intent.fd
                or self.fd_identity!=self.controller.intent.fd_identity):
            raise ValueError('Camp-origin sender differs from the originally tested descriptor')
        self.root=self._root=None;self.pending=self.initial_account=None
        self.starting=False;self.closed=False
        self._plan_pin=self._plan_state()
        self._state=self._identity()

    def _identity(self):
        return (id(self.engine),id(self.prepared),id(self.plan),id(self.controller),id(self.origin),
            self.request_bytes,id(self.journey),self.generation,self.settings,self.epochs,
            id(self.sender),id(self.ui),id(self.gate),id(self.tracker),id(self.reader),
            self.window,self.fd,self.fd_identity)

    def _plan_state(self):
        # The root checks the compact declaration.  Full copied guides are
        # checked at admission and handoffs, never serialized on a DOWN check.
        p=self.plan
        return (id(p.declaration),id(p.probe_bounds),flat_record_state(p.probe_bounds),
            p.bounds_basis,id(p.destination_provider),id(p.sections_provider),id(p.crossing_provider))

    def binding(self):
        e=self.engine
        self.controller.check_binding(e)
        descriptor=self.ui.fileno();descriptor_identity=_fd_identity(self.fd)
        settings=settings_identity(e.settings);queue_empty=e.jobs.empty()
        window=window_identity(e.gate,require_focus=False)
        self.controller.check_binding(e)
        if (self.closed or e.zone_itinerary_owner is not self or self._identity()!=self._state
                or self._plan_state()!=self._plan_pin or self.root is not self._root
                or self.root is not None and self.root.declaration is not self.plan.declaration
                or self.controller.origin is not self.origin
                or self.controller.root is not self.root
                or e.journey is not self.journey or e.cancel_generation!=self.generation
                or self.journey.generation!=self.generation or settings!=self.settings
                or self.epochs!=(e.supervised_epoch,e.route_session_epoch)
                or e.sender is not self.sender or self.sender.ui is not self.ui
                or e.gate is not self.gate or e.live_zone_tracker is not self.tracker
                or self.tracker.reader is not self.reader or self.tracker.closed
                or window!=self.window or descriptor!=self.fd or descriptor_identity!=self.fd_identity
                or e.stopping or e.cancelled or not queue_empty
                or self.sender.unfinished or self.sender.dismissed
                or self.pending is not None or self.initial_account is not None
                or self.journey.continue_camps is not True or self.journey._continue_camps is not True):
            raise ValueError('Camp-origin itinerary lost its actual owner, request or generation')
        return (id(self),self.generation,self.settings,self.epochs,id(self.sender),id(self.ui),
                id(self.gate),id(self.tracker),id(self.reader),self.window)

    def check(self):
        if self.root is not None:self.root.check()
        return self.binding()


class _CampItineraryAssetOwner:
    """Lazy copied assets pinned to the controller's admitted camp origin."""
    def __init__(self, engine, prepared):
        self.engine=engine;self.prepared=prepared;self.valid=True
        self.owner=self.root=None
        p=prepared.pending
        self.reader=p.reader;self.tail=p.reader.tail
        self.log_identity=(self.tail.identity,self.tail.epoch,self.tail.path)
        self.tracker_binding=p.tracker.owner_binding

    def check(self, *, copied=None, plan=None, identifier=None):
        e=self.engine;q=self.prepared;p=q.pending
        q.controller.check_binding(e)
        if not self.valid:raise ValueError('Camp-origin lazy asset binding was retired')
        if copied is not None and copied is not q.metadata.copied:
            raise ValueError('Camp-origin copied metadata was replaced')
        if plan is None:
            q.metadata.check();e._camp_position_current(p)
            if e.zone_itinerary_owner is not None or e._camp_progression_pending is not q:
                raise ValueError('Camp-origin plan must precede its single root')
            return None
        owner=e.zone_itinerary_owner
        if (type(owner) is not _CampItineraryOwner or owner.prepared is not q
                or owner.plan is not plan or type(owner.root) is not ZoneItineraryBudget):
            raise ValueError('Camp-origin assets require their exact owner and root')
        if self.owner is None:self.owner,self.root=owner,owner.root
        if owner is not self.owner or owner.root is not self.root:
            raise ValueError('Camp-origin itinerary owner or root changed')
        owner.check();p.tracker.check_binding()
        reader=self.reader;tail=self.tail;root=self.root
        if (p.tracker.reader is not reader or reader.tail is not tail
                or p.tracker.owner_binding is not self.tracker_binding
                or (tail.identity,tail.epoch,tail.path)!=self.log_identity or tail.identity is None or tail.partial
                or reader.expected_character!=owner.settings[2] or reader.expected_server!=owner.settings[3]
                or copied is not None and (encoded(reader.zone_ids)!=copied.catalog_record
                    or frozenset(reader.ambiguous_zone_names)!=copied.ambiguous)
                or owner.journey.destination_id!=identifier or root.leg.destination_id!=identifier
                or (reader.zone_id,reader.zone_display_name)!=(root.leg.source_zone_id,root.leg.source_name)
                or root.stage.phase not in ('walking','bootstrap') or not root.valid
                or owner.sender.held or getattr(owner.sender,'_eql_route_operation',None) is not None):
            raise ValueError('Camp-origin lazy assets differ from the current observed leg')
        owner.check()
        return root.stage,owner.journey,reader.zone_generation


def _origin_probe_plan(e,p,metadata,basis,clock):
    """Use the actual camp floor, retained hypotheses and new sealed fit."""
    from .camp_source_runtime import CampSourcePlan
    bounds=metadata.retained_bounds;guide=metadata.route_guide;sections=metadata.route_sections
    if (guide.radius!=bounds.body_radius or guide.body_height!=bounds.body_height
            or guide.wld_sha256!=p.floor._terrain.wld_sha256
            or guide.static_inventory_sha256!=p.floor._static.inventory_sha256):
        raise ValueError('Camp-origin guide differs from the actual retained floor')
    scope=None;maximum_seconds=scope_limits('destination_travel')[0]
    def policy(tx):
        nonlocal scope
        e._camp_position_current(p)
        if scope is None:
            budget=e._camp_sections_budget(p)
            expiry=min(p.probe_started+maximum_seconds,budget.expires_at,budget.parent_budget.expires_at)
            declaration=SupervisedCampProbeDeclaration(bounds.record_id,bounds.record_id,True,
                len(PROBES)*bounds.maximum_actual_hold)
            scope=SupervisedCampProbeScope(p.runtime,declaration=declaration,monitor=p.monitor,
                gate=p.gate,expected_window=GameWindowIdentity(*p.window),log_veto=p.probe_log_veto,
                check_current=lambda:e._camp_position_current(p),started_at=p.probe_started,
                expires_at=expiry,journey_budget=budget)
        return scope.policy(tx)
    def execution(runtime,calibration):
        from eqnav import steer
        e._camp_position_current(p)
        if scope is None or not scope.valid or scope.runtime is not runtime:
            raise ValueError('Original camp-origin probe scope must remain active')
        scope._check();fit=checked_fresh_fit(p,runtime,calibration);estimate=fit['estimate']
        onward=replace(bounds,record_id='camp-route-'+runtime.route_preparation.itinerary.sha256,
                       maximum_requested_hold=.1)
        def source_policy(ledger,current):
            scope._check();current()
            seconds,steps,distance,hold=scope_limits('destination_travel')
            remaining=scope.expires_at-runtime.clock()
            if not 0<remaining<=maximum_seconds:raise ValueError('Original camp-origin deadline expired')
            declaration=SupervisedRouteDeclaration('camp-route-'+fit['record_id'],
                ledger.observer.itinerary.sha256,onward.calibration_record_id,onward.record_id,
                False,min(seconds,remaining),steps,distance,min(hold,remaining),'camp_continuation',True)
            return SupervisedSourcePolicy(ledger,declaration=declaration,gate=p.gate,
                owner_input=p.monitor.observer,log_veto=p.probe_log_veto,
                expected_window=GameWindowIdentity(*p.window),topology_generation=p.monitor.topology,
                check_current=current,journey_budget=e._camp_sections_budget(p),release_deadline=scope.expires_at)
        result=CampSourcePlan(onward,steer,steer.Motion(run_speed=estimate['run_speed'],
            turn_rate=estimate['turn_rate'],right_sign=estimate['right_sign'],
            turn_latency=estimate['turn_latency'],back_speed=0.),estimate['final_heading'],.25,source_policy)
        e._camp_position_current(p);scope._check()
        return result
    return CampProbePlan(bounds,basis,policy,PROBES,maximum_seconds,guide,execution,
        metadata.declaration.legs[0].destination_id,metadata.selection.evidence,sections)


def make_camp_progression_engine(base, *, progression_provider=None, origin_provider=None,
                                 clock=time.monotonic):
    """Wrap the existing journey plus zone-itinerary engine, without a new job."""
    from .owner_camp_progression_assets import load_owner_camp_progression, load_camp_origin_itinerary
    if progression_provider is None:progression_provider=load_owner_camp_progression
    if origin_provider is None:origin_provider=load_camp_origin_itinerary
    if not all(callable(v) for v in (progression_provider,origin_provider,clock)):
        raise ValueError('Explicit camp progression providers and clock required')

    class CampProgressionEngine(base):
        def __init__(self,*args,**kwargs):
            self._camp_progression_request=None;self._camp_progression_pending=None
            self._progression_initial_handoff=None
            self._camp_progression_stopping=None
            super().__init__(*args,**kwargs)

        def _supervised_job_names(self):
            return (*super()._supervised_job_names(),CAMP_PROGRESSION_JOB)

        def post(self,name,value=None):
            if name==CAMP_PROGRESSION_JOB:value=deepcopy(value)
            return super().post(name,value)

        def handle_job(self,name,value):
            if name!=CAMP_PROGRESSION_JOB:return super().handle_job(name,value)
            from .camp_progression import CampProgressionSelection
            if type(value) is not dict or set(value)!={'declaration','epoch','generation','settings'}:return
            token=(value['generation'],value['epoch'],self.route_session_epoch,value['settings'],self.sender,self.gate)
            def check_request():
                settings=settings_identity(self.settings);empty=self.jobs.empty();busy=self._navigation_busy()
                if (token!=(self.cancel_generation,self.supervised_epoch,self.route_session_epoch,
                            settings,self.sender,self.gate) or self.stopping or not empty or busy
                        or self.journey is not None or self.camp_session is not None
                        or self.zone_itinerary_owner is not None):
                    raise ValueError('Camp progression request changed before its source journey')
            request=None
            try:
                check_request();declaration=value['declaration']
                if (type(declaration) is not dict or set(declaration)!={
                        'progression_id','open_flat_clear','owner_supervised_continuation'}
                        or declaration.get('progression_id')!='butcher-newbie-goblin-slave-mines'
                        or declaration.get('open_flat_clear') is not True
                        or declaration.get('owner_supervised_continuation') is not True):
                    raise ValueError('Explicit supervised Newbie to Slave Mines progression required')
                if type(self.settings.level) is not int or not 1<=self.settings.level<=4:
                    raise ValueError('Progression requires a configured integer level from 1 through 4')
                raw=encoded(declaration)
                selection=progression_provider(self,deepcopy(declaration))
                if type(selection) is not CampProgressionSelection:raise ValueError('Typed copied progression required')
                selection.check();check_request()
                request=(selection,raw,token);self._camp_progression_request=request
                delegated=dict(value,declaration=dict(open_flat_clear=True,
                    destination_id=selection.initial_destination_id,continue_camps=True))
                result=super().handle_job(SOURCE_JOB,delegated)
                if self._camp_progression_request is not request:return result
                j=self.journey
                if j is None or getattr(j,'progression',None) is None or self.supervised_motion is None:
                    raise ValueError('Initial progression source journey did not start')
                j.progression.check_binding(self)
                self.trace('camp_progression_started',progression_id=selection.profile_id,
                           destination_id=j.destination_id,real_client_accepted=False)
                return result
            except BaseException as error:
                if request is not None and self._camp_progression_request is request and self.journey is not None:
                    self.stop_action('Camp progression stopped: '+str(error))
                self.emit('Camp progression did not start: '+str(error))
            finally:
                if self._camp_progression_request is request:self._camp_progression_request=None

        def _prepare_supervised_job(self,name):
            request=self._camp_progression_request
            if request is not None:
                from .camp_progression import capture_progression_intent
                if name!=SOURCE_JOB:raise ValueError('Progression only adopts its first source job')
                selection,raw,token=request
                if token[:4]!=(self.cancel_generation,self.supervised_epoch,self.route_session_epoch,
                               settings_identity(self.settings)):
                    raise ValueError('Progression request was cancelled before journey capture')
                capture_progression_intent(self,self.journey,selection,raw,clock=clock)
            result=super()._prepare_supervised_job(name)
            if request is not None:
                if self._camp_progression_request is not request or self.journey is None:
                    raise ValueError('Progression cancelled during initial source loading')
                self.journey.progression.check_binding(self)
            return result

        def _continue_source_journey(self,p,token):
            c=getattr(token.journey,'progression',None)
            result=super()._continue_source_journey(p,token)
            if c is not None and isinstance(result,dict) and result.get('camp_started') is True:
                if self._progression_initial_handoff is not None:
                    self._progression_initial_handoff.append(token)
                else:c.adopt_camp_handoff(self,token,self.camp_session)
            return result

        def _advance_walking_section(self,w,arrival):
            c=getattr(w.journey,'progression',None)
            if c is None:return super()._advance_walking_section(w,arrival)
            if self._progression_initial_handoff is not None:raise ValueError('Reentrant initial camp handoff')
            pending=[];self._progression_initial_handoff=pending
            try:
                result=super()._advance_walking_section(w,arrival)
                if pending:
                    if len(pending)!=1:raise ValueError('Exactly one actual initial camp arrival required')
                    c.adopt_camp_handoff(self,pending[0],self.camp_session,trip=w)
                return result
            finally:
                if self._progression_initial_handoff is pending:self._progression_initial_handoff=None

        def _advance_camp_section(self,w,arrival):
            c=getattr(w.journey,'progression',None)
            final=w.index==len(w.sections.guides)-1
            result=super()._advance_camp_section(w,arrival)
            if c is not None and final and isinstance(result,dict) and result.get('camp_started') is True:
                c.adopt_camp_handoff(self,arrival,self.camp_session,trip=w)
            return result

        def _camp_continuation_available(self,j):
            if getattr(j,'progression',None) is None:return super()._camp_continuation_available(j)
            from .camp_progression import continuation_available
            return continuation_available(j)

        def _camp_probe_plan(self,p):
            c=getattr(p.journey,'progression',None)
            if c is None:return super()._camp_probe_plan(p)
            if not self._camp_continuation_available(p.journey):return None
            c.check_binding(self)
            if p.journey.destination_id!=c.selection.trigger_destination_id:
                return super()._camp_probe_plan(p)
            if p.camp.level not in (9,10):return None
            if self._camp_progression_pending is not None:raise ValueError('Camp origin cannot be prepared twice')
            origin=c.claim_goblin_origin(self,p)
            bounds,basis=retained_probe_bounds(p)
            metadata=origin_provider(c.selection,retained_bounds=bounds)
            from .owner_camp_progression_assets import CampOriginItineraryAssets
            if type(metadata) is not CampOriginItineraryAssets:raise ValueError('Typed camp-origin metadata required')
            metadata.check();c.check_binding(self);self._camp_position_current(p)
            plan=_origin_probe_plan(self,p,metadata,basis,clock);plan.state()
            c.check_binding(self)
            if (self.camp_position is not p or self.journey is not p.journey or p.cancelled
                    or self._camp_progression_pending is not None):
                raise ValueError('Camp origin cancelled during final plan validation')
            prepared=_OriginPreparation(c,origin,p,metadata,basis,plan)
            self._camp_progression_pending=prepared
            return plan

        def _camp_probe_started(self,p):
            q=self._camp_progression_pending
            if q is None or q.pending is not p:return super()._camp_probe_started(p)
            from .owner_zone_itinerary_assets import _bind_copied_itinerary_plan
            with self.g0_stop_lock:
                q.controller.check_binding(self);q.metadata.check()
                if self.zone_itinerary_owner is not None or p.probe_plan is not q.probe_plan:
                    raise ValueError('Camp origin lost its single selected probe plan')
                binding=_CampItineraryAssetOwner(self,q)
                plan=_bind_copied_itinerary_plan(self,q.metadata.copied,q.metadata.declaration,
                    q.metadata.probe_bounds,q.metadata.bounds_basis,binding,
                    check_request=lambda:q.controller.check_binding(self))
                owner=_CampItineraryOwner(self,q,plan)
                # Descriptor construction can deliver owner F8/F9. Never
                # publish the candidate after that cancellation boundary.
                q.controller.check_binding(self);self._camp_position_current(p)
                if (self._camp_progression_pending is not q or self.camp_position is not p
                        or self.journey is not p.journey or self.zone_itinerary_owner is not None
                        or p.cancelled or p.probe_plan is not q.probe_plan):
                    raise ValueError('Camp origin cancelled before owner publication')
                self.zone_itinerary_owner=owner
                root=None
                try:
                    initial=owner.binding()
                    root=ZoneItineraryBudget(plan.declaration,clock=clock,stop_lock=self.g0_stop_lock,
                        owner_binding=initial,binding_reader=owner.binding)
                    q.controller.check_binding(self)
                    if (self.zone_itinerary_owner is not owner or owner.closed
                            or self._camp_progression_pending is not q or self.camp_position is not p):
                        raise ValueError('Camp origin cancelled during root construction')
                    owner.root=owner._root=root;q.controller.bind_root(q.origin,root)
                    owner.check();result=super()._camp_probe_started(p);owner.check()
                    return result
                except BaseException:
                    owner.closed=True
                    if root is not None:root.cancel('Camp-origin root admission failed')
                    if self.zone_itinerary_owner is owner:self.zone_itinerary_owner=None
                    raise

        def _camp_position_current(self,p):
            result=super()._camp_position_current(p)
            owner=self.zone_itinerary_owner
            if type(owner) is _CampItineraryOwner:
                if owner.prepared.pending is not p:raise ValueError('Camp-origin position scope changed')
                owner.check()
            return result

        def _camp_trip_parent_budget(self,p,w):
            owner=self.zone_itinerary_owner
            if type(owner) is not _CampItineraryOwner:return super()._camp_trip_parent_budget(p,w)
            owner.check()
            if owner.prepared.pending is not p or w.pending is not p:
                raise ValueError('Camp-origin root cannot parent another trip')
            return owner.root

        def _camp_probe_input_release_deadline(self,p):
            owner=self.zone_itinerary_owner
            if type(owner) is not _CampItineraryOwner:return super()._camp_probe_input_release_deadline(p)
            owner.check()
            if owner.prepared.pending is not p:raise ValueError('Camp-origin deadline lost its probe scope')
            return min(owner.root.expires_at,p.probe_started+p.probe_plan.maximum_seconds)

        def _prepare_camp_itinerary_crossing(self,w,arrival,spec):
            owner=self.zone_itinerary_owner
            if type(owner) is not _CampItineraryOwner:
                return super()._prepare_camp_itinerary_crossing(w,arrival,spec)
            owner.check();owner.prepared.metadata.check();self._check_camp_section_arrival(w,arrival)
            from .owner_zone_itinerary_assets import _crossing_record
            row=owner.prepared.metadata.copied.assets[0]
            if (w.pending is not owner.prepared.pending or w.journey is not owner.journey
                    or w.destination_id!=owner.root.leg.destination_id
                    or w.index!=len(w.sections.guides)-1 or spec.destination_id!=w.destination_id
                    or row.identifier!=w.destination_id or _crossing_record(spec)!=row.crossing_record):
                raise ValueError('Camp-origin crossing lost its exact final section')
            return owner,w,arrival,spec

        def _commit_camp_itinerary_crossing(self,token,w,arrival):
            if token is None:return super()._commit_camp_itinerary_crossing(token,w,arrival)
            owner,trip,reached,spec=token
            if (type(owner) is not _CampItineraryOwner or self.zone_itinerary_owner is not owner
                    or trip is not w or reached is not arrival or spec.destination_id!=w.destination_id):
                raise ValueError('Camp-origin crossing admission token changed')
            owner.controller.commit_first_crossing(self,w,arrival);owner.check()

        def _terminal_itinerary_transferred(self,run,token):
            owner=self.zone_itinerary_owner
            if type(owner) is _CampItineraryOwner:
                if run.root is not owner.root or run.journey is not owner.journey:
                    raise ValueError('Camp progression terminal transfer changed owner')
                owner.controller.consume_terminal(token)
            return super()._terminal_itinerary_transferred(run,token)

        def _terminal_itinerary_camp_started(self,run,token,result):
            c=getattr(run.journey,'progression',None)
            if c is not None and isinstance(result,dict) and result.get('camp_started') is True:
                c.record_terminal_camp(self,token,self.camp_session)
            return super()._terminal_itinerary_camp_started(run,token,result)

        def stop_action(self,reason,*,keep_autopilot=False):
            j=getattr(self,'journey',None);c=getattr(j,'progression',None)
            if c is not None:
                try:
                    from .camp_progression import CampProgression
                    if type(c) is not CampProgression:raise ValueError('Typed progression owner changed')
                    self._camp_progression_stopping=(c.selection.profile_id,c.root is not None)
                    c.cancel(reason)
                except Exception as error:
                    reason=str(reason)+'; progression intent cleanup: '+str(error)
            self._camp_progression_pending=None;self._camp_progression_request=None
            return super().stop_action(reason,keep_autopilot=keep_autopilot)

        def autopilot_payload(self):
            data=super().autopilot_payload()
            c=getattr(getattr(self,'journey',None),'progression',None)
            if c is not None and c.phase not in ('consumed','terminal_camp'):
                data['camp_progression']=dict(progression_id=c.selection.profile_id,
                    phase=c.phase,root_started=c.root is not None,real_client_accepted=False)
            elif self._camp_progression_stopping is not None:
                if self._navigation_busy():
                    profile,root_started=self._camp_progression_stopping
                    data['camp_progression']=dict(progression_id=profile,phase='stopping',
                        root_started=root_started,real_client_accepted=False)
                else:self._camp_progression_stopping=None
            return data

    CampProgressionEngine.__name__='CampProgressionEngine'
    return CampProgressionEngine
