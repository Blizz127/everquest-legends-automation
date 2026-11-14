"""Current stopped-position correspondence for supervised route startup.

The printed actor Z and copied terrain Z are measured separately. Their
difference is an observed correspondence at two decimal-coordinate centers,
not a body height, collision offset, or proof of future ground clearance.
Only measurement-mode route consumers may use this evidence. It never marks
the legacy full-auto calibration or a real route as verified.
"""
from dataclasses import asdict, dataclass
from datetime import datetime
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


@dataclass(frozen=True, kw_only=True)
class ObservedHeightCalibration(HeightCalibration):
    evidence: StoppedHeightEvidence


def height_record(calibration):
    """JSON-compatible run evidence; saved records do not restore live scope."""
    result = asdict(calibration)
    if isinstance(calibration,ObservedHeightCalibration):
        result['evidence']['observed_local_time']=result['evidence']['observed_local_time'].isoformat()
        for key in ('first','second'):
            raw = result['evidence'][key]['raw_fix']
            raw['log_local_time'] = raw['log_local_time'].isoformat()
    return result


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


def measure_current_height(observer, reader, first, second, *, route, segment_index,
                           owner_binding, binding_reader, clock, record_id,
                           released_at, local_wall_clock=datetime.now,
                           residual_limit=.05, valid_for=300.):
    """Create a measured record before constructing the route follower.

    Uses the same live reader that will be handed to RouteSession. The caller
    already owns release/request correlation and the current zone observation;
    an unbound relative-motion JSON cannot be substituted. The source lookup
    considers all terrain layers at each printed XY, without selecting by Z.
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

    def check():
        now = clock()
        wall = local_wall_clock()
        if (binding_reader() != owner_binding or not finite(now)
                or not finite(second.received_monotonic)
                or not 0 <= now-second.received_monotonic <= .5
                or reader.latest is not second or reader.tail.identity != log_identity
                or log_identity is None or reader.tail.partial
                or reader.log_line_seq != second.log_line_seq
                or observer.geometry is not g
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
        source_z, ids = observer.source.source_floor_at(xy)
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
        route.mesh_sha256,segment_index,offsets,residuals,now,released_at,wall)
    return ObservedHeightCalibration(record_id,route.zone,second.zone_id,second.zone_display_name,
        second.log_epoch,second.zone_generation,g.source_archive_sha256,g.source_wld_sha256,
        center,residual_limit,second.log_line_seq,now,now+valid_for,evidence=evidence,
        live_verified=False)
