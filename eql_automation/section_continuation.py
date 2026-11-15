"""Fresh probes and one onward walking section after a healthy stopped arrival.

No camp, target selection, saved-file resume, new sender or login is involved.
The owning engine must select the next immutable guide from its finite section
sequence and explicitly transfer the observer after completion. This adapter
does not install itself in owner controls.
"""
from dataclasses import dataclass, replace
from hashlib import sha256
import json

from .camp_floor_checkpoint import CampFloorCheckpoint
from .camp_motion_continuity import CampInputContinuity, _arrival_basis
from .camp_probe_calibration import reduce_camp_probes
from .camp_probe_preparation import CampProbePreparation
from .camp_probe_runtime import CampProbeRuntime
from .camp_source_runtime import CampSourcePlan, CampSourceRuntime
from .camp_stopped_height import measure_camp_stopped_height
from .flat_record import flat_record_state
from .g2_safety_provider import focused_game_identity
from .ground_binding import finite
from .journey_input_budget import JourneyInputBudget
from .location_hotkey import HOTKEY_CODES, send_location_hotkey
from .motion_calibration import PROBES
from .motion_collection import CommandReceipt, LocationRequest, immutable_binding
from .native_region_policy import encoded
from .owner_camp_plan_provider import arrival_probe_bounds, checked_fresh_fit
from .owner_source_runtime import OwnerSourceRuntime
from .owner_zone_tracker import ZoneReaderLease
from .route_step_sender import _fd_identity
from .route_floor_commit import _chain_snapshot
from .source_probe_geometry import check_source_footprint
from .source_walk_sections import measurement_reserve
from .source_arrival import assert_retained_arrival
from .source_itinerary import SourceItineraryGuide, SourceWalkHint, _guide_snapshot
from .source_walk_driver import SourceWalkFinished
from .stopped_location_pair import StoppedLocationPair
from .supervised_camp_probe import SupervisedCampProbeDeclaration, SupervisedCampProbeScope
from .supervised_route import SupervisedRouteDeclaration, scope_limits
from .supervised_source import SupervisedSourcePolicy


@dataclass(frozen=True)
class SectionArrival:
    runtime: object
    receipt: SourceWalkFinished
    checkpoint: CampFloorCheckpoint
    motion_basis: bytes
    budget: JourneyInputBudget
    guide_sha256: str
    _claim: list


def capture_section_arrival(runtime, budget):
    """Capture before releasing the old reader; terminal phase alone is insufficient."""
    if (type(runtime) not in (OwnerSourceRuntime, CampSourceRuntime)
            or type(budget) is not JourneyInputBudget):
        raise ValueError('Actual source runtime and original journey budget required')
    r = runtime
    with budget.lock:
        budget.check(); r.check_current(); r.policy._check()
        receipt = r.completed_arrival
        if (r.phase != 'complete' or type(receipt) is not SourceWalkFinished
                or getattr(r, '_section_arrival', None) is not None
                or r.policy.journey_budget is not budget or r.ledger.lock is not budget.lock
                or r.clock is not budget.clock or r.collector is not None or r.seal is not None
                or r.transfer is not None or r.pending_preflight is not None or r._work_busy()
                or r.sender.held or r.sender.unfinished
                or getattr(r.sender, '_eql_route_operation', None) is not None
                or receipt.reference is not r.ledger.reference
                or receipt.itinerary_sha256 != r.driver.plan.sha256):
            raise ValueError('Healthy released ordinary section completion required')
        final = r.driver.next_action()
        if type(final) is not SourceWalkFinished or final.reference is not receipt.reference:
            raise ValueError('Section driver has not reached its stopped destination')
        checkpoint = CampFloorCheckpoint(r.ledger)
        try:
            basis = _arrival_basis(r, checkpoint=checkpoint)
            budget.check(); r.check_current(); r.policy._check()
            assert_retained_arrival(r, receipt, checkpoint, budget.check())
            token = SectionArrival(r, receipt, checkpoint, basis, budget,
                r.driver.plan.record()['guide_sha256'], [False])
            r._section_arrival = token
            return token
        except BaseException as error:
            checkpoint.invalidate(error); raise


class SectionContinuation:
    """One retained arrival -> fresh stopped pair -> seven probes -> next section."""
    def __init__(self, arrival, lease, guide, *, owner_binding, binding_reader,
                 generation_reader, fit_library, steering_library, pump, command_state_clear):
        if (type(arrival) is not SectionArrival or type(lease) is not ZoneReaderLease
                or type(guide) is not SourceItineraryGuide or not immutable_binding(owner_binding)
                or not all(callable(v) for v in (binding_reader, generation_reader, pump, command_state_clear))):
            raise ValueError('Retained section arrival, new lease and explicit owner callbacks required')
        guide.validate()
        old = arrival.runtime; b = arrival.budget
        with b.lock:
            b.check()
            assert_retained_arrival(old, arrival.receipt, arrival.checkpoint, b.check())
            if (arrival._claim != [False] or getattr(old,'_section_arrival',None) is not arrival
                    or old.lease.active or old.lease is lease
                    or lease._tracker is not old.lease._tracker or lease.reader is not old.reader
                    or not lease.active or lease._tracker.lease is not lease
                    or any(type(op) is not SourceWalkHint for op in guide.operations)
                    or guide.operations[0].start != tuple(old.driver.plan.record()['goal'])
                    or guide.wld_sha256 != arrival.checkpoint._terrain.wld_sha256
                    or guide.static_inventory_sha256 != arrival.checkpoint._static.inventory_sha256
                    or guide.zone != arrival.checkpoint._policy.zone
                    or guide.radius != old.ledger.bounds.body_radius
                    or guide.body_height != old.ledger.bounds.body_height
                    or old.sender.held or old.sender.unfinished
                    or old.sender.ui is not old.ui or old.ui.fileno() != old.fd
                    or _fd_identity(old.fd) != old.fd_identity
                    or getattr(old.sender, '_eql_route_operation', None) is not None):
                raise ValueError('Section handoff changed, was consumed or lost its released reader')
            self.arrival, self.budget, self.lease, self.guide = arrival, b, lease, guide
            self.floor, self.clock, self.wall = arrival.checkpoint, b.clock, old.wall
            self.lock, self.sender, self.reader = b.lock, old.sender, lease.reader
            self.ui, self.fd, self.fd_identity = old.ui, old.fd, old.fd_identity
            self._device = self.ui, self.fd, self.fd_identity
            self.owner_input, self.hotkey = old.owner_input, old.hotkey
            self.gate, self.window, self.veto = old.policy.gate, old.policy.window, old.policy.log_veto
            self.generation = generation_reader()
            if self.generation != self.veto.cancel_generation:
                raise ValueError('Section must retain the original owner stop generation')
            self.owner_binding, self.binding_reader = owner_binding, binding_reader
            self._generation = self.generation
            self._window_state = flat_record_state(self.window)
            self.generation_reader, self.pump, self.command_clear = generation_reader, pump, command_state_clear
            self.fit_library, self.steering_library = fit_library, steering_library
            self._guide_state = _guide_snapshot(guide)
            self.started = self.last_at = self.clock()
            self.expires_at = min(b.expires_at, self.started+scope_limits('destination_travel')[0])
            self._times = self.started, self.expires_at
            self._context = (arrival, b, lease, guide, self.floor, self.clock, self.wall, self.lock,
                self.sender, self.reader, self.owner_input, self.hotkey, self.gate, self.veto,
                owner_binding, binding_reader, generation_reader, pump, command_state_clear,
                fit_library, steering_library)
            self.phase, self.reason, self.busy, self.closed = 'collect_position', '', False, False
            self.runtime = self.route_runtime = self.collector = self.result = self.scope = None
            self._runtime = self._route_runtime = self._scope = None
            self.reserve = self.reserve_position = self.reserve_height = None
            self.bounds = self.bounds_basis = None
            self._reserve_inputs = self._reserve_bytes = None
            self.calibration = self.calibration_seal = self.completed_arrival = None
            self.sending = False; self.request = None; self.events = []
            binding = self._monitor_binding()
            self.monitor = CampInputContinuity(self.owner_input, topology=old.policy.topology,
                basis=arrival.motion_basis, binding=binding, clock=self.clock, floor=self.floor)
            self._monitor = self.monitor
            self._topology = old.policy.topology
            self.baseline = self.reader.log_line_seq
            self.released_at = old.last_movement_release
            # The claim is consumed even if subsequent preparation fails.
            arrival._claim[0] = True
            try:
                self._check()
                self.collector = StoppedLocationPair(lease, released_at=self.released_at,
                    check_current=self._check, clock=self.clock, local_wall_clock=self.wall)
            except BaseException as error:
                self.cancel(error)
                self.release()
                raise

    def current_input_key(self):
        if not self.busy:return None
        if self.sending and self.request is not None:return HOTKEY_CODES[self.hotkey.key_name]
        active = self.route_runtime if self.route_runtime is not None else self.runtime
        return None if active is None else active.current_input_key()

    def _monitor_binding(self):
        return (self.sender,self.sender.ui,self.gate,self.lease._tracker,self.reader,self,
                self.generation,self.owner_binding)

    def _check(self):
        if self.phase == 'stopped' or self.closed:raise ValueError(self.reason or 'Section closed')
        self.budget.check(); binding = self.binding_reader(); self.lease.check(); self.hotkey.check()
        self.monitor.check_binding(self._monitor_binding())
        sample = self.owner_input.sample(); veto = self.veto.poll()
        window = focused_game_identity(self.gate); now = self.clock()
        actual = (self.arrival, self.budget, self.lease, self.guide, self.floor, self.clock, self.wall, self.lock,
            self.sender, self.reader, self.owner_input, self.hotkey, self.gate, self.veto,
            self.owner_binding, self.binding_reader, self.generation_reader, self.pump, self.command_clear,
            self.fit_library, self.steering_library)
        key = self.current_input_key()
        if self._reserve_inputs is not None and (
                (self.reserve_position,self.reserve_height,id(self.bounds),flat_record_state(self.bounds),
                 self.bounds_basis) != self._reserve_inputs or self.reserve is not self._reserve_bytes):
            raise ValueError('Checked whole-probe reserve changed before continuation')
        if (self.phase == 'stopped' or self.closed
                or any(a is not b for a,b in zip(self._context, actual))
                or self.monitor is not self._monitor or self.monitor.topology != self._topology
                or flat_record_state(self.window) != self._window_state or self.generation != self._generation
                or self.runtime is not self._runtime or self.route_runtime is not self._route_runtime
                or self.scope is not self._scope
                or _guide_snapshot(self.guide) != self._guide_state
                or (self.started, self.expires_at) != self._times
                or binding != self.owner_binding or self.binding_reader() != self.owner_binding
                or self.generation_reader() != self.generation or window != self.window
                or self.veto.cancel_generation != self.generation
                or self.veto.tail.path != self.reader.tail.path or self.veto.clock is not self.clock
                or self.lease.reader is not self.reader or self.monitor.floor is not self.floor
                or (self.ui,self.fd,self.fd_identity) != self._device
                or self.sender.ui is not self.ui or self.ui.fileno() != self.fd
                or _fd_identity(self.fd) != self.fd_identity
                or not sample.clear_at(now) or sample.topology_generation != self.monitor.topology
                or not veto.continuity_available or veto.reason is not None
                or self.sender.unfinished or self.sender.dismissed
                or self.sender.held - ({key} if key is not None else set())
                or not self.command_clear() or not finite(now)
                or not self.started <= self.last_at <= now <= self.expires_at):
            raise ValueError('Section owner, stopped floor, input or fixed child deadline changed')
        self.budget.check(); self.last_at = now
        return self.owner_binding

    def cancel(self, reason):
        with self.lock:
            if self.phase == 'stopped' or self.closed:return
            self.phase, self.reason = 'stopped', str(reason)
            self.budget.cancel(reason)
            reached,self.completed_arrival = self.completed_arrival,None
            if reached is not None and reached._claim == [False]:reached.checkpoint.invalidate(reason)
            if self.collector is not None:self.collector.cancel(reason)
            if self.route_runtime is not None:self.route_runtime.cancel(reason)
            if self.runtime is not None:self.runtime.cancel(reason)
            self.lease.active = False

    def release(self):
        with self.lock:
            if self.closed:return
            if (self.busy or self.sender.held or getattr(self.sender, '_eql_route_operation', None) is not None
                    or self.phase not in ('complete', 'stopped')):
                raise ValueError('Section still owns pending input or work')
            if self.runtime is not None:self.runtime.release()
            else:self.lease.release()
            self.closed = True
            # A successful caller adopts the new checkpoint and observer first.
            if self.phase == 'stopped':self.monitor.close(self.reason)

    def _send_location(self, request):
        collector = self.collector
        def current():
            self._check(); collector.check()
            if (self.collector is not collector or collector.pending is not request
                    or collector.phase != 'requesting' or self.request is not request):
                raise ValueError('Section location request changed')
        self.sending, self.request = True, request
        try:
            sent = send_location_hotkey(self.sender, binding=self.hotkey, owner_input=self.owner_input,
                lock=self.lock, clock=self.clock, expires_at=min(request.expires_at,self.expires_at),
                ensure_current=current, cancel=self.cancel, pump=self.pump, record_event=self.events.append)
            return CommandReceipt(sent.pulse.down_started_at, sent.released_at)
        finally:self.sending, self.request = False, None

    def _probe_policy(self, tx):
        self._check(); r = self.runtime
        if self.scope is None:
            declaration = SupervisedCampProbeDeclaration(r.root.bounds.record_id, r.root.bounds.record_id,
                True, len(PROBES)*r.root.bounds.maximum_actual_hold)
            self.scope = self._scope = SupervisedCampProbeScope(r, declaration=declaration, monitor=self.monitor,
                gate=self.gate, expected_window=self.window, log_veto=self.veto,
                check_current=self._check, started_at=r.started,
                expires_at=r.started+r.maximum_seconds, journey_budget=self.budget)
        return self.scope.policy(tx)

    def _position_complete(self):
        c = self.collector
        self.result = measure_camp_stopped_height(self.floor,self.reader,c.first,c.second,
            minimum_log_seq=self.baseline,released_at=self.released_at,owner_binding=self.owner_binding,
            binding_reader=self._check,clock=self.clock,local_wall_clock=self.wall)
        if self.phase == 'collect_position':
            bounds, basis = arrival_probe_bounds(self.monitor,self.floor,self.result.sha256)
            self.bounds, self.bounds_basis = bounds, basis
            self.reserve_position = self.result.package_xyz
            self.reserve_height = self.result.raw_z_minus_source_z
            self._reserve_inputs = (self.reserve_position,self.reserve_height,id(bounds),flat_record_state(bounds),basis)
            self._check(); began = self.clock()
            original = _chain_snapshot(self.floor._chain)
            footprint, assumptions = measurement_reserve(self.result.package_xyz[:2],bounds)
            checked = check_source_footprint(self.floor.fork(),footprint,terrain=self.floor._terrain,
                static=self.floor._static,bsp=self.floor._bsp,region_policy=self.floor._policy)
            self._check()
            if (not 0 <= self.clock()-began <= 30. or _chain_snapshot(self.floor._chain) != original):
                raise ValueError('Section measurement reserve changed its floor or exceeded work limit')
            self.reserve = self._reserve_bytes = encoded(dict(position=self.reserve_position,assumptions=assumptions,
                terrain_proof_sha256=checked.terrain.proof_sha256,input_authorized=False,
                actual_stopped_position=True,requires_fresh_confirmation=True))
            self.released_at = self.clock(); self.baseline = self.reader.log_line_seq
            self.collector = StoppedLocationPair(self.lease,released_at=self.released_at,
                check_current=self._check,clock=self.clock,local_wall_clock=self.wall)
            self.phase = 'confirm_reserve'
            return
        if (self.result.package_xyz != self.reserve_position
                or self.result.raw_z_minus_source_z != self.reserve_height):
            raise ValueError('Stopped position changed from the checked whole-probe reserve')
        bounds, basis = self.bounds, self.bounds_basis
        preparation = CampProbePreparation(self.floor,self.result,self.lease,probe_kind=PROBES[0].key,
            bounds=bounds,bounds_basis=basis,owner_binding=self.owner_binding,binding_reader=self._check,
            clock=self.clock,local_wall_clock=self.wall)
        remaining = self.expires_at-self.clock()
        self.collector = None
        self.runtime = self._runtime = CampProbeRuntime(preparation,sender=self.sender,hotkey=self.hotkey,
            owner_input=self.owner_input,stop_lock=self.lock,movement_policy_factory=self._probe_policy,
            check_current=self._check,command_state_clear=self.command_clear,pump=self.pump,
            maximum_seconds=remaining,log_veto=self.veto)
        self.phase = 'probe'

    def _start_route(self):
        self.scope._check()
        fit = checked_fresh_fit(self,self.runtime,self.calibration)
        estimate = fit['estimate']; legacy = self.steering_library
        bounds = replace(self.runtime.root.bounds,record_id='section-route-'+self.runtime.route_preparation.itinerary.sha256,
                         maximum_requested_hold=.1)
        def policy(ledger,current):
            self._check(); self.scope._check()
            seconds,steps,distance,hold = scope_limits('destination_travel')
            remaining = self.expires_at-self.clock()
            declaration = SupervisedRouteDeclaration('section-'+fit['record_id'],ledger.observer.itinerary.sha256,
                bounds.calibration_record_id,bounds.record_id,False,min(seconds,remaining),steps,distance,
                min(hold,remaining),'camp_continuation',True)
            return SupervisedSourcePolicy(ledger,declaration=declaration,gate=self.gate,
                owner_input=self.owner_input,log_veto=self.veto,expected_window=self.window,
                topology_generation=self.monitor.topology,check_current=current,journey_budget=self.budget)
        plan = CampSourcePlan(bounds,legacy,legacy.Motion(run_speed=estimate['run_speed'],
            turn_rate=estimate['turn_rate'],right_sign=estimate['right_sign'],turn_latency=estimate['turn_latency'],
            back_speed=0.),estimate['final_heading'],.25,policy)
        self.route_runtime = self._route_runtime = CampSourceRuntime(self.runtime,plan,check_current=self._check,
            mode_reader=lambda:'off' if self.phase=='stopped' else 'camp_route',
            generation_reader=self.generation_reader,generation=self.generation)
        self.phase = 'route'

    def tick(self):
        if self.closed or self.phase in ('complete','stopped'):return
        if self.busy:self._check(); return
        self.busy = True
        try:
            self._check()
            if self.phase in ('collect_position','confirm_reserve'):
                request = self.collector.tick()
                if isinstance(request,LocationRequest):
                    self.collector.command_sent(request,self._send_location(request))
                if self.collector.phase == 'complete':self._position_complete()
            elif self.phase == 'probe':
                self.runtime.tick()
                if self.runtime.phase == 'complete':
                    fit = reduce_camp_probes(self.runtime,legacy=self.fit_library,
                                            record_id='camp-'+self.runtime.results[-1].sha256)
                    self.calibration = dict(status='conditional',estimate=fit)
                    self.calibration_seal = (self.calibration,encoded(self.calibration),self.runtime.reference,
                                            tuple(self.runtime.transactions),tuple(self.runtime.results))
                    self.runtime.prepare_route(self.guide)
                elif self.runtime.phase == 'route_ready':self._start_route()
            elif self.phase == 'route':
                self.route_runtime.tick()
                if self.route_runtime.phase == 'complete':
                    with self.lock:
                        reached = capture_section_arrival(self.route_runtime,self.budget)
                        try:self._check()
                        except BaseException as error:
                            reached.checkpoint.invalidate(error); raise
                        self.completed_arrival = reached
                        self.phase = 'complete'
            else:raise ValueError('Unknown section continuation phase')
        except BaseException as error:
            self.cancel(error); raise
        finally:self.busy = False

    def snapshot(self):
        return dict(phase=self.phase,reason=self.reason,closed=self.closed,
            started_at=self.started,expires_at=self.expires_at,guide_sha256=sha256(encoded(self.guide.record())).hexdigest(),
            completed_probes=0 if self.runtime is None else len(self.runtime.results),
            completed_movements=0 if self.route_runtime is None or self.route_runtime.ledger is None else self.route_runtime.ledger.steps,
            budget=self.budget.snapshot(),location_events=list(self.events),
            measurement_reserve=None if self.reserve is None else json.loads(self.reserve),
            game_login_started=False,camp_started=False,real_client_accepted=False)
