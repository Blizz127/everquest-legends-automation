"""Source-supported one-float32-ULP portal corrections for offline diagnosis.

Only a failed ground-coverage check can be retried. Corrections are ephemeral
XY midpoints; copied data, heights, areas and components are never rewritten.
This does not validate collision, headroom, BSP hazards or client movement.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import struct

from .ground_sweep import GroundFace, GroundCoverage, area, check_ground_coverage, clip, cross, finite, hull


@dataclass(frozen=True)
class PortalLink:
    source: int
    target: int
    edge: tuple[tuple[float, float, float], ...]


@dataclass(frozen=True)
class QuantizedSeam:
    source: int
    target: int
    axis: int
    source_coordinate: float
    target_coordinate: float
    span: tuple[float, float]

    def __post_init__(self):
        if (self.axis not in (0,1) or isinstance(self.axis,bool)
                or any(not isinstance(p,int) or isinstance(p,bool) or p < 0 for p in (self.source,self.target))
                or self.source == self.target or len(self.span) != 2
                or not all(finite(v) for v in self.span) or self.span[0] >= self.span[1]
                or not adjacent_float32(self.source_coordinate,self.target_coordinate)):
            raise ValueError('Invalid one-ULP reciprocal seam')

    @property
    def midpoint(self):
        return (self.source_coordinate + self.target_coordinate) / 2


@dataclass(frozen=True)
class SourceFace:
    vertices_wld: tuple[tuple[float, float, float], ...]
    flag: int
    material_class: str
    fragment: int = -1
    face: int = -1


@dataclass(frozen=True)
class SourceSupport:
    candidate: bool
    reason: str
    fragment: int | None = None
    face: int | None = None
    edge_margin: float | None = None
    grade: float | None = None
    maximum_source_baked_z_difference: float | None = None
    source_faces: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class PrecisionCheck:
    candidate: bool
    reason: str
    coverage: GroundCoverage | None = None
    source_support: SourceSupport | None = None
    seams: tuple[QuantizedSeam, ...] = ()
    shifted_vertices: int = 0
    real_client_accepted: bool = False
    input_authorized: bool = False


def adjacent_float32(a, b):
    if not finite(a) or not finite(b) or not 0 < abs(a-b) <= .001:
        return False
    try:
        pa, pb = struct.pack('<f', a), struct.pack('<f', b)
    except (OverflowError, struct.error):
        return False
    if struct.unpack('<f', pa)[0] != a or struct.unpack('<f', pb)[0] != b:
        return False
    ia, ib = struct.unpack('<I', pa)[0], struct.unpack('<I', pb)[0]
    return ia >> 31 == ib >> 31 and abs(ia-ib) == 1


def derive_seam(first, second, areas, components):
    if (not isinstance(first, PortalLink) or not isinstance(second, PortalLink)
            or first.source != second.target or first.target != second.source
            or first.source == first.target):
        return None
    a, b = first.source, first.target
    try:
        if areas[a] != 63 or areas[b] != 63 or components[a] < 0 or components[a] != components[b]:
            return None
    except (IndexError, KeyError, TypeError):
        return None
    if any(len(link.edge) != 2 or any(len(p) != 3 or not all(finite(v) for v in p) for p in link.edge)
           for link in (first, second)):
        return None
    for axis in (0, 1):
        other = 1-axis
        ea, eb = sorted(first.edge, key=lambda p:p[other]), sorted(second.edge, key=lambda p:p[other])
        if (ea[0][axis] != ea[1][axis] or eb[0][axis] != eb[1][axis]
                or not adjacent_float32(ea[0][axis], eb[0][axis])
                or ea[0][other] >= ea[1][other]
                or any(pa[other] != pb[other] or pa[2] != pb[2] for pa,pb in zip(ea,eb))):
            continue
        return QuantizedSeam(a,b,axis,ea[0][axis],eb[0][axis],(ea[0][other],ea[1][other]))
    return None


def collect_seams(links, areas, components):
    """Duplicate or nonreciprocal links never supply a correction."""
    directed = {}
    for link in links:
        directed.setdefault((link.source,link.target),[]).append(link)
    seams = []
    for (a,b), forward in directed.items():
        reverse = directed.get((b,a),())
        if a < b and len(forward) == len(reverse) == 1:
            seam = derive_seam(forward[0],reverse[0],areas,components)
            if seam is not None:
                seams.append(seam)
    return tuple(seams)


def plane(vertices):
    a,b,c = vertices
    det = cross(a,b,c)
    if abs(det) < 1e-12:
        return None
    dx = ((b[2]-a[2])*(c[1]-a[1])-(c[2]-a[2])*(b[1]-a[1]))/det
    dy = ((b[0]-a[0])*(c[2]-a[2])-(c[0]-a[0])*(b[2]-a[2]))/det
    return dx,dy,lambda p:a[2]+(p[0]-a[0])*dx+(p[1]-a[1])*dy


def source_support(footprint, sources, baked_faces, *, maximum_z_difference, edge_margin=.002):
    """Require one continuous source layer and bound whole-patch height deltas.

    The explicit vertical bound is diagnostic, not a proven bake error bound
    or live alignment. Every source face whose XY projection overlaps must be
    supplied, including other flags/materials/floors; none is height-filtered.
    """
    if (not finite(maximum_z_difference) or maximum_z_difference <= 0
            or not finite(edge_margin) or edge_margin < .002 or len(sources) > 128):
        return SourceSupport(False,'invalid_source_limits')
    boundary = hull(footprint)
    expanded = hull((x+dx,y+dy) for x,y in boundary
                    for dx in (-edge_margin,edge_margin) for dy in (-edge_margin,edge_margin))
    overlapping = []
    for face in sources:
        if (not isinstance(face,SourceFace) or len(face.vertices_wld) != 3
                or any(len(v) != 3 or not all(finite(n) for n in v) for v in face.vertices_wld)):
            return SourceSupport(False,'invalid_source_face')
        vertices = tuple((y,x,z) for x,y,z in face.vertices_wld)
        triangle = hull(p[:2] for p in vertices)
        if len(triangle) == 3 and area(clip(triangle,expanded)) > 1e-10:
            surface = plane(vertices)
            if surface is None:
                return SourceSupport(False,'source_plane_degenerate')
            overlapping.append((face,vertices,triangle,surface))
    if not overlapping or len(overlapping) > 32:
        return SourceSupport(False,'source_projection_missing_or_over_budget')
    if any(face.flag != 0 or face.material_class != 'Diffuse' for face,*_ in overlapping):
        return SourceSupport(False,'source_flag_or_material_refused')
    # A continuous reference is inferred only inside this copied source model.
    # Expanding the footprint verifies a margin across external source edges;
    # shared internal triangle edges may legitimately cross the footprint.
    center = tuple(sum(p[k] for p in boundary)/len(boundary) for k in range(2))
    heights = [surface[2](center) for _,_,tri,surface in overlapping
               if all(cross(a,tri[(i+1)%3],center) >= -1e-10 for i,a in enumerate(tri))]
    if not heights or max(heights)-min(heights) > 1e-6:
        return SourceSupport(False,'source_reference_missing_or_layered')
    source_reference = (*center,heights[0])
    # Include EVERY projected source floor in the vertical window. This must
    # not silently filter out a competing surface above or below the route.
    window = max(abs(surface[2](p)-heights[0]) for _,_,tri,surface in overlapping
                 for p in clip(tri,expanded)) + 1.
    source_check = check_ground_coverage(expanded,
        tuple(GroundFace(vertices,63,0) for _,vertices,_,_ in overlapping),
        reference=source_reference,component=0,vertical_window=window,height_tolerance=1e-6,max_faces=128)
    if not source_check.candidate:
        return SourceSupport(False,'source_'+source_check.reason)
    delta, patches = 0., 0
    for baked in baked_faces:
        polygon = hull(p[:2] for p in baked.vertices)
        patch = clip(polygon,boundary) if len(polygon) == 3 else ()
        if area(patch) <= 1e-7:
            continue
        surface = plane(baked.vertices)
        if surface is None:
            return SourceSupport(False,'baked_plane_degenerate')
        patches += 1
        compared_area = 0.
        for _,_,triangle,source_plane in overlapping:
            intersection = clip(patch,triangle)
            if area(intersection) <= 1e-10:
                continue
            compared_area += area(intersection)
            delta = max(delta,*(abs(surface[2](p)-source_plane[2](p)) for p in intersection))
        if abs(compared_area-area(patch)) > 1e-7:
            return SourceSupport(False,'source_does_not_cover_baked_patch')
    identifiers = tuple((f.fragment,f.face) for f,*_ in overlapping)
    if not patches or not finite(delta) or delta > maximum_z_difference:
        return SourceSupport(False,'source_baked_height_mismatch',edge_margin=edge_margin,
            grade=source_check.max_grade,maximum_source_baked_z_difference=delta,source_faces=identifiers)
    return SourceSupport(True,'source_support_diagnostic_only',edge_margin=edge_margin,
        grade=source_check.max_grade,maximum_source_baked_z_difference=delta,source_faces=identifiers)


def retry_precision_gap(original, footprint, faces, polygon_ids, seams, sources, *,
                        reference, component, vertical_window, maximum_source_z_difference):
    if not isinstance(original,GroundCoverage) or original.candidate or original.reason != 'uncovered_ground_area':
        return PrecisionCheck(False,'original_failure_is_not_a_coverage_gap')
    if (not 1 <= len(seams) <= 8 or len(faces) != len(polygon_ids) or len(faces) > 96
            or any(not isinstance(s,QuantizedSeam) for s in seams)):
        return PrecisionCheck(False,'no_bounded_reciprocal_seam_set')
    corrected, shifted = [], 0
    touches = {(i,p):set() for i,s in enumerate(seams) for p in (s.source,s.target)}
    for face,poly in zip(faces,polygon_ids):
        vertices = []
        for point in face.vertices:
            adjusted = list(point)
            assignments = {}
            for i,seam in enumerate(seams):
                coordinate = seam.source_coordinate if poly == seam.source else seam.target_coordinate if poly == seam.target else None
                if (coordinate is None or point[seam.axis] != coordinate
                        or not seam.span[0] <= point[1-seam.axis] <= seam.span[1]):
                    continue
                if seam.axis in assignments and assignments[seam.axis] != seam.midpoint:
                    return PrecisionCheck(False,'conflicting_local_seam_corrections')
                assignments[seam.axis] = seam.midpoint
                touches[i,poly].add(point[1-seam.axis])
            for axis,value in assignments.items():
                adjusted[axis] = value
            shifted += bool(assignments)
            vertices.append(tuple(adjusted))
        corrected.append(GroundFace(tuple(vertices),face.area_id,face.component))
    if not shifted or any(len(points)<2 for points in touches.values()):
        return PrecisionCheck(False,'both_local_boundary_edges_required')
    corrected = tuple(corrected)
    coverage = check_ground_coverage(footprint,corrected,reference=reference,
                                     component=component,vertical_window=vertical_window)
    if not coverage.candidate:
        return PrecisionCheck(False,'corrected_footprint_'+coverage.reason,coverage,seams=seams,shifted_vertices=shifted)
    support = source_support(footprint,sources,corrected,maximum_z_difference=maximum_source_z_difference)
    return PrecisionCheck(support.candidate,'local_precision_diagnostic_only' if support.candidate else support.reason,
                          coverage,support,seams,shifted)
