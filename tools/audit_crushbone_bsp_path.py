#!/usr/bin/env python3
"""Replay the complete retained source path and audit clipped BSP body volumes.

All current cells and all seven step transfers are checked. Completion of the
audit is distinct from passage; unknowns, hazards and budgets remain refusals.
No client or input is used.
"""
from collections import Counter
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
AUTO = STORE/'nav-candidates/crushbone-auto-source-steps-ranked-0.42.1.json'


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
    from eql_automation.source_step import check_source_step
    from eql_automation.source_step_bsp import check_source_step_bsp
    from eql_automation.bsp_floor_guard import check_source_body_bsp
    from eql_automation.bsp_volume import BspVolumeView

    pins = dict(PINS)
    pins.update({PARENT:'94116bdf777333bb875e537e450818950a4683b0ffd4965b002a0607689002c8',
                 STEPS:'2f4c9a42e293ce4ffcf86d2604f6f88dca31ed48fd843de3c92339aa9ce16f49',
                 AUTO:'fcc23ce2a7f91a2642c7c482307d62d293d8fd33c31b4c15db2154e94fd90a7e'})
    for p in [Path(__file__),Path(__file__).with_name('audit_crushbone_source_crossings.py'),
              *sorted((PROJECT/'eql_automation').glob('*.py')),*sorted((HELPER/'eqnav').glob('*.py'))]:
        pins.setdefault(p,sha256(p.read_bytes()).hexdigest())
    def verify():
        for p,pin in pins.items():
            if p.is_symlink() or not p.is_file() or sha256(p.read_bytes()).hexdigest()!=pin:
                raise ValueError('Source pin changed: '+str(p))
    verify(); began = time.monotonic()
    parent,previous,auto = (json.loads(p.read_text()) for p in (PARENT,STEPS,AUTO))
    assert auto['source_suffix_candidate'] and auto['completed']
    source = PortalPrecisionView(GroundSweepView.load(MESH,zone='crushbone'),MESH,ARCHIVE,zone='crushbone')
    archive = PFSArchive(ARCHIVE); terrain = WLDInventory(archive.read_member('crushbone.wld'))
    static = StaticSourceView.from_wld(WLDInventory(archive.read_member('objects.wld')),
        (WLDInventory(PFSArchive(OBJECTS).read_member('crushbone_obj.wld')),),
        terrain_fragment_max=max(f.index for f in terrain.fragments),transform=zonegeom.place_vertices,
        transform_sha256=pins[HELPER/'eqnav/zonegeom.py'])
    assert source.wld_sha256==parent['source_wld_sha256'] and static.inventory_sha256==parent['static_inventory_sha256']
    bsp = BspVolumeView.from_wld(terrain)
    seed = parent['source_seed']; seed_ids = tuple(sorted(tuple(k) for _,k in seed['candidates']))
    chain = SourceFloorChain(inventory_sha256=source.wld_sha256,
        seed_evidence_sha256=sha256(json.dumps(seed,sort_keys=True).encode()).hexdigest(),
        seed_ids=(seed_ids[0],),body_height=parent['hypothetical_body_height'])
    record = dict(format='eql-crushbone-clipped-bsp-path-v1',offline_only=True,completed=False,
        route_accepted=False,real_client_accepted=False,game_input_sent=False,
        conditional_kinematic_hypothesis=True,client_step_capability_verified=False,
        source_wld_sha256=source.wld_sha256,static_inventory_sha256=static.inventory_sha256,
        bsp_inventory_sha256=bsp.inventory_sha256,cells=[],steps=[],
        current_path_bsp_candidate=False,pins={str(p):h for p,h in pins.items()})
    def save():
        record['seconds'] = time.monotonic()-began
        record['cell_count'] = len(record['cells']); record['step_count'] = len(record['steps'])
        for kind in ('unclipped','clipped'):
            record[kind+'_cell_refusals'] = dict(sorted(Counter(c[kind]['reason'] for c in record['cells']
                                                               if not c[kind]['candidate']).items()))
        record['step_refusals'] = dict(sorted(Counter(s['bsp']['reason'] for s in record['steps']
                                                    if not s['bsp']['candidate']).items()))
        temporary = output.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(record,indent=2)+'\n'); temporary.replace(output)
    def budget():
        if time.monotonic()-began > 300: raise TimeoutError('Complete BSP audit work budget exceeded')
    def replay(cells,label):
        for i,expected in enumerate(cells):
            budget(); footprint = tuple(tuple(p) for p in expected['footprint'])
            sources = source.source_faces_for_footprint(footprint)
            step = chain.advance(footprint,sources)
            assert step.candidate and step.proof_sha256==expected['terrain']['proof_sha256']
            assert check_source_static_floor(step,footprint,sources,static).candidate
            record['cells'].append(dict(origin=label,origin_index=i,floor_proof_sha256=step.proof_sha256,
                footprint=footprint,selected_ids=step.selected_ids,
                unclipped=asdict(check_source_body_bsp(step,footprint,sources,bsp)),
                clipped=asdict(check_source_body_bsp(step,footprint,sources,bsp,clip_branches=True))))
            if len(record['cells'])%200==0:
                save(); print(json.dumps(dict(cells=len(record['cells']),seconds=record['seconds'])),flush=True)
    def replay_step(transition,label,landing_seed_ids=None):
        nonlocal chain
        budget(); e = transition['evidence']
        checked,continued = check_source_step(chain,tuple(e['start']),tuple(e['end']),source,static,
            landing_seed_ids=landing_seed_ids or (tuple(e['landing_endpoint']['selected_ids'][0]),),
            **{k:e[k] for k in ('radius','max_step_height','max_lift','lift_clearance')})
        assert checked.candidate and checked.transition_sha256==transition['transition_sha256']
        classification = check_source_step_bsp(checked,source,static,bsp)
        record['steps'].append(dict(origin=label,transition_sha256=checked.transition_sha256,
            bsp=asdict(classification)))
        chain = continued
    save()
    try:
        replay(parent['cells'],'original_prefix')
        for i,(approach,transition) in enumerate(zip(previous['approaches'],previous['steps'])):
            replay(approach['cells'],f'prior_step_{i}_approach')
            replay_step(transition,f'prior_step_{i}')
        for suffix in previous['suffix']:
            if not suffix['candidate']: break
            replay(suffix['cells'],f"prior_guide_{suffix['guide_waypoint']}")
        assert chain.previous.proof_sha256==auto['prefix_final_proof_sha256']
        for i,accepted in enumerate(auto['accepted']):
            proposal = auto['attempts'][accepted['attempt']]['proposals'][accepted['proposal']]
            replay(proposal['approach']['cells'],f'generated_step_{i}_approach')
            replay_step(proposal['transition'],f'generated_step_{i}',
                        tuple(tuple(k) for k in proposal['proposal']['landing_seed_ids']))
        replay(auto['final_connection']['cells'],'final_connection')
        assert chain.previous.proof_sha256==auto['final_proof_sha256']
        assert len(record['cells'])==1046 and len(record['steps'])==7
        passed = all(c['clipped']['candidate'] for c in record['cells']) and all(s['bsp']['candidate'] for s in record['steps'])
        record.update(completed=True,current_path_bsp_candidate=passed,
            status='checked' if passed else 'checked_with_refusals',final_proof_sha256=chain.previous.proof_sha256)
    except (ValueError,TimeoutError) as error:
        record.update(status='incomplete',error=str(error))
    verify(); save()
    print(json.dumps({k:record[k] for k in ('status','completed','cell_count','step_count','seconds',
        'unclipped_cell_refusals','clipped_cell_refusals','step_refusals','current_path_bsp_candidate')}))
    print(json.dumps(dict(output=str(output),sha256=sha256(output.read_bytes()).hexdigest())))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True); args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink() or args.output.parent.resolve()!=(STORE/'nav-candidates').resolve():
        parser.error('Use a new output directly in approved nav-candidates store')
    os.umask(0o077); os.nice(10); run(args.output)
