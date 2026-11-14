#!/usr/bin/env python3
"""Inspect the copied exit obstruction from a labelled synthetic stair landing.

This replays the accepted exit walks with a new diagnostic seed. It does not
replay the earlier approach/flight or claim a current character observation.
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
from eql_automation.source_itinerary import SourceItineraryGuide,SourceStepHint
from eql_automation.static_floor_guard import check_source_static_floor


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--composed',type=Path,required=True)
    parser.add_argument('--composed-sha256',required=True)
    parser.add_argument('--guide',type=Path,required=True)
    parser.add_argument('--guide-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--waypoint',nargs=2,type=float,action='append',default=[],metavar=('X','Y'),
        help='Explicit diagnostic detour proposal, checked in order from the retained exit prefix')
    args=parser.parse_args()
    if (args.output.exists() or args.output.is_symlink()
            or args.output.parent.resolve()!=(STORE/'nav-candidates').resolve()):
        parser.error('New private diagnostic output required')
    os.umask(0o077);os.nice(19);resource.setrlimit(resource.RLIMIT_CPU,(20,25))
    began=time.monotonic();cpu=time.process_time()
    def timeout(*_):raise TimeoutError('Copied gap diagnostic budget exhausted')
    signal.signal(signal.SIGALRM,timeout);signal.signal(signal.SIGXCPU,timeout);signal.alarm(90)
    pins={str(p.relative_to(PROJECT)):sha256(p.read_bytes()).hexdigest()
          for p in (Path(__file__).resolve(),*sorted((PROJECT/'eql_automation').glob('*.py')))}
    record=dict(format='eql-offline-stair-exit-gap-v1',code_sha256=pins,data_sha256=DATA_PINS,
        composed_sha256=args.composed_sha256,guide_sha256=args.guide_sha256,
        diagnostic_seed_only=True,full_prior_lineage_replayed=False,regions_checked=False,
        input_authorized=False,real_client_accepted=False,game_input_sent=False,
        completed=False,attempts=[])
    try:
        prior=json.loads(checked_bytes(args.composed,args.composed_sha256))
        base=json.loads(checked_bytes(args.guide,args.guide_sha256))
        if prior['data_sha256']!=DATA_PINS or base['data_sha256']!=DATA_PINS:
            raise ValueError('Diagnostic data pins differ')
        guide=SourceItineraryGuide.from_record(base['guide'])
        landing=prior['stair_plan']
        if not landing['flight']['candidate'] or not landing['planned_landing_only']:
            raise ValueError('Checked offline stair landing required')
        start=tuple(landing['end'])
        indices=[i for i,op in enumerate(guide.operations) if type(op) is SourceStepHint and op.end==start]
        if len(indices)!=1:raise ValueError('Unique stair exit required')
        suffix=guide.operations[indices[0]+1:]
        a=load_crushbone_assets(STORE/'owner-route-data'/DATA_NAME,native_planning=True);p=a.planner
        seed=dict(kind='synthetic_diagnostic_stair_landing',start=start,
            seed_ids=landing['landing']['selected_ids'],parent_artifact=args.composed_sha256)
        chain=SourceFloorChain(inventory_sha256=p.source.wld_sha256,
            seed_evidence_sha256=sha256(encoded(seed)).hexdigest(),
            seed_ids=tuple(tuple(k) for k in seed['seed_ids']),body_height=guide.body_height)
        def advance(a,b):
            cap=swept_square(a,b,guide.radius);sources=p.source.source_faces_for_footprint(cap)
            floor=chain.advance(cap,sources)
            if not floor.candidate:raise ValueError('Diagnostic prefix: '+floor.reason)
            static=check_source_static_floor(floor,cap,sources,p.static)
            if not static.candidate:raise ValueError('Diagnostic prefix static: '+static.reason)
            return floor
        advance(start,start);position=start;walks=[]
        for row in prior['exit_shortcuts']['accepted_proposals']:
            if row['kind']!='walk':break
            if tuple(row['start'])!=position:raise ValueError('Exit walk continuity changed')
            floor=advance(position,tuple(row['end']));position=tuple(row['end'])
            walks.append(dict(start=row['start'],end=row['end'],source_ids=floor.selected_ids))
        failed_index=prior['exit_shortcuts']['accepted_proposals'][len(walks)-1]['last_origin']+1
        if suffix[failed_index].start!=position:raise ValueError('Gap does not follow retained walks')
        current_height,current_ids=chain.floor_at(position)
        record.update(seed=seed,walks=walks,position=position,height=current_height,
            current_source_ids=current_ids,failed_operation=failed_index,
            next_endpoint=suffix[failed_index].end)
        candidates=[('original_next',suffix[failed_index].end)]
        candidates.extend((f'neighbor_{dx}_{dy}',(position[0]+2*dx,position[1]+2*dy))
            for dx in (-1,0,1) for dy in (-1,0,1) if dx or dy)
        for name,goal in candidates:
            cap=swept_square(position,goal,guide.radius)
            item=dict(name=name,end=goal,footprint=cap)
            try:
                sources=p.source.source_faces_for_footprint(cap)
                branch=chain.fork();floor=branch.advance(cap,sources)
                item.update(terrain=asdict(floor),source_faces=[asdict(s) for s in sources])
                if floor.candidate:
                    check=check_source_static_floor(floor,cap,sources,p.static)
                    placed=p.static.faces_for_footprint(cap)
                    item.update(static=asdict(check),static_faces=[asdict(s) for s in placed])
                    item['static_identities']={str(s.fragment):p.static.identities[s.fragment] for s in placed}
            except ValueError as error:item['query_refusal']=str(error)
            record['attempts'].append(item)
        # A map marker need not be a usable stopping floor. Check explicit
        # nearby proposals without treating the marker or an object name as
        # permission to omit collision geometry. These remain diagnostic and
        # require the full approach/flight/region rebuild before route use.
        if args.waypoint:
            branch=chain.fork();here=position;checks=[]
            record['waypoint_proposal']=dict(points=[position,*args.waypoint],checks=checks,
                candidate=False,regions_checked=False,full_prior_lineage_replayed=False)
            for point in args.waypoint:
                goal=tuple(point);cap=swept_square(here,goal,guide.radius)
                row=dict(start=here,end=goal,footprint=cap);checks.append(row)
                try:
                    sources=p.source.source_faces_for_footprint(cap)
                    floor=branch.advance(cap,sources);row['terrain']=asdict(floor)
                    if not floor.candidate:break
                    static=check_source_static_floor(floor,cap,sources,p.static)
                    row['static']=asdict(static)
                    if not static.candidate:break
                    here=goal
                except ValueError as error:
                    row['query_refusal']=str(error);break
            else:record['waypoint_proposal']['candidate']=True
        # Raw private context retains every height. The later drawing may show
        # a labelled slice, but none of these faces are dropped from checks.
        window=(position[0]-20,position[1]-20,position[0]+40,position[1]+60)
        def nearby(source):
            points=tuple((y,x,z) for x,y,z in source.vertices_wld)
            return all(min(v[k] for v in points)<=window[k+2] and max(v[k] for v in points)>=window[k] for k in (0,1))
        record.update(window=window,context_source_faces=[asdict(s) for s in p.source.sources if nearby(s)],
            context_static_faces=[asdict(s) for s in p.static.sources if nearby(s)])
        record['context_static_identities']={str(s['fragment']):p.static.identities[s['fragment']]
            for s in record['context_static_faces']}
    except (ValueError,TimeoutError) as error:record['refusal']=str(error)
    signal.alarm(0)
    for name,pin in pins.items():checked_bytes(PROJECT/name,pin)
    for name,pin in DATA_PINS.items():checked_bytes(STORE/'owner-route-data'/DATA_NAME/name,pin)
    checked_bytes(args.composed,args.composed_sha256);checked_bytes(args.guide,args.guide_sha256)
    record.update(completed=True,seconds=time.monotonic()-began,cpu_seconds=time.process_time()-cpu)
    with args.output.open('xb') as f:f.write(encoded(record))
    print(json.dumps(dict(output=str(args.output),sha256=sha256(args.output.read_bytes()).hexdigest(),
        reason=record.get('refusal'),seconds=record['seconds'],cpu_seconds=record['cpu_seconds'],
        attempts=[dict(name=r['name'],terrain=r.get('terrain',{}).get('reason'),
            static=r.get('static',{}).get('reason'),query=r.get('query_refusal')) for r in record['attempts']],
        waypoint_candidate=record.get('waypoint_proposal',{}).get('candidate'),
        waypoint_checks=len(record.get('waypoint_proposal',{}).get('checks',[])))),flush=True)


if __name__=='__main__':main()
