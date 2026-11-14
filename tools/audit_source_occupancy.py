#!/usr/bin/env python3
"""Classify retained terrain layers relative to explicit source-floor hypotheses."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

PROJECT=Path(__file__).resolve().parents[1]
STORE=Path.home()/'.local/share/eql-automation'
PROFILE=STORE/'nav-candidates/gfay-source-profile-0.41.56.json'
MESH=STORE/'navmesh/nov12-7e3cd28-store/gfaydark.npz'
SOURCE=STORE/'client-data/retail-full/assets/gfaydark.s3d'
PINS={PROFILE:'be99450b900f29f736185a21204a4889af78cefe5abf7cb7b73c63a5e68a3be8',
      MESH:'5f8e16c5bcd2221ba273f681750ca480349780524d23609c059a3e817df6abd9',
      SOURCE:'ea95f51a2d4645410223d24cc7da9eb0e7095310c6e9f8756e8c51d67df13d9f'}


def run(output):
    sys.path.insert(0,str(PROJECT))
    from eql_automation.ground_sweep_view import GroundSweepView
    from eql_automation.portal_precision_view import PortalPrecisionView
    from eql_automation.source_occupancy import check_selected_floor_clearance
    pins=dict(PINS)
    for module in ('source_occupancy','ground_sweep','ground_sweep_view','portal_precision','portal_precision_view',
                   'tile_rounding','map_alignment','mesh_geometry','material_audit','pfs_archive','wld_inventory'):
        p=PROJECT/'eql_automation'/(module+'.py');pins[p]=sha256(p.read_bytes()).hexdigest()
    pins[Path(__file__)]=sha256(Path(__file__).read_bytes()).hexdigest()
    def verify():
        if any(p.is_symlink() or sha256(p.read_bytes()).hexdigest()!=h for p,h in pins.items()):
            raise ValueError('Pinned occupancy input changed')
    verify()
    profile=json.loads(PROFILE.read_text());rows={(r['segment'],r['partition']):r for r in profile['cells']}
    ground=GroundSweepView.load(MESH,zone='gfaydark')
    view=PortalPrecisionView(ground,MESH,SOURCE,zone='gfaydark')
    previous=rows[87,48]
    if not previous['candidate'] or [1208,9] not in previous['source_support']['source_faces']:
        raise ValueError('Earlier local grass evidence changed')
    records=[]
    for segment,part,selected in ((87,49,((1208,9),)),(87,50,((1208,9),)),(89,0,((1174,1),))):
        row=rows[segment,part];footprint=tuple(tuple(p) for p in row['footprint'])
        sources=view.source_faces_for_footprint(footprint)
        evidence={'profile_sha256':PINS[PROFILE],'cell':(segment,part),'selected':selected,
            'basis':'same_source_face_as_local_passing_cell_87_48' if segment==87 else 'explicit_floor_hypothesis',
            'g0_connected_floor_chain_verified':False,'live_selection_verified':False}
        selection_sha=sha256(json.dumps(evidence,sort_keys=True).encode()).hexdigest()
        checks=[asdict(check_selected_floor_clearance(footprint,sources,selected_ids=selected,
            selection_evidence_sha256=selection_sha,body_height=height)) for height in (6.,8.)]
        records.append({'cell':(segment,part),'prior_reason':row['reason'],'selection':evidence,
                        'checks':checks,'source_candidates':[(s.fragment,s.face) for s in sources]})
    verify()
    report={'format':'eql-conditional-source-occupancy-v1','offline_only':True,'records':records,
        'inventory_scope':'zone terrain WLD only; placed objects and dynamics absent',
        'actual_body_height_verified':False,'g0_connected_floor_chain_verified':False,
        'complete_route_bound_accepted':False,'source_rule_changed':False,'game_input_sent':False,
        'input_authorized':False,'real_client_accepted':False,'route_accepted':False,
        'source_wld_sha256':view.wld_sha256,'pins':{str(p):h for p,h in pins.items()}}
    with output.open('x') as out:json.dump(report,out,indent=2);out.write('\n')
    print(json.dumps({'artifact':str(output),'sha256':sha256(output.read_bytes()).hexdigest(),
        'cells':[{'cell':r['cell'],'checks':[{'height':c['hypothetical_body_height'],'candidate':c['candidate'],
            'reason':c['reason']} for c in r['checks']]} for r in records]}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();output=args.output.expanduser()
    if (output.parent.resolve()!=(STORE/'nav-candidates').resolve() or output.exists()
            or output.is_symlink() or output.suffix!='.json'):
        parser.error('Use a new private nav-candidates JSON')
    os.umask(0o077);os.nice(15);run(output)


if __name__=='__main__':main()
