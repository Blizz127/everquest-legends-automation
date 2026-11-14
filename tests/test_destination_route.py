"""Fresh destination planning through the retained NavMesh and real guards."""
from dataclasses import replace
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pytest

from eql_automation.destination_route import plan_destination
from eql_automation.fixed_route_follower import FixedRoute
from eql_automation.portal_precision import SourceFace
from test_current_route_start import fixture, MESH
from test_ground_observer import rectangle


@pytest.fixture
def nav_module():
    path=Path.home()/'.local/share/eql-automation/owner-assist/0.39.15/eqnav/mesh.py'
    info=json.loads((path.parents[1]/'SOURCE_HASHES.json').read_text())
    assert sha256(path.read_bytes()).hexdigest()==info['eqnav/mesh.py']
    name='_destination_retained_mesh'
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def f(tmp_path,nav_module):
    f=fixture(tmp_path,y=4.);p=f.planner
    triangles=np.asarray(rectangle(0.,10.,.6)+rectangle(10.,20.,.6))
    triangles[:,:,1]*=2
    ids=np.asarray([0,0,1,1]);areas=np.asarray([63,63]);components=np.asarray([7,7])
    p.mesh.area=p.ground.areas=areas
    p.mesh._detail=p.ground.triangles=triangles;p.mesh._detail_start=np.asarray([0,2,4])
    p.ground.polys=ids;p.ground.components=components
    p.ground.minimum=triangles.min(axis=1);p.ground.maximum=triangles.max(axis=1)
    source_triangles=tuple(tuple((x,y*2,z) for x,y,z in tri) for tri in rectangle(0.,20.,.2))
    p.source.sources=tuple(SourceFace(tuple((y,x,z) for x,y,z in tri),0,'Diffuse',10,i)
        for i,tri in enumerate(source_triangles))
    xyz=np.asarray(source_triangles)
    p.source.source_minimum=xyz.min(axis=1);p.source.source_maximum=xyz.max(axis=1)
    rings=np.zeros((2,6,3))
    for i,x in enumerate((0.,10.)):
        rings[i,:4]=((x,0.,.6),(x+10,0.,.6),(x+10,8.,.6),(x,8.,.6))
    portals=np.asarray([((10.,0.,.6),(10.,8.,.6)),((10.,8.,.6),(10.,0.,.6))])
    nav=nav_module.NavMesh(rings,np.asarray([4,4]),areas,np.asarray([0,1]),np.asarray([1,0]),
        portals,triangles,ids,component=components)
    nav.sha256=MESH
    f.nav=nav;f.goal=(16.,4.)
    f.destination_options={k:v for k,v in f.options.items() if k!='length'}
    f.plan_destination=lambda:plan_destination(p,nav,f.reader,f.a,f.b,goal_xy=f.goal,
                                               **f.destination_options)
    return f


def test_destination_preserves_current_start_and_initial_chain(f,tmp_path):
    plan=f.plan_destination()
    assert len(plan.route.segments)==2
    assert plan.route.segments[0].start==(4.,4.,.6)
    assert plan.route.segments[-1].end==(16.,4.,.6)
    assert plan.route.segments[0].end==plan.route.segments[1].start
    assert plan.observer.geometry.verified_portal_pairs==((0,1),)
    assert plan.observer.links==frozenset(((0,1),(1,0)))
    assert plan.floor_chain.index==1 and plan.floor_chain.previous.candidate
    proof=json.loads(plan.evidence_bytes)
    assert not proof['whole_corridor_clearance_verified']
    assert proof['future_geometry_requires_runtime_checks']
    assert proof['initial_chain_proof']==plan.floor_chain.previous.proof_sha256
    assert plan.observer.geometry.same_floor_evidence_sha256==sha256(plan.evidence_bytes).hexdigest()
    out=tmp_path/'plan.json';out.write_bytes(plan.plan_bytes)
    assert FixedRoute.load(out,expected_sha256=plan.route.artifact_sha256,mesh_sha256=MESH)==plan.route


@pytest.mark.parametrize('change',['wrong_hash','nonreciprocal','duplicate','shifted_reverse','closed','foreign_component',
                                 'snap_start','snap_goal','different_start_floor','owner_after_search','expired_after_search'])
def test_unbound_or_changed_corridor_refused(f,change):
    original=f.nav.find_path
    def search(*args,**kwargs):
        result=original(*args,**kwargs)
        if change=='snap_start':return replace(result,points=((4.01,4.,.6),*result.points[1:]))
        if change=='snap_goal':return replace(result,points=(*result.points[:-1],(16.01,4.,.6)))
        if change=='different_start_floor':return replace(result,polys=(1,1))
        if change=='owner_after_search':f.owner=('changed',)
        if change=='expired_after_search':f.now+=121.
        return result
    f.nav.find_path=search
    if change=='wrong_hash':f.nav.sha256='f'*64
    elif change=='nonreciprocal':f.nav.links[1]=[]
    elif change=='duplicate':f.nav.links[0].append(f.nav.links[0][0])
    elif change=='shifted_reverse':
        f.nav.links[1]=[(0,(13.,0.,.6),(13.,8.,.6))]
    elif change=='closed':f.planner.ground.areas[1]=1
    elif change=='foreign_component':f.planner.ground.components[1]=8
    with pytest.raises((ValueError,RuntimeError)):
        f.plan_destination()


def test_untraversed_static_obstacle_is_not_claimed_clear(f):
    wall=SourceFace(((0.,12.,0.),(4.,12.,0.),(2.,12.,8.)),0,'Diffuse',20,0)
    f.planner.static.faces_for_footprint=lambda footprint:(wall,) if max(x for x,y in footprint)>=12 else ()
    plan=f.plan_destination()
    assert len(plan.route.segments)==2 and plan.floor_chain.index==1
    assert not json.loads(plan.evidence_bytes)['whole_corridor_clearance_verified']
