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

    An optional ``parent_budget`` persists across zone legs; this child retains
    its own limits and exact walking stage throughout its sections. Cancelling
    or retiring the child does not cancel the root. Policies use ``itinerary_root``
    for zone/stage checks and clamp DOWN against both absolute deadlines.
    """
    def __init__(self, declaration, *, clock, stop_lock, owner_binding, binding_reader,
                 parent_budget=None):
        # The root imports our ticket pinning helper, so keep this import local.
        from .zone_itinerary_budget import ZoneItineraryBudget
        if (type(declaration) is not JourneyBudgetDeclaration or not callable(clock)
                or not callable(binding_reader) or type(owner_binding) is not tuple
                or not owner_binding or not isinstance(stop_lock, type(threading.RLock()))
                or parent_budget is not None and (type(parent_budget) is not ZoneItineraryBudget
                    or parent_budget.clock is not clock or parent_budget.lock is not stop_lock)):
            raise ValueError('Exact journey limits, owner binding, clock and shared stop lock required')
        declaration.validate()
        self.declaration, self.clock, self.lock = declaration, clock, stop_lock
        self.owner_binding, self.binding_reader = owner_binding, binding_reader
        self._binding = _value(owner_binding)
        self._declaration = flat_record_state(declaration)
        self.parent_budget = parent_budget
        self.parent_stage = self._parent_stage = None if parent_budget is None else parent_budget.stage
        self._parent_deadline = None if parent_budget is None else parent_budget.expires_at
        self._context = (declaration, clock, stop_lock, owner_binding, binding_reader, parent_budget)
        self.started = self.last_at = self._last_at = clock()
        if not finite(self.started):raise ValueError('Finite journey start time required')
        self.expires_at = self.started + declaration.maximum_seconds
        if not finite(self.expires_at):raise ValueError('Finite absolute journey deadline required')
        self._times = (self.started, self.expires_at)
        self.valid, self.reason = True, ''
        self._reservations = {}
        self._reservation_store = self._reservations
        self._pulses = 0
        self._hold = self._distance = 0.
        self._balance = (0, 0., 0.)
        self._busy = False
        self.check()

    def cancel(self, reason):
        """Retire this child without cancelling or refunding its parent."""
        with self.lock:
            if self.valid:self.reason = str(reason)
            self.valid = False

    def _assert_local(self):
        if (not self.valid or any(a is not b for a, b in zip(self._context,
                (self.declaration, self.clock, self.lock, self.owner_binding,
                 self.binding_reader, self.parent_budget)))
                or self.parent_stage is not self._parent_stage
                or flat_record_state(self.declaration) != self._declaration
                or _value(self.owner_binding) != self._binding
                or (self.started, self.expires_at) != self._times or self.last_at != self._last_at
                or self._reservations is not self._reservation_store
                or (self._pulses, self._hold, self._distance) != self._balance
                or len(self._reservations) != self._pulses):
            raise ValueError(self.reason or 'Whole-journey owner, limits or accounting changed')

    def _check_parent_stage(self):
        parent = self.parent_budget
        if parent is not None and (parent.stage is not self.parent_stage
                or parent.expires_at != self._parent_deadline
                or parent.clock is not self.clock or parent.lock is not self.lock
                or parent.stage.phase != 'walking'
                or self.declaration.destination_id != parent.leg.destination_id
                or self.declaration.arrival_mode != parent.leg.arrival_mode):
            # A healthy root may already have advanced. Do not submit an old
            # reservation to it, which would cancel the newly active stage.
            raise ValueError('Journey child belongs to a retired or different itinerary walking stage')

    def _begin(self):
        if self._busy:
            self.cancel('Journey budget operation reentered')
            raise ValueError(self.reason)
        self._busy = True

    def _check_standalone(self, reservation):
        """Retain the original section budget's callback and timing sequence."""
        if not self.valid:raise ValueError(self.reason)
        binding = self.binding_reader()
        now = self.clock()
        after = self.binding_reader()
        if (not self.valid or any(a is not b for a, b in zip(self._context,
                (self.declaration, self.clock, self.lock, self.owner_binding,
                 self.binding_reader, self.parent_budget)))
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
        self.last_at = self._last_at = now
        return now

    def _check_locked(self, reservation=None, *, parent_reservation=None):
        if self._context[-1] is None:
            return self._check_standalone(reservation)
        self._assert_local()
        self._check_parent_stage()
        binding = self.binding_reader()
        began = self.clock()
        after = self.binding_reader()
        now = self.clock()
        self._assert_local()
        self._check_parent_stage()
        if (_value(binding) != self._binding or _value(after) != self._binding
                or not finite(began) or not finite(now)
                or not self.started <= self.last_at <= began <= now <= self.expires_at):
            raise ValueError('Whole-journey owner or fixed deadline changed')
        row = self._reservation_row(reservation)
        if self.parent_budget is not None:
            # The clocks are the exact same callable. Let the parent's closed
            # check be the last provider call, then validate only local values.
            parent_now = self.parent_budget.check(parent_reservation if row is None else row[5])
            self._assert_local()
            self._check_parent_stage()
            if self._reservation_row(reservation) is not row:
                raise ValueError('Journey reservation row replaced during parent check')
            if (self.parent_budget.valid is not True or not finite(parent_now)
                    or not now <= parent_now <= min(self.expires_at, self._parent_deadline)):
                raise ValueError('Journey child deadline or parent clock changed during parent check')
            now = parent_now
        self.last_at = self._last_at = now
        return now

    def _reservation_row(self, reservation):
        if reservation is None:return None
        if type(reservation) is not JourneyInputReservation:
            raise ValueError('Exact journey reservation required')
        row = self._reservations.get(id(reservation.ticket))
        if (row is None or reservation is not row[0]
                or _value((id(reservation.ticket), reservation.serial, reservation.maximum_hold,
                    reservation.maximum_displacement, reservation.input_authorized)) != _value(row[1])
                or _ticket_state(reservation.ticket) != row[2]
                or flat_record_state(row[3]) != row[4]
                or getattr(row[5], 'ticket', None) is not reservation.ticket
                or getattr(row[5], 'stage', None) is not self.parent_stage):
            raise ValueError('Journey ticket, bounds or reservation changed')
        return row

    def check(self, reservation=None):
        with self.lock:
            self._begin()
            try:
                return self._check_locked(reservation)
            except Exception as error:
                self.cancel(error)
                raise ValueError(self.reason) from error
            finally:
                self._busy = False

    def reserve(self, ticket, *, bounds):
        """Charge the exact ticket once, before a child publishes authorization."""
        with self.lock:
            self._begin()
            try:
                now = self._check_locked()
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
                bounds_state = flat_record_state(bounds)
                parent_reservation = None
                if self.parent_budget is not None:
                    if now + hold > self.expires_at:
                        raise ValueError('Journey child cannot finish the reserved hold before its deadline')
                    parent_reservation = self.parent_budget.reserve(ticket, bounds=bounds)
                    # The parent may invoke owner callbacks. Any successful
                    # parent charge remains spent if this child was retired.
                    now = self._check_locked(parent_reservation=parent_reservation)
                    if (now + hold > self.expires_at or _ticket_state(ticket) != state
                            or flat_record_state(bounds) != bounds_state):
                        raise ValueError('Journey child ticket, bounds or deadline changed during parent reservation')
                r = JourneyInputReservation(ticket, self._pulses+1, hold, displacement)
                self._reservations[id(ticket)] = (r, (id(ticket), r.serial, hold, displacement, False),
                                                 state, bounds, bounds_state, parent_reservation)
                self._pulses += 1
                self._hold += hold
                self._distance += displacement
                self._balance = (self._pulses, self._hold, self._distance)
                return r
            except Exception as error:
                self.cancel(error)
                raise ValueError(self.reason) from error
            finally:
                self._busy = False

    def snapshot(self):
        with self.lock:
            return dict(kind='finite_journey_input_budget', valid=self.valid, reason=self.reason,
                declaration=asdict(self.declaration), started_at=self.started, expires_at=self.expires_at,
                reserved_pulses=self._pulses, reserved_maximum_hold=self._hold,
                reserved_displacement_hypothesis=self._distance, input_authorized=False,
                parent_budget=None if self.parent_budget is None else self.parent_budget.snapshot(),
                permits_section_handoff=False, real_client_accepted=False)


def itinerary_root(budget):
    """Expose a root for policy stage/zone/deadline checks, never double charging.

    Child reservations already charge their parent. Canonical guide hashes in
    a child differ from the root's staged-file hash; existing owner assets keep
    that correspondence. This helper grants no handoff or input permission.
    """
    from .zone_itinerary_budget import ZoneItineraryBudget
    if budget is None or type(budget) is ZoneItineraryBudget:
        return budget
    if type(budget) is not JourneyInputBudget:
        raise ValueError('Exact journey child or itinerary root required')
    parent = budget.parent_budget
    if (parent is not budget._context[-1]
            or parent is not None and type(parent) is not ZoneItineraryBudget):
        raise ValueError('Journey parent identity changed')
    return parent
