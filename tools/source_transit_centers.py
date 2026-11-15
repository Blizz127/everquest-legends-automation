"""Bounded offline rejection of fixed source-graph waypoints.

Independent center seeds are negative search witnesses only. They never
replace the caller's floor, accept an edge, or authorize game input.
"""
from dataclasses import asdict
from hashlib import sha256

from eql_automation.ground_sweep import hull
from eql_automation.native_region_policy import encoded
from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain, inside, rational
from eql_automation.static_floor_guard import check_source_static_floor


def filter_transit_centers(graph, prefix, start, goal, planner, *, rounds,
                           check, progress, start_via_edges=False, maximum_caps=2048):
    if (type(rounds) is not int or not 0 <= rounds <= 16
            or type(maximum_caps) is not int or not 1 <= maximum_caps <= 4096
            or type(start_via_edges) is not bool
            or prefix.inventory_sha256 != planner.source.wld_sha256
            or graph.inventory_sha256 != prefix.inventory_sha256):
        raise ValueError('Bounded matching source center filter required')
    snapshot = _chain_snapshot(prefix)
    excluded = set(); cache = {}; attempts = []
    rejected_reasons = {'selected_floor_uncovered_ground_area',
                        'other_source_surface_intersects_body_band'}

    def current():
        check()
        if _chain_snapshot(prefix) != snapshot:
            raise ValueError('Current source prefix changed during center filtering')

    def report():
        progress(attempts, cache, len(excluded)); current()

    for attempt in range(rounds+1):
        current()
        proposal = graph.propose(prefix, start, goal, excluded=excluded,
            start_via_edges=start_via_edges, max_seconds=10.)
        if proposal is None:
            report()
            raise ValueError('No proposal after bounded fixed-center exclusions; physical disconnection not proven')
        # Root alternatives omit the selected face center. Only actual graph
        # nodes on this proposal are mandatory center visits.
        faces = tuple(dict.fromkeys(face for edge in proposal.edges
            for face in (edge.origin, edge.destination) if face in graph.centers))
        rejected = []
        for face in faces:
            current()
            if face not in cache:
                if len(cache) >= maximum_caps:
                    report(); raise ValueError('Source center query count exhausted')
                point = graph.centers[face][:2]
                evidence = dict(kind='offline_proposal_center_hypothesis',
                    source_wld_sha256=planner.source.wld_sha256,
                    static_inventory_sha256=planner.static.inventory_sha256,
                    face=face, point=point, radius=graph.radius, body_height=prefix.body_height,
                    current_character_observation=False, input_authorized=False)
                cap = swept_square(point, point, graph.radius)
                sources = planner.source.source_faces_for_footprint(cap)
                probe = SourceFloorChain(inventory_sha256=planner.source.wld_sha256,
                    seed_evidence_sha256=sha256(encoded(evidence)).hexdigest(),
                    seed_ids=(face,), body_height=prefix.body_height)
                floor = probe.advance(cap, sources)
                placed = (check_source_static_floor(floor, cap, sources, planner.static)
                          if floor.candidate else None)
                accepted = floor.candidate and placed.candidate
                reason = placed.reason if placed is not None else floor.reason
                # A one-face seed can miss joins retained by an arriving
                # prefix. Coverage exclusions need a deficit even in all
                # eligible local support of this overapproximate component.
                support = [(s.fragment, s.face) for s in sources
                    if graph.components.components.get((s.fragment, s.face))
                       == graph.components.components[face]]
                expanded = hull((x+dx, y+dy) for x, y in cap
                    for dx in (-.002, .002) for dy in (-.002, .002))
                witness = next((p for p in expanded if not any(
                    inside(rational((p,))[0], rational(graph.components.faces[k][0]))
                    for k in support)), None)
                blocker = (next((hit for hit in floor.occupancy.faces
                    if hit.classification == 'intersects_or_touches_body_band'
                    and hit.minimum_above_floor is not None and hit.minimum_above_floor > .11), None)
                    if floor.occupancy is not None else None)
                definite = (reason == 'selected_floor_uncovered_ground_area' and witness is not None
                    or reason == 'other_source_surface_intersects_body_band' and blocker is not None
                    or floor.candidate and placed is not None
                    and placed.reason == 'other_source_surface_intersects_body_band')
                cache[face] = dict(seed=evidence, cap=cap, accepted_cap=accepted, reason=reason,
                    excluded_center=definite, uncovered_corner=witness,
                    positive_height_body_blocker=None if blocker is None else asdict(blocker),
                    support_overapproximation_ids=support,
                    classification=('cap_passed' if accepted else 'geometric_refusal' if definite
                                    else 'independent_seed_inconclusive'),
                    terrain=asdict(floor), static=None if placed is None else asdict(placed),
                    route_accepted=False, physical_disconnection_proven=False)
                if not accepted and reason not in rejected_reasons:
                    report()
                    raise ValueError('Center query cannot justify pruning '+str(face)+': '+reason)
            if cache[face]['excluded_center']:
                rejected.append(face)
        attempts.append(dict(round=attempt, proposal=asdict(proposal), rejected_faces=rejected))
        if not rejected:
            report(); return proposal
        bad = set(rejected)
        for face in bad:
            excluded.add(('start', face)); excluded.add(('goal', face))
        # Block every entry into a bad center. Its ordinary outgoing edges
        # cannot execute without an entry; retain them for root alternatives
        # that leave the selected face without visiting that center.
        for edges in graph.adjacent.values():
            excluded.update(edge.identity for edge in edges if edge.destination in bad)
        report()
    raise ValueError('Fixed-center proposal retry budget exhausted')
