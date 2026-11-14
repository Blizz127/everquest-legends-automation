"""Link an offline checked stair flight to a planning copy of its old floor.

No owner executor consumes this separate certificate. A successful result is
still conditional copied geometry and never a current-character floor commit.
"""
from dataclasses import asdict, dataclass, replace
from fractions import Fraction as F
from hashlib import sha256
import json

from eql_automation.bsp_floor_guard import outward_float
from eql_automation.native_region_policy import encoded
from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_floor_chain import positive_overlap
from eql_automation.ground_sweep import hull
from eql_automation.source_occupancy import clip_xyz
from eql_automation.source_step import digest, vertices, expanded
from eql_automation.static_floor_guard import check_source_static_floor
from eql_automation.source_stair_flight import audit_stair_flight, stair_body_footprint


@dataclass(frozen=True)
class SourceStairPlan:
    payload: bytes
    sha256: str

    def record(self):
        if type(self.payload) is not bytes or sha256(self.payload).hexdigest() != self.sha256:
            raise ValueError('Offline stair plan seal changed')
        result = json.loads(self.payload)
        if encoded(result) != self.payload:
            raise ValueError('Offline stair plan encoding changed')
        return result


def outward_box(boundary):
    low = tuple(outward_float(min(p[k] for p in boundary),lower=True) for k in (0,1))
    high = tuple(outward_float(max(p[k] for p in boundary),lower=False) for k in (0,1))
    return ((low[0],low[1]),(high[0],low[1]),(high[0],high[1]),(low[0],high[1]))


def extend_stair_landing(prefix,target,end,tread_ids,terrain,static,bsp,region_policy,*,radius,check_context):
    """Propose final tread faces through a checked exact-edge landing runout."""
    from .source_probe_geometry import check_source_footprint
    check_context();before=_chain_snapshot(prefix)
    cap=swept_square(target,target,radius);boundary=expanded(cap)
    sources=terrain.source_faces_for_footprint(cap);permitted=set(tread_ids[-1])
    seeds=tuple((s.fragment,s.face) for s in sources if (s.fragment,s.face) in permitted
        and positive_overlap(boundary,hull(p[:2] for p in vertices(s))))
    temporary=SourceFloorChain(inventory_sha256=prefix.inventory_sha256,
        seed_evidence_sha256=prefix.previous.proof_sha256,seed_ids=seeds,body_height=prefix.body_height)
    floor=temporary.advance(cap,sources)
    if not floor.candidate:raise ValueError('Stair target landing: '+floor.reason)
    if not set(floor.selected_ids)<=permitted:
        raise ValueError('Stair target landing escaped original final tread')
    runout=swept_square(target,end,radius)
    checked=check_source_footprint(temporary,runout,terrain=terrain,static=static,bsp=bsp,region_policy=region_policy)
    selected=checked.branch._selected
    heights={p[2] for source,*_ in selected.values() for p in source.vertices_wld}
    if len(heights)!=1:raise ValueError('Stair landing runout must retain one exact flat height')
    group=tuple(sorted(permitted|set(checked.terrain.selected_ids)))
    if len(group)>64:raise ValueError('Stair landing runout exceeds bounded source group')
    check_context()
    if _chain_snapshot(prefix)!=before:raise ValueError('Stair landing runout changed original floor')
    return (*tread_ids[:-1],group),dict(target=target,checked_end=end,footprint=runout,
        terrain=asdict(checked.terrain),static=asdict(checked.static),bsp=asdict(checked.bsp),native=asdict(checked.native))


def plan_stair_flight(prefix,start,end,tread_ids,terrain,static,bsp,region_policy,*,
                      radius,max_rise=2.,max_lift=4.,check_context,progress=lambda _:None,
                      vertical_model='lift_transfer',body_radius=None):
    if vertical_model not in ('lift_transfer','bounded_source_contacts'):
        raise ValueError('Explicit known stair vertical model required')
    if type(prefix) is not SourceFloorChain or prefix.halted or prefix.previous is None:
        raise ValueError('Accepted original floor lineage required')
    before = _chain_snapshot(prefix)
    all_sources = tuple(terrain.sources)
    static_snapshot = tuple(static.sources) if hasattr(static,'sources') else None
    bindings = (terrain.wld_sha256,static.inventory_sha256,
                terrain.source_faces_for_footprint,static.faces_for_footprint)
    if not all_sources or len(all_sources)>1_000_000 or prefix.inventory_sha256 != terrain.wld_sha256:
        raise ValueError('Complete bounded source inventory must match floor lineage')
    def check():
        check_context()
        if (_chain_snapshot(prefix) != before or tuple(terrain.sources) != all_sources
                or (tuple(static.sources) if hasattr(static,'sources') else None) != static_snapshot
                or bindings != (terrain.wld_sha256,static.inventory_sha256,
                    terrain.source_faces_for_footprint,static.faces_for_footprint)):
            raise ValueError('Stair planning context changed')
    check()
    prefix.floor_at(start)
    cap = swept_square(start,start,radius)
    departure = prefix.fork()
    departure_sources = terrain.source_faces_for_footprint(cap)
    floor = departure.advance(cap,departure_sources)
    placed = check_source_static_floor(floor,cap,departure_sources,static)
    if (not floor.candidate or not placed.candidate
            or not set(floor.selected_ids) <= set(tread_ids[0])):
        raise ValueError('Original floor does not support the first stair tread')
    corridor = stair_body_footprint(start,end,radius)
    box = outward_box(corridor)
    local = []
    for index,source in enumerate(all_sources):
        if index % 256 == 0: check()
        points = tuple((y,x,z) for x,y,z in source.vertices_wld)
        if all(min(p[k] for p in points) <= box[2][k]
               and max(p[k] for p in points) >= box[0][k] for k in (0,1)):
            local.append(source)
    local = tuple(local)
    objects = static.faces_for_footprint(box)
    audit=audit_stair_flight;options={}
    if vertical_model=='bounded_source_contacts':
        from .source_stair_contacts import audit_stair_contacts
        audit=audit_stair_contacts;options['body_radius']=body_radius
    flight = audit(local,objects,tread_ids,start=start,end=end,radius=radius,
        body_height=prefix.body_height,source_wld_sha256=terrain.wld_sha256,
        static_inventory_sha256=static.inventory_sha256,bsp=bsp,region_policy=region_policy,
        max_rise=max_rise,max_lift=max_lift,check_context=check,progress=progress,**options)
    if not flight['candidate']:
        raise ValueError('Stair flight: '+flight['reason'])
    if F(departure.floor_at(start)[0]) != F(flight['topology']['treads'][0]['height_exact']):
        raise ValueError('Flight begins on another height than the inherited floor')
    inventory = {(s.fragment,s.face):s for s in local+objects}
    queries = []
    # Independent complete local views must reproduce all faces intersecting
    # each checked phase. A stale/partial whole-flight list cannot omit a wall.
    for phase in flight['phases']:
        check()
        boundary = tuple(tuple(F(v) for v in p) for p in phase['footprint_exact'])
        query = outward_box(boundary)
        sources = terrain.source_faces_for_footprint(query)
        placed_sources = static.faces_for_footprint(query)
        observed = sources+placed_sources
        if len({(s.fragment,s.face) for s in observed}) != len(observed):
            raise ValueError('Duplicate source in complete phase query')
        for source in observed:
            if clip_xyz(vertices(source),boundary) and inventory.get((source.fragment,source.face)) != source:
                raise ValueError('Complete phase query differs from flight inventory')
        observed_inventory = {(s.fragment,s.face):s for s in observed}
        for source in local+objects:
            if clip_xyz(vertices(source),boundary) and observed_inventory.get((source.fragment,source.face)) != source:
                raise ValueError('Complete phase query omitted retained flight geometry')
        queries.append(dict(phase=phase['index'],query_box=query,
            geometry_sha256=digest([asdict(s) for s in observed])))
    cap = swept_square(end,end,radius)
    landing_sources = terrain.source_faces_for_footprint(cap)
    final_boundary = expanded(cap)
    seeds=tuple((s.fragment,s.face) for s in landing_sources if (s.fragment,s.face) in tread_ids[-1]
        and positive_overlap(final_boundary,hull(p[:2] for p in vertices(s))))
    landing = SourceFloorChain(inventory_sha256=prefix.inventory_sha256,
        seed_evidence_sha256=digest(dict(parent=prefix.previous.proof_sha256,flight=digest(flight))),
        seed_ids=seeds,body_height=prefix.body_height)
    landing_objects = static.faces_for_footprint(cap)
    landing_inventory = {(s.fragment,s.face):s for s in landing_sources+landing_objects}
    if len(landing_inventory) != len(landing_sources)+len(landing_objects):
        raise ValueError('Duplicate source in final landing query')
    # The last fresh query must retain exactly the geometry that supported the
    # flight, even if changed same-ID faces still have the expected height.
    for source in landing_sources+landing_objects:
        if clip_xyz(vertices(source),final_boundary) and inventory.get((source.fragment,source.face)) != source:
            raise ValueError('Final landing query differs from flight inventory')
    for source in local+objects:
        if clip_xyz(vertices(source),final_boundary) and landing_inventory.get((source.fragment,source.face)) != source:
            raise ValueError('Final landing query omitted retained flight geometry')
    last_floor = landing.advance(cap,landing_sources)
    last_static = check_source_static_floor(last_floor,cap,landing_sources,static)
    if (not last_floor.candidate or not last_static.candidate
            or not set(last_floor.selected_ids) <= set(tread_ids[-1])
            or F(landing.floor_at(end)[0]) != F(flight['topology']['treads'][-1]['height_exact'])):
        raise ValueError('Stair final full landing cap refused')
    record = dict(format='eql-offline-source-stair-plan-v1',start=start,end=end,
        vertical_model=vertical_model,
        parent_proof_sha256=prefix.previous.proof_sha256,
        initial_seed_sha256=prefix.seed_evidence_sha256,
        source_wld_sha256=terrain.wld_sha256,static_inventory_sha256=static.inventory_sha256,
        departure=asdict(floor),departure_static=asdict(placed),flight=flight,
        complete_phase_queries=queries,landing=asdict(last_floor),landing_static=asdict(last_static),
        final_landing_query_sha256=digest([asdict(s) for s in landing_sources+landing_objects]),
        input_authorized=False,real_client_accepted=False,executable_itinerary=False,
        planned_landing_only=True,current_floor_unchanged=True)
    payload=encoded(record);plan=SourceStairPlan(payload,sha256(payload).hexdigest())
    reason=('conditional_stair_contact_landing_only' if vertical_model=='bounded_source_contacts'
            else 'conditional_stair_flight_landing_only')
    last_floor=replace(last_floor,reason=reason,index=prefix.index,
        carried_ids=(),joins=(),previous_sha256=prefix.previous.proof_sha256,proof_sha256='')
    last_floor=replace(last_floor,proof_sha256=digest(dict(stair_plan_sha256=plan.sha256,landing=asdict(last_floor))))
    branch=prefix.fork();branch.previous=last_floor;branch.index=prefix.index+1
    branch._expanded=landing._expanded;branch._selected=landing._selected.copy()
    check()
    return plan,branch
