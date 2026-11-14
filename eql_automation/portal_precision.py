"""Source-supported bounded float32 portal corrections for offline diagnosis.

Only a failed ground-coverage check can be retried. Corrections are ephemeral
XY midpoints; copied data, heights, areas and components are never rewritten.
This does not validate collision, headroom, BSP hazards or client movement.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import struct

from .ground_sweep import GroundFace, GroundCoverage, area, check_ground_coverage, clip, cross, finite, hull
from .tile_rounding import TileBoundary,TileGrid


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
    maximum_ulp_steps: int = 1
    tile_boundary: TileBoundary | None = None

    def __post_init__(self):
        if (self.axis not in (0,1) or isinstance(self.axis,bool)
                or any(not isinstance(p,int) or isinstance(p,bool) or p < 0 for p in (self.source,self.target))
                or self.source == self.target or len(self.span) != 2
                or not all(finite(v) for v in self.span) or self.span[0] >= self.span[1]
                or type(self.maximum_ulp_steps) is not int or self.maximum_ulp_steps not in (1,2)
                or (self.tile_boundary is None and
                    float32_steps(self.source_coordinate,self.target_coordinate) not in range(1,self.maximum_ulp_steps+1))
                or (self.tile_boundary is not None and (not isinstance(self.tile_boundary,TileBoundary)
                    or not self.tile_boundary.matches(self.axis,self.source_coordinate,self.target_coordinate)))):
            raise ValueError('Invalid explicitly bounded reciprocal seam')

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
class SeamOverlap:
    first_face: int
    second_face: int
    first_polygon: int
    second_polygon: int
    area: float
    maximum_height_difference: float


@dataclass(frozen=True)
class OverlapAttribution:
    candidate: bool
    reason: str
    pairs: tuple[SeamOverlap, ...] = ()


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
    overlap_attribution: OverlapAttribution | None = None


def float32_steps(a, b):
    if not finite(a) or not finite(b) or not 0 < abs(a-b) <= .001:
        return None
    try:
        pa, pb = struct.pack('<f', a), struct.pack('<f', b)
    except (OverflowError, struct.error):
        return None
    if struct.unpack('<f', pa)[0] != a or struct.unpack('<f', pb)[0] != b:
        return None
    ia, ib = struct.unpack('<I', pa)[0], struct.unpack('<I', pb)[0]
    return abs(ia-ib) if ia >> 31 == ib >> 31 else None


def adjacent_float32(a, b):
    return float32_steps(a,b)==1


def derive_seam(first, second, areas, components, *, maximum_ulp_steps=1,tile_grid=None):
    if (not isinstance(first, PortalLink) or not isinstance(second, PortalLink)
            or type(maximum_ulp_steps) is not int or maximum_ulp_steps not in (1,2)
            or (tile_grid is not None and not isinstance(tile_grid,TileGrid))
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
                or ea[0][other] >= ea[1][other]
                or any(pa[other] != pb[other] or pa[2] != pb[2] for pa,pb in zip(ea,eb))):
            continue
        boundary=None
        if tile_grid is not None:
            boundary=tile_grid.match(axis,ea[0][axis],eb[0][axis])
            if boundary is None:continue
        elif float32_steps(ea[0][axis],eb[0][axis]) not in range(1,maximum_ulp_steps+1):
            continue
        return QuantizedSeam(a,b,axis,ea[0][axis],eb[0][axis],(ea[0][other],ea[1][other]),maximum_ulp_steps,boundary)
    return None


def collect_seams(links, areas, components, *, maximum_ulp_steps=1,tile_grid=None):
    """Duplicate or nonreciprocal links never supply a correction."""
    directed = {}
    for link in links:
        directed.setdefault((link.source,link.target),[]).append(link)
    seams = []
    for (a,b), forward in directed.items():
        reverse = directed.get((b,a),())
        if a < b and len(forward) == len(reverse) == 1:
            seam = derive_seam(forward[0],reverse[0],areas,components,
                              maximum_ulp_steps=maximum_ulp_steps,tile_grid=tile_grid)
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


def attribute_seam_overlaps(footprint, faces, polygon_ids, seams, *, reference, component, vertical_window):
    """Attribute EVERY meaningful original overlap to a named rounding strip.

    Both triangle interiors must lie on opposite sides of their own portal
    boundary. The overlap must remain inside that exact strip and portal span,
    with matching ground heights. Original invalid/steep/forbidden faces cannot
    be hidden by a tiny XY correction. The caller subsequently checks the
    entire corrected footprint and complete source terrain again.
    """
    boundary = hull(footprint)
    patches, pairs = [], []
    for index,(face,poly) in enumerate(zip(faces,polygon_ids)):
        if (not isinstance(face,GroundFace) or not isinstance(face.vertices,tuple) or len(face.vertices)!=3
                or any(not isinstance(p,tuple) or len(p)!=3 or not all(finite(n) for n in p) for p in face.vertices)):
            return OverlapAttribution(False,'invalid_original_overlap_face')
        triangle = hull(p[:2] for p in face.vertices)
        patch = clip(triangle,boundary) if len(triangle)==3 else ()
        if area(patch)<=1e-7:
            continue
        surface = plane(face.vertices)
        if surface is None:
            return OverlapAttribution(False,'original_overlap_plane_degenerate')
        heights = [surface[2](p) for p in patch]
        low,high = reference[2]-vertical_window,reference[2]+vertical_window
        if max(heights)<low or min(heights)>high:
            continue
        if (min(heights)<low or max(heights)>high or face.area_id!=63 or face.component!=component
                or math.hypot(*surface[:2])>1.):
            return OverlapAttribution(False,'original_overlap_surface_not_safe_ground')
        patches.append((index,poly,face,patch,surface))
    for offset,(i,poly,face,patch,surface) in enumerate(patches):
        for j,other_poly,other_face,other_patch,other_surface in patches[:offset]:
            intersection = clip(patch,other_patch)
            overlap = area(intersection)
            # With at most 96 faces, ignored arithmetic dust totals <4.6e-9,
            # below the unchanged full-coverage area tolerance of 1e-7.
            if overlap<=1e-12:
                continue
            candidates = [s for s in seams if {s.source,s.target}=={poly,other_poly}]
            if len(candidates)!=1:
                return OverlapAttribution(False,'overlap_pair_not_unique_reciprocal_seam',tuple(pairs))
            seam = candidates[0]
            left,right = sorted((seam.source_coordinate,seam.target_coordinate))
            if any(not left-1e-10 <= p[seam.axis] <= right+1e-10
                   or not seam.span[0]-1e-10 <= p[1-seam.axis] <= seam.span[1]+1e-10
                   for p in intersection):
                return OverlapAttribution(False,'overlap_outside_exact_portal_strip',tuple(pairs))
            signs = []
            for polygon,triangle_face in ((poly,face),(other_poly,other_face)):
                coordinate = seam.source_coordinate if polygon==seam.source else seam.target_coordinate
                offsets = [p[seam.axis]-coordinate for p in triangle_face.vertices]
                nonzero = [v for v in offsets if v!=0]
                if not nonzero or any(v*nonzero[0]<=0 for v in nonzero) or 0 not in offsets:
                    return OverlapAttribution(False,'overlap_face_not_on_one_portal_side',tuple(pairs))
                signs.append(1 if nonzero[0]>0 else -1)
            if signs[0]==signs[1]:
                return OverlapAttribution(False,'overlap_faces_not_on_opposite_portal_sides',tuple(pairs))
            delta = max(abs(surface[2](p)-other_surface[2](p)) for p in intersection)
            if delta>.01:
                return OverlapAttribution(False,'overlap_has_distinct_ground_heights',tuple(pairs))
            pairs.append(SeamOverlap(i,j,poly,other_poly,overlap,delta))
    if not pairs:
        return OverlapAttribution(False,'no_original_seam_overlap')
    return OverlapAttribution(True,'all_original_overlaps_attributed_to_reciprocal_ulps',tuple(pairs))


def retry_precision_gap(original, footprint, faces, polygon_ids, seams, sources, *,
                        reference, component, vertical_window, maximum_source_z_difference,
                        allow_overlap=False):
    allowed = ('uncovered_ground_area','overlapping_ground_faces') if allow_overlap is True else ('uncovered_ground_area',)
    if not isinstance(original,GroundCoverage) or original.candidate or original.reason not in allowed:
        return PrecisionCheck(False,'original_failure_is_not_a_coverage_gap')
    if (not 1 <= len(seams) <= 8 or len(faces) != len(polygon_ids) or len(faces) > 96
            or any(not isinstance(s,QuantizedSeam) for s in seams)):
        return PrecisionCheck(False,'no_bounded_reciprocal_seam_set')
    for seam in seams:
        if seam.tile_boundary is None:continue
        for polygon,coordinate in ((seam.source,seam.source_coordinate),(seam.target,seam.target_coordinate)):
            side=-1 if coordinate==seam.tile_boundary.lower_tile_maximum else 1
            offsets=[(p[seam.axis]-coordinate)*side for face,poly in zip(faces,polygon_ids)
                     if poly==polygon for p in face.vertices]
            if not offsets or min(offsets)<0 or max(offsets)<=0:
                return PrecisionCheck(False,'detail_polygon_disagrees_with_predicted_tile_side')
    attribution = None
    if original.reason=='overlapping_ground_faces':
        repeated = check_ground_coverage(footprint,faces,reference=reference,
            component=component,vertical_window=vertical_window)
        if repeated.candidate or repeated.reason!=original.reason:
            return PrecisionCheck(False,'original_overlap_failure_did_not_reproduce')
        attribution = attribute_seam_overlaps(footprint,faces,polygon_ids,seams,
            reference=reference,component=component,vertical_window=vertical_window)
        if not attribution.candidate:
            return PrecisionCheck(False,attribution.reason,overlap_attribution=attribution)
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
        return PrecisionCheck(False,'corrected_footprint_'+coverage.reason,coverage,seams=seams,
                              shifted_vertices=shifted,overlap_attribution=attribution)
    support = source_support(footprint,sources,corrected,maximum_z_difference=maximum_source_z_difference)
    return PrecisionCheck(support.candidate,'local_precision_diagnostic_only' if support.candidate else support.reason,
                          coverage,support,seams,shifted,overlap_attribution=attribution)
