"""Produce route ground observations from pinned geometry and supplied live calibration.

No input, calibration creation, nearest-point snap or floor-chain advancement.
The caller still owns current zone/character/frame verification, scene checks,
request timing and movement authority. Unbound diagnostic positions are rejected.
"""
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import math
from pathlib import Path

from .fixed_route_follower import FixedRoute
from .ground_binding import (AlignedWldFix, GroundGeometryEvidence, HeightCalibration,
    MeshProjection, SourceFloorObservation, digest, finite, integer, point,
    validate_ground_binding,ground_zone_line)
from .location_log import RawLocationFix


class GroundObservationUnavailable(ValueError):
    pass


@dataclass(frozen=True)
class DetailSupport:
    status: str
    height: float | None = None
    supported_triangles: int = 0


def exact_detail_support(mesh, polygon, xy, *, max_triangles=512):
    """Distinguish absent support from ambiguous or malformed geometry.

    Uses the exact rational values of stored binary floats. No edge projection,
    extrapolation or nearby polygon lookup can manufacture support at raw XY.
    """
    if (not integer(polygon) or not isinstance(xy,tuple) or len(xy)!=2
            or not all(finite(v) for v in xy)
            or type(max_triangles) is not int or not 1<=max_triangles<=512):
        raise GroundObservationUnavailable('Invalid exact detail query')
    try:
        first,last=int(mesh._detail_start[polygon]),int(mesh._detail_start[polygon+1])
        if not 0<=first<last<=len(mesh._detail) or last-first>max_triangles:
            raise ValueError('Missing or oversized detail geometry')
        triangles=mesh._detail[first:last]
    except (AttributeError,IndexError,KeyError,TypeError,ValueError) as error:
        raise GroundObservationUnavailable('Missing or oversized detail geometry') from error
    x,y=(Fraction(v) for v in xy)
    heights=[]
    for triangle in triangles:
        try:
            values=tuple(tuple(float(v) for v in vertex) for vertex in triangle)
            if len(values)!=3 or any(len(v)!=3 or not all(finite(n) for n in v) for v in values):
                raise ValueError('Malformed detail triangle')
            a,b,c=(tuple(Fraction(v) for v in vertex) for vertex in values)
        except (TypeError,ValueError,OverflowError) as error:
            raise GroundObservationUnavailable('Malformed detail triangle') from error
        dx1,dy1=b[0]-a[0],b[1]-a[1]
        dx2,dy2=c[0]-a[0],c[1]-a[1]
        det=dx1*dy2-dy1*dx2
        if det==0:
            raise GroundObservationUnavailable('Degenerate detail triangle')
        u=((x-a[0])*dy2-(y-a[1])*dx2)/det
        v=(dx1*(y-a[1])-dy1*(x-a[0]))/det
        if min(u,v,1-u-v)>=0:
            heights.append(a[2]+u*(b[2]-a[2])+v*(c[2]-a[2]))
    if not heights:return DetailSupport('absent')
    if len(set(heights))!=1:return DetailSupport('ambiguous',supported_triangles=len(heights))
    return DetailSupport('supported',float(heights[0]),len(heights))


class RouteGroundObserver:
    """Read-only route-position producer; use load() for copied client files.

    Direct construction supports dependency-injected geometry fixtures. The
    supplied geometry evidence must already describe a verified source/mesh
    context; this observer does not turn a historical audit into live evidence.
    """
    def __init__(self, *, mesh, ground, source, geometry_evidence, reciprocal_links):
        g=geometry_evidence
        if (not isinstance(g,GroundGeometryEvidence) or g.geometry_verified is not True
                or not g.zone_short_name or not all(digest(v) for v in
                    (g.mesh_sha256,g.source_archive_sha256,g.source_wld_sha256,g.same_floor_evidence_sha256))
                or not finite(g.maximum_source_baked_z_difference)
                or g.maximum_source_baked_z_difference<=0
                or source.archive_sha256!=g.source_archive_sha256
                or source.wld_sha256!=g.source_wld_sha256):
            raise GroundObservationUnavailable('Geometry context/source identity mismatch')
        if len(mesh.area)!=len(ground.areas) or len(ground.areas)!=len(ground.components):
            raise GroundObservationUnavailable('Geometry array lengths differ')
        self.mesh,self.ground,self.source,self.geometry=mesh,ground,source,g
        self.expected_zone_line=ground_zone_line(g)
        if self.expected_zone_line is not None and (
                getattr(mesh,'mesh_sha256',None)!=g.mesh_sha256
                or getattr(ground,'mesh_sha256',None)!=g.mesh_sha256):
            raise GroundObservationUnavailable('Expected zone line needs matching loaded mesh views')
        self.links=frozenset(reciprocal_links)
        if (not isinstance(g.verified_portal_pairs,tuple) or len(g.verified_portal_pairs)>20000
                or len(set(g.verified_portal_pairs))!=len(g.verified_portal_pairs)):
            raise GroundObservationUnavailable('Invalid geometry portal set')
        for pair in g.verified_portal_pairs:
            if (not isinstance(pair,tuple) or len(pair)!=2
                    or not all(integer(v) for v in pair) or pair[0]>=pair[1]):
                raise GroundObservationUnavailable('Invalid geometry portal pair')
            self._portal(*pair)

    @classmethod
    def load(cls, mesh_path: Path, archive_path: Path, *, geometry_evidence):
        """Hash-check copied files before/after loading; keep read-only array views."""
        import numpy as np
        from .bsp_detail_view import BspDetailMeshView
        from .ground_sweep_view import GroundSweepView
        from .portal_precision_view import PortalPrecisionView
        g=geometry_evidence
        if not isinstance(g,GroundGeometryEvidence):
            raise GroundObservationUnavailable('Missing geometry context')
        pins=((mesh_path,g.mesh_sha256),(archive_path,g.source_archive_sha256))
        def verify():
            if any(not digest(expected) or path.is_symlink() or not path.is_file()
                   or sha256(path.read_bytes()).hexdigest()!=expected for path,expected in pins):
                raise GroundObservationUnavailable('Copied geometry file changed')
        verify()
        mesh=BspDetailMeshView.load(mesh_path,zone=g.zone_short_name)
        ground=GroundSweepView.load(mesh_path,zone=g.zone_short_name)
        source=PortalPrecisionView(ground,mesh_path,archive_path,zone=g.zone_short_name)
        with np.load(mesh_path,allow_pickle=False) as data:
            a,b=data['link_a'].reshape(-1),data['link_b'].reshape(-1)
            if len(a)!=len(b):raise GroundObservationUnavailable('Invalid copied link arrays')
            links=tuple((int(x),int(y)) for x,y in zip(a,b))
        result=cls(mesh=mesh,ground=ground,source=source,
                   geometry_evidence=g,reciprocal_links=links)
        verify()
        for owner in (mesh,ground,source):
            for value in vars(owner).values():
                if isinstance(value,np.ndarray):value.flags.writeable=False
        source.sources=tuple(source.sources)
        return result

    def _polygon(self, polygon):
        if not integer(polygon) or polygon>=len(self.ground.areas):
            raise GroundObservationUnavailable('Selected polygon is missing')
        line=ground_zone_line(self.geometry)
        if line is not self.expected_zone_line:
            raise GroundObservationUnavailable('Expected zone-line context changed')
        area=int(self.ground.areas[polygon])
        allowed=(area==63 and (line is None or polygon not in line.polygon_ids))
        if line is not None:allowed=allowed or line.allows_face(polygon,area)
        if (int(self.mesh.area[polygon])!=area or not allowed or int(self.ground.components[polygon])<0):
            raise GroundObservationUnavailable('Selected polygon is missing or not dry ground')
        return int(self.ground.components[polygon])

    def _portal(self, first, second):
        if (self._polygon(first)!=self._polygon(second)
                or (first,second) not in self.links or (second,first) not in self.links):
            raise GroundObservationUnavailable('Portal is not reciprocal dry same-component geometry')

    def observe(self, raw_fix, *, route, segment_index, height_calibration,
                motion_calibration_record_id, now, floor_chain=None,
                endpoint_radius=.25, height_tolerance=.25, mode='full_auto'):
        """Preserve exact raw identity/XY and independently measure both heights."""
        raw,cal,g=raw_fix,height_calibration,self.geometry
        from .observed_height import ObservedHeightCalibration, current_height_allowed
        if (not isinstance(raw,RawLocationFix) or not point(raw.raw_coordinates)
                or not isinstance(cal,HeightCalibration)
                or not current_height_allowed(cal,mode=mode,
                    route_sha256=getattr(route,'artifact_sha256',None))
                or cal.raw_xy_to_wld_transform!='identity'
                or not isinstance(route,FixedRoute) or route.zone!=g.zone_short_name
                or route.mesh_sha256!=g.mesh_sha256
                or not integer(segment_index) or segment_index>=len(route.segments)
                or not isinstance(motion_calibration_record_id,str) or not motion_calibration_record_id
                or not finite(now) or not finite(raw.received_monotonic)
                or not 0<=now-raw.received_monotonic<=.5
                or not all(finite(v) for v in (cal.valid_from_monotonic,cal.valid_until_monotonic))
                or not 0<=cal.valid_from_monotonic<=raw.received_monotonic<=now<=cal.valid_until_monotonic
                or cal.valid_from_monotonic>=cal.valid_until_monotonic
                or (raw.zone_id,raw.zone_display_name,raw.log_epoch,raw.zone_generation)!=
                   (cal.zone_id,cal.zone_display_name,cal.log_epoch,cal.zone_generation)
                or not integer(raw.log_line_seq) or not integer(cal.last_calibration_log_line_seq)
                or raw.log_line_seq<=cal.last_calibration_log_line_seq
                or cal.zone_short_name!=g.zone_short_name
                or cal.source_archive_sha256!=g.source_archive_sha256
                or cal.source_wld_sha256!=g.source_wld_sha256
                or self.source.archive_sha256!=g.source_archive_sha256
                or self.source.wld_sha256!=g.source_wld_sha256
                or not finite(endpoint_radius) or not 0<endpoint_radius<=.25
                or not finite(height_tolerance) or not 0<height_tolerance<=.25):
            raise GroundObservationUnavailable('Missing fresh raw fix/current external calibration or route context')
        xy=(raw.raw_coordinates[1],raw.raw_coordinates[0])
        segment=route.segments[segment_index]
        polygon=segment.polygon;component=self._polygon(polygon)
        support=exact_detail_support(self.mesh,polygon,xy)
        if support.status=='ambiguous':
            raise GroundObservationUnavailable('Current polygon has ambiguous detail heights')
        if support.status=='absent':
            candidates=[]
            for other,portal in ((segment_index-1,segment.start),(segment_index+1,segment.end)):
                if not 0<=other<len(route.segments) or math.dist(xy,portal[:2])>endpoint_radius:continue
                neighbor=route.segments[other].polygon
                if tuple(sorted((polygon,neighbor))) not in g.verified_portal_pairs:continue
                self._portal(polygon,neighbor)
                value=exact_detail_support(self.mesh,neighbor,xy)
                if value.status=='ambiguous':
                    raise GroundObservationUnavailable('Adjacent polygon has ambiguous detail heights')
                if value.status=='supported' and abs(value.height-portal[2])<=endpoint_radius+height_tolerance:
                    candidates.append((neighbor,value))
            if len(candidates)!=1:
                raise GroundObservationUnavailable('No unique selected adjacent portal supports exact raw XY')
            polygon,support=candidates[0]
        # Current support wins even if its source/height check will fail. Never
        # use a more convenient neighbor or raw Z to choose a different floor.
        try:
            if floor_chain is None:
                source_z,source_ids=self.source.source_floor_at(xy)
            else:
                if floor_chain.inventory_sha256!=g.source_wld_sha256:
                    raise ValueError('Floor-chain inventory does not match copied WLD')
                source_z,source_ids=floor_chain.floor_at(xy)
        except (AttributeError,ValueError) as error:
            raise GroundObservationUnavailable('Source floor unavailable: '+str(error)) from error
        source=SourceFloorObservation(raw,(*raw.raw_coordinates[:2],source_z),
            g.source_archive_sha256,g.source_wld_sha256,source_ids,1,True)
        neighbors=tuple(sorted(b if a==polygon else a for a,b in g.verified_portal_pairs if polygon in (a,b)))
        projection=MeshProjection(raw,(*xy,support.height),g.mesh_sha256,polygon,int(self.ground.areas[polygon]),component,
            g.source_archive_sha256,g.source_wld_sha256,source_ids,g.same_floor_evidence_sha256,
            g.maximum_source_baked_z_difference,neighbors,True,True,
            None if self.expected_zone_line is None else self.expected_zone_line.sha256)
        aligned=AlignedWldFix(raw,source,projection,cal,route.zone,motion_calibration_record_id,
            live_alignment_verified=cal.live_verified,
            alignment_kind=('current_stopped_height_correspondence'
                if isinstance(cal,ObservedHeightCalibration) else 'external_live_verification'))
        check=validate_ground_binding(aligned,height_calibration=cal,geometry_evidence=g,
            mesh_sha256=g.mesh_sha256,zone_short_name=route.zone,now=now,
            motion_calibration_record_id=motion_calibration_record_id,mode=mode)
        if not check.candidate:raise GroundObservationUnavailable(check.reason)
        return aligned
