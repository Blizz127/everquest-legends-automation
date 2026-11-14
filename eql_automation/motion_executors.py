"""Concrete measurement input and shared checked location-command execution.

No default scene/envelope observer exists. ``check_input`` is a required live
dependency and must not consume the collector's exclusive location reader.
It checks closed chat before/after a command, known helper drafting during
typing, and current scene plus the initial travel envelope for movement.
Engine flags and these evidence envelopes do not establish those facts.
"""
from dataclasses import asdict, dataclass
import os
from uuid import uuid4

from .motion_calibration import finite
from .motion_collection import (CommandReceipt, ReleasedPulse, LocationRequest,
                               MotionRequest, MotionExperimentSession, CollectionStopped)
from .location_hotkey import _fd_identity
from .uinput_watchdog import _EVENT, PulseSelection, selected_key_pulse_receipt
from .command_submission import (CommandSubmissionJournal, CommandSubmissionSnapshot,
                                 LOCATION_KEYS)


@dataclass(frozen=True)
class MeasurementInputEvidence:
    request: LocationRequest | MotionRequest
    phase: str
    observed_at: float
    valid_until: float
    record_id: str
    submission: CommandSubmissionSnapshot | None = None


class _PinnedCommandIO:
    def __init__(self, scope):
        self.scope = scope

    def write(self, kind, code, value):
        s = self.scope
        with s.session.lock:
            if kind != 1 or type(code) is not int or not 1 <= code <= 255 or value not in (0,1):
                raise ValueError('Unexpected command input event')
            if value:
                s.binding()
                if s.evidence is None or s.session.clock() > s.evidence.valid_until:
                    raise CollectionStopped('Per-key command observation expired')
                snapshot=s.checked_submission
                if (snapshot is None or s.evidence.submission is not snapshot
                        or s.journal.revision!=snapshot.revision
                        or snapshot.uncertain or snapshot.next_key_code!=code):
                    raise CollectionStopped('Command submission changed after observation')
                # A write error does not prove the slash/Enter was undelivered.
                s.chat_started = True
                s.sender.unfinished = True
                s.owned_keys.add(code)
                s.pending_releases.add(code)
            s.write_event(kind, code, value)

    def syn(self):
        self.scope.write_event(0,0,0)

    def fileno(self):
        return self.scope.fd


class _Scope:
    def __init__(self, owner, request, phase):
        self.owner, self.engine, self.session = owner, owner.engine, owner.session
        self.request, self.phase = request, phase
        self.sender = self.engine.sender
        self.marker, self.fd = object(), None
        self.owned_keys = set()
        # Independent of sender bookkeeping, which another stop may clear.
        self.pending_releases = set()
        self.chat_started = False
        self.evidence = None
        self.receipt = None
        self.final_release_at = None
        self.cleanup_error = None
        self.claimed = False
        self.journal=(CommandSubmissionJournal(uuid4().hex)
                      if isinstance(request,LocationRequest) else None)
        self.checked_submission=None
        self.driver=None

    def timestamp(self):
        # Receipt diagnostics must never prevent unconditional UP/SYN cleanup.
        try:
            now=self.session.clock()
            return now if finite(now) else None
        except BaseException:
            return None

    def same_device(self):
        try:
            return (self.engine.sender is self.sender and self.sender.ui is self.ui
                    and self.ui.fileno() == self.original_fd
                    and _fd_identity(self.original_fd) == self.identity)
        except Exception:
            return False

    def binding(self):
        self.session._check()
        e, s = self.engine, self.sender
        driver = self.owner._bound_driver()
        if self.driver is None:self.driver = driver
        if (self.session.pending is not self.request or self.session.phase != self.phase
                or driver is not self.driver or e.cancelled or not e.jobs.empty()
                or s is None or not self.same_device()
                or getattr(s,'_eql_route_operation',None) is not self.marker
                or self.session.clock() > self.request.expires_at +
                    (.2 if isinstance(self.request,MotionRequest) and self.owned_keys else 0)):
            raise CollectionStopped('Measurement request, engine or sender binding changed')

    def check(self, phase):
        self.binding()
        # Honor the original sender's owner-input/focus checks as well as the
        # independent scene provider. No flag is reset to obtain permission.
        self.engine.pump()
        self.engine.autopilot_tick(self.session.clock())
        self.binding()
        self.sender.check()
        self.binding()
        with self.session.lock:
            self.binding()
            snapshot=None if self.journal is None else self.journal.snapshot()
            if snapshot is not None:
                if (snapshot.uncertain or (phase in ('command_start','command_first_key') and snapshot.writes)
                        or (phase=='command_key' and (not 1<=snapshot.submitted_key_count<len(LOCATION_KEYS)
                                                      or snapshot.next_key_code is None))
                        or (phase=='command_end' and not snapshot.enter_submitted)):
                    raise CollectionStopped('Command submission is incomplete or uncertain')
        # No new lock spans the independent observation callback.
        observed = self.owner.check_input(self.request,phase,snapshot)
        with self.session.lock:
            self.binding()
            if snapshot is not None and self.journal.revision!=snapshot.revision:
                raise CollectionStopped('Command submission changed during observation')
        if phase in ('command_first_key','command_key') and (
                self.sender.held or self.sender.dismissed
                or self.sender.unfinished is not (phase == 'command_key')):
            raise CollectionStopped('Per-key command ownership changed')
        now = self.session.clock()
        if (not isinstance(observed,MeasurementInputEvidence)
                or observed.request is not self.request or observed.phase != phase
                or observed.submission is not snapshot
                or not all(finite(t) for t in (observed.observed_at,observed.valid_until))
                or not self.request.issued_at <= observed.observed_at <= now <= observed.valid_until
                or observed.valid_until > observed.observed_at+.1
                or not isinstance(observed.record_id,str) or not observed.record_id):
            raise CollectionStopped('Independent measurement input evidence unavailable or expired')
        self.evidence = observed
        self.checked_submission=snapshot
        self.session.executor_events.append(dict(kind='input_check',phase=phase,at=now,
            evidence_id=observed.record_id,
            command_operation_id=None if snapshot is None else snapshot.operation_id,
            submission_revision=None if snapshot is None else snapshot.revision,
            submitted_prefix=None if snapshot is None else snapshot.submitted_prefix,
            enter_submitted=False if snapshot is None else snapshot.enter_submitted))
        return observed

    def write_event(self, kind, code, value):
        with self.session.lock:
            attempt=(None if self.journal is None else self.journal.begin(
                (kind,code,value),self.timestamp(),_EVENT.size))
            if attempt is not None and kind==1 and value==1 and attempt.started_at is None:
                self.journal.finish(attempt,self.timestamp(),outcome='not_submitted',
                                    error='Command write clock unavailable')
                raise CollectionStopped('Command write clock unavailable')
            try:
                written=self.raw_write_event(kind,code,value)
            except BaseException as error:
                if attempt is not None:
                    self.journal.finish(attempt,self.timestamp(),outcome='exception',
                                        error=type(error).__name__+': '+str(error))
                raise
            if attempt is not None:
                self.journal.finish(attempt,self.timestamp(),written_bytes=written,
                                    outcome='complete' if written==_EVENT.size else 'short')
            if written!=_EVENT.size:
                raise OSError('Incomplete pinned input write')

    def raw_write_event(self, kind, code, value):
        payload = _EVENT.pack(0,0,kind,code,value)
        return os.write(self.fd,payload)

    def release(self, code):
        # No focus/scene checks during release. Never dereference a replaced UI.
        self.write_event(1,code,0)
        self.write_event(0,0,0)
        self.pending_releases.discard(code)
        if self.same_device():
            self.sender.held.discard(code)

    def __enter__(self):
        with self.session.lock:
            s = self.sender
            if (s is None or self.session.lock is not getattr(self.engine,'g0_stop_lock',None)
                    or getattr(s,'_eql_route_operation',None) is not None
                    or s.unfinished is not False or s.dismissed is not False or s.held):
                raise CollectionStopped('Existing idle sender with shared stop lock required')
            self.ui = s.ui
            self.original_fd = self.ui.fileno()
            self.identity = _fd_identity(self.original_fd)
            s._eql_route_operation = self.marker
            self.claimed = True
            try:
                self.binding()
                self.fd = os.dup(self.original_fd)
            except BaseException:
                s._eql_route_operation = None
                self.claimed = False
                raise
        return self

    def __exit__(self, error_type, error, tb):
        try:
            with self.session.lock:
                for key in sorted(self.pending_releases):
                    try:
                        self.release(key)
                    except BaseException as cleanup:
                        self.cleanup_error = cleanup
                if self.cleanup_error is not None or error is not None:
                    if self.chat_started:
                        self.sender.unfinished = True
                    self.session.cancel(str(self.cleanup_error or error))
                self.session.executor_events.append(dict(kind='executor_result',
                    operation='location' if isinstance(self.request,LocationRequest) else 'pulse',
                    phase=self.session.phase, at=self.timestamp(),
                    child_receipt=None if self.receipt is None else asdict(self.receipt),
                    final_release_at=self.final_release_at,
                    held_keys=sorted(self.sender.held), same_device=self.same_device(),
                    pending_releases=sorted(self.pending_releases),
                    command_submission=None if self.journal is None else asdict(self.journal.snapshot()),
                    error=None if error is None else str(error),
                    cleanup_error=None if self.cleanup_error is None else str(self.cleanup_error)))
        finally:
            try:
                if self.fd is not None:
                    os.close(self.fd)
            finally:
                if self.claimed and getattr(self.sender,'_eql_route_operation',None) is self.marker:
                    self.sender._eql_route_operation = None
        if self.cleanup_error is not None:
            raise self.cleanup_error
        return False


def _command_view(scope):
    """Reuse the actual command/character/tap code, with immutable pinned I/O.

    This view bypasses the sender constructor; it creates no virtual device.
    The engine retains its original sender object throughout the operation.
    """
    class CommandView(type(scope.sender)):
        def __init__(self):
            self.codes = scope.sender.codes
            self.allowed = scope.sender.allowed
            self.gate = scope.sender.gate
        @property
        def ui(self): return io
        @property
        def held(self): return scope.sender.held
        @property
        def unfinished(self): return scope.sender.unfinished
        @unfinished.setter
        def unfinished(self,value): scope.sender.unfinished = value
        @property
        def dismissed(self): return scope.sender.dismissed
        @dismissed.setter
        def dismissed(self,value): scope.sender.dismissed = value
        def check(self):
            scope.check('command_key' if scope.chat_started else 'command_first_key')
        def release(self,code): scope.release(code)
    io = _PinnedCommandIO(scope)
    return CommandView()


class _LocationExecutor:
    """Shared fixed-command implementation; subclasses bind a specific driver.

    check_input(request, phase, submission) returns fresh MeasurementInputEvidence
    bound to that exact immutable submission object (None for movement). For
    command_key it must understand the helper-owned draft; command_first_key
    runs before the slash and requires closed chat, as do command_start/end.
    The submission records complete key cycles and all failed attempts, but
    proves neither client delivery nor chat focus. The independent observer
    must compare the current draft/transition with this exact submitted prefix.
    No live observer is included. The caller must keep device replacement/close and
    stop operations under the same existing g0_stop_lock.
    """
    def _bound_driver(self):
        raise NotImplementedError('A concrete session/engine binding is required')

    def request_location(self, request):
        if not isinstance(request,LocationRequest):
            raise ValueError('Exact pending location request required')
        with _Scope(self,request,'requesting') as s:
            names=('SLASH','L','O','C','A','T','I','O','N','ENTER')
            if tuple(getattr(s.sender.codes,'KEY_'+name) for name in names)!=LOCATION_KEYS:
                raise CollectionStopped('Fixed location key bindings changed')
            s.check('command_start')
            if s.sender.unfinished or s.sender.dismissed or s.sender.held:
                raise CollectionStopped('Command start is not clear')
            view = _command_view(s)
            began = self.session.clock()
            view.command('/location')
            completed = self.session.clock()
            s.final_release_at = completed
            if s.sender.held or s.sender.unfinished:
                raise CollectionStopped('Command did not finish with all keys released')
            s.check('command_end')
            if s.sender.held or s.sender.unfinished or s.sender.dismissed:
                raise CollectionStopped('Command end is not clear')
            # Same attribution window as the pinned Engine.send implementation.
            self.engine.recent_commands = [(text,at) for text,at in self.engine.recent_commands
                if completed-at <= 1.5] + [('/location',completed)]
            self.engine.trace('command',text='/location',phase='entered',measurement=True,
                              purpose=self.command_purpose)
            return CommandReceipt(began,completed)


class MeasurementExecutors(_LocationExecutor):
    """Checked command/pulse callbacks for MotionExperimentDriver.

    In addition to the command checks described by _LocationExecutor,
    pulse_start/held/end require current input/scene checks; pulse_start also
    covers the complete initial spatial envelope for the exact key and hold.
    No default live provider exists. No movement logic is shared with routes.
    """
    command_purpose = 'motion_calibration'
    def __init__(self, engine, session, *, check_input):
        if (not isinstance(session,MotionExperimentSession) or not callable(check_input)
                or session.lock is not getattr(engine,'g0_stop_lock',None)):
            raise ValueError('Bound measurement session and independent input provider required')
        self.engine, self.session, self.check_input = engine,session,check_input

    def _bound_driver(self):
        driver = self.engine.motion_collection_driver
        if (driver is None or driver.session is not self.session or not driver.busy
                or not self.engine._motion_idle()):
            raise CollectionStopped('Measurement driver or idle binding changed')
        return driver

    def run_pulse(self, request):
        if not isinstance(request,MotionRequest):
            raise ValueError('Exact pending motion request required')
        with _Scope(self,request,'pulsing') as s:
            if (request.index != len(self.session.receipts) or not self.session.pairs
                    or request.reference is not self.session.pairs[-1]
                    or (s.sender.codes.KEY_UP,s.sender.codes.KEY_LEFT,s.sender.codes.KEY_RIGHT) != (103,105,106)):
                raise CollectionStopped('Pulse reference, index or key bindings changed')
            key = request.probe.key_code
            def select():
                evidence = s.check('pulse_start')
                if s.sender.held or s.sender.unfinished or s.sender.dismissed:
                    raise CollectionStopped('Pulse sender is not idle')
                s.owned_keys.add(key)
                s.pending_releases.add(key)
                s.sender.held.add(key)
                return PulseSelection(key,request.probe.seconds,min(request.expires_at,evidence.valid_until))
            def pump():
                self.engine.pump()
                self.engine.autopilot_tick(self.session.clock())
            def stop():
                try:
                    with self.session.lock:
                        if key in s.owned_keys:
                            s.check('pulse_held')
                        else:
                            # No input exists during child startup. Full scene
                            # and envelope evaluation happens once READY lets
                            # select() obtain a current check.
                            pump()
                            s.binding()
                            s.sender.check()
                            s.binding()
                        if s.sender.unfinished or s.sender.dismissed or s.sender.held-{key}:
                            raise CollectionStopped('Pulse input ownership changed')
                    return False
                except Exception as error:
                    self.session.cancel(str(error))
                    return True
            try:
                s.receipt = selected_key_pulse_receipt(s.fd,select,pump=pump,should_stop=stop,
                                                     go_lock=self.session.lock)
            finally:
                with self.session.lock:
                    if key in s.owned_keys:
                        if not s.same_device():
                            raise CollectionStopped('Device changed; final sender release unavailable')
                        s.sender.release(key)
                        if key in s.sender.held:
                            raise CollectionStopped('Sender did not acknowledge final UP/SYN')
                        s.pending_releases.discard(key)
                        s.final_release_at = self.session.clock()
            if s.receipt is None or s.final_release_at is None:
                raise CollectionStopped('Pulse has no complete release receipt')
            s.check('pulse_end')
            if s.sender.held or s.sender.unfinished or s.sender.dismissed:
                raise CollectionStopped('Pulse end is not clear')
            return ReleasedPulse(s.receipt,s.final_release_at)
