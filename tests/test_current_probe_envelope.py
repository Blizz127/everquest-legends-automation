"""Continuous unknown-heading envelopes over synthetic complete zone views."""
from dataclasses import replace
from hashlib import sha256
import json
import math

import numpy as np
import pytest

from eql_automation.current_route_start import CurrentProbeEnvelope, CurrentStartPlanner
from eql_automation.ground_sweep import cross
from eql_automation.portal_precision import SourceFace, PortalLink, collect_seams
from test_current_route_start import fixture
from test_ground_observer import rectangle
from test_native_region_policy import setup as native_fixture
from test_client_classification import leaf
from test_portal_precision import neighbor


def probe(f,kind='forward'):
    options={k:v for k,v in f.options.items() if k not in {'heading','length','half_width'}}
    options['bounds']=replace(options['bounds'],forward_speed_upper_bound=10.)
    return f.planner.plan_probe_envelope(f.reader,f.a,f.b,probe_kind=kind,**options)


def split_detail(f,*,gap=0.,area=63,component=7,height=.6,seams=False):
    p=f.planner;edge=4.5;other=edge+gap
    triangles=np.asarray(rectangle(0.,edge,.6)+rectangle(other,10.,height))
    p.ground.triangles=p.mesh._detail=triangles
    p.ground.polys=np.asarray([0,0,1,1])
    p.ground.areas=p.mesh.area=np.asarray([63,area])
    p.ground.components=np.asarray([7,component])
    p.ground.minimum=triangles.min(axis=1);p.ground.maximum=triangles.max(axis=1)
    p.mesh._detail_start=np.asarray([0,2,4])
    if seams:
        p.source.seams=collect_seams((
            PortalLink(0,1,((edge,0.,.6),(edge,4.,.6))),
            PortalLink(1,0,((other,4.,.6),(other,0.,.6)))),{0:63,1:63},{0:7,1:7})
        p.source.by_polygon={0:{0},1:{0}}
        f.planner=CurrentStartPlanner(mesh=p.mesh,ground=p.ground,source=p.source,
            static=p.static,bsp=p.bsp,zone_short_name=p.zone,expected_zone_id=p.zone_id,
            expected_zone_name=p.zone_name,mesh_sha256=p.pins[0],source_archive_sha256=p.pins[1],
            source_wld_sha256=p.pins[2],static_inventory_sha256=p.pins[3])


@pytest.mark.parametrize('kind',('forward','left','right'))
def test_area_has_no_heading_or_route_authority_and_covers_all_bearings(tmp_path,kind):
    f=fixture(tmp_path,x=1004.);result=probe(f,kind)
    assert type(result) is CurrentProbeEnvelope and not hasattr(result,'route')
    assert result.reference==(1004.,2.,.6) and result.source_reference==(1004.,2.,.2)
    data=json.loads(result.evidence_bytes);seed=data['seed'];b=result.planning_bounds
    travel=b.forward_speed_upper_bound*b.maximum_actual_hold if kind=='forward' else b.pivot_displacement_upper_bound
    radius=travel+b.body_radius+b.position_error+b.post_release_drift
    for degree in range(360):
        angle=math.radians(degree+.5)
        xy=(result.reference[0]+radius*math.cos(angle),result.reference[1]+radius*math.sin(angle))
        assert all(cross(a,result.footprint[(i+1)%len(result.footprint)],xy)>=-1e-10
                   for i,a in enumerate(result.footprint))
    assert seed['heading'] is None and seed['maximum_center_travel']==travel
    assert data['all_headings'] and data['exact_detail_partition']
    assert sha256(result.evidence_bytes).hexdigest()==result.evidence_sha256
    assert result.requires_fresh_start_pair and not result.input_authorized and not result.current_motion_verified
    assert not result.real_client_accepted and not data['motion_bounds_verified']
    assert f.reader.latest is f.b and f.reader.log_line_seq==f.b.log_line_seq


def test_disk_crosses_continuous_internal_polygon_boundary(tmp_path):
    f=fixture(tmp_path);split_detail(f)
    result=probe(f);data=json.loads(result.evidence_bytes)
    assert data['terrain']['coverage']['used_faces']>=2
    assert min(x for x,y in result.footprint)<4.5<max(x for x,y in result.footprint)


def test_wall_behind_known_forward_ray_is_in_unknown_heading_area(tmp_path):
    f=fixture(tmp_path)
    # The old northbound capsule is clear; an unknown westbound pulse is not.
    wall=SourceFace(((1.5,3.2,0.),(2.5,3.2,0.),(2.,3.2,4.)),0,'Diffuse',20,0)
    f.planner.static.faces_for_footprint=lambda _:(wall,)
    assert f.plan().floor_chain.previous.candidate
    with pytest.raises(ValueError,match='static'):probe(f)


@pytest.mark.parametrize('fault',('water','component','height','tiny_hole','stacked','ceiling'))
def test_whole_area_hazards_and_sub_tolerance_holes_refuse(tmp_path,fault):
    f=fixture(tmp_path,duplicate=fault=='stacked')
    if fault=='water':split_detail(f,area=1)
    elif fault=='component':split_detail(f,component=9)
    elif fault=='height':split_detail(f,height=.8)
    elif fault=='tiny_hole':split_detail(f,gap=1e-8)
    elif fault=='ceiling':
        p=f.planner.source
        ceiling=SourceFace(((2.2,4.6,2.),(2.2,4.8,2.),(2.4,4.6,2.)),0,'Diffuse',30,0)
        p.sources=(*p.sources,ceiling)
        xyz=np.asarray([[(y,x,z) for x,y,z in s.vertices_wld] for s in p.sources])
        p.source_minimum=xyz.min(axis=1);p.source_maximum=xyz.max(axis=1)
    before=f.planner.source.sources
    with pytest.raises(ValueError):probe(f)
    assert f.planner.source.sources is before and f.reader.latest is f.b


def test_one_ulp_gap_needs_exact_reciprocal_seam_evidence(tmp_path):
    f=fixture(tmp_path);gap=neighbor(4.5)-4.5
    split_detail(f,gap=gap)
    with pytest.raises(ValueError):probe(f)
    split_detail(f,gap=gap,seams=True)
    result=probe(f);data=json.loads(result.evidence_bytes)
    assert data['terrain']['precision_retry']['candidate'] and data['exact_detail_partition']


@pytest.mark.parametrize('kind',('steep','raised','source_mismatch','flat'))
def test_sub_tolerance_detail_strip_is_checked_not_just_counted(tmp_path,kind):
    f=fixture(tmp_path);p=f.planner;edge=4.5;width=1e-8
    middle=rectangle(edge,edge+width,.6 if kind in ('steep','flat') else .8)
    if kind=='steep':
        middle=tuple(tuple((x,y,z+(x-edge)*2.) for x,y,z in tri) for tri in middle)
    triangles=np.asarray(rectangle(0.,edge,.6)+middle+rectangle(edge+width,10.,.6))
    p.ground.triangles=p.mesh._detail=triangles
    p.ground.polys=np.zeros(len(triangles),dtype=np.int64)
    p.ground.minimum=triangles.min(axis=1);p.ground.maximum=triangles.max(axis=1)
    p.mesh._detail_start=np.asarray([0,len(triangles)])
    if kind=='source_mismatch':
        # Keep the seam within its existing .01 tolerance, but exceed the
        # explicit source/baked difference only on the tiny strip.
        triangles[2:4,:,2]=.605
        p.ground.minimum=triangles.min(axis=1);p.ground.maximum=triangles.max(axis=1)
        f.options['maximum_source_z_difference']=.402
    if kind=='flat':
        assert probe(f).floor_chain.previous.candidate
    else:
        with pytest.raises(ValueError,match='Probe envelope detail'):
            probe(f)


@pytest.mark.parametrize('change',('stale','moving','owner','source','budget','clock','extra_log','kind'))
def test_changed_pair_scope_budget_or_probe_refuses(tmp_path,change):
    f=fixture(tmp_path);kind='forward'
    if change=='stale':f.now+=.51
    elif change=='moving':f.a=replace(f.a,raw_coordinates=(3.,4.,2.7))
    elif change=='owner':f.owner=('other',)
    elif change=='source':f.planner.source.wld_sha256='f'*64
    elif change=='extra_log':f.reader.log_line_seq+=1
    elif change=='kind':kind='jump'
    else:
        calls=[]
        def binding():
            calls.append(1)
            if len(calls)==3:f.now+=(11 if change=='budget' else -.01)
            return f.owner
        f.options['binding_reader']=binding
    with pytest.raises(ValueError):probe(f,kind)


def test_native_zero_policy_keeps_missing_child_evidence_without_waiver(tmp_path):
    f=native_fixture(tmp_path);data=json.loads(probe(f).evidence_bytes)
    assert not data['bsp']['candidate'] and data['bsp']['reason']=='missing_bsp_child'
    assert data['native_region'] is not None and data['native_region_sha256']


@pytest.mark.parametrize('nodes',((leaf(2),),(leaf(3),),(),((0.,0.,0.,0.,0,1,1),)))
def test_native_nonzero_or_incomplete_classification_refuses(tmp_path,nodes):
    f=native_fixture(tmp_path,native_nodes=nodes)
    with pytest.raises(ValueError):probe(f)
