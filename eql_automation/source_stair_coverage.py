"""All-compatible contact states and coupled XY/height pulse containment.

This consumes an explicitly conditional contact plan. It is not a receipt,
current observation or input authorization; the runtime must supply those.
"""
from dataclasses import asdict,dataclass
from fractions import Fraction as F
from hashlib import sha256
import json
import math

from .ground_sweep import area,clip,cross,finite,hull,motion_footprint
from .native_region_policy import encoded
from .route_geometry import RouteMotionBounds
from .source_floor_chain import inside
from .source_stair_plan import SourceStairPlan
from .source_step_approach import covered_by_union


def closed_hull(points):
    points=tuple(sorted(set(points)))
    return points if len(points)<=2 else hull(points)


def intersection(a,b):return closed_hull(clip(a,b))


def covers_closed(target,polygons):
    """Do not lose point/edge contact by using positive-area coverage alone."""
    if not target:return True
    if not 1<=len(polygons)<=32:raise ValueError('Bounded local stair cell coverage required')
    if len(target)>=3 and area(target)>0:
        full=tuple(p for p in polygons if len(p)>=3 and area(p)>0)
        return bool(full) and covered_by_union(target,full)
    def contains(point,poly):
        if len(poly)==1:return point==poly[0]
        if len(poly)==2:
            a,b=poly
            return cross(a,b,point)==0 and all(min(a[k],b[k])<=point[k]<=max(a[k],b[k]) for k in (0,1))
        return bool(poly) and inside(point,poly)
    if len(target)==1:return any(contains(target[0],p) for p in polygons)
    a,b=target[0],target[-1];intervals=[]
    for poly in polygons:
        if not poly:continue
        if len(poly)==1:
            if contains(poly[0],(a,b)):
                axis=0 if a[0]!=b[0] else 1
                t=(poly[0][axis]-a[axis])/(b[axis]-a[axis]);intervals.append((t,t))
            continue
        low,high=F(0),F(1)
        for i,p in enumerate(poly):
            q=poly[(i+1)%len(poly)];base=cross(p,q,a);slope=cross(p,q,b)-base
            if slope==0:
                if base<0:low,high=F(1),F(0);break
            elif slope>0:low=max(low,-base/slope)
            else:high=min(high,-base/slope)
        if len(poly)==2 and low<=high:
            # The two edge half-planes describe an infinite line. Clip its
            # parameter to the actual segment as well, retaining exact endpoints.
            axis=0 if poly[0][0]!=poly[1][0] else 1
            start,end=sorted((poly[0][axis],poly[1][axis]))
            delta=b[axis]-a[axis]
            if delta:
                p,q=sorted(((start-a[axis])/delta,(end-a[axis])/delta))
                low,high=max(low,p),min(high,q)
            elif not start<=a[axis]<=end:low,high=F(1),F(0)
        if low<=high:intervals.append((low,high))
    end=F(0)
    for low,high in sorted(intervals):
        if low>end:return False
        end=max(end,high)
        if end>=1:return True
    return False


def _polygon(values):
    polygon=tuple(tuple(F(v) for v in p) for p in values)
    if not 3<=len(polygon)<=64 or closed_hull(polygon)!=polygon or area(polygon)<=0:
        raise ValueError('Exact convex cached stair polygon required')
    return polygon


@dataclass(frozen=True)
class StairContactState:
    index: int
    kind: str
    treads: tuple
    polygons: tuple
    height: tuple


@dataclass(frozen=True)
class StairContactCell:
    index: int
    centers: tuple
    body: tuple
    height: tuple
    collision: tuple
    region: tuple


@dataclass(frozen=True)
class StairCompatibility:
    state_index: int
    height_interval: tuple


@dataclass(frozen=True)
class StairPulseCoverage:
    payload: bytes
    sha256: str

    def record(self):
        if type(self.payload) is not bytes or sha256(self.payload).hexdigest()!=self.sha256:
            raise ValueError('Stair pulse coverage seal changed')
        record=json.loads(self.payload)
        if encoded(record)!=self.payload:raise ValueError('Stair pulse coverage encoding changed')
        return record


class SourceStairContactIndex:
    def __init__(self,plan):
        if type(plan) is not SourceStairPlan:raise ValueError('Exact sealed source stair plan required')
        record=plan.record();flight=record['flight']
        if (record.get('vertical_model')!='bounded_source_contacts'
                or flight.get('kind')!='bounded_source_stair_contacts' or flight.get('candidate') is not True
                or record.get('input_authorized') is not False or record.get('executable_itinerary') is not False):
            raise ValueError('Grounded motion requires the distinct bounded contact model')
        self.plan=plan;self._plan=(plan,plan.payload,plan.sha256)
        self.body_radius=flight['body_radius'];self.body_height=flight['body_height']
        self.body_extent=F(flight['body_half_extent_exact'])
        self.corridor=_polygon(flight['center_corridor_exact'])
        self.states=tuple(StairContactState(row['index'],row['kind'],tuple(row['treads']),
            tuple(_polygon(p) for p in row['center_polygons_exact']),
            tuple(F(v) for v in row['height_interval_exact'])) for row in flight['states'])
        self.cells=tuple(StairContactCell(row['index'],_polygon(row['center_footprint_exact']),
            _polygon(row['footprint_exact']),tuple(F(v) for v in row['base_interval_exact']),
            tuple(F(v) for v in row['collision_band_exact']),tuple(F(v) for v in row['region_band_exact']))
            for row in flight['phases'])
        n=len(flight['topology']['treads'])
        if (not 2<=n<=32 or len(self.states)!=2*n-1 or not 1<=len(self.cells)<=128
                or any(s.index!=i or s.height[0]>s.height[1] for i,s in enumerate(self.states))
                or any(c.index!=i or c.height[0]>c.height[1] for i,c in enumerate(self.cells))
                or any(s.kind!='ground' or s.treads!=(i,) or s.height[0]!=s.height[1]
                    for i,s in enumerate(self.states[:n]))
                or any(s.kind!='transition' or s.treads!=(i,i+1)
                    for i,s in enumerate(self.states[n:]))):
            raise ValueError('Complete ordered bounded stair states and cells required')
        neighbors=[set() for _ in self.states]
        for i in range(n-1):
            for ground in (i,i+1):neighbors[ground].add(n+i);neighbors[n+i].add(ground)
            if i+1<n-1:
                neighbors[n+i].add(n+i+1);neighbors[n+i+1].add(n+i)
        self.neighbors=tuple(tuple(sorted(v)) for v in neighbors)
        self._values=self._snapshot()

    def _snapshot(self):
        return (self.body_radius,self.body_height,self.body_extent,self.corridor,
                tuple((s.index,s.kind,s.treads,s.polygons,s.height) for s in self.states),
                tuple((c.index,c.centers,c.body,c.height,c.collision,c.region) for c in self.cells),
                self.neighbors)

    def check(self):
        if (self.plan is not self._plan[0] or self.plan.payload is not self._plan[1]
                or self.plan.sha256!=self._plan[2]
                or self._snapshot()!=self._values):
            raise ValueError('Stair contact index changed')

    def compatible(self,centers,height_interval):
        self.check();low,high=map(F,height_interval)
        if low>high:raise ValueError('Ordered observed height interval required')
        result=[]
        for state in self.states:
            lo,hi=max(low,state.height[0]),min(high,state.height[1])
            if lo<=hi and any(intersection(centers,p) for p in state.polygons):
                result.append(StairCompatibility(state.index,(lo,hi)))
        return tuple(result)

    def cover_pulse(self,point,heading,kind,bounds,*,height_interval):
        self.check()
        if (type(bounds) is not RouteMotionBounds or kind not in ('forward','left','right')
                or type(point) is not tuple or len(point)!=2 or not all(finite(v) for v in point)
                or not finite(heading) or not 0<=heading<360
                or bounds.body_radius!=self.body_radius or bounds.body_height!=self.body_height):
            raise ValueError('Matching body bounds and bounded stair controls required')
        bounds.validate_values(calibration_record_id=bounds.calibration_record_id,maximum_step_seconds=.2)
        b=bounds;reach=b.forward_speed_upper_bound*b.maximum_actual_hold if kind=='forward' else 0.
        pivot=0. if kind=='forward' else b.pivot_displacement_upper_bound
        options=dict(position_error=b.position_error,heading_error_degrees=b.heading_error_degrees,
                     post_release_drift=b.post_release_drift)
        body=motion_footprint(point,heading,reach,extra_radius=b.body_radius+pivot,**options)
        radius=b.position_error+b.post_release_drift+pivot+2*reach*math.sin(math.radians(b.heading_error_degrees)/2)
        if radius:
            centers=motion_footprint(point,heading,reach,extra_radius=pivot,**options)
        else:
            angle=math.radians(heading)
            centers=closed_hull((point,(point[0]+reach*math.sin(angle),point[1]+reach*math.cos(angle))))
        centers=tuple(tuple(F(v) for v in p) for p in centers)
        if b.position_error+b.post_release_drift:
            origin=tuple(tuple(F(v) for v in p) for p in motion_footprint(point,0.,0.,
                position_error=b.position_error,heading_error_degrees=0.,post_release_drift=b.post_release_drift))
        else:origin=(tuple(map(F,point)),)
        compatible=self.compatible(origin,height_interval)
        if not compatible:raise ValueError('No compatible grounded or adjacent stair state')
        if not covers_closed(centers,(self.corridor,)):
            raise ValueError('Whole center motion leaves the cached stair corridor')
        domains={s.index:tuple(part for p in s.polygons if (part:=intersection(centers,p)))
                 for s in self.states}
        present={i for i,parts in domains.items() if parts}
        reachable=set();roots=[]
        for candidate in compatible:
            seen=set();pending=[candidate.state_index]
            while pending:
                i=pending.pop()
                if i in seen or i not in present:continue
                seen.add(i)
                # Narrow tread strips can overlap before the center reaches
                # the middle tread. No uniquely grounded intermediate fix is
                # required, but a shared closed XY/height state is required.
                for neighbor in self.neighbors[i]:
                    a,z=self.states[i].height,self.states[neighbor].height
                    if (max(a[0],z[0])<=min(a[1],z[1])
                            and any(intersection(piece,poly) for piece in domains[i]
                                    for poly in self.states[neighbor].polygons)):
                        pending.append(neighbor)
            polygons=tuple(p for i in sorted(seen) for p in self.states[i].polygons
                           if intersection(centers,p))
            if not polygons or not covers_closed(centers,polygons):
                raise ValueError('A retained stair state cannot cover the complete possible motion')
            roots.append(dict(state=candidate.state_index,reachable=sorted(seen)))
            reachable.update(seen)
        proofs=[];used=set()
        for i in sorted(reachable):
            state=self.states[i];low,high=state.height
            for domain in domains[i]:
                cells=[]
                for cell in self.cells:
                    part=intersection(domain,cell.centers)
                    if not part or not cell.height[0]<=low<=high<=cell.height[1]:continue
                    if (not cell.collision[0]<=low-F(.1)-F(.01)
                            or not high+F(self.body_height)+F(.01)<=cell.collision[1]
                            or not cell.region[0]<=low or not high+F(self.body_height)+F(.01)<=cell.region[1]):
                        continue
                    volume=hull((p[0]+dx,p[1]+dy) for p in part
                                for dx in (-self.body_extent,self.body_extent)
                                for dy in (-self.body_extent,self.body_extent))
                    if all(inside(p,cell.body) for p in volume):cells.append(cell)
                if not cells or not covers_closed(domain,tuple(c.centers for c in cells)):
                    raise ValueError('Uncovered coupled stair state/body/height enclosure')
                used.update(c.index for c in cells)
                proofs.append(dict(state=i,center_piece_exact=[[str(v) for v in p] for p in domain],
                    base_interval_exact=[str(low),str(high)],cells=[c.index for c in cells]))
        if not covered_by_union(body,tuple(self.cells[i].body for i in sorted(used))):
            raise ValueError('Full body motion footprint leaves the checked contact cells')
        self.check()
        record=dict(format='eql-source-stair-pulse-coverage-v1',stair_plan_sha256=self.plan.sha256,
            point=point,heading=heading,kind=kind,motion_bounds=asdict(bounds),
            body_footprint=body,center_footprint_exact=[[str(v) for v in p] for p in centers],
            observed_height_interval_exact=[str(F(v)) for v in height_interval],
            compatible=[dict(state=v.state_index,height_interval_exact=[str(z) for z in v.height_interval])
                        for v in compatible],reachable_by_start=roots,coupled_enclosures=proofs,
            full_motion_coverage_checked=True,conditional_contact_semantics=True,
            client_step_capability_verified=False,source_execution_wired=False,
            input_authorized=False,real_client_accepted=False)
        payload=encoded(record)
        return StairPulseCoverage(payload,sha256(payload).hexdigest())
