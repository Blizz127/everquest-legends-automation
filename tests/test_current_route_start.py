"""Current-start producer over synthetic complete views and a real log reader."""
from dataclasses import replace
from datetime import datetime, timedelta
from hashlib import sha256
import json
from types import SimpleNamespace

import numpy as np
import pytest

from eql_automation.bsp_detail_view import BspDetailMeshView
from eql_automation.bsp_volume import BspVolumeView
from eql_automation.current_route_start import CurrentStartPlanner
from eql_automation.fixed_route_follower import FixedRoute, FixedRouteFollower
from eql_automation.ground_sweep_view import GroundSweepView
from eql_automation.location_log import LocationLogReader
from eql_automation.observed_height import measure_current_height
from eql_automation.portal_precision import SourceFace
from eql_automation.portal_precision_view import PortalPrecisionView
from eql_automation.route_geometry import RouteMotionBounds
from test_ground_observer import rectangle
from test_route_floor_commit import legacy

MESH, ARCHIVE, WLD, STATIC = (v*64 for v in 'abcd')


def fixture(tmp_path, *, x=4., y=2., hole=False, duplicate=False, water=False,
            wall=False, source_layer=False, gap=False):
    # Translate the whole fixture: there is no historical route start here.
    dx = x-4.
    def rect(a, b, z):
        return tuple(tuple((p[0]+dx, p[1], p[2]) for p in tri) for tri in rectangle(a,b,z))
    detail = rect(0, 10, .6)
    if hole:
        # Endpoint XY still has support; missing interior horizontal strip.
        detail = tuple(tuple((p[0], p[1]*.6, p[2]) for p in tri) for tri in detail) + tuple(
            tuple((p[0], 2.6+p[1]*.35, p[2]) for p in tri) for tri in detail)
    if gap:
        detail = rect(0, 3.99999, .6)+rect(4.00001,10,.6)
    layer = rect(0,10,12.) if duplicate else ()
    triangles = np.asarray(detail+layer)
    ids = np.asarray([0]*len(detail)+[1]*len(layer))
    areas = np.asarray([63,63] if duplicate else [63]); components=np.asarray([7]*len(areas))
    ground = GroundSweepView(triangles,ids,areas,components);ground.mesh_sha256=MESH
    mesh = BspDetailMeshView(areas,triangles,np.asarray([0,len(detail),len(triangles)] if duplicate else [0,len(detail)]))
    mesh.mesh_sha256=MESH
    source = PortalPrecisionView.__new__(PortalPrecisionView)
    source.ground=ground;source.mesh_sha256=MESH;source.archive_sha256=ARCHIVE;source.wld_sha256=WLD
    source.seams=();source.by_polygon={}
    sources = rect(0,10,.2)+(rect(0,10,10.) if source_layer else ())
    source.sources=tuple(SourceFace(tuple((p[1],p[0],p[2]) for p in tri),0,'Diffuse',10,i)
                         for i,tri in enumerate(sources))
    coords=np.asarray(sources);source.source_minimum=coords.min(axis=1);source.source_maximum=coords.max(axis=1)
    static_faces=(SourceFace(((2.7,x-1.,0.),(2.7,x+1.,0.),(2.7,x,4.)),
                             0,'Diffuse',20,0),) if wall else ()
    static=SimpleNamespace(inventory_sha256=STATIC,faces_for_footprint=lambda _:static_faces)
    bsp=BspVolumeView(SimpleNamespace(nodes=((0.,0.,0.,0.,1,0,0),),
        labels_by_region={0:{'water'}} if water else {}),region_count=1,wld_sha256=WLD)
    planner=CurrentStartPlanner(mesh=mesh,ground=ground,source=source,static=static,bsp=bsp,
        zone_short_name='fixture',expected_zone_id=54,expected_zone_name='Fixture',
        mesh_sha256=MESH,source_archive_sha256=ARCHIVE,source_wld_sha256=WLD,static_inventory_sha256=STATIC)
    f=SimpleNamespace(now=100.,owner=('game','Probe'),planner=planner)
    f.clock=lambda:f.now;f.wall=lambda:datetime(2026,11,14,12)+timedelta(seconds=f.now-100.)
    log=tmp_path/'eqlog_Probe_private.txt';log.touch()
    names=tmp_path/'ZoneNames.txt';names.write_text('54^Fixture^0^0\n')
    reader=LocationLogReader(log,names,expected_character='Probe',expected_server='private')
    def append(body):
        with log.open('a') as out:out.write(f.wall().strftime('[%a %b %d %H:%M:%S %Y] ')+body+'\n')
    append('You have entered Fixture.');reader.poll(now=f.now)
    def position():
        append(f'Your Location is {y:.2f}, {x:.2f}, 2.70')
        return reader.poll(now=f.now)[0]
    a=position();f.now+=.5;b=position()
    bounds=RouteMotionBounds('explicit-hypotheses','same-session-motion',.01,.05,.1,
        30.,.02,.01,1.,.01,.1,6.)
    f.reader,f.a,f.b,f.position,f.append=reader,a,b,position,append
    f.options=dict(heading=0.,motion_record_id='same-session-motion',bounds=bounds,length=.75,
        half_width=.3,vertical_window=1.,maximum_source_z_difference=1.,
        owner_binding=f.owner,binding_reader=lambda:f.owner,released_at=99.8,
        record_id='current-start-fixture',clock=f.clock,local_wall_clock=f.wall)
    f.plan=lambda:planner.plan(reader,f.a,f.b,**f.options)
    return f


def test_translated_current_start_preserves_xy_and_builds_fresh_proof(tmp_path):
    f=fixture(tmp_path,x=1004.)
    result=f.plan();r=result.route
    assert r.segments[0].start==(1004.,2.,.6) and r.segments[0].end==(1004.,2.75,.6)
    assert f.b.raw_coordinates==(2.,1004.,2.7)
    assert result.observer.source.source_floor_at((1004.,2.))[0]==.2
    evidence=json.loads(result.evidence_bytes)
    assert r.artifact_sha256==sha256(result.plan_bytes).hexdigest()
    assert result.observer.geometry.same_floor_evidence_sha256==sha256(result.evidence_bytes).hexdigest()
    assert all(evidence[k]['candidate'] for k in ('terrain','static','bsp'))
    assert result.observer.geometry.verified_portal_pairs==()
    assert result.floor_chain.previous.candidate and result.floor_chain.index==1
    assert result.requires_fresh_start_pair and not result.input_authorized and not result.real_client_accepted


def test_large_polygon_uses_every_local_triangle_without_remote_budget_charge(tmp_path):
    f=fixture(tmp_path);p=f.planner
    remote=[]
    for i in range(60):
        remote.extend(tuple(tuple((v[0]+100.+i*10.,v[1],v[2]) for v in t)
                            for t in rectangle(0.,10.)))
    triangles=np.concatenate((p.ground.triangles,np.asarray(remote)))
    p.ground.triangles=triangles;p.ground.polys=np.zeros(len(triangles),dtype=np.int64)
    p.ground.minimum=triangles.min(axis=1);p.ground.maximum=triangles.max(axis=1)
    p.mesh._detail=triangles;p.mesh._detail_start=np.asarray([0,len(triangles)])
    result=f.plan()
    assert result.floor_chain.previous.candidate
    assert json.loads(result.evidence_bytes)['selected_coverage']['used_faces']<=2


@pytest.mark.parametrize('kind,reason',[
    ('duplicate','uniquely supported'),('source_layer','layered'),
    ('hole','capsule'),('gap','uniquely supported'),('wall','static geometry'),('water','BSP')])
def test_full_inventory_or_interior_refusal_even_with_clear_endpoints(tmp_path,kind,reason):
    f=fixture(tmp_path,**{kind:True})
    before=f.planner.source.sources
    with pytest.raises(ValueError,match=reason):f.plan()
    assert f.planner.source.sources is before and f.reader.latest is f.b


@pytest.mark.parametrize('change',['stale','unbound','zone','nonconsecutive','moving',
    'owner','source','static','reader','budget','motion','nonfinite','too_short'])
def test_invalid_or_changed_start_never_produces_a_plan(tmp_path,change):
    f=fixture(tmp_path)
    if change=='stale':f.now+=.51
    elif change=='unbound':f.b=object()
    elif change=='zone':f.reader.zone_id=99
    elif change=='nonconsecutive':f.a=replace(f.a,log_line_seq=f.a.log_line_seq-1)
    elif change=='moving':f.a=replace(f.a,raw_coordinates=(3.,4.,2.7))
    elif change=='owner':f.owner=('other',)
    elif change=='source':f.planner.source.wld_sha256='f'*64
    elif change=='static':f.planner.static.inventory_sha256='f'*64
    elif change=='reader':f.reader.latest=None
    elif change=='motion':f.options['motion_record_id']='other-session'
    elif change=='nonfinite':f.options['heading']=float('nan')
    elif change=='too_short':f.options['length']=.5
    elif change=='budget':
        original=f.planner.source.source_faces_for_footprint
        def slow(footprint):
            f.now+=11
            return original(footprint)
        f.planner.source.source_faces_for_footprint=slow
    with pytest.raises((ValueError,AttributeError)):f.plan()


def test_shared_source_edge_keeps_all_seeds(tmp_path):
    f=fixture(tmp_path,x=6.)
    # At y=2, the source diagonal is dx+5, so use a fresh centered pair.
    f.a=replace(f.a,raw_coordinates=(2.,7.,2.7))
    f.b=replace(f.b,raw_coordinates=(2.,7.,2.7));f.reader.latest=f.b
    result=f.plan()
    assert result.floor_chain.seed_ids==((10,0),(10,1))


@pytest.mark.parametrize('change',['deadline','pins','clock_backwards'])
def test_final_binding_callback_cannot_return_stale_plan(tmp_path,change):
    f=fixture(tmp_path);calls=[]
    def binding():
        calls.append(1)
        if len(calls)==3:
            if change=='deadline':f.now+=11
            elif change=='pins':f.planner.source.wld_sha256='f'*64
            else:f.now-=.01
        return f.owner
    f.options['binding_reader']=binding
    with pytest.raises(ValueError):f.plan()
    assert len(calls)==3


def test_same_count_foreign_detail_mesh_cannot_supply_projection(tmp_path):
    f=fixture(tmp_path);old=f.planner.mesh
    replacement=BspDetailMeshView(old.area,old._detail+10.,old._detail_start)
    f.planner.mesh=replacement
    with pytest.raises(ValueError,match='identities'):f.plan()


def test_artifact_height_and_existing_follower_round_trip(tmp_path,legacy):
    f=fixture(tmp_path);result=f.plan()
    path=tmp_path/'current-plan.json';path.write_bytes(result.plan_bytes)
    route=FixedRoute.load(path,expected_sha256=result.route.artifact_sha256,mesh_sha256=MESH)
    assert route==result.route
    # Fresh pair after planning; old samples are not retimestamped or reused.
    f.now+=.2;a=f.position();f.now+=.5;b=f.position()
    height=measure_current_height(result.observer,f.reader,a,b,route=route,segment_index=0,
        owner_binding=f.owner,binding_reader=lambda:f.owner,clock=f.clock,
        record_id='fresh-height',released_at=100.5,local_wall_clock=f.wall)
    runner=FixedRouteFollower(route,legacy=legacy,motion=legacy.Motion(run_speed=30.,turn_rate=180.),
        heading=0.,calibration_record_id=f.options['motion_record_id'],height_calibration=height,
        geometry_evidence=result.observer.geometry,generation=1,generation_reader=lambda:1,
        mode_reader=lambda:'measurement')
    f.now+=.2;a=f.position();f.now+=.5;b=f.position()
    observe=lambda raw:result.observer.observe(raw,route=route,segment_index=0,
        height_calibration=height,motion_calibration_record_id=f.options['motion_record_id'],
        now=raw.received_monotonic,floor_chain=result.floor_chain,mode='measurement')
    runner.observe_stopped(observe(a),observe(b),released_at=101.2,now=f.now)
    assert runner.phase=='ready' and not height.live_verified
    assert not result.real_client_accepted
