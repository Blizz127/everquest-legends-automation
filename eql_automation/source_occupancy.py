"""Conditional vertical occupancy around an explicitly selected source floor.

This is an offline geometry diagnostic. A selection hash binds a caller's
hypothesis; this module cannot prove that floor was reached from G0, measure
the player's body, or establish that placed objects/dynamics were supplied.
Existing complete-source support and real-input gates remain unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math
import re

from .ground_sweep import GroundFace,area,check_ground_coverage,clip,cross,finite,hull
from .portal_precision import SourceFace,plane


@dataclass(frozen=True)
class FaceOccupancy:
    identifier: tuple[int,int]
    classification: str
    minimum_above_floor: float | None = None
    maximum_above_floor: float | None = None


@dataclass(frozen=True)
class SourceOccupancy:
    candidate: bool
    reason: str
    selected_ids: tuple[tuple[int,int], ...] = ()
    selection_evidence_sha256: str = ''
    faces: tuple[FaceOccupancy, ...] = ()
    hypothetical_body_height: float | None = None
    supporting_floor_selection_verified: bool = False
    full_collision_inventory_verified: bool = False
    real_client_accepted: bool = False
    input_authorized: bool = False


def clip_xyz(subject,boundary):
    """Clip XYZ polygons/segments by vertical XY halfspaces, retaining Z."""
    if not boundary:return ()
    result=list(subject)
    for i,a in enumerate(boundary):
        b=boundary[(i+1)%len(boundary)]
        source,result=result,[]
        if not source:break
        previous=source[-1];old=cross(a,b,previous)
        for point in source:
            new=cross(a,b,point)
            if (new>=0)!=(old>=0):
                t=old/(old-new)
                result.append(tuple(previous[k]+t*(point[k]-previous[k]) for k in range(3)))
            if new>=0:result.append(point)
            previous,old=point,new
    return tuple(result)


def exact_floor_partition(boundary,polygons):
    """No uncovered sliver may hide an obstacle's unclassified projection.

    Rational arithmetic treats the supplied finite float coordinates exactly.
    A finite union of closed triangles with no positive-area overlaps and the
    same area as the closed convex boundary covers that boundary, including
    line/point projections. This is independent of the ground check's area
    tolerance and is small because selection is bounded to 32 triangles.
    """
    convert=lambda polygon:tuple(tuple(Fraction(n) for n in p) for p in polygon)
    target=convert(boundary)
    patches=[]
    for polygon in polygons:
        # Clip the small footprint by the triangle's three halfspaces. The
        # intersection is identical, but clipping a large source triangle
        # successively by many near-parallel footprint edges creates very
        # large intermediate rational denominators.
        patch=clip(target,convert(polygon))
        if area(patch)>0:patches.append(patch)
    if sum(area(p) for p in patches)!=area(target):return False
    return all(area(clip(a,b))==0 for i,a in enumerate(patches) for b in patches[:i])


def check_selected_floor_clearance(footprint,sources,*,selected_ids,selection_evidence_sha256,
                                   body_height,below_clearance=.1,numeric_margin=.01):
    """Classify all supplied faces relative to the selected floor partition.

    No face is discarded by nearest Z, material, winding or zero XY area.
    Body/below bounds are explicit hypotheses, not calibration. Every selected
    ground patch must be present, dry, continuous and cover the expanded cell.
    """
    def result(ok,reason,faces=()):
        return SourceOccupancy(ok,reason,selected_ids,selection_evidence_sha256,tuple(faces),body_height)
    if (not isinstance(footprint,tuple) or not 3<=len(footprint)<=64
            or any(not isinstance(p,tuple) or len(p)!=2 or not all(finite(n) for n in p) for p in footprint)
            or not isinstance(sources,tuple) or not 1<=len(sources)
            or not isinstance(selected_ids,tuple) or not 1<=len(selected_ids)<=32
            or any(not isinstance(k,tuple) or len(k)!=2 or any(type(n) is not int or n<0 for n in k) for k in selected_ids)
            or len(set(selected_ids))!=len(selected_ids)
            or not isinstance(selection_evidence_sha256,str) or re.fullmatch('[0-9a-f]{64}',selection_evidence_sha256) is None
            or not all(finite(n) and n>0 for n in (body_height,below_clearance,numeric_margin))
            or body_height>100 or below_clearance>10 or not .001<=numeric_margin<=.1):
        return result(False,'invalid_floor_selection_or_body_hypothesis')
    if len(sources)>128:
        return result(False,'complete_source_budget_exceeded')
    boundary=hull(footprint)
    if len(boundary)!=len(footprint) or area(boundary)<=1e-7:
        return result(False,'footprint_not_convex')
    expanded=hull((x+dx,y+dy) for x,y in boundary for dx in (-.002,.002) for dy in (-.002,.002))
    inventory={}
    for source in sources:
        if (not isinstance(source,SourceFace) or len(source.vertices_wld)!=3
                or any(len(p)!=3 or not all(finite(n) for n in p) for p in source.vertices_wld)
                or type(source.fragment) is not int or type(source.face) is not int
                or source.fragment<0 or source.face<0 or (source.fragment,source.face) in inventory):
            return result(False,'invalid_or_duplicate_source_identity')
        inventory[source.fragment,source.face]=source
    if not set(selected_ids)<=inventory.keys():
        return result(False,'selected_floor_missing_from_inventory')
    selected=[]
    for key in selected_ids:
        source=inventory[key]
        vertices=tuple((y,x,z) for x,y,z in source.vertices_wld)
        polygon=hull(p[:2] for p in vertices)
        surface=plane(vertices)
        if (source.flag!=0 or source.material_class!='Diffuse' or surface is None
                or math.hypot(*surface[:2])>1. or len(polygon)!=3):
            return result(False,'selected_floor_not_supported_ground')
        selected.append((vertices,polygon,surface))
    center=tuple(sum(p[k] for p in expanded)/len(expanded) for k in range(2))
    heights=[surface[2](center) for _,poly,surface in selected
             if all(cross(a,poly[(i+1)%3],center)>=-1e-10 for i,a in enumerate(poly))]
    if not heights or max(heights)-min(heights)>1e-6:
        return result(False,'selected_floor_reference_ambiguous')
    window=max(abs(p[2]-heights[0]) for vertices,_,_ in selected for p in vertices)+1.
    coverage=check_ground_coverage(expanded,tuple(GroundFace(v,63,0) for v,_,_ in selected),
        reference=(*center,heights[0]),component=0,vertical_window=window,height_tolerance=1e-6,max_faces=128)
    if not coverage.candidate:
        return result(False,'selected_floor_'+coverage.reason)
    if not exact_floor_partition(expanded,tuple(poly for _,poly,_ in selected)):
        return result(False,'selected_floor_exact_partition_failed')
    classified=[]
    for key,source in inventory.items():
        if key in selected_ids:continue
        vertices=tuple((y,x,z) for x,y,z in source.vertices_wld)
        patch=clip_xyz(vertices,expanded)
        if not patch:
            classified.append(FaceOccupancy(key,'outside_expanded_footprint'));continue
        differences=[]
        for _,poly,surface in selected:
            pieces=clip_xyz(patch,poly)
            differences.extend(p[2]-surface[2](p) for p in pieces)
        if not differences:
            return result(False,'other_surface_over_uncovered_floor',classified)
        low,high=min(differences),max(differences)
        if low>body_height+numeric_margin:kind='overhead'
        elif high< -below_clearance-numeric_margin:kind='below'
        else:
            classified.append(FaceOccupancy(key,'intersects_or_touches_body_band',low,high))
            return result(False,'other_source_surface_intersects_body_band',classified)
        classified.append(FaceOccupancy(key,kind,low,high))
    return result(True,'conditional_selected_floor_occupancy_only',classified)
