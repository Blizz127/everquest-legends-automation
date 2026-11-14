"""Offline proposal shortcuts through complete terrain/static footprints.

This retains every explicit step and the supplied source-floor lineage. It
only replaces walking hints; a complete itinerary rebuild must still check
BSP/native regions. No device, observer or current-character state is owned.
"""
from collections import Counter
from dataclasses import asdict, replace
from hashlib import sha256
import math

from eql_automation.native_region_policy import encoded
from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_detour import swept_square
from eql_automation.source_itinerary import SourceWalkHint, SourceStepHint, _guide_snapshot
from eql_automation.source_step import check_source_step
from eql_automation.static_floor_guard import check_source_static_floor


def shortcut_walks(prefix, guide, terrain, static, *, check_context,
                   maximum_distance=40., maximum_queries=1000, progress=lambda _: None):
    guide.validate()
    if (not callable(check_context) or not callable(progress)
            or type(maximum_distance) not in (float, int) or not 1 <= maximum_distance <= 40
            or type(maximum_queries) is not int or not 1 <= maximum_queries <= 2000
            or prefix.inventory_sha256 != guide.wld_sha256
            or terrain.wld_sha256 != guide.wld_sha256
            or static.inventory_sha256 != guide.static_inventory_sha256
            or prefix.body_height != guide.body_height):
        raise ValueError('Explicit bounded shortcut context required')
    original = _chain_snapshot(prefix)
    guide_state = _guide_snapshot(guide)
    prefix.floor_at(guide.operations[0].start)
    chain = prefix.fork()
    operations = []
    rows = []
    refusals = Counter()
    queries = 0

    def check():
        check_context()
        if _chain_snapshot(prefix) != original or _guide_snapshot(guide) != guide_state:
            raise ValueError('Shortcut source context changed')

    def report():
        return dict(kind='offline_source_walk_shortcuts', queries=queries,
            query_scope='walking footprint proposals; step validation has its own bounded source queries',
            maximum_distance=maximum_distance, maximum_queries=maximum_queries,
            source_guide_sha256=sha256(encoded(guide.record())).hexdigest(),
            accepted_proposals=rows, refusal_counts=dict(refusals),
            source_prefix_unchanged=True, original_steps_preserved=True,
            bsp_regions_checked=False, requires_complete_rebuild=True,
            input_authorized=False, real_client_accepted=False)

    def walk(current, start, goal):
        nonlocal queries
        check()
        if queries >= maximum_queries:
            raise TimeoutError('Shortcut footprint query budget exhausted')
        queries += 1
        cap = swept_square(start, goal, guide.radius)
        try:
            sources = terrain.source_faces_for_footprint(cap)
        except ValueError as error:
            # A smaller footprint may fit the complete-query budget. This
            # rejects only this long proposal, never the node or component.
            if str(error) != 'Source projection candidate budget exceeded':
                raise
            refusals['inconclusive_projection_budget'] += 1
            return None
        branch = current.fork()
        floor = branch.advance(cap, sources)
        if not floor.candidate:
            refusals['terrain:'+floor.reason] += 1
            return None
        placed = check_source_static_floor(floor, cap, sources, static)
        if not placed.candidate:
            refusals['static:'+placed.reason] += 1
            return None
        check()
        return branch

    index = 0
    position = guide.operations[0].start
    while index < len(guide.operations):
        check()
        operation = guide.operations[index]
        if position != operation.start:
            raise ValueError('Shortcut walk lost exact guide continuity')
        if type(operation) is SourceStepHint:
            departure = walk(chain, position, position)
            if departure is None:
                progress(report())
                raise ValueError('Shortcut cannot retain the original step departure cap at '+str(index))
            transfer, landing = check_source_step(departure, operation.start, operation.end,
                terrain, static, landing_seed_ids=operation.landing_seed_ids,
                radius=guide.radius, max_step_height=operation.max_step_height,
                max_lift=operation.max_lift, lift_clearance=operation.lift_clearance)
            if not transfer.candidate:
                progress(report())
                raise ValueError('Shortcut original step at '+str(index)+': '+transfer.reason)
            check()
            rows.append(dict(kind='unchanged_step', origin=index, transfer=asdict(transfer)))
            operations.append(operation)
            chain, position = landing, operation.end
            index += 1
        else:
            stop = index
            while stop < len(guide.operations) and type(guide.operations[stop]) is SourceWalkHint:
                stop += 1
            chosen = None
            for end in range(stop-1, index-1, -1):
                check()
                goal = guide.operations[end].end
                if math.dist(position, goal) > maximum_distance:
                    continue
                branch = walk(chain, position, goal)
                if branch is not None:
                    chosen = end, goal, branch
                    break
            if chosen is None:
                progress(report())
                raise ValueError('No checked walking shortcut or original endpoint at '+str(index))
            end, goal, chain = chosen
            rows.append(dict(kind='walk', first_origin=index, last_origin=end,
                start=position, end=goal, proof_sha256=chain.previous.proof_sha256))
            operations.append(SourceWalkHint(position, goal))
            index, position = end+1, goal
        progress(report())
    check()
    evidence = report()
    result = replace(guide, operations=tuple(operations),
                     provenance_sha256=sha256(encoded(evidence)).hexdigest())
    result.validate()
    assert tuple(op for op in result.operations if type(op) is SourceStepHint) == tuple(
        op for op in guide.operations if type(op) is SourceStepHint)
    return result, evidence
