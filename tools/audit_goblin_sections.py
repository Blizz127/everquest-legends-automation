#!/usr/bin/env python3
"""Find copied-geometry stopping hints; never advance a real journey or input."""
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
import argparse
import json
import os
import resource
import signal
import sys
import time

SOURCE_SCRIPT=Path(__file__).resolve()
PROJECT=SOURCE_SCRIPT.parents[1]
STORE=Path.home()/'.local/share/eql-automation'
sys.path[:0]=[str(PROJECT),str(STORE/'owner-assist/0.39.4')]

from eql_automation.butcher_assets import DATA_NAME,DATA_PINS,load_butcher_assets
from eql_automation.native_region_policy import encoded
from eql_automation.owner_route_assets import checked_bytes
from eql_automation.route_geometry import RouteMotionBounds
from eql_automation.source_destinations import load_source_guide
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_walk_sections import plan_walk_sections
from audit_butcher_camp_transit import write_checkpoint

PRIOR='butcher-newbie-goblin-transit-20261115-final-source-alienware.json'
PRIOR_PIN='3c396a3944c4aba7ad05def3c939d45d74c24f87ccd7409a2d048cb4c85be22e'


def run(output,speed_upper):
    began=time.monotonic();cpu=time.process_time()
    pins={str(p.relative_to(PROJECT)):sha256(p.read_bytes()).hexdigest()
        for p in (SOURCE_SCRIPT,SOURCE_SCRIPT.with_name('audit_butcher_camp_transit.py'),
                  *sorted((PROJECT/'eql_automation').glob('*.py')))}
    root=STORE/'owner-route-data'/DATA_NAME
    record=dict(format='eql-offline-goblin-sections-audit-v1',code_sha256=pins,data_sha256=DATA_PINS,
        prior_sha256=PRIOR_PIN,completed=False,source_candidate=False,synthetic_start=True,
        current_character_observation=False,input_authorized=False,game_input_sent=False,
        real_client_accepted=False,runtime_continuation_enabled=False)
    def check():
        if time.monotonic()-began>240 or time.process_time()-cpu>120:
            raise TimeoutError('Offline section CPU/wall budget exhausted')
    def save():
        record.update(seconds=time.monotonic()-began,cpu_seconds=time.process_time()-cpu)
        write_checkpoint(output,record)
    save()
    try:
        prior=json.loads(checked_bytes(STORE/'nav-candidates'/PRIOR,PRIOR_PIN))
        guide=load_source_guide(root,'goblin-camp')
        if (prior['completed'] is not True or prior['source_candidate'] is not True
                or prior['game_input_sent'] is not False or prior['data_sha256']!=DATA_PINS
                or encoded(prior['guide'])!=encoded(guide.record())
                or sha256(encoded(prior['seed'])).hexdigest()!=prior['seed_sha256']):
            raise ValueError('Pinned complete Goblin guide and original seed required')
        planner=load_butcher_assets(root,native_planning=True).planner
        start=guide.operations[0].start
        floor=planner.source.propose_unique_diffuse_floor(start,body_height=6.)
        if encoded(asdict(floor))!=encoded(prior['seed']['proposal']):
            raise ValueError('Original start source-floor hypothesis differs')
        prefix=SourceFloorChain(inventory_sha256=guide.wld_sha256,
            seed_evidence_sha256=prior['seed_sha256'],seed_ids=floor.selected_ids,body_height=6.)
        cap=swept_square(start,start,guide.radius)
        if not prefix.advance(cap,planner.source.source_faces_for_footprint(cap)).candidate:
            raise ValueError('Initial section floor is unavailable')
        bounds=RouteMotionBounds('offline-section-probes','unmeasured-speed-hypothesis',
            .01,.15,.2,speed_upper,.4,.01,2.,.1,guide.radius,guide.body_height)
        record.update(bounds_hypothesis=asdict(bounds),bounds_verified=False,
            initial_seed_sha256=prior['seed_sha256'])
        def progress(value):
            record['progress']=value;save()
            if value['candidate_queries']%10==0:
                print(json.dumps({k:value[k] for k in ('checked_operations','sections',
                    'candidate_queries','checked_reserves')}),flush=True)
        result=plan_walk_sections(prefix,guide,planner,bounds=bounds,check_context=check,
            maximum_length=1000.,minimum_length=600.,candidate_spacing=25.,
            maximum_seconds=200.,progress=progress)
        record.update(result=result,source_candidate=True)
    except (ValueError,TimeoutError) as error:
        record['refusal']=str(error)
    signal.setitimer(signal.ITIMER_REAL,0)
    for n,pin in pins.items():checked_bytes(PROJECT/n,pin)
    for n,pin in DATA_PINS.items():checked_bytes(root/n,pin)
    record['completed']=True;save()
    print(json.dumps(dict(output=str(output),sha256=sha256(output.read_bytes()).hexdigest(),
        source_candidate=record['source_candidate'],refusal=record.get('refusal'),
        sections=len(record.get('result',{}).get('sections',[])),seconds=record['seconds'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--speed-upper',type=float,default=30.,help='Unverified planning hypothesis, not a measured client speed')
    args=parser.parse_args()
    if (args.output.exists() or args.output.is_symlink()
            or args.output.parent.resolve()!=(STORE/'nav-candidates').resolve()
            or not 1<=args.speed_upper<=150):
        parser.error('New private output and finite speed hypothesis required')
    os.umask(0o077);os.nice(19)
    def expired(*_):raise TimeoutError('Offline section CPU/wall budget exhausted')
    signal.signal(signal.SIGALRM,expired);signal.signal(signal.SIGXCPU,expired)
    resource.setrlimit(resource.RLIMIT_CPU,(125,130));signal.setitimer(signal.ITIMER_REAL,240)
    run(args.output,args.speed_upper)
