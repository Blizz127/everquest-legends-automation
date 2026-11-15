"""One explicit itinerary after its first actual crossing, without a new job.

The original root owns the input observer through destination measurements,
walking sections and later crossings. Every floor and fit comes from the newly
reached zone. Copied guides and explicit hypotheses do not establish live safety.
"""
from dataclasses import dataclass, field
from hashlib import sha256
import json

from .camp_probe_runtime import CampProbeRuntime
from .destination_floor_bootstrap import DestinationFloorBootstrap
from .destination_bootstrap_runtime import DestinationBootstrapRuntime
from .destination_source_runtime import DestinationSourceDeclaration, start_destination_source
from .flat_record import flat_record_state
from .g2_safety_provider import focused_game_identity
from .ground_binding import finite
from .journey_input_budget import JourneyBudgetDeclaration, JourneyInputBudget
from .native_region_policy import encoded
from .owner_input_observer import OwnerInputObservation
from .owner_source_assets import SourceDestinationAssets
from .owner_source_crossing import OwnerSourceCrossingRuntime, PinnedSourceCrossingSpec
from .route_geometry import RouteMotionBounds
from .route_step_sender import _fd_identity
from .section_continuation import SectionContinuation, capture_section_arrival
from .source_arrival import assert_retained_arrival
from .source_destinations import destination_spec
from .source_section_manifest import BoundWalkingSection, WalkingSections
from .supervised_camp_probe import SupervisedCampProbeDeclaration
from .supervised_route import scope_limits
from .zone_itinerary_budget import ZoneItineraryBudget, ZoneItineraryDeclaration, _declaration_state


@dataclass(frozen=True)
class ZoneItineraryPlan:
    declaration: ZoneItineraryDeclaration
    probe_bounds: RouteMotionBounds
    bounds_basis: bytes
    destination_provider: object
    sections_provider: object
    crossing_provider: object
    _state: tuple = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        if (type(self.declaration) is not ZoneItineraryDeclaration
                or type(self.probe_bounds) is not RouteMotionBounds
                or type(self.bounds_basis) is not bytes or not self.bounds_basis
                or not all(callable(v) for v in
                    (self.destination_provider, self.sections_provider, self.crossing_provider))):
            raise ValueError('Explicit pinned itinerary, independent bounds and asset providers required')
        self.declaration.validate()
        self.probe_bounds.validate_values(calibration_record_id=self.probe_bounds.calibration_record_id,
                                         maximum_step_seconds=.2)
        basis=json.loads(self.bounds_basis)
        if (not isinstance(basis,dict) or not basis or encoded(basis)!=self.bounds_basis
                or not 2<=len(self.declaration.legs)<=8):
            raise ValueError('Canonical planning hypotheses and at least two crossing legs required')
        object.__setattr__(self,'_state',self.state())

    def state(self):
        return (_declaration_state(self.declaration),id(self.probe_bounds),flat_record_state(self.probe_bounds),
                self.bounds_basis,id(self.destination_provider),id(self.sections_provider),id(self.crossing_provider))

    def check(self):
        if self.state()!=self._state:
            raise ValueError('Selected itinerary plan changed')


class ZoneItineraryRuntime:
    """Own the same observer/reader across a sequence of checked child scopes."""
    def __init__(self,engine,journey,first_crossing,*,plan,root,check_current,pump,
                 command_state_clear,fit_library,steering_library,clock=None):
        if (type(first_crossing) is not OwnerSourceCrossingRuntime
                or type(plan) is not ZoneItineraryPlan or type(root) is not ZoneItineraryBudget
                or first_crossing.journey is not journey or first_crossing.engine is not engine
                or first_crossing.journey_budget is not root or root.declaration is not plan.declaration
                or root.stage.phase!='arrival' or root.stage.leg_index!=0
                or clock is not None and clock is not root.clock
                or not all(callable(v) for v in (check_current,pump,command_state_clear))):
            raise ValueError('Actual first crossing and its original explicit itinerary scope required')
        self.engine,self.journey,self.plan,self.root=engine,journey,plan,root
        self.current,self.pump,self.command_clear=check_current,pump,command_state_clear
        self.fit_library,self.steering_library=fit_library,steering_library
        self.clock,self.wall,self.lock=root.clock,first_crossing.wall,root.lock
        self.generation=first_crossing.generation
        self.sender,self.ui=first_crossing.sender,first_crossing.ui
        self.fd,self.fd_identity=self.ui.fileno(),_fd_identity(self.ui.fileno())
        self.owner_input,self.topology=first_crossing.owner_input,first_crossing.topology
        self.gate,self.window,self.hotkey=first_crossing.gate,first_crossing.window,first_crossing.hotkey
        self.tracker,self.reader=first_crossing.lease._tracker,first_crossing.reader
        self.lease=self._lease=first_crossing.lease
        self.started,self.expires_at=root.started,root.expires_at
        self._times=self.started,self.expires_at
        self.last_at=self.clock()
        self.phase,self.reason,self.busy,self.closed='claim','',False,False
        self.leg_index=0
        self.transfer=None
        self.veto=None
        self.bootstrap=self.source=self.section=self.crossing=None
        self._bootstrap=self._source=self._section=self._crossing=None
        self.assets=self.sections=self.crossing_spec=self.child_budget=None
        self._assets=self._sections=self._crossing_spec=self._child_budget=None
        self.section_index=self.section_guard=None
        self.records=[]
        self._observer_closed=False
        self.owner_binding=(root.owner_binding,id(self),self.generation)
        self._context=(engine,journey,plan,root,check_current,pump,command_state_clear,
            fit_library,steering_library,self.clock,self.wall,self.lock,self.sender,self.ui,
            self.owner_input,self.gate,self.window,self.hotkey,self.tracker,self.reader)
        self._generation=self.generation
        self._topology=self.topology
        with self.lock:
            self._check_context()
            transfer=first_crossing.transfer_destination(check_current=self._check_owner)
            # Retain the token before invoking any callback: old crossing
            # cleanup no longer owns it once transfer_destination succeeds.
            self.transfer=transfer
            try:
                transfer.claim()
                self.records.append(dict(kind='crossing',leg=0,
                    crossing=json.loads(transfer.crossing_evidence),
                    arrival=json.loads(transfer.arrival_evidence)))
                self.veto=transfer.log_veto
                self._begin_destination()
            except BaseException as error:
                self.cancel(error)
                self.release()
                raise

    def _check_owner(self):
        if self.closed or self.phase=='stopped':
            raise ValueError(self.reason or 'Itinerary runtime ended')
        self.current()
        self.root.check()
        now=self.clock()
        generation=self.engine.cancel_generation
        actual=(self.engine,self.journey,self.plan,self.root,self.current,self.pump,self.command_clear,
            self.fit_library,self.steering_library,self.clock,self.wall,self.lock,self.sender,self.ui,
            self.owner_input,self.gate,self.window,self.hotkey,self.tracker,self.reader)
        if (self.closed or self.phase=='stopped' or any(a is not b for a,b in zip(self._context,actual))
                or self.generation!=self._generation or type(generation) is not int or generation!=self.generation
                or self.topology!=self._topology or self.root.clock is not self.clock or self.root.lock is not self.lock
                or (self.started,self.expires_at)!=self._times
                or self.sender.ui is not self.ui or self.ui.fileno()!=self.fd
                or _fd_identity(self.fd)!=self.fd_identity
                or not finite(now) or not self.started<=self.last_at<=now<=self.expires_at):
            raise ValueError('Itinerary owner, generation, sender or fixed deadline changed')
        self.plan.check()
        self.last_at=now
        return self.owner_binding

    def _check_context(self):
        binding=self._check_owner()
        if (self.lease is not self._lease or self.bootstrap is not self._bootstrap
                or self.source is not self._source or self.section is not self._section
                or self.crossing is not self._crossing or self.assets is not self._assets
                or self.sections is not self._sections or self.crossing_spec is not self._crossing_spec
                or self.child_budget is not self._child_budget
                or self.tracker.reader is not self.reader or self.root.stage.leg_index!=self.leg_index
                or self.journey.destination_id!=self.root.leg.destination_id
                or self.phase!='claim' and self.journey.destination_assets is not self.assets):
            raise ValueError('Itinerary child ownership changed')
        stages={'claim':('arrival',),'load_destination':('bootstrap',),'bootstrap':('bootstrap',),
            'adopting':('walking',),'source':('walking',),'section_handoff':('walking',),
            'sections':('walking',),'crossing_handoff':('crossing',),
            'crossing':('crossing','loading','arrival'),'finishing':('arrival','complete'),
            'complete':('complete',)}
        if self.root.stage.phase not in stages.get(self.phase,()):
            raise ValueError('Itinerary root stage differs from its actual child phase')
        if self.phase not in ('finishing','complete'):
            self.lease.check()
            if self.lease.reader is not self.reader:
                raise ValueError('Itinerary reader changed')
        if self.section_guard is not None:
            self.section_guard.check_structure(self.section_index)
        self.hotkey.check()
        return binding

    def _binding(self):
        return self._check_context()

    def _scene(self):
        self._check_context()
        if self.phase=='crossing':
            self.crossing.check_current()
            self._check_context()
            return
        began=self.clock()
        before=self.owner_input.sample()
        log=self.veto.poll()
        after=self.owner_input.sample()
        window=focused_game_identity(self.gate)
        self._check_context()
        now=self.last_at
        if (window!=self.window or not 0<=now-began<=.1
                or any(type(v) is not OwnerInputObservation or not v.clear_at(now)
                    or v.topology_generation!=self.topology for v in (before,after))
                or not log.continuity_available or log.reason is not None
                or log.cancel_generation!=self.generation):
            raise ValueError('Itinerary physical input, focus or hazard veto')

    def current_input_key(self):
        if not self.busy or self.closed:return None
        for child in (self.crossing,self.section,self.source,self.bootstrap):
            if child is not None:
                key=child.current_input_key()
                if key is not None:return key
        return None

    def _begin_destination(self):
        self._check_owner()
        self.root.advance(self.root.stage,'bootstrap',zone_id=self.root.leg.destination_zone_id)
        self.leg_index=self.root.stage.leg_index
        self.journey.destination_id=self.root.leg.destination_id
        self.journey.destination_assets=None
        self.phase='load_destination'
        self._check_context()

    def _load_destination(self):
        identifier=self.root.leg.destination_id
        assets=self.plan.destination_provider(identifier)
        self._scene()
        if type(assets) is not SourceDestinationAssets or assets.destination_id!=identifier:
            raise ValueError('Destination provider changed the selected itinerary leg')
        assets.check()
        sections=self.plan.sections_provider(assets)
        crossing=self.plan.crossing_provider(identifier)
        self._scene()
        # Asset loading does not hold the owner stop lock. Only publish a new
        # child after its construction and callbacks have preserved that owner.
        with self.lock:
            self._scene()
            if (self.phase!='load_destination' or self.root.leg.destination_id!=identifier
                    or (assets.planner.zone_id,assets.planner.zone_name)!=(self.reader.zone_id,self.reader.zone_display_name)
                    or assets.planner.zone_id!=self.root.leg.source_zone_id
                    or type(crossing) is not PinnedSourceCrossingSpec or crossing.destination_id!=identifier
                    or crossing.expected_zone_line.sha256!=self.root.leg.expected_zone_line_sha256
                    or sections is not None and (type(sections) is not WalkingSections or sections.original is not assets.guide)
                    or assets.guide.radius!=self.plan.probe_bounds.body_radius
                    or assets.guide.body_height!=self.plan.probe_bounds.body_height):
                raise ValueError('Reached zone, guide, crossing or independent body hypotheses differ')
            assets.check()
            if sections is not None:sections.check()
            boot=candidate=None
            try:
                boot=DestinationFloorBootstrap(assets.planner,self.lease,bounds=self.plan.probe_bounds,
                    bounds_basis=self.plan.bounds_basis,owner_binding=self.owner_binding,binding_reader=self._binding,
                    generation=self.generation,generation_reader=lambda:self.engine.cancel_generation,
                    record_id='itinerary-destination-'+str(self.leg_index),clock=self.clock,local_wall_clock=self.wall,
                    maximum_seconds=min(1500.,self.expires_at-self.clock()))
                candidate=DestinationBootstrapRuntime(boot,sender=self.sender,hotkey=self.hotkey,
                    owner_input=self.owner_input,stop_lock=self.lock,gate=self.gate,expected_window=self.window,
                    topology_generation=self.topology,log_veto=self.veto,
                    declaration=SupervisedCampProbeDeclaration('itinerary-destination-'+str(self.leg_index),
                        self.plan.probe_bounds.record_id,True,7*self.plan.probe_bounds.maximum_actual_hold),
                    check_current=self._check_context,command_state_clear=self.command_clear,pump=self.pump,
                    fit_library=self.fit_library,journey_budget=self.root)
                candidate._check_scene()
                self._scene()
                self.assets=self._assets=assets
                self.sections=self._sections=sections
                self.crossing_spec=self._crossing_spec=crossing
                self.journey.destination_assets=assets
                self.bootstrap=self._bootstrap=candidate
                self.phase='bootstrap'
            except BaseException as error:
                if candidate is not None:
                    candidate.cancel(error)
                    candidate.release(close_observer=False)
                elif boot is not None:
                    boot.cancel(error)
                raise

    def _start_source(self):
        with self.lock:
            self._check_context()
            return self._start_source_owned()

    def _start_source_owned(self):
        b=self.bootstrap
        b.fresh_fit()
        self._check_context()
        self.root.advance(self.root.stage,'walking',zone_id=self.root.leg.source_zone_id)
        self.phase='adopting'
        self.section_index=0 if self.sections is None else b.runtime.route_preparation.section_index
        if self.sections is not None:self.section_guard=BoundWalkingSection(self.sections,self.section_index)
        count=1 if self.sections is None else len(self.sections.guides)-self.section_index
        seconds,pulses,distance,hold=scope_limits('destination_travel')
        declaration=JourneyBudgetDeclaration(sha256(encoded(self.assets.guide.record())).hexdigest(),
            self.root.leg.destination_id,'zone_crossing',count,count*seconds,count*pulses,count*hold,count*distance)
        self.child_budget=self._child_budget=JourneyInputBudget(declaration,clock=self.clock,stop_lock=self.lock,
            owner_binding=self.owner_binding,binding_reader=self._binding,parent_budget=self.root)
        source_declaration=DestinationSourceDeclaration('itinerary-route-'+str(self.leg_index),True,
            min(seconds,self.expires_at-self.clock()),pulses,distance,min(hold,self.expires_at-self.clock()),.25)
        candidate=None
        try:
            candidate=start_destination_source(b,declaration=source_declaration,
                legacy=self.steering_library,check_current=self._check_context,
                mode_reader=lambda:'camp_route' if self.phase in ('adopting','source') else 'off',
                generation_reader=lambda:self.engine.cancel_generation,generation=self.generation,
                journey_budget=self.child_budget)
            candidate.check_current()
            self._scene()
            self.source=self._source=candidate
            self.phase='source'
        except BaseException as error:
            if candidate is not None:candidate.cancel(error)
            raise

    def _retire_monitor(self,monitor):
        # This controller already owns the exact continuously open observer.
        # Retiring a child's historical floor must never close that observer.
        if monitor.observer is not self.owner_input or monitor.topology!=self.topology or monitor.closed:
            raise ValueError('Itinerary lost the original physical observer')
        monitor.check_binding(monitor.binding)
        self._scene()
        monitor.invalidate('Observer retained by the owning zone itinerary')
        monitor.closed=True

    def _handoff_source(self,arrival):
        with self.lock:
            self._scene()
            self.child_budget.check()
            assert_retained_arrival(arrival.runtime,arrival.receipt,arrival.checkpoint,self.clock())
            if arrival._claim!=[False] or arrival.budget is not self.child_budget:
                raise ValueError('Current unclaimed section arrival required')
            previous=self.section if self.section is not None else self.bootstrap
            self._retire_monitor(previous.monitor)
            if type(previous) is SectionContinuation:previous.release(close_observer=False)
            else:previous.release(close_observer=False)
            self.section=self._section=None
            self.bootstrap=self._bootstrap=None
            self.source=self._source=None
            self.lease=self._lease=self.tracker.acquire()
            self.phase='section_handoff'
            self._check_context()
            last=self.sections is None or self.section_index==len(self.sections.guides)-1
            if not last:
                self.section_index+=1
                self.section_guard=BoundWalkingSection(self.sections,self.section_index)
                self.section=self._section=SectionContinuation(arrival,self.lease,
                    self.sections.guides[self.section_index],owner_binding=self.owner_binding,
                    binding_reader=self._binding,generation_reader=lambda:self.engine.cancel_generation,
                    fit_library=self.fit_library,steering_library=self.steering_library,
                    pump=self.pump,command_state_clear=self.command_clear)
                self.phase='sections'
                return
            arrival._claim[0]=True
            r=arrival.runtime
            self.child_budget.cancel('Pre-line destination reached; root itinerary retained')
            self.root.advance(self.root.stage,'crossing',zone_id=self.root.leg.source_zone_id)
            self.phase='crossing_handoff'
            self.journey.arrival_floor=arrival.checkpoint
            self.section_guard=None
            self.crossing=self._crossing=OwnerSourceCrossingRuntime(self.engine,self.journey,
                destination_id=self.root.leg.destination_id,corridor_spec=self.crossing_spec,
                checkpoint=arrival.checkpoint,motion_basis=arrival.motion_basis,
                motion=r.ledger.motion,heading=r.ledger.pose.heading,bounds=r.ledger.bounds,legacy=r.ledger.legacy,
                lease=self.lease,sender=self.sender,hotkey=self.hotkey,owner_input=self.owner_input,
                topology=self.topology,gate=self.gate,window=self.window,
                released_at=r.last_movement_release,owner_binding=self.owner_binding,binding_reader=self._binding,
                generation_reader=lambda:self.engine.cancel_generation,pump=self.pump,
                command_state_clear=self.command_clear,clock=self.clock,local_wall_clock=self.wall,
                journey_budget=self.root,log_veto=self.veto)
            self.phase='crossing'

    def _finish_crossing(self):
        with self.lock:
            r=self.crossing
            self._check_context()
            if r.phase!='complete' or r.busy or self.root.stage.phase!='arrival':
                raise ValueError('Current completed crossing required for itinerary advancement')
            if self.leg_index+1<len(self.plan.declaration.legs):
                token=r.transfer_destination(check_current=self._check_owner)
                self.transfer=token
                token.claim()
                self.records.append(dict(kind='crossing',leg=self.leg_index,
                    crossing=json.loads(token.crossing_evidence),arrival=json.loads(token.arrival_evidence)))
                self.veto=token.log_veto
                self.crossing=self._crossing=None
                self.assets=self._assets=None
                self.sections=self._sections=None
                self.crossing_spec=self._crossing_spec=None
                self.child_budget=self._child_budget=None
                self.section_index=self.section_guard=None
                self._begin_destination()
                return
            record=r.snapshot()
            self._check_context()
            self.phase='finishing'
            r.release(close_observer=False)
            self._check_owner()
            self.root.advance(self.root.stage,'complete',zone_id=self.root.leg.destination_zone_id)
            self.records.append(dict(kind='crossing',leg=self.leg_index,crossing=record))
            self.owner_input.close()
            self._observer_closed=True
            self._check_owner()
            self.phase='complete'

    def tick(self):
        if self.closed or self.phase in ('complete','stopped'):return
        if self.busy:
            try:self._check_context()
            except BaseException as error:self.cancel(error);raise
            return
        self.busy=True
        try:
            self._scene()
            if self.phase=='load_destination':self._load_destination()
            elif self.phase=='bootstrap':
                self.bootstrap.tick()
                if self.bootstrap.phase=='complete':self.bootstrap.prepare_route(self.assets.guide,sections=self.sections)
                elif self.bootstrap.phase=='route_ready':self._start_source()
            elif self.phase=='source':
                self.source.tick()
                if self.source.phase=='complete':
                    self._handoff_source(capture_section_arrival(self.source,self.child_budget))
            elif self.phase=='sections':
                self.section.tick()
                if self.section.phase=='complete':self._handoff_source(self.section.completed_arrival)
            elif self.phase=='crossing':
                self.crossing.tick()
                if self.crossing.phase=='complete':self._finish_crossing()
            else:raise ValueError('Unknown itinerary continuation phase')
            if self.phase=='complete':self._check_owner()
            else:self._scene()
        except BaseException as error:
            self.cancel(error)
            raise
        finally:self.busy=False

    def cancel(self,reason):
        with self.lock:
            if self.closed or self.phase=='stopped':return
            self.phase,self.reason='stopped',str(reason)
            self.root.cancel(reason)
            for child in (self.crossing,self.section,self.source,self.bootstrap):
                if child is not None:child.cancel(reason)
            self.lease.active=False

    def release(self):
        with self.lock:
            if self.closed:return
            if (self.busy or self.sender.held or getattr(self.sender,'_eql_route_operation',None) is not None
                    or self.phase not in ('complete','stopped')):
                raise ValueError('Itinerary still owns pending input or work')
            for child in (self.crossing,self.section,self.bootstrap):
                if child is not None:
                    child.release(close_observer=False)
            self.lease.release()
            if not self._observer_closed:
                self.owner_input.close()
                self._observer_closed=True
            self.closed=True

    def snapshot(self):
        return dict(phase=self.phase,reason=self.reason,closed=self.closed,
            leg_index=self.leg_index,leg_count=len(self.plan.declaration.legs),
            destination_id=self.root.leg.destination_id,section_index=self.section_index,
            section_count=None if self.sections is None else len(self.sections.guides),
            budget=self.root.snapshot(),completed_crossings=list(self.records),
            bootstrap=None if self.bootstrap is None else self.bootstrap.snapshot(),
            source=None if self.source is None else self.source.snapshot(),
            section=None if self.section is None else self.section.snapshot(),
            crossing=None if self.crossing is None else self.crossing.snapshot(),
            camp_started=False,source_zone_state_reused=False,real_client_accepted=False)
