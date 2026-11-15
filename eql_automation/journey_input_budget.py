"""One finite input reservation budget shared by walking and fresh probes.

Accounting adds a bound; it supplies no movement permission, section-completion
receipt or saved-file resume. The engine must retain this same instance across
healthy section handoffs. Child policy deadlines and limits still apply.
"""
from dataclasses import asdict, dataclass, field
import threading

from .flat_record import flat_record_state, _value
from .ground_binding import digest, finite
from .route_geometry import RouteMotionBounds
from .supervised_route import scope_limits


@dataclass(frozen=True)
class JourneyBudgetDeclaration:
    guide_sha256: str
    destination_id: str
    arrival_mode: str
    section_count: int
    maximum_seconds: float
    maximum_pulses: int
    maximum_total_hold: float
    maximum_displacement_reserve: float

    def validate(self):
        seconds, pulses, distance, hold = scope_limits('destination_travel')
        n = self.section_count
        if (not digest(self.guide_sha256) or type(self.destination_id) is not str
                or not self.destination_id or self.arrival_mode not in ('camp', 'stop', 'zone_crossing')
                or type(n) is not int or not 1 <= n <= 16
                or type(self.maximum_pulses) is not int or not 1 <= self.maximum_pulses <= n*pulses
                or not all(finite(v) for v in (self.maximum_seconds, self.maximum_total_hold,
                                             self.maximum_displacement_reserve))
                or not 0 < self.maximum_seconds <= n*seconds
                or not 0 < self.maximum_total_hold <= n*hold
                or not 0 < self.maximum_displacement_reserve <= n*distance):
            raise ValueError('Pinned destination and finite whole-journey limits required')


@dataclass(frozen=True)
class JourneyInputReservation:
    ticket: object
    serial: int
    maximum_hold: float
    maximum_displacement: float
    input_authorized: bool = field(default=False, init=False)


def _ticket_state(ticket):
    from .source_motion import SourceMotionTicket
    from .camp_probe_transaction import CampProbeTicket
    if type(ticket) is SourceMotionTicket:
        return (type(ticket), id(ticket), id(ticket.reference), id(ticket.geometry),
                ticket.geometry.kind, ticket.serial, ticket.proposed_at,
                ticket.requested_seconds, ticket.maximum_actual_hold, ticket.movement_key,
                ticket.input_authorized)
    if type(ticket) is CampProbeTicket:
        return (type(ticket), id(ticket), id(ticket.start), ticket.preparation_sha256,
                ticket.kind, ticket.movement_key, ticket.requested_seconds,
                ticket.maximum_actual_hold, ticket.proposed_at, ticket.input_authorized)
    raise ValueError('Ordinary walking or fresh probe ticket required')


class JourneyInputBudget:
    """Sticky accounting under the sender's existing stop lock.

    ``binding_reader`` must return the current immutable owner/session identity
    (including cancellation generation), without acquiring movement permission.
    Reservations are charged before DOWN, never refunded, and cannot be replayed.
    The displacement sum uses supplied hypotheses, not measured distance.
    """
    def __init__(self, declaration, *, clock, stop_lock, owner_binding, binding_reader):
        if (type(declaration) is not JourneyBudgetDeclaration or not callable(clock)
                or not callable(binding_reader) or type(owner_binding) is not tuple
                or not owner_binding or not isinstance(stop_lock, type(threading.RLock()))):
            raise ValueError('Exact journey limits, owner binding, clock and shared stop lock required')
        declaration.validate()
        self.declaration, self.clock, self.lock = declaration, clock, stop_lock
        self.owner_binding, self.binding_reader = owner_binding, binding_reader
        self._binding = _value(owner_binding)
        self._declaration = flat_record_state(declaration)
        self._context = (declaration, clock, stop_lock, owner_binding, binding_reader)
        self.started = self.last_at = clock()
        if not finite(self.started):raise ValueError('Finite journey start time required')
        self.expires_at = self.started + declaration.maximum_seconds
        self._times = (self.started, self.expires_at)
        self.valid, self.reason = True, ''
        self._reservations = {}
        self._pulses = 0
        self._hold = self._distance = 0.
        self.check()

    def cancel(self, reason):
        with self.lock:
            if self.valid:self.reason = str(reason)
            self.valid = False

    def check(self, reservation=None):
        with self.lock:
            try:
                if not self.valid:raise ValueError(self.reason)
                binding = self.binding_reader()
                now = self.clock()
                # Re-read after the clock callback, which can deliver a stop.
                after = self.binding_reader()
                if (not self.valid or any(a is not b for a, b in zip(self._context,
                        (self.declaration, self.clock, self.lock, self.owner_binding, self.binding_reader)))
                        or flat_record_state(self.declaration) != self._declaration
                        or _value(self.owner_binding) != self._binding
                        or _value(binding) != self._binding or _value(after) != self._binding
                        or (self.started, self.expires_at) != self._times
                        or not finite(now) or not self.started <= self.last_at <= now <= self.expires_at):
                    raise ValueError('Whole-journey owner, limits or fixed deadline changed')
                if reservation is not None:
                    if type(reservation) is not JourneyInputReservation:
                        raise ValueError('Exact journey reservation required')
                    row = self._reservations.get(id(reservation.ticket))
                    if (row is None or reservation is not row[0]
                            or (id(reservation.ticket), reservation.serial, reservation.maximum_hold,
                                reservation.maximum_displacement, reservation.input_authorized) != row[1]
                            or _ticket_state(reservation.ticket) != row[2]
                            or flat_record_state(row[3]) != row[4]):
                        raise ValueError('Journey ticket, bounds or reservation changed')
                self.last_at = now
                return now
            except Exception as error:
                self.cancel(error)
                raise ValueError(self.reason) from error

    def reserve(self, ticket, *, bounds):
        """Charge the exact ticket once, before a child publishes authorization."""
        with self.lock:
            try:
                self.check()
                state = _ticket_state(ticket)
                if type(bounds) is not RouteMotionBounds:
                    raise ValueError('Explicit movement hypotheses required for journey accounting')
                bounds.validate_values(calibration_record_id=bounds.calibration_record_id,
                                       maximum_step_seconds=.2)
                key = ticket.movement_key
                kind = {103: 'forward', 105: 'left', 106: 'right'}.get(key)
                declared_kind = getattr(ticket, 'kind', None)
                if declared_kind is None:declared_kind = ticket.geometry.kind
                if (kind is None or declared_kind != kind or ticket.input_authorized is not False
                        or not finite(ticket.maximum_actual_hold)
                        or ticket.maximum_actual_hold != bounds.maximum_actual_hold
                        or not finite(ticket.requested_seconds)
                        or not bounds.minimum_requested_hold <= ticket.requested_seconds <= bounds.maximum_requested_hold
                        or id(ticket) in self._reservations):
                    raise ValueError('Journey ticket is duplicate or differs from its movement bounds')
                hold = ticket.maximum_actual_hold
                displacement = (bounds.forward_speed_upper_bound*hold if kind == 'forward'
                                else bounds.pivot_displacement_upper_bound) + bounds.post_release_drift
                d = self.declaration
                if (self._pulses+1 > d.maximum_pulses or self._hold+hold > d.maximum_total_hold
                        or self._distance+displacement > d.maximum_displacement_reserve):
                    raise ValueError('Whole-journey input reservation budget exhausted')
                r = JourneyInputReservation(ticket, self._pulses+1, hold, displacement)
                self._reservations[id(ticket)] = (r, (id(ticket), r.serial, hold, displacement, False),
                                                 state, bounds, flat_record_state(bounds))
                self._pulses += 1
                self._hold += hold
                self._distance += displacement
                return r
            except Exception as error:
                self.cancel(error)
                raise ValueError(self.reason) from error

    def snapshot(self):
        with self.lock:
            return dict(kind='finite_journey_input_budget', valid=self.valid, reason=self.reason,
                declaration=asdict(self.declaration), started_at=self.started, expires_at=self.expires_at,
                reserved_pulses=self._pulses, reserved_maximum_hold=self._hold,
                reserved_displacement_hypothesis=self._distance, input_authorized=False,
                permits_section_handoff=False, real_client_accepted=False)
