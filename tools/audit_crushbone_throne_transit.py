#!/usr/bin/env python3
"""Develop North Wall -> Throne hints from copied client geometry only.

The start is an independent, synthetic unique-floor hypothesis, never a replay
of the Mines route or an observation of the owner's character. The complete
start cap and route are checked against terrain, static objects and regions.
Every source floor at the goal remains eligible for proposal; label Z is unused.
No result from this offline tool grants permission to move a character.
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

PROJECT = Path(__file__).resolve().parents[1]
STORE = Path('/home/blizz/.local/share/eql-automation')
sys.path[:0] = [str(PROJECT), str(STORE/'owner-assist/0.39.4')]

from eql_automation.crushbone_assets import DATA_NAME, DATA_PINS, load_crushbone_assets
from eql_automation.native_region_policy import encoded
from eql_automation.owner_route_assets import checked_bytes
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain, inside, rational
from eql_automation.ground_sweep import hull
from eql_automation.source_guide_compaction import compact_source_guide
from eql_automation.source_itinerary import (
    SourceItineraryGuide, SourceWalkHint, plan_source_itinerary,
)
from eql_automation.source_step_links import discover_step_links
from eql_automation.source_transit_graph import SourceTransitGraph
from eql_automation.static_floor_guard import check_source_static_floor

START = (-95., -78.)
GOAL = (106., 154.)


def filter_centers(graph, prefix, planner, *, rounds, check, progress):
    """Prune fixed graph waypoints, never whole components or goal layers.

    Each face center is a mandatory point in this proposal graph. Its own
    source-face seed is an OFFLINE hypothesis used only to reject that point.
    Passing caps do not replace the caller's floor or accept any route edge.
    Query/budget/ambiguity failures abort rather than becoming exclusions.
    """
    excluded = set()
    cache = {}
    attempts = []
    rejected_reasons = {'selected_floor_uncovered_ground_area',
                        'other_source_surface_intersects_body_band'}
    for attempt in range(rounds+1):
        check()
        proposal = graph.propose(prefix, START, GOAL, excluded=excluded, max_seconds=10.)
        if proposal is None:
            progress(attempts, cache, len(excluded))
            raise ValueError('No proposal after bounded fixed-center exclusions; physical disconnection not proven')
        faces = tuple(dict.fromkeys(face for edge in proposal.edges
            for face in (edge.origin, edge.destination) if face in graph.centers))
        rejected = []
        for face in faces:
            check()
            if face not in cache:
                point = graph.centers[face][:2]
                evidence = dict(kind='offline_proposal_center_hypothesis',
                    source_wld_sha256=planner.source.wld_sha256,
                    face=face, point=point, radius=1.2, body_height=6.,
                    current_character_observation=False, input_authorized=False)
                cap = swept_square(point, point, 1.2)
                sources = planner.source.source_faces_for_footprint(cap)
                probe = SourceFloorChain(inventory_sha256=planner.source.wld_sha256,
                    seed_evidence_sha256=sha256(encoded(evidence)).hexdigest(),
                    seed_ids=(face,), body_height=6.)
                floor = probe.advance(cap, sources)
                placed = (check_source_static_floor(floor, cap, sources, planner.static)
                          if floor.candidate else None)
                accepted = floor.candidate and placed.candidate
                reason = placed.reason if placed is not None else floor.reason
                # A one-face synthetic seed can miss joins retained by an
                # arriving prefix. Require a deficit in ALL eligible local
                # support from the graph component before excluding coverage.
                support = [(s.fragment, s.face) for s in sources
                    if graph.components.components.get((s.fragment, s.face))
                       == graph.components.components[face]]
                expanded = hull((x+dx, y+dy) for x, y in cap
                    for dx in (-.002, .002) for dy in (-.002, .002))
                witness = next((point for point in expanded if not any(
                    inside(rational((point,))[0], rational(graph.components.faces[k][0]))
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
                    progress(attempts, cache, len(excluded))
                    raise ValueError('Center query cannot justify pruning '+str(face)+': '+reason)
            if cache[face]['excluded_center']:
                rejected.append(face)
        attempts.append(dict(round=attempt, proposal=asdict(proposal), rejected_faces=rejected))
        if not rejected:
            progress(attempts, cache, len(excluded))
            return proposal
        # Every incoming/outgoing graph edge explicitly visits this center.
        # The start/goal attachment edges also visit it; other faces in the
        # same component and other goal layers remain available.
        bad = set(rejected)
        for face in bad:
            excluded.add(('start', face)); excluded.add(('goal', face))
        for edges in graph.adjacent.values():
            excluded.update(edge.identity for edge in edges
                            if edge.origin in bad or edge.destination in bad)
        progress(attempts, cache, len(excluded))
    raise ValueError('Fixed-center proposal retry budget exhausted')


def run(output, *, wall_budget, cpu_budget, prior_path=None, prior_pin=None, walk_range=None,
        center_rounds=0, smooth=False, underlay_steps=False, exclude_covered=False):
    began, cpu_began = time.monotonic(), time.process_time()
    pins = {str(p.relative_to(PROJECT)): sha256(p.read_bytes()).hexdigest()
            for p in (Path(__file__).resolve(),
                      Path(__file__).with_name('audit_crushbone_camp_transit.py').resolve(),
                      Path(__file__).with_name('source_walk_shortcuts.py').resolve(),
                      Path(__file__).with_name('source_covered_floors.py').resolve(),
                      *sorted((PROJECT/'eql_automation').glob('*.py')))}
    record = dict(format='eql-offline-throne-transit-v1',
        origin='north-wall', destination='throne', start=START, goal=GOAL,
        status='running', stage='loading', completed=False, source_candidate=False,
        synthetic_start=True, current_character_observation=False,
        historical_prefix_replayed=False, label_z_used_for_floor_selection=False,
        input_authorized=False, game_input_sent=False, real_client_accepted=False,
        cpu_budget_seconds=cpu_budget, wall_budget_seconds=wall_budget,
        underlay_step_proposals=underlay_steps,
        code_sha256=pins, data_sha256=DATA_PINS)

    def save():
        record.update(seconds=time.monotonic()-began,
                      cpu_seconds=time.process_time()-cpu_began)
        temporary = output.with_suffix('.json.tmp')
        with temporary.open('x') as stream:
            json.dump(record, stream, indent=2, allow_nan=False)
            stream.write('\n')
        temporary.replace(output)

    def check():
        if time.monotonic()-began > wall_budget:
            raise TimeoutError('Offline Throne audit wall budget exhausted')
        if time.process_time()-cpu_began > cpu_budget:
            raise TimeoutError('Offline Throne audit CPU budget exhausted')

    def stage(name):
        check()
        record['stage'] = name
        save()
        print(json.dumps(dict(stage=name, seconds=record['seconds'],
                              cpu_seconds=record['cpu_seconds'])), flush=True)

    def itinerary(chain, guide):
        check()
        return plan_source_itinerary(chain, START, guide, planner.source,
            planner.static, planner.bsp, planner.region_policy, check_context=check,
            max_seconds=max(.001, min(120., wall_budget-(time.monotonic()-began))))

    save()
    try:
        assets = load_crushbone_assets(STORE/'owner-route-data'/DATA_NAME,
                                      native_planning=True)
        planner = assets.planner
        # XY is confirmed against the pinned client annotations. Their Z and
        # suggested level ranges are recorded, not used to select a floor.
        annotations = {}
        for name, xy in (('north-wall', START), ('throne', GOAL)):
            matches = [a for a in assets.annotations
                       if (-a.map_xyz[0], -a.map_xyz[1]) == xy]
            if len(matches) != 1:
                raise ValueError('No unique copied map annotation for '+name)
            annotations[name] = asdict(matches[0])
        record['annotations'] = annotations
        proposal = planner.source.propose_unique_diffuse_floor(START, body_height=6.)
        seed = dict(kind='synthetic_unique_source_floor', start=START,
            proposal=asdict(proposal), source_wld_sha256=planner.source.wld_sha256,
            data_sha256=DATA_PINS, radius=1.2, body_height=6.,
            synthetic_reference=True, current_character_position=False,
            current_character_observation=False, historical_prefix_replayed=False)
        seed_pin = sha256(encoded(seed)).hexdigest()
        chain = SourceFloorChain(inventory_sha256=planner.source.wld_sha256,
            seed_evidence_sha256=seed_pin, seed_ids=proposal.selected_ids,
            body_height=6.)
        cap = swept_square(START, START, 1.2)
        floor = chain.advance(cap, planner.source.source_faces_for_footprint(cap))
        if not floor.candidate:
            raise ValueError('Synthetic start footprint: '+floor.reason)
        record.update(seed=seed, seed_sha256=seed_pin, initial_floor=asdict(floor),
            goal_intersections=[asdict(h) for h in planner.source.source_hits_at(GOAL)])
        stage('checking_start_cap')
        cap_guide = SourceItineraryGuide('crushbone', planner.source.wld_sha256,
            planner.static.inventory_sha256, seed_pin, 1.2, 6., START,
            (SourceWalkHint(START, START),))
        cap_plan = itinerary(chain, cap_guide)
        record.update(start_cap_plan=cap_plan.record(), start_cap_sha256=cap_plan.sha256)
        if prior_path is None:
            stage('discovering_steps')
            links = discover_step_links(tuple(planner.source.sources),
                inventory_sha256=planner.source.wld_sha256,
                max_step_height=2., min_width=2.404, include_internal_edges=underlay_steps)
            record['step_links'] = len(links)
            stage('building_graph')
            graph = SourceTransitGraph(tuple(planner.source.sources),
                inventory_sha256=planner.source.wld_sha256, step_links=links,
                radius=1.2, max_step_height=2., max_lift=4.)
            record['goal_components'] = asdict(graph.components.goal(chain, GOAL))
            stage('proposing')
            if center_rounds:
                def progress(attempts, cache, excluded):
                    record['center_filter'] = dict(rounds=center_rounds, attempts=attempts,
                        caps=list(cache.values()), excluded_directed_edges=excluded,
                        current_floor_unchanged=True, whole_components_excluded=False,
                        physical_disconnection_proven=False)
                    save()
                    print(json.dumps(dict(stage='center_filter', rounds=len(attempts),
                        checked_centers=len(cache), excluded_centers=sum(r['excluded_center'] for r in cache.values()),
                        excluded_edges=excluded)), flush=True)
                transit = filter_centers(graph, chain, planner, rounds=center_rounds,
                                         check=check, progress=progress)
            else:
                if exclude_covered:
                    from tools.source_covered_floors import propose_above_covered_floors
                    stage('proposing_above_underlays')
                    def progress(evidence):
                        record['covered_floor_filter'] = evidence
                        save()
                    transit = propose_above_covered_floors(graph, chain, START, GOAL,
                        body_height=6., check_context=check, progress=progress)
                else:
                    transit = graph.propose(chain, START, GOAL, max_seconds=10.)
            if transit is None:
                raise ValueError('No Throne proposal under current source/step model')
            record['proposal'] = asdict(transit)
            guide = transit.guide(static_inventory_sha256=planner.static.inventory_sha256,
                                  radius=1.2, body_height=6.)
            record['uncompacted_operations'] = len(guide.operations)
            record['uncompacted_guide'] = guide.record()
            guide = compact_source_guide(guide)
            record['guide'] = guide.record()
            record['compaction'] = dict(maximum_length=8.,
                geometry_equivalence_claimed=False, requires_full_rebuild=True)
        else:
            from audit_crushbone_camp_transit import replay_parent
            from eql_automation.source_detour import find_source_detour
            prior = json.loads(checked_bytes(prior_path, prior_pin))
            if (prior['format'] != record['format'] or prior['data_sha256'] != DATA_PINS
                    or prior['seed_sha256'] != seed_pin or encoded(prior['seed']) != encoded(seed)):
                raise ValueError('Prior proposal does not use this independent source seed')
            guide = SourceItineraryGuide.from_record(prior['guide'])
            record['guide'] = guide.record()
            if (guide.goal != GOAL or guide.radius != 1.2 or guide.body_height != 6.
                    or guide.operations[0].start != START):
                raise ValueError('Prior guide has different bounds or endpoints')
            if smooth:
                from tools.source_walk_shortcuts import shortcut_walks
                record['smoothing_prior_sha256'] = prior_pin
                stage('shortcutting_walks')
                def progress(evidence):
                    record['smoothing'] = evidence
                    save()
                guide, evidence = shortcut_walks(chain, guide, planner.source, planner.static,
                    check_context=check, progress=progress)
                record['smoothing'] = evidence
                guide = compact_source_guide(guide)
            else:
                first, last = walk_range
                if (not 0 <= first <= last < len(guide.operations)
                        or any(type(op) is not SourceWalkHint for op in guide.operations[first:last+1])):
                    raise ValueError('Replacement must be an explicit contiguous walk-only range')
                start, goal = guide.operations[first].start, guide.operations[last].end
                record['repair'] = dict(prior_path=str(prior_path), prior_sha256=prior_pin,
                    first_walk=first, last_walk=last, start=start, goal=goal,
                    automatic_edge_exclusion=False, original_guide_sha256=sha256(encoded(guide.record())).hexdigest())
                # The original start floor is reconstructed, then every prior walk
                # and step is fully checked. No guessed floor is seeded at the fault.
                stage('checking_repair_prefix')
                prefix_guide = replace(guide, goal=start,
                    operations=guide.operations[:first] or (SourceWalkHint(START, START),))
                prefix_plan = itinerary(chain, prefix_guide)
                branch, replayed_goal, replay = replay_parent(
                    dict(plan=prefix_plan.record(), guide=prefix_guide.record()),
                    planner.source, planner.static, check)
                if replayed_goal != start:
                    raise ValueError('Replayed repair prefix ends at a different point')
                record['repair'].update(prefix_plan_sha256=prefix_plan.sha256, replay=replay)
                stage('proposing_local_detour')
                detour, _ = find_source_detour(branch, start, goal, planner.source,
                    planner.static, radius=1.2, max_seconds=60., max_expansions=128)
                record['repair']['detour'] = asdict(detour)
                if not detour.candidate:
                    raise ValueError('Local walk repair: '+detour.reason)
                operations = tuple(SourceWalkHint(a, b) for a, b in zip(detour.points, detour.points[1:]))
                if not operations:
                    operations = (SourceWalkHint(start, goal),)
                guide = replace(guide,
                    provenance_sha256=sha256(encoded(record['repair'])).hexdigest(),
                    operations=guide.operations[:first]+operations+guide.operations[last+1:])
                guide.validate()
        if smooth and prior_path is None:
            from tools.source_walk_shortcuts import shortcut_walks
            stage('shortcutting_new_proposal')
            def progress(evidence):
                record['smoothing'] = evidence
                save()
            guide, record['smoothing'] = shortcut_walks(chain, guide, planner.source, planner.static,
                check_context=check, progress=progress)
            guide = compact_source_guide(guide)
        record['guide'] = guide.record()
        stage('checking_complete_route')
        plan = itinerary(chain, guide)
        result = plan.record()
        record.update(plan=result, plan_sha256=plan.sha256,
            reached_goal_floor=dict(height=result['goal_floor_height'],
                                    source_ids=result['goal_source_ids']),
            source_candidate=True, status='checked', stage='finished')
    except (ValueError, TimeoutError) as error:
        record.update(status='refused', reason=str(error))
    # The main routine arms the wall timer; leave time to pin and persist a
    # refused result after expiry. The independent CPU hard limit remains.
    signal.setitimer(signal.ITIMER_REAL, 0)
    for name, pin in DATA_PINS.items():
        checked_bytes(STORE/'owner-route-data'/DATA_NAME/name, pin)
    for name, pin in pins.items():
        checked_bytes(PROJECT/name, pin)
    if prior_path is not None:
        checked_bytes(prior_path, prior_pin)
    record['completed'] = True
    save()
    print(json.dumps(dict(output=str(output), sha256=sha256(output.read_bytes()).hexdigest(),
        status=record['status'], stage=record['stage'], reason=record.get('reason'),
        seconds=record['seconds'], cpu_seconds=record['cpu_seconds'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--wall-budget', type=float, default=180.)
    parser.add_argument('--cpu-budget', type=float, default=40.)
    parser.add_argument('--prior', type=Path, help='Pinned earlier offline proposal to repair')
    parser.add_argument('--prior-sha256')
    parser.add_argument('--replace-walks', type=int, nargs=2, metavar=('FIRST', 'LAST'),
                        help='Inclusive walk-only range; does not remove or bypass a step')
    parser.add_argument('--smooth', action='store_true', help='Replace walking zigzags with checked source/static shortcuts; retain every step')
    parser.add_argument('--underlay-steps', action='store_true',
                        help='Also propose steps where the lower floor continues under a platform')
    parser.add_argument('--exclude-covered-floors', action='store_true',
                        help='Exclude lower graph faces only after exact upper-surface partition and headroom checks')
    parser.add_argument('--center-rounds', type=int, default=0,
                        help='Up to 16 retries excluding only graph centers refused by full caps')
    args = parser.parse_args()
    if (args.output.exists() or args.output.is_symlink()
            or args.output.with_suffix('.json.tmp').exists()
            or args.output.parent.resolve() != (STORE/'nav-candidates').resolve()
            or not 30 <= args.wall_budget <= 300 or not 5 <= args.cpu_budget <= 120
            or not 0 <= args.center_rounds <= 16
            or args.prior is not None and (args.center_rounds or args.underlay_steps or args.exclude_covered_floors)
            or args.center_rounds and args.exclude_covered_floors):
        parser.error('Use a new private nav-candidates output and bounded CPU/wall budgets')
    if args.prior is not None or args.prior_sha256 is not None or args.replace_walks is not None:
        if (args.prior is None or args.prior_sha256 is None
                or bool(args.replace_walks is not None) == args.smooth
                or args.prior.parent.resolve() != (STORE/'nav-candidates').resolve()
                or args.prior.is_symlink() or not args.prior.is_file()
                or len(args.prior_sha256) != 64
                or any(c not in '0123456789abcdef' for c in args.prior_sha256)):
            parser.error('Repair needs a private prior file, its exact SHA256 and either a walk range or --smooth')
    os.umask(0o077)
    os.nice(19)
    # Some graph construction loops have count bounds but no clock callback.
    # Interrupt this offline process as well as checking cooperative budgets.
    # None of these signal handlers are used by the owner runtime.
    def expired(signum, frame):
        label = 'wall' if signum == signal.SIGALRM else 'CPU'
        raise TimeoutError('Offline Throne audit '+label+' process budget exhausted')
    signal.signal(signal.SIGALRM, expired)
    signal.signal(signal.SIGXCPU, expired)
    cpu_limit = math.ceil(time.process_time()+args.cpu_budget)
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit+5))
    signal.setitimer(signal.ITIMER_REAL, args.wall_budget)
    run(args.output, wall_budget=args.wall_budget, cpu_budget=args.cpu_budget,
        prior_path=args.prior, prior_pin=args.prior_sha256, walk_range=args.replace_walks,
        center_rounds=args.center_rounds, smooth=args.smooth, underlay_steps=args.underlay_steps,
        exclude_covered=args.exclude_covered_floors)
