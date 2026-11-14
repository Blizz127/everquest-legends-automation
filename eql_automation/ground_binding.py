"""Separate physical source ground from its baked navigation approximation.

These immutable records are evidence containers, not movement authority.
The full-auto path requires external live verification. Measurement mode can
instead consume the explicitly typed current stopped-height correspondence
produced by observed_height, without changing its live_verified=False scope.
Historical/offline data cannot self-issue live verification. These checks
reject inconsistent records and never open an input device.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import re

from .location_log import RawLocationFix


def finite(value):
    if not isinstance(value,(int,float)) or isinstance(value,bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def point(value):
    return isinstance(value,tuple) and len(value)==3 and all(finite(v) for v in value)


def digest(value):
    return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None


def integer(value):
    return isinstance(value,int) and not isinstance(value,bool) and value>=0


@dataclass(frozen=True)
class HeightCalibration:
    record_id: str
    zone_short_name: str
    zone_id: int
    zone_display_name: str
    log_epoch: int
    zone_generation: int
    source_archive_sha256: str
    source_wld_sha256: str
    raw_z_minus_source_z: float
    residual_limit: float
    last_calibration_log_line_seq: int
    valid_from_monotonic: float
    valid_until_monotonic: float
    raw_xy_to_wld_transform: str = 'identity'
    live_verified: bool = False


@dataclass(frozen=True)
class SourceFloorObservation:
    raw_fix: RawLocationFix
    ground_wld_xyz: tuple[float,float,float]
    source_archive_sha256: str
    source_wld_sha256: str
    source_surface_ids: tuple[str,...]
    floor_count: int
    geometry_verified: bool = False


@dataclass(frozen=True)
class GroundGeometryEvidence:
    """Independent verifier context, pinned before observations arrive.

    Portal pairs are canonical (smaller polygon first), reciprocal, dry and
    same-component in the pinned mesh. The height bound describes the region
    audited by the same-floor proof, never a limit proposed by an observation.
    This container does not itself compute or verify that proof.
    """
    zone_short_name: str
    mesh_sha256: str
    source_archive_sha256: str
    source_wld_sha256: str
    same_floor_evidence_sha256: str
    maximum_source_baked_z_difference: float
    verified_portal_pairs: tuple[tuple[int,int], ...] = ()
    geometry_verified: bool = False
    expected_zone_line: object = None


@dataclass(frozen=True)
class MeshProjection:
    """Exact-XY mesh observation supplied by an independent geometry verifier.

    A route producer must prefer the current selected polygon when it has
    support at this XY. Neighbor fallback requires verified absence of that
    support, in addition to the consumer's portal disk and adjacency checks.
    RouteGroundObserver enforces that order with exact detail support. Its
    production calibration/zone/scene connection still requires live evidence.
    """
    raw_fix: RawLocationFix
    package_xyz: tuple[float,float,float]
    mesh_sha256: str
    polygon: int
    area: int
    component: int
    source_archive_sha256: str
    source_wld_sha256: str
    source_surface_ids: tuple[str,...]
    same_floor_evidence_sha256: str
    maximum_source_baked_z_difference: float
    verified_neighbor_polygons: tuple[int,...] = ()
    projection_verified: bool = False
    same_floor_verified: bool = False
    expected_zone_line_sha256: str | None = None


def ground_zone_line(geometry):
    """Resolve an explicitly pinned transition context; never infer one."""
    from .zone_line import ExpectedZoneLine
    line=geometry.expected_zone_line
    if line is not None:
        if type(line) is not ExpectedZoneLine:
            raise ValueError('Typed expected zone-line geometry required')
        line.check_sources(zone=geometry.zone_short_name,mesh_sha256=geometry.mesh_sha256,
            archive_sha256=geometry.source_archive_sha256,wld_sha256=geometry.source_wld_sha256)
    return line


@dataclass(frozen=True)
class AlignedWldFix:
    raw_fix: RawLocationFix
    source_floor: SourceFloorObservation
    mesh_projection: MeshProjection
    height_calibration: HeightCalibration
    zone_short_name: str
    # This existing frame/motion record is distinct from height calibration.
    calibration_record_id: str
    live_alignment_verified: bool = False
    alignment_kind: str = 'external_live_verification'

    @property
    def mesh_sha256(self):
        return self.mesh_projection.mesh_sha256


@dataclass(frozen=True)
class GroundBindingCheck:
    candidate: bool
    reason: str
    height_residual: float | None = None
    source_baked_z_difference: float | None = None
    real_client_accepted: bool = False
    input_authorized: bool = False


def validate_ground_binding(aligned, *, height_calibration, geometry_evidence, mesh_sha256, zone_short_name,
                            now, motion_calibration_record_id=None, mode='full_auto'):
    """Validate bindings to the verifier's exact current calibration object.

    Only the identity raw XY→WLD transform is supported by this contract.
    The two heights may differ; they must never be substituted for each other.
    The per-projection source/bake bound must come from pinned same-floor
    evidence, not from widening the route endpoint or G2 snap tolerance.
    """
    from .observed_height import ObservedHeightCalibration, current_height_allowed
    measured = isinstance(height_calibration,ObservedHeightCalibration)
    alignment_ok = (isinstance(aligned,AlignedWldFix) and (
        (not measured and aligned.live_alignment_verified is True)
        or (measured and aligned.live_alignment_verified is False
            and aligned.alignment_kind=='current_stopped_height_correspondence')))
    if (not alignment_ok
            or not isinstance(height_calibration,HeightCalibration)
            or aligned.height_calibration is not height_calibration
            or not current_height_allowed(height_calibration,mode=mode)
            or (measured and height_calibration.evidence.mesh_sha256!=mesh_sha256)
            or not isinstance(geometry_evidence,GroundGeometryEvidence)
            or geometry_evidence.geometry_verified is not True
            or not isinstance(aligned.raw_fix,RawLocationFix)
            or not isinstance(aligned.source_floor,SourceFloorObservation)
            or not isinstance(aligned.mesh_projection,MeshProjection)):
        return GroundBindingCheck(False,'missing_current_verified_ground_binding')
    raw,source,projection,cal = aligned.raw_fix,aligned.source_floor,aligned.mesh_projection,height_calibration
    geometry = geometry_evidence
    try:line=ground_zone_line(geometry)
    except ValueError:return GroundBindingCheck(False,'expected_zone_line_context_mismatch')
    if projection.expected_zone_line_sha256!=(None if line is None else line.sha256):
        return GroundBindingCheck(False,'expected_zone_line_projection_mismatch')
    if (geometry.zone_short_name != zone_short_name or geometry.mesh_sha256 != mesh_sha256
            or geometry.source_archive_sha256 != cal.source_archive_sha256
            or geometry.source_wld_sha256 != cal.source_wld_sha256
            or not digest(geometry.same_floor_evidence_sha256)
            or projection.same_floor_evidence_sha256 != geometry.same_floor_evidence_sha256
            or not finite(geometry.maximum_source_baked_z_difference)
            or geometry.maximum_source_baked_z_difference <= 0
            or projection.maximum_source_baked_z_difference != geometry.maximum_source_baked_z_difference
            or not isinstance(geometry.verified_portal_pairs,tuple)
            or len(geometry.verified_portal_pairs) > 20000
            or any(not isinstance(pair,tuple) or len(pair)!=2
                   or not all(integer(p) for p in pair) or pair[0]>=pair[1]
                   for pair in geometry.verified_portal_pairs)
            or len(set(geometry.verified_portal_pairs)) != len(geometry.verified_portal_pairs)):
        return GroundBindingCheck(False,'ground_geometry_context_mismatch')
    if (source.raw_fix is not raw or projection.raw_fix is not raw
            or source.geometry_verified is not True or projection.projection_verified is not True
            or projection.same_floor_verified is not True
            or not isinstance(cal.record_id,str) or not cal.record_id
            or not isinstance(aligned.calibration_record_id,str) or not aligned.calibration_record_id
            or (motion_calibration_record_id is not None and aligned.calibration_record_id != motion_calibration_record_id)
            or not isinstance(zone_short_name,str) or not zone_short_name
            or aligned.zone_short_name != zone_short_name or cal.zone_short_name != zone_short_name
            or cal.raw_xy_to_wld_transform != 'identity'):
        return GroundBindingCheck(False,'ground_observation_identity_or_verification_mismatch')
    if (not all(integer(v) for v in (raw.zone_id,raw.log_epoch,raw.zone_generation,raw.log_line_seq,
                                     cal.zone_id,cal.log_epoch,cal.zone_generation,cal.last_calibration_log_line_seq))
            or not isinstance(cal.zone_display_name,str) or not cal.zone_display_name
            or (raw.zone_id,raw.zone_display_name,raw.log_epoch,raw.zone_generation) !=
               (cal.zone_id,cal.zone_display_name,cal.log_epoch,cal.zone_generation)
            or raw.log_line_seq <= cal.last_calibration_log_line_seq
            or not all(finite(v) for v in (now,raw.received_monotonic,cal.valid_from_monotonic,cal.valid_until_monotonic))
            or not 0 <= cal.valid_from_monotonic <= raw.received_monotonic <= now <= cal.valid_until_monotonic
            or cal.valid_from_monotonic >= cal.valid_until_monotonic):
        return GroundBindingCheck(False,'height_calibration_session_or_time_mismatch')
    if (not digest(mesh_sha256) or projection.mesh_sha256 != mesh_sha256
            or not digest(cal.source_archive_sha256) or not digest(cal.source_wld_sha256)
            or source.source_archive_sha256 != cal.source_archive_sha256
            or source.source_wld_sha256 != cal.source_wld_sha256
            or projection.source_archive_sha256 != source.source_archive_sha256
            or projection.source_wld_sha256 != source.source_wld_sha256
            or not digest(projection.same_floor_evidence_sha256)
            or not isinstance(source.source_surface_ids,tuple) or not 1 <= len(source.source_surface_ids) <= 128
            or any(not isinstance(s,str) or not s for s in source.source_surface_ids)
            or len(set(source.source_surface_ids)) != len(source.source_surface_ids)
            or projection.source_surface_ids != source.source_surface_ids):
        return GroundBindingCheck(False,'ground_geometry_provenance_mismatch')
    area_ok=(projection.area==63 and (line is None or projection.polygon not in line.polygon_ids))
    if line is not None:area_ok=area_ok or line.allows_face(projection.polygon,projection.area)
    if (not integer(source.floor_count) or source.floor_count != 1
            or not integer(projection.polygon) or not integer(projection.area) or not area_ok
            or not integer(projection.component)
            or not isinstance(projection.verified_neighbor_polygons,tuple)
            or len(projection.verified_neighbor_polygons)>32
            or any(not integer(p) or p==projection.polygon for p in projection.verified_neighbor_polygons)
            or len(set(projection.verified_neighbor_polygons)) != len(projection.verified_neighbor_polygons)):
        return GroundBindingCheck(False,'source_floor_or_mesh_projection_ambiguous')
    if any(tuple(sorted((projection.polygon,p))) not in geometry.verified_portal_pairs
           for p in projection.verified_neighbor_polygons):
        return GroundBindingCheck(False,'ground_projection_adjacency_not_verified')
    if not all(point(p) for p in (raw.raw_coordinates,source.ground_wld_xyz,projection.package_xyz)):
        return GroundBindingCheck(False,'invalid_ground_coordinates')
    if (source.ground_wld_xyz[:2] != raw.raw_coordinates[:2]
            or projection.package_xyz[:2] != (source.ground_wld_xyz[1],source.ground_wld_xyz[0])):
        return GroundBindingCheck(False,'ground_projection_changed_raw_xy')
    if (not finite(cal.raw_z_minus_source_z) or cal.raw_z_minus_source_z <= 0
            or not finite(cal.residual_limit) or not 0 < cal.residual_limit <= .25
            or not finite(projection.maximum_source_baked_z_difference)
            or projection.maximum_source_baked_z_difference <= 0):
        return GroundBindingCheck(False,'invalid_ground_height_limits')
    residual = raw.raw_coordinates[2]-source.ground_wld_xyz[2]-cal.raw_z_minus_source_z
    delta = projection.package_xyz[2]-source.ground_wld_xyz[2]
    if abs(residual)>cal.residual_limit:
        return GroundBindingCheck(False,'raw_height_does_not_match_calibrated_source_floor',residual,delta)
    if abs(delta)>projection.maximum_source_baked_z_difference:
        return GroundBindingCheck(False,'source_mesh_same_floor_bound_exceeded',residual,delta)
    return GroundBindingCheck(True,'ground_binding_consistent_only',residual,delta)
