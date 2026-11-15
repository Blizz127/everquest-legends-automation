"""Plan finite walking sections with copied-geometry measurement reserves.

These are route hints, not movement permission or live checkpoints. Each actual
section needs fresh observations and a separately completed child scope; a
timeout, cancellation or rejected observation cannot advance to another section.
"""
from dataclasses import asdict, replace
from hashlib import sha256
import math
import time

from .ground_binding import finite
from .ground_sweep import motion_footprint
from .motion_calibration import PROBES
from .native_region_policy import encoded
from .route_floor_commit import _chain_snapshot
from .route_geometry import RouteMotionBounds
from .source_detour import swept_square
from .source_itinerary import SourceItineraryGuide, SourceWalkHint, _guide_snapshot
from .source_probe_geometry import check_source_footprint


SPATIAL_REFUSALS = frozenset((
    'Source motion terrain: selected_floor_uncovered_ground_area',
    'Source motion terrain: other_source_surface_intersects_body_band',
    'Source motion static: other_source_surface_intersects_body_band',
))
UNRESOLVED_RESERVES = frozenset((
    'Source motion terrain: floor_patch_budget_exceeded',
    'Source motion static: complete_source_budget_exceeded',
))


def measurement_reserve(position, bounds):
    """Enclose the whole seven-probe sequence under explicit motion hypotheses.

    Add every maximum displacement and post-release drift. Unknown headings
    cannot reduce this reserve. Runtime still checks each actual pulse and its
    stopped observations; this offline area does not certify future dynamics.
    """
    if (type(position) is not tuple or len(position)!=2 or not all(finite(v) for v in position)
            or type(bounds) is not RouteMotionBounds):
        raise ValueError('Exact XY and explicit measurement bounds required')
    bounds.validate_values(calibration_record_id=bounds.calibration_record_id, maximum_step_seconds=.2)
    if any(not bounds.minimum_requested_hold<=p.seconds<=bounds.maximum_requested_hold for p in PROBES):
        raise ValueError('The complete measurement sequence must fit supplied bounds')
    travel=sum(bounds.forward_speed_upper_bound*bounds.maximum_actual_hold
               if p.key=='forward' else bounds.pivot_displacement_upper_bound for p in PROBES)
    drift=len(PROBES)*bounds.post_release_drift
    footprint=motion_footprint(position,0.,0.,position_error=bounds.position_error,
        heading_error_degrees=0.,post_release_drift=drift,extra_radius=bounds.body_radius+travel)
    return footprint,dict(probes=[asdict(p) for p in PROBES],bounds=asdict(bounds),
        maximum_center_travel=travel,maximum_accumulated_drift=drift,all_headings=True,
        nominal_waypoint_only=True,arrival_offset_covered=False,
        actual_probes_require_fresh_checks=True,motion_bounds_verified=False)


def plan_walk_sections(prefix, guide, planner, *, bounds, maximum_length=1000.,
                       minimum_length=600., candidate_spacing=25., maximum_sections=16,
                       maximum_queries=256, maximum_seconds=120., check_context,
                       clock=time.monotonic, progress=lambda _:None):
    """Replay the complete source route and choose bounded, clear pause hints.

    Candidate reserve branches are discarded: they cannot expand the route's
    carried floor. Only ordinary route cells advance that floor. Region, query,
    identity and time failures abort. An independent reserve that exceeds the
    local patch/complete-face limits stays unresolved; it cannot be selected or treated as
    a collision. Sections retain every original operation.
    """
    if (type(guide) is not SourceItineraryGuide or type(bounds) is not RouteMotionBounds
            or not all(finite(v) for v in (maximum_length,minimum_length,candidate_spacing,maximum_seconds))
            or not 0<minimum_length<maximum_length<=2000
            or not 0<candidate_spacing<=maximum_length-minimum_length
            or not 0<maximum_seconds<=240 or type(maximum_sections) is not int
            or not 1<=maximum_sections<=32 or type(maximum_queries) is not int
            or not 1<=maximum_queries<=512 or not all(callable(f) for f in (check_context,clock,progress))):
        raise ValueError('Finite section geometry and work bounds required')
    guide.validate()
    if (any(type(op) is not SourceWalkHint for op in guide.operations)
            or guide.zone!=planner.region_policy.zone or guide.wld_sha256!=planner.source.wld_sha256
            or guide.static_inventory_sha256!=planner.static.inventory_sha256
            or prefix.inventory_sha256!=guide.wld_sha256 or prefix.body_height!=guide.body_height
            or bounds.body_height!=guide.body_height or bounds.body_radius!=guide.radius):
        raise ValueError('Same-zone ordinary guide and matching source/body required')
    measurement_reserve(guide.operations[0].start,bounds)
    original=_chain_snapshot(prefix);guide_state=_guide_snapshot(guide)
    bounds_state=tuple(vars(bounds).items());began=last=clock()
    if not finite(began):raise ValueError('Finite section planning clock required')
    branch=prefix.fork();position=guide.operations[0].start;branch.floor_at(position)
    guide_pin=sha256(encoded(guide.record())).hexdigest()
    total=sum(math.dist(op.start,op.end) for op in guide.operations)
    if total<=0:raise ValueError('Section route must make progress')
    section_start=0;section_distance=walked=0.;last_query_distance=-candidate_spacing
    pending=None;sections=[];attempts=[];walked_proofs=[]

    def check():
        nonlocal last
        check_context();now=clock()
        if (not finite(now) or not began<=last<=now<=began+maximum_seconds
                or _chain_snapshot(prefix)!=original or _guide_snapshot(guide)!=guide_state
                or tuple(vars(bounds).items())!=bounds_state):
            raise ValueError('Source section context changed or planning budget expired')
        last=now

    def add_section(end_index,end_distance,reserve):
        nonlocal section_start,section_distance
        if (len(sections)>=maximum_sections or end_index<section_start
                or not 0<end_distance-section_distance<=maximum_length):
            raise ValueError('Finite source section budget exhausted')
        ops=guide.operations[section_start:end_index+1]
        evidence=dict(kind='copied_source_walking_section',original_guide_sha256=guide_pin,
            first_operation=section_start,last_operation=end_index,
            distance=end_distance-section_distance,final=end_index==len(guide.operations)-1,
            reserve_sha256=None if reserve is None else sha256(encoded(reserve)).hexdigest(),
            current_character_observation=False,input_authorized=False)
        part=replace(guide,goal=ops[-1].end,operations=ops,
            provenance_sha256=sha256(encoded(evidence)).hexdigest())
        part.validate()
        sections.append(dict(**evidence,guide=part.record(),guide_sha256=sha256(encoded(part.record())).hexdigest(),
                             measurement_reserve=reserve))
        section_start=end_index+1;section_distance=end_distance

    for index,op in enumerate(guide.operations):
        check()
        if op.start!=position:raise ValueError('Section planning lost exact route continuity')
        distance=math.dist(op.start,op.end)
        # Complete a previously checked waypoint before the proposed child
        # section would exceed its finite length. Never increase the bound.
        if walked+distance-section_distance>maximum_length:
            if pending is None:
                raise ValueError('No checked measurement reserve before section length limit at operation '
                                 +str(index)+' from operation '+str(section_start))
            add_section(*pending);pending=None
            if walked+distance-section_distance>maximum_length:
                raise ValueError('Section waypoint spacing exceeds the remaining length budget')
        checked=check_source_footprint(branch,swept_square(op.start,op.end,guide.radius),
            terrain=planner.source,static=planner.static,bsp=planner.bsp,region_policy=planner.region_policy)
        check();branch=checked.branch;position=op.end;walked+=distance
        walked_proofs.append(dict(operation=index,previous=checked.terrain.previous_sha256,
                                  proof=checked.terrain.proof_sha256))
        if (total-section_distance>maximum_length and index<len(guide.operations)-1
                and walked-section_distance>=minimum_length and walked-last_query_distance>=candidate_spacing):
            if len(attempts)>=maximum_queries:raise ValueError('Measurement reserve query budget exhausted')
            footprint,assumptions=measurement_reserve(position,bounds)
            attempt=dict(operation=index,position=position,distance=walked,
                source_floor_proof_sha256=branch.previous.proof_sha256,candidate=False)
            attempts.append(attempt);last_query_distance=walked
            route_floor_before_reserve=_chain_snapshot(branch)
            try:
                reserve=check_source_footprint(branch,footprint,terrain=planner.source,static=planner.static,
                    bsp=planner.bsp,region_policy=planner.region_policy)
            except ValueError as error:
                if str(error) in UNRESOLVED_RESERVES:
                    # Only this detached candidate fork exhausted its local
                    # geometry budget. Keep the route/bounds unchanged and try a
                    # different waypoint; this supplies no obstacle evidence.
                    attempt.update(status='unresolved',unresolved_reason=str(error))
                elif str(error) in SPATIAL_REFUSALS:
                    attempt.update(status='spatial_refusal',refusal=str(error))
                else:raise
            else:
                check();attempt.update(status='checked',candidate=True)
                record=dict(assumptions=assumptions,footprint=footprint,
                    source_floor_proof_sha256=branch.previous.proof_sha256,
                    terrain=asdict(reserve.terrain),static=asdict(reserve.static),
                    bsp=asdict(reserve.bsp),native=asdict(reserve.native),
                    current_position_verified=False,input_authorized=False,real_client_accepted=False)
                pending=(index,walked,record)
            if _chain_snapshot(branch)!=route_floor_before_reserve:
                raise ValueError('Measurement reserve changed the carried route floor')
            check();progress(dict(checked_operations=index+1,sections=len(sections),
                candidate_queries=len(attempts),checked_reserves=sum(a['candidate'] for a in attempts),
                unresolved_reserves=sum(a.get('status')=='unresolved' for a in attempts),
                last_attempt=dict(attempt)))
    check()
    if position!=guide.goal:raise ValueError('Section route did not reach the exact guide goal')
    add_section(len(guide.operations)-1,walked,None)
    if tuple(op for row in sections for op in SourceItineraryGuide.from_record(row['guide']).operations)!=guide.operations:
        raise ValueError('Section partition changed original operations')
    result=dict(format='eql-copied-source-walk-sections-v1',original_guide_sha256=guide_pin,
        sections=sections,attempts=attempts,checked_operations=len(walked_proofs),
        checked_route_proofs_sha256=sha256(encoded(walked_proofs)).hexdigest(),
        source_prefix_unchanged=True,total_length=walked,maximum_section_length=maximum_length,
        maximum_sections=maximum_sections,maximum_queries=maximum_queries,
        current_character_observation=False,input_authorized=False,real_client_accepted=False,
        requires_fresh_live_section_receipts=True,requires_new_motion_observations=True,
        runtime_continuation_enabled=False)
    check();return result
