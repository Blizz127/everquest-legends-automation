#!/usr/bin/env python3
"""Audit the copied Crushbone graph detour with continuous source-body cells.

The graph supplies only XY waypoints. Actual supporting floor, terrain/static
occupancy and above-support BSP volumes are checked anew for every full cell.
This does not rewrite baked heights or enable a client route.
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

from audit_crushbone_source_crossings import PROJECT,STORE,HELPER,MESH,ARCHIVE,OBJECTS,PINS

ENDPOINTS=STORE/'nav-candidates/crushbone-detail025-avoid-658-623-route-0.41.39.json'
CROSSING=STORE/'nav-candidates/crushbone-source-body-crossings-0.41.98.json'


def run(output, *, repair_raised_corner=False):
    sys.path[:0]=[str(PROJECT),str(HELPER)]
    from eqnav.mesh import NavMesh
    from eqnav import zonegeom
    from eql_automation.graph_cut_audit import ground_reachability
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
    from eql_automation.bsp_floor_guard import check_source_body_bsp
    from eql_automation.bsp_volume import BspVolumeView
    pins=dict(PINS)
    pins[ENDPOINTS]='5762a13cf23d5b3a957d7e896662ff114700a1711c3d42cbe644f1a4eb15d9ad'
    pins[CROSSING]='b14bed5ed58a855e01eba453280660a708759ec2a727353f9d5215ffad5f9435'
    for p in [Path(__file__),Path(__file__).with_name('audit_crushbone_source_crossings.py'),
              *sorted((PROJECT/'eql_automation').glob('*.py')),*sorted((HELPER/'eqnav').glob('*.py'))]:
        pins.setdefault(p,sha256(p.read_bytes()).hexdigest())
    def verify():
        for p,pin in pins.items():
            if p.is_symlink() or not p.is_file() or sha256(p.read_bytes()).hexdigest()!=pin:
                raise ValueError('Source pin changed: '+str(p))
    verify();began=time.monotonic()
    parent=json.loads(CROSSING.read_text())
    assert any(r['edge']==[658,623] and r['fraction']==.5 and r['source_candidate'] for r in parent['rows'])
    mesh=NavMesh.load(MESH)
    graph=ground_reachability(mesh,2241,3799,blocked=frozenset({3244}))
    assert graph.reachable and len(graph.path)==174 and 4316 not in graph.path
    edges=tuple(zip(graph.path,graph.path[1:]));assert (658,623) in edges
    endpoints=json.loads(ENDPOINTS.read_text())
    points=[tuple(endpoints['start_wld_xyz'][:2])]
    for a,b in edges:
        links=[(l,r) for n,l,r in mesh.links[a] if n==b]
        if len(links)!=1:raise ValueError('Missing or ambiguous portal')
        l,r=links[0];points.append(tuple((l[k]+r[k])/2 for k in range(2)))
    points.append(tuple(endpoints['goal_wld_xyz'][:2]))
    segment_polygons=list(graph.path)
    if repair_raised_corner:
        # The retained segment-70 midpoint guide clips a real raised corner.
        # This candidate goes north of it. Recheck every cell; it grants no
        # exemption for the following obstacle or any BSP refusal.
        assert segment_polygons[70]==440
        points.insert(71,(-177.,72.5))
        segment_polygons.insert(71,440)
    source=PortalPrecisionView(GroundSweepView.load(MESH,zone='crushbone'),MESH,ARCHIVE,zone='crushbone')
    archive=PFSArchive(ARCHIVE);terrain=WLDInventory(archive.read_member('crushbone.wld'))
    static=StaticSourceView.from_wld(WLDInventory(archive.read_member('objects.wld')),
        (WLDInventory(PFSArchive(OBJECTS).read_member('crushbone_obj.wld')),),
        terrain_fragment_max=max(f.index for f in terrain.fragments),transform=zonegeom.place_vertices,
        transform_sha256=pins[HELPER/'eqnav/zonegeom.py'])
    bsp=BspVolumeView.from_wld(terrain)
    radius=1.2;body=6.
    def footprint(a,b):
        return hull((p[0]+dx,p[1]+dy) for p in (a,b) for dx in (-radius,radius) for dy in (-radius,radius))
    initial=footprint(points[0],points[0]);sources=source.source_faces_for_footprint(initial)
    seeds=[]
    for f in sources:
        z=_triangle_height(points[0][1],points[0][0],f.vertices_wld)
        surface=plane(tuple((y,x,z) for x,y,z in f.vertices_wld))
        if z is not None and f.flag==0 and f.material_class=='Diffuse' and surface is not None and math.hypot(*surface[:2])<=1.:
            seeds.append((z,(f.fragment,f.face)))
    if not seeds or max(z for z,_ in seeds)-min(z for z,_ in seeds)>1e-7:
        raise ValueError('Diagnostic start has missing/layered source floor')
    seed=dict(point=points[0],candidates=seeds,selection='unique_walkable_height_at_historical_guide_only')
    chain=SourceFloorChain(inventory_sha256=source.wld_sha256,
        seed_evidence_sha256=sha256(json.dumps(seed,sort_keys=True).encode()).hexdigest(),
        seed_ids=(sorted(k for _,k in seeds)[0],),body_height=body)
    record=dict(format='eql-crushbone-source-corridor-v1',offline_only=True,
        source_route_candidate=False,source_occupancy_candidate=False,bsp_refusals=[],route_accepted=False,real_client_accepted=False,game_input_sent=False,
        graph=asdict(graph),waypoints=points,segment_polygons=segment_polygons,
        repair_raised_corner=repair_raised_corner,source_seed=seed,source_seed_live_verified=False,
        source_wld_sha256=source.wld_sha256,static_inventory_sha256=static.inventory_sha256,
        bsp_inventory_sha256=bsp.inventory_sha256,hypothetical_body_radius=radius,hypothetical_body_height=body,
        maximum_source_grade=1.,maximum_cell_length=2.,baked_mesh_modified=False,
        bsp_scope='above_each_verified_source_floor_patch; below-floor BSP remains unclassified',
        pins={str(p):h for p,h in pins.items()},cells=[],status='checking',completed=False)
    def save():
        record['seconds']=time.monotonic()-began
        temporary=output.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(record,indent=2)+'\n');temporary.replace(output)
    def check(index,division,cell):
        if time.monotonic()-began>240:raise TimeoutError('Source corridor work budget exceeded')
        sources=source.source_faces_for_footprint(cell)
        step=chain.advance(cell,sources)
        item=dict(segment=index,division=division,polygon=None if index<0 else segment_polygons[index],
                  footprint=cell,terrain=asdict(step),static=None,bsp=None)
        record['cells'].append(item)
        if not step.candidate:record['reason']=step.reason;return False
        placed=check_source_static_floor(step,cell,sources,static);item['static']=asdict(placed)
        if not placed.candidate:record['reason']=placed.reason;return False
        volume=check_source_body_bsp(step,cell,sources,bsp);item['bsp']=asdict(volume)
        if not volume.candidate:
            record['bsp_refusals'].append(dict(segment=index,division=division,reason=volume.reason))
        return True
    save()
    try:
        okay=check(-1,0,initial)
        for index,(a,b) in enumerate(zip(points,points[1:])):
            if not okay:break
            count=max(1,math.ceil(math.dist(a,b)/2.))
            for j in range(count):
                start=tuple(a[k]+(b[k]-a[k])*j/count for k in range(2))
                end=tuple(a[k]+(b[k]-a[k])*(j+1)/count for k in range(2))
                if not check(index,j,footprint(start,end)):okay=False;break
            if index%20==0:
                save();print(json.dumps(dict(segment=index,cells=len(record['cells']),candidate=okay)),flush=True)
        record.update(source_occupancy_candidate=okay,source_route_candidate=okay and not record['bsp_refusals'],status='checked',completed=True)
        if okay and record['bsp_refusals']:record['reason']='source_body_bsp_refused'
    except (ValueError,TimeoutError) as error:
        record.update(status='refused',reason=str(error),completed=True)
    verify();save()
    print(json.dumps(dict(output=str(output),sha256=sha256(output.read_bytes()).hexdigest(),
        source_route_candidate=record['source_route_candidate'],cells=len(record['cells']),reason=record.get('reason'),
        last_checked_polygon=record['cells'][-1]['polygon'],
        first_bsp_refusal=next(iter(record['bsp_refusals']),None))))
    return record


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--repair-raised-corner',action='store_true',
                        help='Test the source-supported polygon-440 waypoint alternative')
    args=parser.parse_args()
    if args.output.exists() or args.output.is_symlink() or args.output.parent.resolve()!=(STORE/'nav-candidates').resolve():
        parser.error('Use a new output directly in approved nav-candidates store')
    os.umask(0o077);os.nice(10);run(args.output,repair_raised_corner=args.repair_raised_corner)
