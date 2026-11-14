"""Conditional flat-terrain contact corridors and whole-pulse coverage.

The terrain reference remains separate from possible thin placed-sheet contact.
This supplies geometry to a future receipt controller, never an ordinary floor,
observed character state, sender permit or accepted route.
"""
from dataclasses import asdict,dataclass
from fractions import Fraction as F
from hashlib import sha256
import json
import math
import time

from .ground_binding import finite
from .ground_sweep import area,hull,motion_footprint
from .native_region_policy import encoded
from .route_floor_commit import _chain_snapshot
from .route_geometry import RouteMotionBounds
from .source_contact_envelope import ContactHypothesis,audit_contact_walks,declare_contact_hypothesis
from .source_detour import swept_square
from .source_floor_chain import SourceFloorChain,rational
from .source_itinerary import xy
from .source_probe_geometry import _source_storage
from .source_stair_coverage import closed_hull,covers_closed,intersection


@dataclass(frozen=True)
class SourceContactPlan:
    payload: bytes
    sha256: str

    def record(self):
        if type(self.payload) is not bytes or sha256(self.payload).hexdigest()!=self.sha256:
            raise ValueError('Contact plan seal changed')
        value=json.loads(self.payload)
        if encoded(value)!=self.payload:raise ValueError('Contact plan encoding changed')
        return value


def plan_source_contact(prefix,operations,goal,terrain,static,bsp,policy,hypothesis,*,
                        body_radius,checked_radius,check_context,clock=time.monotonic,
                        maximum_seconds=30.,forward_runout=0.):
    """Rebuild every cell on a private terrain fork without adopting it."""
    if (type(prefix) is not SourceFloorChain or prefix.halted or prefix.previous is None
            or type(hypothesis) is not ContactHypothesis
            or not all(finite(v) for v in (body_radius,checked_radius,maximum_seconds,forward_runout))
            or not .05<=body_radius<=checked_radius<=10. or not 0<maximum_seconds<=180.
            or not 0<=forward_runout<=40.):
        raise ValueError('Original source floor and explicit bounded contact corridor required')
    before=_chain_snapshot(prefix);storage=_source_storage(terrain,static)
    declaration=hypothesis.record();ids=tuple((s['fragment'],s['face']) for s in declaration['faces'])
    region=encoded(policy.record());classifier=policy.classifier
    began=last=clock()
    if not finite(began):raise ValueError('Finite contact planning clock required')
    def check():
        nonlocal last
        check_context();now=clock()
        if not finite(now) or not last<=now<=began+maximum_seconds:
            raise ValueError('Contact planning deadline expired or clock moved backward')
        last=now
        if (_chain_snapshot(prefix)!=before or _source_storage(terrain,static)!=storage
                or encoded(policy.record())!=region or policy.classifier is not classifier
                or declare_contact_hypothesis(static,ids,
                    max_rise=declaration['maximum_height_above_reference_terrain'])!=hypothesis):
            raise ValueError('Contact source, original floor or declaration changed')
    check()
    cells=audit_contact_walks(prefix,operations,goal,terrain,static,bsp,policy,hypothesis,
        radius=checked_radius,check_context=check,forward_runout=forward_runout)
    check()
    if not cells['exit_envelopes_clear'] or not 1<=len(cells['accepted_envelopes'])<=128:
        raise ValueError('Complete bounded contact corridor required')
    record=dict(format='eql-source-contact-plan-v1',source_wld_sha256=terrain.wld_sha256,
        static_inventory_sha256=static.inventory_sha256,parent_proof_sha256=prefix.previous.proof_sha256,
        body_radius=body_radius,body_height=prefix.body_height,checked_radius=checked_radius,
        forward_runout=forward_runout,
        contact_hypothesis_sha256=hypothesis.sha256,contact_hypothesis=declaration,
        start=operations[0].start,goal=goal,contact_walks=cells,
        current_floor_unchanged=True,contact_semantics_verified=False,
        input_authorized=False,real_client_accepted=False,executable_itinerary=False)
    payload=encoded(record);plan=SourceContactPlan(payload,sha256(payload).hexdigest())
    SourceContactIndex(plan)  # Reject nonflat/disconnected or inconsistent cells now.
    check()
    return plan


@dataclass(frozen=True)
class ContactCell:
    index: int
    footprint: tuple
    reference_height: F
    region_band: tuple


@dataclass(frozen=True)
class ContactSheet:
    identifier: tuple
    footprint: tuple
    height: F


@dataclass(frozen=True)
class ContactCompatibility:
    kind: str
    source_ids: tuple
    height_interval: tuple


@dataclass(frozen=True)
class ContactPulseCoverage:
    payload: bytes
    sha256: str

    def record(self):
        if type(self.payload) is not bytes or sha256(self.payload).hexdigest()!=self.sha256:
            raise ValueError('Contact pulse coverage seal changed')
        value=json.loads(self.payload)
        if encoded(value)!=self.payload:raise ValueError('Contact pulse encoding changed')
        return value


class SourceContactIndex:
    def __init__(self,plan):
        if type(plan) is not SourceContactPlan:raise ValueError('Sealed contact plan required')
        r=plan.record();walks=r['contact_walks'];declaration=r['contact_hypothesis']
        self.plan=plan;self._plan=(plan,plan.payload,plan.sha256)
        self.body_radius=r['body_radius'];self.body_height=r['body_height']
        rise=declaration['maximum_height_above_reference_terrain'];runout=r.get('forward_runout',0.)
        if (r['format']!='eql-source-contact-plan-v1'
                or any(r[k] is not False for k in ('input_authorized','real_client_accepted','executable_itinerary'))
                or not all(finite(v) for v in (self.body_radius,self.body_height,r['checked_radius'],rise))
                or not .05<=self.body_radius<=r['checked_radius']<=10. or not 0<self.body_height<=100.
                or not 0<rise<=.125 or walks['exit_envelopes_clear'] is not True
                or not finite(runout) or not 0<=runout<=40. or walks.get('forward_runout',0.)!=runout
                or walks['start']!=r['start'] or walks['goal']!=r['goal']
                or walks['parent_terrain_proof_sha256']!=r['parent_proof_sha256']
                or sha256(encoded(declaration)).hexdigest()!=r['contact_hypothesis_sha256']
                or walks['contact_hypothesis_sha256']!=r['contact_hypothesis_sha256']
                or not 1<=len(walks['accepted_envelopes'])<=128):
            raise ValueError('Matching bounded conditional contact corridor required')
        cells=[];previous=r['start']
        for i,row in enumerate(walks['accepted_envelopes']):
            e=row['contact_envelope'];floor=row['terrain'];occupancy=e['other_surface_occupancy']
            footprint=rational(e['footprint']);base=F(e['reference_height_exact'])
            band=tuple(F(v) for v in e['region_body_band_exact']);classes=e['native']['possible_classes']
            a,b=tuple(row['start']),tuple(row['end'])
            if not xy(a) or not xy(b) or a==b:
                raise ValueError('Contact cell needs distinct finite endpoints')
            length=math.dist(a,b)
            checked_end=tuple(b[k]+runout*(b[k]-a[k])/length for k in (0,1))
            if (row['start']!=previous or floor['candidate'] is not True
                    or length+runout>40 or tuple(row.get('checked_end',b))!=checked_end
                    or footprint!=rational(swept_square(a,checked_end,r['checked_radius']))
                    or e['reference_terrain_proof_sha256']!=floor['proof_sha256']
                    or e['source_wld_sha256']!=r['source_wld_sha256']
                    or e['contact_hypothesis']!=declaration
                    or e['contact_hypothesis_sha256']!=r['contact_hypothesis_sha256']
                    or e['envelope_clear'] is not True or occupancy['candidate'] is not True
                    or F(e['maximum_contact_rise_exact'])!=F(rise)
                    or F(occupancy['hypothetical_body_height'])<F(self.body_height)+F(rise)
                    or len(band)!=2 or band[0]>base or band[1]<base+F(self.body_height)+F(rise)+F(.01)
                    or not 3<=len(footprint)<=64 or hull(footprint)!=footprint or area(footprint)<=0
                    or not e['native']['complete'] or not classes
                    or any(c['flags']!=0 or c['class_id']!=0 for c in classes)
                    or not e['bsp']['candidate'] and e['bsp']['reason']!='missing_bsp_child'):
                raise ValueError('Contact cell lacks complete consistent body and region coverage')
            cells.append(ContactCell(i,footprint,base,band));previous=row['end']
        if previous!=r['goal'] or len({c.reference_height for c in cells})!=1:
            raise ValueError('Contact corridor must reach its exact goal on one flat terrain reference')
        self.cells=tuple(cells);base=cells[0].reference_height
        self.height=(base,base+F(rise));sheets=[]
        for face in declaration['faces']:
            points=tuple((F(y),F(x),F(z)) for x,y,z in face['vertices_wld'])
            polygon=hull(p[:2] for p in points);heights={p[2] for p in points}
            if (face['flag']!=0 or face['material_class'] not in ('Diffuse','TransparentMasked')
                    or len(polygon)!=3 or len(heights)!=1
                    or not base<points[0][2]<=self.height[1]):
                raise ValueError('Declared contact sheet must retain its exact bounded flat height')
            sheets.append(ContactSheet((face['fragment'],face['face']),polygon,points[0][2]))
        if not 1<=len(sheets)<=16 or len({s.identifier for s in sheets})!=len(sheets):
            raise ValueError('Bounded unique declared contact sheets required')
        self.sheets=tuple(sheets);self._values=self._snapshot()

    def _snapshot(self):
        return (self.body_radius,self.body_height,self.height,
                tuple((id(c),c.index,c.footprint,c.reference_height,c.region_band) for c in self.cells),
                tuple((id(s),s.identifier,s.footprint,s.height) for s in self.sheets))

    def check(self):
        if (self.plan is not self._plan[0] or self.plan.payload is not self._plan[1]
                or self.plan.sha256!=self._plan[2] or self._snapshot()!=self._values):
            raise ValueError('Contact plan or coverage index changed')

    def _bounds(self,bounds):
        if (type(bounds) is not RouteMotionBounds or bounds.body_radius!=self.body_radius
                or bounds.body_height!=self.body_height):
            raise ValueError('Matching contact body bounds required')
        bounds.validate_values(calibration_record_id=bounds.calibration_record_id,maximum_step_seconds=.2)

    def compatible(self,point,bounds,*,height_interval):
        """Retain all locally supported heights for an unissued raw observation.

        Callers must bind replies/arrival to their original calibration and
        receipt. This geometry query never snaps a fix or renews calibration.
        Future movement/pivot reach cannot justify present elevation.
        """
        self.check()
        self._bounds(bounds)
        if (type(height_interval) is not tuple or len(height_interval)!=2
                or not all(isinstance(v,F) or finite(v) for v in height_interval)
                or height_interval[0]>height_interval[1]):
            raise ValueError('Ordered finite observed height interval required')
        observed=tuple(F(v) for v in height_interval);b=bounds
        origin=rational(motion_footprint(point,0.,0.,position_error=b.position_error,
            heading_error_degrees=0.,post_release_drift=b.post_release_drift,extra_radius=b.body_radius))
        cells=tuple(c for c in self.cells if intersection(origin,c.footprint))
        if not cells or not covers_closed(origin,tuple(c.footprint for c in cells)):
            return ()
        states=[]
        def retain(kind,ids,height):
            low,high=max(observed[0],height[0]),min(observed[1],height[1])
            if low<=high:states.append(ContactCompatibility(kind,ids,(low,high)))
        retain('terrain',(),(self.height[0],self.height[0]))
        for height in sorted({s.height for s in self.sheets}):
            group=tuple(s for s in self.sheets if s.height==height)
            touched=tuple(s for s in group if intersection(origin,s.footprint))
            if not touched:continue
            ids=tuple(s.identifier for s in touched)
            retain('sheet_top',ids,(height,height))
            if not covers_closed(origin,tuple(s.footprint for s in group)):
                retain('sheet_edge_transition',ids,(self.height[0],height))
        self.check()
        return tuple(states)

    def cover_pulse(self,point,heading,kind,bounds,*,height_interval):
        self.check();self._bounds(bounds)
        if kind not in ('forward','left','right'):raise ValueError('Bounded contact controls required')
        b=bounds;reach=b.forward_speed_upper_bound*b.maximum_actual_hold if kind=='forward' else 0.
        pivot=0. if kind=='forward' else b.pivot_displacement_upper_bound
        footprint=motion_footprint(point,heading,reach,position_error=b.position_error,
            heading_error_degrees=b.heading_error_degrees,post_release_drift=b.post_release_drift,
            extra_radius=b.body_radius+pivot)
        # A body's covered area cannot authorize extra translation of its
        # center. Preserve exact closed point/line cases when uncertainty is zero.
        center_radius=(b.position_error+b.post_release_drift+pivot
                       +2*reach*math.sin(math.radians(b.heading_error_degrees)/2))
        if center_radius:
            centers=motion_footprint(point,heading,reach,position_error=b.position_error,
                heading_error_degrees=b.heading_error_degrees,post_release_drift=b.post_release_drift,
                extra_radius=pivot)
        else:
            angle=math.radians(heading)
            centers=closed_hull((point,(point[0]+reach*math.sin(angle),point[1]+reach*math.cos(angle))))
        body=rational(footprint)
        cells=tuple(c for c in self.cells if intersection(body,c.footprint))
        if not cells or not covers_closed(body,tuple(c.footprint for c in cells)):
            raise ValueError('Whole maximum-hold body motion leaves the checked contact corridor')
        compatible=self.compatible(point,bounds,height_interval=height_interval)
        if not compatible:raise ValueError('Observed height has no compatible local contact state')
        # Every cell encloses the entire possible vertical band, even if this
        # observation intersects just one height. No state may be discarded
        # because its body is harder to cover, and no sheet becomes a floor.
        self.check()
        record=dict(format='eql-source-contact-pulse-coverage-v1',contact_plan_sha256=self.plan.sha256,
            point=point,heading=heading,kind=kind,motion_bounds=asdict(bounds),body_footprint=footprint,
            center_footprint_exact=[[str(F(v)) for v in p] for p in centers],
            observed_height_interval_exact=[str(F(v)) for v in height_interval],
            compatible=[dict(kind=c.kind,source_ids=c.source_ids,
                height_interval_exact=[str(v) for v in c.height_interval]) for c in compatible],
            possible_motion_height_interval_exact=[str(v) for v in self.height],cells=[c.index for c in cells],
            full_motion_coverage_checked=True,terrain_reference_only=True,
            contact_semantics_verified=False,source_execution_wired=False,
            input_authorized=False,real_client_accepted=False)
        payload=encoded(record)
        return ContactPulseCoverage(payload,sha256(payload).hexdigest())
