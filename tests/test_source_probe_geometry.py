"""Unknown-heading body checks on an explicit, already reached source floor."""
from dataclasses import replace
from hashlib import sha256
import math

import numpy as np
import pytest

from eql_automation.ground_sweep import cross
from eql_automation.portal_precision import SourceFace
from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_probe_geometry import check_source_probe
from test_client_classification import leaf
from test_ground_observer import rectangle
from test_native_region_policy import setup


def fixture(tmp_path,**options):
    f=setup(tmp_path,**options);p=f.planner
    chain=SourceFloorChain(inventory_sha256=p.source.wld_sha256,
        seed_evidence_sha256='e'*64,seed_ids=((10,1),),body_height=6.)
    cap=swept_square((4.,2.),(4.,2.),.1)
    assert chain.advance(cap,p.source.source_faces_for_footprint(cap)).candidate
    f.prefix=chain;f.reference=(4.,2.,.2)
    f.bounds=replace(f.options['bounds'],forward_speed_upper_bound=10.)
    f.context=lambda:None
    return f


def probe(f,kind='forward'):
    p=f.planner
    return check_source_probe(f.prefix,f.reference,probe_kind=kind,bounds=f.bounds,
        terrain=p.source,static=p.static,bsp=p.bsp,region_policy=p.region_policy,
        check_context=f.context,clock=f.clock,maximum_seconds=10.)


@pytest.mark.parametrize('kind',('forward','left','right'))
def test_all_heading_body_area_preserves_original_floor_and_grants_no_input(tmp_path,kind):
    f=fixture(tmp_path);before=_chain_snapshot(f.prefix);result=probe(f,kind)
    data=result.record();assert _chain_snapshot(f.prefix)==before
    assert result.branch is not f.prefix and result.branch.index==f.prefix.index+1
    assert result.branch.floor_at((4.,2.))[0]==.2
    assert data['previous_floor_proof_sha256']==f.prefix.previous.proof_sha256
    assert data['all_headings'] and data['heading'] is None
    b=f.bounds;travel=b.forward_speed_upper_bound*b.maximum_actual_hold if kind=='forward' else b.pivot_displacement_upper_bound
    radius=b.body_radius+travel+b.position_error+b.post_release_drift
    footprint=data['footprint']
    for angle in range(360):
        t=math.radians(angle+.5);xy=(4.+radius*math.cos(t),2.+radius*math.sin(t))
        assert all(cross(a,footprint[(i+1)%len(footprint)],xy)>=-1e-10 for i,a in enumerate(footprint))
    assert not result.input_authorized and not result.current_position_verified
    assert not result.current_motion_verified and not result.real_client_accepted
    assert not data['baked_mesh_coverage_claimed'] and data['requires_fresh_start_pair']
    assert not data['bsp']['candidate'] and data['bsp']['reason']=='missing_bsp_child'
    assert data['native']['complete'] and data['native']['possible_flags']==[0]
    assert sha256(result.payload).hexdigest()==result.sha256


def add_source(f,sources):
    p=f.planner.source;p.sources=(*p.sources,*sources)
    xyz=np.asarray([[(y,x,z) for x,y,z in s.vertices_wld] for s in p.sources])
    p.source_minimum=xyz.min(axis=1);p.source_maximum=xyz.max(axis=1)


def test_retained_lower_floor_is_not_reseeded_from_all_layer_xy(tmp_path):
    f=fixture(tmp_path)
    add_source(f,tuple(SourceFace(tuple((y,x,z) for x,y,z in tri),0,'Diffuse',20,i)
        for i,tri in enumerate(rectangle(0.,10.,10.))))
    with pytest.raises(ValueError,match='layered'):
        f.planner.source.propose_unique_diffuse_floor((4.,2.),body_height=6.)
    result=probe(f)
    assert result.branch.floor_at((4.,2.))[0]==.2
    assert all(fragment==10 for fragment,face in result.branch.previous.selected_ids)


@pytest.mark.parametrize('fault',('terrain_wall','ceiling','static_wall','hole'))
def test_entire_source_occupancy_is_still_checked(tmp_path,fault):
    f=fixture(tmp_path);before=_chain_snapshot(f.prefix)
    wall=SourceFace(((1.5,3.2,0.),(2.5,3.2,0.),(2.,3.2,4.)),0,'Diffuse',20,0)
    if fault=='terrain_wall':add_source(f,(wall,))
    elif fault=='ceiling':add_source(f,(SourceFace(((1.7,3.5,4.),(2.3,3.5,4.),(2.,4.5,4.)),0,'Diffuse',20,0),))
    elif fault=='static_wall':f.planner.static.faces_for_footprint=lambda _:(wall,)
    else:
        f.bounds=replace(f.bounds,forward_speed_upper_bound=30.)
    with pytest.raises(ValueError):probe(f)
    assert _chain_snapshot(f.prefix)==before


@pytest.mark.parametrize('options',({'old_water':True},{'native_nodes':(leaf(2),)},
                                  {'native_nodes':(leaf(3),)},{'native_nodes':()}))
def test_old_hazards_and_native_nonzero_or_unknown_refuse(tmp_path,options):
    f=fixture(tmp_path,**options)
    with pytest.raises(ValueError):probe(f)


@pytest.mark.parametrize('fault',('outside_cap','raw_eye_height','body','kind','cancel','clock','expired','prefix','policy','storage'))
def test_reference_context_and_bounds_cannot_be_reused_after_change(tmp_path,fault):
    f=fixture(tmp_path);kind='forward'
    if fault=='outside_cap':f.reference=(6.,2.,.2)
    elif fault=='raw_eye_height':f.reference=(4.,2.,2.7)
    elif fault=='body':f.bounds=replace(f.bounds,body_height=5.)
    elif fault=='kind':kind='jump'
    else:
        calls=[]
        def context():
            calls.append(1)
            if len(calls)!=2:return
            if fault=='cancel':raise ValueError('Owner OFF')
            elif fault=='clock':f.now-=.1
            elif fault=='expired':f.now+=11.
            elif fault=='policy':f.planner.region_policy.classifier.inventory_sha256='d'*64
            elif fault=='storage':f.planner.source.sources=tuple(list(f.planner.source.sources))
            else:f.prefix.seed_evidence_sha256='d'*64
        f.context=context
    with pytest.raises(ValueError):probe(f,kind)
