"""Discover projected source-boundary step proposals, without accepting travel.

Only full 3D edges with one eligible floor owner enter discovery. Exact
projected overlap, opposite interiors and bounded height differences produce
links between continuous-floor components. Every proposed cap/transfer still
needs the source floor, riser, body and static checks; BSP and real movement
remain separate. Absence of a link is not proof of physical disconnection.
"""
from collections import defaultdict, deque
from dataclasses import dataclass
from fractions import Fraction
from heapq import heappop, heappush
from itertools import combinations
from itertools import count
import math

from .source_floor_chain import rational
from .source_floor_components import SourceFloorComponents


@dataclass(frozen=True)
class StepLink:
    from_face: tuple
    to_face: tuple
    from_component: tuple
    to_component: tuple
    edge_from: tuple
    edge_to: tuple
    from_side: int
    along_axis: int
    along_interval: tuple
    height_differences: tuple
    inventory_sha256: str
    discovery_only: bool = True
    source_occupancy_checked: bool = False
    client_step_capability_verified: bool = False
    input_authorized: bool = False


@dataclass(frozen=True)
class StepCaps:
    start: tuple
    end: tuple
    landing_seed_ids: tuple
    crossing_exact: tuple
    discovery_only: bool = True


def _cross(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def _at(edge, axis, value):
    a, b = edge
    t = (value-a[axis])/(b[axis]-a[axis])
    return tuple(a[k]+t*(b[k]-a[k]) for k in range(3))


def discover_step_links(sources, *, inventory_sha256, max_step_height,
                        min_width=0., max_pairs=1_000_000, include_internal_edges=False):
    """Return directed proposals with exact clipped height-gap intervals.

    Long edges are split at gap zero and both height limits; a valid partial
    interval survives even if the remainder exceeds the limit. Shared or
    ambiguous full edges are already represented in the ordinary component
    graph and are excluded by default. The explicit internal-edge option also
    proposes crossings from two-owner edges: a lower floor can continue under
    a raised platform. Opposite interiors, gap and width checks still apply;
    the complete step checker must retain the underlay and verify a real riser.
    Ambiguous edges with more than two owners remain excluded from discovery.
    All source surfaces remain in later checks.
    """
    if (any(type(v) not in (int, float) or not math.isfinite(v)
            for v in (max_step_height, min_width))
            or not 0 < max_step_height <= 4 or not 0 <= min_width <= 20
            or type(include_internal_edges) is not bool
            or type(max_pairs) is not int or not 1 <= max_pairs <= 10_000_000):
        raise ValueError('Invalid source step discovery bounds')
    graph = SourceFloorComponents(sources, inventory_sha256=inventory_sha256)
    bound, width = Fraction(max_step_height), Fraction(min_width)
    edges = defaultdict(list)
    for source in sources:
        identity = (source.fragment, source.face)
        if identity not in graph.components:
            continue
        points = rational(tuple((y, x, z) for x, y, z in source.vertices_wld))
        for i, a in enumerate(points):
            b, third = points[(i+1) % 3], points[(i+2) % 3]
            if a[:2] != b[:2]:
                edges[tuple(sorted((a, b)))].append((identity, a, b, third))
    lines = defaultdict(list)
    for owners in edges.values():
        if len(owners) != 1 and not (include_internal_edges and len(owners) == 2):
            continue
        for identity, a, b, third in owners:
            axis = 0 if abs(b[0]-a[0]) >= abs(b[1]-a[1]) else 1
            other = 1-axis
            slope = (b[other]-a[other])/(b[axis]-a[axis])
            intercept = a[other]-slope*a[axis]
            lines[(axis, slope, intercept)].append((identity, a, b, third))
    links, pairs = [], 0
    for (axis, slope, _), members in sorted(lines.items()):
        for left, right in combinations(sorted(members), 2):
            pairs += 1
            if pairs > max_pairs:
                raise ValueError('Source step pair budget exceeded; no complete discovery returned')
            face_a, a, b, third_a = left
            face_b, c, d, third_b = right
            ca, cb = graph.components[face_a], graph.components[face_b]
            if ca == cb or _cross(a, b, third_a)*_cross(a, b, third_b) >= 0:
                continue
            lo = max(min(a[axis], b[axis]), min(c[axis], d[axis]))
            hi = min(max(a[axis], b[axis]), max(c[axis], d[axis]))
            if lo >= hi:
                continue
            gap = lambda s: _at((c, d), axis, s)[2]-_at((a, b), axis, s)[2]
            gl, gh = gap(lo), gap(hi)
            cuts = {lo, hi}
            if gl != gh:
                for height in (-bound, Fraction(0), bound):
                    root = lo+(height-gl)*(hi-lo)/(gh-gl)
                    if lo < root < hi:
                        cuts.add(root)
            ordered = sorted(cuts)
            for start, end in zip(ordered, ordered[1:]):
                middle = gap((start+end)/2)
                if not 0 < abs(middle) <= bound:
                    continue
                if (end-start)**2*(1+slope*slope) < width*width:
                    continue
                for f, t, fc, tc, origin, dest, third, sign in (
                    (face_a, face_b, ca, cb, (a,b), (c,d), third_a, 1),
                    (face_b, face_a, cb, ca, (c,d), (a,b), third_b, -1),
                ):
                    links.append(StepLink(f, t, fc, tc,
                        tuple(tuple(str(v) for v in p) for p in origin),
                        tuple(tuple(str(v) for v in p) for p in dest),
                        1 if _cross(*origin, third) > 0 else -1, axis,
                        (str(start), str(end)),
                        (str(sign*gap(start)), str(sign*gap(end))), inventory_sha256))
    return tuple(sorted(links, key=lambda link: (
        link.from_component, link.to_component, link.from_face,
        link.to_face, tuple(Fraction(s) for s in link.along_interval))))


def propose_step_caps(link, *, radius, reserve=.1, fractions=(.5,.25,.75)):
    """Propose square caps fully to either side of the projected edge.

    The exact interval erosion covers the full expanded swept footprint's
    intersection with the edge. This does not prove either cap is supported:
    unrelated edges, narrow landings and collision surfaces must still reject.
    Returned floats are proposals only and get independently rechecked.
    """
    if (not isinstance(link, StepLink)
            or any(type(v) not in (int,float) or not math.isfinite(v) for v in (radius,reserve))
            or not .05 <= radius <= 10 or not .001 <= reserve <= 1
            or not isinstance(fractions, tuple) or not 1 <= len(fractions) <= 16
            or any(type(v) not in (int,float) or not math.isfinite(v) or not 0 < v < 1
                   for v in fractions)):
        raise ValueError('Invalid source step cap proposal')
    a,b = (tuple(Fraction(v) for v in p) for p in link.edge_from)
    dx,dy = b[0]-a[0],b[1]-a[1]
    norm2 = dx*dx+dy*dy
    l1 = abs(dx)+abs(dy)
    expanded_radius = Fraction(radius)+Fraction(.002)
    along_half = expanded_radius*l1*abs((dx,dy)[link.along_axis])/norm2
    lo,hi = (Fraction(v) for v in link.along_interval)
    lo,hi = lo+along_half,hi-along_half
    if lo >= hi:
        return ()
    offset = (expanded_radius+Fraction(reserve))*l1/norm2
    normal = (-dy*offset*link.from_side, dx*offset*link.from_side)
    proposals = []
    for fraction in fractions:
        s = lo+Fraction(fraction)*(hi-lo)
        crossing = _at((a,b),link.along_axis,s)
        start = tuple(float(crossing[k]+normal[k]) for k in range(2))
        end = tuple(float(crossing[k]-normal[k]) for k in range(2))
        proposals.append(StepCaps(start,end,(link.to_face,),tuple(str(v) for v in crossing[:2])))
    return tuple(proposals)


def candidate_component_path(links, start, goals):
    """Shortest discovery graph path; None means no proposal, not no route."""
    goals = set(goals)
    adjacent = defaultdict(list)
    for link in links:
        adjacent[link.from_component].append(link)
    queue = deque([(start, ())]); seen = {start}
    while queue:
        component, path = queue.popleft()
        if component in goals:
            return path
        for link in adjacent[component]:
            if link.to_component not in seen:
                seen.add(link.to_component)
                queue.append((link.to_component, path+(link,)))
    return None


def candidate_step_path(links, start_component, start, goals, goal, *, radius,
                        max_approach=80., max_expansions=4096):
    """Rank generated crossings by travel distance, keeping all goal layers.

    States retain their arrival point, since two links into one component can
    have very different onward distances. Euclidean approach cost is a search
    hint only; actual floor detours may fail or be longer. An absent result
    means no proposal within these bounds, never physical disconnection.
    """
    if (any(not isinstance(p,tuple) or len(p)!=2 or
            any(type(v) not in (int,float) or not math.isfinite(v) for v in p) for p in (start,goal))
            or type(max_approach) not in (int,float) or not math.isfinite(max_approach)
            or not 0 < max_approach <= 80 or type(max_expansions) is not int
            or not 1 <= max_expansions <= 16384):
        raise ValueError('Invalid bounded candidate path request')
    adjacent = defaultdict(list)
    for link in links:
        adjacent[link.from_component].extend((link,p) for p in propose_step_caps(link,radius=radius))
    goals = set(goals); serial = count(); initial = (start_component,start)
    queue = [(0.,next(serial),initial,())]; best = {initial:0.}
    expanded = 0
    while queue:
        cost,_,state,path = heappop(queue)
        if state is None: return path
        if cost != best[state]: continue
        if expanded >= max_expansions: return None
        expanded += 1
        component,position = state
        if component in goals and math.dist(position,goal) <= max_approach:
            heappush(queue,(cost+math.dist(position,goal),next(serial),None,path))
        for link,proposal in adjacent[component]:
            approach = math.dist(position,proposal.start)
            if approach > max_approach: continue
            following = (link.to_component,proposal.end)
            total = cost+approach+math.dist(proposal.start,proposal.end)
            if total >= best.get(following,math.inf): continue
            best[following] = total
            heappush(queue,(total,next(serial),following,path+((link,proposal),)))
    return None
