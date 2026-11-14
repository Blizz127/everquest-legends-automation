#!/usr/bin/env python3
"""Pin the inferred tile-side model against copied GFay links and one failure."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys

PROJECT=Path(__file__).resolve().parents[1]
STORE=Path.home()/'.local/share/eql-automation'
MESH=STORE/'navmesh/nov12-7e3cd28-store/gfaydark.npz'
SOURCE=STORE/'client-data/retail-full/assets/gfaydark.s3d'
REPLAY=STORE/'nav-candidates/gfay-two-ulp-replay-0.41.56.json'
BAKER=STORE/'nav-candidates/trainer-sensitivity-20261113T1557Z/eqlnav_bake'
PINS={MESH:'5f8e16c5bcd2221ba273f681750ca480349780524d23609c059a3e817df6abd9',
      MESH.with_suffix('.json'):'ac9591eb63e1394363ad37d7d0ca6609a1ebe11fd8786bedb5b165b833e2eb82',
      SOURCE:'ea95f51a2d4645410223d24cc7da9eb0e7095310c6e9f8756e8c51d67df13d9f',
      REPLAY:'65b7560c62b41ae6af69dc9d95138ff275fc8e7ce9acd35e4300a6ed800f29f7',
      BAKER:'072f9b06935ef76d870219e4e2812146006d0c86fdca4bb6c78b70eed4383d44'}


def run(output):
    sys.path.insert(0,str(PROJECT))
    import numpy as np
    from eql_automation.ground_sweep_view import GroundSweepView
    from eql_automation.portal_precision_view import PortalPrecisionView
    from eql_automation.portal_precision import float32_steps
    pins=dict(PINS)
    for module in ('tile_rounding','ground_sweep','ground_sweep_view','portal_precision','portal_precision_view',
                   'map_alignment','mesh_geometry','material_audit','pfs_archive','wld_inventory'):
        p=PROJECT/'eql_automation'/(module+'.py');pins[p]=sha256(p.read_bytes()).hexdigest()
    pins[Path(__file__)]=sha256(Path(__file__).read_bytes()).hexdigest()
    def verify():
        if any(p.is_symlink() or sha256(p.read_bytes()).hexdigest()!=h for p,h in pins.items()):
            raise ValueError('Pinned tile-model input changed')
    verify()
    ground=GroundSweepView.load(MESH,zone='gfaydark')
    view=PortalPrecisionView(ground,MESH,SOURCE,zone='gfaydark',tile_rounding=True)
    if view.tile_grid.baker_sha256!=PINS[BAKER]:raise ValueError('Retained baker identity changed')
    with np.load(MESH,allow_pickle=False) as data:
        links={}
        for a,b,edge in zip(data['link_a'],data['link_b'],data['link_pts']):
            links.setdefault((int(a),int(b)),[]).append(tuple(tuple(float(v) for v in p) for p in edge))
    mismatches=[]
    matched={(s.source,s.target):s for s in view.seams}
    for (a,b),forward in links.items():
        reverse=links.get((b,a),())
        if (a>=b or len(forward)!=1 or len(reverse)!=1 or ground.areas[a]!=63
                or ground.areas[b]!=63 or ground.components[a]!=ground.components[b]):continue
        for axis in (0,1):
            other=1-axis
            first=sorted(forward[0],key=lambda p:p[other]);second=sorted(reverse[0],key=lambda p:p[other])
            if (first[0][axis]!=first[1][axis] or second[0][axis]!=second[1][axis]
                    or first[0][axis]==second[0][axis] or
                    any(p[other]!=q[other] or p[2]!=q[2] for p,q in zip(first,second))):continue
            seam=matched.get((a,b))
            mismatches.append({'polygons':(a,b),'axis':axis,'coordinates':(first[0][axis],second[0][axis]),
                'matched':seam is not None,'lower_tile':None if seam is None else seam.tile_boundary.lower_tile,
                'ulp_steps':float32_steps(first[0][axis],second[0][axis])})
    failure=json.loads(REPLAY.read_text())['sweep_failure']
    if failure['segment']!=65 or failure['result']['reason']!='overlapping_ground_faces':
        raise ValueError('Unexpected retained tile failure')
    footprint=tuple(tuple(p) for p in failure['footprint']);reference=tuple(failure['reference'])
    window=max(math.dist(reference[:2],p) for p in footprint)+.05
    original,ids=ground.check(footprint,reference=reference,component=2,vertical_window=window)
    if tuple(failure['detail_ids'])!=ids or original.reason!='overlapping_ground_faces':
        raise ValueError('Retained tile overlap did not reproduce')
    result=view.retry(original,footprint,ids,reference=reference,component=2,vertical_window=window,
        maximum_source_z_difference=.9,allow_overlap=True)
    verify()
    report={'format':'eql-inferred-tile-rounding-audit-v1','model_is_inferred':True,
        'native_baker_source_verified':False,'offline_only':True,'game_input_sent':False,
        'input_authorized':False,'real_client_accepted':False,'route_accepted':False,'source_or_mesh_modified':False,
        'model':asdict(view.tile_grid),'mismatches':mismatches,'matched_count':sum(r['matched'] for r in mismatches),
        'orientation_refusals':view.tile_orientation_refusals,'eligible_seams':len(view.seams),
        'original':asdict(original),'local_retry':asdict(result),'footprint':footprint,'reference':reference,
        'detail_ids':ids,'source_wld_sha256':view.wld_sha256,'pins':{str(p):h for p,h in pins.items()}}
    with output.open('x') as out:json.dump(report,out,indent=2);out.write('\n')
    print(json.dumps({'artifact':str(output),'sha256':sha256(output.read_bytes()).hexdigest(),
        'mismatches':len(mismatches),'matched':report['matched_count'],'orientation_refusals':view.tile_orientation_refusals,
        'local_candidate':result.candidate,'reason':result.reason,
        'overlap_after':None if result.coverage is None else result.coverage.overlap_area}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();output=args.output.expanduser()
    if (output.parent.resolve()!=(STORE/'nav-candidates').resolve() or output.exists()
            or output.is_symlink() or output.suffix!='.json'):
        parser.error('Use a new private nav-candidates JSON')
    os.umask(0o077);os.nice(15);run(output)


if __name__=='__main__':main()
