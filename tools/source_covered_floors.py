"""Exclude a lower graph face only with exact full upper-surface coverage.

The upper surface may use different triangle diagonals. Its clipped patches
must partition the entire lower triangle, with a strictly positive bounded
height gap at every patch vertex. Upper faces and other layers remain.
Full terrain, static, BSP and region checks still decide the final itinerary.
"""
from collections import defaultdict
from fractions import Fraction
import math

from eql_automation.ground_sweep import area, clip
from eql_automation.source_floor_chain import exact_plane, rational
from eql_automation.source_occupancy import exact_floor_partition


def covered_floor_exclusions(graph, *, body_height, face_ids=None,
                             maximum_pairs=100_000, check_context=lambda: None):
    if (type(body_height) not in (int, float) or not math.isfinite(body_height)
            or not 0 < body_height <= 100 or type(maximum_pairs) is not int
            or not 1 <= maximum_pairs <= 1_000_000):
        raise ValueError('Bounded covered-floor discovery required')
    selected = sorted(graph.points if face_ids is None else set(face_ids))
    if any(face not in graph.points for face in selected):
        raise ValueError('Unknown source face in covered-floor discovery')
    faces = graph.components.faces
    planes, polygons = {}, {}
    def plane(key):
        if key not in planes:
            planes[key] = exact_plane(graph.points[key])
        return planes[key]
    def polygon(key):
        if key not in polygons:
            polygons[key] = rational(faces[key][0])
        return polygons[key]
    # Float boxes only reject candidates; positive evidence uses exact supplied
    # coordinates. The caller checks lower faces lazily along its proposals.
    indexed = sorted((low[0], key, low, high) for key, (_, low, high) in faces.items())
    pairs, rejected = 0, {}
    for lower in selected:
        check_context()
        _, low, high = faces[lower]
        boundary = polygon(lower)
        bottom = plane(lower)
        groups = defaultdict(list)
        for _, upper, upper_low, upper_high in indexed:
            if upper_low[0] >= high[0]:
                break
            if (upper == lower or upper_high[0] <= low[0]
                    or upper_high[1] <= low[1] or upper_low[1] >= high[1]):
                continue
            pairs += 1
            if pairs > maximum_pairs:
                raise ValueError('Covered-floor pair budget exceeded; no exclusions returned')
            if pairs % 128 == 0:
                check_context()
            patch = clip(boundary, polygon(upper))
            if area(patch) <= 0:
                continue
            top = plane(upper)
            gaps = tuple((top[0]-bottom[0])*x + (top[1]-bottom[1])*y
                         + top[2]-bottom[2] for x, y in patch)
            if all(Fraction(.11) < gap <= Fraction(body_height) for gap in gaps):
                group = groups[graph.components.components[upper]]
                group.append((upper, patch, gaps))
                if len(group) > 64:
                    raise ValueError('Covered-floor patch budget exceeded; no exclusions returned')
        for component, patches in sorted(groups.items()):
            # Overlap must not compensate for a gap in the summed area.
            if not exact_floor_partition(boundary, tuple(p[1] for p in patches)):
                continue
            upper_ids = [p[0] for p in patches]
            rejected[lower] = dict(lower_face=lower,
                covering_face=upper_ids[0] if len(upper_ids) == 1 else None,
                covering_faces=upper_ids, covering_component=component,
                projected_triangle=faces[lower][0],
                patches=[dict(face=key, polygon_exact=[[str(v) for v in p] for p in patch],
                              height_gaps_exact=[str(gap) for gap in gaps])
                         for key, patch, gaps in patches],
                body_height=body_height, exact_partition_verified=True,
                conclusion='insufficient_headroom_on_this_lower_face',
                physical_disconnection_proven=False)
            break
    check_context()
    excluded = set()
    for face in rejected:
        excluded.add(('start', face)); excluded.add(('goal', face))
    for edges in graph.adjacent.values():
        excluded.update(edge.identity for edge in edges
                        if edge.origin in rejected or edge.destination in rejected)
    return excluded, dict(kind='exact_projected_covering_floor_exclusions',
        source_wld_sha256=graph.inventory_sha256, examined_pairs=pairs,
        examined_faces=selected,
        exclusions=list(rejected.values()), excluded_directed_edges=len(excluded),
        goal_layers_preserved_in_graph=True, current_floor_unchanged=True,
        input_authorized=False, real_client_accepted=False)


def propose_above_covered_floors(graph, prefix, start, goal, *, body_height,
                                rounds=16, maximum_pairs=100_000,
                                check_context=lambda: None, progress=lambda record: None):
    """Retry proposals after proving coverage on their lower faces.

    Inconclusive faces remain available. No failed cap, ambiguous partition or
    exhausted budget becomes a lower-face exclusion.
    """
    if (type(rounds) is not int or not 1 <= rounds <= 16
            or type(maximum_pairs) is not int or not 1 <= maximum_pairs <= 1_000_000):
        raise ValueError('Bounded covered-floor retries and pair budget required')
    excluded, checked, records, attempts, pairs = set(), set(), [], [], 0
    def report():
        progress(dict(kind='lazy_exact_projected_covering_floor_exclusions',
            source_wld_sha256=graph.inventory_sha256, attempts=list(attempts),
            examined_faces=len(checked), examined_pairs=pairs, audits=list(records),
            excluded_directed_edges=len(excluded), current_floor_unchanged=True,
            goal_layers_preserved_in_graph=True, physical_disconnection_proven=False,
            input_authorized=False, real_client_accepted=False))
    for index in range(rounds):
        check_context()
        proposal = graph.propose(prefix, start, goal, excluded=excluded, max_seconds=10.)
        if proposal is None:
            attempts.append(dict(round=index, proposal=False))
            report()
            return None
        selected = {key for edge in proposal.edges for key in (edge.origin, edge.destination)
                    if key in graph.points} - checked
        if not selected:
            return proposal
        if pairs >= maximum_pairs:
            raise ValueError('Covered-floor total pair budget exceeded')
        found, record = covered_floor_exclusions(graph, body_height=body_height,
            face_ids=selected, maximum_pairs=maximum_pairs-pairs, check_context=check_context)
        checked.update(selected); pairs += record['examined_pairs']
        records.append(record)
        attempts.append(dict(round=index, proposal=True, edges=len(proposal.edges),
                             new_exclusions=len(record['exclusions'])))
        excluded.update(found)
        report()
        if not found:
            return proposal
    raise ValueError('Covered-floor proposal retry budget exhausted')
