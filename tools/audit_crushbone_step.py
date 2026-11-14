#!/usr/bin/env python3
"""Replay the copied Crushbone prefix, check its riser and try the suffix.

This uses a conditional lift/transfer/settle hypothesis, not client input or
accepted step capability. The original route's BSP refusals remain in force.
"""
from dataclasses import asdict
from hashlib import sha256
import argparse
import json
import math
import os
from pathlib import Path
import sys
import time

from audit_crushbone_source_crossings import PROJECT,STORE,HELPER,MESH,ARCHIVE,OBJECTS,PINS

PARENT=STORE/'nav-candidates/crushbone-auto-source-detours-0.41.99.json'


def run(output):
    sys.path[:0]=[str(PROJECT),str(HELPER)]
    from eqnav import zonegeom
    from eql_automation.ground_sweep_view import GroundSweepView
    from eql_automation.portal_precision_view import PortalPrecisionView
    from eql_automation.pfs_archive import PFSArchive
    from eql_automation.wld_inventory import WLDInventory
    from eql_automation.static_source_view import StaticSourceView
    from eql_automation.source_floor_chain import SourceFloorChain
    from eql_automation.static_floor_guard import check_source_static_floor
    from eql_automation.source_detour import find_source_detour
    from eql_automation.source_step import check_source_step
    from eql_automation.source_floor_components import SourceFloorComponents
    pins=dict(PINS)
    pins[PARENT]='94116bdf777333bb875e537e450818950a4683b0ffd4965b002a0607689002c8'
    for p in [Path(__file__),Path(__file__).with_name('audit_crushbone_source_crossings.py'),
              *sorted((PROJECT/'eql_automation').glob('*.py')),*sorted((HELPER/'eqnav').glob('*.py'))]:
        pins.setdefault(p,sha256(p.read_bytes()).hexdigest())
    def verify():
        for p,pin in pins.items():
            if p.is_symlink() or not p.is_file() or sha256(p.read_bytes()).hexdigest()!=pin:
                raise ValueError('Source pin changed: '+str(p))
    verify();began=time.monotonic()
    parent=json.loads(PARENT.read_text())
    source=PortalPrecisionView(GroundSweepView.load(MESH,zone='crushbone'),MESH,ARCHIVE,zone='crushbone')
    archive=PFSArchive(ARCHIVE);terrain=WLDInventory(archive.read_member('crushbone.wld'))
    static=StaticSourceView.from_wld(WLDInventory(archive.read_member('objects.wld')),
        (WLDInventory(PFSArchive(OBJECTS).read_member('crushbone_obj.wld')),),
        terrain_fragment_max=max(f.index for f in terrain.fragments),transform=zonegeom.place_vertices,
        transform_sha256=pins[HELPER/'eqnav/zonegeom.py'])
    assert source.wld_sha256==parent['source_wld_sha256'] and static.inventory_sha256==parent['static_inventory_sha256']
    components=SourceFloorComponents(tuple(source.sources),inventory_sha256=source.wld_sha256)
    seed=parent['source_seed'];seed_ids=tuple(sorted(tuple(k) for _,k in seed['candidates']))
    chain=SourceFloorChain(inventory_sha256=source.wld_sha256,
        seed_evidence_sha256=sha256(json.dumps(seed,sort_keys=True).encode()).hexdigest(),
        seed_ids=(seed_ids[0],),body_height=parent['hypothetical_body_height'])
    record=dict(format='eql-crushbone-step-v2',offline_only=True,status='checking',completed=False,
        real_client_accepted=False,route_accepted=False,game_input_sent=False,
        conditional_kinematic_hypothesis=True,client_step_capability_verified=False,bsp_classified=False,
        parent_bsp_refusals=len(parent['bsp_refusals']),pins={str(p):h for p,h in pins.items()},
        prefix_replayed_count=0,approaches=[],steps=[],suffix=[],skipped_guide=[],
        continuous_floor_faces=components.face_count,continuous_floor_components=components.component_count,
        remaining_source_occupancy_candidate=False)
    def save():
        record['seconds']=time.monotonic()-began
        temporary=output.with_suffix('.json.tmp');temporary.write_text(json.dumps(record,indent=2)+'\n');temporary.replace(output)
    def budget():
        if time.monotonic()-began>180:raise TimeoutError('Step diagnostic work budget exceeded')
    save()
    try:
        for expected in parent['cells']:
            budget();footprint=tuple(tuple(p) for p in expected['footprint'])
            sources=source.source_faces_for_footprint(footprint)
            step=chain.advance(footprint,sources)
            assert step.candidate and step.proof_sha256==expected['terrain']['proof_sha256']
            assert check_source_static_floor(step,footprint,sources,static).candidate
            record['prefix_replayed_count']+=1
            if record['prefix_replayed_count']%250==0:
                save();print(json.dumps(dict(prefix_replayed=record['prefix_replayed_count'])),flush=True)
        record['prefix_final_proof_sha256']=chain.previous.proof_sha256
        last=parent['cells'][-1];index=last['segment']
        a,b=parent['waypoints'][index:index+2];count=max(1,math.ceil(math.dist(a,b)/2.))
        position=tuple(a[k]+(b[k]-a[k])*(last['division']+1)/count for k in range(2))
        for start,end,landing_seed,lift_bound in (
                ((443.5,228.5),(446.1,228.5),(1538,2),1.),
                ((461.5,228.5),(464.1,228.5),(2485,15),2.5)):
            approach,at_step=find_source_detour(chain,position,start,source,static,radius=1.2,
                                                max_expansions=96,max_seconds=8.)
            record['approaches'].append(asdict(approach))
            if not approach.candidate:raise ValueError('Step approach: '+approach.reason)
            budget()
            transition,landing=check_source_step(at_step,start,end,source,static,landing_seed_ids=(landing_seed,),
                radius=1.2,max_step_height=.5,max_lift=lift_bound,lift_clearance=.125)
            record['steps'].append(asdict(transition));save()
            print(json.dumps(dict(step=len(record['steps']),candidate=transition.candidate,reason=transition.reason)),flush=True)
            if not transition.candidate:raise ValueError('Step transfer: '+transition.reason)
            chain=landing;position=end
        for target_index in range(index+1,len(parent['waypoints'])):
            budget();target=tuple(parent['waypoints'][target_index])
            connectivity=components.goal(chain,target)
            if not connectivity.possible:
                record['skipped_guide'].append(dict(guide_waypoint=target_index,**asdict(connectivity)))
                continue
            detour,continued=find_source_detour(chain,position,target,source,static,radius=1.2,
                                               max_expansions=128,max_seconds=10.)
            item=asdict(detour);item['guide_waypoint']=target_index;record['suffix'].append(item)
            if not detour.candidate:raise ValueError('Suffix: '+detour.reason)
            chain=continued;position=target
            if target_index%5==0:save()
        if position!=tuple(parent['waypoints'][-1]):
            raise ValueError('Suffix requires another source-floor transition; no physical disconnection claimed')
        record.update(remaining_source_occupancy_candidate=True,final_proof_sha256=chain.previous.proof_sha256,
                      final_chain_index=chain.previous.index,status='checked',completed=True)
    except (ValueError,TimeoutError) as error:
        record.update(status='refused',reason=str(error),completed=True)
    verify();save()
    print(json.dumps(dict(output=str(output),sha256=sha256(output.read_bytes()).hexdigest(),
        prefix_cells=record['prefix_replayed_count'],steps=[s['candidate'] for s in record['steps']],
        remaining_source_occupancy_candidate=record['remaining_source_occupancy_candidate'],reason=record.get('reason'))))
    return record


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() or args.output.is_symlink() or args.output.parent.resolve()!=(STORE/'nav-candidates').resolve():
        parser.error('Use a new output directly in approved nav-candidates store')
    os.umask(0o077);os.nice(10);run(args.output)
