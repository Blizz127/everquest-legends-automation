#!/usr/bin/env python3
"""Compare retained owner G0 heights with copied source terrain and baked ground.

Historical evidence only: no client input, calibration acceptance or movement
permission. Source ground and the navmesh approximation are kept distinct.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

PROJECT=Path(__file__).resolve().parents[1]
STORE=Path.home()/'.local/share/eql-automation'
ALIGNMENT=STORE/'nav-candidates/g0-gfay-mesh-alignment-20261113T2132Z.json'
ARCHIVE=STORE/'client-data/retail-full/assets/gfaydark.s3d'
MESH=STORE/'navmesh/nov12-7e3cd28-store/gfaydark.npz'
PINS={ALIGNMENT:'083b8effbef8966877d01e21f68b666c814a81bd706156999a1d8fcf64b3d06e',
      ARCHIVE:'ea95f51a2d4645410223d24cc7da9eb0e7095310c6e9f8756e8c51d67df13d9f',
      MESH:'5f8e16c5bcd2221ba273f681750ca480349780524d23609c059a3e817df6abd9',
      STORE/'owner-traces/g0-20261113T2122Z-f5d07cd4.jsonl':'f5d07cd4d424bad8b0f494a85cbf389823ee2c3445e497165a20aad9aca1ecc8'}


def run(output):
    sys.path.insert(0,str(PROJECT))
    from eql_automation.bsp_detail_view import BspDetailMeshView
    from eql_automation.portal_surface_audit import _supported_detail_height
    from eql_automation.map_alignment import _triangle_height
    from eql_automation.material_audit import mesh_face_materials
    from eql_automation.mesh_geometry import read_meshes
    from eql_automation.pfs_archive import PFSArchive
    from eql_automation.wld_inventory import WLDInventory
    pins=dict(PINS)
    for name in ('bsp_detail_view','portal_surface_audit','map_alignment','material_audit',
                 'mesh_geometry','pfs_archive','wld_inventory'):
        p=PROJECT/'eql_automation'/(name+'.py');pins[p]=sha256(p.read_bytes()).hexdigest()
    pins[Path(__file__)]=sha256(Path(__file__).read_bytes()).hexdigest()
    def verify():
        if any(p.is_symlink() or sha256(p.read_bytes()).hexdigest()!=h for p,h in pins.items()):
            raise ValueError('G0 comparison input changed')
    verify()
    alignment=json.loads(ALIGNMENT.read_text())
    wld=WLDInventory(PFSArchive(ARCHIVE).read_member('gfaydark.wld'))
    mesh=BspDetailMeshView.load(MESH,zone='gfaydark')
    fragments={f.index:f for f in wld.fragments}
    raw_meshes=read_meshes(wld)
    records=[];seen=set()
    for fix in alignment['fixes']:
        raw=tuple(fix['raw_log_yxz'])
        if raw in seen:continue
        seen.add(raw);hits=[]
        for terrain in raw_meshes:
            vertices=tuple(terrain.vertex(i) for i in range(len(terrain.raw_vertices)))
            materials=None
            for index,face in enumerate(terrain.triangles):
                z=_triangle_height(*raw[:2],tuple(vertices[i] for i in (face.a,face.b,face.c)))
                if z is None:continue
                if materials is None:materials=mesh_face_materials(wld,fragments[terrain.fragment_index])
                hits.append({'fragment':terrain.fragment_index,'face':index,'z':z,'flag':face.flag,
                             'material_class':materials[index].material_class})
        if (not hits or len({round(h['z'],7) for h in hits})!=1
                or any(h['flag']!=0 or h['material_class']!='Diffuse' for h in hits)):
            raise ValueError('Historical G0 source floor is missing or ambiguous')
        source_z=hits[0]['z']
        baked_z=_supported_detail_height(mesh,int(fix['polygon']),raw[1],raw[0])
        if baked_z is None or abs(baked_z-fix['snapped_wld_xyz'][2])>1e-7:
            raise ValueError('Retained G0 mesh height did not reproduce')
        records.append({'raw_log_coordinates':raw,'source_ground_wld_xyz':(*raw[:2],source_z),
            'mesh_ground_package_xyz':(raw[1],raw[0],baked_z),'polygon':fix['polygon'],'source_faces':hits,
            'raw_minus_source_z':raw[2]-source_z,'raw_minus_baked_z':raw[2]-baked_z,
            'baked_minus_source_z':baked_z-source_z})
    if len(records)!=2:raise ValueError('Expected two distinct historical G0 positions')
    verify()
    report={'format':'eql-historical-g0-source-mesh-heights-v1','records':records,
        'raw_source_offset_span':max(r['raw_minus_source_z'] for r in records)-min(r['raw_minus_source_z'] for r in records),
        'raw_baked_offset_span':max(r['raw_minus_baked_z'] for r in records)-min(r['raw_minus_baked_z'] for r in records),
        'source_wld_sha256':wld.sha256,'pins':{str(p):h for p,h in pins.items()},
        'live_alignment_verified':False,'speed_upper_bound_verified':False,
        'game_input_sent':False,'route_accepted':False,'real_client_accepted':False}
    with output.open('x') as out:json.dump(report,out,indent=2);out.write('\n')
    print(json.dumps({'artifact':str(output),'sha256':sha256(output.read_bytes()).hexdigest(),
        'raw_source_offset_span':report['raw_source_offset_span'],'raw_baked_offset_span':report['raw_baked_offset_span']}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output.expanduser()
    if (output.parent.resolve()!=(STORE/'nav-candidates').resolve() or output.exists()
            or output.is_symlink() or output.suffix!='.json'):
        parser.error('Use a new private nav-candidates JSON')
    os.umask(0o077);os.nice(15);run(output)


if __name__=='__main__':main()
