"""Finite calibration collection on engine ticks, with no default input driver.

The caller supplies checked command/pulse executors. They must enforce current
scene, initial travel envelope and descriptor release. This module preserves
their receipts and fresh log provenance; it does not establish those guards.
It never uses the old autopilot calibration or its bare coordinate callback.
"""
from dataclasses import asdict, dataclass
from datetime import datetime
import math
import threading
import time

from .location_log import LocationLogReader
from .unbound_location_log import UnboundLocationReader
from .motion_calibration import (PROBES, Position, StoppedPair, finite, integer,
                                 reduce_experiment, pair_geometry, measure_forward,
                                 measure_turn, common_speed)
from .uinput_watchdog import PulseReceipt


class CollectionStopped(RuntimeError):
    pass


def immutable_binding(value):
    return (isinstance(value, tuple) and bool(value) and all(
        immutable_binding(item) if isinstance(item, tuple)
        else isinstance(item, str) and bool(item) or integer(item)
        for item in value))


@dataclass(frozen=True)
class LocationRequest:
    serial: int
    pair_index: int
    issued_at: float
    expires_at: float


@dataclass(frozen=True)
class MotionRequest:
    index: int
    reference: StoppedPair
    issued_at: float
    expires_at: float

    @property
    def probe(self):
        return PROBES[self.index]


@dataclass(frozen=True)
class CommandReceipt:
    started_at: float
    completed_at: float


@dataclass(frozen=True)
class ReleasedPulse:
    receipt: PulseReceipt
    final_release_at: float


class MotionExperimentSession:
    """One finite measurement session; unknown bindings never use log history.

    Normally requires a new matching zone event. Explicit relative measurement
    instead uses UnboundLocationReader and None for all zone fields: it measures
    motion in printed coordinate units without claiming an absolute zone.
    ``binding_reader`` must return the same owner settings/window/process tuple
    throughout. It must not silently restore it after a process/settings change.
    Consumers must poll at each engine tick, including while a checked executor
    pumps cancellation. There is no automatic retry or rearming.
    """
    def __init__(self, reader, *, zone_id, zone_display_name, zone_short_name,
                 generation, generation_reader, mode_reader, binding_reader,
                 record_id, horizontal_error, legacy,
                 clock=time.monotonic, local_wall_clock=datetime.now, stop_lock=None,
                 relative=False):
        source_valid = ((relative is False and isinstance(reader, LocationLogReader)
                         and integer(zone_id) and bool(zone_display_name) and bool(zone_short_name))
                        or (relative is True and isinstance(reader, UnboundLocationReader)
                            and zone_id is None and zone_display_name is None and zone_short_name is None))
        if (not source_valid
                or not integer(generation) or not isinstance(record_id, str) or not record_id
                or not finite(horizontal_error) or horizontal_error <= 0
                or not all(callable(f) for f in (generation_reader, mode_reader, binding_reader,
                                                clock, local_wall_clock))):
            raise ValueError("Bound reader, identity, generation and explicit error assumption required")
        self.lock = threading.RLock() if stop_lock is None else stop_lock
        if not all(callable(getattr(self.lock, name, None)) for name in ('acquire','release','__enter__','__exit__')):
            raise ValueError('A shared stop lock must be a context-manageable lock')
        self.reader, self.zone, self.relative = reader, zone_short_name, relative
        self.generation, self.generation_reader = generation, generation_reader
        self.mode_reader, self.binding_reader = mode_reader, binding_reader
        self.binding = binding_reader()
        if not immutable_binding(self.binding):
            raise ValueError("Owner settings/window/process binding must be an immutable tuple")
        self.clock, self.wall_clock, self.legacy = clock, local_wall_clock, legacy
        self.record_id, self.error = record_id, horizontal_error
        self.started = self.last_at = clock()
        self.log_binding = (zone_id, zone_display_name, reader.tail.identity,
                            reader.tail.epoch, None if relative else reader.zone_generation)
        self.phase, self.reason = "need_location", ""
        self.pairs, self.receipts, self.requests, self.releases, self.raw_fixes = [], [], [], [], []
        self.legs, self.turns = [], []
        self.release_attempts = []
        self.executor_events = []
        self.first = self.pending = self.result = None
        self.due, self.deadline = self.started, self.started + 2.5
        self.last_seq = self._reader_sequence()
        self.latest = reader.latest
        self._check()

    def _reader_sequence(self):
        return self.reader.line_seq if self.relative else self.reader.log_line_seq

    def _reader_binding(self):
        r = self.reader
        if self.relative:
            return None, None, r.tail.identity, r.tail.epoch, None
        return r.zone_id, r.zone_display_name, r.tail.identity, r.tail.epoch, r.zone_generation

    def cancel(self, reason):
        with self.lock:
            if self.phase != "complete":
                self.phase, self.reason, self.pending = "stopped", str(reason), None
                self.result = None

    def _stop(self, reason):
        self.cancel(reason)
        raise CollectionStopped(str(reason))

    def _check(self):
        if self.phase == "stopped":
            raise CollectionStopped(self.reason)
        now = self.clock()
        generation = self.generation_reader()
        if (not finite(now) or not finite(self.started) or now < self.last_at
                or now - self.started > 120 or type(generation) is not int
                or generation != self.generation or self.mode_reader() != "measurement"
                or self.binding_reader() != self.binding or self.phase == "stopped"):
            self._stop("Measurement cancelled, binding changed or clock expired")
        self.last_at = now
        current = self._reader_binding()
        if current != self.log_binding or self.reader.tail.identity is None:
            self._stop("Fresh zone/log binding missing or changed")
        return now

    def _poll(self):
        now = self._check()
        if self._reader_sequence() != self.last_seq or self.reader.latest is not self.latest:
            self._stop("Location reader was consumed outside this session")
        old_seq = self._reader_sequence()
        try:
            fixes = self.reader.poll(now=now)
        except Exception as exc:
            self._stop("Location reader failed: " + str(exc))
        now = self._check()
        # Partial lines may include a delayed location. Do not carry them
        # through another command or pulse as though the stream were drained.
        if self.reader.tail.partial:
            self._stop("Incomplete log line during measurement")
        if self._reader_sequence() != old_seq + len(fixes):
            self._stop("Location replies were invalidated or consumed elsewhere")
        if len(fixes) > 1 or (fixes and self.phase != "await_location"):
            self._stop("Batched or unsolicited location replies")
        if not fixes:
            if self.reader.latest is not self.latest:
                self._stop("Location reader invalidated its latest observation")
            return
        fix = fixes[0]
        request, sent = self.pending
        wall = self.wall_clock()
        if (not isinstance(wall, datetime) or wall.tzinfo is not None
                or abs((wall - fix.log_local_time).total_seconds()) > 2
                or fix.log_line_seq <= self.last_seq
                or not sent.completed_at <= fix.received_monotonic <= now <= request.expires_at):
            self._stop("Location reply timing or sequence is invalid")
        self.last_seq = fix.log_line_seq
        self.latest = fix
        raw = asdict(fix)
        raw["log_local_time"] = fix.log_local_time.isoformat()
        self.raw_fixes.append(raw)
        position = Position(fix.received_monotonic, fix.log_line_seq, fix.raw_coordinates,
                            self.zone, fix.log_epoch, None if self.relative else fix.zone_generation)
        self.pending = None
        if self.first is None:
            self.first = position
            self.due, self.deadline = position.at + .4, position.at + 2.5
            self.phase = "need_location"
            return
        pair = StoppedPair(self.first, position)
        if (not .4 - 1e-9 <= position.at - self.first.at <= 2.5
                or math.dist(position.raw_yxz[:2], self.first.raw_yxz[:2]) > .25
                or abs(position.raw_yxz[2] - self.first.raw_yxz[2]) > .25):
            self._stop("Fresh position pair did not remain stopped")
        if self.pairs:
            before, e1 = pair_geometry(self.pairs[-1], self.error)
            after, e2 = pair_geometry(pair, self.error)
            if abs(after[2] - before[2]) > .25:
                self._stop("Measurement changed height")
            probe = PROBES[len(self.receipts)-1]
            if probe.key != "forward" and math.dist(after[:2], before[:2]) > min(.25, e1+e2):
                self._stop("Pivot translated the character")
            if probe.key == "forward":
                try:
                    index = len(self.receipts)-1
                    leg = measure_forward(index, self.pairs[-1], pair, self.receipts[-1],
                                          legacy=self.legacy, horizontal_error=self.error)
                    common_speed([*self.legs, leg])
                    if self.legs:
                        turn = measure_turn(index-1, self.legs[-1], leg,
                                            self.receipts[-2], legacy=self.legacy)
                        if self.turns and ((index == 4 and turn['delta']*self.turns[0]['delta'] <= 0)
                                or (index == 6 and turn['delta']*self.turns[0]['delta'] >= 0)):
                            raise ValueError("Turn directions contradict previous observations")
                        self.turns.append(turn)
                    self.legs.append(leg)
                except Exception as exc:
                    self._stop("Intermediate motion cannot be measured: " + str(exc))
        self.pairs.append(pair)
        self.first = None
        if len(self.pairs) == 8:
            try:
                self.result = reduce_experiment(self.pairs, self.receipts, legacy=self.legacy,
                    horizontal_error=self.error, record_id=self.record_id)
            except Exception as exc:
                self._stop("Collected experiment cannot be fitted: " + str(exc))
            self._check()
            self.phase = "complete"
        else:
            self.phase = "need_pulse"

    def tick(self):
        """Return at most one proposal. Caller must execute with its own guards."""
        with self.lock:
            if self.phase == "complete":
                return None
            self._poll()
            if self.phase == "complete":
                return None
            now = self._check()
            if self.phase in ("need_location", "await_location", "requesting"):
                if now > self.deadline:
                    self._stop("Stopped location request expired")
                if self.phase != "need_location" or now < self.due:
                    return None
                self.pending = LocationRequest(len(self.requests), len(self.pairs), now, self.deadline)
                self.phase = "requesting"
                return self.pending
            if self.phase == "need_pulse":
                limit = self.pairs[-1].second.at + .5
                if now > limit:
                    self._stop("Stopped reference expired before pulse")
                self.pending = MotionRequest(len(self.receipts), self.pairs[-1], now, limit)
                self.phase = "pulsing"
                return self.pending
            # While the external executor pumps, polling observes cancellation
            # and unsolicited replies but cannot schedule another operation.
            if self.phase == "pulsing" and now > self.pending.expires_at + .2:
                self._stop("Pulse executor exceeded the collection deadline")
            return None

    def command_sent(self, request, receipt):
        with self.lock:
            now = self._check()
            if (self.phase != "requesting" or request is not self.pending
                    or not isinstance(receipt, CommandReceipt)
                    or not all(finite(t) for t in (receipt.started_at, receipt.completed_at))
                    or not request.issued_at <= receipt.started_at <= receipt.completed_at <= now <= request.expires_at):
                self._stop("Location command completion does not match the pending request")
            self.requests.append(dict(request=asdict(request), receipt=asdict(receipt)))
            self.pending, self.phase = (request, receipt), "await_location"

    def pulse_released(self, request, released):
        with self.lock:
            # A cancellation after cleanup must not erase what the executor
            # reported physically writing. This is evidence, not acceptance.
            self.release_attempts.append(dict(index=getattr(request, "index", None),
                reported=asdict(released) if isinstance(released, ReleasedPulse) else None,
                phase=self.phase))
            now = self._check()
            if (self.phase != "pulsing" or request is not self.pending
                    or not isinstance(released, ReleasedPulse)
                    or not isinstance(released.receipt, PulseReceipt)):
                self._stop("No matching pulse and final-release receipt")
            r, probe = released.receipt, request.probe
            stamps = (r.down_started_at, r.down_completed_at, r.up_started_at,
                      r.up_completed_at, released.final_release_at)
            if (r.key_code != probe.key_code or type(r.key_code) is not int
                    or r.requested_seconds != probe.seconds or r.completion != "elapsed"
                    or not all(finite(t) for t in stamps)
                    or not request.issued_at <= stamps[0] <= request.expires_at
                    or not stamps[0] <= stamps[1] < stamps[2] <= stamps[3] <= stamps[4] <= now
                    or not probe.seconds - 1e-9 <= stamps[2]-stamps[1]
                    or r.maximum_held_seconds > .2 or now - stamps[3] > .3):
                self._stop("Pulse cancelled, timing overrun or final release unavailable")
            self.receipts.append(r)
            self.releases.append(asdict(released))
            self.pending, self.phase = None, "need_location"
            self.due, self.deadline = released.final_release_at + .12, r.up_completed_at + 2.5

    def snapshot(self):
        """Serializable partial evidence; completion never grants movement."""
        with self.lock:
            return dict(format="eql-motion-experiment-v1", record_id=self.record_id,
                relative_measurement=self.relative,
                absolute_zone_binding='unbound' if self.relative else 'log_event',
                horizontal_error=self.error, outcome=self.phase, reason=self.reason,
                pairs=[asdict(p) for p in self.pairs], receipts=[asdict(r) for r in self.receipts],
                raw_fixes=list(self.raw_fixes), command_requests=list(self.requests),
                final_releases=list(self.releases), owner_binding=self.binding,
                release_attempts=list(self.release_attempts),
                executor_events=list(self.executor_events),
                log_binding=self.log_binding, cancel_generation=self.generation,
                started_monotonic=self.started, last_checked_monotonic=self.last_at,
                estimate=self.result, input_authorized=False, real_client_accepted=False,
                request_correlation_verified=False)


class MotionExperimentDriver:
    """Service one session from an engine tick with explicit checked executors.

    No executors are supplied by default. A callback returns only after its
    command/pulse and cleanup finish; an exception cancels the whole session.
    The pulse executor must pump ``session.tick`` while held so input/log
    cancellation is observed. It must release even when that pump raises.
    """
    def __init__(self, session, *, request_location, run_pulse):
        if not isinstance(session, MotionExperimentSession) or not all(
                callable(f) for f in (request_location, run_pulse)):
            raise ValueError("Session and checked executors are required")
        self.session, self.request_location, self.run_pulse = session, request_location, run_pulse
        self.busy = False

    def tick(self):
        if self.busy:
            # A valid reply can be printed during Enter handling, before the
            # typed-command callback returns. Defer its read until completion;
            # retain cancellation checks while the executor handles its guards.
            if self.session.phase == "requesting":
                with self.session.lock:
                    self.session._check()
            else:
                self.session.tick()
            return
        self.busy = True
        try:
            action = self.session.tick()
            if isinstance(action, LocationRequest):
                self.session.command_sent(action, self.request_location(action))
            elif isinstance(action, MotionRequest):
                self.session.pulse_released(action, self.run_pulse(action))
        except BaseException as exc:
            self.session.cancel(str(exc))
            raise
        finally:
            self.busy = False
