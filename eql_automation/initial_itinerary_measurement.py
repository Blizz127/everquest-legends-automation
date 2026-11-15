"""Charge the actual initial relative experiment to its persistent itinerary.

The caller supplies independent movement hypotheses and a separately observed
source-zone reader. Accounting does not turn relative positions into navigation
fixes, verify these hypotheses, or replace the existing supervised input guard.
"""
from dataclasses import asdict
from hashlib import sha256
import json

from .flat_record import flat_record_state
from .ground_binding import finite
from .location_log import LocationLogReader
from .motion_calibration import PROBES, Position, StoppedPair
from .motion_collection import MotionExperimentSession, MotionRequest, ReleasedPulse
from .native_region_policy import encoded
from .route_geometry import RouteMotionBounds
from .uinput_watchdog import PulseReceipt
from .zone_itinerary_budget import ZoneItineraryBudget


def initial_request_state(request):
    if (type(request) is not MotionRequest or type(request.index) is not int
            or not 0 <= request.index < len(PROBES)
            or type(request.reference) is not StoppedPair
            or any(type(v) is not Position for v in
                   (request.reference.first, request.reference.second))):
        raise ValueError('Exact initial experiment request and stopped reference required')
    return (id(request), request.index, id(request.reference),
        flat_record_state(request.reference.first), flat_record_state(request.reference.second),
        request.issued_at, request.expires_at, flat_record_state(request.probe))


class InitialItineraryMeasurement:
    def __init__(self, session, root_budget, *, bounds, bounds_basis, source_reader):
        if (type(session) is not MotionExperimentSession or session.relative is not True
                or type(root_budget) is not ZoneItineraryBudget
                or session.clock is not root_budget.clock or session.lock is not root_budget.lock
                or type(bounds) is not RouteMotionBounds or type(bounds_basis) is not bytes
                or not 0 < len(bounds_basis) <= 16384 or type(source_reader) is not LocationLogReader):
            raise ValueError('Actual initial relative experiment, root and independent bounds required')
        basis = json.loads(bounds_basis)
        if not isinstance(basis, dict) or not basis or encoded(basis) != bounds_basis:
            raise ValueError('Canonical independent initial measurement bounds provenance required')
        bounds.validate_values(calibration_record_id=bounds.calibration_record_id, maximum_step_seconds=.2)
        if any(not bounds.minimum_requested_hold <= p.seconds <= bounds.maximum_requested_hold for p in PROBES):
            raise ValueError('Explicit bounds must cover the existing standard seven probes')
        now = root_budget.check()
        session._check()
        if (session.phase != 'need_location' or session.pending is not None
                or any((session.pairs, session.receipts, session.requests, session.releases,
                        session.raw_fixes, session.release_attempts))
                or not root_budget.started <= session.started <= now):
            raise ValueError('Root deadline must precede a new untouched initial experiment')
        self.session, self.root, self.bounds = session, root_budget, bounds
        self.bounds_basis, self.source_reader = bounds_basis, source_reader
        self.clock, self.lock = session.clock, session.lock
        self.stage = root_budget.stage
        self.release_deadline = root_budget.expires_at
        self._context = (session, root_budget, bounds, bounds_basis, source_reader,
                         self.clock, self.lock, self.stage)
        self._bounds = flat_record_state(bounds)
        self._basis = sha256(bounds_basis).hexdigest()
        self._source = self._source_state()
        self._session = (session.reader, session.generation, session.generation_reader,
            session.mode_reader, session.binding_reader, session.binding, session.clock,
            session.lock, session.record_id, session.started, session.log_binding)
        self._deadline = self.release_deadline
        self.reservations, self.releases = [], []
        self._reservations, self._releases = self.reservations, self.releases
        self._reservation_rows, self._release_rows = [], []
        self._request = self._request_pin = self._reservation = None
        self._phase, self._registered = 'new', False
        self.valid, self.reason = True, ''
        self._assert_intact()
        root_budget._claim_initial_measurement(self)
        self._registered = True
        self.check()

    def _source_state(self):
        r = self.source_reader
        return (id(r.tail), r.tail.path, r.tail.identity, r.tail.epoch,
                r.zone_id, r.zone_display_name, r.zone_generation,
                r.expected_character, r.expected_server)

    def _assert_intact(self):
        s, root = self.session, self.root
        if (not self.valid or any(a is not b for a, b in zip(self._context,
                (s, root, self.bounds, self.bounds_basis, self.source_reader,
                 self.clock, self.lock, self.stage)))
                or self.stage is not root.stage or self.stage.leg_index != 0
                or self.stage.phase != 'walking' or self.stage.epoch != 0
                or self._registered and root._initial_measurement is not self
                or flat_record_state(self.bounds) != self._bounds
                or sha256(self.bounds_basis).hexdigest() != self._basis
                or self.release_deadline != self._deadline or self.release_deadline != root.expires_at
                or self._source_state() != self._source or self.source_reader.tail.partial
                or (self.source_reader.zone_id, self.source_reader.zone_display_name)
                    != (root.leg.source_zone_id, root.leg.source_name)
                or s.relative is not True or s.reader.tail.identity is None
                or s.reader.tail.path != self.source_reader.tail.path
                or s.reader.tail.identity != self.source_reader.tail.identity
                or (s.reader, s.generation, s.generation_reader, s.mode_reader, s.binding_reader,
                    s.binding, s.clock, s.lock, s.record_id, s.started, s.log_binding) != self._session
                or self.reservations is not self._reservations or self.releases is not self._releases
                or tuple(map(id, self.reservations)) != tuple(map(id, self._reservation_rows))
                or tuple((id(v), flat_record_state(v.receipt), v.final_release_at) for v in self.releases)
                    != tuple(self._release_rows)):
            raise ValueError(self.reason or 'Initial itinerary measurement ownership or hypotheses changed')
        if self._request is not None and initial_request_state(self._request) != self._request_pin:
            raise ValueError('Initial itinerary request changed after reservation')

    def cancel(self, reason):
        if self.valid:
            self.reason = str(reason)
        self.valid = False
        self.root.cancel(reason)
        self.session.cancel(reason)

    def check(self):
        try:
            self._assert_intact()
            self.root.check()
            self.session._check()
            now = self.root.check()
            self._assert_intact()
            return now
        except Exception as error:
            self.cancel(error)
            raise ValueError(self.reason) from error

    def _pending(self, request):
        now = self.check()
        s = self.session
        initial_request_state(request)
        if (s.phase != 'pulsing' or s.pending is not request
                or request.index != len(s.receipts) or request.index != len(self.releases)
                or not s.pairs or request.reference is not s.pairs[-1]
                or len(s.pairs) != request.index+1
                or not finite(request.issued_at) or not finite(request.expires_at)
                or not self.stage.started_at <= request.issued_at <= now
                or request.expires_at != request.reference.second.at+.5):
            raise ValueError('Initial measurement must retain its actual pending ordered request')
        return now

    @property
    def complete(self):
        self._assert_intact()
        return (len(self.releases) == len(PROBES) and self._phase == 'released'
                and self.session.phase == 'complete'
                and len(self.session.receipts) == len(PROBES)
                and all(a.receipt is b for a, b in zip(self.releases, self.session.receipts)))

    def observe(self, request, phase):
        with self.lock:
            try:
                now = self._pending(request)
                if phase == 'pulse_start':
                    if self._phase not in ('new', 'released') or len(self.reservations) != len(self.releases):
                        raise ValueError('Initial measurement DOWN can only be reserved once')
                    reservation = self.root.reserve_initial_measurement(self, request)
                    self._request, self._request_pin = request, initial_request_state(request)
                    self._reservation = reservation
                    self.reservations.append(reservation)
                    self._reservation_rows.append(reservation)
                    self._phase = 'reserved'
                elif phase not in ('pulse_held', 'pulse_end') or self._phase != 'reserved':
                    raise ValueError('Initial measurement callback is not inside its reserved pulse')
                if self._request is not request or self._reservation is None:
                    raise ValueError('Initial measurement callback changed its reserved request')
                self.root.check(self._reservation)
                now = self._pending(request)
                if phase == 'pulse_end':
                    self._phase = 'ended'
                limit = min(self.release_deadline, request.expires_at+.2)
                if phase == 'pulse_start':
                    limit = min(request.expires_at, self.release_deadline-self.bounds.maximum_actual_hold)
                if now > limit:
                    raise ValueError('Initial measurement input deadline expired')
                return limit
            except Exception as error:
                self.cancel(error)
                raise

    def released(self, request, released):
        with self.lock:
            try:
                now = self._pending(request)
                self.root.check(self._reservation)
                if (self._phase != 'ended' or self._request is not request
                        or type(released) is not ReleasedPulse or type(released.receipt) is not PulseReceipt):
                    raise ValueError('Actual completed initial measurement release required')
                r = released.receipt
                if (r.key_code != request.probe.key_code or r.requested_seconds != request.probe.seconds
                        or r.completion != 'elapsed' or not finite(r.maximum_held_seconds)
                        or not all(finite(v) for v in (r.down_started_at, r.down_completed_at,
                            r.up_started_at, r.up_completed_at, released.final_release_at))
                        or not 0 < r.maximum_held_seconds <= self.bounds.maximum_actual_hold
                        or not request.issued_at <= r.down_started_at <= request.expires_at
                        or not r.down_started_at <= r.down_completed_at < r.up_started_at
                            <= r.up_completed_at <= released.final_release_at <= now <= self.release_deadline):
                    raise ValueError('Initial measurement release exceeded its reserved hold or deadline')
                self.releases.append(released)
                self._release_rows.append((id(released), flat_record_state(r), released.final_release_at))
                self._phase = 'released'
                self._assert_intact()
            except Exception as error:
                self.cancel(error)
                raise

    def snapshot(self):
        return dict(kind='initial_itinerary_measurement', valid=self.valid, reason=self.reason,
            root_record_id=self.root.declaration.record_id, session_record_id=self.session.record_id,
            stage=asdict(self.stage), accepted_releases=len(self.releases),
            reserved_pulses=len(self.reservations), release_deadline=self.release_deadline,
            bounds=asdict(self.bounds), bounds_basis=json.loads(self.bounds_basis),
            relative_positions_remain_unbound=True, input_authorized=False,
            motion_bounds_verified=False, real_client_accepted=False)
