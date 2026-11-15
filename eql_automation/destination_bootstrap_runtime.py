"""Fresh destination observations and seven probes under one retained deadline.

This adapter is not connected to owner controls. A caller supplies an exclusive
destination lease, independent planning bounds, a continuous hazard observer and
explicit supervision. It never imports a source-zone floor, heading or speed.
"""
import threading

from .camp_motion_continuity import CampInputContinuity
from .camp_probe_calibration import reduce_camp_probes
from .camp_probe_preparation import CampProbePreparation
from .camp_probe_runtime import CampProbeRuntime
from .camp_stopped_height import measure_camp_stopped_height
from .destination_floor_bootstrap import DestinationFloorBootstrap
from .flat_record import flat_record_state
from .g2_safety_provider import GameWindowIdentity, focused_game_identity
from .ground_binding import finite
from .location_hotkey import HOTKEY_CODES, OwnerLocationHotkey, send_location_hotkey
from .motion_calibration import PROBES
from .motion_collection import CommandReceipt, LocationRequest
from .native_region_policy import encoded
from .owner_camp_plan_provider import checked_fresh_fit
from .owner_input_observer import OwnerInputObservation
from .route_step_sender import _fd_identity
from .scene_log_veto import SceneLogVeto
from .stopped_location_pair import StoppedLocationPair
from .supervised_camp_probe import SupervisedCampProbeDeclaration, SupervisedCampProbeScope
from .zone_itinerary_budget import ZoneItineraryBudget


class DestinationBootstrapRuntime:
    def __init__(self, bootstrap, *, sender, hotkey, owner_input, stop_lock,
                 gate, expected_window, topology_generation, log_veto,
                 declaration, check_current, command_state_clear, pump, fit_library,
                 journey_budget=None):
        if (type(bootstrap) is not DestinationFloorBootstrap or bootstrap.phase != 'new'
                or hasattr(bootstrap, '_runtime_claim')
                or type(hotkey) is not OwnerLocationHotkey
                or not isinstance(stop_lock, type(threading.RLock()))
                or type(expected_window) is not GameWindowIdentity
                or type(topology_generation) is not int or topology_generation < 0
                or type(log_veto) is not SceneLogVeto
                or type(declaration) is not SupervisedCampProbeDeclaration
                or declaration.owner_supervised_continuation is not True
                or declaration.bounds_record_id != bootstrap.bounds.record_id
                or type(declaration.record_id) is not str or not declaration.record_id
                or not finite(declaration.maximum_total_hold)
                or not 0 < declaration.maximum_total_hold <= len(PROBES)*bootstrap.bounds.maximum_actual_hold
                or journey_budget is not None and (type(journey_budget) is not ZoneItineraryBudget
                    or journey_budget.clock is not bootstrap.clock or journey_budget.lock is not stop_lock)
                or not all(callable(v) for v in (check_current, command_state_clear, pump,
                    getattr(owner_input, 'sample', None), getattr(fit_library, 'fit_calibration', None)))):
            raise ValueError('Fresh destination bootstrap and retained explicit observation scope required')
        self.bootstrap, self.sender, self.hotkey = bootstrap, sender, hotkey
        self.owner_input, self.lock, self.gate = owner_input, stop_lock, gate
        self.window, self.topology, self.log_veto = expected_window, topology_generation, log_veto
        self.current, self.command_clear, self.pump = check_current, command_state_clear, pump
        self.fit_library, self.journey_budget = fit_library, journey_budget
        self.declaration = declaration
        self._declaration = (id(declaration), flat_record_state(declaration))
        self.clock, self.wall, self.lease, self.reader = bootstrap.clock, bootstrap.wall, bootstrap.lease, bootstrap.reader
        if (log_veto.clock is not self.clock or log_veto.tail.path != self.reader.tail.path
                or log_veto.cancel_generation != bootstrap.generation):
            raise ValueError('Destination hazard observer must retain the destination log and generation')
        self.ui = sender.ui
        self.fd, self.fd_identity = self.ui.fileno(), _fd_identity(self.ui.fileno())
        self.started = self.last_at = self.clock()
        self.expires_at = (bootstrap.expires_at if journey_budget is None
                           else journey_budget.cap_deadline(bootstrap.expires_at))
        self._times = (self.started, self.expires_at)
        self._context = (bootstrap, sender, hotkey, owner_input, stop_lock, gate, expected_window,
            log_veto, check_current, command_state_clear, pump, fit_library, journey_budget,
            self.clock, self.wall, self.lease, self.reader, self.ui)
        self._veto = (log_veto.tail, log_veto.tail.path, log_veto.clock, log_veto.cancel_generation)
        self._topology = topology_generation
        self.phase, self.reason, self.busy, self.closed = 'new', '', False, False
        self.collector = self.collection_kind = self.baseline = self.released_at = None
        self.input_request = None
        self.floor = self.height = self.runtime = self.scope = self.calibration = self.calibration_seal = None
        self._floor = self._height = self._runtime = self._scope = None
        self._calibration = self._calibration_seal = None
        self.events, self.collections = [], []
        self.binding = (sender, self.ui, gate, self.lease._tracker, self.reader, self,
                        bootstrap.generation, bootstrap.owner_binding)
        self.monitor = CampInputContinuity(owner_input, topology=topology_generation,
            basis=bootstrap.bounds_basis, binding=self.binding, clock=self.clock)
        self._monitor = self.monitor
        self.bootstrap._runtime_claim = self
        self._budget_stage = None if journey_budget is None else journey_budget.stage
        if journey_budget is not None and (self._budget_stage.phase != 'bootstrap'
                or journey_budget.leg.source_zone_id != self.reader.zone_id):
            raise ValueError('Destination probes require the next itinerary bootstrap stage')
        self._check_context()
        bootstrap.check()
        if sender.held or getattr(sender, '_eql_route_operation', None) is not None:
            raise ValueError('Destination bootstrap starts only after actual input release')

    def _check_context(self):
        if self.closed or self.phase == 'stopped':
            raise ValueError(self.reason or 'Destination bootstrap scope ended')
        self.current()
        self.lease.check()
        self.hotkey.check()
        if self.journey_budget is not None:
            self.journey_budget.check()
        now = self.clock()
        binding = self.bootstrap.binding_reader()
        generation = self.bootstrap.generation_reader()
        actual = (self.bootstrap, self.sender, self.hotkey, self.owner_input, self.lock, self.gate,
            self.window, self.log_veto, self.current, self.command_clear, self.pump, self.fit_library,
            self.journey_budget, self.clock, self.wall, self.lease, self.reader, self.ui)
        if (self.closed or self.phase == 'stopped'
                or any(a is not b for a, b in zip(self._context, actual))
                or (self.started, self.expires_at) != self._times
                or self.topology != self._topology or self.monitor is not self._monitor
                or (id(self.declaration), flat_record_state(self.declaration)) != self._declaration
                or self.floor is not self._floor or self.height is not self._height
                or self.runtime is not self._runtime or self.scope is not self._scope
                or self.calibration is not self._calibration or self.calibration_seal is not self._calibration_seal
                or self.sender.ui is not self.ui or self.ui.fileno() != self.fd
                or _fd_identity(self.fd) != self.fd_identity
                or self.lease.reader is not self.reader or self.bootstrap.lease is not self.lease
                or self.bootstrap._runtime_claim is not self
                or binding != self.bootstrap.owner_binding
                or self.journey_budget is not None and (self.journey_budget.stage is not self._budget_stage
                    and not (self.phase == 'route_ready'
                        and self.journey_budget.stage.phase == 'walking'
                        and self.journey_budget.stage.leg_index == self._budget_stage.leg_index
                        and self.journey_budget.stage.epoch == self._budget_stage.epoch+1))
                or (self.log_veto.tail, self.log_veto.tail.path, self.log_veto.clock,
                    self.log_veto.cancel_generation) != self._veto
                or not finite(now) or not self.started <= self.last_at <= now <= self.expires_at
                or type(generation) is not int or generation != self.bootstrap.generation):
            raise ValueError('Destination bootstrap ownership, descriptor, generation or deadline changed')
        self.bootstrap._assert_intact()
        self.monitor.check_binding(self.binding)
        self.last_at = now
        return now

    def _check_scene(self):
        began = self._check_context()
        window = focused_game_identity(self.gate)
        before = self.owner_input.sample()
        log = self.log_veto.poll()
        after = self.owner_input.sample()
        final_window = focused_game_identity(self.gate)
        finished = self._check_context()
        if (window != self.window or final_window != self.window or not 0 <= finished-began <= .1
                or not all(type(v) is OwnerInputObservation and v.clear_at(finished)
                    and v.topology_generation == self.topology for v in (before, after))
                or not log.continuity_available or log.reason is not None
                or log.cancel_generation != self.bootstrap.generation
                or not began <= before.started_at <= before.finished_at <= log.started_at
                    <= log.finished_at <= after.started_at <= after.finished_at <= finished):
            raise ValueError('Destination input, focus or hazard observation veto')
        return finished

    def _begin_pair(self, kind):
        released = self._check_context()
        self.baseline, self.released_at = self.reader.log_line_seq, released
        self.collection_kind = kind
        self.collector = StoppedLocationPair(self.lease, released_at=released,
            check_current=self._check_context, clock=self.clock, local_wall_clock=self.wall)
        self.phase = 'collect_'+kind

    def current_input_key(self):
        if self.closed or not self.busy:
            return None
        if self.runtime is not None:
            return self.runtime.current_input_key()
        if (self.input_request is not None and self.collector is not None
                and self.collector.phase == 'requesting' and self.input_request is self.collector.pending):
            return HOTKEY_CODES[self.hotkey.key_name]
        return None

    def _collect(self):
        c = self.collector
        request = c.tick()
        if isinstance(request, LocationRequest):
            def current():
                self._check_scene()
                c.check()
                if self.collector is not c or c.phase != 'requesting' or c.pending is not request:
                    raise ValueError('Destination position request changed')
            self.input_request = request
            try:
                receipt = send_location_hotkey(self.sender, binding=self.hotkey, owner_input=self.owner_input,
                    lock=self.lock, clock=self.clock, expires_at=min(request.expires_at, self.expires_at),
                    release_deadline=self.expires_at,
                    ensure_current=current, cancel=self.cancel, pump=self.pump, record_event=self.events.append)
            finally:
                self.input_request = None
            c.command_sent(request, CommandReceipt(receipt.pulse.down_started_at, receipt.released_at))
        if c.phase != 'complete':
            return None
        self.collections.append(dict(kind=self.collection_kind, evidence=c.snapshot()))
        self.collector = None
        return c.first, c.second

    def _policy(self, transaction):
        self._check_context()
        if self.scope is None:
            r = self.runtime
            self.scope = self._scope = SupervisedCampProbeScope(r,
                declaration=self.declaration,
                monitor=self.monitor, gate=self.gate, expected_window=self.window, log_veto=self.log_veto,
                check_current=self._check_context, started_at=r.started,
                expires_at=min(self.expires_at, r.started+min(120., r.maximum_seconds)),
                journey_budget=self.journey_budget)
        return self.scope.policy(transaction)

    def tick(self):
        if self.closed or self.phase in ('complete', 'route_ready', 'stopped'):
            return
        if self.busy:
            try:
                self._check_context()
            except Exception as error:
                self.cancel(error)
                raise
            return
        self.busy = True
        try:
            self._check_scene()
            if self.phase == 'new':
                self.bootstrap.check()
                self._begin_pair('planning')
            elif self.phase.startswith('collect_'):
                kind, pair = self.collection_kind, self._collect()
                if pair is None:
                    return
                a, b = pair
                if kind == 'planning':
                    self.bootstrap.prepare(a, b, minimum_log_seq=self.baseline, released_at=self.released_at,
                        maximum_seconds=min(30., self.expires_at-self.clock()))
                    self._begin_pair('capture')
                elif kind == 'capture':
                    self.floor = self._floor = self.bootstrap.capture(a, b,
                        minimum_log_seq=self.baseline, released_at=self.released_at)
                    self._begin_pair('height')
                elif kind == 'height':
                    boot = self.bootstrap
                    self.height = self._height = measure_camp_stopped_height(self.floor, self.reader, a, b,
                        minimum_log_seq=self.baseline, released_at=self.released_at,
                        owner_binding=boot.owner_binding, binding_reader=boot.binding_reader,
                        clock=self.clock, local_wall_clock=self.wall)
                    preparation = CampProbePreparation(self.floor, self.height, self.lease, probe_kind='forward',
                        bounds=boot.bounds, bounds_basis=boot.bounds_basis, owner_binding=boot.owner_binding,
                        binding_reader=boot.binding_reader, clock=self.clock, local_wall_clock=self.wall)
                    self.runtime = self._runtime = CampProbeRuntime(preparation, sender=self.sender,
                        hotkey=self.hotkey, owner_input=self.owner_input, stop_lock=self.lock,
                        movement_policy_factory=self._policy, check_current=self._check_context,
                        command_state_clear=self.command_clear, pump=self.pump, probes=PROBES,
                        maximum_seconds=min(1500., self.expires_at-self.clock()),
                        log_veto=self.log_veto, check_scene=self._check_scene,
                        input_release_deadline=self.expires_at)
                    self.phase = 'probes'
                else:
                    raise ValueError('Unknown destination collection phase')
            elif self.phase in ('probes', 'route_planning'):
                self.runtime.tick()
                self._check_context()
                if self.runtime.phase == 'complete':
                    fit = reduce_camp_probes(self.runtime, legacy=self.fit_library,
                        record_id='camp-'+self.runtime.results[-1].sha256)
                    self.calibration = self._calibration = dict(status='conditional', estimate=fit)
                    self.calibration_seal = self._calibration_seal = (
                        self.calibration, encoded(self.calibration), self.runtime.reference,
                        tuple(self.runtime.transactions), tuple(self.runtime.results))
                    self.phase = 'complete'
                elif self.runtime.phase == 'route_ready':
                    self.phase = 'route_ready'
            else:
                raise ValueError('Unknown destination bootstrap phase')
            self._check_scene()
        except BaseException as error:
            self.cancel(error)
            raise
        finally:
            self.busy = False

    def prepare_route(self, guide, *, sections=None):
        with self.lock:
            try:
                self._check_scene()
                if self.phase != 'complete' or self.busy or self.calibration_seal is None:
                    raise ValueError('Completed idle destination measurements required')
                self.runtime.prepare_route(guide, sections=sections)
                self._check_context()
                self.phase = 'route_planning'
            except BaseException as error:
                self.cancel(error)
                raise

    def fresh_fit(self):
        """For immediate CampSourceRuntime adoption; never renews a position."""
        with self.lock:
            try:
                self._check_context()
                if self.phase != 'route_ready' or self.busy:
                    raise ValueError('Fresh destination route start is not ready')
                result = checked_fresh_fit(self, self.runtime, self.calibration)
                self._check_context()
                return result
            except BaseException as error:
                self.cancel(error)
                raise

    def cancel(self, reason):
        with self.lock:
            if self.phase == 'stopped':
                return
            self.phase, self.reason = 'stopped', str(reason)
            if self.collector is not None:
                self.collector.cancel(reason)
            if self.runtime is not None:
                self.runtime.cancel(reason)
            if self.scope is not None:
                self.scope.cancel(reason)
            self.bootstrap.cancel(reason)
            self.monitor.invalidate(reason)
            if self.journey_budget is not None:
                self.journey_budget.cancel(reason)
            self.lease.active = False

    def release(self, *, close_observer=True):
        with self.lock:
            if self.closed:
                return
            if (self.busy or self.sender.held or getattr(self.sender, '_eql_route_operation', None) is not None
                    or self.phase not in ('complete', 'route_ready', 'stopped')):
                raise ValueError('Destination bootstrap still owns work or pending input')
            if self.runtime is not None:
                self.runtime.release()
            else:
                self.lease.release()
            self.bootstrap.cancel('Destination bootstrap released')
            if close_observer:
                self.monitor.close('Destination bootstrap released')
            else:
                self.monitor.invalidate('Destination bootstrap released')
            self.closed = True

    def snapshot(self):
        return dict(phase=self.phase, reason=self.reason, started=self.started, expires_at=self.expires_at,
            closed=self.closed, collections=list(self.collections), bootstrap=self.bootstrap.snapshot(),
            probes=None if self.runtime is None else self.runtime.snapshot(),
            calibration=self.calibration, journey_budget=None if self.journey_budget is None else self.journey_budget.snapshot(),
            source_zone_state_reused=False, input_authorized=False, real_client_accepted=False)
