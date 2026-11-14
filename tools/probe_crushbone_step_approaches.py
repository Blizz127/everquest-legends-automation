#!/usr/bin/env python3
"""Probe retained Crushbone steps with explicit synthetic motion hypotheses."""
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys
import time

PROJECT=Path(__file__).resolve().parents[1]
STORE=Path.home()/'.local/share/eql-automation'
sys.path[:0]=[str(PROJECT),str(STORE/'owner-assist/0.39.4')]
from build_crushbone_itinerary import extract
from eql_automation.crushbone_assets import load_crushbone_assets,DATA_NAME
from eql_automation.ground_sweep import motion_footprint
from eql_automation.native_region_policy import encoded
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_itinerary import SourceStepHint
from eql_automation.source_step_approach import plan_source_step_approach,source_step_supports


def run(output):
    assets=load_crushbone_assets(STORE/'owner-route-data'/DATA_NAME,native_planning=True)
    p=assets.planner;guide=extract(assets)
    pins={str(path.relative_to(PROJECT)):sha256(path.read_bytes()).hexdigest()
        for path in (Path(__file__),PROJECT/'tools/build_crushbone_itinerary.py',
            *sorted((PROJECT/'eql_automation').glob('*.py')))}
    rows=[];began=time.monotonic()
    for index,hint in enumerate(guide.operations):
        if type(hint) is not SourceStepHint:continue
        direction=tuple((hint.end[k]-hint.start[k])/math.dist(hint.start,hint.end) for k in (0,1))
        heading=math.degrees(math.atan2(direction[0],direction[1]))%360
        for setback in (.25,1.):
            start=tuple(hint.start[k]-setback*direction[k] for k in (0,1))
            reach=math.dist(start,hint.end)+.5
            end=tuple(start[k]+reach*direction[k] for k in (0,1))
            radius=(guide.radius+.02+2*reach*math.sin(math.radians(1.)/2))/math.cos(math.pi/16)
            row=dict(operation=index,synthetic_start=start,setback=setback,nominal_end=end,
                hypothetical_reach=reach,hypothetical_checked_radius=radius)
            try:
                proposal=p.source.propose_unique_diffuse_floor(start,body_height=guide.body_height)
                row['synthetic_floor_proposal']=asdict(proposal)
                seed=sha256(encoded(dict(start=start,proposal=asdict(proposal),synthetic=True))).hexdigest()
                chain=SourceFloorChain(inventory_sha256=p.source.wld_sha256,
                    seed_evidence_sha256=seed,seed_ids=proposal.selected_ids,body_height=guide.body_height)
                cap=swept_square(start,start,guide.radius)
                checked=chain.advance(cap,p.source.source_faces_for_footprint(cap))
                if not checked.candidate:raise ValueError('Synthetic start cap: '+checked.reason)
                footprint=motion_footprint(start,heading,reach,position_error=.01,
                    heading_error_degrees=1.,post_release_drift=.01,extra_radius=guide.radius)
                plan=plan_source_step_approach(chain,start,hint,p.source,p.static,p.bsp,p.region_policy,
                    footprint=footprint,nominal_end=end,body_radius=guide.radius,checked_radius=radius,
                    check_context=p._check_views)
                supports=source_step_supports(plan,start,p.source,p.static,check_context=p._check_views)
                row.update(candidate=True,plan_sha256=plan.sha256,plan=plan.record(),
                    start_support_candidates=[asdict(s) for s in supports])
            except ValueError as error:
                row.update(candidate=False,reason=str(error))
            rows.append(row)
    if any(sha256((PROJECT/name).read_bytes()).hexdigest()!=pin for name,pin in pins.items()):
        raise ValueError('Implementation changed during copied step probe')
    result=dict(format='eql-copied-step-approaches-v1',code_pins=pins,guide_sha256=sha256(encoded(guide.record())).hexdigest(),
        cases=rows,seconds=time.monotonic()-began,synthetic_positions=True,measured_motion=False,
        owner_observations=False,game_input_sent=False,real_client_accepted=False)
    with output.open('x') as out:json.dump(result,out,indent=2);out.write('\n')
    print(json.dumps(dict(output=str(output),sha256=sha256(output.read_bytes()).hexdigest(),
        cases=len(rows),candidates=sum(r['candidate'] for r in rows),seconds=result['seconds'],
        outcomes=[{k:r[k] for k in ('operation','setback','candidate','reason') if k in r} for r in rows])))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if (args.output.exists() or args.output.is_symlink()
            or args.output.parent.resolve()!=(STORE/'nav-candidates').resolve()):
        parser.error('Need a new file under the approved nav-candidates store')
    os.umask(0o077);os.nice(10);run(args.output)
