#!/usr/bin/env python3
"""Replay isolated route tile crossings against copied GFay geometry, no input.

The synthetic positions are taken three units before selected portal targets
in the retained 197-segment planning artifact. This is not a route traversal.
"""
import argparse
from dataclasses import asdict, replace
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
import time

PROJECT=Path(__file__).resolve().parents[1]
STORE=Path.home()/'.local/share/eql-automation'
sys.path[:0]=[str(PROJECT),str(STORE/'owner-assist/0.39.15')]
from eql_automation.owner_route_assets import load_gfay_planner,TILE_DATA_NAME
from eql_automation.route_geometry import RouteGeometryPreparer,RouteMotionBounds
from eql_automation.source_floor_chain import SourceFloorChain


def run(output):
    if output.exists() or output.is_symlink() or not output.resolve().is_relative_to((STORE/'nav-candidates').resolve()):
        raise ValueError('Use a new private nav-candidates directory')
    plan_path=STORE/'nav-candidates/gfay-crushbone-destination-pinned-0.42.11/plan.json'
    pins={plan_path:'ebe75cdd071ab04866b79ef559a8b56a702b9dc29988e9fdcd206ad0d90e021b'}
    for path in (Path(__file__),*(PROJECT/'eql_automation').glob('*.py')):
        pins[path]=sha256(path.read_bytes()).hexdigest()
    def verify():
        if any(path.is_symlink() or sha256(path.read_bytes()).hexdigest()!=pin for path,pin in pins.items()):
            raise ValueError('Probe inputs changed')
    verify()
    p=load_gfay_planner(STORE/'owner-route-data'/TILE_DATA_NAME,tile_rounding=True)
    segments=json.loads(plan_path.read_text())['segments']
    bounds=RouteMotionBounds('synthetic-retained-seam-hypotheses','no-client-motion',
        .01,.1,.2,30.,.4,.01,2.,.1,1.2,6.)
    # Evaluate the pure geometry method with actual complete views. No ledger,
    # scene authority, receipt or sender is constructed or implied by this probe.
    q=RouteGeometryPreparer.__new__(RouteGeometryPreparer)
    q.ground,q.source,q.static,q.bsp=p.ground,p.source,p.static,p.bsp
    q.vertical_window=3.;q.maximum_source_z_difference=2.;q.precision_policy=p.precision_policy
    q.expected_zone_line=None
    records=[]
    for index in (39,54,58):
        a,b=segments[index]['points'];length=math.dist(a[:2],b[:2])
        direction=tuple((b[j]-a[j])/length for j in (0,1))
        xy=tuple(b[j]-3*direction[j] for j in (0,1))
        heading=math.degrees(math.atan2(direction[0],direction[1]))%360
        poly,z=p._support(xy);source_z,names=p.source.source_floor_at(xy)
        chain=SourceFloorChain(inventory_sha256=p.pins[2],
            seed_evidence_sha256=sha256(b'synthetic isolated copied GFay seam probe, not a route traversal').hexdigest(),
            seed_ids=tuple(tuple(map(int,name.split(':')[1::2])) for name in names),body_height=bounds.body_height)
        record=dict(segment=index,polygon=poly,position=(*xy,z),source_z=source_z,
                    heading=heading,source_ids=names,crossing=b)
        began=time.monotonic();cpu=time.process_time()
        seed=q._trial('pivot',(*xy,z),heading,int(p.ground.components[poly]),chain,bounds)
        if isinstance(seed,str):raise ValueError('Copied isolated seed refused: '+seed)
        before=seed[2].previous.proof_sha256
        result=q._trial('forward',(*xy,z),heading,int(p.ground.components[poly]),seed[2],bounds)
        record['initial_index']=seed[2].index
        if isinstance(result,str):record['forward_refusal']=result
        else:
            record.update(footprint=result[0],terrain=asdict(result[3]),static=asdict(result[4]),
                bsp=asdict(result[5]),fork_index=result[2].index)
            q.precision_policy=replace(p.precision_policy,allow_overlap=False)
            denied=q._trial('forward',(*xy,z),heading,int(p.ground.components[poly]),seed[2],bounds)
            record['without_overlap']=denied if isinstance(denied,str) else 'accepted'
            q.precision_policy=p.precision_policy
        record.update(seconds=time.monotonic()-began,cpu_seconds=time.process_time()-cpu,
            original_chain_unchanged=seed[2].index==1 and seed[2].previous.proof_sha256==before)
        records.append(record)
    verify();p._check_views()
    assert all(records[i]['without_overlap']=='Terrain: overlapping_ground_faces' for i in (0,2))
    assert records[1]['forward_refusal']=='Terrain: surface_crosses_height_window'
    assert all(r['original_chain_unchanged'] for r in records)
    evidence=dict(format='eql-isolated-tile-runtime-geometry-probe-v1',pins={str(p):h for p,h in pins.items()},
        data_pins=p.pins,bsp_inventory_sha256=p.bsp_pin,precision_policy=p.precision_policy.record(),
        bounds=asdict(bounds),records=records,simulation_only=True,ledger_sender_test=False,
        game_input_sent=False,real_client_accepted=False,whole_corridor_clearance_verified=False)
    output.mkdir(parents=True);(output/'executed.py').write_bytes(Path(__file__).read_bytes())
    path=output/'probe.json';path.write_text(json.dumps(evidence,indent=2)+'\n')
    return dict(path=str(path),sha256=sha256(path.read_bytes()).hexdigest(),
        positive_segments=[39,58],height_window_refusal=54,real_client_accepted=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    print(json.dumps(run(parser.parse_args().output),indent=2))
