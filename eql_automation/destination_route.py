"""A fresh-start destination corridor with incrementally checked geometry.

The initial floor/body footprint is proved by CurrentStartPlanner. Reciprocal
dry mesh topology supplies a proposed suffix; each future movement still needs
RouteGeometryPreparer and receipt-bound RouteFloorCommit. Planning does not
certify whole-route clearance, turn a map label into a zone trigger, or send input.
"""
from dataclasses import replace
from hashlib import sha256
import json
import math
import time

from .current_route_start import CurrentStartPlanner, CurrentStartPlan, encoded
from .fixed_route_follower import FixedRoute, FixedSegment
from .ground_binding import GroundGeometryEvidence, finite, integer
from .ground_observer import RouteGroundObserver
from .portal_surface_audit import _supported_detail_height


def crossing_on_portal(xy, edge):
    if (len(edge)!=3 or any(len(p)!=3 or not all(finite(v) for v in p) for p in edge[1:])):
        return False
    a,b=edge[1:];dx,dy=b[0]-a[0],b[1]-a[1]
    length2=dx*dx+dy*dy
    if not finite(length2) or length2<=0:return False
    t=((xy[0]-a[0])*dx+(xy[1]-a[1])*dy)/length2
    nearest=(a[0]+min(1.,max(0.,t))*dx,a[1]+min(1.,max(0.,t))*dy)
    return math.dist(xy,nearest)<=.0005


def corridor_points(mesh,polygons,portals,start,goal,check):
    """Choose connected portal targets; do not assert future body clearance.

    Every candidate belongs to both directed portals and both detail surfaces.
    Dynamic programming avoids tiny endpoint legs where a different crossing
    can resolve them. The authoritative collision check remains per movement.
    """
    states=[(0.,(start[:2],),(),start[2])]
    checks=0
    for index,polygon in enumerate(polygons):
        candidates=[]
        if index==len(polygons)-1:
            candidates=[(goal[:2],goal[2],goal[2],None)]
        else:
            portal=portals[index];a,b=portal['forward'][1:]
            for fraction in (.5,.4,.6,.3,.7,.2,.8):
                xy=tuple(float((1-fraction)*a[k]+fraction*b[k]) for k in (0,1))
                if not all(crossing_on_portal(xy,portal[key]) for key in ('forward','reverse')):
                    continue
                left=_supported_detail_height(mesh,polygon,*xy)
                right=_supported_detail_height(mesh,polygons[index+1],*xy)
                if left is not None and right is not None and abs(left-right)<=.25:
                    candidates.append((xy,left,right,fraction))
        following=[]
        for xy,z,next_z,fraction in candidates:
            best=None
            for cost,path,fractions,previous_z in states:
                length=math.dist(path[-1],xy);checks+=1
                if length<=.5 or abs(z-previous_z)>length:continue
                middle=tuple((path[-1][k]+xy[k])/2 for k in (0,1))
                if _supported_detail_height(mesh,polygon,*middle) is None:continue
                value=(cost+length,path+(xy,),fractions+(() if fraction is None else (fraction,)),next_z)
                if best is None or value[0]<best[0]:best=value
            if best is not None:following.append(best)
        if not following:
            raise ValueError('No connected bounded portal targets in polygon '+str(polygon))
        states=following;check()
    best=min(states,key=lambda v:v[0])
    return dict(method='reciprocal_portal_target_selection',points=best[1],fractions=best[2],
        length=best[0],segment_choices_checked=checks,body_clearance_verified=False,
        whole_corridor_clearance_verified=False)


def plan_destination(planner, navigation_mesh, reader, first, second, *, goal_xy,
                     maximum_seconds=120., max_polygons=512, clock=time.monotonic,
                     **start_options):
    """Use the retained navigation search, then verify its selected endpoints.

    ``navigation_mesh`` is the owner's pinned eqnav.mesh.NavMesh. Its nearest
    point lookup is not accepted as current position/floor: both endpoints are
    independently resolved at exact XY and the returned corridor must match.
    A new stopped pair remains required after planning for height/startup.
    """
    if (not isinstance(planner, CurrentStartPlanner)
            or not isinstance(goal_xy, tuple) or len(goal_xy)!=2
            or not all(finite(v) for v in goal_xy)
            or not finite(maximum_seconds) or not 0<maximum_seconds<=240
            or not integer(max_polygons) or not 1<=max_polygons<=4096
            or not callable(clock) or 'length' in start_options):
        raise ValueError('Exact destination, current-start options and bounded planning required')
    began=clock();last=began
    mesh_pin=planner.pins[0]
    owner=start_options.get('owner_binding');binding=start_options.get('binding_reader')
    if not callable(binding):raise ValueError('Current owner binding required')
    identity=(reader.tail.identity,reader.tail.epoch,reader.zone_generation,
              reader.zone_id,reader.zone_display_name)
    def check():
        nonlocal last
        actual=binding();planner._check_views();now=clock()
        if (actual!=owner or not finite(now) or not finite(began)
                or not began<=last<=now<=began+maximum_seconds
                or getattr(navigation_mesh,'sha256',None)!=mesh_pin
                or len(navigation_mesh.area)!=len(planner.mesh.area)
                or reader.latest is not second or reader.log_line_seq!=second.log_line_seq
                or reader.tail.partial
                or identity!=(reader.tail.identity,reader.tail.epoch,reader.zone_generation,
                              reader.zone_id,reader.zone_display_name)):
            raise ValueError('Destination planning context changed or expired')
        last=now
        return began+maximum_seconds-now
    check()
    # This accepted capsule includes the initial pivot/body footprint. Keep
    # its chain at the starting floor; never pre-commit an untraversed suffix.
    initial=planner.plan(reader,first,second,length=.75,clock=clock,
                         maximum_seconds=min(30.,maximum_seconds),**start_options)
    check()
    start=initial.route.segments[0].start
    start_polygon=initial.route.segments[0].polygon
    goal_polygon,goal_z=planner._support(goal_xy)
    component=int(planner.ground.components[start_polygon])
    if int(planner.ground.components[goal_polygon])!=component:
        raise ValueError('Destination is not in the current dry connected component')
    goal=(*goal_xy,goal_z)
    path=navigation_mesh.find_path(start,goal,water_cost=None,allow_zone_lines=(),
        locate_radius=0.,max_expansions=200000,margin=initial.route.half_width)
    check()
    polygons=tuple(path.polys)
    if (not 1<=len(polygons)<=max_polygons or polygons[0]!=start_polygon
            or polygons[-1]!=goal_polygon or len(path.points)<2
            or tuple(path.points[0][:2])!=start[:2] or tuple(path.points[-1][:2])!=goal_xy):
        raise ValueError('Navigation search moved an endpoint or selected another floor')
    links=[];pairs=[];portal_records=[]
    for polygon in polygons:
        if (not integer(polygon) or polygon>=len(planner.ground.areas)
                or int(navigation_mesh.area[polygon])!=63
                or int(planner.ground.areas[polygon])!=63
                or int(planner.ground.components[polygon])!=component):
            raise ValueError('Destination corridor contains a closed or foreign component')
    for a,b in zip(polygons,polygons[1:]):
        forward=[edge for edge in navigation_mesh.links[a] if edge[0]==b]
        reverse=[edge for edge in navigation_mesh.links[b] if edge[0]==a]
        if a==b or len(forward)!=1 or len(reverse)!=1:
            raise ValueError('Destination portal is missing, ambiguous or not reciprocal')
        links.extend(((a,b),(b,a)));pairs.append(tuple(sorted((a,b))))
        portal_records.append(dict(source=a,target=b,forward=forward[0],reverse=reverse[0]))
    selection=corridor_points(navigation_mesh,polygons,portal_records,start,goal,check)
    check()
    points=selection['points']
    if len(points)!=len(polygons)+1 or points[0]!=start[:2] or points[-1]!=goal_xy:
        raise ValueError('Destination portal sequence changed its endpoints')
    for crossing,portal in zip(points[1:-1],portal_records):
        if not all(crossing_on_portal(crossing,portal[key]) for key in ('forward','reverse')):
            raise ValueError('Selected crossing does not lie on both directed portals')
    segments=[]
    for index,polygon in enumerate(polygons):
        endpoints=[]
        for xy in points[index:index+2]:
            z=_supported_detail_height(navigation_mesh,polygon,*xy)
            if z is None or not finite(z):
                raise ValueError('Destination portal lacks bounded detail support')
            endpoints.append((*xy,z))
        segment=FixedSegment(polygon,*endpoints)
        if segment.length<=.5 or (segments and (
                segments[-1].end[:2]!=segment.start[:2]
                or abs(segments[-1].end[2]-segment.start[2])>.25)):
            raise ValueError('Destination segment is too short or crosses an unsupported height step')
        segments.append(segment)
    # Preserve exact independent start/destination heights. Portal targets may
    # use the existing <=0.0005-unit planning projection; live raw fixes never do.
    segments[0]=replace(segments[0],start=start)
    segments[-1]=replace(segments[-1],end=goal)
    finished=clock();check()
    evidence=encoded(dict(format='eql-current-destination-geometry-v1',
        scope='initial_support_and_reciprocal_corridor; future_footprints_checked_before_input',
        initial_geometry=json.loads(initial.evidence_bytes),initial_chain_index=initial.floor_chain.index,
        initial_chain_proof=initial.floor_chain.previous.proof_sha256,
        polygons=polygons,portals=portal_records,selection=selection,
        start=start,goal=goal,started=began,finished=finished,
        whole_corridor_clearance_verified=False,future_geometry_requires_runtime_checks=True,
        planning_portal_projection_limit=.0005,live_raw_projection_allowed=False,
        requires_fresh_start_pair=True,real_client_accepted=False,input_authorized=False))
    proof=sha256(evidence).hexdigest()
    geometry=GroundGeometryEvidence(planner.zone,*planner.pins[:3],proof,
        start_options['maximum_source_z_difference'],tuple(sorted(set(pairs))),True)
    plan_bytes=encoded(dict(format='eql-fixed-segment-plan-v1',zone=planner.zone,
        frame='helper_package_WLD_Y_X_Z',offline_only=True,route_accepted=False,
        real_client_accepted=False,pins=dict(mesh=mesh_pin,archive=planner.pins[1],
            wld=planner.pins[2],static=planner.pins[3],bsp=planner.bsp_pin,geometry=proof),
        half_width=initial.route.half_width,segments=[dict(index=i,polygon=s.polygon,
            points=(s.start,s.end)) for i,s in enumerate(segments)],
        scope='fresh_destination_corridor_with_incremental_geometry',
        whole_corridor_clearance_verified=False,future_geometry_requires_runtime_checks=True,
        requires_fresh_start_pair=True))
    route=FixedRoute(planner.zone,mesh_pin,sha256(plan_bytes).hexdigest(),
                     initial.route.half_width,tuple(segments))
    observer=RouteGroundObserver(mesh=planner.mesh,ground=planner.ground,source=planner.source,
        geometry_evidence=geometry,reciprocal_links=tuple(links))
    check()
    return CurrentStartPlan(route,observer,initial.floor_chain,initial.planning_bounds,plan_bytes,evidence,
                            initial.precision_policy)
