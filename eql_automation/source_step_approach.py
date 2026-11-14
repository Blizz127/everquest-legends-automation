"""Recheck a compound approach/step/exit against an entire movement envelope.

All branches are conditional planning state. No key receipt or hypothetical
landing commits these branches; an execution consumer must bind fresh replies.
"""
from dataclasses import asdict,dataclass,field
from fractions import Fraction
from hashlib import sha256
import json
import math
import time

from .bsp_floor_guard import check_source_body_bsp
from .ground_sweep import area,cross,finite,hull
from .native_body_regions import classify_source_body_regions
from .native_region_policy import NativeZeroRegionTrialPolicy,encoded
from .native_step_regions import classify_source_step_regions
from .route_floor_commit import _chain_snapshot
from .source_detour import swept_square
from .source_floor_chain import rational,inside,exact_plane
from .source_itinerary import SourceStepHint,_zero_native,xy
from .source_step import check_source_step,digest
from .source_step_bsp import check_source_step_bsp
from .static_floor_guard import check_source_static_floor


def _halfspace(polygon,a,b,positive):
    if not polygon:return ()
    result=[];previous=polygon[-1];old=cross(a,b,previous)
    for point in polygon:
        new=cross(a,b,point)
        inside=new>=0 if positive else new<=0
        was=old>=0 if positive else old<=0
        if inside!=was:
            t=old/(old-new)
            result.append(tuple(previous[k]+t*(point[k]-previous[k]) for k in (0,1)))
        if inside:result.append(point)
        previous,old=point,new
    return hull(result)


def covered_by_union(footprint,polygons):
    """Exact convex subtraction; overlap cannot hide an uncovered sliver."""
    target=rational(footprint)
    if len(target)<3 or area(target)<=0:raise ValueError('Positive motion footprint required')
    if not 1<=len(polygons)<=32:raise ValueError('Bounded compound cell inventory required')
    remaining=[target]
    for polygon in polygons:
        cover=rational(polygon)
        if len(cover)<3 or area(cover)<=0 or tuple(hull(cover))!=cover:
            raise ValueError('Compound coverage must use positive convex footprints')
        uncovered=[]
        for piece in remaining:
            inside=piece
            for index,a in enumerate(cover):
                b=cover[(index+1)%len(cover)]
                outside=_halfspace(inside,a,b,False)
                if area(outside)>0:uncovered.append(outside)
                inside=_halfspace(inside,a,b,True)
                if area(inside)==0:break
            if len(uncovered)>256:raise ValueError('Compound coverage budget exceeded')
        remaining=uncovered
        if not remaining:return True
    return False


@dataclass(frozen=True)
class SourceStepApproachPlan:
    payload: bytes
    sha256: str
    conditional_branches: tuple = field(default=(),repr=False,compare=False)
    branch_snapshots: tuple = field(default=(),repr=False,compare=False)

    def record(self):
        if type(self.payload) is not bytes or sha256(self.payload).hexdigest()!=self.sha256:
            raise ValueError('Source step approach evidence changed')
        result=json.loads(self.payload)
        if encoded(result)!=self.payload:raise ValueError('Noncanonical source step approach')
        return result

    def checked_branches(self):
        data=self.record()
        if (len(self.conditional_branches)!=len(data['cells'])
                or tuple(_chain_snapshot(c) for c in self.conditional_branches)!=self.branch_snapshots):
            raise ValueError('Missing unchanged conditional source branches')
        seed=data['initial_seed']
        for chain,cell in zip(self.conditional_branches,data['cells']):
            expected=(cell['terrain']['proof_sha256'] if cell['kind']=='walk'
                else cell['transfer']['landing_proof_sha256'])
            if (chain.previous.proof_sha256!=expected
                    or (chain.inventory_sha256,chain.seed_evidence_sha256,chain.seed_ids)!=
                       (seed['wld'],seed['sha256'],tuple(tuple(k) for k in seed['ids']))):
                raise ValueError('Conditional branch does not belong to this source plan')
        return self.conditional_branches


def plan_source_step_approach(prefix,start,hint,terrain,static,bsp,policy,*,
        footprint,nominal_end,body_radius,checked_radius,check_context,
        max_seconds=10.,clock=time.monotonic):
    """Rebase one explicit step, retaining the full supplied movement envelope.

    First try a direct transfer from the actual cap. If its source patches do
    not cover the intervening approach, rebuild that continuous approach before
    the transfer. Departure/landing caps move outward for the larger uncertainty
    radius. The exit is checked far enough for the full envelope; another riser,
    a gap, a hazard or an uncovered corner refuses instead of shrinking it.
    """
    if (type(hint) is not SourceStepHint or not all(xy(p) for p in (start,hint.start,hint.end,nominal_end))
            or type(policy) is not NativeZeroRegionTrialPolicy
            or not all(finite(v) for v in (body_radius,checked_radius,max_seconds))
            or not .05<=body_radius<=checked_radius<=10 or not 0<max_seconds<=60
            or not callable(check_context) or not callable(clock)
            or type(footprint) is not tuple or not 3<=len(footprint)<=64
            or not all(xy(p) for p in footprint) or tuple(hull(footprint))!=footprint
            or not 0<math.dist(hint.start,hint.end)<=20
            or math.dist(start,hint.start)>20 or math.dist(start,nominal_end)>80):
        raise ValueError('Bounded explicit step, motion envelope and source context required')
    state=_chain_snapshot(prefix);seed=(prefix.inventory_sha256,prefix.seed_evidence_sha256,prefix.seed_ids)
    # This fails if the actual start is not on the committed source branch.
    start_z,start_ids=prefix.floor_at(start)
    hint_state=tuple(vars(hint).items());classifier=policy.classifier;policy_bytes=encoded(policy.record())
    query=(terrain.source_faces_for_footprint,static.faces_for_footprint)
    began=last=clock()

    def check():
        nonlocal last
        policy.check_context(zone='crushbone',pins=(policy.mesh_sha256,terrain.archive_sha256,
            terrain.wld_sha256,static.inventory_sha256),bsp=bsp)
        now=clock();check_context()
        if (not finite(now) or not finite(began) or not began<=last<=now<=began+max_seconds
                or _chain_snapshot(prefix)!=state or tuple(vars(hint).items())!=hint_state
                or policy.classifier is not classifier or encoded(policy.record())!=policy_bytes
                or query!=(terrain.source_faces_for_footprint,static.faces_for_footprint)
                or prefix.inventory_sha256!=terrain.wld_sha256):
            raise ValueError('Source step approach changed, cancelled or expired')
        last=now

    cells=[];branches=[]
    def walk(chain,a,b,phase):
        check();polygon=swept_square(a,b,checked_radius)
        sources=terrain.source_faces_for_footprint(polygon)
        fork=chain.fork();floor=fork.advance(polygon,sources)
        if not floor.candidate:raise ValueError('Compound '+phase+' terrain: '+floor.reason)
        objects=check_source_static_floor(floor,polygon,sources,static)
        if not objects.candidate:raise ValueError('Compound '+phase+' static: '+objects.reason)
        old=check_source_body_bsp(floor,polygon,sources,bsp,clip_branches=True)
        if not old.candidate and old.reason!='missing_bsp_child':
            raise ValueError('Compound '+phase+' BSP: '+old.reason)
        native=classify_source_body_regions(floor,polygon,sources,static,classifier,
            source_wld_sha256=terrain.wld_sha256)
        _zero_native(native);check()
        cells.append(dict(kind='walk',phase=phase,start=a,end=b,footprint=polygon,
            terrain=asdict(floor),static=asdict(objects),bsp=asdict(old),native=asdict(native)))
        branches.append(fork)
        return fork

    def transfer(chain,a,b):
        check()
        result,landing=check_source_step(chain,a,b,terrain,static,
            landing_seed_ids=hint.landing_seed_ids,radius=checked_radius,
            max_step_height=hint.max_step_height,max_lift=hint.max_lift,lift_clearance=hint.lift_clearance)
        check()
        return result,landing

    check()
    length=math.dist(hint.start,hint.end)
    direction=tuple((hint.end[k]-hint.start[k])/length for k in (0,1))
    # The checked caps are axis-aligned squares, whose support along a
    # diagonal crossing normal grows by its L1 norm. Every proposal is still
    # independently checked; this is no waiver for a skew crossing or short edge.
    grow=(checked_radius-body_radius)*sum(abs(v) for v in direction)
    departure=tuple(hint.start[k]-grow*direction[k] for k in (0,1))
    destination=tuple(hint.end[k]+grow*direction[k] for k in (0,1))
    cap=walk(prefix,start,start,'actual_start_cap')
    result,landing=transfer(cap,start,destination)
    attempts=[dict(kind='direct',candidate=result.candidate,reason=result.reason)]
    if not result.candidate:
        approach=walk(cap,start,departure,'continuous_approach')
        approach=walk(approach,departure,departure,'departure_cap')
        result,landing=transfer(approach,departure,destination)
        attempts.append(dict(kind='compound',candidate=result.candidate,reason=result.reason))
    if not result.candidate:raise ValueError('Compound source transfer: '+result.reason)
    old=check_source_step_bsp(result,terrain,static,bsp)
    if not old.pieces or any(not p['traversal']['candidate'] and p['traversal']['reason']!='missing_bsp_child'
                             for p in old.pieces):
        raise ValueError('Compound step BSP: '+old.reason)
    native=classify_source_step_regions(result,terrain,static,classifier)
    _zero_native(native);check()
    cells.append(dict(kind='step',phase='conditional_transfer',start=result.evidence['start'],
        end=destination,footprint=result.evidence['footprint'],transfer=asdict(result),
        bsp=asdict(old),native=asdict(native)))
    branches.append(landing)
    # Never walk back from the landing toward a ray endpoint still before it.
    # In that case the conditional step already covers the forward reach.
    beyond=sum((nominal_end[k]-destination[k])*direction[k] for k in (0,1))
    exit_point=nominal_end if beyond>0 else destination
    exit_branch=walk(landing,destination,exit_point,'maximum_hold_exit')
    if not covered_by_union(footprint,tuple(c['footprint'] for c in cells)):
        raise ValueError('Compound approach does not cover the full movement envelope')
    check()
    payload=encoded(dict(format='eql-source-step-approach-v1',source_wld_sha256=terrain.wld_sha256,
        static_inventory_sha256=static.inventory_sha256,region_policy=policy.record(),
        initial_proof_sha256=prefix.previous.proof_sha256,initial_index=prefix.index,
        initial_seed=dict(wld=seed[0],sha256=seed[1],ids=seed[2]),
        start=start,start_floor_height=start_z,start_source_ids=start_ids,
        guide_step=asdict(hint),motion_footprint=footprint,nominal_end=nominal_end,
        body_radius=body_radius,checked_radius=checked_radius,body_height=prefix.body_height,
        attempts=attempts,cells=cells,final_proof_sha256=exit_branch.previous.proof_sha256,
        full_motion_envelope_covered=True,requires_fresh_observed_landing=True,
        conditional_kinematic_hypothesis=True,client_step_capability_verified=False,
        input_authorized=False,real_client_accepted=False,game_input_sent=False,
        started=began,finished=last))
    check()
    return SourceStepApproachPlan(payload,sha256(payload).hexdigest(),tuple(branches),
        tuple(_chain_snapshot(c) for c in branches))


@dataclass(frozen=True)
class SourceStepSupport:
    point: tuple
    height_exact: str
    source_ids: tuple
    cell_indices: tuple
    complete_body_cap_verified: bool = False
    observed_grounded: bool = False
    input_authorized: bool = False


def source_step_supports(plan,point,terrain,static,*,check_context):
    """Query pinned XY supports first; raw Z must never choose a nearer floor.

    A riser edge can return two heights even when both fit a raw-Z residual.
    These are point-support candidates, not full caps or grounded observations.
    Only the future receipt/observation consumer may establish an actual cap.
    """
    if type(plan) is not SourceStepApproachPlan or not xy(point) or not callable(check_context):
        raise ValueError('Exact compound step plan and point required')
    check_context();data=plan.record();payload=plan.payload
    if (data['source_wld_sha256']!=terrain.wld_sha256
            or data['static_inventory_sha256']!=static.inventory_sha256
            or data['full_motion_envelope_covered'] is not True):
        raise ValueError('Source step support inventory changed')
    q=rational((point,))[0]
    if not inside(q,rational(data['motion_footprint'])):
        raise ValueError('Position lies outside the full checked movement envelope')
    hits={}
    for index,cell in enumerate(data['cells']):
        polygon=tuple(tuple(p) for p in cell['footprint'])
        if not inside(q,rational(polygon)):continue
        sources=terrain.source_faces_for_footprint(polygon)
        inventory={(s.fragment,s.face):s for s in sources}
        if len(inventory)!=len(sources):raise ValueError('Duplicate step support source identity')
        if cell['kind']=='walk':
            if digest({'footprint':polygon,'sources':[asdict(s) for s in sources]})!=cell['terrain']['geometry_sha256']:
                raise ValueError('Source step walking support geometry changed')
            ids=cell['terrain']['selected_ids']
        elif cell['kind']=='step':
            transfer=cell['transfer'];e=transfer['evidence']
            if (digest(e)!=transfer['transition_sha256']
                    or digest({'footprint':polygon,'terrain':[asdict(s) for s in sources],
                        'static':[asdict(s) for s in static.faces_for_footprint(polygon)]})!=e['geometry_sha256']):
                raise ValueError('Source step transfer support geometry changed')
            ids=(*e['lower_endpoint']['selected_ids'],*e['landing_endpoint']['selected_ids'])
        else:raise ValueError('Unknown compound support lineage')
        for key in ids:
            key=tuple(key)
            if key not in inventory:raise ValueError('Selected source step support is missing')
            face=inventory[key]
            vertices=rational(tuple((y,x,z) for x,y,z in face.vertices_wld))
            if not inside(q,hull(p[:2] for p in vertices)):continue
            a,b,c=exact_plane(vertices);height=a*q[0]+b*q[1]+c
            names,cells=hits.setdefault(height,(set(),set()))
            names.add(key);cells.add(index)
    check_context()
    if plan.payload is not payload:raise ValueError('Source step support plan changed')
    return tuple(SourceStepSupport(point,str(height),tuple(sorted(names)),tuple(sorted(cells)))
        for height,(names,cells) in sorted(hits.items()))
