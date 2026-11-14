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
import math
import re
import sys
import time

PROJECT=Path(__file__).resolve().parents[1]
STORE=Path.home()/'.local/share/eql-automation'
sys.path.insert(0,str(PROJECT))
from eql_automation.fixed_route_follower import FixedRoute
from eql_automation.ground_binding import GroundGeometryEvidence,HeightCalibration
from eql_automation.ground_observer import RouteGroundObserver,GroundObservationUnavailable,exact_detail_support
from eql_automation.location_log import RawLocationFix,parse_client_log_line,parse_raw_location
from eql_automation.source_floor_chain import SourceFloorChain

REPLAY=STORE/'nav-candidates/gfay-bsp-volume-replay-0.41.62.json'
REPLAY_SHA='ff21dfa92e8dbd391002512ed7d5950280655ac066b3967b0e0d8b9ee4af6319'
PLAN=STORE/'nav-candidates/gfay-east-tile-portal-plan-0.41.60.json'
MESH=STORE/'navmesh/nov12-7e3cd28-store/gfaydark.npz'
ARCHIVE=STORE/'client-data/retail-full/assets/gfaydark.s3d'
FLOOR_CHAIN=STORE/'nav-candidates/gfay-source-floor-chain-fast-0.41.58.json'
FLOOR_CHAIN_SHA='06c0a1d0818826ca0913e94a05b26912f9be05b994fa328230857b42dd04a497'
SOURCE_PROFILE=STORE/'nav-candidates/gfay-tile-source-profile-0.41.57.json'
LOCATION_LOG=STORE/'owner-traces/eqlog-Legira-20261113.txt'
LOCATION_LOG_SHA='d622b3c12567f903d411860d3de1a0be28e4e8b38be7bbdc2bebfdd62c60f04e'


def observed_location_format(text):
    """Validate the retained examples; this is not a universal client guarantee."""
    count=0
    pattern=re.compile(r'Your Location is [+-]?\d+\.\d{2}, [+-]?\d+\.\d{2}, [+-]?\d+\.\d{2}')
    for line in text.splitlines():
        parsed=parse_client_log_line(line)
        if parsed is None or not parsed[1].startswith('Your Location is '):continue
        if pattern.fullmatch(parsed[1]) is None or parse_raw_location(parsed[1]) is None:
            raise ValueError('Retained location examples have a different format')
        count+=1
    if not count:raise ValueError('No retained client location examples')
    return {'examples':count,'decimal_places':2,'scope':'retained examples only'}


def synthetic_location(position,source_z,offset,*,client_format):
    """Serialize a simulated physical pose, never change it or use baked Z.

    Production observation preserves the parsed raw coordinates. Quantization
    belongs only here, at the simulated client/log boundary.
    """
    values=(position[1],position[0],source_z+offset)
    if not all(math.isfinite(v) for v in values):raise ValueError('Nonfinite synthetic location')
    if not client_format:return values,None
    body='Your Location is '+', '.join(f'{v:.2f}' for v in values)
    raw=parse_raw_location(body)
    if raw is None:raise ValueError('Synthetic client location failed parsing')
    return raw,body


def committed_cells(replay):
    """Accept only this completed, one-successful-trial-per-step replay shape.

    Trials with shortening/rejection need an explicit commit ledger instead of
    guessing which proposed chain was committed.
    """
    count=replay['steps']
    groups=[replay[k] for k in ('source_floor_trials','static_floor_trials','bsp_volume_trials')]
    if (type(count) is not int or count<=0 or replay['phase']!='arrived'
            or any(len(rows)!=count for rows in groups)):
        raise ValueError('No complete unambiguous committed floor sequence')
    cells=[]
    for index,rows in enumerate(zip(*groups)):
        source,static,bsp=rows
        identity=(source['step'],source['segment'],source['hold'])
        if (source['step']!=index or any(
                (row['step'],row['segment'],row['hold'])!=identity or row['trial']['candidate'] is not True
                for row in rows) or static['footprint']!=bsp['footprint']
                or source['trial']['floor_step']['candidate'] is not True):
            raise ValueError('Ambiguous or uncommitted floor trial')
        cells.append((index,tuple(tuple(p) for p in static['footprint']),source['trial']['floor_step']))
    return cells


def reconstructed_cells(source,replay,seed_evidence,initial_footprint):
    """Recompute each committed floor cell and its exact retained proof.

    Yield the initial cell at step -1, then post-step cells. The caller must
    consume observations immediately: the yielded chain advances on iteration.
    This is an offline proof reconstruction, never a live floor bootstrap.
    """
    if source.wld_sha256!=seed_evidence['source_wld_sha256']:
        raise ValueError('Floor seed source identity changed')
    cells=committed_cells(replay)
    seed=seed_evidence['seed']
    chain=SourceFloorChain(inventory_sha256=source.wld_sha256,
        seed_evidence_sha256=sha256(json.dumps(seed,sort_keys=True).encode()).hexdigest(),
        seed_ids=tuple(tuple(k) for k in seed['selected_ids']),
        body_height=seed_evidence['hypothetical_body_height'])
    initial=replay['conditional_source_floor_chain']['initial']
    for step,footprint,expected in [(-1,initial_footprint,initial),*cells]:
        result=chain.advance(footprint,source.source_faces_for_footprint(footprint))
        if (not result.candidate or json.dumps(asdict(result),sort_keys=True)!=json.dumps(expected,sort_keys=True)):
            raise ValueError(f'Committed source-floor proof mismatch at step {step}')
        yield step,chain
    retained=replay['conditional_source_floor_chain']
    if (chain.index!=retained['committed_cells'] or chain.previous.proof_sha256!=retained['last_proof_sha256']):
        raise ValueError('Final committed floor chain differs')


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--committed-floor-chain',action='store_true',
        help='Recompute the retained committed source-floor context before sampling')
    parser.add_argument('--client-location-format',action='store_true',
        help='Serialize synthetic raw positions through the observed two-decimal client log format')
    parser.add_argument('--wall-budget',type=float,default=300.,help='Offline probe time budget in seconds')
    args=parser.parse_args()
    if not math.isfinite(args.wall_budget) or args.wall_budget<=0:raise ValueError('Invalid probe budget')
    if (args.output.exists() or args.output.is_symlink()
            or not args.output.resolve().is_relative_to((STORE/'nav-candidates').resolve())):
        raise ValueError('Choose a new private nav-candidates output')
    began=time.monotonic();cpu=time.process_time()
    if REPLAY.is_symlink() or sha256(REPLAY.read_bytes()).hexdigest()!=REPLAY_SHA:
        raise ValueError('Retained replay changed')
    replay=json.loads(REPLAY.read_text());fixture=replay['ground_binding_fixture']
    assert replay['simulation_only'] is True and fixture['simulation_only'] is True
    pins={str(REPLAY):REPLAY_SHA,str(PLAN):fixture['plan'],str(MESH):fixture['mesh'],str(ARCHIVE):fixture['source_archive']}
    modules=('ground_observer','ground_binding','portal_precision_view','source_floor_chain',
        'location_log','source_occupancy','ground_sweep','portal_precision','ground_sweep_view',
        'bsp_detail_view','fixed_route_follower','pfs_archive','wld_inventory','mesh_geometry',
        'material_audit','map_alignment','tile_rounding')
    for path in [Path(__file__),*(PROJECT/'eql_automation'/(name+'.py') for name in modules)]:
        pins[str(path)]=sha256(path.read_bytes()).hexdigest()
    def verify():
        for path,digest in pins.items():
            if Path(path).is_symlink() or sha256(Path(path).read_bytes()).hexdigest()!=digest:
                raise ValueError('Probe input changed: '+path)
    format_evidence=None;seed_evidence=None;initial_footprint=None
    if args.client_location_format:
        pins[str(LOCATION_LOG)]=LOCATION_LOG_SHA
        verify()
        format_evidence=observed_location_format(LOCATION_LOG.read_text(errors='replace'))
    if args.committed_floor_chain:
        pins[str(FLOOR_CHAIN)]=FLOOR_CHAIN_SHA
        pins[str(SOURCE_PROFILE)]=replay['pins'][str(SOURCE_PROFILE)]
        verify()
        seed_evidence=json.loads(FLOOR_CHAIN.read_text())
        initial_footprint=tuple(tuple(p) for p in json.loads(SOURCE_PROFILE.read_text())['cells'][0]['footprint'])
    verify()
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
    points=[dict(item,sample_index=i) for i,item in enumerate(points)]
    results=[];seq=0
    def sample(item,chain):
        nonlocal seq
        seq+=1
        xyz=tuple(item['position']);index=item['segment']
        polygon=route.segments[index].polygon
        row={'sample_index':item['sample_index'],'step':item['step'],'segment':index,'input_package_xyz':xyz,
             'floor_chain_index':None if chain is None else chain.index,
             'floor_chain_proof':None if chain is None else chain.previous.proof_sha256}
        try:
            physical_source_z,ids=(observer.source.source_floor_at(xyz[:2]) if chain is None else chain.floor_at(xyz[:2]))
            coordinates,body=synthetic_location(xyz,physical_source_z,2.564,client_format=args.client_location_format)
            observed_xy=(coordinates[1],coordinates[0])
            row.update(observed_raw_coordinates=coordinates,synthetic_log_body=body,
                physical_source_z=physical_source_z,
                observed_xy_displacement=math.dist(xyz[:2],observed_xy),
                current_detail=asdict(exact_detail_support(observer.mesh,polygon,observed_xy)))
            # Fixture values only: no historical raw fix or live calibration is promoted.
            raw=RawLocationFix(54,'Greater Faydark',coordinates,
                datetime(2026,11,14),100.+seq,1,seq,1)
            aligned=observer.observe(raw,route=route,segment_index=index,height_calibration=height,
                motion_calibration_record_id='synthetic-probe-motion-not-live',now=raw.received_monotonic,
                floor_chain=chain)
            source_z=aligned.source_floor.ground_wld_xyz[2]
            row.update(candidate=True,polygon=aligned.mesh_projection.polygon,
                source_z=source_z,baked_z=aligned.mesh_projection.package_xyz[2],
                raw_height_residual=coordinates[2]-2.564-source_z,
                difference_from_replay_z=aligned.mesh_projection.package_xyz[2]-xyz[2])
        except ValueError as error:
            row.update(candidate=False,reason=str(error))
        results.append(row)

    rebuilt=0
    if args.committed_floor_chain:
        by_step={}
        for item in points:by_step.setdefault(item['step'],[]).append(item)
        for step,chain in reconstructed_cells(observer.source,replay,seed_evidence,initial_footprint):
            rebuilt+=1
            for item in by_step.pop(step,[]):sample(item,chain)
            if time.monotonic()-began>args.wall_budget:raise ValueError('Probe wall budget exhausted')
            if step>=0 and step%500==0:print(json.dumps({'reconstructed_through_step':step,'samples':len(results)}),flush=True)
        if by_step:raise ValueError('Retained samples outside committed sequence')
    else:
        for item in points:
            sample(item,None)
            if time.monotonic()-began>args.wall_budget:raise ValueError('Probe wall budget exhausted')
    verify()
    results.sort(key=lambda row:row['sample_index'])
    result={'format':'eql-ground-producer-probe-v2','simulation_only':True,'game_input_sent':False,
        'real_client_accepted':False,'route_accepted':False,'samples':len(results),'unique_steps':len({r['step'] for r in results}),
        'passed':sum(r['candidate'] for r in results),'source_floor_chain_used':args.committed_floor_chain,
        'reconstructed_committed_cells':rebuilt,'client_location_format':format_evidence,
        'note':'Retained motion unchanged; sampled observation probe only, not a quantized controller replay. Synthetic height 2.564.',
        'wall_seconds':time.monotonic()-began,'cpu_seconds':time.process_time()-cpu,'pins':pins,'results':results}
    with args.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('results','pins')}))
    print('artifact_sha256',sha256(args.output.read_bytes()).hexdigest())


if __name__=='__main__':main()
