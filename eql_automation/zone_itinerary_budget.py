"""Fixed accounting across adjacent source crossings and fresh destination probes.

This root is additional to each child's geometry, observation and input policy.
Its stage changes record caller-proven handoffs; they neither prove arrival nor
authorize movement. No saved record resumes a trip, and no handoff resets its
deadline or refunds a reservation.
"""
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import threading

from .flat_record import flat_record_state, _value
from .ground_binding import digest, finite
from .journey_input_budget import _ticket_state as _ordinary_ticket_state
from .motion_collection import immutable_binding
from .native_region_policy import encoded
from .route_geometry import RouteMotionBounds
from .source_destinations import destination_spec
from .source_zones import source_zone_id


@dataclass(frozen=True)
class ZoneItineraryLeg:
    destination_id: str
    source_zone: str
    source_zone_id: int
    source_name: str
    destination_zone: str
    destination_zone_id: int
    destination_name: str
    guide_sha256: str
    corridor_sha256: str
    expected_zone_line_sha256: str
    catalog_sha256: str

    def validate(self):
        spec = destination_spec(self.destination_id)
        if (spec.arrival_mode != 'zone_crossing'
                or (self.source_zone, self.source_zone_id, self.guide_sha256)
                    != (spec.zone, spec.zone_id, spec.file_sha256)
                or type(self.source_zone_id) is not int
                or type(self.destination_zone_id) is not int
                or source_zone_id(self.destination_zone) != self.destination_zone_id
                or self.source_zone_id == self.destination_zone_id
                or any(type(value) is not str or not value for value in
                       (self.source_name, self.destination_name))
                or not all(digest(value) for value in
                           (self.guide_sha256, self.corridor_sha256,
                            self.expected_zone_line_sha256, self.catalog_sha256))):
            raise ValueError('Pinned crossing guide, distinct catalog zones and source identities required')


def load_zone_itinerary(identifiers, *, zone_catalog, crossing_provider=None):
    """Resolve copied spec/catalog adjacency without inspecting a live prefix.

The default provider verifies the privately staged crossing file's hash. A
caller can supply another pinned provider for an isolated fixture. Catalog
identities say nothing about the actual server destination or spawn location.
"""
    from .owner_source_crossing import PinnedSourceCrossingSpec, load_source_crossing_spec
    from .zone_line import ExpectedZoneLine

    if (type(identifiers) is not tuple or not 1 <= len(identifiers) <= 8
            or any(type(value) is not str or not value for value in identifiers)
            or len(set(identifiers)) != len(identifiers)
            or not isinstance(zone_catalog, Mapping)):
        raise ValueError('Bounded ordered unique destination IDs and copied zone catalog required')
    catalog = dict(zone_catalog)
    if (not catalog or any(type(name) is not str or not name or type(zone_id) is not int
                           or zone_id <= 0 for name, zone_id in catalog.items())):
        raise ValueError('Exact display-name to integer zone catalog required')
    provider = load_source_crossing_spec if crossing_provider is None else crossing_provider
    if not callable(provider):
        raise ValueError('Pinned crossing provider required')
    catalog_pin = sha256(encoded(catalog)).hexdigest()
    legs = []
    for identifier in identifiers:
        guide = destination_spec(identifier)
        crossing = provider(identifier)
        if (guide.arrival_mode != 'zone_crossing'
                or type(crossing) is not PinnedSourceCrossingSpec
                or crossing.destination_id != identifier or crossing.zone != guide.zone
                or crossing.start_xy != guide.goal
                or crossing.provenance_sha256 != guide.provenance_sha256
                or type(crossing.expected_zone_line) is not ExpectedZoneLine
                or crossing.expected_zone_line.zone != guide.zone
                or catalog.get(crossing.destination) != crossing.destination_zone_id):
            raise ValueError('Crossing provider differs from its registered guide or copied catalog')
        source_names = [name for name, zone_id in catalog.items() if zone_id == guide.zone_id]
        destination_names = [name for name, zone_id in catalog.items()
                             if zone_id == crossing.destination_zone_id]
        if len(source_names) != 1 or destination_names != [crossing.destination]:
            raise ValueError('Source and destination need unique copied catalog names')
        leg = ZoneItineraryLeg(identifier, guide.zone, guide.zone_id, source_names[0],
            crossing.destination_zone, crossing.destination_zone_id, crossing.destination,
            guide.file_sha256, crossing.corridor_file_sha256,
            crossing.expected_zone_line.sha256, catalog_pin)
        leg.validate()
        if legs and (legs[-1].destination_zone, legs[-1].destination_zone_id,
                     legs[-1].destination_name) != (leg.source_zone, leg.source_zone_id, leg.source_name):
            raise ValueError('Ordered crossing legs are not adjacent in the copied catalog')
        legs.append(leg)
    return tuple(legs)


@dataclass(frozen=True)
class ZoneItineraryDeclaration:
    record_id: str
    legs: tuple
    maximum_seconds: float
    maximum_pulses: int
    maximum_total_hold: float
    maximum_displacement_reserve: float

    def validate(self):
        if (type(self.record_id) is not str or not 1 <= len(self.record_id) <= 128
                or type(self.legs) is not tuple or not 1 <= len(self.legs) <= 8
                or any(type(leg) is not ZoneItineraryLeg for leg in self.legs)
                or len({leg.destination_id for leg in self.legs}) != len(self.legs)
                or type(self.maximum_pulses) is not int or self.maximum_pulses <= 0
                or not all(finite(value) and value > 0 for value in
                           (self.maximum_seconds, self.maximum_total_hold,
                            self.maximum_displacement_reserve))
                or self.maximum_total_hold > self.maximum_seconds):
            raise ValueError('Explicit finite itinerary duration and input limits required')
        for leg in self.legs:
            leg.validate()
            if leg.catalog_sha256 != self.legs[0].catalog_sha256:
                raise ValueError('Itinerary legs must share the same copied zone catalog')
        for previous, current in zip(self.legs, self.legs[1:]):
            if (previous.destination_zone, previous.destination_zone_id, previous.destination_name) != (
                    current.source_zone, current.source_zone_id, current.source_name):
                raise ValueError('Ordered crossing legs are not adjacent in the copied catalog')


@dataclass(frozen=True)
class ZoneItineraryStage:
    leg_index: int
    destination_id: str
    phase: str
    epoch: int
    started_at: float


@dataclass(frozen=True)
class ZoneItineraryReservation:
    ticket: object
    stage: ZoneItineraryStage
    serial: int
    maximum_hold: float
    maximum_displacement: float
    input_authorized: bool = field(default=False, init=False)


def _ticket_state(ticket):
    from .camp_probe_transaction import CampProbeTicket
    from .source_crossing_corridor import SourceCrossingGeometry, SourceCrossingTicket
    from .source_motion import SourceMotionGeometry, SourceMotionTicket

    if type(ticket) is SourceMotionTicket:
        if type(ticket.geometry) is not SourceMotionGeometry:
            raise ValueError('Exact ordinary source movement geometry required')
        return 'walking', (_ordinary_ticket_state(ticket), flat_record_state(ticket.geometry))
    if type(ticket) is CampProbeTicket:
        return 'probe', _ordinary_ticket_state(ticket)
    if type(ticket) is SourceCrossingTicket:
        if type(ticket.geometry) is not SourceCrossingGeometry or type(ticket.touches_line) is not bool:
            raise ValueError('Exact source crossing geometry and transition flag required')
        return 'crossing', (type(ticket), id(ticket), id(ticket.reference),
            flat_record_state(ticket.geometry), ticket.serial, ticket.proposed_at,
            ticket.requested_seconds, ticket.maximum_actual_hold, ticket.movement_key,
            ticket.touches_line, ticket.input_authorized)
    raise ValueError('Exact ordinary, crossing or fresh probe ticket required')


def _declaration_state(declaration):
    return (id(declaration), declaration.record_id, type(declaration.legs), id(declaration.legs),
            tuple(flat_record_state(leg) for leg in declaration.legs),
            declaration.maximum_seconds, declaration.maximum_pulses,
            declaration.maximum_total_hold, declaration.maximum_displacement_reserve)


class ZoneItineraryBudget:
    """One sticky root budget alongside unchanged per-child input policies.

    Owner binding must retain generation, settings, process and sender identity,
    but not the zone/lease fields that legitimately change at a checked handoff.
    ``advance`` consumes the exact stage once; the caller still proves its
    arrival, floor, measurement and release conditions independently.
    """
    def __init__(self, declaration, *, clock, stop_lock, owner_binding, binding_reader):
        if (type(declaration) is not ZoneItineraryDeclaration
                or not all(callable(value) for value in (clock, binding_reader))
                or not immutable_binding(owner_binding)
                or not isinstance(stop_lock, type(threading.RLock()))):
            raise ValueError('Exact itinerary declaration, stable owner binding and shared stop lock required')
        declaration.validate()
        self.declaration, self.clock, self.lock = declaration, clock, stop_lock
        self.owner_binding, self.binding_reader = owner_binding, binding_reader
        self._context = (declaration, clock, stop_lock, owner_binding, binding_reader)
        self._binding = _value(owner_binding)
        self._declaration = _declaration_state(declaration)
        self.started = self.last_at = clock()
        self.expires_at = self.started + declaration.maximum_seconds
        if not finite(self.started) or not finite(self.expires_at):
            raise ValueError('Finite absolute itinerary start and deadline required')
        self._times = (self.started, self.expires_at)
        self.stage = ZoneItineraryStage(0, declaration.legs[0].destination_id, 'walking', 0, self.started)
        self._stage_state = flat_record_state(self.stage)
        self.valid, self.reason = True, ''
        self._reservations = {}
        self._reservation_store = self._reservations
        self._pulses = 0
        self._hold = self._distance = 0.
        self._balance = (self._pulses, self._hold, self._distance)
        self._checking = self._mutating = False
        self.check()

    @property
    def leg(self):
        return self.declaration.legs[self.stage.leg_index]

    def cancel(self, reason):
        with self.lock:
            if self.valid:
                self.reason = str(reason)
            self.valid = False

    def _assert_intact(self):
        if (not self.valid or any(a is not b for a, b in zip(self._context,
                (self.declaration, self.clock, self.lock, self.owner_binding, self.binding_reader)))
                or _declaration_state(self.declaration) != self._declaration
                or _value(self.owner_binding) != self._binding
                or (self.started, self.expires_at) != self._times
                or flat_record_state(self.stage) != self._stage_state
                or self._reservations is not self._reservation_store
                or (self._pulses, self._hold, self._distance) != self._balance
                or len(self._reservations) != self._pulses):
            raise ValueError(self.reason or 'Root itinerary owner, stage, declaration or accounting changed')

    def check(self, reservation=None):
        with self.lock:
            try:
                if self._checking:
                    raise ValueError('Root itinerary check reentered')
                self._checking = True
                self._assert_intact()
                stage = self.stage
                before = self.binding_reader()
                now = self.clock()
                after = self.binding_reader()
                self._assert_intact()
                if (stage is not self.stage or _value(before) != self._binding
                        or _value(after) != self._binding or not finite(now)
                        or not self.started <= self.last_at <= now <= self.expires_at):
                    raise ValueError('Root itinerary owner or fixed deadline changed')
                if reservation is not None:
                    if type(reservation) is not ZoneItineraryReservation:
                        raise ValueError('Exact root itinerary reservation required')
                    row = self._reservations.get(id(reservation.ticket))
                    if (row is None or reservation is not row[0]
                            or reservation.stage is not self.stage
                            or (id(reservation.ticket), id(reservation.stage), reservation.serial,
                                reservation.maximum_hold, reservation.maximum_displacement,
                                reservation.input_authorized) != row[1]
                            or _ticket_state(reservation.ticket) != row[2]
                            or flat_record_state(row[3]) != row[4]):
                        raise ValueError('Root reservation is changed, copied or belongs to a retired stage')
                self.last_at = now
                return now
            except Exception as error:
                self.cancel(error)
                raise ValueError(self.reason) from error
            finally:
                self._checking = False

    def _begin_mutation(self):
        if self._mutating or self._checking:
            self.cancel('Root itinerary mutation reentered')
            raise ValueError(self.reason)
        self._mutating = True

    def reserve(self, ticket, *, bounds):
        """Charge before DOWN; child scene/geometry/receipt checks remain mandatory."""
        with self.lock:
            self._begin_mutation()
            try:
                now = self.check()
                state = _ticket_state(ticket)
                allowed = {'walking': ('walking', 'probe'), 'crossing': ('crossing',),
                           'bootstrap': ('probe',)}.get(self.stage.phase, ())
                if state[0] not in allowed:
                    raise ValueError('Ticket type is not allowed in the current itinerary stage')
                if type(bounds) is not RouteMotionBounds:
                    raise ValueError('Explicit unchanged movement bounds required')
                bounds.validate_values(calibration_record_id=bounds.calibration_record_id,
                                       maximum_step_seconds=.2)
                kind = {103: 'forward', 105: 'left', 106: 'right'}.get(ticket.movement_key)
                declared = getattr(ticket, 'kind', None)
                if declared is None:
                    declared = ticket.geometry.kind
                if (kind is None or kind != declared or ticket.input_authorized is not False
                        or not finite(ticket.proposed_at) or not self.stage.started_at <= ticket.proposed_at <= now
                        or not finite(ticket.maximum_actual_hold)
                        or ticket.maximum_actual_hold != bounds.maximum_actual_hold
                        or now + ticket.maximum_actual_hold > self.expires_at
                        or not finite(ticket.requested_seconds)
                        or not bounds.minimum_requested_hold <= ticket.requested_seconds <= bounds.maximum_requested_hold
                        or id(ticket) in self._reservations):
                    raise ValueError('Root ticket is duplicate, future-dated or outside its movement bounds/deadline')
                hold = ticket.maximum_actual_hold
                displacement = (bounds.forward_speed_upper_bound * hold if kind == 'forward'
                                else bounds.pivot_displacement_upper_bound) + bounds.post_release_drift
                d = self.declaration
                if (self._pulses + 1 > d.maximum_pulses or self._hold + hold > d.maximum_total_hold
                        or self._distance + displacement > d.maximum_displacement_reserve):
                    raise ValueError('Root itinerary input reservation budget exhausted')
                self._assert_intact()
                result = ZoneItineraryReservation(ticket, self.stage, self._pulses + 1, hold, displacement)
                self._reservations[id(ticket)] = (result,
                    (id(ticket), id(self.stage), result.serial, hold, displacement, False),
                    state, bounds, flat_record_state(bounds))
                self._pulses += 1
                self._hold += hold
                self._distance += displacement
                self._balance = (self._pulses, self._hold, self._distance)
                return result
            except Exception as error:
                self.cancel(error)
                raise ValueError(self.reason) from error
            finally:
                self._mutating = False

    def advance(self, stage, next_phase, *, zone_id):
        """Record one ordered, externally proven handoff without renewing time."""
        with self.lock:
            self._begin_mutation()
            try:
                now = self.check()
                if type(stage) is not ZoneItineraryStage or stage is not self.stage:
                    raise ValueError('Exact unconsumed itinerary stage required')
                leg = self.leg
                next_index = stage.leg_index
                transitions = {
                    'walking': ('crossing', leg.source_zone_id),
                    'crossing': ('loading', None),
                    'loading': ('arrival', leg.destination_zone_id),
                    'bootstrap': ('walking', leg.source_zone_id),
                }
                if stage.phase == 'arrival':
                    if stage.leg_index + 1 < len(self.declaration.legs):
                        next_index += 1
                        expected = ('bootstrap', self.declaration.legs[next_index].source_zone_id)
                    else:
                        expected = ('complete', leg.destination_zone_id)
                else:
                    expected = transitions.get(stage.phase)
                if (expected is None or (next_phase, zone_id) != expected
                        or zone_id is not None and type(zone_id) is not int):
                    raise ValueError('Itinerary phase or observed zone is out of order')
                self._assert_intact()
                self.stage = ZoneItineraryStage(next_index,
                    self.declaration.legs[next_index].destination_id, next_phase, stage.epoch + 1, now)
                self._stage_state = flat_record_state(self.stage)
                return self.stage
            except Exception as error:
                self.cancel(error)
                raise ValueError(self.reason) from error
            finally:
                self._mutating = False

    def cap_deadline(self, child_expires_at):
        """Clamp an already captured child deadline, not a renewable duration."""
        with self.lock:
            now = self.check()
            if not finite(child_expires_at) or child_expires_at <= now:
                self.cancel('Child absolute deadline is invalid or already expired')
                raise ValueError(self.reason)
            return min(child_expires_at, self.expires_at)

    def snapshot(self):
        with self.lock:
            return dict(kind='finite_zone_itinerary_budget', valid=self.valid, reason=self.reason,
                declaration=asdict(self.declaration), stage=asdict(self.stage),
                started_at=self.started, expires_at=self.expires_at,
                reserved_pulses=self._pulses, reserved_maximum_hold=self._hold,
                reserved_displacement_hypothesis=self._distance,
                input_authorized=False, permits_zone_handoff=False, child_limits_replaced=False,
                server_destinations_verified=False, real_client_accepted=False)
