#!/usr/bin/env python3
"""Rebuild a finite source route to the Throne stair landing, without combat."""
from dataclasses import asdict,replace
from hashlib import sha256
from pathlib import Path
import argparse
import json
import os
import resource
import signal
import sys
import time

PROJECT=Path(__file__).resolve().parents[1]
STORE=Path.home()/'.local/share/eql-automation'
sys.path[:0]=[str(PROJECT),str(STORE/'owner-assist/0.39.4')]
from eql_automation.crushbone_assets import DATA_NAME,DATA_PINS,load_crushbone_assets
from eql_automation.native_region_policy import encoded
from eql_automation.owner_route_assets import checked_bytes
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_itinerary import SourceItineraryGuide,plan_source_itinerary
from eql_automation.source_stair_hint import SourceStairHint


def proposal(record,artifact_sha256):
    if (record.get('completed') is not True or record.get('data_sha256')!=DATA_PINS
            or record.get('stair_vertical_model')!='bounded_source_contacts'
            or record.get('game_input_sent') is not False):
        raise ValueError('Pinned complete copied contact artifact required')
    approach=SourceItineraryGuide.from_record(record['approach_guide'])
    flight=record['stair_plan'];topology=flight['flight']['topology']
    if (flight['vertical_model']!='bounded_source_contacts' or flight['flight']['candidate'] is not True
            or tuple(flight['start'])!=approach.goal or approach.operations[-1].end!=approach.goal):
        raise ValueError('Contact staircase does not continue the retained approach')
    hint=SourceStairHint(tuple(flight['start']),tuple(flight['end']),
        tuple(tuple(tuple(k) for k in group) for group in topology['tread_ids']),
        record['stair_checked_radius'],topology['max_individual_rise'],4.,'bounded_source_contacts')
    provenance=sha256(encoded(dict(kind='finite_stair_landing_stop',artifact_sha256=artifact_sha256,
        approach_sha256=record['approach_sha256'],stair_sha256=record['stair_sha256'],
        goal=hint.end,arrival_mode='stop',contact_exit_included=False))).hexdigest()
    guide=replace(approach,goal=hint.end,provenance_sha256=provenance,
        operations=(*approach.operations,hint))
    guide.validate();return guide


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact',type=Path,required=True)
    parser.add_argument('--artifact-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args()
    if (any(p.exists() or p.is_symlink() for p in (args.output,args.evidence))
            or args.output.parent.resolve()!=(STORE/'owner-route-data'/DATA_NAME).resolve()
            or args.evidence.parent.resolve()!=(STORE/'nav-candidates').resolve()):
        parser.error('New private guide and evidence paths required')
    os.umask(0o077);os.nice(19);resource.setrlimit(resource.RLIMIT_CPU,(40,45))
    began=time.monotonic()
    def check(*_):
        if time.monotonic()-began>180:raise TimeoutError('Stair landing build expired')
    def timeout(*_):raise TimeoutError('Stair landing build expired')
    signal.signal(signal.SIGALRM,timeout);signal.signal(signal.SIGXCPU,timeout);signal.alarm(180)
    if args.artifact.stat().st_size>8*1024*1024:raise ValueError('Contact artifact exceeds input bound')
    record=json.loads(checked_bytes(args.artifact,args.artifact_sha256))
    guide=proposal(record,args.artifact_sha256)
    assets=load_crushbone_assets(STORE/'owner-route-data'/DATA_NAME,native_planning=True);p=assets.planner
    start=tuple(record['approach_plan']['start'])
    seed=p.source.propose_unique_diffuse_floor(start,body_height=guide.body_height)
    if sorted(f'wld:{fragment}:face:{face}' for fragment,face in seed.selected_ids)!=sorted(record['approach_plan']['start_source_ids']):
        raise ValueError('Synthetic copied departure source identity changed')
    prefix=SourceFloorChain(inventory_sha256=p.source.wld_sha256,
        seed_evidence_sha256=args.artifact_sha256,
        seed_ids=seed.selected_ids,body_height=guide.body_height)
    cap=swept_square(start,start,guide.radius)
    if not prefix.advance(cap,p.source.source_faces_for_footprint(cap)).candidate:
        raise ValueError('Synthetic copied departure cap refused')
    plan=plan_source_itinerary(prefix,start,guide,p.source,p.static,p.bsp,p.region_policy,
        check_context=check,max_seconds=150.)
    check()
    evidence=dict(format='eql-finite-stair-landing-build-v1',artifact_sha256=args.artifact_sha256,
        code_sha256={str(path.relative_to(PROJECT)):sha256(path.read_bytes()).hexdigest()
            for path in (Path(__file__).resolve(),*sorted((PROJECT/'eql_automation').glob('*.py')))},
        plan=plan.record(),plan_sha256=plan.sha256,synthetic_seed=asdict(seed),synthetic_start=True,arrival_mode='stop',
        contact_exit_included=False,game_input_sent=False,real_client_accepted=False,
        seconds=time.monotonic()-began)
    guide_record=dict(format='eql-copied-source-guide-v1',client_data_pins=DATA_PINS,
        guide=guide.record(),guide_sha256=sha256(encoded(guide.record())).hexdigest(),
        evidence_sha256=sha256(encoded(evidence)).hexdigest(),arrival_mode='stop',
        safe_camp_verified=False,input_authorized=False,real_client_accepted=False)
    for path,data in ((args.evidence,evidence),(args.output,guide_record)):
        with path.open('x') as f:json.dump(data,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(guide=str(args.output),guide_file_sha256=sha256(args.output.read_bytes()).hexdigest(),
        provenance_sha256=guide.provenance_sha256,goal=guide.goal,operations=len(guide.operations),
        evidence_file_sha256=sha256(args.evidence.read_bytes()).hexdigest(),seconds=evidence['seconds'],
        real_client_accepted=False)))


if __name__=='__main__':main()
