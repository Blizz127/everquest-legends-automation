"""Bounded source-tread/riser contacts, distinct from collision-free flight.

These cells cover grounded intermediate treads and adjacent step transitions.
Only the exact local dry treads and bounded riser pieces are hypothesized foot
contacts. No static object or unrelated wall receives that exception. Client
contact/step behavior remains unverified; this module sends no input.
"""
from dataclasses import asdict
from fractions import Fraction as F
import math

from .bsp_clip import check_bsp_wedge
from .ground_sweep import area,clip,cross,hull
from .native_region_policy import NativeZeroRegionTrialPolicy
from .portal_precision import SourceFace
from .source_occupancy import clip_xyz,exact_floor_partition
from .source_stair_flight import stair_body_extent
from .source_stair_topology import audit_stair_topology
from .source_step import digest,patches,riser_link,vertices


def _dot(n,p):return sum(n[k]*p[k] for k in (0,1))


def _slab(polygon,normal,low,high):
    """Closed exact halfspaces, preserving point/line intersections."""
    result=polygon
    for sign,limit in ((1,low),(-1,-high)):
        before,result=result,[]
        if not before:return ()
        p=before[-1];old=sign*_dot(normal,p)-limit
        for q in before:
            new=sign*_dot(normal,q)-limit
            if (old>=0)!=(new>=0):
                t=old/(old-new);result.append(tuple(p[k]+t*(q[k]-p[k]) for k in (0,1)))
            if new>=0:result.append(q)
            p,old=q,new
        result=hull(result)
    return tuple(result)


def audit_stair_contacts(sources,static_sources,tread_ids,*,start,end,radius,body_radius,
                         body_height,source_wld_sha256,static_inventory_sha256,bsp,
                         region_policy,max_rise=2.,max_lift=4.,check_context=lambda:None,
                         progress=lambda _:None):
    if (type(region_policy) is not NativeZeroRegionTrialPolicy
            or type(static_sources) is not tuple or len(static_sources)>1024
            or not all(type(s) is SourceFace for s in static_sources)
            or not all(type(v) in (int,float) and math.isfinite(v)
                for v in (body_radius,body_height,max_lift))
            or not 0<body_radius<=radius or not 0<body_height<=100 or not 0<max_lift<=4):
        raise ValueError('Explicit bounded contact body and installed region policy required')
    policy_record=region_policy.record()
    def check():
        check_context()
        region_policy.check_context(zone='crushbone',pins=(region_policy.mesh_sha256,
            region_policy.archive_sha256,source_wld_sha256,static_inventory_sha256),bsp=bsp)
        if region_policy.record()!=policy_record:raise ValueError('Stair contact policy changed')
    check()
    topology=audit_stair_topology(sources,tread_ids,start=start,end=end,radius=radius,
        max_rise=max_rise,check_context=check)
    record=dict(kind='bounded_source_stair_contacts',topology=topology,
        source_wld_sha256=source_wld_sha256,static_inventory_sha256=static_inventory_sha256,
        static_geometry_sha256=digest([asdict(s) for s in static_sources]),region_policy=policy_record,
        body_radius=body_radius,body_height=body_height,max_lift=max_lift,
        candidate=False,phases=[],states=[],input_authorized=False,real_client_accepted=False,
        executable_itinerary=False,floor_lineage_adopted=False,
        contact_semantics_verified=False,client_step_capability_verified=False,
        dynamic_obstacles_checked=False)
    def refuse(reason):return dict(record,reason=reason)
    if not topology['topology_candidate']:return refuse(topology['reason'])
    combined=sources+static_sources
    inventory={(s.fragment,s.face):s for s in combined}
    if len(inventory)!=len(combined):return refuse('duplicate_terrain_or_static_source_identity')
    extent=stair_body_extent(start,end,radius)
    # The existing 16-sided motion envelope circumscribes the body circle.
    # Its body contribution fits this square; remaining width is for centers.
    body=F(math.nextafter(body_radius/math.cos(math.pi/16),math.inf))
    centers=extent-body
    if centers<=0:return refuse('checked_radius_leaves_no_center_corridor')
    first,last=tuple(map(F,start)),tuple(map(F,end))
    delta=tuple(last[k]-first[k] for k in (0,1))
    square=lambda p,r:hull((p[0]+dx,p[1]+dy) for dx in (-r,r) for dy in (-r,r))
    corridor=hull((*square(first,extent),*square(last,extent)))
    center_corridor=hull((*square(first,centers),*square(last,centers)))
    supports=[patches(ids,inventory,corridor) for ids in tread_ids]
    if not exact_floor_partition(corridor,tuple(p for group in supports for _,_,p,_ in group)):
        return refuse('expanded_contact_corridor_support_gap')
    heights=[F(t['height_exact']) for t in topology['treads']]
    for p,group in ((first,supports[0]),(last,supports[-1])):
        if not exact_floor_partition(square(p,extent),tuple(poly for _,_,poly,_ in group)):
            return refuse('contact_endpoint_not_wholly_supported')
    normal=None;planes=[];links=[]
    for i,(before,after) in enumerate(zip(supports,supports[1:])):
        check()
        lower,upper=(before,after) if heights[i]<heights[i+1] else (after,before)
        link=riser_link(lower,upper,corridor,sources,F(max_rise))
        if link is None:return refuse('expanded_contact_riser_missing')
        points=sorted({p[:2] for key in link['riser_ids'] for p in vertices(inventory[tuple(key)])})
        a,b=points[0],points[-1]
        n=(a[1]-b[1],b[0]-a[0])
        if a==b or any(cross(a,b,p)!=0 for p in points):return refuse('riser_not_one_vertical_plane')
        if _dot(n,delta)<0:n=tuple(-v for v in n)
        if _dot(n,delta)<=0:return refuse('contact_flight_parallel_to_riser')
        if normal is None:normal=n
        if normal[0]*n[1]!=normal[1]*n[0]:return refuse('contact_risers_not_parallel')
        c=_dot(normal,a)
        if planes and c<=planes[-1]:return refuse('contact_risers_not_in_progress_order')
        planes.append(c)
        links.append((link,min(heights[i:i+2]),max(heights[i:i+2]),c))
    q0,q1=_dot(normal,first),_dot(normal,last)
    reach=extent*sum(abs(v) for v in normal)
    cuts={q0,q1}
    for c in planes:
        cuts.update(q for q in (c-reach,c,c+reach) if q0<q<q1)
    # Also bound long outer-tread cells; no runtime pulse length is reduced.
    count=max(1,math.ceil(math.dist(start,end)/4.))
    cuts.update(q0+(q1-q0)*F(i,count) for i in range(1,count))
    cuts=sorted(cuts)
    if len(cuts)>129:return refuse('contact_cell_budget_exceeded')
    point=lambda q:tuple(first[k]+(q-q0)/(q1-q0)*delta[k] for k in (0,1))
    exact_sources=[(s,vertices(s)) for s in combined]
    static_ids={(s.fragment,s.face) for s in static_sources}
    record.update(center_corridor_exact=[[str(v) for v in p] for p in center_corridor],
        body_half_extent_exact=str(body),exact_body_half_extent=str(extent),
        center_half_extent_exact=str(centers),normal_exact=[str(v) for v in normal],
        contact_risers=[link for link,_,_,_ in links])
    for i,group in enumerate(supports):
        record['states'].append(dict(index=len(record['states']),kind='ground',treads=[i],
            height_interval_exact=[str(heights[i])]*2,source_ids=tread_ids[i],
            center_polygons_exact=[[[str(v) for v in p] for p in hull(polygon)] for _,_,polygon,_ in group]))
    body_reach=body*sum(abs(v) for v in normal)
    for i,(link,low,high,c) in enumerate(links):
        strip=_slab(center_corridor,normal,c-body_reach,c+body_reach)
        if not strip:return refuse('adjacent_contact_strip_missing')
        record['states'].append(dict(index=len(record['states']),kind='transition',treads=[i,i+1],
            height_interval_exact=[str(low),str(high)],source_ids=link['riser_ids'],
            center_polygons_exact=[[[str(v) for v in p] for p in strip]]))
    for index,(qa,qb) in enumerate(zip(cuts,cuts[1:])):
        check();a,b=point(qa),point(qb)
        boundary=hull((*square(a,extent),*square(b,extent)))
        center_boundary=hull((*square(a,centers),*square(b,centers)))
        local_treads={key:h for h,group in zip(heights,supports) for key,points,_,_ in group
                      if clip_xyz(points,boundary)}
        if not local_treads:return refuse('contact_cell_without_source_support')
        low,high=min(local_treads.values()),max(local_treads.values())
        if high-low>F(max_lift):return refuse('contact_cell_vertical_span_exceeded')
        if not exact_floor_partition(boundary,tuple(poly for group in supports for key,_,poly,_ in group
                                                   if key in local_treads)):
            return refuse('contact_cell_projected_support_gap')
        collision_low=low-F(.1)-F(.01);collision_high=high+F(body_height)+F(.01)
        phase=dict(index=index,kind='ground_contact',start_exact=[str(v) for v in a],
            end_exact=[str(v) for v in b],base_interval_exact=[str(low),str(high)],
            footprint_exact=[[str(v) for v in p] for p in boundary],
            center_footprint_exact=[[str(v) for v in p] for p in center_boundary],
            collision_band_exact=[str(collision_low),str(collision_high)],
            region_band_exact=[str(low),str(collision_high)],terrain_static_clear=False,
            conditional_contacts=[],source_classifications=[])
        record['phases'].append(phase);seen=0
        for source,points in exact_sources:
            patch=clip_xyz(points,boundary)
            if not patch:continue
            seen+=1
            if seen>128:return refuse('contact_cell_source_budget_exceeded')
            key=(source.fragment,source.face);classification=None
            if key not in static_ids and key in local_treads:
                if any(p[2]!=local_treads[key] for p in patch):return refuse('contact_tread_height_changed')
                classification='conditional_tread_contact'
            if (classification is None and key not in static_ids
                    and source.flag==0 and source.material_class=='Diffuse'):
                for link,lower,upper,c in links:
                    axis=link['along_axis'];left,right=map(F,link['along_bounds'])
                    if (key in tuple(map(tuple,link['riser_ids']))
                            and all(_dot(normal,p)==c and left<=p[axis]<=right
                                    and lower<=p[2]<=upper for p in patch)
                            and low<=lower<upper<=high):
                        classification='conditional_riser_contact';break
            if classification is not None:
                phase['conditional_contacts'].append(dict(source_id=key,kind=classification,
                    heights_exact=[str(min(p[2] for p in patch)),str(max(p[2] for p in patch))]))
            elif max(p[2] for p in patch)<collision_low:classification='below'
            elif min(p[2] for p in patch)>collision_high:classification='above'
            else:
                phase['obstruction']=dict(source_id=key,static=key in static_ids,
                    heights_exact=[str(min(p[2] for p in patch)),str(max(p[2] for p in patch))])
                return refuse('noncontact_source_intersects_stair_body')
            phase['source_classifications'].append(dict(source_id=key,classification=classification))
        phase['terrain_static_clear']=True
        old=check_bsp_wedge(bsp,tuple((y,x) for x,y in boundary),(0,0,low),(0,0,collision_high))
        native=region_policy.classifier.classify_convex_enclosure_after_bounds(
            tuple((y,x,z) for x,y in boundary for z in (low,collision_high)))
        phase.update(bsp=asdict(old),native=asdict(native))
        if not old.candidate and old.reason!='missing_bsp_child':return refuse('contact_bsp_'+old.reason)
        if (not native.complete or not native.possible_classes
                or any(c.flags!=0 or c.class_id!=0 for c in native.possible_classes)):
            return refuse('contact_nonzero_or_unresolved_native_regions')
        progress(record)
    check()
    record.update(candidate=True,reason='conditional_bounded_stair_contacts_only',
        phase_count=len(record['phases']),full_body_clearance_checked=True,
        static_objects_checked=True,bsp_regions_checked=True,conditional_native_zero_policy=True)
    return record
