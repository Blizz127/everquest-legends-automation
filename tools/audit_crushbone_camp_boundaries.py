#!/usr/bin/env python3
"""Inventory exact projected boundaries incident to isolated camp components.

This linear source inventory plus bounded incident-pair scan performs no route
search, bake, collision acceptance or input. Zero-gap partial edges are retained
as diagnostics, rather than silently discarded by nonzero step discovery.
"""
from collections import Counter,defaultdict
from fractions import Fraction
from hashlib import sha256
from itertools import combinations
from pathlib import Path
import argparse
import json
import math
import os
import sys
import time

PROJECT=Path(__file__).resolve().parents[1]
STORE=Path('/home/blizz/.local/share/eql-automation')
sys.path.insert(0,str(PROJECT))

from eql_automation.crushbone_assets import DATA_NAME,DATA_PINS,WLD_PIN
from eql_automation.material_audit import mesh_face_materials
from eql_automation.mesh_geometry import read_meshes
from eql_automation.pfs_archive import PFSArchive
from eql_automation.portal_precision import SourceFace
from eql_automation.source_floor_chain import rational
from eql_automation.source_floor_components import SourceFloorComponents
from eql_automation.source_step_links import _at,_cross
from eql_automation.wld_inventory import WLDInventory


def inventory(sources,pin,components,*,max_pairs=100_000):
    graph=SourceFloorComponents(sources,inventory_sha256=pin)
    selected=set(components)
    if not selected<=set(graph.components.values()):raise ValueError('Requested component is absent')
    edges=defaultdict(list);all_edges=defaultdict(list)
    for source in sources:
        identity=(source.fragment,source.face)
        points=rational(tuple((y,x,z) for x,y,z in source.vertices_wld))
        for i,a in enumerate(points):
            b,third=points[(i+1)%3],points[(i+2)%3]
            key=tuple(sorted((a,b)))
            all_edges[key].append((identity,source.flag,source.material_class))
            if identity in graph.components and a[:2]!=b[:2]:
                edges[key].append((identity,a,b,third))
    lines=defaultdict(list);boundaries=[]
    for edge,owners in edges.items():
        if len(owners)!=1:continue
        identity,a,b,third=owners[0]
        axis=0 if abs(b[0]-a[0])>=abs(b[1]-a[1]) else 1
        slope=(b[1-axis]-a[1-axis])/(b[axis]-a[axis]);intercept=a[1-axis]-slope*a[axis]
        lines[(axis,slope,intercept)].append(owners[0])
        if graph.components[identity] in selected:
            boundaries.append(dict(face=identity,component=graph.components[identity],
                edge=[[str(v) for v in p] for p in edge],all_full_edge_owners=all_edges[edge]))
    rows=[];pairs=0;incident_lines=0
    for (axis,slope,intercept),members in sorted(lines.items()):
        if not any(graph.components[v[0]] in selected for v in members):continue
        incident_lines+=1
        for left,right in combinations(sorted(members),2):
            fa,a,b,third_a=left;fb,c,d,third_b=right
            ca,cb=graph.components[fa],graph.components[fb]
            if not (ca in selected or cb in selected) or ca==cb:continue
            pairs+=1
            if pairs>max_pairs:raise ValueError('Incident pair budget exceeded')
            lo=max(min(a[axis],b[axis]),min(c[axis],d[axis]))
            hi=min(max(a[axis],b[axis]),max(c[axis],d[axis]))
            if lo>=hi:continue
            opposite=_cross(a,b,third_a)*_cross(a,b,third_b)<0
            gl=_at((c,d),axis,lo)[2]-_at((a,b),axis,lo)[2]
            gh=_at((c,d),axis,hi)[2]-_at((a,b),axis,hi)[2]
            width=float(hi-lo)*math.sqrt(1+float(slope)**2)
            # Report exact nonzero intervals admitted by the existing 2-unit,
            # 2.404-wide discovery model, without any cap/occupancy approval.
            cuts={lo,hi}
            if gl!=gh:
                for height in (Fraction(-2),Fraction(0),Fraction(2)):
                    root=lo+(height-gl)*(hi-lo)/(gh-gl)
                    if lo<root<hi:cuts.add(root)
            segments=[]
            ordered=sorted(cuts)
            for start,end in zip(ordered,ordered[1:]):
                gap=gl+(gh-gl)*(((start+end)/2-lo)/(hi-lo))
                span=float(end-start)*math.sqrt(1+float(slope)**2)
                reason=('same_side' if not opposite else 'zero_height_gap' if gap==0
                    else 'height_over_two' if abs(gap)>2 else 'width_under_2.404' if span<2.404
                    else 'nonzero_step_proposal')
                segments.append(dict(interval=[str(start),str(end)],width=span,reason=reason))
            rows.append(dict(from_face=fa,to_face=fb,from_component=ca,to_component=cb,
                axis=axis,line_slope=str(slope),line_intercept=str(intercept),
                from_edge=[[str(v) for v in p] for p in (a,b)],to_edge=[[str(v) for v in p] for p in (c,d)],
                overlap=[str(lo),str(hi)],width=width,height_gaps=[str(gl),str(gh)],
                opposite_interiors=opposite,intervals=segments))
    return dict(source_faces=len(sources),eligible_faces=graph.face_count,
        selected_component_faces={str(c):sum(v==c for v in graph.components.values()) for c in components},
        incident_lines=incident_lines,examined_pairs=pairs,boundaries=boundaries,pairs=rows,
        interval_reasons=dict(Counter(s['reason'] for r in rows for s in r['intervals'])))


def run(output,components):
    started=time.monotonic();root=STORE/'owner-route-data'/DATA_NAME
    code_pins={str(p):sha256(p.read_bytes()).hexdigest() for p in
        (Path(__file__),*sorted((PROJECT/'eql_automation').glob('*.py')))}
    archive=PFSArchive(root/'crushbone.s3d')
    if archive.sha256!=DATA_PINS['crushbone.s3d']:raise ValueError('Copied archive changed')
    wld=WLDInventory(archive.read_member('crushbone.wld'))
    if wld.sha256!=WLD_PIN:raise ValueError('Copied terrain changed')
    fragments={f.index:f for f in wld.fragments};sources=[]
    for mesh in read_meshes(wld):
        materials=mesh_face_materials(wld,fragments[mesh.fragment_index])
        vertices=tuple(mesh.vertex(i) for i in range(len(mesh.raw_vertices)))
        for index,face in enumerate(mesh.triangles):
            sources.append(SourceFace(tuple(vertices[i] for i in (face.a,face.b,face.c)),
                face.flag,materials[index].material_class,mesh.fragment_index,index))
    result=inventory(tuple(sources),wld.sha256,components)
    if any(sha256(Path(p).read_bytes()).hexdigest()!=pin for p,pin in code_pins.items()):
        raise ValueError('Diagnostic implementation changed during inventory')
    result.update(format='eql-offline-camp-boundaries-v1',source_archive_sha256=archive.sha256,
        source_wld_sha256=wld.sha256,seconds=time.monotonic()-started,
        code_sha256=code_pins[str(Path(__file__))],code_pins=code_pins,complete=True,
        source_occupancy_checked=False,static_support_checked=False,
        route_accepted=False,physical_disconnection_proven=False,game_input_sent=False)
    with output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(dict(output=str(output),sha256=sha256(output.read_bytes()).hexdigest(),
        seconds=result['seconds'],pairs=len(result['pairs']),interval_reasons=result['interval_reasons'])))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--component',type=int,nargs=2,action='append',metavar=('FRAGMENT','FACE'))
    args=parser.parse_args()
    if (args.output.exists() or args.output.is_symlink()
            or args.output.parent.resolve()!=(STORE/'nav-candidates').resolve()):
        parser.error('Use a new file under the private nav-candidates store')
    components=tuple(tuple(c) for c in (args.component or ((454,2),(937,6))))
    if not 1<=len(set(components))==len(components)<=16:parser.error('Need one to sixteen distinct components')
    os.umask(0o077);os.nice(10);run(args.output,components)
