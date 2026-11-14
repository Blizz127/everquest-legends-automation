#!/usr/bin/env python3
"""Extract XY/step hints from retained proofs; replan from a supplied test start.

The approved private store holds every output. No retained floor chain, label
height or acceptance flag becomes current state. This CLI's start is synthetic;
the library separately accepts an actual caller-owned source-floor prefix.
"""
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys
import time

PROJECT = Path(__file__).resolve().parents[1]
STORE = Path.home()/'.local/share/eql-automation'
sys.path[:0] = [str(PROJECT), str(STORE/'owner-assist/0.39.4')]

from eql_automation.source_itinerary import (SourceItineraryGuide, SourceWalkHint,
    SourceStepHint, plan_source_itinerary)
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.native_region_policy import encoded

RETAINED = {
    'crushbone-auto-source-detours-0.41.99.json': '94116bdf777333bb875e537e450818950a4683b0ffd4965b002a0607689002c8',
    'crushbone-source-steps-and-components-0.42.0.json': '2f4c9a42e293ce4ffcf86d2604f6f88dca31ed48fd843de3c92339aa9ce16f49',
    'crushbone-auto-source-steps-ranked-0.42.1.json': 'fcc23ce2a7f91a2642c7c482307d62d293d8fd33c31b4c15db2154e94fd90a7e',
}


def extract(assets):
    retained=[]
    for name,pin in RETAINED.items():
        path=STORE/'nav-candidates'/name
        raw=path.read_bytes()
        if path.is_symlink() or sha256(raw).hexdigest()!=pin:
            raise ValueError('Retained recipe provenance changed: '+name)
        retained.append(json.loads(raw))
    parent,prior,auto=retained
    operations=[]
    radius=parent['hypothetical_body_radius']
    def cell(a,b,expected):
        a,b=tuple(a),tuple(b)
        if swept_square(a,b,radius)!=tuple(tuple(p) for p in expected['footprint']):
            raise ValueError('Extracted guide does not reproduce the retained footprint')
        operations.append(SourceWalkHint(a,b))
    def detour(cells):
        for row in cells:cell(row['start'],row['end'],row)
    def transfer(row,ids=None):
        e=row['evidence']
        operations.append(SourceStepHint(tuple(e['start']),tuple(e['end']),
            tuple(tuple(k) for k in (ids or (e['landing_endpoint']['selected_ids'][0],))),
            e['max_step_height'],e['max_lift'],e['lift_clearance']))
    index=0
    while index<len(parent['cells']):
        row=parent['cells'][index]
        if 'detour' in row:
            hint=parent['detours'][row['detour']]
            if index!=hint['first_cell_index']:raise ValueError('Retained detour index differs')
            points=hint['points']; pairs=[(points[0],points[0])]
            for a,b in zip(points,points[1:]):pairs.extend(((a,b),(b,b)))
            if len(pairs)!=hint['cell_count']:raise ValueError('Retained detour count differs')
            for (a,b),expected in zip(pairs,parent['cells'][index:index+len(pairs)]):cell(a,b,expected)
            index+=len(pairs);continue
        segment=row['segment']
        if segment<0:a=b=parent['waypoints'][0]
        else:
            a,b=parent['waypoints'][segment:segment+2]
            count=max(1,math.ceil(math.dist(a,b)/parent['maximum_cell_length']))
            j=row['division']
            start=tuple(a[k]+(b[k]-a[k])*j/count for k in range(2))
            end=tuple(a[k]+(b[k]-a[k])*(j+1)/count for k in range(2))
            a,b=start,end
        cell(a,b,row);index+=1
    for approach,step in zip(prior['approaches'],prior['steps']):
        detour(approach['cells']);transfer(step)
    for suffix in prior['suffix']:
        if not suffix['candidate']:break
        detour(suffix['cells'])
    for accepted in auto['accepted']:
        proposal=auto['attempts'][accepted['attempt']]['proposals'][accepted['proposal']]
        detour(proposal['approach']['cells'])
        transfer(proposal['transition'],proposal['proposal']['landing_seed_ids'])
    detour(auto['final_connection']['cells'])
    labels=[a for a in assets.annotations if a.name == 'Slave Mines']
    if len(labels)!=1:raise ValueError('Need one exact copied Slave Mines annotation')
    annotation=labels[0]
    goal=tuple(-v for v in annotation.map_xyz[:2])
    provenance=sha256(encoded(dict(retained=RETAINED,annotation=asdict(annotation),
        map_xy_to_package='-x,-y',label_z_used=False))).hexdigest()
    guide=SourceItineraryGuide('crushbone',parent['source_wld_sha256'],
        parent['static_inventory_sha256'],provenance,radius,parent['hypothetical_body_height'],
        goal,tuple(operations))
    guide.validate()
    return guide


def run(args):
    from eql_automation.crushbone_assets import load_crushbone_assets, DATA_NAME
    code_pins={str(p.relative_to(PROJECT)):sha256(p.read_bytes()).hexdigest()
        for p in (Path(__file__), *sorted((PROJECT/'eql_automation').glob('*.py')))}
    assets=load_crushbone_assets(STORE/'owner-route-data'/DATA_NAME,native_planning=True)
    guide=extract(assets); planner=assets.planner
    point=(args.x,args.y)
    proposal=planner.source.propose_unique_diffuse_floor(point,body_height=guide.body_height)
    seed=encoded(dict(kind='explicit_synthetic_start',point=point,proposal=asdict(proposal)))
    chain=SourceFloorChain(inventory_sha256=planner.source.wld_sha256,
        seed_evidence_sha256=sha256(seed).hexdigest(),seed_ids=proposal.selected_ids,
        body_height=guide.body_height)
    footprint=swept_square(point,point,guide.radius)
    floor=chain.advance(footprint,planner.source.source_faces_for_footprint(footprint))
    if not floor.candidate:raise ValueError('Synthetic current floor refused: '+floor.reason)
    started=time.monotonic()
    result=plan_source_itinerary(chain,point,guide,planner.source,planner.static,planner.bsp,
        planner.region_policy,check_context=planner._check_views)
    data=dict(format='eql-crushbone-source-itinerary-probe-v1',synthetic_current_position=True,
        game_input_sent=False,real_client_accepted=False,guide=guide.record(),
        plan_sha256=result.sha256,plan=result.record(),seconds=time.monotonic()-started,
        code_pins=code_pins)
    if any(sha256((PROJECT/name).read_bytes()).hexdigest()!=pin for name,pin in code_pins.items()):
        raise ValueError('Implementation changed during the copied itinerary run')
    with args.output.open('x') as out:json.dump(data,out,indent=2);out.write('\n')
    rows=data['plan']['cells']
    print(json.dumps(dict(output=str(args.output),sha256=sha256(args.output.read_bytes()).hexdigest(),
        operations=len(guide.operations),walks=sum(r['kind']=='walk' for r in rows),
        steps=sum(r['kind']=='step' for r in rows),goal=data['plan']['goal'],
        goal_floor_height=data['plan']['goal_floor_height'],seconds=data['seconds'])))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--x',type=float,required=True)
    parser.add_argument('--y',type=float,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if (not all(math.isfinite(v) for v in (args.x,args.y)) or args.output.exists()
            or args.output.is_symlink()
            or args.output.parent.resolve()!=(STORE/'nav-candidates').resolve()):
        parser.error('Finite explicit test XY and a new approved nav-candidates output required')
    os.umask(0o077);os.nice(10);run(args)
