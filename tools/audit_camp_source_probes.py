#!/usr/bin/env python3
"""Check unknown-heading areas using copied source floors, never live input.

Slave Mines uses a fully replayed historical source/static prefix. North Wall
uses its unique source point as an explicit synthetic floor hypothesis. Every
probe checks full source terrain, static objects, body BSP and native regions.
"""
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys
import time

PROJECT=Path(__file__).resolve().parents[1]
STORE=Path.home()/'.local/share/eql-automation'
sys.path[:0]=[str(PROJECT),str(STORE/'owner-assist/0.39.4')]

from audit_crushbone_camp_transit import PARENT,PARENT_PIN,replay_parent
from eql_automation.crushbone_assets import DATA_NAME,DATA_PINS,load_crushbone_assets
from eql_automation.native_region_policy import encoded
from eql_automation.owner_route_assets import checked_bytes
from eql_automation.route_geometry import RouteMotionBounds
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_probe_geometry import check_source_probe


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--maximum-holds',type=float,nargs='+',required=True)
    parser.add_argument('--speed-bound',type=float,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if (args.output.exists() or args.output.is_symlink()
            or args.output.parent.resolve()!=(STORE/'nav-candidates').resolve()
            or not 1<=len(args.maximum_holds)<=4):
        parser.error('Use a new output in the private nav-candidates store and at most four holds')
    bounds=[]
    for hold in args.maximum_holds:
        b=RouteMotionBounds('offline-source-probe','synthetic-no-calibration',
            .01,min(.05,hold),hold,args.speed_bound,.1,.05,180.,.1,1.2,6.)
        b.validate_values(calibration_record_id='synthetic-no-calibration',maximum_step_seconds=.2)
        bounds.append(b)
    code_pins={str(p.relative_to(PROJECT)):sha256(p.read_bytes()).hexdigest()
        for p in (Path(__file__).resolve(),Path(__file__).with_name('audit_crushbone_camp_transit.py').resolve(),
                  *sorted((PROJECT/'eql_automation').glob('*.py')))}
    # This retained full-route report is 19 MB; the small route-data loader
    # intentionally caps ordinary inputs at 16 MB. Bound this audit separately.
    if PARENT.is_symlink() or not PARENT.is_file() or PARENT.stat().st_size>32*1024*1024:
        raise ValueError('Missing or oversized retained parent report')
    parent_bytes=PARENT.read_bytes()
    if sha256(parent_bytes).hexdigest()!=PARENT_PIN:raise ValueError('Retained parent hash differs')
    parent=json.loads(parent_bytes)
    assets=load_crushbone_assets(STORE/'owner-route-data'/DATA_NAME,native_planning=True)
    p=assets.planner;began=time.monotonic()
    def check():
        if time.monotonic()-began>600:raise TimeoutError('Source probe audit budget exhausted')
    chain,goal,replay=replay_parent(parent,p.source,p.static,check)
    print(json.dumps(dict(stage='parent_replayed',**replay)),flush=True)
    starts=[('slave-mines',chain,goal,dict(kind='replayed_historical_prefix',**replay))]
    goal=(-95.,-78.)
    proposal=p.source.propose_unique_diffuse_floor(goal,body_height=6.)
    north=SourceFloorChain(inventory_sha256=p.source.wld_sha256,
        seed_evidence_sha256=sha256(encoded(asdict(proposal))).hexdigest(),
        seed_ids=proposal.selected_ids,body_height=6.)
    cap=swept_square(goal,goal,1.2)
    initial=north.advance(cap,p.source.source_faces_for_footprint(cap))
    if not initial.candidate:raise ValueError('Synthetic North Wall seed: '+initial.reason)
    starts.append(('north-wall',north,goal,dict(kind='synthetic_unique_source_floor',proposal=asdict(proposal))))
    rows=[]
    for name,prefix,xy,provenance in starts:
        reference=(*xy,prefix.floor_at(xy)[0])
        for b in bounds:
            row=dict(destination_id=name,reference=reference,bounds=asdict(b),prefix=provenance,
                accepted_geometry=False)
            start=time.monotonic()
            try:
                result=check_source_probe(prefix,reference,probe_kind='forward',bounds=b,
                    terrain=p.source,static=p.static,bsp=p.bsp,region_policy=p.region_policy,
                    check_context=check,maximum_seconds=30.)
                row.update(accepted_geometry=True,evidence=result.record(),evidence_sha256=result.sha256)
            except ValueError as error:row['refusal']=str(error)
            row['seconds']=time.monotonic()-start;rows.append(row)
            print(json.dumps({k:v for k,v in row.items() if k not in ('evidence','prefix','bounds')},
                allow_nan=False),flush=True)
    for name,pin in DATA_PINS.items():checked_bytes(STORE/'owner-route-data'/DATA_NAME/name,pin)
    for name,pin in code_pins.items():checked_bytes(PROJECT/name,pin)
    if PARENT.is_symlink() or sha256(PARENT.read_bytes()).hexdigest()!=PARENT_PIN:
        raise ValueError('Retained parent changed during replay')
    record=dict(format='eql-offline-camp-source-probes-v1',rows=rows,
        code_sha256=code_pins,data_sha256=DATA_PINS,parent_sha256=PARENT_PIN,
        seconds=time.monotonic()-began,synthetic_reference=True,current_character_position=False,
        game_input_sent=False,input_authorized=False,real_client_accepted=False)
    raw=encoded(record)
    with args.output.open('xb') as out:out.write(raw)
    args.output.chmod(0o600)
    print(json.dumps(dict(output=str(args.output),sha256=sha256(raw).hexdigest(),
                         accepted=sum(r['accepted_geometry'] for r in rows),total=len(rows))),flush=True)


if __name__=='__main__':main()
