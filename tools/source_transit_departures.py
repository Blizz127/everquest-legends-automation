"""Try alternative graph departures using the actual retained source prefix.

Negative witnesses are scoped to this bounded search. No independent floor
seed or physical-disconnection claim is produced; the whole guide must rebuild.
"""
from dataclasses import asdict
import math
import time

from eql_automation.ground_binding import finite
from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_detour import swept_square
from eql_automation.source_probe_geometry import check_source_footprint
from tools.source_walk_repairs import GEOMETRIC_REFUSALS


def filter_transit_departures(graph, prefix, start, goal, planner, *, check_context,
                             progress=lambda _:None, rounds=8, maximum_queries=512,
                             maximum_seconds=30., clock=time.monotonic):
    if (type(rounds) is not int or not 1 <= rounds <= 32
            or type(maximum_queries) is not int or not 1 <= maximum_queries <= 2048
            or not finite(maximum_seconds) or not 0 < maximum_seconds <= 120
            or graph.inventory_sha256 != prefix.inventory_sha256
            or planner.source.wld_sha256 != prefix.inventory_sha256):
        raise ValueError('Bounded matching departure context required')
    snapshot=_chain_snapshot(prefix);selected=set(prefix.previous.selected_ids)
    excluded=set();attempts=[];queries=0;began=last=clock()
    if not finite(began):raise ValueError('Invalid departure clock')

    def check():
        nonlocal last
        check_context();now=clock()
        if not finite(now) or not began <= last <= now:
            raise ValueError('Invalid departure clock')
        if now-began > maximum_seconds:raise TimeoutError('Departure search time budget exhausted')
        last=now
        if _chain_snapshot(prefix)!=snapshot:
            raise ValueError('Original source prefix changed during departure search')

    def report():
        progress(dict(kind='offline_carried_source_departures',start=start,goal=goal,
            initial_floor_proof_sha256=prefix.previous.proof_sha256,
            source_wld_sha256=prefix.inventory_sha256,
            static_inventory_sha256=planner.static.inventory_sha256,
            radius=graph.radius,body_height=prefix.body_height,
            attempts=attempts,excluded_identities=tuple(sorted(excluded,key=repr)),queries=queries,
            maximum_queries=maximum_queries,maximum_seconds=maximum_seconds,
            exclusion_scope='this_departure_search_from_this_carried_prefix',
            prefix_unchanged=True,requires_complete_rebuild=True,new_source_seed=False,
            physical_disconnection_proven=False,input_authorized=False,real_client_accepted=False))
        check()

    for attempt in range(rounds):
        check()
        remaining=maximum_seconds-(last-began)
        if remaining<=0:raise TimeoutError('Departure search time budget exhausted')
        proposal=graph.propose(prefix,start,goal,excluded=excluded,start_via_edges=True,
            max_seconds=min(30.,remaining))
        if proposal is None:
            report();raise ValueError('No departure proposal within current exclusions; physical disconnection not proven')
        branch=prefix.fork();position=start
        row=dict(attempt=attempt,proposal=asdict(proposal),checked_cells=[],candidate=False)
        attempts.append(row)
        rejected=False
        for edge_index,edge in enumerate(proposal.edges):
            check()
            if edge_index>=64:report();raise ValueError('Departure edge count exhausted')
            if edge.step is not None or edge.points[0][:2]!=position:
                raise ValueError('Exactly contiguous ordinary departure required')
            if (edge.origin!=('start',)
                    and f'wld:{edge.origin[0]}:face:{edge.origin[1]}' not in branch.floor_at(position)[1]):
                raise ValueError('Departure edge does not match the carried source layer')
            for xyz in edge.points[1:]:
                target=xyz[:2];origin=position
                count=max(1,math.ceil(math.dist(origin,target)/2.))
                for index in range(count):
                    check()
                    if queries>=maximum_queries:
                        report();raise TimeoutError('Departure geometry query count exhausted')
                    end=target if index==count-1 else tuple(origin[k]+(target[k]-origin[k])*(index+1)/count for k in (0,1))
                    queries+=1
                    try:
                        checked=check_source_footprint(branch,swept_square(position,end,graph.radius),
                            terrain=planner.source,static=planner.static,bsp=planner.bsp,
                            region_policy=planner.region_policy)
                    except ValueError as error:
                        row['refusal']=dict(reason=str(error),edge_identity=edge.identity,
                            start=position,end=end,prior_floor_proof_sha256=branch.previous.proof_sha256,
                            selected_ids=branch.previous.selected_ids,
                            geometric_exclusion=str(error) in GEOMETRIC_REFUSALS)
                        if str(error) not in GEOMETRIC_REFUSALS:
                            report();raise
                        excluded.add(edge.identity);rejected=True;break
                    row['checked_cells'].append(dict(edge_identity=edge.identity,start=position,end=end,
                        proof_sha256=checked.terrain.proof_sha256,
                        previous_sha256=checked.terrain.previous_sha256,
                        selected_ids=checked.terrain.selected_ids,
                        bsp=asdict(checked.bsp),native=asdict(checked.native)))
                    branch=checked.branch;position=end
                if rejected:break
            if rejected:break
            if edge.destination not in selected:
                if (edge.destination!=('goal',)
                        and f'wld:{edge.destination[0]}:face:{edge.destination[1]}' not in branch.floor_at(position)[1]):
                    row['layer_refusal']=dict(expected_face=edge.destination,position=position,
                        actual_floor_ids=branch.floor_at(position)[1])
                    report()
                    raise ValueError('Departure destination differs from the actual carried source layer')
                row.update(candidate=True,end=position,reached_proof_sha256=branch.previous.proof_sha256)
                report();return proposal
        if not rejected:
            raise ValueError('Departure proposal never left its selected faces or reached the goal')
        report()
    raise ValueError('Departure proposal retry count exhausted')
