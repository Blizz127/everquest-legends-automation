"""Conditional lift/transfer/settle diagnostics for an explicit source riser.

Ordinary floor continuity is unchanged. This checks a separate kinematic
hypothesis and returns a distinctly labelled landing linked to the old prefix.
It neither establishes client step capability nor authorizes input.
"""
from dataclasses import asdict,dataclass,replace
from fractions import Fraction
from hashlib import sha256
import json
import math

from .bsp_floor_guard import outward_float
from .ground_sweep import area,clip,cross,finite,hull
from .portal_precision import SourceFace
from .source_detour import swept_square
from .source_floor_chain import SourceFloorChain,exact_plane,rational
from .source_occupancy import check_selected_floor_clearance,clip_xyz,exact_floor_partition
from .static_floor_guard import check_source_static_floor


def digest(value):
    return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def expanded(footprint):
    return rational(hull((x+dx,y+dy) for x,y in footprint
                         for dx in (-.002,.002) for dy in (-.002,.002)))


def vertices(source):
    return rational(tuple((y,x,z) for x,y,z in source.vertices_wld))


def patches(ids,inventory,boundary):
    result=[]
    for key in ids:
        points=vertices(inventory[key]);polygon=hull(p[:2] for p in points)
        patch=clip(boundary,polygon)
        if area(patch)>0:
            a,b,c=exact_plane(points)
            result.append((key,points,patch,tuple(a*x+b*y+c for x,y in patch)))
    return result


def riser_link(lower,upper,boundary,sources,max_rise):
    """Match a straight, possibly split source edge and its full vertical wall."""
    for low_id,low_points,_,_ in lower:
        for i in range(3):
            a,b=low_points[i],low_points[(i+1)%3]
            if a[:2]==b[:2]:continue
            axis=0 if abs(b[0]-a[0])>=abs(b[1]-a[1]) else 1
            low_side=cross(a,b,low_points[(i+2)%3])
            if not low_side:continue
            # The whole footprint's intersection with this infinite line
            # must fit within both source edge projections.
            cuts=[]
            for j,p in enumerate(boundary):
                q=boundary[(j+1)%len(boundary)];v,w=cross(a,b,p),cross(a,b,q)
                if v==0:cuts.append(p)
                if v*w<0:
                    t=v/(v-w);cuts.append(tuple(p[k]+t*(q[k]-p[k]) for k in range(2)))
            if len(set(cuts))<2:continue
            left,right=min(p[axis] for p in cuts),max(p[axis] for p in cuts)
            if not min(a[axis],b[axis])<=left<right<=max(a[axis],b[axis]):continue
            if any(cross(a,b,p)*low_side<0 for _,_,patch,_ in lower for p in patch):continue
            for high_id,high_points,_,_ in upper:
                for j in range(3):
                    c,d=high_points[j],high_points[(j+1)%3]
                    if (c[axis]==d[axis] or cross(a,b,c)!=0 or cross(a,b,d)!=0
                            or not min(c[axis],d[axis])<=left<right<=max(c[axis],d[axis])
                            or cross(a,b,high_points[(j+2)%3])*low_side>=0):continue
                    if any(cross(a,b,p)*low_side>0 for _,_,patch,_ in upper for p in patch):continue
                    z=lambda p,q,s:p[2]+(q[2]-p[2])*(s-p[axis])/(q[axis]-p[axis])
                    lows=(z(a,b,left),z(a,b,right));highs=(z(c,d,left),z(c,d,right))
                    rises=tuple(h-l for l,h in zip(lows,highs))
                    if not all(0<r<=max_rise for r in rises):continue
                    wall=hull(((left,lows[0]),(right,lows[1]),(right,highs[1]),(left,highs[0])))
                    risers=[];ids=[]
                    for source in sources:
                        pts=vertices(source)
                        if any(cross(a,b,p)!=0 for p in pts):continue
                        poly=hull((p[axis],p[2]) for p in pts)
                        if area(poly)>0 and area(clip(wall,poly))>0:
                            risers.append(poly);ids.append((source.fragment,source.face))
                    if exact_floor_partition(wall,risers):
                        return dict(lower_face=low_id,upper_face=high_id,riser_ids=ids,
                            along_axis=axis,along_bounds=[str(left),str(right)],
                            lower_heights=[str(v) for v in lows],upper_heights=[str(v) for v in highs],
                            rises=[str(v) for v in rises])
    return None


@dataclass(frozen=True)
class StepTransfer:
    candidate: bool
    reason: str
    evidence: dict
    transition_sha256: str = ''
    landing_proof_sha256: str = ''
    conditional_kinematic_hypothesis: bool = True
    client_step_capability_verified: bool = False
    bsp_classified: bool = False
    input_authorized: bool = False
    real_client_accepted: bool = False


def check_source_step(prefix,start,end,terrain_view,static_view,*,landing_seed_ids,
                      radius,max_step_height,max_lift,lift_clearance=.125):
    if (not isinstance(prefix,SourceFloorChain) or prefix.halted or prefix.previous is None
            or any(not isinstance(p,tuple) or len(p)!=2 or not all(finite(v) for v in p) for p in (start,end))
            or not all(finite(v) for v in (radius,max_step_height,max_lift,lift_clearance))
            or not .05<=radius<=10 or not 0<max_step_height<=4 or not max_step_height<=max_lift<=8
            or not .11<lift_clearance<=.5 or not 0<math.dist(start,end)<=20):
        raise ValueError('Invalid bounded source-step hypothesis')
    if getattr(terrain_view,'wld_sha256',None)!=prefix.inventory_sha256:
        raise ValueError('Source-step inventory differs from the floor prefix')
    first=swept_square(start,start,radius);last=swept_square(end,end,radius)
    sweep=swept_square(start,end,radius);boundary=expanded(sweep)
    evidence=dict(parent_proof_sha256=prefix.previous.proof_sha256,
        source_wld_sha256=prefix.inventory_sha256,static_inventory_sha256=getattr(static_view,'inventory_sha256',None),
        start=start,end=end,radius=radius,body_height=prefix.body_height,max_step_height=max_step_height,
        max_lift=max_lift,lift_clearance=lift_clearance,footprint=sweep)
    def refuse(reason):return StepTransfer(False,reason,evidence),None
    if prefix._expanded!=expanded(first):return refuse('source_step_needs_committed_start_cap')
    try:
        lower_sources=terrain_view.source_faces_for_footprint(first)
        lower=prefix.fork();low_step=lower.advance(first,lower_sources)
        if not low_step.candidate:return refuse('lower_'+low_step.reason)
        low_static=check_source_static_floor(low_step,first,lower_sources,static_view)
        if not low_static.candidate:return refuse('lower_'+low_static.reason)
        upper_sources=terrain_view.source_faces_for_footprint(last)
        upper=SourceFloorChain(inventory_sha256=prefix.inventory_sha256,
            seed_evidence_sha256=digest({'parent':prefix.previous.proof_sha256,'proposed_landing':landing_seed_ids}),
            seed_ids=landing_seed_ids,body_height=prefix.body_height)
        high_step=upper.advance(last,upper_sources)
        if not high_step.candidate:return refuse('landing_'+high_step.reason)
        high_static=check_source_static_floor(high_step,last,upper_sources,static_view)
        if not high_static.candidate:return refuse('landing_'+high_static.reason)
        sources=terrain_view.source_faces_for_footprint(sweep)
        static=static_view.faces_for_footprint(sweep)
        all_faces=sources+static
        inventory={}
        if not 1<=len(all_faces)<=256:return refuse('source_step_inventory_budget')
        for face in all_faces:
            if (not isinstance(face,SourceFace) or len(face.vertices_wld)!=3
                    or any(len(p)!=3 or not all(finite(v) for v in p) for p in face.vertices_wld)
                    or (face.fragment,face.face) in inventory):return refuse('invalid_step_source_inventory')
            inventory[face.fragment,face.face]=face
        selected=(*low_step.selected_ids,*high_step.selected_ids)
        if len(set(selected))!=len(selected):return refuse('step_supports_are_not_distinct')
        if not set(selected)<=inventory.keys():return refuse('step_support_missing_from_sweep')
        for face in (*lower_sources,*upper_sources):
            key=(face.fragment,face.face)
            if key in inventory and face!=inventory[key]:return refuse('step_source_identity_changed')
        low_patches=patches(low_step.selected_ids,inventory,boundary)
        high_patches=patches(high_step.selected_ids,inventory,boundary)
        if not exact_floor_partition(boundary,tuple(hull(p[:2] for p in pts)
                for _,pts,_,_ in (*low_patches,*high_patches))):return refuse('step_support_partition_failed')
        link=riser_link(low_patches,high_patches,boundary,sources,Fraction(max_step_height))
        direction='up'
        if link is None:
            link=riser_link(high_patches,low_patches,boundary,sources,Fraction(max_step_height))
            direction='down'
        if link is None:return refuse('complete_bounded_source_riser_not_found')
        evidence['riser']=link;evidence['direction']=direction
        heights=tuple(z for _,_,_,zs in (*low_patches,*high_patches) for z in zs)
        transfer=max(heights)+Fraction(lift_clearance)
        endpoint_min=[]
        for footprint,step in ((first,low_step),(last,high_step)):
            endpoint_min.append(min(z for _,_,_,zs in patches(step.selected_ids,inventory,expanded(footprint)) for z in zs))
        lifts=tuple(transfer-z for z in endpoint_min)
        evidence.update(transfer_height_exact=str(transfer),endpoint_max_lifts=[str(v) for v in lifts])
        if any(not 0<=v<=Fraction(max_lift) for v in lifts):return refuse('step_lift_bound_exceeded')
        for name,footprint,step,terrain,delta in (('lift',first,low_step,lower_sources,lifts[0]),
                                                 ('settle',last,high_step,upper_sources,lifts[1])):
            phase=check_selected_floor_clearance(footprint,terrain+static_view.faces_for_footprint(footprint),
                selected_ids=step.selected_ids,selection_evidence_sha256=step.proof_sha256,
                body_height=outward_float(Fraction(prefix.body_height)+delta,lower=False))
            evidence[name]=asdict(phase)
            if not phase.candidate:return refuse(name+'_'+phase.reason)
        band=(transfer-Fraction(.1)-Fraction(.01),transfer+Fraction(prefix.body_height)+Fraction(.01))
        classified=[]
        for face in all_faces:
            patch=clip_xyz(vertices(face),boundary)
            kind='outside'
            if patch:
                low,high=min(p[2] for p in patch),max(p[2] for p in patch)
                kind='below' if high<band[0] else 'above' if low>band[1] else 'intersects'
            classified.append(dict(identifier=(face.fragment,face.face),classification=kind))
            if kind=='intersects':
                evidence['transfer_faces']=classified;return refuse('step_transfer_body_band_intersection')
        evidence.update(transfer_faces=classified,transfer_band_exact=[str(v) for v in band],
            geometry_sha256=digest({'footprint':sweep,'terrain':[asdict(s) for s in sources],
                                    'static':[asdict(s) for s in static]}),
            lower_endpoint=asdict(low_step),landing_endpoint=asdict(high_step))
        transition=digest(evidence)
        # A step is explicitly represented instead of inventing an equal-edge
        # FloorJoin. Its certificate binds both the old prefix and new support.
        landing=replace(high_step,reason='conditional_step_landing_only',index=prefix.index,
                        carried_ids=(),joins=(),previous_sha256=prefix.previous.proof_sha256,proof_sha256='')
        landing=replace(landing,proof_sha256=digest({'step_transition':transition,'landing':asdict(landing)}))
        continued=prefix.fork();continued.previous=landing;continued.index=prefix.index+1
        continued._expanded=upper._expanded;continued._selected=upper._selected.copy()
        return StepTransfer(True,'conditional_lift_transfer_settle_only',evidence,transition,landing.proof_sha256),continued
    except (KeyError,ValueError,TypeError,ZeroDivisionError,OverflowError) as error:
        evidence['error_type']=type(error).__name__
        return refuse('source_step_geometry_refused')
