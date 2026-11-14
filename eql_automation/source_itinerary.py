"""Rebuild mixed walking/step itineraries from a supplied source-floor prefix.

Guides propose XY and source step edges; they never seed the current floor or
commit an untraversed suffix. Every cell is rebuilt against the complete copied
terrain/static inventories. A step remains a kinematic hypothesis, even when
all its region metadata is zero. This module owns no reader or input device.
"""
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
import time

from .bsp_floor_guard import check_source_body_bsp
from .ground_binding import digest, finite
from .native_body_regions import classify_source_body_regions
from .native_region_policy import NativeZeroRegionTrialPolicy, encoded
from .native_step_regions import classify_source_step_regions
from .route_floor_commit import _chain_snapshot
from .source_detour import find_source_detour, swept_square
from .source_step import check_source_step
from .source_stair_hint import SourceStairHint
from .source_step_bsp import check_source_step_bsp
from .static_floor_guard import check_source_static_floor


def xy(value):
    return type(value) is tuple and len(value) == 2 and all(finite(v) for v in value)


def _guide_snapshot(guide):
    # Every validated field is immutable. Copy values rather than re-encoding
    # the complete thousand-cell guide at each geometry/context boundary.
    return (guide.zone, guide.wld_sha256, guide.static_inventory_sha256,
        guide.provenance_sha256, guide.radius, guide.body_height, guide.goal,
        tuple((type(op), tuple(vars(op).items())) for op in guide.operations))


class SourceItineraryGeometryError(ValueError):
    """A checked proposal failed geometry; owner/context failures are separate."""


@dataclass(frozen=True)
class SourceWalkHint:
    start: tuple
    end: tuple


@dataclass(frozen=True)
class SourceStepHint:
    start: tuple
    end: tuple
    landing_seed_ids: tuple
    max_step_height: float
    max_lift: float
    lift_clearance: float = .125


@dataclass(frozen=True)
class SourceItineraryGuide:
    zone: str
    wld_sha256: str
    static_inventory_sha256: str
    provenance_sha256: str
    radius: float
    body_height: float
    goal: tuple
    operations: tuple

    def validate(self):
        if (self.zone != 'crushbone'
                or not all(digest(p) for p in (self.wld_sha256,
                    self.static_inventory_sha256, self.provenance_sha256))
                or not finite(self.radius) or not .05 <= self.radius <= 10
                or not finite(self.body_height) or not 0 < self.body_height <= 100
                or not xy(self.goal) or type(self.operations) is not tuple
                or not 1 <= len(self.operations) <= 10000):
            raise ValueError('Bounded pinned source itinerary guide required')
        previous = None
        for op in self.operations:
            if (type(op) not in (SourceWalkHint, SourceStepHint, SourceStairHint)
                    or not xy(op.start) or not xy(op.end)
                    or math.dist(op.start, op.end) > 80
                    or previous is not None and math.dist(previous, op.start) > 1e-6):
                raise ValueError('Guide has an invalid operation or unexplained gap')
            if type(op) is SourceStepHint and (
                    not all(finite(v) for v in (op.max_step_height, op.max_lift, op.lift_clearance))
                    or not 0 < op.max_step_height <= 4
                    or not op.max_step_height <= op.max_lift <= 8
                    or not .11 < op.lift_clearance <= .5
                    or not 0 < math.dist(op.start, op.end) <= 20
                    or type(op.landing_seed_ids) is not tuple or not 1 <= len(op.landing_seed_ids) <= 128
                    or len(set(op.landing_seed_ids)) != len(op.landing_seed_ids)
                    or any(type(k) is not tuple or len(k) != 2
                        or any(type(i) is not int or i < 0 for i in k) for k in op.landing_seed_ids)):
                raise ValueError('Invalid explicit source step guide')
            if type(op) is SourceStairHint:
                op.validate()
                if op.vertical_model!='bounded_source_contacts' or op.radius<=self.radius/math.cos(math.pi/16):
                    raise ValueError('Stair guide requires explicit grounded contact clearance')
            previous = op.end
        if math.dist(previous, self.goal) > 80:
            raise ValueError('Exact destination needs a bounded final connector')

    def record(self):
        self.validate()
        value = asdict(self)
        kinds={SourceWalkHint:'walk',SourceStepHint:'step',SourceStairHint:'stair'}
        value['operations'] = [dict(kind=kinds[type(op)],
                                    **asdict(op)) for op in self.operations]
        return value

    @classmethod
    def from_record(cls, data):
        """Parse private guide data. Stored proofs/acceptance flags are not read."""
        operations = []
        for item in data['operations']:
            if item['kind'] == 'walk':
                operations.append(SourceWalkHint(tuple(item['start']), tuple(item['end'])))
            elif item['kind'] == 'step':
                operations.append(SourceStepHint(tuple(item['start']), tuple(item['end']),
                    tuple(tuple(k) for k in item['landing_seed_ids']),
                    item['max_step_height'], item['max_lift'], item['lift_clearance']))
            elif item['kind']=='stair':
                operations.append(SourceStairHint(tuple(item['start']),tuple(item['end']),
                    tuple(tuple(tuple(k) for k in group) for group in item['tread_ids']),
                    item['radius'],item['max_rise'],item['max_lift'],item['vertical_model']))
            else:
                raise ValueError('Unknown source itinerary operation')
        guide = cls(data['zone'], data['wld_sha256'], data['static_inventory_sha256'],
            data['provenance_sha256'], data['radius'], data['body_height'],
            tuple(data['goal']), tuple(operations))
        guide.validate()
        return guide


@dataclass(frozen=True)
class SourceItineraryPlan:
    payload: bytes
    sha256: str

    def record(self):
        if type(self.payload) is not bytes or sha256(self.payload).hexdigest() != self.sha256:
            raise ValueError('Source itinerary evidence changed')
        data = json.loads(self.payload)
        if encoded(data) != self.payload:
            raise ValueError('Source itinerary evidence is not canonical')
        return data


def _zero_native(native):
    if (native.complete is not True or native.possible_flags != (0,) or not native.pieces
            or any(p['classification']['complete'] is not True
                or not p['classification']['possible_classes']
                or any(type(c['flags']) is not int or c['flags'] != 0
                    for c in p['classification']['possible_classes']) for p in native.pieces)):
        raise SourceItineraryGeometryError('Source itinerary contains nonzero or unresolved native regions')


def plan_source_itinerary(prefix, start, guide, terrain, static, bsp, region_policy, *,
                          check_context, max_seconds=240., clock=time.monotonic,
                          max_connect_distance=12., max_connect_attempts=4):
    """Rejoin a checked guide from the actual supplied floor, then rebuild it.

    The caller binds a fresh source prefix and owner/log identity through
    check_context. Planning can be slow; the result requires a fresh stopped
    pair before execution. No future branch is returned as a live floor.
    Closest guide starts are merely proposals; same-XY upstairs/downstairs
    connections must still pass the continuous source-floor checks.
    """
    if (type(guide) is not SourceItineraryGuide or not xy(start)
            or type(region_policy) is not NativeZeroRegionTrialPolicy
            or not callable(check_context) or not callable(clock)
            or not finite(max_seconds) or not 0 < max_seconds <= 300
            or not finite(max_connect_distance) or not 0 <= max_connect_distance <= 80
            or type(max_connect_attempts) is not int or not 1 <= max_connect_attempts <= 16):
        raise ValueError('Explicit bounded source itinerary context required')
    guide.validate()
    original = _chain_snapshot(prefix)
    # The caller's prefix, not a guide seed or label Z, must contain start.
    start_height, start_ids = prefix.floor_at(start)
    policy_record = encoded(region_policy.record())
    policy_classifier = region_policy.classifier
    guide_record = encoded(guide.record())
    guide_state = _guide_snapshot(guide)
    began = last = clock()
    if not finite(began):
        raise ValueError('Invalid itinerary planning clock')

    def check():
        nonlocal last
        check_context()
        region_policy.check_context(zone=guide.zone,
            pins=(region_policy.mesh_sha256, terrain.archive_sha256,
                  terrain.wld_sha256, static.inventory_sha256), bsp=bsp)
        now = clock()
        if (not finite(now) or not began <= last <= now <= began + max_seconds
                or _chain_snapshot(prefix) != original
                or guide.wld_sha256 != terrain.wld_sha256
                or guide.static_inventory_sha256 != static.inventory_sha256
                or prefix.inventory_sha256 != guide.wld_sha256
                or prefix.body_height != guide.body_height
                or region_policy.classifier is not policy_classifier
                or encoded(region_policy.record()) != policy_record
                or _guide_snapshot(guide) != guide_state):
            raise ValueError('Source itinerary context changed or expired')
        last = now

    cells = []

    def walk(chain, a, b, origin):
        check()
        footprint = swept_square(a, b, guide.radius)
        sources = terrain.source_faces_for_footprint(footprint)
        branch = chain.fork()
        floor = branch.advance(footprint, sources)
        if not floor.candidate:
            raise SourceItineraryGeometryError(f'Source itinerary terrain at {origin}: ' + floor.reason)
        placed = check_source_static_floor(floor, footprint, sources, static)
        if not placed.candidate:
            raise SourceItineraryGeometryError(f'Source itinerary static at {origin}: ' + placed.reason)
        old_bsp = check_source_body_bsp(floor, footprint, sources, bsp, clip_branches=True)
        if not old_bsp.candidate and old_bsp.reason != 'missing_bsp_child':
            raise SourceItineraryGeometryError(f'Source itinerary BSP at {origin}: ' + old_bsp.reason)
        native = classify_source_body_regions(floor, footprint, sources, static,
            policy_classifier, source_wld_sha256=guide.wld_sha256)
        _zero_native(native)
        check()
        cells.append(dict(kind='walk', origin=origin, start=a, end=b, footprint=footprint,
            start_floor_height=branch.floor_at(a)[0],end_floor_height=branch.floor_at(b)[0],
            terrain=asdict(floor), static=asdict(placed), bsp=asdict(old_bsp), native=asdict(native)))
        return branch

    check()
    # Try only nearby guide entries; every candidate inherits the same current
    # prefix. Failure is not permission to seed a different component/layer.
    entries = sorted((math.dist(start, op.start), index) for index, op in enumerate(guide.operations)
                     if math.dist(start, op.start) <= max_connect_distance)
    attempts = []
    chosen = None
    seen = set()
    for distance, index in entries:
        target = guide.operations[index].start
        if target in seen:
            continue
        seen.add(target)
        if len(attempts) >= max_connect_attempts:
            break
        check()
        detour, _ = find_source_detour(prefix, start, target, terrain, static,
            radius=guide.radius, max_expansions=128,
            max_seconds=max(.001, min(10., began + max_seconds - last)))
        check()
        attempts.append(dict(index=index, distance=distance, candidate=detour.candidate,
                             reason=detour.reason))
        if not detour.candidate:
            continue
        chain = prefix.fork()
        # Rebuild detour cells; never adopt its proposed branch without region checks.
        count = len(cells)
        try:
            for cell in detour.cells:
                chain = walk(chain, cell.start, cell.end, 'current_start_connector')
        except SourceItineraryGeometryError as error:
            del cells[count:]
            attempts[-1].update(candidate=False, reason=str(error))
            check()  # A stop, changed owner or expired budget must still abort.
            continue
        chosen = index
        break
    if chosen is None:
        raise ValueError('No checked connector from current floor to this source guide')
    position = guide.operations[chosen].start
    for index, op in enumerate(guide.operations[chosen:], chosen):
        if position != op.start:
            chain = walk(chain, position, op.start, 'guide_rounding_connector')
        if type(op) is SourceWalkHint:
            chain = walk(chain, op.start, op.end, index)
        elif type(op) is SourceStairHint:
            from .source_stair_plan import plan_stair_flight
            chain=walk(chain,op.start,op.start,'stair_departure_cap')
            departure_height=chain.floor_at(op.start)[0]
            check()
            stair,landing=plan_stair_flight(chain,op.start,op.end,op.tread_ids,terrain,static,bsp,
                region_policy,radius=op.radius,body_radius=guide.radius,max_rise=op.max_rise,
                max_lift=op.max_lift,vertical_model=op.vertical_model,check_context=check)
            cells.append(dict(kind='stair',origin=index,start=op.start,end=op.end,
                start_floor_height=departure_height,end_floor_height=landing.floor_at(op.end)[0],
                hint=asdict(op),stair_plan=stair.record(),stair_plan_sha256=stair.sha256))
            chain=landing  # Only the planning suffix uses this hypothetical cap.
        else:
            # A departure cap is actual geometry, not an asserted start point.
            chain = walk(chain, op.start, op.start, 'step_departure_cap')
            departure_height=chain.floor_at(op.start)[0]
            check()
            transfer, landing = check_source_step(chain, op.start, op.end, terrain, static,
                landing_seed_ids=op.landing_seed_ids, radius=guide.radius,
                max_step_height=op.max_step_height, max_lift=op.max_lift,
                lift_clearance=op.lift_clearance)
            if not transfer.candidate:
                raise ValueError('Source itinerary step: ' + transfer.reason)
            old_bsp = check_source_step_bsp(transfer, terrain, static, bsp)
            if not old_bsp.pieces or any(not p['traversal']['candidate']
                    and p['traversal']['reason'] != 'missing_bsp_child' for p in old_bsp.pieces):
                raise ValueError('Source itinerary step BSP: ' + old_bsp.reason)
            native = classify_source_step_regions(transfer, terrain, static, policy_classifier)
            _zero_native(native)
            check()
            cells.append(dict(kind='step', origin=index, start=op.start, end=op.end,
                start_floor_height=departure_height,end_floor_height=landing.floor_at(op.end)[0],
                transfer=asdict(transfer), bsp=asdict(old_bsp), native=asdict(native)))
            chain = landing  # Planning branch only; never published as current floor.
        position = op.end
    chain = walk(chain, position, guide.goal, 'exact_destination_connector')
    chain = walk(chain, guide.goal, guide.goal, 'exact_destination_cap')
    goal_height, goal_ids = chain.floor_at(guide.goal)
    check()
    payload = encoded(dict(format='eql-source-itinerary-v1', zone=guide.zone,
        source_wld_sha256=guide.wld_sha256, static_inventory_sha256=guide.static_inventory_sha256,
        guide_sha256=sha256(guide_record).hexdigest(), guide_provenance_sha256=guide.provenance_sha256,
        region_policy=json.loads(policy_record), initial_proof_sha256=original[7].proof_sha256,
        initial_seed_sha256=prefix.seed_evidence_sha256, initial_chain_index=prefix.index,
        radius=guide.radius, body_height=guide.body_height,
        start=start, start_floor_height=start_height, start_source_ids=start_ids,
        goal=guide.goal, goal_floor_height=goal_height, goal_source_ids=goal_ids,
        connector_attempts=attempts, guide_entry=chosen, cells=cells,
        final_proof_sha256=chain.previous.proof_sha256,
        started=began, finished=last, geometry_candidate=True,
        requires_fresh_start_pair=True, future_geometry_requires_runtime_checks=True,
        conditional_kinematic_hypothesis=True, client_step_capability_verified=False,
        input_authorized=False, real_client_accepted=False, game_input_sent=False))
    check()
    return SourceItineraryPlan(payload, sha256(payload).hexdigest())
