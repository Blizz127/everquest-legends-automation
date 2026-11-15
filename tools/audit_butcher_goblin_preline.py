#!/usr/bin/env python3
"""Offline source-only Goblin -> retained pre-line XY approach; no game input.

The Goblin start is a synthetic unique-Diffuse-floor hypothesis, not a live
arrival. The old selector supplies only its final XY, never floor or mesh Z.
When --check-carried-crossing is enabled, the exact reached pre-line floor
lineage continues directly through check_source_crossing_cell without any
synthetic floor seed at the pre-line point.
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

PRIOR_NAME = 'butcher-kaladim-to-gfay-complex-select-only-20261113T2248Z.json'
PRIOR_PIN = '5c7babe22742d9d1c9ae4d293e2f0a9f52ace21bd8687702260f1cedbd70fad8'
EXPECTED_START = (-2069., -298.)
EXPECTED_GOAL = (-3084.646484375, -1328.2936706542969)
CPU_SECONDS, DEFAULT_WALL_SECONDS = 240., 300.


def run(project, output, *, departure_rounds=8, center_rounds=0, connection_rounds=0,
        check_carried_crossing=False, plan_sections=False,
        wall_seconds=DEFAULT_WALL_SECONDS, resume_path=None, resume_pin=None):
    began, cpu_began = time.monotonic(), time.process_time()
    store = Path.home()/'.local/share/eql-automation'
    sys.path[:0] = [str(project), str(store/'owner-assist/0.39.4')]
    from eql_automation.butcher_assets import DATA_NAME, DATA_PINS, load_butcher_assets
    from eql_automation.butcher_crossing_assets import load_butcher_crossing
    from eql_automation.native_crossing_policy import check_source_crossing_cell
    from eql_automation.native_region_policy import encoded
    from eql_automation.owner_route_assets import checked_bytes
    from eql_automation.route_floor_commit import _chain_snapshot
    from eql_automation.route_geometry import RouteMotionBounds
    from eql_automation.source_destinations import destination_spec, load_source_guide
    from eql_automation.source_detour import swept_square
    from eql_automation.source_floor_chain import SourceFloorChain
    from eql_automation.source_itinerary import SourceItineraryGuide, SourceWalkHint, plan_source_itinerary
    from eql_automation.source_probe_geometry import check_source_footprint
    from eql_automation.source_transit_graph import SourceTransitGraph
    from eql_automation.source_walk_sections import plan_walk_sections
    from tools.audit_butcher_camp_transit import write_checkpoint, join_source_suffix
    from tools.source_transit_departures import filter_transit_departures
    from tools.source_transit_centers import filter_transit_centers
    from tools.source_transit_connections import filter_transit_connections
    from tools.source_walk_repairs import repair_walks
    from tools.source_walk_prefix import replay_walk_prefix

    root = store/'owner-route-data'/DATA_NAME
    prior_path = store/'nav-candidates'/PRIOR_NAME
    spec = destination_spec('goblin-camp')
    code_files = (Path(__file__).resolve(), project/'tools/audit_butcher_camp_transit.py',
        project/'tools/source_transit_departures.py', project/'tools/source_walk_repairs.py',
        project/'tools/source_walk_prefix.py',
        project/'tools/source_transit_centers.py',
        project/'tools/source_transit_connections.py',
        *sorted((project/'eql_automation').glob('*.py')))
    code_pins = {str(p):sha256(p.read_bytes()).hexdigest() for p in code_files}
    record = dict(format='eql-offline-goblin-gfay-preline-source-approach-v1',
        origin='goblin-camp', destination='gfay-retained-preline-xy',
        start=EXPECTED_START, goal=EXPECTED_GOAL, status='running', stage='loading',
        completed=False, source_candidate=False, ordinary_walking_only=True,
        proposal_model='full_source_graph',
        departure_rounds=0 if (center_rounds or connection_rounds) else departure_rounds,
        center_rounds=center_rounds,
        connection_rounds=connection_rounds,
        check_carried_crossing=check_carried_crossing,
        plan_sections=plan_sections,
        synthetic_start=True, synthetic_floor_seed=True,
        synthetic_preline_floor_seed=False,
        retained_real_arrival=False,
        current_character_observation=False, historical_prefix_replayed=False,
        mesh_z_used_for_floor_selection=False, label_z_used_for_floor_selection=False,
        zone_transition_checked=False, destination_server_verified=False,
        physical_disconnection_proven=False, input_authorized=False,
        game_input_sent=False, runtime_ready=False, real_client_accepted=False,
        cpu_budget_seconds=CPU_SECONDS, wall_budget_seconds=wall_seconds,
        code_sha256=code_pins, data_sha256=DATA_PINS,
        start_guide_file=spec.filename, start_guide_file_sha256=spec.file_sha256,
        prior_xy=dict(path=str(prior_path),sha256=PRIOR_PIN,
                      field='unverified_points[-1][:2]',floor_evidence_adopted=False))

    def save():
        record.update(seconds=time.monotonic()-began, cpu_seconds=time.process_time()-cpu_began)
        write_checkpoint(output, record)

    def check():
        if time.monotonic()-began > wall_seconds:
            raise TimeoutError('Offline Goblin approach wall budget exhausted')
        if time.process_time()-cpu_began > CPU_SECONDS:
            raise TimeoutError('Offline Goblin approach CPU budget exhausted')

    def stage(name):
        check(); record['stage']=name; save()
        print(json.dumps(dict(stage=name,seconds=record['seconds'],cpu_seconds=record['cpu_seconds'])),flush=True)

    def evidence(name):
        def progress(value):
            record[name]=value
            save()
            check()
        return progress

    def check_source_itinerary(prefix, start, guide):
        check()
        plan = plan_source_itinerary(prefix,start,guide,planner.source,planner.static,
            planner.bsp,planner.region_policy,check_context=check,
            max_seconds=max(.001,min(240.,wall_seconds-(time.monotonic()-began))))
        data=plan.record()
        if data['guide_entry']!=0 or tuple(data['start'])!=start or tuple(data['goal'])!=guide.goal:
            raise ValueError('Complete approach must check every original operation from the supplied start')
        check()
        return plan

    with output.open('x') as stream:
        json.dump(record,stream,allow_nan=False)
    save()
    checked_plan = None
    try:
        prior=json.loads(checked_bytes(prior_path,PRIOR_PIN))
        if prior.get('format')!='eql-copied-ground-selector-v1' or prior.get('zone')!='butcher':
            raise ValueError('Unexpected retained pre-line XY provenance')
        point=prior['unverified_points'][-1]
        goal=tuple(float(v) for v in point[:2])
        if len(goal)!=2 or not all(math.isfinite(v) for v in goal) or goal!=EXPECTED_GOAL:
            raise ValueError('Pinned retained pre-line XY changed')
        goblin=load_source_guide(root,'goblin-camp');start=goblin.goal
        if start!=EXPECTED_START:raise ValueError('Pinned Goblin destination changed')
        record['start_guide_sha256']=sha256(encoded(goblin.record())).hexdigest()
        assets=load_butcher_assets(root,native_planning=True);planner=assets.planner
        crossing=load_butcher_crossing(root,assets) if check_carried_crossing else None
        if (goblin.wld_sha256,goblin.static_inventory_sha256)!=(planner.source.wld_sha256,planner.static.inventory_sha256):
            raise ValueError('Goblin guide and current copied source differ')
        check()
        proposal=planner.source.propose_unique_diffuse_floor(start,body_height=6.)
        seed=dict(kind='synthetic_unique_source_floor',start=start,proposal=asdict(proposal),
            source_wld_sha256=planner.source.wld_sha256,data_sha256=DATA_PINS,
            radius=1.2,body_height=6.,synthetic_reference=True,
            retained_real_arrival=False,current_character_observation=False)
        seed_pin=sha256(encoded(seed)).hexdigest()
        chain=SourceFloorChain(inventory_sha256=planner.source.wld_sha256,
            seed_evidence_sha256=seed_pin,seed_ids=proposal.selected_ids,body_height=6.)
        cap=swept_square(start,start,1.2)
        floor=chain.advance(cap,planner.source.source_faces_for_footprint(cap))
        if not floor.candidate:raise ValueError('Synthetic Goblin cap: '+floor.reason)
        prefix_state=_chain_snapshot(chain)
        record.update(seed=seed,seed_sha256=seed_pin,initial_floor=asdict(floor),
            goal_intersections=[asdict(h) for h in planner.source.source_hits_at(goal)])
        stage('checking_synthetic_start_cap')
        cap_guide=SourceItineraryGuide('butcher',planner.source.wld_sha256,
            planner.static.inventory_sha256,seed_pin,1.2,6.,start,(SourceWalkHint(start,start),))
        cap_plan=check_source_itinerary(chain,start,cap_guide)
        record.update(start_cap_plan=cap_plan.record(),start_cap_sha256=cap_plan.sha256)
        transit_prefix,transit_start,retained_ops=chain,start,()
        if resume_path is not None:
            stage('rebuilding_checked_source_prefix')
            previous=json.loads(checked_bytes(resume_path,resume_pin))
            if (previous['format']!=record['format'] or previous['completed'] is not True
                    or previous['source_candidate'] is not False
                    or previous['data_sha256']!=DATA_PINS or previous['seed_sha256']!=seed_pin
                    or previous['seed']!=json.loads(encoded(seed))
                    or tuple(previous['start'])!=start or tuple(previous['goal'])!=goal
                    or previous['game_input_sent'] is not False):
                raise ValueError('Resume artifact differs from this synthetic source approach')
            old_guide=SourceItineraryGuide.from_record(previous['original_guide'])
            if (old_guide.operations[0].start!=start or old_guide.goal!=goal
                    or old_guide.radius!=1.2 or old_guide.body_height!=6.):
                raise ValueError('Prior guide endpoints or body changed')
            transit_prefix,transit_start,retained_ops=replay_walk_prefix(chain,old_guide,
                previous['repair_evidence'],planner,check_context=check)
            record['prefix_from']=dict(path=str(resume_path),sha256=resume_pin,
                rechecked_operations=len(retained_ops),end=transit_start,
                reached_proof_sha256=transit_prefix.previous.proof_sha256,
                new_source_seed=False,current_character_observation=False)
        stage('building_full_source_graph')
        graph=SourceTransitGraph(tuple(planner.source.sources),
            inventory_sha256=planner.source.wld_sha256,step_links=(),radius=1.2)
        record['graph']=dict(faces=graph.components.face_count,
            components=graph.components.component_count,
            directed_edges=sum(len(v) for v in graph.adjacent.values()),step_links=0)
        record['goal_components']=asdict(graph.components.goal(transit_prefix,goal))
        stage('proposing_source_xy')
        if connection_rounds:
            transit=filter_transit_connections(graph,transit_prefix,transit_start,goal,planner,
                check_context=check,progress=evidence('connection_evidence'),
                rounds=connection_rounds,start_via_edges=True,
                maximum_edge_queries=512,maximum_cell_queries=8192,
                maximum_seconds=min(300.,max(1.,wall_seconds-(time.monotonic()-began))))
        elif center_rounds:
            def center_progress(attempts, cache, excluded):
                record['center_filter']=dict(rounds=center_rounds,attempts=attempts,
                    caps=list(cache.values()),excluded_directed_edges=excluded,
                    current_floor_unchanged=True,whole_components_excluded=False,
                    input_authorized=False,physical_disconnection_proven=False)
                save();check()
            transit=filter_transit_centers(graph,transit_prefix,transit_start,goal,planner,
                rounds=center_rounds,check=check,progress=center_progress,start_via_edges=True)
        elif departure_rounds:
            transit=filter_transit_departures(graph,transit_prefix,transit_start,goal,planner,
                check_context=check,progress=evidence('departure_evidence'),
                rounds=departure_rounds,maximum_queries=512,maximum_seconds=30.)
        else:
            transit=graph.propose(transit_prefix,transit_start,goal,start_via_edges=True,
                max_expansions=32768,max_seconds=30.)
        if transit is None:
            raise ValueError('No bounded ordinary source-graph proposal; physical disconnection not proven')
        record['proposal']=asdict(transit)
        guide=join_source_suffix(retained_ops,transit.guide(
            static_inventory_sha256=planner.static.inventory_sha256,
            radius=1.2,body_height=6.,zone='butcher'))
        provenance=dict(proposal_sha256=sha256(encoded(record['proposal'])).hexdigest(),
            data_sha256=DATA_PINS,start_guide_sha256=record['start_guide_sha256'],
            prior_xy=record['prior_xy'],prefix_from=record.get('prefix_from'),
            center_filter_sha256=sha256(encoded(record['center_filter'])).hexdigest()
                if center_rounds else None,
            connection_filter_sha256=sha256(encoded(record['connection_evidence'])).hexdigest()
                if connection_rounds else None)
        guide=replace(guide,provenance_sha256=sha256(encoded(provenance)).hexdigest())
        record['provenance']=provenance
        record['proposal_length']=sum(edge.cost for edge in transit.edges)
        record['original_guide']=guide.record();record['guide']=guide.record()
        stage('checking_and_repairing_walks')
        guide,record['repair_evidence']=repair_walks(chain,guide,planner,
            check_context=check,progress=evidence('repair_evidence'),maximum_repairs=8,
            maximum_rejoin_distance=40.,detour_seconds=20.,maximum_expansions=128)
        record['guide']=guide.record()
        if _chain_snapshot(chain)!=prefix_state:raise ValueError('Synthetic start prefix changed')
        stage('checking_complete_source_itinerary')
        plan=check_source_itinerary(chain,start,guide)
        if _chain_snapshot(chain)!=prefix_state:raise ValueError('Complete approach changed initial prefix')
        data=plan.record();plan_path=output.with_suffix('.plan.json')
        with plan_path.open('xb') as stream:stream.write(plan.payload)
        checked_plan=dict(file=str(plan_path),sha256=plan.sha256,cells=len(data['cells']),
            goal=data['goal'],goal_floor_height=data['goal_floor_height'],
            goal_source_ids=data['goal_source_ids'],
            final_proof_sha256=data['final_proof_sha256'],
            initial_prefix_unchanged=True,
            requires_fresh_live_arrival=True,zone_crossing_included=False)
        record['checked_plan']=checked_plan
        if plan_sections:
            stage('planning_walking_sections')
            bounds=RouteMotionBounds('offline-section-probes','unmeasured-speed-hypothesis',
                .01,.15,.2,30.,.4,.01,2.,.1,guide.radius,guide.body_height)
            sections=plan_walk_sections(chain,guide,planner,bounds=bounds,check_context=check,
                maximum_length=1000.,minimum_length=600.,candidate_spacing=25.,
                maximum_seconds=min(240.,max(1.,wall_seconds-(time.monotonic()-began))),
                progress=evidence('sections_progress'))
            if _chain_snapshot(chain)!=prefix_state:
                raise ValueError('Section planning changed initial prefix')
            record['walk_sections']=sections
        if check_carried_crossing:
            stage('checking_carried_crossing_cells')
            carried=chain.fork()
            for cell in data['cells']:
                check()
                if cell['kind']!='walk':
                    raise ValueError('Butcher pre-line itinerary must contain ordinary walks only')
                carried=check_source_footprint(
                    carried,swept_square(tuple(cell['start']),tuple(cell['end']),guide.radius),
                    terrain=planner.source,static=planner.static,
                    bsp=planner.bsp,region_policy=planner.region_policy,
                ).branch
            if carried.previous.proof_sha256!=data['final_proof_sha256']:
                raise ValueError('Carried pre-line floor proof differs from checked source itinerary')
            preline_proof=carried.previous.proof_sha256
            c_goal=crossing.goal_xy
            count=max(1,math.ceil(math.dist(goal,c_goal)/2.))
            points=[goal]+[tuple(goal[k]+(c_goal[k]-goal[k])*i/count for k in (0,1))
                           for i in range(1,count)]+[c_goal]
            crossing_cells=[]
            crossing_end=None
            for a,b in ((goal,goal),*zip(points,points[1:])):
                check()
                carried,cell=check_source_crossing_cell(carried,a,b,radius=1.2,
                    terrain=planner.source,static=planner.static,bsp=planner.bsp,policy=crossing.policy)
                value=cell.record()
                crossing_cells.append(dict(sha256=cell.sha256,**value))
                if b!=goal and value['native']['possible_flags']==[0x80000000]:
                    carried,end_cap=check_source_crossing_cell(carried,b,b,radius=1.2,
                        terrain=planner.source,static=planner.static,bsp=planner.bsp,policy=crossing.policy)
                    cap_value=end_cap.record()
                    if cap_value['native']['possible_flags']!=[0x80000000]:
                        raise ValueError('Carried crossing final cap no longer lies wholly in the expected native label')
                    crossing_cells.append(dict(sha256=end_cap.sha256,**cap_value))
                    crossing_end=b
                    break
            if crossing_end is None:
                raise ValueError('Carried crossing did not reach a complete body cell in the expected transition')
            if _chain_snapshot(chain)!=prefix_state:
                raise ValueError('Carried crossing check changed initial prefix')
            record['carried_crossing']=dict(
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
            record['zone_transition_checked']=True
    except (ValueError,TimeoutError,OSError,KeyError,TypeError) as error:
        record.update(status='refused',reason=str(error))
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
    try:
        for name,pin in code_pins.items():checked_bytes(name,pin)
        for name,pin in DATA_PINS.items():checked_bytes(root/name,pin)
        checked_bytes(root/spec.filename,spec.file_sha256)
        checked_bytes(prior_path,PRIOR_PIN)
        if resume_path is not None:checked_bytes(resume_path,resume_pin)
        check()
        record['inputs_rehashed']=True
    except (ValueError,TimeoutError,OSError) as error:
        record.update(status='refused',reason=str(error),inputs_rehashed=False)
    if checked_plan is not None and record['status']!='refused':
        record.update(source_candidate=True,status='checked',stage='finished')
    record['completed']=True;save()
    print(json.dumps(dict(output=str(output),sha256=sha256(output.read_bytes()).hexdigest(),
        status=record['status'],source_candidate=record['source_candidate'],
        zone_transition_checked=record['zone_transition_checked'],
        sections=len(record.get('walk_sections',{}).get('sections',[])),
        crossing_cells=len(record.get('carried_crossing',{}).get('cells',[])),
        reason=record.get('reason'),seconds=record['seconds'],cpu_seconds=record['cpu_seconds'])),flush=True)
    return 0 if record['source_candidate'] else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--departure-rounds',type=int,default=8)
    parser.add_argument('--center-rounds',type=int,default=0,
        help='Use bounded fixed-center exclusions instead of departure retries')
    parser.add_argument('--connection-rounds',type=int,default=0,
        help='Use bounded per-edge connection exclusions verified on a carried floor fork')
    parser.add_argument('--check-carried-crossing',action='store_true',
        help='Continue the checked pre-line floor directly through check_source_crossing_cell')
    parser.add_argument('--plan-sections',action='store_true',
        help='Partition the checked ordinary approach into WalkingSections with measurement reserves')
    parser.add_argument('--wall-seconds',type=float,default=DEFAULT_WALL_SECONDS,
        help='Bounded wall-clock timeout in seconds (60..900)')
    parser.add_argument('--nice',type=int,default=19,
        help='Non-negative niceness increment (0..19)')
    parser.add_argument('--resume-source-from',type=Path)
    parser.add_argument('--prior-sha256')
    args=parser.parse_args()
    store=Path.home()/'.local/share/eql-automation/nav-candidates'
    if (args.output.exists() or args.output.is_symlink() or args.output.with_suffix('.plan.json').exists()
            or args.output.with_suffix('.plan.json').is_symlink() or args.output.parent.resolve()!=store.resolve()
            or not 0<=args.departure_rounds<=8 or not 0<=args.center_rounds<=16
            or not 0<=args.connection_rounds<=16
            or not 60.<=args.wall_seconds<=900.
            or not 0<=args.nice<=19
            or (args.center_rounds>0 and args.connection_rounds>0)
            or not (args.project/'tools/audit_butcher_camp_transit.py').is_file()):
        parser.error('Use a current project and new private nav-candidates output; choose at most one graph filter')
    if args.resume_source_from is not None or args.prior_sha256 is not None:
        if (args.resume_source_from is None or args.prior_sha256 is None
                or args.resume_source_from.parent.resolve()!=store.resolve()
                or args.resume_source_from.resolve()==args.output.resolve()):
            parser.error('Resume needs a separate pinned private approach diagnostic')
    os.umask(0o077)
    if args.nice:os.nice(args.nice)
    def expired(*_):raise TimeoutError('Offline Goblin approach CPU/wall budget exhausted')
    signal.signal(signal.SIGALRM,expired);signal.signal(signal.SIGXCPU,expired)
    resource.setrlimit(resource.RLIMIT_CPU,(int(CPU_SECONDS)+5,int(CPU_SECONDS)+10))
    signal.setitimer(signal.ITIMER_REAL,args.wall_seconds)
    return run(args.project.resolve(),args.output,departure_rounds=args.departure_rounds,
        center_rounds=args.center_rounds,connection_rounds=args.connection_rounds,
        check_carried_crossing=args.check_carried_crossing,plan_sections=args.plan_sections,
        wall_seconds=args.wall_seconds,
        resume_path=args.resume_source_from,resume_pin=args.prior_sha256)


if __name__=='__main__':raise SystemExit(main())
