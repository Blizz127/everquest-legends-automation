#!/usr/bin/env python3
"""Offline source-only Greater Faydark transit and carried Crushbone crossing audit.

Uses copied client map labels (gfaydark_1.txt / gfaydark_3.txt) for XY endpoints
only, never label Z or mesh Z. Carries one checked SourceFloorChain end-to-end
through terrain, static placements, scoped BSP, NativeZeroRegionTrialPolicy,
WalkingSections, and (for orc-camps-to-crushbone) carried check_source_crossing_cell
into DRNTP00255000004_ZONE. Sends zero game input.
"""
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path
import argparse
import json
import math
import os
import resource
import signal
import sys
import time

BUTCHER_EXIT_XY = (2642.0693, -1627.6870)
ORC_CAMPS_XY = (48.0, 1849.0)
CRUSHBONE_PRELINE_XY = (-52.0, 2597.0)

ROUTES = {
    'butcher-exit-to-orc-camps': (
        'gfaydark_1:to_Butcherblock_Mountains',
        'gfaydark_3:L04-07_Orc_Camps',
        BUTCHER_EXIT_XY,
        ORC_CAMPS_XY,
        False,
    ),
    'orc-camps-to-crushbone': (
        'gfaydark_3:L04-07_Orc_Camps',
        'gfaydark_3:L04-10_GO_TO_CRUSHBONE',
        ORC_CAMPS_XY,
        CRUSHBONE_PRELINE_XY,
        True,
    ),
    'butcher-exit-to-crushbone': (
        'gfaydark_1:to_Butcherblock_Mountains',
        'gfaydark_3:L04-10_GO_TO_CRUSHBONE',
        BUTCHER_EXIT_XY,
        CRUSHBONE_PRELINE_XY,
        True,
    ),
}

CPU_SECONDS = 720.
DEFAULT_WALL_SECONDS = 900.


def _read_map_points(raw: bytes) -> dict:
    points = {}
    for line in raw.decode('latin-1').splitlines():
        text = line.strip()
        if not text.startswith('P '):
            continue
        parts = [p.strip() for p in text[2:].split(',')]
        if len(parts) < 8:
            continue
        mx, my, mz = float(parts[0]), float(parts[1]), float(parts[2])
        label = parts[7]
        points[label] = (mx, my, mz)
    return points


def run(project: Path, output: Path, *, route_name: str, connection_rounds: int = 12,
        plan_sections: bool = True, check_carried_crossing: bool = False,
        wall_seconds: float = DEFAULT_WALL_SECONDS,
        prior_guides: tuple = ()) -> int:
    began, cpu_began = time.monotonic(), time.process_time()
    store = Path.home() / '.local/share/eql-automation'
    sys.path[:0] = [str(project), str(store / 'owner-assist/0.39.10')]

    from eql_automation.gfay_assets import DATA_NAME, DATA_PINS, load_gfay_assets
    from eql_automation.gfay_crossing_assets import load_gfay_crushbone_crossing
    from eql_automation.native_crossing_policy import check_source_crossing_cell
    from eql_automation.native_region_policy import encoded
    from eql_automation.owner_route_assets import checked_bytes
    from eql_automation.route_floor_commit import _chain_snapshot
    from eql_automation.route_geometry import RouteMotionBounds
    from eql_automation.source_detour import swept_square
    from eql_automation.source_floor_chain import SourceFloorChain
    from eql_automation.source_itinerary import SourceItineraryGuide, SourceWalkHint, plan_source_itinerary
    from eql_automation.source_probe_geometry import check_source_footprint
    from eql_automation.source_transit_graph import SourceTransitGraph
    from eql_automation.source_walk_sections import plan_walk_sections
    from tools.audit_butcher_camp_transit import join_source_suffix, write_checkpoint
    from tools.source_transit_connections import filter_transit_connections
    from tools.source_walk_repairs import repair_walks

    origin_label, dest_label, start, goal, supports_crossing = ROUTES[route_name]
    if check_carried_crossing and not supports_crossing:
        raise ValueError('Carried Crushbone crossing only applies to orc-camps-to-crushbone')

    root = store / 'owner-route-data' / DATA_NAME
    code_files = (
        Path(__file__).resolve(),
        project / 'tools/audit_butcher_camp_transit.py',
        project / 'tools/source_transit_connections.py',
        project / 'tools/source_walk_repairs.py',
        *sorted((project / 'eql_automation').glob('*.py')),
    )
    code_pins = {str(p): sha256(p.read_bytes()).hexdigest() for p in code_files}
    record = dict(
        format='eql-offline-gfay-source-transit-v1',
        route_name=route_name,
        origin=origin_label,
        destination=dest_label,
        start=start,
        goal=goal,
        status='running',
        stage='loading',
        completed=False,
        source_candidate=False,
        ordinary_walking_only=True,
        proposal_model='full_source_graph',
        connection_rounds=connection_rounds,
        plan_sections=plan_sections,
        check_carried_crossing=check_carried_crossing,
        synthetic_start=True,
        synthetic_floor_seed=True,
        synthetic_preline_floor_seed=False,
        retained_real_arrival=False,
        current_character_observation=False,
        historical_prefix_replayed=False,
        mesh_z_used_for_floor_selection=False,
        label_z_used_for_floor_selection=False,
        zone_transition_checked=False,
        destination_server_verified=False,
        physical_disconnection_proven=False,
        input_authorized=False,
        game_input_sent=False,
        runtime_ready=False,
        real_client_accepted=False,
        cpu_budget_seconds=CPU_SECONDS,
        wall_budget_seconds=wall_seconds,
        code_sha256=code_pins,
        data_sha256=DATA_PINS,
    )

    def save():
        record.update(seconds=time.monotonic() - began, cpu_seconds=time.process_time() - cpu_began)
        write_checkpoint(output, record)

    def check():
        if time.monotonic() - began > wall_seconds:
            raise TimeoutError('Offline GFay transit wall budget exhausted')
        if time.process_time() - cpu_began > CPU_SECONDS:
            raise TimeoutError('Offline GFay transit CPU budget exhausted')

    def stage(name: str):
        check()
        record['stage'] = name
        save()
        print(json.dumps(dict(stage=name, seconds=record['seconds'], cpu_seconds=record['cpu_seconds'])), flush=True)

    def evidence(name: str):
        def progress(value):
            record[name] = value
            save()
            check()
        return progress

    def check_source_itinerary(prefix, origin_xy, guide):
        check()
        plan = plan_source_itinerary(
            prefix, origin_xy, guide,
            planner.source, planner.static, planner.bsp, planner.region_policy,
            check_context=check,
            max_seconds=max(.001, min(240., wall_seconds - (time.monotonic() - began))),
        )
        data = plan.record()
        if data['guide_entry'] != 0 or tuple(data['start']) != origin_xy or tuple(data['goal']) != guide.goal:
            raise ValueError('Complete GFay approach must check every original operation from start')
        check()
        return plan

    with output.open('x') as stream:
        json.dump(record, stream, allow_nan=False)
    save()
    checked_plan = None
    try:
        map1 = _read_map_points(checked_bytes(root / 'gfaydark_1.txt', DATA_PINS['gfaydark_1.txt']))
        assets = load_gfay_assets(root, native_planning=True)
        planner = assets.planner
        ann_by_label = {a.raw_label: a for a in assets.annotations}
        if route_name == 'butcher-exit-to-orc-camps':
            m_start = map1['to_Butcherblock_Mountains']
            if (-m_start[0], -m_start[1]) != start:
                raise ValueError('Pinned gfaydark_1 Butcherblock exit XY changed')
            m_goal = ann_by_label['L04-07_Orc_Camps'].map_xyz
            if (-m_goal[0], -m_goal[1]) != goal:
                raise ValueError('Pinned gfaydark_3 Orc Camps XY changed')
        elif route_name == 'butcher-exit-to-crushbone':
            m_start = map1['to_Butcherblock_Mountains']
            if (-m_start[0], -m_start[1]) != start:
                raise ValueError('Pinned gfaydark_1 Butcherblock exit XY changed')
            m_goal = ann_by_label['L04-10_GO_TO_CRUSHBONE'].map_xyz
            if (-m_goal[0], -m_goal[1]) != goal:
                raise ValueError('Pinned gfaydark_3 Crushbone approach XY changed')
        else:
            m_start = ann_by_label['L04-07_Orc_Camps'].map_xyz
            m_goal = ann_by_label['L04-10_GO_TO_CRUSHBONE'].map_xyz
            if (-m_start[0], -m_start[1]) != start or (-m_goal[0], -m_goal[1]) != goal:
                raise ValueError('Pinned gfaydark_3 Orc Camps or Crushbone approach XY changed')

        crossing = load_gfay_crushbone_crossing(root, assets) if check_carried_crossing else None
        check()

        proposal = planner.source.propose_unique_diffuse_floor(start, body_height=6.)
        seed = dict(
            kind='synthetic_unique_source_floor',
            start=start,
            proposal=asdict(proposal),
            source_wld_sha256=planner.source.wld_sha256,
            data_sha256=DATA_PINS,
            radius=1.2,
            body_height=6.,
            synthetic_reference=True,
            retained_real_arrival=False,
            current_character_observation=False,
        )
        seed_pin = sha256(encoded(seed)).hexdigest()
        chain = SourceFloorChain(
            inventory_sha256=planner.source.wld_sha256,
            seed_evidence_sha256=seed_pin,
            seed_ids=proposal.selected_ids,
            body_height=6.,
        )
        cap = swept_square(start, start, 1.2)
        floor = chain.advance(cap, planner.source.source_faces_for_footprint(cap))
        if not floor.candidate:
            raise ValueError('Synthetic GFay start cap: ' + floor.reason)
        prefix_state = _chain_snapshot(chain)
        record.update(
            seed=seed,
            seed_sha256=seed_pin,
            initial_floor=asdict(floor),
            goal_intersections=[asdict(h) for h in planner.source.source_hits_at(goal)],
        )

        stage('checking_synthetic_start_cap')
        cap_guide = SourceItineraryGuide(
            'gfaydark',
            planner.source.wld_sha256,
            planner.static.inventory_sha256,
            seed_pin,
            1.2,
            6.,
            start,
            (SourceWalkHint(start, start),),
        )
        cap_plan = check_source_itinerary(chain, start, cap_guide)
        record.update(start_cap_plan=cap_plan.record(), start_cap_sha256=cap_plan.sha256)

        if prior_guides:
            stage('loading_prior_guides')
            loaded_guides = []
            prior_meta = []
            for p_name, p_pin in prior_guides:
                p_data = json.loads(checked_bytes(store / 'nav-candidates' / p_name, p_pin))
                if (p_data.get('data_sha256') != DATA_PINS
                        or p_data.get('input_authorized') is not False
                        or p_data.get('game_input_sent') is not False
                        or p_data.get('real_client_accepted') is not False):
                    raise ValueError('Prior GFay candidate pins or flags invalid: ' + p_name)
                g = SourceItineraryGuide.from_record(p_data['guide'])
                loaded_guides.append(g)
                prior_meta.append(dict(
                    name=p_name,
                    sha256=p_pin,
                    guide_sha256=sha256(encoded(g.record())).hexdigest(),
                ))
            record['proposal_model'] = 'pinned_prior_guide' if len(loaded_guides) == 1 else 'joined_pinned_guides'
            record['prior_guides'] = prior_meta
            if len(loaded_guides) == 1:
                guide = loaded_guides[0]
            else:
                ops = []
                prev_goal = None
                for g in loaded_guides:
                    if prev_goal is not None and g.operations[0].start != prev_goal:
                        raise ValueError('Joined GFay prior guides do not share an exact waypoint')
                    ops.extend(g.operations)
                    prev_goal = g.goal
                provenance = dict(
                    route_name=route_name,
                    origin=origin_label,
                    destination=dest_label,
                    joined_priors=prior_meta,
                    data_sha256=DATA_PINS,
                    seed_sha256=seed_pin,
                )
                guide = SourceItineraryGuide(
                    'gfaydark',
                    planner.source.wld_sha256,
                    planner.static.inventory_sha256,
                    sha256(encoded(provenance)).hexdigest(),
                    1.2,
                    6.,
                    goal,
                    tuple(ops),
                )
                record['provenance'] = provenance
            if guide.operations[0].start != start or guide.goal != goal:
                raise ValueError('Prior GFay guide start/goal does not match route endpoints')
            record['guide'] = guide.record()
        else:
            stage('building_full_source_graph')
            graph = SourceTransitGraph(
                tuple(planner.source.sources),
                inventory_sha256=planner.source.wld_sha256,
                step_links=(),
                radius=1.2,
            )
            record['graph'] = dict(
                faces=graph.components.face_count,
                components=graph.components.component_count,
                directed_edges=sum(len(v) for v in graph.adjacent.values()),
                step_links=0,
            )
            record['goal_components'] = asdict(graph.components.goal(chain, goal))

            stage('proposing_source_xy')
            if connection_rounds > 0:
                transit = filter_transit_connections(
                    graph, chain, start, goal, planner,
                    check_context=check,
                    progress=evidence('connection_evidence'),
                    rounds=connection_rounds,
                    start_via_edges=True,
                    maximum_edge_queries=2048,
                    maximum_cell_queries=32768,
                    maximum_cell_length=8.,
                    maximum_seconds=min(600., max(1., wall_seconds - (time.monotonic() - began))),
                )
            else:
                transit = graph.propose(
                    chain, start, goal,
                    start_via_edges=True,
                    max_expansions=65536,
                    max_seconds=60.,
                )
            if transit is None:
                raise ValueError('No bounded ordinary GFay source-graph proposal; physical disconnection not proven')

            record['proposal'] = asdict(transit)
            guide = join_source_suffix(
                (),
                transit.guide(
                    static_inventory_sha256=planner.static.inventory_sha256,
                    radius=1.2,
                    body_height=6.,
                    zone='gfaydark',
                ),
            )
            provenance = dict(
                route_name=route_name,
                origin=origin_label,
                destination=dest_label,
                proposal_sha256=sha256(encoded(record['proposal'])).hexdigest(),
                data_sha256=DATA_PINS,
                seed_sha256=seed_pin,
                connection_filter_sha256=(
                    sha256(encoded(record['connection_evidence'])).hexdigest()
                    if connection_rounds > 0 else None
                ),
            )
            guide = replace(guide, provenance_sha256=sha256(encoded(provenance)).hexdigest())
            record['provenance'] = provenance
            record['proposal_length'] = sum(edge.cost for edge in transit.edges)
            record['original_guide'] = guide.record()
            record['guide'] = guide.record()

            stage('checking_and_repairing_walks')
            guide, record['repair_evidence'] = repair_walks(
                chain, guide, planner,
                check_context=check,
                progress=evidence('repair_evidence'),
                maximum_repairs=12,
                maximum_rejoin_distance=40.,
                detour_seconds=20.,
                maximum_expansions=128,
            )
            record['guide'] = guide.record()
            if _chain_snapshot(chain) != prefix_state:
                raise ValueError('Synthetic GFay start prefix changed')

        stage('checking_complete_source_itinerary')
        plan = check_source_itinerary(chain, start, guide)
        if _chain_snapshot(chain) != prefix_state:
            raise ValueError('Complete GFay itinerary changed initial prefix')
        data = plan.record()
        plan_path = output.with_suffix('.plan.json')
        with plan_path.open('xb') as stream:
            stream.write(plan.payload)
        checked_plan = dict(
            file=str(plan_path),
            sha256=plan.sha256,
            cells=len(data['cells']),
            goal=data['goal'],
            goal_floor_height=data['goal_floor_height'],
            goal_source_ids=data['goal_source_ids'],
            final_proof_sha256=data['final_proof_sha256'],
            initial_prefix_unchanged=True,
            requires_fresh_live_arrival=True,
            zone_crossing_included=False,
        )
        record['checked_plan'] = checked_plan

        if plan_sections:
            stage('planning_walking_sections')
            bounds = RouteMotionBounds(
                'offline-section-probes', 'unmeasured-speed-hypothesis',
                .01, .15, .2, 30., .4, .01, 2., .1, guide.radius, guide.body_height,
            )
            sections = plan_walk_sections(
                chain, guide, planner,
                bounds=bounds,
                check_context=check,
                maximum_length=1000.,
                minimum_length=600.,
                candidate_spacing=25.,
                maximum_sections=16,
                maximum_queries=512,
                maximum_seconds=min(240., max(1., wall_seconds - (time.monotonic() - began))),
                progress=evidence('sections_progress'),
            )
            if _chain_snapshot(chain) != prefix_state:
                raise ValueError('Section planning changed initial GFay prefix')
            record['walk_sections'] = sections

        if check_carried_crossing:
            stage('checking_carried_crossing_cells')
            carried = chain.fork()
            for cell in data['cells']:
                check()
                if cell['kind'] != 'walk':
                    raise ValueError('GFay pre-line itinerary must contain ordinary walks only')
                carried = check_source_footprint(
                    carried,
                    swept_square(tuple(cell['start']), tuple(cell['end']), guide.radius),
                    terrain=planner.source,
                    static=planner.static,
                    bsp=planner.bsp,
                    region_policy=planner.region_policy,
                ).branch
            if carried.previous.proof_sha256 != data['final_proof_sha256']:
                raise ValueError('Carried pre-line floor proof differs from checked GFay itinerary')
            preline_proof = carried.previous.proof_sha256
            c_goal = crossing.goal_xy
            count = max(1, math.ceil(math.dist(goal, c_goal) / 2.))
            points = [goal] + [
                tuple(goal[k] + (c_goal[k] - goal[k]) * i / count for k in (0, 1))
                for i in range(1, count)
            ] + [c_goal]
            crossing_cells = []
            crossing_end = None
            for a, b in ((goal, goal), *zip(points, points[1:])):
                check()
                carried, cell = check_source_crossing_cell(
                    carried, a, b,
                    radius=1.2,
                    terrain=planner.source,
                    static=planner.static,
                    bsp=planner.bsp,
                    policy=crossing.policy,
                )
                value = cell.record()
                crossing_cells.append(dict(sha256=cell.sha256, **value))
                if b != goal and value['native']['possible_flags'] == [0x80000000]:
                    carried, end_cap = check_source_crossing_cell(
                        carried, b, b,
                        radius=1.2,
                        terrain=planner.source,
                        static=planner.static,
                        bsp=planner.bsp,
                        policy=crossing.policy,
                    )
                    cap_value = end_cap.record()
                    if cap_value['native']['possible_flags'] != [0x80000000]:
                        raise ValueError('Carried GFay crossing final cap no longer lies wholly in transition')
                    crossing_cells.append(dict(sha256=end_cap.sha256, **cap_value))
                    crossing_end = b
                    break
            if crossing_end is None:
                raise ValueError('Carried GFay crossing did not reach a complete body cell in transition')
            if _chain_snapshot(chain) != prefix_state:
                raise ValueError('Carried GFay crossing check changed initial prefix')
            record['carried_crossing'] = dict(
                descriptor=crossing.record(),
                preline_floor_proof_sha256=preline_proof,
                first_cell_previous_sha256=crossing_cells[0]['terrain']['previous_sha256'],
                synthetic_preline_floor_seed=False,
                start=goal,
                region_center_target=c_goal,
                transition_endpoint=crossing_end,
                endpoint_reason='first_complete_body_cell_and_cap_in_exact_native_label',
                possible_transition_regions=sorted({r for c in crossing_cells for r in c['possible_transition_regions']}),
                cells=crossing_cells,
                destination_server_verified=False,
                input_authorized=False,
                real_client_accepted=False,
            )
            record['zone_transition_checked'] = True
    except (ValueError, TimeoutError, OSError, KeyError, TypeError) as error:
        record.update(status='refused', reason=str(error))
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    try:
        for name, pin in code_pins.items():
            checked_bytes(name, pin)
        for name, pin in DATA_PINS.items():
            checked_bytes(root / name, pin)
        check()
        record['inputs_rehashed'] = True
    except (ValueError, TimeoutError, OSError) as error:
        record.update(status='refused', reason=str(error), inputs_rehashed=False)
    if checked_plan is not None and record['status'] != 'refused':
        record.update(source_candidate=True, status='checked', stage='finished')
    record['completed'] = True
    save()
    print(json.dumps(dict(
        output=str(output),
        sha256=sha256(output.read_bytes()).hexdigest(),
        route_name=route_name,
        status=record['status'],
        source_candidate=record['source_candidate'],
        zone_transition_checked=record['zone_transition_checked'],
        operations=len(record.get('guide', {}).get('operations', [])),
        sections=len(record.get('walk_sections', {}).get('sections', [])),
        crossing_cells=len(record.get('carried_crossing', {}).get('cells', [])),
        reason=record.get('reason'),
        seconds=record['seconds'],
        cpu_seconds=record['cpu_seconds'],
    )), flush=True)
    return 0 if record['source_candidate'] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--route', choices=sorted(ROUTES), required=True)
    parser.add_argument('--connection-rounds', type=int, default=12)
    parser.add_argument('--plan-sections', action='store_true')
    parser.add_argument('--check-carried-crossing', action='store_true')
    parser.add_argument('--wall-seconds', type=float, default=DEFAULT_WALL_SECONDS)
    parser.add_argument('--nice', type=int, default=19)
    parser.add_argument('--prior-guide', action='append', default=[],
                        help='Pinned nav-candidates NAME:SHA256 (1 for replay, 2+ for join)')
    args = parser.parse_args()
    store = Path.home() / '.local/share/eql-automation/nav-candidates'
    prior_guides = []
    for item in args.prior_guide:
        name, sep, pin = item.partition(':')
        if not sep or not name or len(pin) != 64:
            parser.error('Each --prior-guide must be NAME:SHA256')
        prior_guides.append((name, pin))
    if (args.output.exists() or args.output.is_symlink()
            or args.output.with_suffix('.plan.json').exists()
            or args.output.with_suffix('.plan.json').is_symlink()
            or args.output.parent.resolve() != store.resolve()
            or not 0 <= args.connection_rounds <= 24
            or not 0 <= len(prior_guides) <= 4
            or not 60. <= args.wall_seconds <= 900.
            or not 0 <= args.nice <= 19):
        parser.error('Use a new private nav-candidates output and valid bounds')
    os.umask(0o077)
    if args.nice:
        os.nice(args.nice)

    def expired(*_):
        raise TimeoutError('Offline GFay transit CPU/wall budget exhausted')

    signal.signal(signal.SIGALRM, expired)
    signal.signal(signal.SIGXCPU, expired)
    resource.setrlimit(resource.RLIMIT_CPU, (int(CPU_SECONDS) + 5, int(CPU_SECONDS) + 10))
    signal.setitimer(signal.ITIMER_REAL, args.wall_seconds)
    return run(
        args.project.resolve(),
        args.output,
        route_name=args.route,
        connection_rounds=args.connection_rounds,
        plan_sections=args.plan_sections,
        check_carried_crossing=args.check_carried_crossing,
        wall_seconds=args.wall_seconds,
        prior_guides=tuple(prior_guides),
    )


if __name__ == '__main__':
    raise SystemExit(main())
