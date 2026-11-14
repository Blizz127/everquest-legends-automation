"""Offline body/region audit of one straight flight between supported caps.

This is a separate conditional movement model, not a walk or single-step hint.
Intermediate treads never become ordinary floor caps or current floor state.
"""
from dataclasses import asdict
from fractions import Fraction as F
import math

from eql_automation.bsp_clip import check_bsp_wedge
from eql_automation.ground_sweep import area, clip, cross, hull
from eql_automation.native_region_policy import NativeZeroRegionTrialPolicy
from eql_automation.portal_precision import SourceFace
from eql_automation.source_detour import swept_square
from eql_automation.source_occupancy import clip_xyz, exact_floor_partition
from eql_automation.source_step import digest, expanded, patches, riser_link, vertices
from tools.source_stair_topology import audit_stair_topology


def stair_body_extent(start, end, radius):
    """Enclose the configured body and both existing float-expanded caps."""
    return max(F(radius)+F(.002), *(abs(p[k]-F(q[k]))
        for q in (start,end) for p in expanded(swept_square(q,q,radius)) for k in (0,1)))


def stair_body_footprint(start, end, radius):
    extent = stair_body_extent(start,end,radius)
    return hull((F(p[0])+dx,F(p[1])+dy) for p in (start,end)
                for dx in (-extent,extent) for dy in (-extent,extent))


def audit_stair_flight(sources, static_sources, tread_ids, *, start, end, radius,
                      body_height, source_wld_sha256, static_inventory_sha256,
                      bsp, region_policy, max_rise=2., max_lift=4.,
                      lift_clearance=.125, reserve=.05, max_transfer_distance=4., check_context=lambda: None,
                      progress=lambda _: None):
    if (type(region_policy) is not NativeZeroRegionTrialPolicy
            or not isinstance(static_sources, tuple) or len(static_sources) > 1024
            or any(type(s) is not SourceFace for s in static_sources)
            or any(type(v) not in (int, float) or not math.isfinite(v)
                   for v in (body_height, max_lift, lift_clearance, reserve, max_transfer_distance))
            or not 0 < body_height <= 100 or not 0 < max_lift <= 8
            or not .11 < lift_clearance <= .5 or not .01 <= reserve <= .5
            or not 0 < max_transfer_distance <= 20
            or not callable(check_context) or not callable(progress)):
        raise ValueError('Bounded stair body and pinned region policy required')
    policy_record = region_policy.record()
    def check():
        check_context()
        region_policy.check_context(zone='crushbone',
            pins=(region_policy.mesh_sha256, region_policy.archive_sha256,
                  source_wld_sha256, static_inventory_sha256), bsp=bsp)
        if region_policy.record() != policy_record:
            raise ValueError('Stair-flight region policy changed')
    check()
    topology = audit_stair_topology(sources, tread_ids, start=start, end=end,
        radius=radius, max_rise=max_rise, check_context=check)
    record = dict(kind='offline_stair_flight_geometry', topology=topology,
        source_wld_sha256=source_wld_sha256, static_inventory_sha256=static_inventory_sha256,
        static_geometry_sha256=digest([asdict(s) for s in static_sources]),
        region_policy=policy_record, body_height=body_height, max_lift=max_lift,
        lift_clearance=lift_clearance, before_or_after_riser_reserve=reserve,
        max_transfer_distance=max_transfer_distance,
        candidate=False, events=[], phases=[], input_authorized=False,
        real_client_accepted=False, executable_itinerary=False,
        floor_lineage_adopted=False, client_step_capability_verified=False,
        endpoint_ground_contact_assumed=True, dynamic_obstacles_checked=False)
    def refuse(reason):
        return dict(record, reason=reason)
    if not topology['topology_candidate']:
        return refuse(topology['reason'])
    inventory = {(s.fragment, s.face):s for s in sources}
    combined = sources + static_sources
    if len({(s.fragment, s.face) for s in combined}) != len(combined):
        return refuse('duplicate_terrain_or_static_source_identity')
    # Exact squares enclose both the configured body and the existing floating
    # endpoint expansion. No rounded vertex may silently shrink the corridor.
    first, last = tuple(map(F, start)), tuple(map(F, end))
    extent = stair_body_extent(start,end,radius)
    square = lambda p: hull((p[0]+dx, p[1]+dy)
                           for dx in (-extent,extent) for dy in (-extent,extent))
    corridor = hull((*square(first), *square(last)))
    supports = [patches(ids, inventory, corridor) for ids in tread_ids]
    heights = [F(t['height_exact']) for t in topology['treads']]
    if not exact_floor_partition(corridor, tuple(p for group in supports for _,_,p,_ in group)):
        return refuse('exact_phase_corridor_support_gap')
    for point, group in ((first,supports[0]),(last,supports[-1])):
        if not exact_floor_partition(square(point), tuple(p for _,_,p,_ in group)):
            return refuse('exact_phase_endpoint_support_gap')
    direction = topology['direction']
    step_sign = 1 if direction == 'up' else -1
    delta = tuple(last[k]-first[k] for k in (0,1))
    prior_normal = None; times = []
    for i, (a_group, b_group) in enumerate(zip(supports, supports[1:])):
        check()
        pair = (a_group,b_group) if step_sign == 1 else (b_group,a_group)
        link = riser_link(*pair, corridor, sources, F(max_rise))
        if link is None:
            return refuse('expanded_phase_corridor_riser_missing')
        wall_points = sorted({p[:2] for key in link['riser_ids'] for p in vertices(inventory[key])})
        a, b = wall_points[0], wall_points[-1]
        if a == b or any(cross(a,b,p) != 0 for p in wall_points):
            return refuse('riser_not_one_vertical_plane')
        normal = (a[1]-b[1], b[0]-a[0])
        speed = sum(normal[k]*delta[k] for k in (0,1))
        if speed == 0:
            return refuse('flight_parallel_to_riser')
        if speed < 0:
            normal = tuple(-v for v in normal); speed = -speed
        if prior_normal is not None and prior_normal[0]*normal[1] != prior_normal[1]*normal[0]:
            return refuse('flight_risers_not_parallel')
        prior_normal = normal
        initial = sum(normal[k]*(first[k]-a[k]) for k in (0,1))
        reach = (extent+F(reserve))*sum(abs(v) for v in normal)
        # Ascent rises before leading-edge contact. Descent lowers only after
        # trailing-edge clearance; no interior grounded cap is invented.
        t = (-step_sign*reach-initial)/speed
        if not 0 <= t <= 1 or times and t <= times[-1]:
            return refuse('riser_phase_order_or_outer_cap_refused')
        times.append(t)
        record['events'].append(dict(riser=i, parameter_exact=str(t),
            position_exact=[str(first[k]+t*delta[k]) for k in (0,1)],
            before_height_exact=str(heights[i]+F(lift_clearance)),
            after_height_exact=str(heights[i+1]+F(lift_clearance)), riser_evidence=link))
    base = heights[0]+F(lift_clearance)
    position = first
    phases = [('ground_lift', first, first, heights[0], base, tread_ids[0])]
    for i,t in enumerate(times):
        point = tuple(first[k]+t*delta[k] for k in (0,1))
        phases.append(('transfer', position, point, base, base, ()))
        next_base = heights[i+1]+F(lift_clearance)
        phases.append(('raise' if step_sign == 1 else 'lower', point, point, base, next_base, ()))
        position, base = point, next_base
    phases.append(('transfer', position, last, base, base, ()))
    phases.append(('ground_settle', last, last, base, heights[-1], tread_ids[-1]))
    exact_sources = [(s, vertices(s)) for s in combined]
    for index, (kind,a,b,z0,z1,ground_ids) in enumerate(phases):
        check()
        if sum((b[k]-a[k])**2 for k in (0,1)) > F(max_transfer_distance)**2:
            return refuse('phase_horizontal_transfer_bound_exceeded')
        footprint = hull((*square(a), *square(b)))
        local_patches = [(key, clip(footprint,polygon), heights[i])
            for i,group in enumerate(supports) for key,_,polygon,_ in group
            if area(clip(footprint,polygon)) > 0]
        if not exact_floor_partition(footprint, tuple(p for _,p,_ in local_patches)):
            return refuse('phase_projected_support_gap')
        lowest = min(h for _,_,h in local_patches)
        local_lift = max(z0,z1)-lowest
        phase = dict(index=index, kind=kind, start_exact=[str(v) for v in a],
            end_exact=[str(v) for v in b], base_start_exact=str(z0), base_end_exact=str(z1),
            footprint_exact=[[str(v) for v in p] for p in footprint],
            lowest_support_exact=str(lowest), local_lift_exact=str(local_lift),
            grounded_support_ids=ground_ids, terrain_static_clear=False)
        record['phases'].append(phase)
        if not 0 <= local_lift <= F(max_lift):
            return refuse('phase_local_lift_bound_exceeded')
        low = min(z0,z1)-F(.1)-F(.01)
        high = max(z0,z1)+F(body_height)+F(.01)
        phase['collision_band_exact'] = [str(low),str(high)]
        classified = []
        for count,(source,points) in enumerate(exact_sources):
            if count % 64 == 0:
                check()
            key = (source.fragment,source.face)
            patch = clip_xyz(points, footprint)
            if not patch:
                continue
            if key in ground_ids:
                if any(p[2] != min(z0,z1) for p in patch):
                    return refuse('ground_contact_is_not_endpoint_floor')
                classification = 'ground_contact'
            elif max(p[2] for p in patch) < low:
                classification = 'below'
            elif min(p[2] for p in patch) > high:
                classification = 'above'
            else:
                phase['obstruction'] = dict(source_id=key,
                    static=source in static_sources,
                    heights_exact=[str(min(p[2] for p in patch)),str(max(p[2] for p in patch))])
                return refuse('source_intersects_stair_phase_body')
            classified.append(dict(source_id=key,classification=classification))
        phase.update(terrain_static_clear=True, source_classifications=classified)
        # Grounded endpoint contact follows the existing body-region scope:
        # classify from its selected floor; airborne phases use the full band.
        region_low = min(z0,z1) if ground_ids else low
        wld_xy = tuple((y,x) for x,y in footprint)
        old_bsp = check_bsp_wedge(bsp,wld_xy,(0,0,region_low),(0,0,high))
        native = region_policy.classifier.classify_convex_enclosure_after_bounds(
            tuple((y,x,z) for x,y in footprint for z in (region_low,high)))
        phase.update(bsp=asdict(old_bsp),native=asdict(native),
                     region_band_exact=[str(region_low),str(high)])
        if not old_bsp.candidate and old_bsp.reason != 'missing_bsp_child':
            return refuse('stair_phase_bsp_'+old_bsp.reason)
        if (not native.complete or not native.possible_classes
                or any(c.flags != 0 or c.class_id != 0 for c in native.possible_classes)):
            return refuse('stair_phase_nonzero_or_unresolved_native_regions')
        progress(record)
    check()
    record.update(candidate=True, reason='conditional_stair_flight_geometry_only',
        phase_count=len(phases), exact_body_half_extent=str(extent),
        full_body_clearance_checked=True, static_objects_checked=True,
        bsp_regions_checked=True, conditional_native_zero_policy=True)
    return record
