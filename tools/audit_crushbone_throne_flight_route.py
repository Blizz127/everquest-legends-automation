#!/usr/bin/env python3
"""Compose a checked North Wall approach, stair flight and Throne exit offline."""
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
from eql_automation.ground_sweep import area,clip
from eql_automation.native_region_policy import encoded
from eql_automation.owner_route_assets import checked_bytes
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain,rational
from eql_automation.source_floor_components import SourceFloorComponents
from eql_automation.source_guide_compaction import compact_source_guide
from eql_automation.source_itinerary import SourceItineraryGuide,SourceWalkHint,plan_source_itinerary
from tools.audit_crushbone_camp_transit import replay_parent
from tools.source_stair_flight import stair_body_footprint
from tools.source_stair_plan import plan_stair_flight
from tools.source_walk_shortcuts import shortcut_walks
from tools.source_contact_envelope import declare_contact_hypothesis,audit_contact_walks


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prior',type=Path,required=True)
    parser.add_argument('--prior-sha256',required=True)
    parser.add_argument('--first-step',type=int,required=True)
    parser.add_argument('--last-step',type=int,required=True)
    parser.add_argument('--output',type=Path,required=True)
    exit_policy=parser.add_mutually_exclusive_group()
    exit_policy.add_argument('--exit-detour-range',nargs=2,type=int,metavar=('FIRST','LAST'))
    exit_policy.add_argument('--exit-contact-face',nargs=2,type=int,action='append',metavar=('FRAGMENT','FACE'))
    args=parser.parse_args()
    if (args.output.exists() or args.output.is_symlink()
            or args.output.with_suffix('.json.tmp').exists()
            or args.output.parent.resolve()!=(STORE/'nav-candidates').resolve()
            or not 0<=args.first_step<args.last_step<32):
        parser.error('New private output and explicit bounded stair sequence required')
    os.umask(0o077);os.nice(19);resource.setrlimit(resource.RLIMIT_CPU,(40,45))
    began=time.monotonic();cpu=time.process_time()
    def timeout(*_):raise TimeoutError('Composed stair route audit budget exhausted')
    signal.signal(signal.SIGALRM,timeout);signal.signal(signal.SIGXCPU,timeout);signal.alarm(180)
    code=[Path(__file__).resolve(),*(PROJECT/'tools'/name for name in (
        'audit_crushbone_camp_transit.py','source_stair_topology.py','source_stair_flight.py',
        'source_stair_plan.py','source_walk_shortcuts.py','source_contact_envelope.py')),*sorted((PROJECT/'eql_automation').glob('*.py'))]
    pins={str(p.relative_to(PROJECT)):sha256(p.read_bytes()).hexdigest() for p in code}
    record=dict(format='eql-offline-composed-stair-route-v1',code_sha256=pins,data_sha256=DATA_PINS,
        prior_sha256=args.prior_sha256,completed=False,stage='loading',source_candidate=False,
        executable_itinerary=False,input_authorized=False,real_client_accepted=False,
        game_input_sent=False,synthetic_start=True,current_floor_committed=False)
    def check():
        if time.monotonic()-began>180 or time.process_time()-cpu>40:timeout()
    def save():
        record.update(seconds=time.monotonic()-began,cpu_seconds=time.process_time()-cpu)
        temporary=args.output.with_suffix('.json.tmp')
        with temporary.open('x') as f:json.dump(record,f,indent=2,allow_nan=False)
        temporary.replace(args.output)
    def stage(value):
        check();record['stage']=value;save()
        print(json.dumps(dict(stage=value,seconds=record['seconds'],cpu_seconds=record['cpu_seconds'])),flush=True)
    try:
        prior=json.loads(checked_bytes(args.prior,args.prior_sha256))
        if prior['data_sha256']!=DATA_PINS:raise ValueError('Prior client data differs')
        guide=SourceItineraryGuide.from_record(prior['guide'])
        steps=[edge for edge in prior['proposal']['edges'] if edge['step']]
        flight_edges=steps[args.first_step:args.last_step+1]
        if len(flight_edges)!=args.last_step-args.first_step+1:raise ValueError('Unknown stair range')
        flight_start=tuple(flight_edges[0]['step']['start']);flight_end=tuple(flight_edges[-1]['step']['end'])
        prefix_ops=[]
        for row in prior['smoothing']['accepted_proposals']:
            if row['kind']=='walk':prefix_ops.append(SourceWalkHint(tuple(row['start']),tuple(row['end'])))
            elif row['kind']=='unchanged_step':prefix_ops.append(guide.operations[row['origin']])
            else:raise ValueError('Unknown retained shortcut proposal')
        if not prefix_ops or prefix_ops[-1].end!=flight_start:
            raise ValueError('Retained accepted approach does not end at first stair')
        indices=[i for i,op in enumerate(guide.operations)
                 if op.start==tuple(flight_edges[-1]['step']['start']) and op.end==flight_end]
        if len(indices)!=1:raise ValueError('No unique original final stair operation')
        suffix_ops=guide.operations[indices[0]+1:]
        if not suffix_ops or suffix_ops[0].start!=flight_end:raise ValueError('No contiguous stair exit')
        assets=load_crushbone_assets(STORE/'owner-route-data'/DATA_NAME,native_planning=True);p=assets.planner
        start=tuple(prior['start']);seed=p.source.propose_unique_diffuse_floor(start,body_height=6.)
        if encoded(asdict(seed))!=encoded(prior['seed']['proposal']):raise ValueError('Synthetic initial seed changed')
        prefix=SourceFloorChain(inventory_sha256=p.source.wld_sha256,seed_evidence_sha256=prior['seed_sha256'],
            seed_ids=seed.selected_ids,body_height=6.)
        cap=swept_square(start,start,guide.radius)
        if not prefix.advance(cap,p.source.source_faces_for_footprint(cap)).candidate:raise ValueError('Initial cap refused')
        approach=replace(guide,goal=flight_start,operations=tuple(prefix_ops))
        stage('checking_complete_approach')
        first_plan=plan_source_itinerary(prefix,start,approach,p.source,p.static,p.bsp,p.region_policy,
            check_context=check,max_seconds=90.)
        record.update(approach_guide=approach.record(),approach_plan=first_plan.record(),
                      approach_sha256=first_plan.sha256)
        before,goal,replay=replay_parent(dict(plan=first_plan.record(),guide=approach.record()),p.source,p.static,check)
        if goal!=flight_start:raise ValueError('Replayed approach differs from stair start')
        record['approach_replay']=replay
        components=SourceFloorComponents(tuple(p.source.sources),inventory_sha256=p.source.wld_sha256)
        selected=[components.components[tuple(flight_edges[0]['origin'])]]
        for edge in flight_edges:
            if components.components[tuple(edge['origin'])]!=selected[-1]:raise ValueError('Stairs skip a component')
            selected.append(components.components[tuple(edge['destination'])])
        boundary=stair_body_footprint(flight_start,flight_end,guide.radius)
        groups=tuple(tuple(key for key,(poly,_,_) in components.faces.items()
            if components.components[key]==component and area(clip(boundary,rational(poly)))>0)
            for component in selected)
        stage('rebuilding_complete_flight')
        def progress(value):record['flight_progress']=value
        flight,after=plan_stair_flight(before,flight_start,flight_end,groups,p.source,p.static,p.bsp,p.region_policy,
            radius=guide.radius,check_context=check,progress=progress)
        record.pop('flight_progress',None)
        record.update(stair_plan=flight.record(),stair_sha256=flight.sha256,
            planned_landing_proof_sha256=after.previous.proof_sha256)
        suffix=replace(guide,operations=suffix_ops)
        if args.exit_contact_face:
            stage('checking_conditional_contact_exit')
            hypothesis=declare_contact_hypothesis(p.static,tuple(tuple(k) for k in args.exit_contact_face))
            def progress(value):record['contact_exit']=value;save()
            contact=audit_contact_walks(after,suffix.operations,guide.goal,p.source,p.static,p.bsp,
                p.region_policy,hypothesis,radius=guide.radius,check_context=check,progress=progress)
            record.update(contact_exit=contact,contact_hypothesis=hypothesis.record(),
                combined_conditional_envelopes_clear=contact['exit_envelopes_clear'],
                goal=guide.goal,stage='finished_conditional_contact_envelopes',
                contact_semantics_verified=False,transition_kinematics_verified=False)
            # Deliberately leave source_candidate false: an envelope under a
            # contact assumption is not an accepted walking/step itinerary.
        else:
            stage('shortcutting_stair_exit')
            def progress(value):record['exit_shortcuts']=value;save()
            suffix,evidence=shortcut_walks(after,suffix,p.source,p.static,check_context=check,progress=progress,
                detour_rejoin=tuple(args.exit_detour_range) if args.exit_detour_range else None)
            suffix=compact_source_guide(suffix)
            record.update(exit_guide=suffix.record(),exit_shortcuts=evidence)
            stage('checking_complete_exit')
            last_plan=plan_source_itinerary(after,flight_end,suffix,p.source,p.static,p.bsp,p.region_policy,
                check_context=check,max_seconds=90.)
            record.update(exit_plan=last_plan.record(),exit_sha256=last_plan.sha256,
                goal=guide.goal,goal_floor_height=last_plan.record()['goal_floor_height'],
                goal_source_ids=last_plan.record()['goal_source_ids'],source_candidate=True,stage='finished')
    except (ValueError,TimeoutError) as error:
        record['refusal']=str(error)
    signal.alarm(0)
    for name,pin in pins.items():checked_bytes(PROJECT/name,pin)
    for name,pin in DATA_PINS.items():checked_bytes(STORE/'owner-route-data'/DATA_NAME/name,pin)
    checked_bytes(args.prior,args.prior_sha256)
    record['completed']=True;save()
    print(json.dumps(dict(output=str(args.output),sha256=sha256(args.output.read_bytes()).hexdigest(),
        candidate=record['source_candidate'],conditional_envelopes=record.get('combined_conditional_envelopes_clear',False),
        stage=record['stage'],reason=record.get('refusal'),
        seconds=record['seconds'],cpu_seconds=record['cpu_seconds'])),flush=True)


if __name__=='__main__':main()
