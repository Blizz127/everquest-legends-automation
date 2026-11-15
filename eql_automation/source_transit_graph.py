"""Long-distance proposals through exact source-face adjacency and step hints.

This graph is deliberately not a navigation permit. Face centers, shared-edge
midpoints and step caps are search hints. A consumer must carry one checked
floor lineage through terrain/static/region validation of the entire guide.
"""
from collections import defaultdict
from dataclasses import asdict, dataclass
from hashlib import sha256
from heapq import heappop, heappush
from itertools import combinations, count
import math
import time

from .ground_binding import finite
from .native_region_policy import encoded
from .portal_precision import plane
from .route_floor_commit import _chain_snapshot
from .source_floor_components import SourceFloorComponents
from .source_itinerary import SourceItineraryGuide, SourceStepHint, SourceWalkHint
from .source_step_links import StepLink, propose_step_caps
from .source_zones import source_zone_id


@dataclass(frozen=True)
class TransitEdge:
    identity: tuple
    origin: tuple
    destination: tuple
    points: tuple
    step: SourceStepHint | None = None

    @property
    def cost(self):
        return sum(math.dist(a,b) for a,b in zip(self.points,self.points[1:]))


@dataclass(frozen=True)
class SourceTransitProposal:
    start: tuple
    goal: tuple
    edges: tuple
    source_wld_sha256: str
    initial_floor_proof_sha256: str
    expanded: int
    discovery_only: bool = True
    input_authorized: bool = False
    real_client_accepted: bool = False

    def guide(self, *, static_inventory_sha256, radius, body_height, maximum_cell_length=2., zone='crushbone'):
        source_zone_id(zone)
        if not finite(maximum_cell_length) or not .25<=maximum_cell_length<=4:
            raise ValueError('Bounded source guide cells required')
        operations=[];point=self.start
        def walk(goal):
            nonlocal point
            a=point;n=max(1,math.ceil(math.dist(a,goal)/maximum_cell_length))
            for index in range(n):
                end=goal if index==n-1 else tuple(a[k]+(goal[k]-a[k])*(index+1)/n for k in (0,1))
                if len(operations)>=10000:raise ValueError('Source guide operation budget exceeded')
                operations.append(SourceWalkHint(point,end));point=end
        for edge in self.edges:
            if edge.step is not None:
                walk(edge.step.start);operations.append(edge.step);point=edge.step.end
                walk(edge.points[-1][:2])
            else:
                for xyz in edge.points[1:]:walk(xyz[:2])
        if point!=self.goal:raise ValueError('Source proposal did not end at the exact goal')
        result=SourceItineraryGuide(zone,self.source_wld_sha256,static_inventory_sha256,
            sha256(encoded(asdict(self))).hexdigest(),radius,body_height,self.goal,tuple(operations))
        result.validate();return result


class SourceTransitGraph:
    """Retain source-layer identities across long ordinary transit and steps."""
    def __init__(self,sources,*,inventory_sha256,step_links=(),radius=1.2,max_step_height=2.,max_lift=4.,max_edges=262144):
        if (not finite(radius) or not .05<=radius<=10 or not finite(max_step_height)
                or not finite(max_lift) or not 0<max_step_height<=4 or not max_step_height<=max_lift<=8
                or type(max_edges) is not int or not 1<=max_edges<=1_000_000):
            raise ValueError('Explicit bounded body/step hypotheses required')
        self.components=SourceFloorComponents(sources,inventory_sha256=inventory_sha256)
        self.inventory_sha256=inventory_sha256
        self.radius=radius;self.max_step_height=max_step_height;self.max_lift=max_lift
        self.points={};self.centers={};self.planes={};self.adjacent=defaultdict(list)
        edges=defaultdict(list)
        for face in sources:
            key=(face.fragment,face.face)
            if key not in self.components.components:continue
            vertices=tuple((y,x,z) for x,y,z in face.vertices_wld)
            self.points[key]=vertices;self.planes[key]=plane(vertices)
            self.centers[key]=tuple(sum(p[k] for p in vertices)/3 for k in range(3))
            for i,a in enumerate(vertices):
                b=vertices[(i+1)%3]
                if a[:2]!=b[:2]:edges[tuple(sorted((a,b)))].append(key)
        # Full 3D identity matters: a coincident upstairs XY edge is not an
        # ordinary neighbor. Ambiguous owners remain proposals and must fail
        # later if a complete footprint cannot retain a unique floor.
        edge_count=0
        for edge,owners in sorted(edges.items()):
            edge_count+=len(owners)*(len(owners)-1)
            if edge_count>max_edges:raise ValueError('Source transit edge budget exceeded')
            midpoint=tuple((edge[0][k]+edge[1][k])/2 for k in range(3))
            for first,second in combinations(sorted(owners),2):
                for a,b in ((first,second),(second,first)):
                    self.adjacent[a].append(TransitEdge(('walk',a,b,edge),a,b,
                        (self.centers[a],midpoint,self.centers[b])))
        for index,link in enumerate(step_links):
            if (type(link) is not StepLink or link.inventory_sha256!=inventory_sha256
                    or link.from_face not in self.points or link.to_face not in self.points
                    or self.components.components[link.from_face]!=link.from_component
                    or self.components.components[link.to_face]!=link.to_component):
                raise ValueError('Step discovery belongs to another source inventory/component')
            for cap_index,cap in enumerate(propose_step_caps(link,radius=radius)):
                edge_count+=1
                if edge_count>max_edges:raise ValueError('Source transit edge budget exceeded')
                hint=SourceStepHint(cap.start,cap.end,cap.landing_seed_ids,max_step_height,max_lift)
                points=(self.centers[link.from_face],self._xyz(link.from_face,cap.start),
                        self._xyz(link.to_face,cap.end),self.centers[link.to_face])
                self.adjacent[link.from_face].append(TransitEdge(('step',index,cap_index),
                    link.from_face,link.to_face,points,hint))
        self.adjacent={key:tuple(sorted(value,key=lambda e:repr(e.identity)))
                       for key,value in self.adjacent.items()}

    def _xyz(self,face,point):
        _,_,height=self.planes[face]
        return (*point,height(point))

    def propose(self,prefix,start,goal,*,excluded=(),start_via_edges=False,
                max_expansions=32768,max_seconds=30.,clock=time.monotonic):
        if (type(max_expansions) is not int or not 1<=max_expansions<=65536
                or type(start_via_edges) is not bool
                or not finite(max_seconds) or not 0<max_seconds<=120
                or not all(type(p) is tuple and len(p)==2 and all(finite(v) for v in p) for p in (start,goal))):
            raise ValueError('Finite bounded source transit search required')
        context=self.components.goal(prefix,goal);snapshot=_chain_snapshot(prefix)
        starts=tuple(prefix.previous.selected_ids);goals=set(context.goal_faces)
        if not goals:return None
        if any(face not in self.points for face in starts):raise ValueError('Unknown current source face')
        start_xyz=(*start,prefix.floor_at(start)[0]);root=('start',);finish=('goal',)
        excluded=set(excluded);serial=count();began=last=clock();expanded=0
        if not finite(began):raise ValueError('Invalid source transit clock')
        queue=[(math.dist(start,goal),next(serial),0.,root)];best={root:0.};parents={}
        while queue:
            now=clock()
            if not finite(now) or now<last:raise ValueError('Invalid source transit clock')
            if now-began>max_seconds:raise TimeoutError('Source transit proposal time budget exceeded')
            last=now
            _,_,cost,node=heappop(queue)
            if cost!=best[node]:continue
            if node==finish:
                path=[]
                while node!=root:
                    edge=parents[node];path.append(edge);node=edge.origin
                if _chain_snapshot(prefix)!=snapshot:raise ValueError('Source prefix changed during proposal')
                return SourceTransitProposal(start,goal,tuple(reversed(path)),self.inventory_sha256,
                    prefix.previous.proof_sha256,expanded)
            if expanded>=max_expansions:raise TimeoutError('Source transit proposal expansion budget exceeded')
            expanded+=1
            if node==root:
                edges=tuple(TransitEdge(('start',face),root,face,(start_xyz,self.centers[face])) for face in starts)
                if start_via_edges:
                    # A center is a search hint, not a required physical stop.
                    # Leave only an actually selected face through its existing
                    # exact 3D shared edge. Never shorten an explicit step.
                    edges+=tuple(TransitEdge(('start-via-edge',edge.identity),root,edge.destination,
                        (start_xyz,*edge.points[1:]))
                        for face in starts for edge in self.adjacent.get(face,())
                        if edge.step is None and edge.identity not in excluded)
            else:
                edges=self.adjacent.get(node,())
                if node in goals:
                    edges=(*edges,TransitEdge(('goal',node),node,finish,(self.centers[node],self._xyz(node,goal))))
            for edge in edges:
                if edge.identity in excluded:continue
                total=cost+edge.cost
                if total>=best.get(edge.destination,math.inf):continue
                best[edge.destination]=total;parents[edge.destination]=edge
                remaining=math.dist(edge.points[-1][:2],goal)
                heappush(queue,(total+remaining,next(serial),total,edge.destination))
        if _chain_snapshot(prefix)!=snapshot:raise ValueError('Source prefix changed during proposal')
        return None
