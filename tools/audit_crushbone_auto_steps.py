#!/usr/bin/env python3
"""Replay the retained prefix, then discover/check source steps automatically.

Only copied data is used. Height/lift/body bounds are explicit hypotheses.
BSP refusals and all real-client acceptance gates remain in force.
"""
from dataclasses import asdict
from hashlib import sha256
import argparse
import json
import os
from pathlib import Path
import sys
import time

from audit_crushbone_source_crossings import PROJECT,STORE,HELPER,MESH,ARCHIVE,OBJECTS,PINS

PARENT = STORE/'nav-candidates/crushbone-auto-source-detours-0.41.99.json'
STEPS = STORE/'nav-candidates/crushbone-source-steps-and-components-0.42.0.json'


def run(output):
    sys.path[:0] = [str(PROJECT),str(HELPER)]
    from eqnav import zonegeom
    from eql_automation.ground_sweep_view import GroundSweepView
    from eql_automation.portal_precision_view import PortalPrecisionView
    from eql_automation.pfs_archive import PFSArchive
    from eql_automation.wld_inventory import WLDInventory
    from eql_automation.static_source_view import StaticSourceView
    from eql_automation.source_floor_chain import SourceFloorChain
    from eql_automation.static_floor_guard import check_source_static_floor
    from eql_automation.source_detour import find_source_detour, swept_square
    from eql_automation.source_step import check_source_step
    from eql_automation.source_floor_components import SourceFloorComponents
    from eql_automation.source_step_links import discover_step_links, propose_step_caps, candidate_step_path

    pins = dict(PINS)
    pins[PARENT] = '94116bdf777333bb875e537e450818950a4683b0ffd4965b002a0607689002c8'
    pins[STEPS] = '2f4c9a42e293ce4ffcf86d2604f6f88dca31ed48fd843de3c92339aa9ce16f49'
    for p in [Path(__file__), *sorted((PROJECT/'eql_automation').glob('*.py')),
              *sorted((HELPER/'eqnav').glob('*.py'))]:
        pins.setdefault(p,sha256(p.read_bytes()).hexdigest())
    def verify():
        for p,pin in pins.items():
            if p.is_symlink() or not p.is_file() or sha256(p.read_bytes()).hexdigest()!=pin:
                raise ValueError('Source pin changed: '+str(p))
    verify(); began = time.monotonic()
    parent, previous = (json.loads(p.read_text()) for p in (PARENT,STEPS))
    source = PortalPrecisionView(GroundSweepView.load(MESH,zone='crushbone'),MESH,ARCHIVE,zone='crushbone')
    archive = PFSArchive(ARCHIVE); terrain = WLDInventory(archive.read_member('crushbone.wld'))
    static = StaticSourceView.from_wld(WLDInventory(archive.read_member('objects.wld')),
        (WLDInventory(PFSArchive(OBJECTS).read_member('crushbone_obj.wld')),),
        terrain_fragment_max=max(f.index for f in terrain.fragments),transform=zonegeom.place_vertices,
        transform_sha256=pins[HELPER/'eqnav/zonegeom.py'])
    assert source.wld_sha256==parent['source_wld_sha256'] and static.inventory_sha256==parent['static_inventory_sha256']
    components = SourceFloorComponents(tuple(source.sources),inventory_sha256=source.wld_sha256)
    seed = parent['source_seed']; seed_ids = tuple(sorted(tuple(k) for _,k in seed['candidates']))
    chain = SourceFloorChain(inventory_sha256=source.wld_sha256,
        seed_evidence_sha256=sha256(json.dumps(seed,sort_keys=True).encode()).hexdigest(),
        seed_ids=(seed_ids[0],),body_height=parent['hypothetical_body_height'])
    record = dict(format='eql-crushbone-auto-steps-v1',offline_only=True,completed=False,
        route_accepted=False,real_client_accepted=False,game_input_sent=False,bsp_classified=False,
        conditional_kinematic_hypothesis=True,client_step_capability_verified=False,
        max_step_height=2.,max_lift=4.,radius=1.2,body_height=6.,
        parent_bsp_refusals=len(parent['bsp_refusals']),replayed_cells=0,replayed_steps=0,
        attempts=[],accepted=[],pins={str(p):h for p,h in pins.items()})
    def save():
        record['seconds'] = time.monotonic()-began
        temporary = output.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(record,indent=2)+'\n'); temporary.replace(output)
    def budget():
        if time.monotonic()-began > 180:
            raise TimeoutError('Automatic step diagnostic work budget exceeded')
    def replay(cells):
        for expected in cells:
            budget(); footprint = tuple(tuple(p) for p in expected['footprint'])
            sources = source.source_faces_for_footprint(footprint)
            step = chain.advance(footprint,sources)
            assert step.candidate and step.proof_sha256==expected['terrain']['proof_sha256']
            assert check_source_static_floor(step,footprint,sources,static).candidate
            record['replayed_cells'] += 1
    save()
    try:
        replay(parent['cells'])
        for approach,transition in zip(previous['approaches'],previous['steps']):
            replay(approach['cells']); e = transition['evidence']
            checked, chain = check_source_step(chain,tuple(e['start']),tuple(e['end']),source,static,
                landing_seed_ids=(tuple(e['landing_endpoint']['selected_ids'][0]),),
                **{k:e[k] for k in ('radius','max_step_height','max_lift','lift_clearance')})
            assert checked.candidate and checked.transition_sha256==transition['transition_sha256']
            record['replayed_steps'] += 1
        for suffix in previous['suffix']:
            if not suffix['candidate']: break
            replay(suffix['cells']); position = tuple(suffix['points'][-1])
        record['prefix_final_proof_sha256'] = chain.previous.proof_sha256
        record['start'] = position; goal = tuple(parent['waypoints'][-1]); record['goal'] = goal
        links = discover_step_links(tuple(source.sources),inventory_sha256=source.wld_sha256,
                                    max_step_height=2.,min_width=2.404)
        record['discovered_directed_links'] = len(links)
        goal_components = components.goal(chain,goal).goal_components
        record['goal_components'] = goal_components
        unavailable = set()
        for iteration in range(16):
            budget(); here = components.goal(chain,position).prefix_component
            route = candidate_step_path((v for v in links if v not in unavailable),here,position,
                                         goal_components,goal,radius=1.2)
            if route is None:
                raise ValueError('No remaining discovery path within this bounded proposal set')
            if not route:
                final, continued = find_source_detour(chain,position,goal,source,static,
                    radius=1.2,max_expansions=128,max_seconds=10.)
                record['final_connection'] = asdict(final)
                if not final.candidate: raise ValueError('Final connector: '+final.reason)
                chain = continued; position = goal
                record.update(source_suffix_candidate=True,final_proof_sha256=chain.previous.proof_sha256)
                break
            link,preferred = route[0]
            attempt = dict(link=asdict(link),proposals=[]); record['attempts'].append(attempt)
            proposals = (preferred, *(p for p in propose_step_caps(link,radius=1.2) if p!=preferred))
            accepted = False
            for proposal in proposals:
                budget(); item = dict(proposal=asdict(proposal)); attempt['proposals'].append(item)
                # Cheap independent geometry screening, never grafted onto the
                # accepted prefix. The actual approach and transfer are below.
                cap_chain = SourceFloorChain(inventory_sha256=source.wld_sha256,
                    seed_evidence_sha256='0'*64,seed_ids=(link.from_face,),body_height=6.)
                footprint = swept_square(proposal.start,proposal.start,1.2)
                cap_sources = source.source_faces_for_footprint(footprint)
                cap = cap_chain.advance(footprint,cap_sources)
                item['departure_cap'] = asdict(cap)
                if not cap.candidate: continue
                screened, _ = check_source_step(cap_chain,proposal.start,proposal.end,source,static,
                    landing_seed_ids=proposal.landing_seed_ids,radius=1.2,max_step_height=2.,max_lift=4.)
                item['screen'] = asdict(screened)
                if not screened.candidate: continue
                approach, at_step = find_source_detour(chain,position,proposal.start,source,static,
                    radius=1.2,max_expansions=128,max_seconds=8.)
                item['approach'] = asdict(approach)
                if not approach.candidate: continue
                transition, continued = check_source_step(at_step,proposal.start,proposal.end,source,static,
                    landing_seed_ids=proposal.landing_seed_ids,radius=1.2,max_step_height=2.,max_lift=4.)
                item['transition'] = asdict(transition)
                if not transition.candidate: continue
                chain, position = continued, proposal.end; accepted = True
                record['accepted'].append(dict(attempt=len(record['attempts'])-1,
                    proposal=len(attempt['proposals'])-1,position=position,
                    transition_sha256=transition.transition_sha256))
                print(json.dumps(dict(accepted=len(record['accepted']),position=position)),flush=True)
                break
            if not accepted: unavailable.add(link)
            save()
        if position != goal:
            raise ValueError('Bounded automatic step proposals exhausted before final goal')
        record.update(status='checked',completed=True)
    except (ValueError,TimeoutError) as error:
        record.update(status='refused',completed=True,reason=str(error))
    verify(); save()
    print(json.dumps(dict(output=str(output),sha256=sha256(output.read_bytes()).hexdigest(),
        accepted=len(record['accepted']),reason=record.get('reason'),seconds=record['seconds'])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True); args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink() or args.output.parent.resolve()!=(STORE/'nav-candidates').resolve():
        parser.error('Use a new output directly in approved nav-candidates store')
    os.umask(0o077); os.nice(10); run(args.output)
