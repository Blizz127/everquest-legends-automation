"""Track one supporting terrain layer through ordered copied route cells.

The explicit seed and body dimensions are offline hypotheses. This follows
source face identities and exact 3D edges, never a nearest-height choice.
It checks every supplied source layer for occupancy but does not establish
that placed objects/dynamics were supplied, or authorize game input.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
from hashlib import sha256
import json
import math

from .ground_sweep import area, clip, cross, finite, hull
from .portal_precision import SourceFace, plane
from .source_occupancy import SourceOccupancy, check_selected_floor_clearance, clip_xyz
from .tile_rounding import digest


def rational(points):
    return tuple(tuple(Fraction(n) for n in p) for p in points)


def exact_plane(vertices):
    a,b,c = rational(vertices)
    denominator = cross(a,b,c)
    dx = ((b[2]-a[2])*(c[1]-a[1])-(c[2]-a[2])*(b[1]-a[1]))/denominator
    dy = ((b[0]-a[0])*(c[2]-a[2])-(c[0]-a[0])*(b[2]-a[2]))/denominator
    return dx,dy,a[2]-dx*a[0]-dy*a[1]


@dataclass(frozen=True)
class FloorJoin:
    first: tuple[int,int]
    second: tuple[int,int]
    edge: tuple[tuple[float,float,float],tuple[float,float,float]]


@dataclass(frozen=True)
class FloorChainStep:
    candidate: bool
    reason: str
    index: int
    selected_ids: tuple[tuple[int,int], ...] = ()
    carried_ids: tuple[tuple[int,int], ...] = ()
    joins: tuple[FloorJoin, ...] = ()
    occupancy: SourceOccupancy | None = None
    geometry_sha256: str = ''
    previous_sha256: str = ''
    proof_sha256: str = ''
    real_client_accepted: bool = False
    input_authorized: bool = False


class SourceFloorChain:
    """Fail-latched conditional chain; instantiate once per pinned route scan."""

    def __init__(self, *, inventory_sha256, seed_evidence_sha256, seed_ids, body_height):
        if (not digest(inventory_sha256) or not digest(seed_evidence_sha256)
                or not isinstance(seed_ids,tuple) or not 1<=len(seed_ids)<=32
                or any(not isinstance(k,tuple) or len(k)!=2 or any(type(v) is not int or v<0 for v in k)
                       for k in seed_ids)
                or len(set(seed_ids))!=len(seed_ids)
                or not finite(body_height) or not 0<body_height<=100):
            raise ValueError('Invalid copied floor seed or body hypothesis')
        self.inventory_sha256=inventory_sha256
        self.seed_evidence_sha256=seed_evidence_sha256
        self.seed_ids=seed_ids
        self.body_height=body_height
        self.index=0
        self.halted=False
        self.previous=None
        self._expanded=None
        self._selected={}

    def advance(self, footprint, sources):
        """Accept a whole footprint or latch refusal without advancing state."""
        previous_sha=self.previous.proof_sha256 if self.previous else self.seed_evidence_sha256
        def refuse(reason, *, ids=(), carried=(), joins=(), occupancy=None, geometry_sha=''):
            self.halted=True
            return FloorChainStep(False,reason,self.index,ids,carried,joins,occupancy,geometry_sha,previous_sha)
        if self.halted:
            return refuse('source_floor_chain_already_halted')
        if (not isinstance(footprint,tuple) or not 3<=len(footprint)<=64
                or any(not isinstance(p,tuple) or len(p)!=2 or not all(finite(v) for v in p) for p in footprint)
                or not isinstance(sources,tuple) or not 1<=len(sources)<=128):
            return refuse('invalid_cell_or_source_budget')
        boundary=hull(footprint)
        if len(boundary)!=len(footprint) or area(boundary)<=1e-7:
            return refuse('invalid_cell_footprint')
        expanded=hull((x+dx,y+dy) for x,y in boundary for dx in (-.002,.002) for dy in (-.002,.002))
        exact_boundary=rational(expanded)
        inventory={}
        patches={}
        for source in sources:
            if (not isinstance(source,SourceFace) or not isinstance(source.vertices_wld,tuple)
                    or len(source.vertices_wld)!=3
                    or any(not isinstance(p,tuple) or len(p)!=3 or not all(finite(v) for v in p)
                           for p in source.vertices_wld)
                    or type(source.fragment) is not int or type(source.face) is not int
                    or source.fragment<0 or source.face<0
                    or type(source.flag) is not int or not isinstance(source.material_class,str)):
                return refuse('invalid_source_face')
            key=(source.fragment,source.face)
            if key in inventory:
                return refuse('duplicate_source_identity')
            if key in self._selected and source!=self._selected[key][0]:
                return refuse('source_identity_changed')
            inventory[key]=source
            vertices=tuple((y,x,z) for x,y,z in source.vertices_wld)
            polygon=hull(p[:2] for p in vertices)
            surface=plane(vertices)
            if (source.flag!=0 or source.material_class!='Diffuse' or surface is None
                    or len(polygon)!=3 or math.hypot(*surface[:2])>1.):
                continue
            exact_polygon=rational(polygon)
            if area(clip(exact_polygon,exact_boundary))>0:
                patches[key]=(source,vertices,exact_polygon)
        geometry_sha=sha256(json.dumps({'footprint':footprint,'sources':[asdict(s) for s in sources]},
                                      sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if len(patches)>32:
            return refuse('floor_patch_budget_exceeded',geometry_sha=geometry_sha)
        overlap=None
        if self.previous is None:
            carried=tuple(sorted(self.seed_ids))
            if not set(carried)<=patches.keys():
                return refuse('seed_floor_missing_or_unsupported',geometry_sha=geometry_sha)
        else:
            overlap=clip(exact_boundary,self._expanded)
            if area(overlap)<=0:
                return refuse('successive_cells_do_not_overlap',geometry_sha=geometry_sha)
            carried=tuple(sorted(k for k in patches if k in self._selected
                                  and area(clip(patches[k][2],overlap))>0))
            if not carried:
                return refuse('no_shared_source_floor_with_previous_cell',geometry_sha=geometry_sha)

        # Only an exact, positive-length 3D edge inside this cell can connect
        # two local walkable triangles. Full-edge matching intentionally
        # refuses unsupported T-junctions. All other faces remain occupancy.
        owners={}
        for key,(_,vertices,_) in patches.items():
            for i in range(3):
                edge=tuple(sorted((vertices[i],vertices[(i+1)%3])))
                if edge[0][:2]!=edge[1][:2]:
                    owners.setdefault(edge,[]).append(key)
        adjacency={key:[] for key in patches}
        branches=set()
        for edge,keys in owners.items():
            portion=clip_xyz(rational(edge),exact_boundary)
            if len({p[:2] for p in portion})<2:
                continue
            if len(keys)>2:
                branches.update(keys)
            if len(keys)!=2:
                continue
            a,b=keys
            third_a=next(v for v in patches[a][1] if v not in edge)
            third_b=next(v for v in patches[b][1] if v not in edge)
            p,q=rational(edge)
            if cross(p,q,rational((third_a,))[0])*cross(p,q,rational((third_b,))[0])>=0:
                continue
            adjacency[a].append((b,edge));adjacency[b].append((a,edge))
        selected={carried[0]} if self.previous is None else set(carried)
        queue=list(selected);joins=[]
        while queue:
            key=queue.pop()
            if key in branches:
                return refuse('ambiguous_source_edge_branch',carried=carried,geometry_sha=geometry_sha)
            for neighbor,edge in adjacency[key]:
                if neighbor not in selected:
                    selected.add(neighbor);queue.append(neighbor)
                    joins.append(FloorJoin(key,neighbor,edge))
        if not set(carried)<=selected:
            return refuse('seed_faces_not_edge_connected',carried=carried,geometry_sha=geometry_sha)
        ids=tuple(sorted(selected));joins=tuple(joins)
        selection={'inventory':self.inventory_sha256,'seed':self.seed_evidence_sha256,
                   'previous':previous_sha,'cell_geometry':geometry_sha,'selected':ids,'carried':carried,
                   'joins':[asdict(j) for j in joins]}
        selection_sha=sha256(json.dumps(selection,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        occupancy=check_selected_floor_clearance(footprint,sources,selected_ids=ids,
                selection_evidence_sha256=selection_sha,body_height=self.body_height)
        if not occupancy.candidate:
            return refuse(occupancy.reason,ids=ids,carried=carried,joins=joins,
                          occupancy=occupancy,geometry_sha=geometry_sha)
        # Compare every positive-area patch in the complete cell overlap.
        # Sharing one old face somewhere is insufficient to exclude a fork
        # into a different physical layer elsewhere in that overlap.
        if overlap is not None:
            for _,old_vertices,old_polygon in self._selected.values():
                old_patch=clip(old_polygon,overlap)
                if area(old_patch)<=0:continue
                old_plane=exact_plane(old_vertices)
                for key in ids:
                    _,new_vertices,new_polygon=patches[key]
                    if area(clip(old_patch,new_polygon))>0 and exact_plane(new_vertices)!=old_plane:
                        return refuse('previous_overlap_floor_changed',ids=ids,carried=carried,joins=joins,
                                      occupancy=occupancy,geometry_sha=geometry_sha)
        values=dict(candidate=True,reason='conditional_connected_source_cell_only',index=self.index,
                    selected_ids=ids,carried_ids=carried,joins=joins,occupancy=occupancy,
                    geometry_sha256=geometry_sha,previous_sha256=previous_sha)
        proof=sha256(json.dumps({**selection,'result':asdict(FloorChainStep(**values))},
                               sort_keys=True,separators=(',',':')).encode()).hexdigest()
        result=FloorChainStep(**values,proof_sha256=proof)
        self.previous=result;self.index+=1
        self._expanded=exact_boundary
        self._selected={k:patches[k] for k in ids}
        return result

    def floor_at(self, package_xy):
        """Sample only the latest accepted cell's selected, connected floor."""
        if self.halted or self.previous is None:
            raise ValueError('No active conditional floor cell')
        if (not isinstance(package_xy,tuple) or len(package_xy)!=2 or not all(finite(v) for v in package_xy)):
            raise ValueError('Invalid source floor point')
        point=rational((package_xy,))[0]
        if any(cross(a,self._expanded[(i+1)%len(self._expanded)],point)<0
               for i,a in enumerate(self._expanded)):
            raise ValueError('Point outside the current checked cell')
        hits=[]
        for key,(_,vertices,polygon) in self._selected.items():
            if all(cross(a,polygon[(i+1)%3],point)>=0 for i,a in enumerate(polygon)):
                dx,dy,k=exact_plane(vertices)
                hits.append((dx*point[0]+dy*point[1]+k,key))
        if not hits or len({height for height,_ in hits})!=1:
            raise ValueError('Selected source floor missing or ambiguous')
        return float(hits[0][0]),tuple(f'wld:{key[0]}:face:{key[1]}' for _,key in sorted(hits))
