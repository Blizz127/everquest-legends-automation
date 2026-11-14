"""Fresh source-floor observations without a manufactured mesh projection."""
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime

from .current_source_itinerary import CurrentSourceItinerary
from .ground_binding import SourceFloorObservation, finite, point
from .location_log import LocationLogReader, RawLocationFix
from .observed_height import ObservedHeightCalibration, current_height_allowed, _bound_initial_floor
from .route_floor_commit import _chain_snapshot
from .native_region_policy import encoded


@dataclass(frozen=True)
class SourceStoppedFix:
    raw_fix: RawLocationFix
    source_floor: SourceFloorObservation
    package_xyz: tuple
    floor_proof_sha256: str
    initial_plan_sha256: str
    itinerary_sha256: str
    height_calibration: ObservedHeightCalibration
    observed_at: float
    input_authorized: bool = field(default=False, init=False)
    real_client_accepted: bool = field(default=False, init=False)


class SourceItineraryObserver:
    """Consume each new reply once; the ledger selects the checked floor branch.

    A supplied branch is never reseeded or snapped to a closer height. Records
    remain bound to the original initial-plan height calibration and to the
    separate itinerary hash. The two latest issued records are retained for
    stopped-pair validation; copied dataclasses cannot impersonate a reading.
    """
    def __init__(self, plan, reader, *, height_calibration, binding_reader,
                 mode_reader, generation_reader, generation, clock):
        if (type(plan) is not CurrentSourceItinerary or type(reader) is not LocationLogReader
                or type(height_calibration) is not ObservedHeightCalibration
                or not all(callable(f) for f in (binding_reader, mode_reader, generation_reader, clock))
                or type(generation) is not int or generation < 0):
            raise ValueError('Current source plan, reader and observed height required')
        self.plan, self.reader, self.calibration = plan, reader, height_calibration
        self.binding_reader, self.mode_reader = binding_reader, mode_reader
        self.generation_reader, self.generation, self.clock = generation_reader, generation, clock
        self.owner = height_calibration.evidence.owner_binding
        self.initial, self.itinerary = plan.initial, plan.itinerary
        self._payload = self.itinerary.payload
        data = self.itinerary.record()
        self.start_xy=tuple(data['start'])
        self._start_xy=self.start_xy
        initial = self.initial
        self.policy = initial.region_policy
        if self.policy is None:
            raise ValueError('Source observations require the explicit native region model')
        self._classifier = self.policy.classifier
        self._policy_record = encoded(self.policy.record())
        self._chain, self._check_initial = _bound_initial_floor(initial, initial.observer,
            initial.route, reader, self.owner, 0, height_calibration.evidence.first.raw_fix)
        self._seed = (self._chain.inventory_sha256, self._chain.seed_evidence_sha256,
                      self._chain.seed_ids, self._chain.body_height)
        if (data['format'] != 'eql-source-itinerary-v1' or data['zone'] != 'crushbone'
                or data['initial_proof_sha256'] != self._chain.previous.proof_sha256
                or data['initial_seed_sha256'] != self._chain.seed_evidence_sha256
                or data['initial_chain_index'] != self._chain.index
                or data['source_wld_sha256'] != self.policy.wld_sha256
                or data['static_inventory_sha256'] != self.policy.static_inventory_sha256
                or encoded(data['region_policy']) != self._policy_record
                or data['body_height'] != self._chain.body_height
                or data['radius'] != initial.planning_bounds.body_radius
                or data['requires_fresh_start_pair'] is not True
                or data['input_authorized'] is not False or data['real_client_accepted'] is not False):
            raise ValueError('Source itinerary does not extend this exact current plan')
        self._identity = (reader.tail.identity, reader.tail.epoch, reader.zone_generation,
                          reader.zone_id, reader.zone_display_name)
        if self._identity[0] != height_calibration.evidence.log_identity:
            raise ValueError('Height and source itinerary log identity differ')
        self._objects = (plan, reader, height_calibration, binding_reader, mode_reader,
                         generation_reader, clock, self.owner)
        self._check_initial()
        self._initial_state = self._initial_snapshot()
        self._issued = deque(maxlen=2)
        self.last_seq = height_calibration.last_calibration_log_line_seq
        self.last_at = self.clock()
        self.check()

    def _initial_snapshot(self):
        p=self.initial;o=p.observer;n=p.native_region_evidence
        return (id(p.route),p.route,id(o),id(o.source),id(o.mesh),id(o.ground),id(o.geometry),
            p.plan_bytes,p.evidence_bytes,id(p.planning_bounds),p.planning_bounds,
            id(p.precision_policy),id(p.region_policy),id(n),n.payload,n.sha256,
            _chain_snapshot(p.floor_chain))

    @staticmethod
    def _observation_snapshot(observation):
        r=observation.raw_fix;s=observation.source_floor
        return (id(r),tuple(vars(r).items()),id(s),tuple(vars(s).items()),
                observation.package_xyz,observation.floor_proof_sha256,
                observation.initial_plan_sha256,observation.itinerary_sha256,
                id(observation.height_calibration),observation.observed_at,
                observation.input_authorized,observation.real_client_accepted)

    def check(self):
        self.binding_reader()
        # Initial semantics were verified once; immutable evidence and the
        # exact object/value snapshot are sufficient for repeated pulse checks.
        if self._initial_snapshot()!=self._initial_state:
            raise ValueError('Source observation initial plan changed')
        self.policy.check_classifier()
        now = self.clock()
        # The clock/provider callbacks can deliver an owner stop. Read scope
        # after the final clock call, before publishing any accepted state.
        actual = self.binding_reader()
        mode, generation = self.mode_reader(), self.generation_reader()
        c = self.calibration
        if (any(a is not b for a,b in zip(self._objects,
                (self.plan, self.reader, c, self.binding_reader, self.mode_reader,
                 self.generation_reader, self.clock, self.owner)))
                or self.plan.initial is not self.initial or self.plan.itinerary is not self.itinerary
                or self.itinerary.payload is not self._payload
                or self.start_xy!=self._start_xy
                or self.initial.region_policy is not self.policy
                or self.policy.classifier is not self._classifier
                or encoded(self.policy.record()) != self._policy_record
                or actual != self.owner or mode != 'measurement' or generation != self.generation
                or type(generation) is not int
                or not finite(now) or not finite(self.last_at) or now < self.last_at
                or not current_height_allowed(c,mode=mode,route_sha256=self.initial.route.artifact_sha256,
                                               owner_binding=self.owner)
                or not 0 <= c.valid_from_monotonic <= now <= c.valid_until_monotonic
                or c.raw_xy_to_wld_transform != 'identity'
                or c.zone_short_name != 'crushbone' or c.zone_id != 58
                or c.source_archive_sha256 != self.policy.archive_sha256
                or c.source_wld_sha256 != self.policy.wld_sha256
                or self.reader.tail.partial
                or self._identity != (self.reader.tail.identity, self.reader.tail.epoch,
                    self.reader.zone_generation, self.reader.zone_id, self.reader.zone_display_name)):
            raise ValueError('Source observation owner, height, mode or log binding changed')
        self.last_at = now
        return now

    def _sample(self, raw, chain, observed_at):
        c = self.calibration
        if (type(raw) is not RawLocationFix or not point(raw.raw_coordinates)
                or type(raw.log_line_seq) is not int or raw.log_line_seq <= c.last_calibration_log_line_seq
                or not finite(raw.received_monotonic)
                or raw.coordinates_aligned_to_wld is not False
                or not isinstance(raw.log_local_time,datetime) or raw.log_local_time.tzinfo is not None
                or abs((raw.log_local_time-c.evidence.observed_local_time).total_seconds()
                    -(raw.received_monotonic-c.valid_from_monotonic))>2.
                or (raw.zone_id,raw.zone_display_name,raw.log_epoch,raw.zone_generation) !=
                   (c.zone_id,c.zone_display_name,c.log_epoch,c.zone_generation)
                or not c.valid_from_monotonic <= raw.received_monotonic <= observed_at
                or (chain.inventory_sha256,chain.seed_evidence_sha256,chain.seed_ids,chain.body_height)
                    != self._seed):
            raise ValueError('Source reply or selected floor has foreign provenance')
        state = _chain_snapshot(chain)
        xy = (raw.raw_coordinates[1],raw.raw_coordinates[0])
        z, ids = chain.floor_at(xy)
        if (abs(raw.raw_coordinates[2]-z-c.raw_z_minus_source_z) > c.residual_limit
                or _chain_snapshot(chain) != state):
            raise ValueError('Raw height differs from the selected source floor')
        source = SourceFloorObservation(raw,(*raw.raw_coordinates[:2],z),
            c.source_archive_sha256,c.source_wld_sha256,ids,1,True)
        return SourceStoppedFix(raw,source,(*xy,z),chain.previous.proof_sha256,
            self.initial.route.artifact_sha256,self.itinerary.sha256,c,observed_at),state

    def observe(self, raw, *, checked_chain):
        now = self.check()
        if (self.reader.latest is not raw or self.reader.log_line_seq != raw.log_line_seq
                or raw.log_line_seq <= self.last_seq
                or not 0 <= now-raw.received_monotonic <= .5):
            raise ValueError('Need one fresh, latest, unreplayed source reply')
        result, state = self._sample(raw,checked_chain,now)
        finished = self.check()
        if (self.reader.latest is not raw or self.reader.log_line_seq != raw.log_line_seq
                or _chain_snapshot(checked_chain) != state
                or not 0 <= finished-raw.received_monotonic <= .5):
            raise ValueError('Source reply changed or expired during observation')
        self.last_seq = raw.log_line_seq
        self._issued.append((result,checked_chain,state,self._observation_snapshot(result)))
        return result

    def validate(self, observation, chain, *, maximum_age=2.5):
        now = self.check()
        issued = next((v for v in self._issued if v[0] is observation), None)
        if (issued is None or issued[1] is not chain or _chain_snapshot(chain) != issued[2]
                or not finite(maximum_age) or not 0 < maximum_age <= 2.5
                or not 0 <= now-observation.raw_fix.received_monotonic <= maximum_age):
            raise ValueError('Missing current issued source observation/floor')
        if self._observation_snapshot(observation)!=issued[3]:
            raise ValueError('Issued source observation changed')
        finished=self.check()
        if (not 0 <= finished-observation.raw_fix.received_monotonic <= maximum_age
                or _chain_snapshot(chain) != issued[2]):
            raise ValueError('Source observation expired during validation')
        return finished

    def rebind_cap(self, observation, old_chain, cap):
        """Same reply on a newly checked endpoint cap; never renew its timestamp."""
        self.validate(observation,old_chain,maximum_age=.5)
        updated,state = self._sample(observation.raw_fix,cap,observation.observed_at)
        if updated.package_xyz != observation.package_xyz:
            raise ValueError('Endpoint cap selected a different observed floor')
        finished=self.check()
        if not 0 <= finished-observation.raw_fix.received_monotonic <= .5:
            raise ValueError('Endpoint cap observation expired')
        for index,entry in enumerate(self._issued):
            if entry[0] is observation:
                self._issued[index]=(updated,cap,state,self._observation_snapshot(updated))
                return updated
        raise ValueError('Endpoint cap lost its original reply')
