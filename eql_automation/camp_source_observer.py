"""Fresh source observations for an explicitly adopted reached-camp route.

The actual route start supplies a new height correspondence. The original camp
scope, lease and deadline remain required; this is not a replacement travel
plan or an extension of the earlier observation's lifetime. No input is sent.
"""
from collections import deque
from dataclasses import asdict
from datetime import datetime
import json
import threading

from .camp_probe_floor import CampProbeFloorReference,assert_camp_ancestry
from .camp_probe_preparation import _height_state
from .camp_route_preparation import CampRoutePreparation, CampRouteStart
from .camp_source_height import CampSourceHeight
from .flat_record import flat_record_state
from .ground_binding import finite, point
from .location_log import RawLocationFix
from .native_region_policy import encoded
from .observed_height import height_snapshot
from .route_floor_commit import _chain_snapshot
from .route_geometry import RouteMotionBounds
from .source_observer import SourceItineraryObserver


class CampSourceObserver(SourceItineraryObserver):
    """Reuse source-fix issuance while retaining a distinct camp provenance type.

    ``scope_check`` must reject cancellation/deadline/owner-context changes in
    the original scope. A new startup pair after construction is mandatory;
    the measured route-start pair cannot be replayed as movement observations.
    """
    def __init__(self, preparation, start, *, scope_check, mode_reader,
                 generation_reader, generation, expires_at, walk_half_width, stop_lock, route_bounds):
        if (type(preparation) is not CampRoutePreparation or type(start) is not CampRouteStart
                or not all(callable(f) for f in (scope_check, mode_reader, generation_reader))
                or type(generation) is not int or generation < 0
                or not finite(expires_at) or not finite(walk_half_width) or not .05 <= walk_half_width <= 6.
                or type(route_bounds) is not RouteMotionBounds
                or not isinstance(stop_lock, type(threading.RLock()))):
            raise ValueError('Exact fresh camp route and explicit bounded observer scope required')
        route_bounds.validate_values(calibration_record_id=preparation.bounds.calibration_record_id,
                                     maximum_step_seconds=.2)
        original, onward = asdict(preparation.bounds), asdict(route_bounds)
        # Turning probes can use .15s holds; ordinary route control caps requests
        # at .1s. A caller can tighten that request without inventing new motion,
        # body, timing or positional bounds. The actual-hold envelope is unchanged.
        if (not route_bounds.minimum_requested_hold <= route_bounds.maximum_requested_hold
                <= min(.1, preparation.bounds.maximum_requested_hold)
                or any(onward[k] != v for k,v in original.items()
                       if k not in ('record_id', 'maximum_requested_hold'))):
            raise ValueError('Explicit route bounds may only tighten the requested hold')
        if (type(preparation.checkpoint) is CampProbeFloorReference
                and preparation.checkpoint._transaction.lock is not stop_lock):
            raise ValueError('Camp source observer must retain the original stop lock')
        self.preparation, self.start, self.lock = preparation, start, stop_lock
        self.scope_check, self.mode_reader = scope_check, mode_reader
        self.generation_reader, self.generation = generation_reader, generation
        self.reader, self.clock = preparation.reader, preparation.clock
        self.owner = preparation.owner_binding
        self.itinerary = preparation.itinerary
        self.policy = preparation.checkpoint._policy
        self._width = walk_half_width
        self._width_state, self._generation = walk_half_width, generation
        self._route_bounds, self._route_bounds_bytes = route_bounds, flat_record_state(route_bounds)
        self.cancelled, self.reason = False, ''
        self._chain = None
        with stop_lock:
            try:
                scope_check()
                preparation.check_start(start)
                h = start.height
                if not h.observed_at <= preparation.clock() <= expires_at <= h.observed_at+300.:
                    raise ValueError('Camp source correspondence needs a current bounded deadline')
                measured = json.loads(h.payload)
                self.calibration = CampSourceHeight(h.first, h.second, self.owner, h.sha256,
                    preparation.sha256, self.itinerary.sha256, self.policy.archive_sha256,
                    self.policy.wld_sha256, h.raw_z_minus_source_z, measured['residual_limit'],
                    h.second.log_line_seq, h.observed_at, expires_at, h.expires_at)
                self._height_bytes = encoded(self.calibration.record())
                self._height_state = height_snapshot(self.calibration)
                self._height_identity = self._height_bytes
                self._identity = self._reader_identity()
                self._payload = self.itinerary.payload
                self.start_xy = h.package_xyz[:2]
                self._start_xy = self.start_xy
                self._start_bytes = (flat_record_state(h.first), flat_record_state(h.second))
                self._start_state = (id(h), _height_state(h), start.preparation_sha256,
                                     start.itinerary_sha256, start.observed_at, start.expires_at,
                                     start.input_authorized, start.real_client_accepted)
                self._classifier = self.policy.classifier
                self._policy_bytes = encoded(self.policy.record())
                self._objects = (preparation, start, stop_lock, scope_check, mode_reader,
                    generation_reader, self.reader, self.clock, self.owner, self.itinerary,
                    self.policy, self.calibration, route_bounds)
                self._chain = preparation.consume_start(start)
                self._chain_state = _chain_snapshot(self._chain)
                self._seed = (self._chain.inventory_sha256, self._chain.seed_evidence_sha256,
                              self._chain.seed_ids, self._chain.body_height)
                data = self.itinerary.record()
                if (tuple(data['start']) != self.start_xy
                        or data['initial_proof_sha256'] != self._chain.previous.proof_sha256
                        or data['initial_seed_sha256'] != self._chain.seed_evidence_sha256
                        or data['initial_chain_index'] != self._chain.index):
                    raise ValueError('Camp itinerary differs from its reached prefix')
                self._issued = deque(maxlen=2)
                self.last_seq = self.calibration.last_calibration_log_line_seq
                self.last_at = self.clock()
                self.check()
                # Adoption itself still consumes the original half-second start.
                if (self.last_at > start.expires_at or self.reader.latest is not h.second
                        or self.reader.log_line_seq != h.second.log_line_seq):
                    raise ValueError('Camp route start expired during observer adoption')
            except Exception as error:
                self.cancel(error)
                preparation.cancel(error)
                raise

    def _reader_identity(self):
        r = self.reader
        return (r.tail.identity, r.tail.epoch, r.zone_generation, r.zone_id,
                r.zone_display_name, r.expected_character, r.expected_server)

    @property
    def initial_floor_chain(self):return self._chain

    @property
    def planning_bounds(self):return self._route_bounds

    @property
    def terrain(self):return self.preparation.checkpoint._terrain

    @property
    def walk_half_width(self):return self._width

    @property
    def initial_plan_sha256(self):return self.preparation.sha256

    def cancel(self, reason):
        self.cancelled, self.reason = True, str(reason)
        if hasattr(self, '_issued'):self._issued.clear()

    def check(self):
        try:
            if self.cancelled:raise ValueError(self.reason)
            self.scope_check()
            self.preparation.check()
            self.policy.check_classifier()
            self.scope_check()
            mode, generation = self.mode_reader(), self.generation_reader()
            now = self.clock()
            assert_camp_ancestry(self.preparation.checkpoint)
            h, c = self.start.height, self.calibration
            if (self.cancelled or any(a is not b for a,b in zip(self._objects,
                    (self.preparation, self.start, self.lock, self.scope_check, self.mode_reader,
                     self.generation_reader, self.reader, self.clock, self.owner, self.itinerary,
                     self.policy, c, self._route_bounds)))
                    or self.preparation.phase != 'observing' or self.preparation.start is not self.start
                    or self.preparation.reader is not self.reader
                    or self.preparation.itinerary is not self.itinerary or self.itinerary.payload is not self._payload
                    or self.preparation.checkpoint._policy is not self.policy
                    or self.policy.classifier is not self._classifier or encoded(self.policy.record()) != self._policy_bytes
                    or self._height_bytes is not self._height_identity
                    or height_snapshot(c) != self._height_state
                    or h.sha256 != c.measured_height_sha256 or h.first is not c.first or h.second is not c.second
                    or (flat_record_state(h.first), flat_record_state(h.second)) != self._start_bytes
                    or (id(h), _height_state(h), self.start.preparation_sha256,
                        self.start.itinerary_sha256, self.start.observed_at, self.start.expires_at,
                        self.start.input_authorized, self.start.real_client_accepted) != self._start_state
                    or self.start_xy != self._start_xy or _chain_snapshot(self._chain) != self._chain_state
                    or self._width != self._width_state or self.generation != self._generation
                    or flat_record_state(self._route_bounds) != self._route_bounds_bytes
                    or mode != 'camp_route' or type(generation) is not int or generation != self.generation
                    or self.reader.tail.partial or self._reader_identity() != self._identity
                    or not finite(now) or not c.valid_from_monotonic <= self.last_at <= now <= c.valid_until_monotonic):
                raise ValueError('Camp source observer scope, measured height or reached floor changed')
            self.last_at = now
            return now
        except Exception as error:
            self.cancel(error)
            raise ValueError(self.reason) from error

    def validate_raw(self, raw, observed_at):
        c = self.calibration
        anchor = c.second
        if (type(raw) is not RawLocationFix or not point(raw.raw_coordinates)
                or type(raw.log_line_seq) is not int or raw.log_line_seq <= c.last_calibration_log_line_seq
                or not finite(raw.received_monotonic) or raw.coordinates_aligned_to_wld is not False
                or not isinstance(raw.log_local_time, datetime) or raw.log_local_time.tzinfo is not None
                or (raw.zone_id, raw.zone_display_name, raw.log_epoch, raw.zone_generation) !=
                   (anchor.zone_id, anchor.zone_display_name, anchor.log_epoch, anchor.zone_generation)
                or abs((raw.log_local_time-anchor.log_local_time).total_seconds()
                       -(raw.received_monotonic-anchor.received_monotonic)) > 2.
                or not c.valid_from_monotonic <= raw.received_monotonic <= observed_at):
            raise ValueError('Camp source reply has foreign provenance')
