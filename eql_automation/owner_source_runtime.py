"""Finite owner source-route loop, sharing the existing sender and log lease.

Construction needs a freshly started ledger. This adapter neither calibrates
nor logs in, creates input devices, changes targets, or starts combat.
"""
from dataclasses import asdict

from .g2_safety_provider import GameWindowIdentity
from .location_hotkey import send_location_hotkey
from .motion_collection import CommandReceipt, LocationRequest
from .route_step_sender import _fd_identity
from .source_step_sender import run_checked_source_step
from .source_transfer import SourceTransferController
from .source_walk_driver import SourceWalkDriver, SourceStepBoundary, SourceWalkFinished
from .stopped_location_pair import StoppedLocationPair
from .supervised_route import SupervisedRouteDeclaration, scope_limits
from .supervised_source import SupervisedSourcePolicy


class OwnerSourceRuntime:
    def __init__(self, engine, pending, driver, *, clock, local_wall_clock):
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

    @property
    def active(self):
        return self.transfer if self.transfer is not None else self.ledger

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

    def cancel(self, reason):
        with self.ledger.lock:
            self.phase, self.reason = 'stopped', str(reason)
            self.completed_arrival = None
            if self.collector is not None:
                self.collector.cancel(reason)
            if self.transfer is not None:
                self.transfer.cancel(reason)
            self.ledger.cancel(reason)

    def _new_pair(self):
        # Settling retains the same release/deadline; it never buys another
        # movement or renews the transfer's ten-second observation window.
        active, seal, previous = self.active, self.seal, self.collector
        collector = StoppedLocationPair(self.lease,
            released_at=seal.receipt.up_completed_at, check_current=self.check_current,
            clock=self.clock, local_wall_clock=self.wall)
        with self.ledger.lock:
            self.check_current()
            active._check_seal(seal)
            if (self.phase == 'stopped' or self.active is not active
                    or self.seal is not seal or self.collector is not previous):
                collector.cancel('Source pair creation cancelled')
                raise ValueError('Source pair creation cancelled')
            self.collector = collector
            self.observations = []
            self.phase = 'settling' if active.phase == 'settling' else 'positions'

    def _request_location(self, request):
        e, p, collector, active, seal = self.engine, self.pending, self.collector, self.active, self.seal
        if type(request) is not LocationRequest or collector is None:
            raise ValueError('Owned source position request required')

        def current():
            self.check_current()
            collector.check()
            active._check_seal(seal)
            if (self.active is not active or self.seal is not seal or self.collector is not collector
                    or collector.pending is not request or collector.phase != 'requesting'
                    or not p['busy'] or self.clock() < e.zone_loading_until
                    or p.get('source_runtime') is not self):
                raise ValueError('Source position request changed or client is loading')

        def pump():
            e.pump()
            e.autopilot_tick(self.clock())

        receipt = send_location_hotkey(self.sender, binding=self.hotkey, owner_input=self.owner_input,
            lock=self.ledger.lock, clock=self.clock, expires_at=min(request.expires_at, seal.expires_at),
            ensure_current=current, cancel=lambda reason:e._cancel_trial(reason),
            pump=pump, record_event=self.events.append)
        return CommandReceipt(receipt.pulse.down_started_at, receipt.released_at)

    def _collect(self):
        collector, active, seal = self.collector, self.active, self.seal
        active._check_seal(seal)
        action = collector.tick()
        fixes = tuple(raw for raw in (collector.first, collector.second) if raw is not None)
        if len(fixes) != len(self.observations):
            if len(fixes) != len(self.observations)+1:
                raise ValueError('Source route skipped an owned position reply')
            self.observations.append(active.observe_reply(seal, fixes[-1]))
        if isinstance(action, LocationRequest):
            collector.command_sent(action, self._request_location(action))
        if collector.phase != 'complete':
            return
        outcome = active.acknowledge_stopped(seal, *self.observations)
        self.pairs.append(collector.snapshot())
        kind = outcome.kind if self.transfer is not None else 'walk'
        self.events.append(dict(kind='source_acknowledgment', outcome=kind,
            floor_proof_sha256=outcome.floor_proof_sha256,
            raw_seq=self.observations[-1].raw_fix.log_line_seq,
            real_client_accepted=False))
        if kind == 'settling':
            self._new_pair()
            return
        if kind in ('approach', 'landed'):
            self.policy.finish_transfer(self.transfer)
            self.transfer = None
        self.collector = self.seal = None
        self.observations = []
        self.phase = 'ready'

    def tick(self):
        if self.phase == 'complete':
            return
        e, p = self.engine, self.pending
        self.check_current()
        if p['busy']:
            return  # Nested pumps check scope without consuming the reader.
        p['busy'] = True
        try:
            self.active._check()
            if self.collector is not None:
                self._collect()
                return
            action = self.transfer.next_command() if self.transfer is not None else self.driver.next_action()
            if isinstance(action, SourceStepBoundary):
                self.transfer = SourceTransferController(self.driver, action)
                self.policy.bind_transfer(self.transfer)
                action = self.transfer.next_command()
            elif isinstance(action, SourceWalkFinished):
                self.completed_arrival = action
                self.phase = 'complete'
                return

            def pump():
                e.pump()
                e.autopilot_tick(self.clock())

            self.seal = run_checked_source_step(self.sender, self.active, policy=self.policy,
                kind=action.kind, requested_seconds=action.requested_seconds,
                command_state_clear=lambda:e._route_idle() and not e.cancelled and e.jobs.empty(), pump=pump)
            self.events.append(dict(kind='source_pulse', cell_index=action.cell_index,
                movement=action.kind, receipt=asdict(self.seal.receipt),
                geometry_sha256=self.seal.ticket.geometry.sha256, real_client_accepted=False))
            self._new_pair()
        except BaseException as error:
            self.cancel(str(error))
            raise
        finally:
            p['busy'] = False

    def snapshot(self):
        return dict(phase=self.phase, reason=self.reason, itinerary_sha256=self.driver.plan.sha256,
            cell_index=self.driver.index, completed_movements=self.ledger.steps,
            transfer_phase=None if self.transfer is None else self.transfer.phase,
            partial_movements=0 if self.transfer is None else self.transfer.local_steps,
            incomplete_pair=None if self.collector is None else self.collector.snapshot(),
            stopped_pairs=list(self.pairs), executor_events=list(self.events), policy=self.policy.snapshot(),
            ordinary_route_driver_used=False, real_client_accepted=False)
