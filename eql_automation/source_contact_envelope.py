"""Offline body envelope around explicitly hypothesized thin contact sheets.

The inherited terrain must still support the complete footprint. Exact pinned
placed sheets may be foot contact or noncolliding under a separate hypothesis;
all other geometry is checked against the enlarged body envelope. This does
not establish an entry/exit trajectory, client collision filtering, movement
capability or an executable route. Ordinary floor/static guards are unchanged.
"""
from dataclasses import asdict, dataclass
from fractions import Fraction as F
from hashlib import sha256
import json
import math

from eql_automation.bsp_clip import check_bsp_wedge
from eql_automation.bsp_floor_guard import outward_float
from eql_automation.ground_binding import digest as valid_digest
from eql_automation.ground_sweep import area, clip, hull
from eql_automation.native_region_policy import NativeZeroRegionTrialPolicy, encoded
from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_detour import swept_square
from eql_automation.source_itinerary import SourceWalkHint, xy
from eql_automation.source_floor_chain import FloorChainStep, exact_plane, rational
from eql_automation.source_occupancy import check_selected_floor_clearance, clip_xyz, exact_floor_partition
from eql_automation.source_step import digest, expanded, vertices
from eql_automation.static_floor_guard import check_source_static_floor


@dataclass(frozen=True)
class ContactHypothesis:
    payload: bytes
    sha256: str

    def record(self):
        if type(self.payload) is not bytes or sha256(self.payload).hexdigest() != self.sha256:
            raise ValueError('Contact hypothesis seal changed')
        value = json.loads(self.payload)
        if encoded(value) != self.payload:
            raise ValueError('Contact hypothesis encoding changed')
        return value


def declare_contact_hypothesis(static, face_ids, *, max_rise=.125):
    """Pin explicit raw faces/provenance; never discover contact from a name."""
    if (not valid_digest(static.inventory_sha256) or type(face_ids) is not tuple
            or not 1 <= len(face_ids) <= 16 or len(set(face_ids)) != len(face_ids)
            or any(type(k) is not tuple or len(k) != 2
                   or any(type(n) is not int or n < 0 for n in k) for k in face_ids)
            or type(max_rise) not in (int,float) or not 0 < max_rise <= .125
            or type(static.sources) is not tuple):
        raise ValueError('Explicit bounded contact hypothesis required')
    inventory = {(s.fragment,s.face):s for s in static.sources}
    if len(inventory) != len(static.sources) or not set(face_ids) <= inventory.keys():
        raise ValueError('Contact faces missing from complete placed inventory')
    faces = []
    for key in sorted(face_ids):
        source = inventory[key]
        points = vertices(source)
        # This only bounds the hypothesized contact geometry. These labels do
        # not establish collidability; unsupported/known special surfaces are
        # not silently promoted to ground by the explicit declaration.
        if (source.flag != 0 or source.material_class not in ('Diffuse','TransparentMasked')
                or len(set(p[2] for p in points)) != 1
                or len(hull(p[:2] for p in points)) != 3):
            raise ValueError('Only explicit flat nondegenerate sheets are supported')
        faces.append(asdict(source))
    identities = {str(key[0]):static.identities[key[0]] for key in face_ids}
    payload = encoded(dict(format='eql-thin-contact-hypothesis-v1',
        static_inventory_sha256=static.inventory_sha256,faces=faces,identities=identities,
        maximum_height_above_reference_terrain=max_rise,
        assumption='declared_sheets_may_be_foot_contact_or_noncolliding',
        contact_semantics_verified=False,transition_kinematics_verified=False,
        input_authorized=False,real_client_accepted=False))
    return ContactHypothesis(payload,sha256(payload).hexdigest())


def audit_contact_envelope(step,footprint,terrain_sources,static,hypothesis,*,
                           source_wld_sha256,bsp,region_policy,check_context=lambda:None):
    """Classify a full cell without returning a floor, step or route permit."""
    if type(hypothesis) is not ContactHypothesis:
        raise ValueError('Sealed explicit contact hypothesis required')
    declaration = hypothesis.record()
    record = dict(format='eql-offline-contact-envelope-v1',
        contact_hypothesis_sha256=hypothesis.sha256,contact_hypothesis=declaration,
        envelope_clear=False,reason='unexamined',contact_faces=[],
        ordinary_static_clearance=False,contact_semantics_verified=False,
        transition_kinematics_verified=False,route_candidate=False,
        input_authorized=False,real_client_accepted=False,
        source_wld_sha256=source_wld_sha256,reference_terrain_proof_sha256=getattr(step,'proof_sha256',None))
    def refuse(reason):
        record['reason'] = reason
        return record
    if (type(step) is not FloorChainStep or not step.candidate
            or step.occupancy is None or not step.occupancy.candidate
            or type(region_policy) is not NativeZeroRegionTrialPolicy
            or source_wld_sha256 != region_policy.wld_sha256
            or static.inventory_sha256 != declaration['static_inventory_sha256']):
        return refuse('matching_terrain_static_and_region_context_required')
    ids = tuple((s['fragment'],s['face']) for s in declaration['faces'])
    current = declare_contact_hypothesis(static,ids,
        max_rise=declaration['maximum_height_above_reference_terrain'])
    if current != hypothesis:
        return refuse('declared_contact_geometry_or_placement_changed')
    snapshot = (static.sources,static.faces_for_footprint,static.inventory_sha256,
                encoded({str(k[0]):static.identities[k[0]] for k in ids}),encoded(region_policy.record()))
    def check():
        check_context()
        region_policy.check_context(zone='crushbone',
            pins=(region_policy.mesh_sha256,region_policy.archive_sha256,
                  source_wld_sha256,static.inventory_sha256),bsp=bsp)
        if snapshot != (static.sources,static.faces_for_footprint,static.inventory_sha256,
                encoded({str(k[0]):static.identities[k[0]] for k in ids}),encoded(region_policy.record())):
            raise ValueError('Contact envelope context changed')
    check()
    raw_geometry = digest(dict(footprint=footprint,sources=[asdict(s) for s in terrain_sources]))
    if raw_geometry != step.geometry_sha256:
        return refuse('reference_terrain_cell_changed')
    placed = static.faces_for_footprint(footprint)
    combined = terrain_sources+placed
    inventory = {(s.fragment,s.face):s for s in combined}
    if not 1 <= len(combined) <= 128 or len(inventory) != len(combined):
        return refuse('complete_contact_inventory_budget_or_duplicate')
    if not set(step.selected_ids) <= inventory.keys():
        return refuse('reference_terrain_support_missing')
    # Complete source query membership is checked against the immutable source
    # list for this exact expanded footprint, in both directions.
    boundary = expanded(footprint)
    queried = {(s.fragment,s.face):s for s in placed}
    bounds = tuple((outward_float(min(p[k] for p in boundary),lower=True),
                    outward_float(max(p[k] for p in boundary),lower=False)) for k in (0,1))
    for source in static.sources:
        key = (source.fragment,source.face)
        points = tuple((y,x) for x,y,_ in source.vertices_wld)
        if any(max(p[k] for p in points) < bounds[k][0]
               or min(p[k] for p in points) > bounds[k][1] for k in (0,1)):
            continue
        if clip_xyz(vertices(source),boundary) and queried.get(key) != source:
            return refuse('complete_static_query_omitted_or_changed_geometry')
    full_static = {(s.fragment,s.face):s for s in static.sources}
    if any(full_static.get(k) != v for k,v in queried.items()):
        return refuse('static_query_invented_or_changed_geometry')
    ordinary = check_source_static_floor(step,footprint,terrain_sources,static)
    record.update(ordinary_static=asdict(ordinary),ordinary_static_clearance=ordinary.candidate,
        footprint=footprint,complete_geometry_sha256=digest([asdict(s) for s in combined]),
        complete_source_count=len(combined),hypothesized_contact_ids=ids)
    if static.faces_for_footprint(footprint) != placed:
        raise ValueError('Contact query changed during ordinary guard')
    support = []
    heights = []
    for key in step.selected_ids:
        points = vertices(inventory[key]);polygon = hull(p[:2] for p in points)
        patch = clip(boundary,polygon)
        if area(patch) <= 0:
            return refuse('reference_support_has_no_area')
        plane = exact_plane(points)
        heights.extend(plane[0]*x+plane[1]*y+plane[2] for x,y in patch)
        support.append((key,patch,plane))
    if not heights or len(set(heights)) != 1 or not exact_floor_partition(boundary,tuple(p for _,p,_ in support)):
        return refuse('flat_complete_reference_support_required')
    base = heights[0];rise = F(declaration['maximum_height_above_reference_terrain'])
    permitted = set()
    for source in placed:
        key = (source.fragment,source.face)
        if key not in ids:
            continue
        patch = clip_xyz(vertices(source),boundary)
        entry = dict(identifier=key,raw_face=asdict(source),classification='outside_expanded_footprint')
        record['contact_faces'].append(entry)
        if not patch:
            continue
        offsets = tuple(p[2]-base for p in patch)
        entry.update(minimum_above_terrain_exact=str(min(offsets)),
                     maximum_above_terrain_exact=str(max(offsets)))
        # Selected terrain's exact partition includes the full closed boundary,
        # so point/edge contacts are checked too, rather than dropped by area.
        if not all(0 < z <= rise for z in offsets):
            return refuse('declared_sheet_outside_bounded_contact_band')
        entry['classification']='hypothesized_thin_foot_contact_not_ordinary_clearance'
        permitted.add(key)
    body = F(step.occupancy.hypothetical_body_height)
    enlarged = check_selected_floor_clearance(footprint,
        tuple(s for s in combined if (s.fragment,s.face) not in permitted),
        selected_ids=step.selected_ids,
        selection_evidence_sha256=digest(dict(terrain=step.proof_sha256,hypothesis=hypothesis.sha256,
                                              geometry=record['complete_geometry_sha256'])),
        body_height=outward_float(body+rise,lower=False))
    record['other_surface_occupancy']=asdict(enlarged)
    if not enlarged.candidate:
        return refuse('enlarged_body_'+enlarged.reason)
    low,high=base,base+body+rise+F(.01)
    xy=tuple((y,x) for x,y in boundary)
    old_bsp=check_bsp_wedge(bsp,xy,(0,0,low),(0,0,high))
    native=region_policy.classifier.classify_convex_enclosure_after_bounds(
        tuple((y,x,z) for x,y in boundary for z in (low,high)))
    record.update(bsp=asdict(old_bsp),native=asdict(native),
        reference_height_exact=str(base),maximum_contact_rise_exact=str(rise),
        region_body_band_exact=[str(low),str(high)],below_floor_region_classified=False)
    check()
    if not old_bsp.candidate and old_bsp.reason != 'missing_bsp_child':
        return refuse('contact_envelope_bsp_'+old_bsp.reason)
    if (not native.complete or not native.possible_classes
            or any(c.flags != 0 or c.class_id != 0 for c in native.possible_classes)):
        return refuse('contact_envelope_nonzero_or_unresolved_native_regions')
    record.update(envelope_clear=True,reason='conditional_contact_layer_inventory_only',
                  current_floor_unchanged=True,terrain_collision_margins_unchanged=True)
    return record


def audit_contact_walks(prefix,operations,goal,terrain,static,bsp,region_policy,hypothesis,*,
                        radius,check_context,progress=lambda _:None,forward_runout=0.):
    """Follow only a private terrain reference through conditional envelopes.

    No future floor object or executable itinerary is returned. The caller's
    original prefix is unchanged, including when a proposal fails.
    """
    if (type(operations) is not tuple or not 1<=len(operations)<=10000
            or any(type(op) is not SourceWalkHint or not xy(op.start) or not xy(op.end) or op.start==op.end
                   for op in operations)
            or any(a.end!=b.start for a,b in zip(operations,operations[1:]))
            or not xy(goal) or operations[-1].end!=goal
            or type(radius) not in (float,int) or not .05<=radius<=10
            or type(forward_runout) not in (float,int) or not 0<=forward_runout<=40.
            or prefix.inventory_sha256!=terrain.wld_sha256):
        raise ValueError('Continuous walk-only hints ending at the exact goal required')
    original=_chain_snapshot(prefix)
    bindings=(terrain.wld_sha256,terrain.source_faces_for_footprint,
              tuple(terrain.sources) if hasattr(terrain,'sources') else None)
    def check():
        check_context()
        if (_chain_snapshot(prefix)!=original or bindings!=(terrain.wld_sha256,
                terrain.source_faces_for_footprint,
                tuple(terrain.sources) if hasattr(terrain,'sources') else None)):
            raise ValueError('Contact walk reference inventory or original floor changed')
    check();position=operations[0].start;prefix.floor_at(position)
    chain=prefix.fork();index=0
    record=dict(format='eql-offline-contact-walks-v1',start=position,goal=goal,
        parent_terrain_proof_sha256=prefix.previous.proof_sha256,forward_runout=forward_runout,
        contact_hypothesis_sha256=hypothesis.sha256,attempts=[],accepted_envelopes=[],
        exit_envelopes_clear=False,original_floor_unchanged=True,
        contact_semantics_verified=False,transition_kinematics_verified=False,
        route_candidate=False,executable_itinerary=False,input_authorized=False,real_client_accepted=False)
    progress(record)
    while index<len(operations):
        check();chosen=None
        for end in range(len(operations)-1,index-1,-1):
            destination=operations[end].end
            length=math.dist(position,destination)
            if not 0<length or length+forward_runout>40:continue
            check()
            if len(record['attempts'])>=512:raise TimeoutError('Contact proposal query budget exhausted')
            # Check the maximum possible last pulse beyond each waypoint,
            # including corners. The actual destination remains unchanged.
            checked_end=tuple(destination[k]+forward_runout*(destination[k]-position[k])/length
                              for k in (0,1))
            row=dict(first_origin=index,last_origin=end,start=position,end=destination,
                     checked_end=checked_end)
            record['attempts'].append(row)
            cap=swept_square(position,checked_end,radius)
            try:sources=terrain.source_faces_for_footprint(cap)
            except ValueError as error:
                if str(error)!='Source projection candidate budget exceeded':raise
                row['query_refusal']=str(error);continue
            branch=chain.fork();floor=branch.advance(cap,sources)
            row['terrain']=asdict(floor)
            if not floor.candidate:continue
            contact=audit_contact_envelope(floor,cap,sources,static,hypothesis,
                source_wld_sha256=terrain.wld_sha256,bsp=bsp,
                region_policy=region_policy,check_context=check)
            row['contact_envelope']=contact
            if contact['envelope_clear']:
                chosen=(end,destination,branch,row);break
        if chosen is None:
            progress(record)
            raise ValueError('No bounded contact-envelope proposal at '+str(index))
        end,position,chain,row=chosen;index=end+1
        record['accepted_envelopes'].append(row);progress(record)
    check()
    if position!=goal:raise ValueError('Contact exit did not reach its exact destination')
    record.update(exit_envelopes_clear=True,reference_goal_height=chain.floor_at(position)[0],
        reference_goal_source_ids=chain.floor_at(position)[1],
        conclusion='exit_clear_only_under_unverified_contact_and_motion_hypotheses')
    progress(record)
    return record
