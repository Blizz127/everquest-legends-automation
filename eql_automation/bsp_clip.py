"""Exact closed-polyhedron BSP traversal for vertical floor/body wedges.

Child volumes are intersected with every ancestor halfspace. A clipped face,
edge or point remains present: boundary contact still visits both children.
No missing child, absent region or copied hazard label is reclassified here.
"""
from dataclasses import dataclass
from fractions import Fraction

from .bsp_volume import BspVolumeView, rational_number
from .ground_sweep import area, hull


@dataclass(frozen=True)
class ClippedBspResult:
    candidate: bool
    reason: str
    visits: int
    region_ids: tuple = ()
    labelled_regions: tuple = ()
    refused_node: int | None = None
    refused_vertices_exact: tuple = ()
    conservative_unclipped_traversal: bool = False
    exact_closed_clipping: bool = True
    input_authorized: bool = False
    real_client_accepted: bool = False


def _vertices(faces):
    return tuple(sorted({p for face in faces for p in face}))


def _distance(plane, point):
    return sum(a*b for a,b in zip(plane[:3],point))+plane[3]


def _clip(faces, plane, sign):
    """Intersect a face representation with sign*distance >= 0 exactly."""
    kept = []; cuts = set()
    for face in faces:
        polygon = []
        previous = face[-1]; old = sign*_distance(plane,previous)
        for point in face:
            new = sign*_distance(plane,point)
            if (new >= 0) != (old >= 0):
                t = old/(old-new)
                hit = tuple(previous[k]+t*(point[k]-previous[k]) for k in range(3))
                polygon.append(hit); cuts.add(hit)
            if new >= 0:
                polygon.append(point)
                if new == 0: cuts.add(point)
            previous,old = point,new
        # Consecutive duplicates arise at closed-boundary contacts. Preserve
        # one/two-point faces; they can reach an unknown or labelled child.
        clean = []
        for point in polygon:
            if not clean or point != clean[-1]: clean.append(point)
        if len(clean)>1 and clean[0]==clean[-1]: clean.pop()
        if clean: kept.append(tuple(clean))
    if cuts:
        axis = max(range(3),key=lambda k:abs(plane[k]))
        if not plane[axis]:
            # A zero plane either kept everything or nothing; it creates no
            # cap. The caller retains both branches when distance is zero.
            return tuple(kept)
        others = tuple(k for k in range(3) if k!=axis)
        projection = {(p[others[0]],p[others[1]]):p for p in cuts}
        boundary = tuple(sorted(projection)) if len(projection)<=2 else hull(projection)
        kept.append(tuple(projection[p] for p in boundary))
    # Duplicate coincident faces do not affect coverage, but removing them
    # controls degenerate surface propagation through several touching planes.
    unique = {}
    for face in kept:
        unique.setdefault(tuple(sorted(set(face))),face)
    return tuple(unique.values())


def check_bsp_wedge(view, xy_wld, lower_plane, upper_plane, *,
                    max_visits=4096, max_depth=256, max_vertices=256):
    """Classify z between two affine planes over a convex raw-WLD polygon.

    Planes are (dx,dy,offset), with z=dx*x+dy*y+offset. They must leave
    positive height everywhere. The constructed polyhedron is convex; face
    clipping preserves its exact intersection, including degenerate contacts.
    """
    if (not isinstance(view,BspVolumeView) or not isinstance(xy_wld,tuple)
            or not 3<=len(xy_wld)<=128
            or any(not isinstance(p,tuple) or len(p)!=2 for p in xy_wld)
            or any(not isinstance(p,tuple) or len(p)!=3 for p in (lower_plane,upper_plane))
            or type(max_visits) is not int or not 1<=max_visits<=4096
            or type(max_depth) is not int or not 1<=max_depth<=256
            or type(max_vertices) is not int or not 4<=max_vertices<=1024):
        raise ValueError('Invalid clipped BSP wedge request')
    xy = tuple(tuple(rational_number(v) for v in p) for p in xy_wld)
    boundary = hull(xy)
    if len(boundary)!=len(xy) or area(boundary)<=0:
        raise ValueError('BSP wedge needs a convex nonzero footprint')
    lo,hi = (tuple(rational_number(v) for v in plane) for plane in (lower_plane,upper_plane))
    lower = tuple((x,y,lo[0]*x+lo[1]*y+lo[2]) for x,y in boundary)
    upper = tuple((x,y,hi[0]*x+hi[1]*y+hi[2]) for x,y in boundary)
    if any(a[2]>=b[2] for a,b in zip(lower,upper)):
        raise ValueError('BSP wedge needs strictly positive height')
    faces = (lower,upper)+tuple((a,lower[(i+1)%len(lower)],upper[(i+1)%len(lower)],upper[i])
                               for i,a in enumerate(lower))
    stack = [(1,frozenset(),faces)]
    visits = 0; regions = set(); labelled = []
    def result(ok,reason,number=None,vertices=()):
        return ClippedBspResult(ok,reason,visits,tuple(sorted(regions)),tuple(labelled),
            number,tuple(tuple(str(v) for v in p) for p in vertices))
    while stack:
        if visits>=max_visits:
            return result(False,'bsp_volume_visit_budget_exceeded')
        number,ancestry,faces = stack.pop(); visits+=1
        vertices = _vertices(faces)
        if not vertices:
            return result(False,'unexpected_empty_bsp_child_volume',number)
        if len(vertices)>max_vertices or len(faces)>max_vertices:
            return result(False,'bsp_clipped_geometry_budget_exceeded',number)
        if any(v.numerator.bit_length()>16384 or v.denominator.bit_length()>16384
               for p in vertices for v in p):
            return result(False,'bsp_clipped_arithmetic_budget_exceeded',number)
        if number==0:
            return result(False,'missing_bsp_child',number,vertices)
        if number in ancestry:
            return result(False,'bsp_volume_cycle',number,vertices)
        if len(ancestry)>=max_depth:
            return result(False,'bsp_volume_depth_budget_exceeded',number,vertices)
        nx,ny,nz,split,region,left,right = view.nodes[number-1]
        if left==right==0:
            if not region: return result(False,'bsp_leaf_has_no_region',number,vertices)
            region-=1; regions.add(region)
            if view.labels[region]:
                labelled.append((region,view.labels[region]))
                return result(False,'labelled_bsp_volume',number,vertices)
            continue
        plane = (nx,ny,nz,split)
        values = tuple(_distance(plane,p) for p in vertices)
        low,high = min(values),max(values); seen = ancestry|{number}
        if low>0:
            stack.append((left,seen,faces))
        elif high<0:
            stack.append((right,seen,faces))
        else:
            stack.append((right,seen,_clip(faces,plane,-1)))
            stack.append((left,seen,_clip(faces,plane,1)))
    return result(True,'copied_clipped_bsp_wedge_candidate_only')
