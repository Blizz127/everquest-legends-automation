"""Run a fixed corridor through checked steps and fresh stopped log pairs.

The session owns its LocationLogReader and preserves the exact aligned stopped
reference throughout each pulse. The driver uses the existing transactional
sender; it supplies no default input, scene, calibration or motion authority.
No owner hotkey instantiates this loop. Assist/off cannot run it.
"""
from dataclasses import asdict, dataclass
from datetime import datetime

from .fixed_route_follower import RouteHalt, finite
from .ground_observer import RouteGroundObserver
from .location_log import LocationLogReader
from .motion_collection import CommandReceipt, LocationRequest, immutable_binding
from .route_floor_commit import RouteFloorCommit
from .route_step_sender import RouteStepResult, RouteStepScene, run_checked_route_step


@dataclass(frozen=True)
class RouteStepRequest:
    index: int
    reference: object
    issued_at: float
    expires_at: float


class RouteSession:
    """Tick-driven route execution; each command and pulse is explicit.

    A new matching zone event must already have bound the exclusive reader.
    ``initial_release_at`` is supplied by the caller after releasing controls;
    it is not inferred from a quiet log. The mandatory external location
    executor must guard its own chat/input operation and finish all cleanup
    before returning a CommandReceipt. Printed replies have no request ID.
    """
    def __init__(self, ledger, reader, ground, *, initial_release_at,
                 binding_reader, record_id, max_seconds=1800.,
                 local_wall_clock=datetime.now, zone_lease=None):
        if (not isinstance(ledger, RouteFloorCommit)
                or not isinstance(reader, LocationLogReader)
                or not isinstance(ground, RouteGroundObserver)
                or not callable(binding_reader) or not callable(local_wall_clock)
                or not isinstance(record_id, str) or not record_id
                or not finite(max_seconds) or not 0 < max_seconds <= 86400):
            raise ValueError('Route ledger, exclusive log, ground producer and bounded session required')
        if zone_lease is not None:
            from .owner_zone_tracker import ZoneReaderLease
            if not isinstance(zone_lease, ZoneReaderLease) or zone_lease.reader is not reader:
                raise ValueError('Zone lease must own the route reader')
            zone_lease.check()
        self.zone_lease = zone_lease
        r = ledger.runner
        now = ledger.clock()
        if (r.phase != 'need_start' or r.steps or ledger._pending is not None or ledger._busy is not None
                or not finite(now) or not finite(initial_release_at)
                or not 0 <= initial_release_at <= now or now-initial_release_at > 2.5
                or ground.geometry is not r.geometry_evidence):
            raise ValueError('New route at a confirmed release with matching ground geometry required')
        self.ledger, self.reader, self.ground = ledger, reader, ground
        self.runner, self.lock, self.clock = r, ledger.lock, ledger.clock
        self.binding_reader, self.wall_clock = binding_reader, local_wall_clock
        self.binding = binding_reader()
        if not immutable_binding(self.binding):
            raise ValueError('Owner settings/window/process binding must be immutable')
        self.mode = r.mode_reader()
        cal = r.height_calibration
        self.height_calibration = cal
        from .observed_height import ObservedHeightCalibration, current_height_allowed
        if isinstance(cal,ObservedHeightCalibration) and (
                not current_height_allowed(cal,mode=self.mode,route_sha256=r.route.artifact_sha256,
                                           owner_binding=self.binding)
                or cal.evidence.log_identity != reader.tail.identity):
            raise ValueError('Observed height belongs to another owner/log/route session')
        self.log_binding = (cal.zone_id, cal.zone_display_name, reader.tail.identity,
                            cal.log_epoch, cal.zone_generation)
        self.record_id, self.max_seconds = record_id, max_seconds
        self.started = self.last_at = now
        self.phase, self.reason = 'need_location', ''
        self.last_seq, self.latest = reader.log_line_seq, reader.latest
        self.pending = self.first = self.reference = None
        self.released_at = initial_release_at
        self.due, self.deadline = initial_release_at+.12, initial_release_at+2.5
        self.chain = ledger.chain
        self.requests, self.pairs, self.steps, self.raw_fixes = [], [], [], []
        self.step_attempts = []
        self.executor_events = []
        self._check()

    def cancel(self, reason):
        with self.lock:
            if self.phase != 'arrived':
                self.phase, self.reason, self.pending = 'stopped', str(reason), None
                self.reference = None
                self.ledger.cancel(str(reason))

    def _stop(self, reason):
        self.cancel(reason)
        raise RouteHalt(str(reason))

    def _check(self):
        if self.phase == 'stopped':
            raise RouteHalt(self.reason)
        now = self.clock()
        try:
            self.runner._check(now)
            if self.zone_lease is not None:
                self.zone_lease.check()
            binding = self.binding_reader()
        except Exception as error:
            self._stop('Route session binding failed: '+str(error))
        if (not finite(now) or now < self.last_at or now-self.started > self.max_seconds
                or self.runner.mode_reader() != self.mode or self.mode not in ('measurement','full_auto')
                or binding != self.binding or self.ledger.runner is not self.runner
                or self.runner.height_calibration is not self.height_calibration):
            self._stop('Route cancelled, session binding changed or deadline expired')
        current = (self.reader.zone_id, self.reader.zone_display_name, self.reader.tail.identity,
                   self.reader.tail.epoch, self.reader.zone_generation)
        if current != self.log_binding or self.reader.tail.identity is None:
            self._stop('Route zone/log identity changed')
        if self.phase != 'stepping' and self.ledger.chain is not self.chain:
            self._stop('Committed route floor changed outside a checked step')
        if self.phase in ('need_location','requesting','await_location'):
            expected = 'need_start' if not self.steps else 'await_stopped'
            if self.runner.phase != expected:
                self._stop('Route controller changed while waiting for stopped positions')
        elif self.phase == 'ready' and self.runner.phase != 'ready':
            self._stop('Route controller is no longer ready')
        self.last_at = now
        return now

    def _poll(self):
        now = self._check()
        if self.reader.log_line_seq != self.last_seq or self.reader.latest is not self.latest:
            self._stop('Route location reader was consumed elsewhere')
        old_seq = self.reader.log_line_seq
        try:
            fixes = self.reader.poll(now=now)
        except Exception as error:
            self._stop('Route location poll failed: '+str(error))
        now = self._check()
        if self.reader.tail.partial:
            self._stop('Incomplete log line during route observation')
        if self.reader.log_line_seq != old_seq+len(fixes):
            self._stop('Route location replies were invalidated')
        if len(fixes) > 1 or (fixes and self.phase != 'await_location'):
            self._stop('Batched or unsolicited route location replies')
        if not fixes:
            if self.reader.latest is not self.latest:
                self._stop('Route reader invalidated its latest location')
            return
        raw = fixes[0]
        request, receipt = self.pending
        wall = self.wall_clock()
        if (not isinstance(wall, datetime) or wall.tzinfo is not None
                or abs((wall-raw.log_local_time).total_seconds()) > 2
                or raw.log_line_seq <= self.last_seq
                or not receipt.completed_at <= raw.received_monotonic <= now <= request.expires_at):
            self._stop('Route reply timing or sequence is invalid')
        self.last_seq, self.latest = raw.log_line_seq, raw
        record = asdict(raw);record['log_local_time'] = raw.log_local_time.isoformat()
        self.raw_fixes.append(record)
        aligned = self.ground.observe(raw, route=self.runner.route, segment_index=self.runner.index,
            height_calibration=self.runner.height_calibration, now=now,
            motion_calibration_record_id=self.runner.calibration, floor_chain=self.chain,
            endpoint_radius=self.runner.radius, height_tolerance=self.runner.height_tolerance,
            mode=self.runner.mode_reader())
        self._check()
        self.pending = None
        if self.first is None:
            self.first = aligned
            self.phase = 'need_location'
            self.due, self.deadline = raw.received_monotonic+.4, raw.received_monotonic+2.5
            return
        first = self.first
        self.runner.observe_stopped(first, aligned, released_at=self.released_at, now=self.clock())
        self.first, self.reference = None, aligned
        self.pairs.append(dict(first_seq=first.raw_fix.log_line_seq, second_seq=raw.log_line_seq,
            released_at=self.released_at, position=aligned.mesh_projection.package_xyz,
            segment_index=self.runner.index, floor_proof_sha256=self.chain.previous.proof_sha256))
        self.phase = 'arrived' if self.runner.phase == 'arrived' else 'ready'
        self._check()

    def tick(self):
        """Poll once and return at most one operation; never sleep or send."""
        with self.lock:
            if self.phase == 'arrived':
                return None
            try:
                self._poll()
                if self.phase == 'arrived':
                    return None
                now = self._check()
                if self.phase in ('need_location','requesting','await_location'):
                    if now > self.deadline:
                        self._stop('Route stopped-location request expired')
                    if self.phase != 'need_location' or now < self.due:
                        return None
                    self.pending = LocationRequest(len(self.requests), len(self.pairs), now, self.deadline)
                    self.phase = 'requesting'
                    return self.pending
                if self.phase == 'ready':
                    deadline = self.reference.raw_fix.received_monotonic+.5
                    if now > deadline:
                        self._stop('Stopped route reference expired before next step')
                    self.pending = RouteStepRequest(len(self.steps), self.reference, now, deadline)
                    self.phase = 'stepping'
                    return self.pending
                if self.phase == 'stepping' and now > self.pending.expires_at+self.runner.max_step_seconds:
                    self._stop('Checked route step exceeded its deadline')
                return None
            except BaseException as error:
                self.cancel(str(error))
                raise

    def command_sent(self, request, receipt):
        with self.lock:
            now = self._check()
            if (self.phase != 'requesting' or self.pending is not request
                    or not isinstance(receipt, CommandReceipt)
                    or not all(finite(t) for t in (receipt.started_at,receipt.completed_at))
                    or not request.issued_at <= receipt.started_at <= receipt.completed_at <= now <= request.expires_at):
                self._stop('Command receipt does not match the pending route request')
            self.requests.append(dict(request=asdict(request), receipt=asdict(receipt)))
            self.pending, self.phase = (request,receipt), 'await_location'

    def step_released(self, request, result):
        with self.lock:
            self.step_attempts.append(dict(index=getattr(request,'index',None), phase=self.phase,
                result=asdict(result) if isinstance(result,RouteStepResult) else None))
            now = self._check()
            r = self.runner
            if (self.phase != 'stepping' or self.pending is not request
                    or not isinstance(result, RouteStepResult) or request.reference is not self.reference
                    or r.phase != 'await_stopped' or r.pending is not None
                    or r.steps != len(self.steps)+1 or self.ledger._pending is not None
                    or self.ledger._busy is not None or self.ledger.chain is self.chain
                    or self.ledger.chain.index != self.chain.index+1
                    or self.ledger.chain.previous.previous_sha256 != self.chain.previous.proof_sha256
                    or result.floor_proof_sha256 != self.ledger.chain.previous.proof_sha256
                    or r.released_at != result.receipt.up_completed_at
                    or not r.released_at <= now <= r.released_at+.3):
                self._stop('Checked route receipt or committed floor did not complete')
            self.steps.append(asdict(result))
            self.chain = self.ledger.chain
            self.released_at = r.released_at
            self.pending = self.reference = None
            self.phase = 'need_location'
            # The transactional sender has finished its final release before
            # returning. Settle from that return, not its earlier child receipt.
            self.due, self.deadline = now+.12, r.released_at+2.5

    def snapshot(self):
        with self.lock:
            from .observed_height import height_record
            return dict(format='eql-fixed-route-session-v1', record_id=self.record_id,
                outcome=self.phase, reason=self.reason, mode=self.mode,
                route_sha256=self.runner.route.artifact_sha256, segment_index=self.runner.index,
                segment_count=len(self.runner.route.segments), owner_binding=self.binding,
                log_binding=self.log_binding, started_monotonic=self.started, last_checked_monotonic=self.last_at,
                command_requests=list(self.requests), raw_fixes=list(self.raw_fixes), stopped_pairs=list(self.pairs),
                steps=list(self.steps), step_attempts=list(self.step_attempts),
                executor_events=list(self.executor_events),
                height_calibration=height_record(self.height_calibration),
                real_client_accepted=False, request_correlation_verified=False)


class RouteSessionDriver:
    """Join the session to the existing checked sender on an engine tick.

    ``request_location`` is a checked command executor, not bare sender.command.
    ``sample_scene(reference)`` must freshly check scene/input/log hazards
    without consuming the session's reader or rebuilding the aligned reference.
    All other provider contracts are those of run_checked_route_step.
    """
    def __init__(self, session, sender, *, request_location, sample_scene, prepare_step,
                 authorize_step, still_authorized, command_state_clear, pump,
                 supervised_policy=None):
        if not isinstance(session,RouteSession) or not all(callable(f) for f in
                (request_location,sample_scene,prepare_step,authorize_step,still_authorized,command_state_clear,pump)):
            raise ValueError('Route session, checked command and independent step providers required')
        self.session, self.sender, self.request_location = session, sender, request_location
        self.sample_scene, self.pump = sample_scene, pump
        self.options = dict(prepare_step=prepare_step,authorize_step=authorize_step,
            still_authorized=still_authorized,command_state_clear=command_state_clear,
            supervised_policy=supervised_policy)
        if supervised_policy is not None:
            from .supervised_route import SupervisedRoutePolicy
            if (type(supervised_policy) is not SupervisedRoutePolicy
                    or supervised_policy.ledger is not session.ledger
                    or session.mode != 'measurement'):
                raise ValueError('Supervised policy belongs to this measurement route only')
            session.executor_events.append(supervised_policy.snapshot())
        self.busy = False

    def tick(self):
        s = self.session
        if self.busy:
            if s.phase == 'requesting':
                # Enter may print a reply before command cleanup returns.
                with s.lock:s._check()
            else:s.tick()
            return
        self.busy = True
        try:
            action = s.tick()
            if isinstance(action,LocationRequest):
                s.command_sent(action,self.request_location(action))
            elif isinstance(action,RouteStepRequest):
                def scene():
                    s._check()
                    if s.pending is not action or s.reference is not action.reference:
                        raise RouteHalt('Stopped reference changed during route step')
                    value = self.sample_scene(action.reference)
                    s._check()
                    return RouteStepScene(action.reference,value)
                def pump():
                    self.pump()
                    self.tick()
                attempt = dict(index=action.index,started_at=s.clock(),outcome='started',
                               input_delivery='unknown',error=None)
                s.step_attempts.append(attempt)
                try:
                    result = run_checked_route_step(self.sender,s.ledger,
                        scene_provider=scene,pump=pump,**self.options)
                except BaseException as error:
                    attempt.update(outcome='failed',error=type(error).__name__+': '+str(error))
                    raise
                else:attempt['outcome'] = 'returned_receipt'
                finally:
                    policy = self.options['supervised_policy']
                    if policy is not None:
                        s.executor_events.append(dict(policy.snapshot(), record_phase='after_step_attempt'))
                s.step_released(action,result)
        except BaseException as error:
            s.cancel(str(error))
            raise
        finally:
            self.busy = False
