#!/usr/bin/env python3
"""Compare failed baked portal turns with complete copied-source crossings.

This never flattens, edits or waives the baked mesh. It tests a separate local
source-floor hypothesis, including all-height terrain/static occupancy and BSP.
No resulting crossing is an accepted route or a live movement permission.
"""
from dataclasses import asdict
from hashlib import sha256
import argparse
import json
import math
import os
from pathlib import Path
import sys
import time

PROJECT=Path(__file__).resolve().parents[1]
STORE=Path.home()/'.local/share/eql-automation'
HELPER=STORE/'owner-assist/0.39.4'
MESH=STORE/'navmesh/crushbone-detail025-cut-v1/crushbone.npz'
ARCHIVE=STORE/'client-data/retail-full/assets/crushbone.s3d'
OBJECTS=ARCHIVE.with_name('crushbone_obj.s3d')
PINS={MESH:'ba544e96700b51777d81c522c3dd6eba27c4d4a1af387852bf70729086158e56',
      ARCHIVE:'a2591482aac0a478caec1d79bf662a3f0f93d4ef2dc423be8f7591fe6d45e36f',
      OBJECTS:'d80521fdb69c53497d3070b4869dd33ecbdeafdca9ee5f6a3010a93e228f14a5',
      HELPER/'eqnav/zonegeom.py':'bffd21c5767b111f9516180377838d180bf31e3af8e2bc427258c987d6609a60',
      HELPER/'eqnav/mesh.py':'89682ac2f6ee6ad4fc4e4530d946e4d7d883d860573a958d45f7cd7a074fef85'}


def crossing_points(mesh,a,b,fraction,reach):
    matches=[(left,right) for neighbor,left,right in mesh.links[a] if neighbor==b]
    if len(matches)!=1:raise ValueError('Missing or ambiguous directed portal')
    left,right=matches[0]
    center=tuple((1-fraction)*left[k]+fraction*right[k] for k in range(2))
    dx,dy=right[0]-left[0],right[1]-left[1];length=math.hypot(dx,dy)
    if length<=1e-6:raise ValueError('Degenerate portal')
    normal=(-dy/length,dx/length)
    centers=[tuple(sum(float(p[k]) for p in mesh.polys[poly])/len(mesh.polys[poly]) for k in range(2)) for poly in (a,b)]
    if sum(normal[k]*(centers[1][k]-centers[0][k]) for k in range(2))<0:normal=tuple(-n for n in normal)
    return (tuple(center[k]-reach*normal[k] for k in range(2)),center,
            tuple(center[k]+reach*normal[k] for k in range(2)))


def run(output, fractions, reach):
    sys.path[:0]=[str(PROJECT),str(HELPER)]
    from eqnav.mesh import NavMesh
    from eqnav import zonegeom
    from eql_automation.ground_sweep import hull
    from eql_automation.ground_sweep_view import GroundSweepView
    from eql_automation.portal_precision_view import PortalPrecisionView
    from eql_automation.portal_precision import plane
    from eql_automation.map_alignment import _triangle_height
    from eql_automation.pfs_archive import PFSArchive
    from eql_automation.wld_inventory import WLDInventory
    from eql_automation.static_source_view import StaticSourceView
    from eql_automation.source_floor_chain import SourceFloorChain
    from eql_automation.static_floor_guard import check_source_static_floor
    from eql_automation.bsp_floor_guard import check_source_bsp_floor, check_source_body_bsp
    from eql_automation.bsp_volume import BspVolumeView
    from eql_automation.turn_disk_audit import audit_turn_disk
    pins=dict(PINS)
    for p in [Path(__file__),*sorted((PROJECT/'eql_automation').glob('*.py')),*sorted((HELPER/'eqnav').glob('*.py'))]:
        pins.setdefault(p,sha256(p.read_bytes()).hexdigest())
    def verify():
        for p,pin in pins.items():
            if p.is_symlink() or not p.is_file() or sha256(p.read_bytes()).hexdigest()!=pin:
                raise ValueError('Source changed: '+str(p))
    verify();began=time.monotonic()
    mesh=NavMesh.load(MESH)
    source=PortalPrecisionView(GroundSweepView.load(MESH,zone='crushbone'),MESH,ARCHIVE,zone='crushbone')
    archive=PFSArchive(ARCHIVE);terrain=WLDInventory(archive.read_member('crushbone.wld'))
    objects=WLDInventory(archive.read_member('objects.wld'))
    library=WLDInventory(PFSArchive(OBJECTS).read_member('crushbone_obj.wld'))
    static=StaticSourceView.from_wld(objects,(library,),terrain_fragment_max=max(f.index for f in terrain.fragments),
        transform=zonegeom.place_vertices,transform_sha256=pins[HELPER/'eqnav/zonegeom.py'])
    bsp=BspVolumeView.from_wld(terrain)
    radius=1.2;body_height=6.;rows=[]
    for a,b in ((3244,3242),(4316,4315),(658,623)):
        for fraction in fractions:
            if time.monotonic()-began>240:raise TimeoutError('Crossing probe exceeded 240 seconds')
            points=crossing_points(mesh,a,b,fraction,reach)
            row=dict(edge=(a,b),fraction=fraction,points=points,
                baked_turn=asdict(audit_turn_disk(mesh,a,b,points[1],maximum_grade=1.2,max_seconds=10)),
                source_candidate=False,source_occupancy_candidate=False,cells=[])
            rows.append(row)
            def footprint(start,end):
                # Axis-aligned square caps contain the radius-1.2 swept disk.
                return hull((p[0]+dx,p[1]+dy) for p in (start,end) for dx in (-radius,radius) for dy in (-radius,radius))
            initial=footprint(points[0],points[0]);faces=source.source_faces_for_footprint(initial)
            seeds=[]
            for f in faces:
                z=_triangle_height(points[0][1],points[0][0],f.vertices_wld)
                surface=plane(tuple((y,x,z) for x,y,z in f.vertices_wld))
                if z is not None and f.flag==0 and f.material_class=='Diffuse' and surface is not None and math.hypot(*surface[:2])<=1.:
                    seeds.append((z,(f.fragment,f.face)))
            row['source_seed_candidates']=seeds
            if not seeds or max(z for z,_ in seeds)-min(z for z,_ in seeds)>1e-7:
                row['reason']='source_seed_missing_or_layered';continue
            seed=dict(point=points[0],candidates=seeds,selection='unique_walkable_height_at_diagnostic_start_only')
            chain=SourceFloorChain(inventory_sha256=source.wld_sha256,
                seed_evidence_sha256=sha256(json.dumps(seed,sort_keys=True).encode()).hexdigest(),
                seed_ids=(sorted(k for _,k in seeds)[0],),body_height=body_height)
            for start,end in ((points[0],points[0]),(points[0],points[1]),(points[1],points[2])):
                cell=footprint(start,end);sources=source.source_faces_for_footprint(cell)
                step=chain.advance(cell,sources)
                record=dict(footprint=cell,terrain=asdict(step),static=None,bsp=None,expanded_bsp_prism=None)
                row['cells'].append(record)
                if not step.candidate:row['reason']=step.reason;break
                placed=check_source_static_floor(step,cell,sources,static);record['static']=asdict(placed)
                if not placed.candidate:row['reason']=placed.reason;break
                record['expanded_bsp_prism']=asdict(check_source_bsp_floor(step,cell,sources,bsp))
                volume=check_source_body_bsp(step,cell,sources,bsp);record['bsp']=asdict(volume)
                if not volume.candidate:row.setdefault('reason',volume.reason)
            else:
                # Continue terrain diagnostics after a BSP refusal, but never
                # turn that separate evidence into an accepted crossing.
                row['source_occupancy_candidate']=True
                row['source_candidate']=all(cell['bsp']['candidate'] for cell in row['cells'])
                if row['source_candidate']:row['reason']='local_source_crossing_only'
            print(json.dumps({k:row[k] for k in ('edge','fraction','source_candidate','source_occupancy_candidate','reason')}),flush=True)
    verify()
    result=dict(format='eql-crushbone-source-crossings-v1',offline_only=True,game_input_sent=False,
        route_accepted=False,real_client_accepted=False,baked_mesh_modified=False,baked_checks_waived=False,
        hypothetical_body_radius=radius,hypothetical_body_height=body_height,maximum_source_grade=1.,
        source_seed_live_verified=False,center_to_endpoint_distance=reach,
        source_wld_sha256=source.wld_sha256,static_inventory_sha256=static.inventory_sha256,
        static_faces=len(static.sources),placements=len(static.identities),bsp_inventory_sha256=bsp.inventory_sha256,
        rows=rows,source_candidates=sum(r['source_candidate'] for r in rows),
        pins={str(p):v for p,v in pins.items()},seconds=time.monotonic()-began,
        not_checked=['full_camp_route','dynamic_objects_and_enemies','current_player_position','live_body_and_motion','real_movement'])
    with output.open('x') as out:json.dump(result,out,indent=2);out.write('\n')
    print(json.dumps(dict(output=str(output),sha256=sha256(output.read_bytes()).hexdigest(),source_candidates=result['source_candidates'])))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--fractions',type=float,nargs='+',default=[.2,.35,.5,.65,.8,.85])
    parser.add_argument('--reach',type=float,default=3.)
    args=parser.parse_args()
    if (args.output.exists() or args.output.is_symlink()
            or args.output.parent.resolve()!=(STORE/'nav-candidates').resolve()
            or not 1<=len(args.fractions)<=32 or len(set(args.fractions))!=len(args.fractions)
            or any(not math.isfinite(v) or not 0<v<1 for v in args.fractions)
            or not math.isfinite(args.reach) or not .5<=args.reach<=10):
        parser.error('New approved output, bounded unique fractions and reach required')
    os.umask(0o077);os.nice(10)
    run(args.output,args.fractions,args.reach)
