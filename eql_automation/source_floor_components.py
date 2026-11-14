"""Overapproximate exact-edge floor connectivity for offline search pruning.

Every full 3D edge joins its eligible owners, including ambiguous branches.
Consequently a possible connection is only a hint. An absent connection rules
out the current continuous-floor model, not physical movement or a step model.
"""
from dataclasses import dataclass
import math

from .ground_sweep import finite,hull
from .portal_precision import SourceFace,plane
from .source_floor_chain import inside,rational


@dataclass(frozen=True)
class FloorConnectivity:
    possible: bool
    reason: str
    prefix_component: tuple
    goal_faces: tuple
    goal_components: tuple
    overapproximate_graph_only: bool = True
    physical_disconnection_proven: bool = False


class SourceFloorComponents:
    def __init__(self,sources,*,inventory_sha256):
        if not isinstance(sources,tuple) or not 1<=len(sources)<=1_000_000:
            raise ValueError('Complete source inventory required')
        self.inventory_sha256=inventory_sha256
        parents={};edges={};self.faces={};identities=set()
        for source in sources:
            if not isinstance(source,SourceFace):raise ValueError('Invalid source face')
            key=(source.fragment,source.face)
            if key in identities:raise ValueError('Duplicate source identity')
            identities.add(key)
            points=tuple((y,x,z) for x,y,z in source.vertices_wld)
            surface=plane(points)
            if source.flag!=0 or source.material_class!='Diffuse' or surface is None or math.hypot(*surface[:2])>1.:continue
            polygon=hull(p[:2] for p in points)
            if len(polygon)!=3:continue
            parents[key]=key
            self.faces[key]=(polygon,tuple(min(p[k] for p in polygon) for k in range(2)),
                                     tuple(max(p[k] for p in polygon) for k in range(2)))
            for i,p in enumerate(points):
                q=points[(i+1)%3]
                if p[:2]!=q[:2]:edges.setdefault(tuple(sorted((p,q))),[]).append(key)
        def root(key):
            while parents[key]!=key:
                parents[key]=parents[parents[key]];key=parents[key]
            return key
        for owners in edges.values():
            first=root(owners[0])
            for owner in owners[1:]:
                other=root(owner)
                if first!=other:
                    low,high=sorted((first,other));parents[high]=low;first=low
        self.components={key:root(key) for key in parents}
        self.face_count=len(self.faces);self.component_count=len(set(self.components.values()))

    def goal(self,prefix,point):
        if (prefix.inventory_sha256!=self.inventory_sha256 or prefix.halted or prefix.previous is None
                or not isinstance(point,tuple) or len(point)!=2 or not all(finite(v) for v in point)):
            raise ValueError('Matching active floor prefix and finite goal required')
        current={self.components[k] for k in prefix.previous.selected_ids}
        if len(current)!=1:raise ValueError('Floor prefix does not have one graph component')
        component=next(iter(current));exact=rational((point,))[0];hits=[]
        for key,(polygon,low,high) in self.faces.items():
            if all(low[k]<=point[k]<=high[k] for k in range(2)) and inside(exact,rational(polygon)):
                hits.append(key)
        regions=tuple(sorted({self.components[k] for k in hits}))
        possible=component in regions
        reason=('same_overapproximate_floor_component' if possible else
                'different_exact_edge_floor_component' if hits else 'no_supported_floor_at_goal')
        return FloorConnectivity(possible,reason,component,tuple(sorted(hits)),regions)
