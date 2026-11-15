"""Offline walking proposal repair with one continuous, fully checked floor.

Only explicit terrain/static refusals trigger local search. Detours remain
proposals until every returned cell also passes BSP/native checks. No new
source seed, current-character state or movement permission is produced.
"""
from dataclasses import asdict, replace
from hashlib import sha256
import math

from eql_automation.native_region_policy import encoded
from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_detour import find_source_detour, swept_square
from eql_automation.source_itinerary import SourceWalkHint, _guide_snapshot
from eql_automation.source_probe_geometry import check_source_footprint

GEOMETRIC_REFUSALS = frozenset((
    'Source motion terrain: selected_floor_uncovered_ground_area',
    'Source motion terrain: other_source_surface_intersects_body_band',
    'Source motion static: other_source_surface_intersects_body_band',
))


def repair_walks(prefix, guide, planner, *, check_context, progress=lambda _: None,
                 maximum_repairs=8, maximum_rejoin_distance=40.,
                 detour_seconds=20., maximum_expansions=128):
    guide.validate()
    if (not guide.operations or any(type(op) is not SourceWalkHint for op in guide.operations)
            or type(maximum_repairs) is not int or not 1 <= maximum_repairs <= 32
            or type(maximum_rejoin_distance) not in (int, float)
            or not 1 <= maximum_rejoin_distance <= 60
            or type(detour_seconds) not in (int, float) or not 0 < detour_seconds <= 30
            or type(maximum_expansions) is not int or not 1 <= maximum_expansions <= 256
            or not callable(check_context) or not callable(progress)
            or guide.zone != planner.region_policy.zone
            or prefix.inventory_sha256 != guide.wld_sha256
            or guide.wld_sha256 != planner.source.wld_sha256
            or guide.static_inventory_sha256 != planner.static.inventory_sha256
            or guide.body_height != prefix.body_height):
        raise ValueError('Bounded ordinary source-walk repair context required')
    before = _chain_snapshot(prefix); guide_state = _guide_snapshot(guide)
    chain = prefix.fork(); position = guide.operations[0].start
    chain.floor_at(position)
    output = []; rows = []; repairs = []; index = 0

    def check():
        check_context()
        if _chain_snapshot(prefix) != before or _guide_snapshot(guide) != guide_state:
            raise ValueError('Original source prefix or guide changed during repair')

    def record():
        return dict(kind='offline_checked_walking_repairs',
            source_guide_sha256=sha256(encoded(guide.record())).hexdigest(),
            completed_operations=index, next_position=position,
            reached_proof_sha256=chain.previous.proof_sha256,
            checked_cells=rows, repairs=repairs, source_prefix_unchanged=True,
            maximum_repairs=maximum_repairs, maximum_rejoin_distance=maximum_rejoin_distance,
            detour_seconds=detour_seconds, maximum_expansions=maximum_expansions,
            requires_complete_itinerary_rebuild=True, input_authorized=False,
            current_character_observation=False, real_client_accepted=False)

    def step(current, a, b):
        check()
        result = check_source_footprint(current, swept_square(a, b, guide.radius),
            terrain=planner.source, static=planner.static, bsp=planner.bsp,
            region_policy=planner.region_policy)
        check()
        row = dict(start=a, end=b, previous_sha256=result.terrain.previous_sha256,
            proof_sha256=result.terrain.proof_sha256, selected_ids=result.terrain.selected_ids,
            bsp=asdict(result.bsp), native=asdict(result.native))
        return result.branch, row

    while index < len(guide.operations):
        check(); op = guide.operations[index]
        if position != op.start: raise ValueError('Repair lost exact guide continuity')
        try:
            branch, row = step(chain, op.start, op.end)
        except ValueError as error:
            # Binding/region/budget errors do not become obstacle exclusions.
            if str(error) not in GEOMETRIC_REFUSALS:
                progress(record()); raise
            if len(repairs) >= maximum_repairs:
                progress(record()); raise ValueError('Source walk repair count exhausted') from error
            end = index; walked = math.dist(op.start, op.end)
            if walked > maximum_rejoin_distance:
                progress(record()); raise ValueError('Refused walk exceeds the local repair bound') from error
            while end+1 < len(guide.operations):
                following = guide.operations[end+1]
                length = math.dist(following.start, following.end)
                if walked+length > maximum_rejoin_distance: break
                end += 1; walked += length
            goal = guide.operations[end].end
            attempt = dict(first_origin=index, last_origin=end, start=position, goal=goal,
                original_refusal=str(error), prior_floor_proof_sha256=chain.previous.proof_sha256,
                candidate=False, adopted=False)
            repairs.append(attempt); progress(record())
            detour, _ = find_source_detour(chain, position, goal, planner.source, planner.static,
                radius=guide.radius, max_seconds=detour_seconds, max_expansions=maximum_expansions)
            attempt['detour'] = asdict(detour)
            if not detour.candidate:
                progress(record()); raise ValueError('Local repair at '+str(index)+': '+detour.reason)
            # Replay every cap and sweep on the original branch; never adopt
            # the search's terrain/static-only branch as region-checked state.
            repaired = chain.fork(); local_rows = []
            try:
                for cell in detour.cells:
                    repaired, checked = step(repaired, cell.start, cell.end)
                    local_rows.append(checked)
            except (ValueError, TimeoutError) as failure:
                attempt['complete_check_refusal'] = str(failure)
                progress(record()); raise
            check(); attempt.update(candidate=True, adopted=True)
            output.extend(SourceWalkHint(a, b) for a, b in zip(detour.points, detour.points[1:]))
            rows.extend(local_rows); chain = repaired; position = goal; index = end+1
            progress(record())
            continue
        chain = branch; rows.append(row); output.append(op); position = op.end; index += 1
        if index % 25 == 0: progress(record())
    check()
    if position != guide.goal: raise ValueError('Repair did not end at the exact destination')
    evidence = record(); progress(evidence)
    result = replace(guide, operations=tuple(output), provenance_sha256=sha256(encoded(evidence)).hexdigest())
    result.validate()
    return result, evidence
