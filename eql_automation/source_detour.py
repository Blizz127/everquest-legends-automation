"""Bounded offline rerouting over complete copied-source swept footprints.

Grid points are search proposals, never walkability evidence. Every proposed
edge checks the connected terrain floor and all static geometry. Node states
end with a fixed square footprint and keep the selected source layer, so a
search cannot merge an upstairs and downstairs visit to the same XY point.
BSP regions, dynamic obstacles and real movement are outside this result.
"""
from collections import Counter
from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count
import math
import time

from .ground_sweep import hull
from .source_floor_chain import SourceFloorChain
from .static_floor_guard import check_source_static_floor


def swept_square(start, end, radius):
    return hull((p[0]+dx,p[1]+dy) for p in (start,end)
                for dx in (-radius,radius) for dy in (-radius,radius))


@dataclass(frozen=True)
class DetourCell:
    start: tuple
    end: tuple
    footprint: tuple
    terrain: object
    static: object


@dataclass(frozen=True)
class SourceDetour:
    candidate: bool
    reason: str
    points: tuple = ()
    cells: tuple = ()
    expanded: int = 0
    attempted_edges: int = 0
    refusals: tuple = ()
    bsp_classified: bool = False
    real_client_accepted: bool = False
    input_authorized: bool = False


def find_source_detour(prefix, start, goal, terrain_view, static_view, *,
                       radius, spacing=2., padding=8., max_expansions=512,
                       max_seconds=30.):
    """Return a conditional route plus its independent accepted floor prefix.

    Search is confined to a padded start/goal rectangle. A failed or exhausted
    search returns no partial route. The supplied prefix is never advanced.
    """
    if (not isinstance(prefix,SourceFloorChain) or prefix.halted or prefix.previous is None
            or any(not isinstance(p,tuple) or len(p)!=2
                   or any(type(v) not in (int,float) or not math.isfinite(v) for v in p)
                   for p in (start,goal))
            or any(type(v) not in (int,float) or not math.isfinite(v)
                   for v in (radius,spacing,padding,max_seconds))
            or not .05<=radius<=10 or not .25<=spacing<=4 or not 0<=padding<=32
            or not 0<max_seconds<=120 or math.dist(start,goal)>80
            or type(max_expansions) is not int or not 1<=max_expansions<=4096):
        raise ValueError('Invalid bounded source detour request')
    if getattr(terrain_view,'wld_sha256',None)!=prefix.inventory_sha256:
        raise ValueError('Detour terrain does not match the accepted floor inventory')
    began=time.monotonic();expanded=0;attempted=0;refusals=Counter()
    def result(ok,reason,points=(),cells=(),chain=None):
        return (SourceDetour(ok,reason,points,cells,expanded,attempted,
                             tuple(sorted(refusals.items()))),chain)
    def check(chain,a,b):
        footprint=swept_square(a,b,radius)
        try:
            sources=terrain_view.source_faces_for_footprint(footprint)
            step=chain.advance(footprint,sources)
            if not step.candidate:
                refusals[step.reason]+=1;return None
            placed=check_source_static_floor(step,footprint,sources,static_view)
            if not placed.candidate:
                refusals[placed.reason]+=1;return None
        except ValueError:
            refusals['source_query_refused']+=1;return None
        return DetourCell(a,b,footprint,step,placed)
    def edge(chain,a,b):
        nonlocal attempted
        attempted+=1
        branch=chain.fork();sweep=check(branch,a,b)
        if sweep is None:return None
        # Canonical endpoint footprints make layer-aware node equivalence
        # independent of which swept edge reached the point.
        endpoint=check(branch,b,b)
        if endpoint is None:return None
        return branch,(sweep,endpoint)
    initial=prefix.fork();first=check(initial,start,start)
    if first is None:return result(False,'detour_start_refused')
    if start==goal:return result(True,'conditional_source_detour_only',(start,),(first,),initial)
    lower=tuple(min(a,b)-padding for a,b in zip(start,goal))
    upper=tuple(max(a,b)+padding for a,b in zip(start,goal))
    key=((0,0),initial.previous.selected_ids)
    # Queue entries retain their own branch and ancestry. Improved visits
    # cannot replace the proof prefix held by a previously queued successor.
    serial=count();queue=[];best={key:0.}
    heappush(queue,(math.dist(start,goal),next(serial),0.,(0,0),initial,(start,),(first,)))
    offsets=tuple((x,y) for x in (-1,0,1) for y in (-1,0,1) if x or y)
    while queue:
        if time.monotonic()-began>max_seconds:return result(False,'detour_time_budget_exceeded')
        if expanded>=max_expansions:return result(False,'detour_expansion_budget_exceeded')
        _,_,cost,node,chain,points,cells=heappop(queue)
        key=(node,chain.previous.selected_ids)
        if cost!=best.get(key):continue
        expanded+=1;here=points[-1]
        # Trying the full goal sweep permits a direct, checked rejoin instead
        # of requiring the exact goal to fall on this search lattice.
        direct=edge(chain,here,goal)
        if direct is not None:
            final,added=direct
            return result(True,'conditional_source_detour_only',points+(goal,),cells+added,final)
        for dx,dy in offsets:
            if time.monotonic()-began>max_seconds:return result(False,'detour_time_budget_exceeded')
            other=(node[0]+dx,node[1]+dy)
            point=tuple(start[k]+spacing*other[k] for k in range(2))
            if any(not lower[k]<=point[k]<=upper[k] for k in range(2)):continue
            checked=edge(chain,here,point)
            if checked is None:continue
            branch,added=checked;new_cost=cost+math.dist(here,point)
            key=(other,branch.previous.selected_ids)
            if new_cost>=best.get(key,math.inf):continue
            best[key]=new_cost
            heappush(queue,(new_cost+math.dist(point,goal),next(serial),new_cost,
                            other,branch,points+(point,),cells+added))
    return result(False,'no_source_detour_in_search_box')
