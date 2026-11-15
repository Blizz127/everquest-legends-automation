"""Explicit onward camp execution on the retained probe scope and sender.

No default motion estimate or scene declaration is supplied. The caller must
provide a route plan and a current policy; the original camp deadline remains
in force throughout startup, walking and step transfer.
"""
from dataclasses import dataclass

from .camp_probe_runtime import CampProbeRuntime
from .camp_source_observer import CampSourceObserver
from .flat_record import flat_record_state
from .ground_binding import finite
from .location_hotkey import HOTKEY_CODES, send_location_hotkey
from .motion_collection import CommandReceipt, LocationRequest
from .route_geometry import RouteMotionBounds
from .route_step_sender import _fd_identity
from .source_execution_loop import SourceExecutionLoop
from .source_motion import SourceReceiptLedger
from .source_step_sender import run_checked_source_step
from .source_walk_driver import SourceWalkDriver
from .stopped_location_pair import StoppedLocationPair
from .supervised_source import SupervisedSourcePolicy


@dataclass(frozen=True)
class CampSourcePlan:
    bounds: RouteMotionBounds
    legacy: object
    motion: object
    heading: float
    walk_half_width: float
    policy_factory: object

    def state(self):
        if (type(self.bounds) is not RouteMotionBounds or not callable(self.policy_factory)
                or not isinstance(self.motion, self.legacy.Motion)
                or not finite(self.heading) or not 0 <= self.heading < 360
                or not finite(self.walk_half_width) or not .05 <= self.walk_half_width <= 6.):
            raise ValueError('Explicit camp route bounds, motion, heading and policy required')
        return (id(self), id(self.bounds), flat_record_state(self.bounds), id(self.legacy),
                id(self.motion), flat_record_state(self.motion), self.heading,
                self.walk_half_width, id(self.policy_factory))


class CampSourceRuntime(SourceExecutionLoop):
    def __init__(self, probe, plan, *, check_current, mode_reader,
                 generation_reader, generation,check_scene=None,input_release_deadline=None):
        if (type(probe) is not CampProbeRuntime or probe.phase != 'route_ready' or probe.busy
                or type(plan) is not CampSourcePlan
                or check_scene is not None and not callable(check_scene)
                or input_release_deadline is not None and not finite(input_release_deadline)
                or not all(callable(f) for f in (check_current, mode_reader, generation_reader))):
            raise ValueError('Prepared idle camp scope and explicit execution plan required')
        self.probe, self.plan = probe, plan
        self.plan_state = plan.state()
        self.current = check_current
        self.scene_current=check_scene
        self.input_release_deadline=input_release_deadline
        self.mode_reader, self.generation_reader, self.generation = mode_reader, generation_reader, generation
        self.sender, self.lease, self.hotkey = probe.sender, probe.lease, probe.hotkey
        self.owner_input, self.lock = probe.owner_input, probe.lock
        self.clock, self.wall, self.reader = probe.clock, probe.wall, probe.lease.reader
        self.ui = self.sender.ui
        self.fd, self.fd_identity = self.ui.fileno(), _fd_identity(self.ui.fileno())
        self.phase, self.reason, self.busy = 'startup', '', False
        self.collector = self.transfer = self.seal = self.completed_arrival = None
        self.stair_preflight=self.stair_boundary=None
        self.contact_preflight=self.contact_boundary=self._contact_driver_state=None
        self.last_movement_release=None
        self.ledger = self.observer = self.driver = self.policy = None
        self._owned_ledger = self._owned_observer = self._owned_driver = self._owned_policy = None
        self.events, self.pairs, self.observations = [], [], []
        self.input_kind = self.input_request = None
        self._context = (probe, plan, check_current, mode_reader, generation_reader,
            self.sender, self.lease, self.hotkey, self.owner_input, self.lock, self.clock, self.wall, self.reader,check_scene,
            input_release_deadline)
        try:
            with self.lock:
                probe._check()
                self.check_current()
                if input_release_deadline is not None and not self.clock()<input_release_deadline<=probe.started+probe.maximum_seconds:
                    raise ValueError('Source release deadline must fit its original probe scope')
                if self.sender.held or getattr(self.sender, '_eql_route_operation', None) is not None:
                    raise ValueError('Camp route adoption requires released keys and operation')
                self.observer = self._owned_observer = CampSourceObserver(probe.route_preparation, probe.route_start,
                    scope_check=self.check_current, mode_reader=mode_reader,
                    generation_reader=generation_reader, generation=generation,
                    expires_at=min(probe.started+probe.maximum_seconds,
                        float('inf') if input_release_deadline is None else input_release_deadline),
                    walk_half_width=plan.walk_half_width, stop_lock=self.lock, route_bounds=plan.bounds)
                floor = probe.reference
                self.ledger = self._owned_ledger = SourceReceiptLedger(self.observer, terrain=floor._terrain,
                    static=floor._static, bsp=floor._bsp, bounds=plan.bounds,
                    installed_model=floor._model, legacy=plan.legacy, motion=plan.motion,
                    heading=plan.heading, stop_lock=self.lock)
                self.driver = self._owned_driver = SourceWalkDriver(self.ledger)
                self.collector = StoppedLocationPair(self.lease, released_at=self.clock(),
                    check_current=self.check_current, clock=self.clock, local_wall_clock=self.wall)
                self.check_current()
        except BaseException as error:
            self.cancel(error)
            raise

    def check_current(self):
        # Do not call ledger._check here: the observer calls this callback.
        if self.phase == 'stopped':raise ValueError(self.reason)
        # Binding checks do not rescan floor ancestry. The source observer
        # checks that ancestry in every ledger check, and location admission
        # explicitly checks the active ledger before requesting a reading.
        self.current()
        actual = (self.probe, self.plan, self.current, self.mode_reader, self.generation_reader,
            self.sender, self.lease, self.hotkey, self.owner_input, self.lock, self.clock, self.wall, self.reader,self.scene_current,
            self.input_release_deadline)
        if (self.phase == 'stopped' or any(a is not b for a,b in zip(self._context, actual))
                or self.plan.state() != self.plan_state or self.probe.phase != 'route_ready'
                or self.probe.busy or self.probe.closed or self.probe.sender is not self.sender
                or self.probe.lease is not self.lease or self.lease.reader is not self.reader
                or self.probe.lock is not self.lock or self.sender.ui is not self.ui
                or self.observer is not self._owned_observer or self.ledger is not self._owned_ledger
                or self.driver is not self._owned_driver or self.policy is not self._owned_policy
                or self.ui.fileno() != self.fd or _fd_identity(self.fd) != self.fd_identity
                or self.mode_reader() != 'camp_route' or self.generation_reader() != self.generation):
            raise ValueError('Camp route owner, original probe scope or sender changed')
        # Provider callbacks cannot carry a check beyond the original deadline.
        self.probe._check_scope();self.current()
        self.check_contact_boundary()

    def cancel(self, reason):
        with self.lock:
            self.phase, self.reason = 'stopped', str(reason)
            self.completed_arrival = None
            if self.collector is not None:self.collector.cancel(reason)
            if self.transfer is not None:self.transfer.cancel(reason)
            if self.stair_preflight is not None:self.stair_preflight.cancel(reason)
            if self.contact_preflight is not None:self.contact_preflight.cancel(reason)
            if self._owned_ledger is not None:self._owned_ledger.cancel(reason)
            if self._owned_observer is not None:self._owned_observer.cancel(reason)

    def _work_busy(self):return self.busy

    def _set_work_busy(self, value):self.busy = value

    def current_input_key(self):
        if not self.busy:return None
        if (self.input_kind == 'location' and self.collector is not None
                and self.collector.phase == 'requesting'
                and self.collector.pending is self.input_request):
            return HOTKEY_CODES[self.hotkey.key_name]
        if self.input_kind == 'movement' and self.input_request is not None:
            return {'forward':103, 'left':105, 'right':106}.get(self.input_request.kind)
        return None

    def _request_location(self, request):
        collector, active, seal = self.collector, self.active, self.seal
        pre=self.pending_preflight
        if type(request) is not LocationRequest or collector is None:
            raise ValueError('Owned camp route location request required')
        def current():
            self.check_current();collector.check()
            if seal is not None:active._check_seal(seal)
            elif self.phase in ('stair_start','contact_start') and pre is not None and self.pending_preflight is pre:pre.check()
            elif self.phase=='startup':active._check()
            else:raise ValueError('Camp position request lacks its startup or receipt context')
            if self.scene_current is not None:
                self.scene_current();self.check_current()
            if (not self.busy or self.collector is not collector or self.active is not active
                    or self.seal is not seal or collector.phase != 'requesting'
                    or collector.pending is not request or self.input_request is not request):
                raise ValueError('Camp route location request changed')
        self.input_kind, self.input_request = 'location', request
        try:
            limits=[v for v in (self.probe.input_release_deadline,self.input_release_deadline) if v is not None]
            deadline={} if not limits else dict(release_deadline=min(limits))
            receipt = send_location_hotkey(self.sender, binding=self.hotkey, owner_input=self.owner_input,
                lock=self.lock, clock=self.clock,
                expires_at=min(request.expires_at, seal.expires_at) if seal else request.expires_at,
                ensure_current=current, cancel=self.cancel, pump=self.probe.pump, record_event=self.events.append, **deadline)
            return CommandReceipt(receipt.pulse.down_started_at, receipt.released_at)
        finally:self.input_kind = self.input_request = None

    def _send_movement(self, action):
        self.input_kind, self.input_request = 'movement', action
        try:
            return run_checked_source_step(self.sender, self.active, policy=self.policy,
                kind=action.kind, requested_seconds=action.requested_seconds,
                command_state_clear=self.probe.command_clear, pump=self.probe.pump)
        finally:self.input_kind = self.input_request = None

    def tick(self):
        if self.phase != 'startup':return super().tick()
        self.check_current()
        if self.busy:return
        self.busy = True
        try:
            c = self.collector
            action = c.tick()
            fixes = tuple(raw for raw in (c.first, c.second) if raw is not None)
            if len(fixes) != len(self.observations):
                if len(fixes) != len(self.observations)+1:
                    raise ValueError('Camp startup skipped an owned position')
                self.observations.append(self.observer.observe(fixes[-1], checked_chain=self.ledger.chain))
            if isinstance(action, LocationRequest):c.command_sent(action, self._request_location(action))
            if c.phase != 'complete':return
            self.ledger.start(*self.observations, released_at=c.released_at)
            self.last_movement_release=c.released_at
            self.pairs.append(c.snapshot());self.collector = None;self.observations = []
            policy = self.plan.policy_factory(self.ledger, self.check_current)
            self.check_current()
            if (type(policy) is not SupervisedSourcePolicy or policy.ledger is not self.ledger
                    or policy.owner_input is not self.owner_input
                    or self.probe.log_veto is not None and policy.log_veto is not self.probe.log_veto
                    or policy.check_current != self.check_current):
                raise ValueError('Exact current camp source policy and retained input observer required')
            self.policy = self._owned_policy = policy
            policy._check();self.check_current();self.phase = 'ready'
        except BaseException as error:
            self.cancel(error)
            raise
        finally:self.busy = False

    def snapshot(self):
        # Diagnostics use the owned objects even after a public reference was
        # replaced and refused; reporting must not obstruct release cleanup.
        ledger, driver, policy = self._owned_ledger, self._owned_driver, self._owned_policy
        route = None if policy is None else dict(phase=self.phase, reason=self.reason,
            movement_phase=ledger.phase, movement_reason=ledger.reason,
            itinerary_sha256=driver.plan.sha256, cell_index=driver.index,
            completed_movements=ledger.steps, stopped_pairs=list(self.pairs),
            executor_events=list(self.events), policy=policy.snapshot(), real_client_accepted=False)
        return dict(phase=self.phase, reason=self.reason, original_scope_started=self.probe.started,
            original_scope_expires=self.probe.started+self.probe.maximum_seconds,
            startup_pending=self.policy is None,
            incomplete_pair=None if self.collector is None else self.collector.snapshot(),
            executor_events=list(self.events),
            route=route,
            startup_pairs=list(self.pairs[:1]), input_authorized=False, real_client_accepted=False)
