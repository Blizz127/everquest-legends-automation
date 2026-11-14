#!/usr/bin/env python3
"""Follow one conditional source floor through pinned, ordered route cells."""
from __future__ import annotations

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
PROFILE=STORE/'nav-candidates/gfay-tile-source-profile-0.41.57.json'
PLAN=STORE/'nav-candidates/gfay-west-portal-plan-0.41.53.json'
MESH=STORE/'navmesh/nov12-7e3cd28-store/gfaydark.npz'
SOURCE=STORE/'client-data/retail-full/assets/gfaydark.s3d'
PINS={PROFILE:'e5dd717c1bd93770d3ec8419dc948efe0c1ebf3f789297533520bdeae0ed4fbd',
      PLAN:'9207b689d3ca462f0eb0b6d45af87deb902662c237dd33f5172ab613021e12f6',
      MESH:'5f8e16c5bcd2221ba273f681750ca480349780524d23609c059a3e817df6abd9',
      MESH.with_suffix('.json'):'ac9591eb63e1394363ad37d7d0ca6609a1ebe11fd8786bedb5b165b833e2eb82',
      SOURCE:'ea95f51a2d4645410223d24cc7da9eb0e7095310c6e9f8756e8c51d67df13d9f'}


def run(output, *, seconds, body_height):
    sys.path.insert(0,str(PROJECT))
    from eql_automation.fixed_route_follower import FixedRoute
    from eql_automation.ground_sweep_view import GroundSweepView
    from eql_automation.portal_precision_view import PortalPrecisionView
    from eql_automation.source_floor_chain import SourceFloorChain
    pins=dict(PINS)
    for name in ('source_floor_chain','source_occupancy','ground_sweep','ground_sweep_view','portal_precision',
                 'portal_precision_view','tile_rounding','fixed_route_follower','map_alignment',
                 'mesh_geometry','material_audit','pfs_archive','wld_inventory'):
        p=PROJECT/'eql_automation'/(name+'.py');pins[p]=sha256(p.read_bytes()).hexdigest()
    pins[Path(__file__)]=sha256(Path(__file__).read_bytes()).hexdigest()
    def verify():
        if any(p.is_symlink() or sha256(p.read_bytes()).hexdigest()!=h for p,h in pins.items()):
            raise ValueError('Pinned floor-chain inputs changed')
    began=time.monotonic();verify()
    profile=json.loads(PROFILE.read_text())
    route=FixedRoute.load(PLAN,expected_sha256=PINS[PLAN],mesh_sha256=PINS[MESH])
    order=[(i,j) for i,s in enumerate(route.segments) for j in range(math.ceil(s.length/2.))]
    if (not profile['complete_cell_scan'] or profile['checked_cells']!=len(order)
            or [(r['segment'],r['partition']) for r in profile['cells']]!=order
            or not profile['cells'][0]['candidate']):
        raise ValueError('Profile is not a complete ordered route-cell scan')
    ground=GroundSweepView.load(MESH,zone='gfaydark')
    view=PortalPrecisionView(ground,MESH,SOURCE,zone='gfaydark',tile_rounding=True)
    seed=tuple(tuple(k) for k in profile['cells'][0]['source_support']['source_faces'])
    seed_evidence={'profile_sha256':PINS[PROFILE],'cell':[0,0],'selected_ids':seed,
                   'basis':'unambiguous_copied_source_support_at_planned_start',
                   'live_start_identity_verified':False}
    seed_sha=sha256(json.dumps(seed_evidence,sort_keys=True).encode()).hexdigest()
    chain=SourceFloorChain(inventory_sha256=view.wld_sha256,seed_evidence_sha256=seed_sha,
                           seed_ids=seed,body_height=body_height)
    records=[];timed_out=False
    for old in profile['cells']:
        if time.monotonic()-began>seconds:
            timed_out=True;break
        footprint=tuple(tuple(p) for p in old['footprint'])
        sources=view.source_faces_for_footprint(footprint)
        if {(s.fragment,s.face) for s in sources}!={tuple(k) for k in old['source_candidates']}:
            raise ValueError('Profile source inventory did not reproduce')
        result=chain.advance(footprint,sources)
        record={'cell':[old['segment'],old['partition']],'old_candidate':old['candidate'],
                'old_reason':old['reason'],'chain':asdict(result)}
        records.append(record)
        if not result.candidate:break
        z,ids=chain.floor_at(tuple(old['reference'][:2]))
        record['source_reference']={'package_xyz':[*old['reference'][:2],z],'source_surface_ids':ids}
    verify()
    complete=len(records)==len(order) and bool(records) and records[-1]['chain']['candidate'] and not timed_out
    report={'format':'eql-conditional-source-floor-chain-v1','offline_only':True,
            'source_or_mesh_modified':False,'game_input_sent':False,'input_authorized':False,
            'real_client_accepted':False,'route_accepted':False,
            'inventory_scope':'zone terrain WLD only; placed objects and dynamics absent',
            'actual_body_height_verified':False,'hypothetical_body_height':body_height,
            'live_start_identity_verified':False,'seed':seed_evidence,'source_wld_sha256':view.wld_sha256,
            'complete_conditional_source_chain':complete,'expected_cells':len(order),'checked_cells':len(records),
            'passed_cells':sum(r['chain']['candidate'] for r in records),'budget_exhausted':timed_out,
            'complete_route_bound_accepted':False,'last_proof_sha256':chain.previous.proof_sha256 if chain.previous else None,
            'cells':records,'pins':{str(p):h for p,h in pins.items()},'seconds':time.monotonic()-began}
    with output.open('x') as out:json.dump(report,out,indent=2);out.write('\n')
    print(json.dumps({'artifact':str(output),'sha256':sha256(output.read_bytes()).hexdigest(),
        'checked':len(records),'passed':report['passed_cells'],'expected':len(order),'complete':complete,
        'last':None if not records else {'cell':records[-1]['cell'],'reason':records[-1]['chain']['reason']},
        'seconds':report['seconds']}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--seconds',type=float,default=240.)
    parser.add_argument('--body-height',type=float,default=8.,help='Explicit hypothetical source-relative body height')
    args=parser.parse_args();output=args.output.expanduser()
    if (output.parent.resolve()!=(STORE/'nav-candidates').resolve() or output.exists() or output.is_symlink()
            or output.suffix!='.json' or not math.isfinite(args.seconds) or not 1<=args.seconds<=300
            or not math.isfinite(args.body_height) or not 0<args.body_height<=100):
        parser.error('Use a new private nav-candidates JSON and bounded finite diagnostic parameters')
    os.umask(0o077);os.nice(15);run(output,seconds=args.seconds,body_height=args.body_height)


if __name__=='__main__':main()
