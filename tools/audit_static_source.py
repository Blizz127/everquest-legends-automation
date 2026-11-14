#!/usr/bin/env python3
"""Compare a copied GFay static-face inventory with its retained bake input.

No client, device, server or install is opened. Data stays in the private store.
This checks transformed source parity, not real collision or route acceptance.
"""
from collections import Counter
from hashlib import sha256
import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
STORE=Path.home()/'.local/share/eql-automation'
HELPER=STORE/'owner-assist/0.39.4'
ASSETS=STORE/'client-data/retail-full/assets'
PINS={ASSETS/'gfaydark.s3d':'ea95f51a2d4645410223d24cc7da9eb0e7095310c6e9f8756e8c51d67df13d9f',
      ASSETS/'gfaydark_obj.s3d':'3439c59e9c6c1623e85b29694d6a6161b924b0a9ece39751b0234ab5c6f71892',
      HELPER/'eqnav/zonegeom.py':'bffd21c5767b111f9516180377838d180bf31e3af8e2bc427258c987d6609a60'}


def run(output):
    import numpy as np
    sys.path[:0]=[str(ROOT),str(HELPER)]
    from eql_automation.static_source_view import StaticSourceView
    from eql_automation.pfs_archive import PFSArchive
    from eql_automation.wld_inventory import WLDInventory
    from eqnav import zonegeom
    began=time.monotonic();pins=dict(PINS)
    for name in ('static_source_view','material_audit','mesh_geometry','model_links',
                 'placement_audit','portal_precision','pfs_archive','wld_inventory'):
        p=ROOT/'eql_automation'/(name+'.py');pins[p]=sha256(p.read_bytes()).hexdigest()
    for name in ('wld.py','pfs.py'):
        p=HELPER/'eqnav'/name;pins[p]=sha256(p.read_bytes()).hexdigest()
    pins[Path(__file__)]=sha256(Path(__file__).read_bytes()).hexdigest()
    def verify():
        if any(p.is_symlink() or sha256(p.read_bytes()).hexdigest()!=h for p,h in pins.items()):
            raise ValueError('Pinned static-source input changed')
    verify()
    main=PFSArchive(ASSETS/'gfaydark.s3d');obj=PFSArchive(ASSETS/'gfaydark_obj.s3d')
    terrain=WLDInventory(main.read_member('gfaydark.wld'))
    objects=WLDInventory(main.read_member('objects.wld'))
    library=WLDInventory(obj.read_member('gfaydark_obj.wld'))
    view=StaticSourceView.from_wld(objects,(library,),
        terrain_fragment_max=max(f.index for f in terrain.fragments),
        transform=zonegeom.place_vertices,transform_sha256=pins[HELPER/'eqnav/zonegeom.py'])
    geometry=zonegeom.load_zone_geometry(ASSETS,'gfaydark',convention='model')
    for name,digest in geometry.sources.items():
        if pins.get(ASSETS/name)!=digest:raise ValueError('Retained geometry used an unpinned archive')
    our=np.asarray([f.vertices_wld for f in view.sources if f.flag==0],dtype=np.float32)[:,:,[1,0,2]]
    cross=np.cross(our[:,1].astype(np.float64)-our[:,0],our[:,2].astype(np.float64)-our[:,0])
    keep=(cross*cross).sum(axis=1)>zonegeom.ZERO_AREA
    ours=our[keep]
    object_ids=[i for i,g in enumerate(geometry.groups) if g.kind=='object']
    expected=geometry.triangles[np.isin(geometry.group_ids,object_ids)]
    keys=lambda triangles:Counter(np.ascontiguousarray(t,dtype='<f4').tobytes() for t in triangles)
    actual_keys,expected_keys=keys(ours),keys(expected)
    matches=actual_keys==expected_keys
    proof={'format':'eql-static-source-parity-v1','zone':'gfaydark','offline_only':True,
           'game_input_sent':False,'route_accepted':False,'real_client_accepted':False,
           'full_collision_inventory_verified':False,'dynamics_included':False,
           'inventory_sha256':view.inventory_sha256,'static_source_faces':len(view.sources),
           'placement_count':len(view.identities),'excluded_placements':view.excluded,
           'models':len({(i['model_wld_sha256'],i['mesh_fragment']) for i in view.identities.values()}),
           'flag_counts':dict(sorted(Counter(f.flag for f in view.sources).items())),
           'material_counts':dict(sorted(Counter(f.material_class for f in view.sources).items())),
           'source_face_identity_scope':'terrain-max+sorted-instance surrogate; original model triangle index',
           'members':{'gfaydark.wld':terrain.sha256,'objects.wld':objects.sha256,'gfaydark_obj.wld':library.sha256},
           'exact_transformed_solid_multiset_matches_retained_baker':matches,
           'comparable_static_faces':len(ours),'retained_static_faces':len(expected),
           'solid_zero_area_removed_only_for_parity':int((~keep).sum()),
           'missing_from_adapter':sum((expected_keys-actual_keys).values()),
           'extra_in_adapter':sum((actual_keys-expected_keys).values()),
           'retained_scene_stats':geometry.stats,
           'not_checked':['integration_into_floor_trials','whole_route_static_occupancy','live_transform_or_collision'],
           'pins':{str(p):h for p,h in pins.items()},'seconds':time.monotonic()-began}
    verify()
    with output.open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
    print(json.dumps({'matches':matches,'static_faces':len(view.sources),'placements':len(view.identities),
        'excluded':len(view.excluded),'bake_comparable_faces':len(ours),'artifact':str(output),
        'sha256':sha256(output.read_bytes()).hexdigest(),'seconds':proof['seconds']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();output=args.output.expanduser()
    if (output.parent.resolve()!=(STORE/'nav-candidates').resolve()
            or output.is_symlink() or output.exists() or output.suffix!='.json'):
        parser.error('Use a new regular JSON file directly in private nav-candidates')
    os.umask(0o077);os.nice(15);run(output)
