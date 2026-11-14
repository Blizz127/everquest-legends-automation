#!/usr/bin/env python3
"""Check the ground producer on retained replay points, with synthetic calibration.

This reads copied owner geometry only. It cannot calibrate or accept live
movement. The synthetic raw Z offset is explicit and never inferred from G0.
"""
from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import sys
import time

PROJECT=Path(__file__).resolve().parents[1]
STORE=Path.home()/'.local/share/eql-automation'
sys.path.insert(0,str(PROJECT))
from eql_automation.fixed_route_follower import FixedRoute
from eql_automation.ground_binding import GroundGeometryEvidence,HeightCalibration
from eql_automation.ground_observer import RouteGroundObserver,GroundObservationUnavailable,exact_detail_support
from eql_automation.location_log import RawLocationFix

REPLAY=STORE/'nav-candidates/gfay-bsp-volume-replay-0.41.62.json'
REPLAY_SHA='ff21dfa92e8dbd391002512ed7d5950280655ac066b3967b0e0d8b9ee4af6319'
PLAN=STORE/'nav-candidates/gfay-east-tile-portal-plan-0.41.60.json'
MESH=STORE/'navmesh/nov12-7e3cd28-store/gfaydark.npz'
ARCHIVE=STORE/'client-data/retail-full/assets/gfaydark.s3d'


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if (args.output.exists() or args.output.is_symlink()
            or not args.output.resolve().is_relative_to((STORE/'nav-candidates').resolve())):
        raise ValueError('Choose a new private nav-candidates output')
    began=time.monotonic();cpu=time.process_time()
    if REPLAY.is_symlink() or sha256(REPLAY.read_bytes()).hexdigest()!=REPLAY_SHA:
        raise ValueError('Retained replay changed')
    replay=json.loads(REPLAY.read_text());fixture=replay['ground_binding_fixture']
    assert replay['simulation_only'] is True and fixture['simulation_only'] is True
    proof=sha256(json.dumps(fixture,sort_keys=True).encode()).hexdigest()
    geometry=GroundGeometryEvidence('gfaydark',fixture['mesh'],fixture['source_archive'],
        fixture['source_wld'],proof,fixture['source_z_limit'],
        tuple(tuple(v) for v in fixture['portal_pairs']),True)
    route=FixedRoute.load(PLAN,expected_sha256=fixture['plan'],mesh_sha256=fixture['mesh'])
    observer=RouteGroundObserver.load(MESH,ARCHIVE,geometry_evidence=geometry)
    height=HeightCalibration('synthetic-probe-height-not-live','gfaydark',54,'Greater Faydark',1,1,
        fixture['source_archive'],fixture['source_wld'],2.564,.05,0,0.,1000.,live_verified=True)
    points=[{'step':-1,'segment':0,'position':route.segments[0].start},
            *replay['history'],*replay['recent']]
    results=[]
    for seq,item in enumerate(points,1):
        xyz=tuple(item['position']);index=item['segment']
        polygon=route.segments[index].polygon
        row={'step':item['step'],'segment':index,'input_package_xyz':xyz}
        try:
            row['current_detail']=asdict(exact_detail_support(observer.mesh,polygon,xyz[:2]))
            source_z,ids=observer.source.source_floor_at(xyz[:2])
            # Fixture values only: no historical raw fix or live calibration is promoted.
            raw=RawLocationFix(54,'Greater Faydark',(xyz[1],xyz[0],source_z+2.564),
                datetime(2026,11,14),100.+seq,1,seq,1)
            aligned=observer.observe(raw,route=route,segment_index=index,height_calibration=height,
                motion_calibration_record_id='synthetic-probe-motion-not-live',now=raw.received_monotonic)
            row.update(candidate=True,polygon=aligned.mesh_projection.polygon,
                source_z=source_z,baked_z=aligned.mesh_projection.package_xyz[2],
                difference_from_replay_z=aligned.mesh_projection.package_xyz[2]-xyz[2])
        except ValueError as error:
            row.update(candidate=False,reason=str(error))
        results.append(row)
    pins={str(REPLAY):REPLAY_SHA,str(PLAN):fixture['plan'],str(MESH):fixture['mesh'],str(ARCHIVE):fixture['source_archive']}
    for name in ('ground_observer','ground_binding','portal_precision_view','source_floor_chain'):
        path=PROJECT/'eql_automation'/(name+'.py');pins[str(path)]=sha256(path.read_bytes()).hexdigest()
    for path,digest in pins.items():
        if sha256(Path(path).read_bytes()).hexdigest()!=digest:raise ValueError('Probe input changed')
    result={'format':'eql-ground-producer-probe-v1','simulation_only':True,'game_input_sent':False,
        'real_client_accepted':False,'route_accepted':False,'samples':len(results),
        'passed':sum(r['candidate'] for r in results),'source_floor_chain_used':False,
        'note':'Complete source-layer point queries, not committed source-floor-chain replay; synthetic height 2.564.',
        'wall_seconds':time.monotonic()-began,'cpu_seconds':time.process_time()-cpu,'pins':pins,'results':results}
    with args.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('results','pins')}))
    print('artifact_sha256',sha256(args.output.read_bytes()).hexdigest())


if __name__=='__main__':main()
