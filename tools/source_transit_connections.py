"""Bounded offline rejection of obstructed source-graph connections.

Independent edge probes are negative search witnesses only: an internal edge is
pruned across rounds only when its swept cells have a component-wide coverage
deficit, a positive-height terrain body blocker, or a static body-band obstacle
above the component surface. Winning proposals are verified end-to-end on a
fork of the caller's carried source floor without mutating the original prefix
or authorizing game input.
"""
from dataclasses import asdict
from hashlib import sha256
import math
import time

from eql_automation.ground_binding import finite
from eql_automation.ground_sweep import hull
from eql_automation.native_region_policy import encoded
from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain, inside, rational
from eql_automation.source_probe_geometry import check_source_footprint
from eql_automation.static_floor_guard import check_source_static_floor
from tools.source_walk_repairs import GEOMETRIC_REFUSALS

_INDEPENDENT_REASONS = frozenset((
    'selected_floor_uncovered_ground_area',
    'other_source_surface_intersects_body_band',
))


def _edge_sweeps(points, maximum_cell_length):
    cells = []
    position = points[0][:2]
    for xyz in points[1:]:
        target = xyz[:2]
        origin = position
        count = max(1, math.ceil(math.dist(origin, target) / maximum_cell_length))
        for index in range(count):
            end = (target if index == count - 1 else
                   tuple(origin[k] + (target[k] - origin[k]) * (index + 1) / count for k in (0, 1)))
            cells.append((position, end))
            position = end
    return tuple(cells)


def filter_transit_connections(graph, prefix, start, goal, planner, *,
                               check_context, progress=lambda _: None,
                               rounds=8, start_via_edges=True,
                               maximum_edge_queries=512, maximum_cell_queries=8192,
                               maximum_seconds=120., maximum_cell_length=2.,
                               clock=time.monotonic):
    if (type(rounds) is not int or not 1 <= rounds <= 32
            or type(start_via_edges) is not bool
            or type(maximum_edge_queries) is not int or not 1 <= maximum_edge_queries <= 4096
            or type(maximum_cell_queries) is not int or not 1 <= maximum_cell_queries <= 32768
            or not finite(maximum_seconds) or not 0 < maximum_seconds <= 600
            or not finite(maximum_cell_length) or not .25 <= maximum_cell_length <= 8.
            or not all(callable(f) for f in (check_context, progress, clock))
            or graph.inventory_sha256 != prefix.inventory_sha256
            or planner.source.wld_sha256 != prefix.inventory_sha256):
        raise ValueError('Bounded matching connection context required')
    snapshot = _chain_snapshot(prefix)
    excluded = set()
    cache = {}
    attempts = []
    cell_queries = 0
    began = last = clock()
    if not finite(began):
        raise ValueError('Invalid connection search clock')

    def check():
        nonlocal last
        check_context()
        now = clock()
        if not finite(now) or not began <= last <= now:
            raise ValueError('Invalid connection search clock')
        if now - began > maximum_seconds:
            raise TimeoutError('Connection search time budget exhausted')
        last = now
        if _chain_snapshot(prefix) != snapshot:
            raise ValueError('Original source prefix changed during connection search')

    def report():
        progress(dict(
            kind='offline_source_graph_connection_filter',
            start=start,
            goal=goal,
            initial_floor_proof_sha256=prefix.previous.proof_sha256,
            source_wld_sha256=prefix.inventory_sha256,
            static_inventory_sha256=planner.static.inventory_sha256,
            radius=graph.radius,
            body_height=prefix.body_height,
            attempts=attempts,
            edge_queries=len(cache),
            cell_queries=cell_queries,
            excluded_count=len(excluded),
            excluded_identities=tuple(sorted(excluded, key=repr)),
            maximum_edge_queries=maximum_edge_queries,
            maximum_cell_queries=maximum_cell_queries,
            maximum_seconds=maximum_seconds,
            exclusion_scope='this_connection_search_from_this_carried_prefix',
            prefix_unchanged=True,
            requires_complete_rebuild=True,
            new_source_seed=False,
            physical_disconnection_proven=False,
            input_authorized=False,
            real_client_accepted=False,
        ))
        check()

    def count_cell():
        nonlocal cell_queries
        check()
        if cell_queries >= maximum_cell_queries:
            report()
            raise TimeoutError('Connection cell query count exhausted')
        cell_queries += 1

    def probe_edge(edge):
        if edge.step is not None:
            raise ValueError('Step edges are not supported by ordinary connection filtering')
        if edge.identity in cache:
            return cache[edge.identity]
        if len(cache) >= maximum_edge_queries:
            report()
            raise TimeoutError('Connection edge query count exhausted')
        origin_xy = edge.points[0][:2]
        sweeps = _edge_sweeps(edge.points, maximum_cell_length)
        carried_root = edge.origin == ('start',)
        if carried_root:
            if origin_xy != start:
                raise ValueError('Root connection edge does not start at the supplied start XY')
            probe = prefix.fork()
            component = None
            seed = None
            cells = sweeps
        else:
            if edge.origin not in graph.components.components:
                raise ValueError('Unknown connection origin face')
            component = graph.components.components[edge.origin]
            seed = dict(
                kind='offline_proposal_edge_hypothesis',
                source_wld_sha256=planner.source.wld_sha256,
                static_inventory_sha256=planner.static.inventory_sha256,
                edge_identity=repr(edge.identity),
                origin_face=edge.origin,
                destination_face=edge.destination,
                origin_xy=origin_xy,
                radius=graph.radius,
                body_height=prefix.body_height,
                current_character_observation=False,
                input_authorized=False,
            )
            probe = SourceFloorChain(
                inventory_sha256=planner.source.wld_sha256,
                seed_evidence_sha256=sha256(encoded(seed)).hexdigest(),
                seed_ids=(edge.origin,),
                body_height=prefix.body_height,
            )
            cells = ((origin_xy, origin_xy), *sweeps)

        for a, b in cells:
            count_cell()
            footprint = swept_square(a, b, graph.radius)
            sources = planner.source.source_faces_for_footprint(footprint)
            floor = probe.advance(footprint, sources)
            placed = (check_source_static_floor(floor, footprint, sources, planner.static)
                      if floor.candidate else None)
            accepted = bool(floor.candidate and placed is not None and placed.candidate)
            if not accepted:
                reason = placed.reason if placed is not None else floor.reason
                if reason not in _INDEPENDENT_REASONS:
                    cache[edge.identity] = dict(
                        edge_identity=repr(edge.identity),
                        seed=seed,
                        carried_root=carried_root,
                        failed_cell=(a, b),
                        accepted_edge=False,
                        excluded_edge=False,
                        reason=reason,
                        classification='non_geometric_failure',
                        route_accepted=False,
                        physical_disconnection_proven=False,
                    )
                    report()
                    raise ValueError(f'Connection query cannot justify pruning {edge.identity!r}: {reason}')
                if carried_root:
                    definite = True
                    witness = None
                    blocker = None
                    support = None
                else:
                    support = [(s.fragment, s.face) for s in sources
                               if graph.components.components.get((s.fragment, s.face)) == component]
                    expanded = hull((x + dx, y + dy) for x, y in footprint
                                    for dx in (-.002, .002) for dy in (-.002, .002))
                    witness = next((p for p in expanded if not any(
                        inside(rational((p,))[0], rational(graph.components.faces[k][0]))
                        for k in support)), None)
                    blocker = (next((hit for hit in floor.occupancy.faces
                                     if hit.classification == 'intersects_or_touches_body_band'
                                     and hit.minimum_above_floor is not None
                                     and hit.minimum_above_floor > .11), None)
                               if floor.occupancy is not None else None)
                    definite = bool(
                        (reason == 'selected_floor_uncovered_ground_area' and witness is not None)
                        or (reason == 'other_source_surface_intersects_body_band' and blocker is not None)
                        or (floor.candidate and placed is not None
                            and placed.reason == 'other_source_surface_intersects_body_band')
                    )
                entry = dict(
                    edge_identity=repr(edge.identity),
                    seed=seed,
                    carried_root=carried_root,
                    failed_cell=(a, b),
                    accepted_edge=False,
                    excluded_edge=definite,
                    reason=reason,
                    uncovered_corner=witness,
                    positive_height_body_blocker=None if blocker is None else asdict(blocker),
                    support_overapproximation_ids=support,
                    classification='geometric_refusal' if definite else 'independent_seed_inconclusive',
                    route_accepted=False,
                    physical_disconnection_proven=False,
                )
                cache[edge.identity] = entry
                return entry

        end_xy = edge.points[-1][:2]
        layer_ok = (edge.destination == ('goal',)
                    or f'wld:{edge.destination[0]}:face:{edge.destination[1]}' in probe.floor_at(end_xy)[1])
        if carried_root and not layer_ok:
            cache[edge.identity] = dict(
                edge_identity=repr(edge.identity),
                carried_root=True,
                accepted_edge=False,
                excluded_edge=False,
                classification='layer_mismatch',
                expected_face=edge.destination,
                actual_floor_ids=probe.floor_at(end_xy)[1],
                route_accepted=False,
                physical_disconnection_proven=False,
            )
            report()
            raise ValueError('Connection destination differs from the actual carried source layer')
        entry = dict(
            edge_identity=repr(edge.identity),
            seed=seed,
            carried_root=carried_root,
            accepted_edge=layer_ok,
            excluded_edge=False,
            reason='conditional_terrain_and_static_occupancy_only' if layer_ok else 'independent_layer_mismatch',
            classification='edge_passed' if layer_ok else 'independent_seed_inconclusive',
            route_accepted=False,
            physical_disconnection_proven=False,
        )
        cache[edge.identity] = entry
        return entry

    for attempt in range(rounds):
        check()
        remaining = maximum_seconds - (last - began)
        if remaining <= 0:
            raise TimeoutError('Connection search time budget exhausted')
        proposal = graph.propose(
            prefix, start, goal,
            excluded=excluded,
            start_via_edges=start_via_edges,
            max_seconds=min(30., remaining),
        )
        if proposal is None:
            report()
            raise ValueError('No connection proposal within current exclusions; physical disconnection not proven')
        rejected = []
        inconclusive = []
        for edge in proposal.edges:
            check()
            outcome = probe_edge(edge)
            if outcome['excluded_edge']:
                rejected.append(dict(edge_identity=repr(edge.identity), reason=outcome['reason'],
                                     failed_cell=outcome['failed_cell']))
                excluded.add(edge.identity)
            elif not outcome['accepted_edge']:
                inconclusive.append(repr(edge.identity))
        row = dict(
            round=attempt,
            proposal_edges=len(proposal.edges),
            proposal_expanded=proposal.expanded,
            rejected_edges=rejected,
            inconclusive_edges=inconclusive,
            candidate=False,
        )
        attempts.append(row)
        if rejected:
            report()
            continue

        branch = prefix.fork()
        position = start
        carried_rejected = False
        for edge in proposal.edges:
            check()
            if edge.step is not None or edge.points[0][:2] != position:
                raise ValueError('Exactly contiguous ordinary connection required')
            if (edge.origin != ('start',)
                    and f'wld:{edge.origin[0]}:face:{edge.origin[1]}' not in branch.floor_at(position)[1]):
                row['layer_refusal'] = dict(
                    expected_face=edge.origin,
                    position=position,
                    actual_floor_ids=branch.floor_at(position)[1],
                )
                report()
                raise ValueError('Connection origin differs from the actual carried source layer')
            for a, b in _edge_sweeps(edge.points, maximum_cell_length):
                count_cell()
                try:
                    checked = check_source_footprint(
                        branch, swept_square(a, b, graph.radius),
                        terrain=planner.source, static=planner.static,
                        bsp=planner.bsp, region_policy=planner.region_policy,
                    )
                except ValueError as error:
                    geometric = str(error) in GEOMETRIC_REFUSALS
                    row['carried_refusal'] = dict(
                        reason=str(error),
                        edge_identity=repr(edge.identity),
                        start=a,
                        end=b,
                        prior_floor_proof_sha256=branch.previous.proof_sha256,
                        selected_ids=branch.previous.selected_ids,
                        geometric_exclusion=geometric,
                    )
                    if not geometric:
                        report()
                        raise
                    excluded.add(edge.identity)
                    carried_rejected = True
                    break
                branch = checked.branch
                position = b
            if carried_rejected:
                break
            if (edge.destination != ('goal',)
                    and f'wld:{edge.destination[0]}:face:{edge.destination[1]}' not in branch.floor_at(position)[1]):
                row['layer_refusal'] = dict(
                    expected_face=edge.destination,
                    position=position,
                    actual_floor_ids=branch.floor_at(position)[1],
                )
                report()
                raise ValueError('Connection destination differs from the actual carried source layer')
        if carried_rejected:
            report()
            continue
        if position != goal:
            raise ValueError('Connection proposal did not end at the exact goal')
        floor_z, floor_ids = branch.floor_at(goal)
        row.update(
            candidate=True,
            end=position,
            reached_proof_sha256=branch.previous.proof_sha256,
            goal_floor_height=floor_z,
            goal_floor_ids=floor_ids,
        )
        report()
        return proposal
    raise ValueError('Connection proposal retry count exhausted')
