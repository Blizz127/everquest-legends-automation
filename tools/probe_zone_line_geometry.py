#!/usr/bin/env python3
"""Check one synthetic GFay crossing footprint against complete copied geometry.

The starting point, heading, body/motion envelope and floor face are EXPLICIT
offline hypotheses. They are never current character observations or movement
permission. Every terrain layer remains in occupancy, static and BSP checks.
"""
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys
import time

PROJECT=Path(__file__).resolve().parents[1]
STORE=Path.home()/'.local/share/eql-automation'
HELPER=STORE/'owner-assist/0.39.18'
sys.path[:0]=[str(PROJECT),str(HELPER)]
from eql_automation.map_alignment import _triangle_height
from eql_automation.owner_route_assets import (load_gfay_planner,checked_bytes,TILE_DATA_NAME,
    TILE_MANIFEST_PIN,DATA_PINS)
from eql_automation.pfs_archive import PFSArchive
from eql_automation.route_geometry import RouteGeometryPreparer,RouteMotionBounds
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.wld_inventory import WLDInventory
from eql_automation.zone_line import ExpectedZoneLine
from eqnav.mesh import NavMesh


def run(output):
    if output.exists() or output.is_symlink() or not output.resolve().is_relative_to((STORE/'nav-candidates').resolve()):
        raise ValueError('Use a new private nav-candidates directory')
    pins={p:sha256(p.read_bytes()).hexdigest() for p in
          (Path(__file__),*(PROJECT/'eql_automation').glob('*.py'))}
    helper_manifest=json.loads((HELPER/'SOURCE_HASHES.json').read_text())
    pins[HELPER/'eqnav/mesh.py']=helper_manifest['eqnav/mesh.py']
    def verify():
        if any(p.is_symlink() or sha256(p.read_bytes()).hexdigest()!=h for p,h in pins.items()):
            raise ValueError('Copied crossing probe implementation changed')
    verify();began=time.monotonic()
    root=STORE/'owner-route-data'/TILE_DATA_NAME
    planner=load_gfay_planner(root,tile_rounding=True)
    manifest=checked_bytes(root/'gfaydark.json',TILE_MANIFEST_PIN)
    mesh=NavMesh.load(root/'gfaydark.npz',expected_sha256=DATA_PINS['gfaydark.npz'])
    wld=WLDInventory(PFSArchive(root/'gfaydark.s3d').read_member('gfaydark.wld'))
    line=ExpectedZoneLine.from_sources(crossing_id='copied-gfay-crushbone-fixture',wld=wld,
        bsp=planner.bsp,mesh=mesh,manifest_bytes=manifest,area_id=4)
    if line.polygon_ids!=(19256,) or line.region_ids!=(2884,):
        raise ValueError('Inspected copied crossing inventory differs')
    print('Copied views loaded; checking synthetic crossing footprint.',flush=True)
    bounds=RouteMotionBounds('copied-zone-line-hypotheses','synthetic-motion',
        .01,.1,.2,30.,.4,.01,2.,.1,1.2,6.)
    # A bounded pure geometry probe: no ledger, sender, device or live observer.
    q=RouteGeometryPreparer.__new__(RouteGeometryPreparer)
    q.ground,q.source,q.static,q.bsp=planner.ground,planner.source,planner.static,planner.bsp
    q.vertical_window=3.;q.maximum_source_z_difference=2.;q.precision_policy=planner.precision_policy
    q.expected_zone_line=line
    xy=(-51.,2612.);polygon,z=planner._support(xy)
    seed_id=(1707,28)
    faces=[f for f in planner.source.sources if (f.fragment,f.face)==seed_id]
    if len(faces)!=1:raise ValueError('Explicit copied source-floor fixture missing')
    source_z=_triangle_height(xy[1],xy[0],faces[0].vertices_wld)
    if source_z is None:raise ValueError('Explicit copied source-floor fixture misses XY')
    seed_record=dict(fixture_xy=xy,heading=0.,selected_ids=(seed_id,),source_z=source_z,
        starting_floor_is_offline_hypothesis=True,bounds=asdict(bounds),zone_line=line.record())
    chain=SourceFloorChain(inventory_sha256=wld.sha256,
        seed_evidence_sha256=sha256(json.dumps(seed_record,sort_keys=True).encode()).hexdigest(),
        seed_ids=(seed_id,),body_height=bounds.body_height)
    component=int(planner.ground.components[polygon]);record=dict(seed=seed_record,polygon=polygon,baked_z=z)
    seed=q._trial('pivot',(*xy,z),0.,component,chain,bounds)
    if isinstance(seed,str):record['seed_refusal']=seed
    else:
        chain=seed[2];before=chain.previous.proof_sha256
        start=time.monotonic()
        trial=q._trial('forward',(*xy,z),0.,component,chain,bounds)
        record.update(forward_seconds=time.monotonic()-start,seed_terrain=asdict(seed[3]),
            seed_static=asdict(seed[4]),seed_bsp=asdict(seed[5]))
        if isinstance(trial,str):record['forward_refusal']=trial
        else:
            record.update(footprint=trial[0],terrain=asdict(trial[3]),static=asdict(trial[4]),
                bsp=asdict(trial[5]),fork_index=trial[2].index)
        q.expected_zone_line=None
        denied=q._trial('forward',(*xy,z),0.,component,chain,bounds)
        record['without_expected_line']=denied if isinstance(denied,str) else 'accepted'
        record['original_chain_unchanged']=chain.index==1 and chain.previous.proof_sha256==before
    verify();planner._check_views()
    evidence=dict(format='eql-copied-zone-line-geometry-probe-v1',
        pins={str(p):h for p,h in pins.items()},data_pins=planner.pins,
        expected_zone_line=line.record(),record=record,seconds=time.monotonic()-began,
        simulation_only=True,ledger_sender_test=False,game_input_sent=False,real_client_accepted=False,
        crossing_move_wired=False,destination_verified=False,whole_corridor_clearance_verified=False)
    output.mkdir(parents=True);(output/'executed.py').write_bytes(Path(__file__).read_bytes())
    path=output/'probe.json';path.write_text(json.dumps(evidence,indent=2)+'\n')
    return dict(path=str(path),sha256=sha256(path.read_bytes()).hexdigest(),
        candidate='bsp' in record,refusal=record.get('seed_refusal',record.get('forward_refusal')),
        without_expected_line=record.get('without_expected_line'),
        labelled_regions=record.get('bsp',{}).get('traversal',{}).get('labelled_regions'),
        forward_seconds=record.get('forward_seconds'),real_client_accepted=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    print(json.dumps(run(parser.parse_args().output),indent=2))
