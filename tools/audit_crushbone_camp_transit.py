#!/usr/bin/env python3
"""Propose later-camp transit from an exactly replayed retained offline prefix.

This uses private copied client data. It never opens an input device or treats
the retained synthetic start as a current character observation. Proposals are
rebuilt by the complete itinerary checker before being called candidates.
"""
from dataclasses import asdict
from hashlib import sha256
import argparse
import json
import os
from pathlib import Path
import sys
import time

PROJECT=Path(__file__).resolve().parents[1]
STORE=Path.home()/'.local/share/eql-automation'
PARENT=STORE/'nav-candidates/crushbone-source-itinerary-0.42.28-final.json'
PARENT_PIN='09c4cf3d6e69245249f8df9ef66a8f1914c7fc5038bb3dd8b5b1c01dee98bb28'
DESTINATIONS={'trainer':(119.,-212.),'north-wall':(-95.,-78.),'throne':(106.,154.)}


def replay_parent(parent,terrain,static,check):
    """Recover lineage by redoing every source/static check, never reseeding goal Z."""
    from eql_automation.source_floor_chain import SourceFloorChain
    from eql_automation.source_detour import swept_square
    from eql_automation.static_floor_guard import check_source_static_floor
    from eql_automation.source_step import check_source_step
    from eql_automation.source_itinerary import SourceItineraryGuide,SourceStepHint
    plan=parent['plan'];guide=SourceItineraryGuide.from_record(parent['guide'])
    def identity(value):
        parts=value.split(':')
        if len(parts)!=4 or parts[0]!='wld' or parts[2]!='face':raise ValueError('Unknown retained source ID')
        return (int(parts[1]),int(parts[3]))
    chain=SourceFloorChain(inventory_sha256=terrain.wld_sha256,
        seed_evidence_sha256=plan['initial_seed_sha256'],
        seed_ids=tuple(identity(v) for v in plan['start_source_ids']),body_height=guide.body_height)
    start=tuple(plan['start']);footprint=swept_square(start,start,guide.radius)
    first=chain.advance(footprint,terrain.source_faces_for_footprint(footprint))
    if (not first.candidate or first.proof_sha256!=plan['initial_proof_sha256']
            or chain.index!=plan['initial_chain_index']):raise ValueError('Retained initial prefix differs')
    steps=0
    for index,cell in enumerate(plan['cells']):
        check()
        if cell['kind']=='walk':
            footprint=tuple(tuple(v) for v in cell['footprint'])
            sources=terrain.source_faces_for_footprint(footprint)
            floor=chain.advance(footprint,sources)
            if not floor.candidate or floor.proof_sha256!=cell['terrain']['proof_sha256']:
                raise ValueError('Retained walk differs at '+str(index))
            if not check_source_static_floor(floor,footprint,sources,static).candidate:
                raise ValueError('Retained static check refused at '+str(index))
        elif cell['kind']=='step':
            op=guide.operations[cell['origin']]
            if (type(op) is not SourceStepHint or op.start!=tuple(cell['start'])
                    or op.end!=tuple(cell['end'])):raise ValueError('Retained step guide differs')
            transfer,continued=check_source_step(chain,op.start,op.end,terrain,static,
                landing_seed_ids=op.landing_seed_ids,radius=guide.radius,
                max_step_height=op.max_step_height,max_lift=op.max_lift,lift_clearance=op.lift_clearance)
            expected=cell['transfer']
            if (not transfer.candidate or transfer.transition_sha256!=expected['transition_sha256']
                    or transfer.landing_proof_sha256!=expected['landing_proof_sha256']):
                raise ValueError('Retained transfer differs at '+str(index))
            chain=continued;steps+=1
        else:raise ValueError('Unknown retained cell')
    if chain.previous.proof_sha256!=plan['final_proof_sha256']:
        raise ValueError('Retained endpoint lineage differs')
    return chain,tuple(plan['goal']),dict(cells=len(plan['cells']),steps=steps,
        final_proof_sha256=chain.previous.proof_sha256,
        source_static_replayed=True,parent_regions_replayed=False,
        synthetic_offline_start=True,current_character_observation=False)


def run(output,destination,strategy,compact):
    sys.path[:0]=[str(PROJECT),str(STORE/'owner-assist/0.39.4')]
    from eql_automation.crushbone_assets import load_crushbone_assets,DATA_NAME
    from eql_automation.source_step_links import discover_step_links
    from eql_automation.source_transit_graph import SourceTransitGraph
    from eql_automation.source_itinerary import plan_source_itinerary,SourceItineraryPlan
    from eql_automation.source_reverse_guide import reverse_source_plan
    from eql_automation.source_guide_compaction import compact_source_guide
    from eql_automation.native_region_policy import encoded
    import math
    pins={p:sha256(p.read_bytes()).hexdigest() for p in
        [Path(__file__),*sorted((PROJECT/'eql_automation').glob('*.py'))]}
    pins[PARENT]=PARENT_PIN
    def verify():
        for path,pin in pins.items():
            if path.is_symlink() or sha256(path.read_bytes()).hexdigest()!=pin:
                raise ValueError('Copied evidence or code changed: '+str(path))
    verify();began=time.monotonic()
    def check():
        if time.monotonic()-began>600:raise TimeoutError('Camp transit audit budget exhausted')
    record=dict(format='eql-offline-camp-transit-v1',destination=destination,
        goal=DESTINATIONS[destination],strategy=strategy,compact=compact,
        offline_audit_budget_seconds=600,maximum_itinerary_check_seconds=240,
        parent_sha256=PARENT_PIN,status='running',
        completed=False,source_candidate=False,game_input_sent=False,
        input_authorized=False,real_client_accepted=False,
        code_pins={str(p):v for p,v in pins.items()})
    def save():
        record['seconds']=time.monotonic()-began
        temporary=output.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(record,indent=2)+'\n');temporary.replace(output)
    save()
    try:
        assets=load_crushbone_assets(STORE/'owner-route-data'/DATA_NAME,native_planning=True)
        planner=assets.planner;terrain=planner.source;static=planner.static
        parent=json.loads(PARENT.read_bytes())
        chain,start,replayed=replay_parent(parent,terrain,static,check)
        record['replay']=replayed;record['start']=start;save()
        print(json.dumps(dict(stage='prefix_replayed',**replayed)),flush=True)
        if strategy=='graph':
            links=discover_step_links(tuple(terrain.sources),inventory_sha256=terrain.wld_sha256,
                max_step_height=2.,min_width=2.404)
            graph=SourceTransitGraph(tuple(terrain.sources),inventory_sha256=terrain.wld_sha256,
                step_links=links,radius=1.2,max_step_height=2.,max_lift=4.)
            proposal=graph.propose(chain,start,DESTINATIONS[destination])
            record['step_links']=len(links)
            if proposal is None:raise ValueError('No transit proposal under current source/step model')
            record['proposal']=asdict(proposal)
            guide=proposal.guide(static_inventory_sha256=static.inventory_sha256,radius=1.2,body_height=6.)
        else:
            retained=SourceItineraryPlan(encoded(parent['plan']),parent['plan_sha256'])
            index=min(range(len(parent['plan']['cells'])),
                key=lambda i:math.dist(parent['plan']['cells'][i]['start'],DESTINATIONS[destination]))
            guide=reverse_source_plan(retained,first_cell=index,goal=DESTINATIONS[destination])
            record['reverse_first_cell']=index
        record['uncompacted_operations']=len(guide.operations)
        if compact:
            guide=compact_source_guide(guide)
            record['compaction']=dict(maximum_length=8.,xy_rounding_tolerance=1e-8,
                geometry_equivalence_claimed=False,requires_full_rebuild=True)
        record['guide']=guide.record();save()
        print(json.dumps(dict(stage='proposal',strategy=strategy,operations=len(guide.operations))),flush=True)
        plan=plan_source_itinerary(chain,start,guide,terrain,static,planner.bsp,planner.region_policy,
            check_context=check,max_seconds=max(.001,min(240.,600-(time.monotonic()-began))))
        record.update(plan=plan.record(),plan_sha256=plan.sha256,source_candidate=True,status='checked')
    except (ValueError,TimeoutError) as error:
        record.update(status='refused',reason=str(error))
    verify();record['completed']=True;save()
    print(json.dumps(dict(output=str(output),sha256=sha256(output.read_bytes()).hexdigest(),
        status=record['status'],reason=record.get('reason'),seconds=record['seconds'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--destination',choices=DESTINATIONS,required=True)
    parser.add_argument('--strategy',choices=('graph','reverse'),default='graph')
    parser.add_argument('--compact',action='store_true',help='Merge straight hints before the complete geometry check')
    args=parser.parse_args()
    if (args.output.exists() or args.output.is_symlink()
            or args.output.parent.resolve()!=(STORE/'nav-candidates').resolve()):
        parser.error('Use a new output directly in the approved nav-candidates store')
    os.umask(0o077);os.nice(19);run(args.output,args.destination,args.strategy,args.compact)
