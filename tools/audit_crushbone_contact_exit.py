#!/usr/bin/env python3
"""Check remaining Throne exit envelopes under an explicit thin-sheet hypothesis.

Replays only the diagnostic stair-landing/ordinary-exit prefix from a pinned
artifact. No full approach/flight replay, trajectory acceptance or game input.
"""
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
import argparse,json,os,resource,signal,sys,time

PROJECT=Path(__file__).resolve().parents[1];STORE=Path.home()/'.local/share/eql-automation'
sys.path[:0]=[str(PROJECT),str(STORE/'owner-assist/0.39.4')]
from eql_automation.crushbone_assets import DATA_NAME,DATA_PINS,load_crushbone_assets
from eql_automation.native_region_policy import encoded
from eql_automation.owner_route_assets import checked_bytes
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_itinerary import SourceItineraryGuide,SourceStepHint,SourceWalkHint
from eql_automation.static_floor_guard import check_source_static_floor
from tools.source_contact_envelope import declare_contact_hypothesis,audit_contact_walks


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--composed',type=Path,required=True)
    parser.add_argument('--composed-sha256',required=True)
    parser.add_argument('--guide',type=Path,required=True)
    parser.add_argument('--guide-sha256',required=True)
    parser.add_argument('--contact-face',nargs=2,type=int,action='append',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if (args.output.exists() or args.output.is_symlink()
            or args.output.with_suffix('.json.tmp').exists()
            or args.output.parent.resolve()!=(STORE/'nav-candidates').resolve()):
        parser.error('New private diagnostic output required')
    os.umask(0o077);os.nice(19);resource.setrlimit(resource.RLIMIT_CPU,(40,45))
    began=time.monotonic();cpu=time.process_time()
    def check():
        if time.monotonic()-began>180 or time.process_time()-cpu>40:
            raise TimeoutError('Contact exit diagnostic budget exhausted')
    def timeout(*_):raise TimeoutError('Contact exit diagnostic budget exhausted')
    signal.signal(signal.SIGALRM,timeout);signal.signal(signal.SIGXCPU,timeout);signal.alarm(180)
    code=[Path(__file__).resolve(),PROJECT/'tools/source_contact_envelope.py',
          *sorted((PROJECT/'eql_automation').glob('*.py'))]
    pins={str(p.relative_to(PROJECT)):sha256(p.read_bytes()).hexdigest() for p in code}
    record=dict(format='eql-offline-contact-exit-v1',code_sha256=pins,data_sha256=DATA_PINS,
        composed_sha256=args.composed_sha256,guide_sha256=args.guide_sha256,
        completed=False,exit_envelopes_clear=False,full_prior_lineage_replayed=False,
        diagnostic_seed_only=True,route_candidate=False,executable_itinerary=False,
        transition_kinematics_verified=False,contact_semantics_verified=False,
        input_authorized=False,real_client_accepted=False,game_input_sent=False,
        attempts=[],accepted_envelopes=[])
    def save():
        record.update(seconds=time.monotonic()-began,cpu_seconds=time.process_time()-cpu)
        temporary=args.output.with_suffix('.json.tmp')
        with temporary.open('x') as f:json.dump(record,f,indent=2,allow_nan=False)
        temporary.replace(args.output)
    try:
        prior=json.loads(checked_bytes(args.composed,args.composed_sha256))
        base=json.loads(checked_bytes(args.guide,args.guide_sha256))
        if prior['data_sha256']!=DATA_PINS or base['data_sha256']!=DATA_PINS:
            raise ValueError('Contact audit data pins differ')
        guide=SourceItineraryGuide.from_record(base['guide']);landing=prior['stair_plan']
        if not landing['flight']['candidate'] or not landing['planned_landing_only']:
            raise ValueError('Checked offline stair landing required')
        start=tuple(landing['end'])
        indices=[i for i,op in enumerate(guide.operations) if type(op) is SourceStepHint and op.end==start]
        if len(indices)!=1:raise ValueError('Unique stair exit required')
        suffix=guide.operations[indices[0]+1:]
        if any(type(op) is not SourceWalkHint for op in suffix):
            raise ValueError('Contact exit audit cannot reinterpret source steps')
        a=load_crushbone_assets(STORE/'owner-route-data'/DATA_NAME,native_planning=True);p=a.planner
        declaration=declare_contact_hypothesis(p.static,tuple(tuple(k) for k in args.contact_face))
        record['contact_hypothesis']=declaration.record()
        seed=dict(kind='synthetic_diagnostic_stair_landing',start=start,
            seed_ids=landing['landing']['selected_ids'],parent_artifact=args.composed_sha256)
        chain=SourceFloorChain(inventory_sha256=p.source.wld_sha256,
            seed_evidence_sha256=sha256(encoded(seed)).hexdigest(),
            seed_ids=tuple(tuple(k) for k in seed['seed_ids']),body_height=guide.body_height)
        def advance(a,b):
            cap=swept_square(a,b,guide.radius);sources=p.source.source_faces_for_footprint(cap)
            floor=chain.advance(cap,sources)
            if not floor.candidate:raise ValueError('Ordinary prefix: '+floor.reason)
            placed=check_source_static_floor(floor,cap,sources,p.static)
            if not placed.candidate:raise ValueError('Ordinary prefix static: '+placed.reason)
        advance(start,start);position=start;walks=[]
        for row in prior['exit_shortcuts']['accepted_proposals']:
            if row['kind']!='walk':break
            if tuple(row['start'])!=position:raise ValueError('Exit prefix continuity differs')
            advance(position,tuple(row['end']));position=tuple(row['end']);walks.append(row)
        index=walks[-1]['last_origin']+1
        if suffix[index].start!=position:raise ValueError('Unknown diagnostic exit boundary')
        record.update(seed=seed,ordinary_prefix_walks=walks,start=position,goal=guide.goal)
        def progress(value):
            record.update(contact_walks=value,attempts=value['attempts'],
                accepted_envelopes=value['accepted_envelopes']);save()
        result=audit_contact_walks(chain,suffix[index:],guide.goal,p.source,p.static,p.bsp,
            p.region_policy,declaration,radius=guide.radius,check_context=check,progress=progress)
        record.update(exit_envelopes_clear=result['exit_envelopes_clear'],
            attempts=result['attempts'],accepted_envelopes=result['accepted_envelopes'],
            reference_goal_height=result['reference_goal_height'],
            reference_goal_source_ids=result['reference_goal_source_ids'],
            conclusion='remaining_exit_clear_only_under_unverified_contact_and_motion_hypotheses')
    except (ValueError,TimeoutError) as error:record['refusal']=str(error)
    signal.alarm(0)
    for name,pin in pins.items():checked_bytes(PROJECT/name,pin)
    for name,pin in DATA_PINS.items():checked_bytes(STORE/'owner-route-data'/DATA_NAME/name,pin)
    checked_bytes(args.composed,args.composed_sha256);checked_bytes(args.guide,args.guide_sha256)
    record['completed']=True;save()
    print(json.dumps(dict(output=str(args.output),sha256=sha256(args.output.read_bytes()).hexdigest(),
        envelopes_clear=record['exit_envelopes_clear'],reason=record.get('refusal'),
        accepted=len(record['accepted_envelopes']),attempted=len(record['attempts']),
        seconds=record['seconds'],cpu_seconds=record['cpu_seconds'])),flush=True)


if __name__=='__main__':main()
