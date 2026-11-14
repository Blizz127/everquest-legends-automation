#!/usr/bin/env python3
"""Reproduce the retained GFay overlap and its scoped offline correction."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
STORE = Path.home()/'.local/share/eql-automation'
REPLAY = STORE/'nav-candidates/gfay-separated-ground-z2-replay-0.41.55.json'
MESH = STORE/'navmesh/nov12-7e3cd28-store/gfaydark.npz'
SOURCE = STORE/'client-data/retail-full/assets/gfaydark.s3d'
PINS = {
    REPLAY:'12ebd718d386ed8f7a8df7fdf43054a047b162a74ba73408eb50549e4ccd99a8',
    MESH:'5f8e16c5bcd2221ba273f681750ca480349780524d23609c059a3e817df6abd9',
    SOURCE:'ea95f51a2d4645410223d24cc7da9eb0e7095310c6e9f8756e8c51d67df13d9f',
}


def run(output):
    sys.path.insert(0,str(PROJECT))
    from eql_automation.ground_sweep_view import GroundSweepView
    from eql_automation.portal_precision_view import PortalPrecisionView
    pins = dict(PINS)
    for name in ('ground_sweep','ground_sweep_view','portal_precision','portal_precision_view',
                 'map_alignment','pfs_archive','wld_inventory','mesh_geometry','material_audit'):
        p=PROJECT/'eql_automation'/(name+'.py'); pins[p]=sha256(p.read_bytes()).hexdigest()
    pins[Path(__file__)]=sha256(Path(__file__).read_bytes()).hexdigest()
    def verify():
        if any(p.is_symlink() or sha256(p.read_bytes()).hexdigest()!=h for p,h in pins.items()):
            raise ValueError('Pinned overlap input changed')
    verify()
    replay=json.loads(REPLAY.read_text())
    failure=replay['sweep_failure']
    if failure['segment']!=38 or failure['result']['reason']!='overlapping_ground_faces':
        raise ValueError('Unexpected retained overlap')
    footprint=tuple(tuple(p) for p in failure['footprint'])
    reference=tuple(failure['reference'])
    window=max(math.dist(reference[:2],p) for p in footprint)+.05
    ground=GroundSweepView.load(MESH,zone='gfaydark')
    view=PortalPrecisionView(ground,MESH,SOURCE,zone='gfaydark')
    original,ids=ground.check(footprint,reference=reference,component=2,vertical_window=window)
    if original.reason!='overlapping_ground_faces' or tuple(failure['detail_ids'])!=ids:
        raise ValueError('Copied overlap did not reproduce')
    args=dict(reference=reference,component=2,vertical_window=window,maximum_source_z_difference=.6)
    control=view.retry(original,footprint,ids,**args)
    result=view.retry(original,footprint,ids,allow_overlap=True,**args)
    if control.candidate or not result.candidate or not result.overlap_attribution.candidate:
        raise ValueError('Scoped overlap correction or unchanged default did not reproduce')
    pairs=[{'detail_ids':[ids[p.first_face],ids[p.second_face]],**asdict(p)}
           for p in result.overlap_attribution.pairs]
    verify()
    report={'format':'eql-source-supported-overlap-diagnostic-v1',
        'offline_only':True,'game_input_sent':False,'input_authorized':False,
        'real_client_accepted':False,'route_accepted':False,'source_or_mesh_modified':False,
        'reference':reference,'footprint':footprint,'detail_ids':ids,'vertical_window':window,
        'original':asdict(original),'default_gap_only_control':asdict(control),
        'overlap_retry':asdict(result),'attributed_pairs':pairs,
        'source_wld_sha256':view.wld_sha256,'pins':{str(p):h for p,h in pins.items()}}
    with output.open('x') as out:json.dump(report,out,indent=2);out.write('\n')
    print(json.dumps({'artifact':str(output),'sha256':sha256(output.read_bytes()).hexdigest(),
        'overlap_before':original.overlap_area,'overlap_after':result.coverage.overlap_area,
        'source_baked_delta':result.source_support.maximum_source_baked_z_difference,
        'pairs':pairs,'shifted_vertices':result.shifted_vertices}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();output=args.output.expanduser()
    if (output.parent.resolve()!=(STORE/'nav-candidates').resolve() or output.exists()
            or output.is_symlink() or output.suffix!='.json'):
        parser.error('Use a new private nav-candidates JSON')
    os.umask(0o077);os.nice(15);run(output)


if __name__=='__main__':main()
