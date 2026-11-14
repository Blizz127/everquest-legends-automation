"""Current stopped-position correspondence for supervised route startup.

The printed actor Z and copied terrain Z are measured separately. Their
difference is an observed correspondence at two decimal-coordinate centers,
not a body height, collision offset, or proof of future ground clearance.
Only measurement-mode route consumers may use this evidence. It never marks
the legacy full-auto calibration or a real route as verified.
"""
from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
import json
import math

from .ground_binding import (HeightCalibration, SourceFloorObservation,
    digest, finite, point)
from .location_log import LocationLogReader, RawLocationFix
from .motion_collection import immutable_binding


@dataclass(frozen=True)
class StoppedHeightEvidence:
    first: SourceFloorObservation
    second: SourceFloorObservation
    owner_binding: tuple
    log_identity: tuple[int, int]
    route_sha256: str
    mesh_sha256: str
    segment_index: int
    offsets: tuple[float, float]
    residuals: tuple[float, float]
    observed_at: float
    released_at: float
    observed_local_time: datetime
    evidence_kind: str = 'current_stopped_height_correspondence'
    coordinate_scope: str = 'printed_decimal_centers; source_geometry_not_live_collision'
    body_height_verified: bool = False
    real_client_accepted: bool = False
    source_floor_kind: str = 'all_layers_exact_point'
    source_floor_proof_sha256: str | None = None
    source_floor_seed_sha256: str | None = None


@dataclass(frozen=True, kw_only=True)
class ObservedHeightCalibration(HeightCalibration):
    evidence: StoppedHeightEvidence


def height_record(calibration):
    """JSON-compatible run evidence; saved records do not restore live scope."""
    from .camp_source_height import CampSourceHeight
    if type(calibration) is CampSourceHeight:
        return calibration.record()
    result = asdict(calibration)
    if isinstance(calibration,ObservedHeightCalibration):
        result['evidence']['observed_local_time']=result['evidence']['observed_local_time'].isoformat()
        for key in ('first','second'):
            raw = result['evidence'][key]['raw_fix']
            raw['log_local_time'] = raw['log_local_time'].isoformat()
    return result


def height_snapshot(calibration):
    """Value snapshot for repeated identity checks, without JSON/deep copying.

    Descend into the actual evidence and raw fixes, so mutation of a nested
    frozen dataclass is still detected. This does not establish live validity.
    """
    from .camp_source_height import CampSourceHeight
    nodes=[calibration]
    if type(calibration) is ObservedHeightCalibration:
        e=calibration.evidence
        nodes.extend((e,e.first,e.second,e.first.raw_fix,e.second.raw_fix))
    elif type(calibration) is CampSourceHeight:
        nodes.extend((calibration.first,calibration.second))
    elif type(calibration) is not HeightCalibration:
        raise ValueError('Unknown height evidence type')
    # Every nested record is included separately. Flat dictionaries keep the
    # immutable coordinates/dates/scalars; node identities and field types
    # also detect replacement or bool/int coercion, without deep copying.
    return tuple((type(node),id(node),tuple((key,type(v)) for key,v in vars(node).items()),
                  dict(vars(node))) for node in nodes)


def current_height_allowed(calibration, *, mode, route_sha256=None, owner_binding=None):
    """Recognize this narrow evidence without promoting it into full auto.

    Existing time/zone/hash/residual checks still run in the ground consumer.
    The route/session additionally supplies its plan and owner binding.
    """
    if not isinstance(calibration, ObservedHeightCalibration):
        return isinstance(calibration, HeightCalibration) and calibration.live_verified is True
    e = calibration.evidence
    if (mode != 'measurement' or calibration.live_verified is not False
            or not finite(calibration.raw_z_minus_source_z) or calibration.raw_z_minus_source_z<=0
            or not finite(calibration.residual_limit) or not 0<calibration.residual_limit<=.25
            or not isinstance(e, StoppedHeightEvidence)
            or e.evidence_kind != 'current_stopped_height_correspondence'
            or e.body_height_verified is not False or e.real_client_accepted is not False
            or not digest(e.route_sha256) or not digest(e.mesh_sha256)
            or not isinstance(e.offsets,tuple) or len(e.offsets)!=2
            or not isinstance(e.residuals,tuple) or len(e.residuals)!=2
            or not finite(e.released_at) or e.released_at<0
            or not isinstance(e.observed_local_time,datetime) or e.observed_local_time.tzinfo is not None
            or not isinstance(e.log_identity,tuple) or len(e.log_identity)!=2
            or any(type(v) is not int or v<0 for v in e.log_identity)
            or not immutable_binding(e.owner_binding)
            or (route_sha256 is not None and route_sha256 != e.route_sha256)
            or (owner_binding is not None and owner_binding != e.owner_binding)):
        return False
    if e.source_floor_kind == 'all_layers_exact_point':
        if e.source_floor_proof_sha256 is not None or e.source_floor_seed_sha256 is not None:
            return False
    elif e.source_floor_kind == 'checked_initial_plan_floor':
        if not digest(e.source_floor_proof_sha256) or not digest(e.source_floor_seed_sha256):
            return False
    else:
        return False
    a, b = e.first, e.second
    if (not isinstance(a, SourceFloorObservation) or not isinstance(b, SourceFloorObservation)
            or not isinstance(a.raw_fix, RawLocationFix) or not isinstance(b.raw_fix, RawLocationFix)
            or not finite(a.raw_fix.received_monotonic) or not finite(b.raw_fix.received_monotonic)
            or type(a.raw_fix.log_line_seq) is not int or a.raw_fix.log_line_seq<1
            or type(b.raw_fix.log_line_seq) is not int
            or calibration.last_calibration_log_line_seq != b.raw_fix.log_line_seq
            or calibration.valid_from_monotonic != e.observed_at
            or not all(finite(v) for v in (*e.offsets, *e.residuals, e.observed_at))
            or not b.raw_fix.received_monotonic <= e.observed_at <= b.raw_fix.received_monotonic+.5
            or not e.released_at+.12 <= a.raw_fix.received_monotonic
            or not .4 <= b.raw_fix.received_monotonic-a.raw_fix.received_monotonic <= 2.5
            or b.raw_fix.log_line_seq != a.raw_fix.log_line_seq+1):
        return False
    for sample, offset, residual in zip((a,b), e.offsets, e.residuals):
        raw = sample.raw_fix
        if (sample.geometry_verified is not True or sample.floor_count != 1
                or not isinstance(raw.log_local_time,datetime) or raw.log_local_time.tzinfo is not None
                or abs((e.observed_local_time-raw.log_local_time).total_seconds()
                       -(e.observed_at-raw.received_monotonic))>2
                or not isinstance(sample.source_surface_ids,tuple)
                or not 1 <= len(sample.source_surface_ids) <= 128
                or any(not isinstance(v,str) or not v for v in sample.source_surface_ids)
                or len(set(sample.source_surface_ids))!=len(sample.source_surface_ids)
                or not point(sample.ground_wld_xyz) or not point(raw.raw_coordinates)
                or sample.ground_wld_xyz[:2] != raw.raw_coordinates[:2]
                or sample.source_archive_sha256 != calibration.source_archive_sha256
                or sample.source_wld_sha256 != calibration.source_wld_sha256
                or (raw.zone_id,raw.zone_display_name,raw.log_epoch,raw.zone_generation) !=
                   (calibration.zone_id,calibration.zone_display_name,
                    calibration.log_epoch,calibration.zone_generation)
                or offset != raw.raw_coordinates[2]-sample.ground_wld_xyz[2]
                or residual != offset-calibration.raw_z_minus_source_z
                or abs(residual)>calibration.residual_limit):
            return False
    return True


def _bound_initial_floor(plan, observer, route, reader, owner_binding, segment_index, first):
    """Bind the accepted initial cell once, then recheck a small value snapshot."""
    from .current_route_start import CurrentStartPlan, encoded
    from .route_floor_commit import _chain_snapshot
    if (not isinstance(plan, CurrentStartPlan) or plan.route is not route
            or plan.observer is not observer or segment_index != 0):
        raise ValueError('Exact initial plan, observer and first segment required')
    chain = plan.floor_chain
    snapshot = _chain_snapshot(chain)
    geometry = observer.geometry
    source, mesh, ground = observer.source, observer.mesh, observer.ground
    plan_bytes, evidence_bytes, bounds = plan.plan_bytes, plan.evidence_bytes, plan.planning_bounds
    region_policy, native_evidence = plan.region_policy, plan.native_region_evidence
    classifier = region_policy.classifier if region_policy is not None else None
    if (sha256(plan_bytes).hexdigest() != route.artifact_sha256
            or sha256(evidence_bytes).hexdigest() != geometry.same_floor_evidence_sha256
            or chain.index != 1 or chain.inventory_sha256 != geometry.source_wld_sha256
            or chain.body_height != bounds.body_height):
        raise ValueError('Initial floor plan hashes or source context differ')
    try:
        evidence = json.loads(evidence_bytes)
        if evidence['format'] == 'eql-current-destination-geometry-v1':
            if (evidence['initial_chain_proof'] != chain.previous.proof_sha256
                    or evidence['initial_chain_index'] != chain.index):
                raise ValueError('Destination initial floor proof differs')
            evidence = evidence['initial_geometry']
        seed = evidence['seed']
        seed_fix = seed['observations'][-1]
        if evidence['format'] == 'eql-current-start-geometry-v1':
            if region_policy is not None or native_evidence is not None:
                raise ValueError('Legacy floor cannot claim native policy evidence')
            if any(evidence[key]['candidate'] is not True for key in ('terrain', 'static', 'bsp')):
                raise ValueError('Initial terrain/static/BSP evidence refused')
        elif evidence['format'] == 'eql-current-start-geometry-v2':
            from .native_region_policy import (NativeZeroRegionTrialPolicy,
                NativeRegionPlanningEvidence, encoded as native_encoded)
            if (type(region_policy) is not NativeZeroRegionTrialPolicy
                    or type(native_evidence) is not NativeRegionPlanningEvidence
                    or route.zone != 'crushbone' or reader.zone_id != 58
                    or region_policy.wld_sha256 != chain.inventory_sha256
                    or region_policy.mesh_sha256 != geometry.mesh_sha256
                    or region_policy.archive_sha256 != geometry.source_archive_sha256
                    or seed['native_region_policy'] != region_policy.record()
                    or native_encoded(evidence['native_region']) != native_evidence.payload
                    or evidence['native_region_sha256'] != native_evidence.sha256):
                raise ValueError('Initial native floor context differs')
            region_policy.validate(native_evidence, **{k:evidence[k] for k in ('terrain', 'static', 'bsp')})
        else:
            raise ValueError('Unknown initial floor evidence format')
        if (
                encoded(evidence['terrain']['floor_step']) != encoded(asdict(chain.previous))
                or sha256(encoded(seed)).hexdigest() != chain.seed_evidence_sha256
                or seed['pins'][2] != chain.inventory_sha256
                or encoded(seed['owner_binding']) != encoded(owner_binding)
                or encoded(seed['log_identity']) != encoded(reader.tail.identity)
                or tuple(seed_fix[k] for k in ('zone_id', 'zone_display_name', 'log_epoch', 'zone_generation')) !=
                   (reader.zone_id, reader.zone_display_name, reader.tail.epoch, reader.zone_generation)
                or first.log_line_seq <= seed_fix['log_line_seq']):
            raise ValueError('Initial checked floor or fresh owner observations differ')
    except (KeyError, TypeError, IndexError, json.JSONDecodeError) as error:
        raise ValueError('Malformed initial floor geometry evidence') from error

    def check():
        if (plan.floor_chain is not chain or plan.route is not route
                or plan.observer is not observer or observer.geometry is not geometry
                or observer.source is not source or observer.mesh is not mesh or observer.ground is not ground
                or plan.plan_bytes is not plan_bytes or plan.evidence_bytes is not evidence_bytes
                or plan.planning_bounds is not bounds or _chain_snapshot(chain) != snapshot
                or plan.region_policy is not region_policy or plan.native_region_evidence is not native_evidence):
            raise ValueError('Initial floor plan changed during height measurement')
        if region_policy is not None:
            if region_policy.classifier is not classifier:
                raise ValueError('Initial native classifier changed during height measurement')
            region_policy.validate(native_evidence, **{k:evidence[k] for k in ('terrain', 'static', 'bsp')})
    return chain, check


def measure_current_height(observer, reader, first, second, *, route, segment_index,
                           owner_binding, binding_reader, clock, record_id,
                           released_at, local_wall_clock=datetime.now,
                           residual_limit=.05, valid_for=300., floor_plan=None):
    """Create a measured record before constructing the route follower.

    Uses the same live reader that will be handed to RouteSession. The caller
    already owns release/request correlation and the current zone observation;
    an unbound relative-motion JSON cannot be substituted. The source lookup
    considers all terrain layers at each printed XY, without selecting by Z.
    An explicit exact current plan may instead supply its already checked
    initial floor cell; fresh positions must remain inside that unchanged cell.
    This function does no input and leaves the reader/geometry unchanged.
    """
    from .fixed_route_follower import FixedRoute
    from .ground_observer import RouteGroundObserver, exact_detail_support

    if (not isinstance(observer, RouteGroundObserver) or not isinstance(reader, LocationLogReader)
            or not isinstance(route, FixedRoute) or not digest(route.artifact_sha256)
            or not isinstance(first, RawLocationFix) or not isinstance(second, RawLocationFix)
            or type(segment_index) is not int or not 0 <= segment_index < len(route.segments)
            or not isinstance(record_id,str) or not record_id
            or not immutable_binding(owner_binding) or not isinstance(owner_binding,tuple)
            or not callable(binding_reader) or not callable(clock)
            or not callable(local_wall_clock) or not finite(released_at) or released_at<0
            or not finite(residual_limit) or not 0 < residual_limit <= .25
            or not finite(valid_for) or not 0 < valid_for <= 1800.):
        raise ValueError('Current reader, stopped samples, route and owner binding required')
    g = observer.geometry
    if (route.zone != g.zone_short_name or route.mesh_sha256 != g.mesh_sha256
            or observer.source.archive_sha256 != g.source_archive_sha256
            or observer.source.wld_sha256 != g.source_wld_sha256):
        raise ValueError('Current height geometry identity mismatch')
    log_identity = reader.tail.identity
    source = observer.source
    floor = check_floor = None
    if floor_plan is not None:
        floor, check_floor = _bound_initial_floor(floor_plan, observer, route, reader,
            owner_binding, segment_index, first)

    def check():
        binding = binding_reader()
        wall = local_wall_clock()
        # Scope callbacks may pump events or take time. Judge freshness only
        # after they finish, including the native evidence validation work.
        if check_floor is not None:
            check_floor()
        now = clock()
        if (binding != owner_binding or not finite(now)
                or not finite(second.received_monotonic)
                or not 0 <= now-second.received_monotonic <= .5
                or reader.latest is not second or reader.tail.identity != log_identity
                or log_identity is None or reader.tail.partial
                or reader.log_line_seq != second.log_line_seq
                or observer.geometry is not g
                or observer.source is not source
                or observer.source.archive_sha256 != g.source_archive_sha256
                or observer.source.wld_sha256 != g.source_wld_sha256
                or not isinstance(wall,datetime) or wall.tzinfo is not None
                or any(not finite(f.received_monotonic) or not isinstance(f.log_local_time,datetime)
                       or f.log_local_time.tzinfo is not None for f in (first,second))
                or any(abs((wall-f.log_local_time).total_seconds()-(now-f.received_monotonic))>2
                       for f in (first,second))
                or (reader.zone_id,reader.zone_display_name,reader.tail.epoch,reader.zone_generation) !=
                   (second.zone_id,second.zone_display_name,second.log_epoch,second.zone_generation)):
            raise ValueError('Stopped height owner/log/session changed or samples expired')
        return now,wall

    check()
    if (not all(point(f.raw_coordinates) and finite(f.received_monotonic) for f in (first,second))
            or (first.zone_id,first.zone_display_name,first.log_epoch,first.zone_generation) !=
               (second.zone_id,second.zone_display_name,second.log_epoch,second.zone_generation)
            or type(first.log_line_seq) is not int or first.log_line_seq < 1
            or first.received_monotonic < released_at+.12
            or not isinstance(first.log_local_time,datetime) or first.log_local_time.tzinfo is not None
            or first.log_local_time>second.log_local_time
            or second.log_line_seq != first.log_line_seq+1
            or not .4 <= second.received_monotonic-first.received_monotonic <= 2.5
            or math.dist(first.raw_coordinates[:2],second.raw_coordinates[:2])>.25
            or abs(first.raw_coordinates[2]-second.raw_coordinates[2])>.25):
        raise ValueError('Two fresh consecutive stopped positions in one zone are required')
    polygon = route.segments[segment_index].polygon
    observer._polygon(polygon)
    samples = []
    for raw in (first,second):
        xy = (raw.raw_coordinates[1],raw.raw_coordinates[0])
        support = exact_detail_support(observer.mesh,polygon,xy)
        if support.status != 'supported':
            raise ValueError('Selected starting polygon does not uniquely support printed XY')
        source_z, ids = (observer.source.source_floor_at(xy) if floor is None else floor.floor_at(xy))
        if (not finite(source_z) or not isinstance(ids,tuple) or not 1 <= len(ids) <= 128
                or any(not isinstance(v,str) or not v for v in ids) or len(set(ids))!=len(ids)
                or abs(source_z-support.height)>g.maximum_source_baked_z_difference):
            raise ValueError('Independent source height/identity does not match selected geometry')
        samples.append(SourceFloorObservation(raw,(*raw.raw_coordinates[:2],source_z),
            g.source_archive_sha256,g.source_wld_sha256,ids,1,True))
        check()
    offsets = tuple(s.raw_fix.raw_coordinates[2]-s.ground_wld_xyz[2] for s in samples)
    center = sum(offsets)/2
    residuals = tuple(v-center for v in offsets)
    if center <= 0 or any(abs(v)>residual_limit for v in residuals):
        raise ValueError('Stopped height samples do not give a consistent positive correspondence')
    now,wall = check()
    evidence = StoppedHeightEvidence(*samples,owner_binding,log_identity,route.artifact_sha256,
        route.mesh_sha256,segment_index,offsets,residuals,now,released_at,wall,
        source_floor_kind='all_layers_exact_point' if floor is None else 'checked_initial_plan_floor',
        source_floor_proof_sha256=None if floor is None else floor.previous.proof_sha256,
        source_floor_seed_sha256=None if floor is None else floor.seed_evidence_sha256)
    return ObservedHeightCalibration(record_id,route.zone,second.zone_id,second.zone_display_name,
        second.log_epoch,second.zone_generation,g.source_archive_sha256,g.source_wld_sha256,
        center,residual_limit,second.log_line_seq,now,now+valid_for,evidence=evidence,
        live_verified=False)
