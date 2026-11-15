#!/usr/bin/env python3
"""Propose and check Newbie Hills -> level-5 camps using copied Butcher source.

The map supplies XY only. The independent initial source-floor hypothesis is
synthetic, not a retained/live character position. Exact-edge graph proposals
do not authorize movement; the full itinerary still checks source floors,
static placements and native region metadata. No game input is available.
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
import tempfile
import time

PROJECT = Path(__file__).resolve().parents[1]
STORE = Path.home()/'.local/share/eql-automation'
sys.path[:0] = [str(PROJECT), str(STORE/'owner-assist/0.39.4')]

from eql_automation.butcher_assets import DATA_NAME, DATA_PINS, load_butcher_assets
from eql_automation.native_region_policy import encoded
from eql_automation.owner_route_assets import checked_bytes
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_guide_compaction import compact_source_guide
from eql_automation.source_itinerary import SourceItineraryGuide, SourceWalkHint, plan_source_itinerary
from eql_automation.source_transit_graph import SourceTransitGraph

START = (-650., 2700.)
DESTINATIONS = {'goblin': (-2069., -298.), 'skeletons': (884., -1540.)}


def write_checkpoint(output, record):
    """Keep the previous checkpoint if serialization is interrupted."""
    fd, name = tempfile.mkstemp(dir=output.parent, prefix=output.name+'.', suffix='.tmp')
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(record, stream, indent=2, allow_nan=False); stream.write('\n')
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)


def run(output, *, destination, wall_budget, cpu_budget, proposal_only=False, repair=False,
        proposal_model='source', prior_path=None, prior_pin=None, start_via_edges=False,
        center_rounds=0):
    began, cpu_began = time.monotonic(), time.process_time()
    goal = DESTINATIONS[destination]
    pins = {str(p.relative_to(PROJECT)): sha256(p.read_bytes()).hexdigest()
            for p in (Path(__file__).resolve(), Path(__file__).with_name('source_walk_repairs.py'),
                      Path(__file__).with_name('source_transit_centers.py'),
                      Path(__file__).with_name('source_walk_prefix.py'),
                      *sorted((PROJECT/'eql_automation').glob('*.py')))}
    record = dict(format='eql-offline-butcher-camp-transit-v1',
        origin='newbie-hills', destination=destination, start=START, goal=goal,
        status='running', stage='loading', completed=False, source_candidate=False,
        ordinary_walking_only=True, proposal_only=proposal_only, repair_walks=repair,
        proposal_model=proposal_model, start_via_edges=start_via_edges, center_rounds=center_rounds,
        synthetic_start=True, current_character_observation=False,
        historical_prefix_replayed=False, label_z_used_for_floor_selection=False,
        input_authorized=False, game_input_sent=False, real_client_accepted=False,
        cpu_budget_seconds=cpu_budget, wall_budget_seconds=wall_budget,
        code_sha256=pins, data_sha256=DATA_PINS)

    def save():
        record.update(seconds=time.monotonic()-began,
                      cpu_seconds=time.process_time()-cpu_began)
        write_checkpoint(output, record)

    def check():
        if time.monotonic()-began > wall_budget:
            raise TimeoutError('Offline Butcher transit wall budget exhausted')
        if time.process_time()-cpu_began > cpu_budget:
            raise TimeoutError('Offline Butcher transit CPU budget exhausted')

    def stage(name):
        check(); record['stage'] = name; save()
        print(json.dumps(dict(stage=name, seconds=record['seconds'],
                              cpu_seconds=record['cpu_seconds'])), flush=True)

    def itinerary(chain, guide):
        check()
        return plan_source_itinerary(chain, START, guide, planner.source,
            planner.static, planner.bsp, planner.region_policy, check_context=check,
            max_seconds=max(.001, min(240., wall_budget-(time.monotonic()-began))))

    save()
    try:
        assets = load_butcher_assets(STORE/'owner-route-data'/DATA_NAME, native_planning=True)
        planner = assets.planner
        annotations = {}
        for name, point in (('newbie-hills', START), (destination, goal)):
            matches = [a for a in assets.annotations if tuple(-v for v in a.map_xyz[:2]) == point]
            if len(matches) != 1:
                raise ValueError('No unique copied map annotation for '+name)
            annotations[name] = asdict(matches[0])
        record['annotations'] = annotations
        proposal = planner.source.propose_unique_diffuse_floor(START, body_height=6.)
        seed = dict(kind='synthetic_unique_source_floor', start=START,
            proposal=asdict(proposal), source_wld_sha256=planner.source.wld_sha256,
            data_sha256=DATA_PINS, radius=1.2, body_height=6.,
            synthetic_reference=True, current_character_observation=False)
        seed_pin = sha256(encoded(seed)).hexdigest()
        chain = SourceFloorChain(inventory_sha256=planner.source.wld_sha256,
            seed_evidence_sha256=seed_pin, seed_ids=proposal.selected_ids, body_height=6.)
        cap = swept_square(START, START, 1.2)
        floor = chain.advance(cap, planner.source.source_faces_for_footprint(cap))
        if not floor.candidate:
            raise ValueError('Synthetic start footprint: '+floor.reason)
        record.update(seed=seed, seed_sha256=seed_pin, initial_floor=asdict(floor),
            goal_intersections=[asdict(hit) for hit in planner.source.source_hits_at(goal)])
        stage('checking_start_cap')
        cap_guide = SourceItineraryGuide('butcher', planner.source.wld_sha256,
            planner.static.inventory_sha256, seed_pin, 1.2, 6., START,
            (SourceWalkHint(START, START),))
        cap_plan = itinerary(chain, cap_guide)
        record.update(start_cap_plan=cap_plan.record(), start_cap_sha256=cap_plan.sha256)
        retained_ops = ()
        transit_start, transit_prefix = START, chain
        if prior_path is not None:
            stage('rebuilding_prior_checked_prefix')
            prior = json.loads(checked_bytes(prior_path, prior_pin))
            evidence = prior.get('repair_evidence', {})
            if (prior['format'] != record['format'] or prior['data_sha256'] != DATA_PINS
                    or prior['seed_sha256'] != seed_pin or prior['seed'] != json.loads(encoded(seed))
                    or prior['destination'] != destination or prior['completed'] is not True
                    or prior['source_candidate'] is not False or prior['game_input_sent'] is not False):
                raise ValueError('Prior record does not bind a synthetic prefix of this destination')
            original = SourceItineraryGuide.from_record(prior['guide'])
            completed = evidence.get('completed_operations')
            if (original.zone != 'butcher' or original.goal != goal
                    or original.wld_sha256 != planner.source.wld_sha256
                    or original.static_inventory_sha256 != planner.static.inventory_sha256
                    or original.radius != 1.2 or original.body_height != 6.
                    or original.operations[0].start != START):
                raise ValueError('Prior checked walking prefix is incomplete or mismatched')
            from source_walk_prefix import replay_walk_prefix
            transit_prefix, transit_start, retained_ops = replay_walk_prefix(
                chain, original, evidence, planner, check_context=check)
            record['prefix_from'] = dict(path=str(prior_path), sha256=prior_pin,
                rechecked_operations=len(retained_ops), original_operations_completed=completed,
                adopted_detours=sum(bool(r['adopted']) for r in evidence.get('repairs', [])),
                reached_proof_sha256=transit_prefix.previous.proof_sha256,
                end=transit_start, new_source_seed=False, current_character_observation=False)
        if proposal_model == 'mesh':
            from eqnav import mesh as mesh_module
            stage('proposing_mesh_xy')
            code_path = Path(mesh_module.__file__).resolve()
            record['legacy_code_sha256'] = {str(code_path):sha256(code_path.read_bytes()).hexdigest()}
            mesh = mesh_module.NavMesh.load(STORE/'owner-route-data'/DATA_NAME/'butcher.npz',
                                           expected_sha256=DATA_PINS['butcher.npz'])
            goal_floor = planner.source.propose_unique_diffuse_floor(goal, body_height=6.)
            record['mesh_goal_query_hypothesis'] = asdict(goal_floor)
            try:
                path = mesh.find_path((*START, proposal.height), (*goal, goal_floor.height),
                    water_cost=None, margin=1.2, allow_zone_lines=(), max_expansions=65536)
            except mesh_module.NavMeshError as error:
                raise ValueError('Mesh XY proposal: '+str(error)) from error
            record['proposal'] = dict(kind='mesh_xy_hints_only', mesh_sha256=mesh.sha256,
                points=[tuple(float(v) for v in p) for p in path.points],
                polygons=[int(p) for p in path.polys], length=float(path.length),
                areas=sorted(int(v) for v in path.areas), mesh_z_used_for_floor_selection=False,
                source_continuity_checked=False, input_authorized=False)
            ops = []; position = START
            for point in (*path.points, goal):
                end = tuple(float(v) for v in point[:2])
                if end == position: continue
                count = max(1, math.ceil(math.dist(position, end)/8.)); origin = position
                for i in range(count):
                    next_point = end if i == count-1 else tuple(origin[k]+(end[k]-origin[k])*(i+1)/count for k in (0, 1))
                    ops.append(SourceWalkHint(position, next_point)); position = next_point
            guide = SourceItineraryGuide('butcher', planner.source.wld_sha256,
                planner.static.inventory_sha256, seed_pin, 1.2, 6., goal, tuple(ops))
            proposal_length = float(path.length)
        else:
            stage('building_graph')
            graph = SourceTransitGraph(tuple(planner.source.sources),
                inventory_sha256=planner.source.wld_sha256, step_links=(), radius=1.2)
            record['graph'] = dict(faces=graph.components.face_count,
                components=graph.components.component_count,
                directed_edges=sum(len(v) for v in graph.adjacent.values()), step_links=0)
            record['goal_components'] = asdict(graph.components.goal(transit_prefix, goal))
            stage('proposing')
            if center_rounds:
                from source_transit_centers import filter_transit_centers
                def center_progress(attempts, cache, excluded):
                    record['center_filter'] = dict(rounds=center_rounds, attempts=attempts,
                        caps=list(cache.values()), excluded_directed_edges=excluded,
                        current_floor_unchanged=True, whole_components_excluded=False,
                        current_character_observation=False, input_authorized=False)
                    save()
                    print(json.dumps(dict(stage='filtering_centers', attempts=len(attempts),
                        checked_centers=len(cache), excluded_centers=sum(r['excluded_center'] for r in cache.values()),
                        excluded_edges=excluded)), flush=True)
                transit = filter_transit_centers(graph, transit_prefix, transit_start, goal, planner,
                    rounds=center_rounds, check=check, progress=center_progress,
                    start_via_edges=start_via_edges)
            else:
                transit = graph.propose(transit_prefix, transit_start, goal, max_seconds=30.,
                                        start_via_edges=start_via_edges)
            if transit is None:
                raise ValueError('No proposal under the current exact-edge ordinary-walking model; physical disconnection not proven')
            record['proposal'] = asdict(transit)
            guide = transit.guide(static_inventory_sha256=planner.static.inventory_sha256,
                                  radius=1.2, body_height=6., zone='butcher')
            guide = replace(guide, operations=retained_ops+guide.operations)
            proposal_length = sum(edge.cost for edge in transit.edges)+sum(math.dist(op.start, op.end) for op in retained_ops)
        record['uncompacted_operations'] = len(guide.operations)
        guide = compact_source_guide(guide)
        provenance = encoded(dict(proposal_sha256=sha256(encoded(record['proposal'])).hexdigest(),
            annotations=annotations, data_sha256=DATA_PINS, zone='butcher',
            maximum_compacted_length=8., label_z_used=False, requires_full_rebuild=True,
            prefix_from=record.get('prefix_from')))
        guide = replace(guide, provenance_sha256=sha256(provenance).hexdigest())
        guide.validate()
        record.update(guide=guide.record(), provenance=json.loads(provenance),
            proposal_length=proposal_length)
        if repair:
            from source_walk_repairs import repair_walks
            record['original_guide'] = guide.record()
            stage('checking_and_repairing_walks')
            def progress(evidence):
                record['repair_evidence'] = evidence
                save()
            guide, record['repair_evidence'] = repair_walks(chain, guide, planner,
                check_context=check, progress=progress)
            guide = compact_source_guide(guide)
            record['guide'] = guide.record()
        if proposal_only:
            record.update(status='proposed', stage='finished')
        else:
            stage('checking_complete_route')
            plan = itinerary(chain, guide)
            data = plan.record()
            plan_path = output.with_suffix('.plan.json')
            with plan_path.open('xb') as stream: stream.write(plan.payload)
            record.update(checked_plan=dict(file=str(plan_path), sha256=plan.sha256,
                cells=len(data['cells']), goal=data['goal'],
                goal_floor_height=data['goal_floor_height'], goal_source_ids=data['goal_source_ids']),
                source_candidate=True, status='checked', stage='finished')
    except (ValueError, TimeoutError) as error:
        record.update(status='refused', reason=str(error))
    signal.setitimer(signal.ITIMER_REAL, 0)
    for name, pin in DATA_PINS.items(): checked_bytes(STORE/'owner-route-data'/DATA_NAME/name, pin)
    for name, pin in pins.items(): checked_bytes(PROJECT/name, pin)
    for name, pin in record.get('legacy_code_sha256', {}).items(): checked_bytes(name, pin)
    if prior_path is not None: checked_bytes(prior_path, prior_pin)
    record['completed'] = True
    save()
    print(json.dumps(dict(output=str(output), sha256=sha256(output.read_bytes()).hexdigest(),
        status=record['status'], stage=record['stage'], reason=record.get('reason'),
        seconds=record['seconds'], cpu_seconds=record['cpu_seconds'],
        operations=len(record.get('guide', {}).get('operations', [])))), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--destination', choices=tuple(DESTINATIONS), default='goblin')
    parser.add_argument('--proposal-only', action='store_true')
    parser.add_argument('--proposal-model', choices=('source', 'mesh'), default='source',
                        help='XY proposal source; both still need complete source/static/region checking')
    parser.add_argument('--repair-walks', action='store_true',
                        help='Check every walk and attempt bounded local repairs at terrain/static refusals')
    parser.add_argument('--start-via-edges', action='store_true',
                        help='Also propose leaving the selected start face through an exact shared edge')
    parser.add_argument('--center-rounds', type=int, default=0,
                        help='Bounded retries excluding only independently demonstrated blocked fixed centers')
    parser.add_argument('--resume-source-from', type=Path,
                        help='Rebuild a pinned checked prefix, then replace its failed suffix with a source-graph proposal')
    parser.add_argument('--prior-sha256')
    parser.add_argument('--wall-budget', type=float, default=240.)
    parser.add_argument('--cpu-budget', type=float, default=60.)
    args = parser.parse_args()
    if ((args.start_via_edges or args.center_rounds) and args.proposal_model != 'source'
            or not 0 <= args.center_rounds <= 16):
        parser.error('Start-edge attachments and 0–16 center retries apply only to source-graph proposals')
    if (args.output.exists() or args.output.is_symlink()
            or args.output.with_suffix('.json.tmp').exists()
            or args.output.with_suffix('.plan.json').exists()
            or args.output.parent.resolve() != (STORE/'nav-candidates').resolve()
            or not 30 <= args.wall_budget <= 300 or not 5 <= args.cpu_budget <= 120):
        parser.error('Use a new private nav-candidates output and bounded CPU/wall budgets')
    if args.resume_source_from is not None or args.prior_sha256 is not None:
        if (args.resume_source_from is None or args.prior_sha256 is None
                or args.proposal_model != 'source'
                or args.resume_source_from.parent.resolve() != (STORE/'nav-candidates').resolve()
                or args.resume_source_from.resolve() == args.output.resolve()):
            parser.error('Source resumption needs a separate pinned private diagnostic')
    os.umask(0o077); os.nice(19)
    def expired(*_): raise TimeoutError('Offline Butcher transit CPU/wall budget exhausted')
    signal.signal(signal.SIGALRM, expired); signal.signal(signal.SIGXCPU, expired)
    resource.setrlimit(resource.RLIMIT_CPU, (int(args.cpu_budget+5), int(args.cpu_budget+10)))
    signal.setitimer(signal.ITIMER_REAL, args.wall_budget)
    run(args.output, destination=args.destination, wall_budget=args.wall_budget,
        cpu_budget=args.cpu_budget, proposal_only=args.proposal_only, repair=args.repair_walks,
        proposal_model=args.proposal_model, prior_path=args.resume_source_from, prior_pin=args.prior_sha256,
        start_via_edges=args.start_via_edges, center_rounds=args.center_rounds)
