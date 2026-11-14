"""Finite owner source-route loop, sharing the existing sender and log lease.

Construction needs a freshly started ledger. This adapter neither calibrates
nor logs in, creates input devices, changes targets, or starts combat.
"""
from .g2_safety_provider import GameWindowIdentity
from .location_hotkey import send_location_hotkey
from .motion_collection import CommandReceipt, LocationRequest
from .route_step_sender import _fd_identity
from .source_step_sender import run_checked_source_step
from .source_walk_driver import SourceWalkDriver
from .supervised_route import SupervisedRouteDeclaration, scope_limits
from .supervised_source import SupervisedSourcePolicy


from .source_execution_loop import SourceExecutionLoop


class OwnerSourceRuntime(SourceExecutionLoop):
    def __init__(self, engine, pending, driver, *, clock, local_wall_clock,startup_released_at):
        if type(driver) is not SourceWalkDriver or driver.ledger.phase != 'ready':
            raise ValueError('Freshly started source driver required')
        self.engine, self.pending, self.driver = engine, pending, driver
        self.ledger, self.clock, self.wall = driver.ledger, clock, local_wall_clock
        self.sender, self.lease = pending['sender'], pending['lease']
        self.owner_input, self.hotkey, self.veto = pending['observer'], pending['binding'], pending['veto']
        self.reader = self.lease.reader
        self.ui = self.sender.ui
        self.fd, self.fd_identity = self.ui.fileno(), _fd_identity(self.ui.fileno())
        self.zone = self._zone()
        self.phase, self.reason = 'ready', ''
        self.completed_arrival = None
        self.transfer = self.seal = self.collector = None
        self.stair_preflight=self.stair_boundary=None
        self.contact_preflight=self.contact_boundary=self._contact_driver_state=None
        self.last_movement_release=startup_released_at
        self.observations, self.events, self.pairs = [], [], []
        if (self.ledger.observer.reader is not self.reader or self.ledger.clock is not clock
                or self.ledger.lock is not engine.g0_stop_lock):
            raise ValueError('Source route must retain the same reader, clock and stop lock')
        self.check_current()
        scope = pending['continuation']['scope']
        seconds, steps, distance, hold = scope_limits(scope)
        if scope == 'local_trial':
            distance = 3.
        declaration = SupervisedRouteDeclaration(pending['trial_id'], driver.plan.sha256,
            self.ledger.bounds.calibration_record_id, self.ledger.bounds.record_id,
            True, seconds, steps, distance, hold, scope)
        self.policy = SupervisedSourcePolicy(self.ledger, declaration=declaration,
            gate=engine.gate, owner_input=self.owner_input, log_veto=self.veto,
            expected_window=GameWindowIdentity(*pending['window']),
            topology_generation=pending['topology'], check_current=self.check_current)

    def _zone(self):
        r = self.reader
        return (r.zone_id, r.zone_display_name, r.tail.identity, r.tail.epoch, r.zone_generation)

    def _exclusive(self):
        e, p = self.engine, self.pending
        if (self.phase == 'stopped' or p.get('source_runtime') not in (None, self)
                or p.get('corridor_runtime') is not None or p.get('driver') is not None
                or e.route_session_driver is not None or p['lease'] is not self.lease
                or self.lease.reader is not self.reader or self._zone() != self.zone
                or p['observer'] is not self.owner_input or p['binding'] is not self.hotkey
                or p['veto'] is not self.veto or e.sender is not self.sender
                or self.sender.ui is not self.ui or self.ui.fileno() != self.fd
                or _fd_identity(self.fd) != self.fd_identity):
            raise ValueError('Exclusive source route, sender, reader or owner scope changed')

    def observation_binding(self):
        """Reader/owner identity only; full scene checks belong to the sender.

        The engine brackets this with its current mode/generation/job/window
        check. Avoid recursively reading physical input and files inside each
        source observation check; the policy still checks those at admission,
        immediately before DOWN, during the pulse and after release.
        """
        self._exclusive()
        binding = self.lease.check()
        self._exclusive()
        return binding

    def check_current(self):
        # Never enter ledger._check here: it calls back through the observer.
        e, p = self.engine, self.pending
        e._trial_common_current(p)
        self.observation_binding()
        veto = self.veto.poll()
        if not veto.continuity_available or veto.reason is not None:
            raise ValueError('Source route log hazard or coverage changed')
        e._trial_common_current(p)
        self._exclusive()
        self.check_contact_boundary()

    def _request_location(self, request):
        e, p, collector, active, seal = self.engine, self.pending, self.collector, self.active, self.seal
        pre=self.pending_preflight
        if type(request) is not LocationRequest or collector is None:
            raise ValueError('Owned source position request required')

        def current():
            self.check_current()
            collector.check()
            if seal is not None:active._check_seal(seal)
            elif pre is not None and self.pending_preflight is pre and self.phase in ('stair_start','contact_start'):pre.check()
            else:raise ValueError('Source location request lacks a movement seal or stair preflight')
            if (self.active is not active or self.seal is not seal or self.collector is not collector
                    or collector.pending is not request or collector.phase != 'requesting'
                    or not p['busy'] or self.clock() < e.zone_loading_until
                    or p.get('source_runtime') is not self):
                raise ValueError('Source position request changed or client is loading')

        def pump():
            e.pump()
            e.autopilot_tick(self.clock())

        expires=(seal.expires_at if seal else min(self.policy.started+self.policy.declaration.maximum_seconds,
            self.ledger.observer.calibration.valid_until_monotonic))
        receipt = send_location_hotkey(self.sender, binding=self.hotkey, owner_input=self.owner_input,
            lock=self.ledger.lock, clock=self.clock, expires_at=min(request.expires_at,expires),
            ensure_current=current, cancel=lambda reason:e._cancel_trial(reason),
            pump=pump, record_event=self.events.append)
        return CommandReceipt(receipt.pulse.down_started_at, receipt.released_at)

    def _work_busy(self):return self.pending['busy']

    def _set_work_busy(self,value):self.pending['busy']=value

    def _send_movement(self,action):
        e=self.engine
        def pump():
            e.pump();e.autopilot_tick(self.clock())
        return run_checked_source_step(self.sender,self.active,policy=self.policy,
            kind=action.kind,requested_seconds=action.requested_seconds,
            command_state_clear=lambda:e._route_idle() and not e.cancelled and e.jobs.empty(),pump=pump)
