"""The offline probe models client printing and reconstructs committed context."""
from dataclasses import asdict
from hashlib import sha256
import json
from types import SimpleNamespace

import pytest

from eql_automation.ground_observer import exact_detail_support
from eql_automation.portal_precision import SourceFace
from eql_automation.source_floor_chain import SourceFloorChain
from tools.probe_route_ground_observer import (
    committed_cells, observed_location_format, reconstructed_cells, synthetic_location)


def test_client_format_uses_physical_source_height_and_preserves_pose():
    position=[148.44380187991518,1343.38757324221,99.]
    original=list(position)
    raw,body=synthetic_location(position,-8.75,2.564,client_format=True)
    assert raw==(1343.39,148.44,-6.19)
    assert body=='Your Location is 1343.39, 148.44, -6.19'
    assert position==original  # baked Z=99 never entered the log
    assert synthetic_location(position,-8.75,2.564,client_format=False)==(
        (position[1],position[0],-8.75+2.564),None)


def test_observation_precision_does_not_widen_exact_mesh_support():
    edge=1343.3875732421875
    other=edge+1/8192
    a,b,c,d=(140.,edge,0.),(160.,edge,0.),(160.,1300.,0.),(140.,1300.,0.)
    e,f,g,h=(140.,other,0.),(160.,other,0.),(160.,1400.,0.),(140.,1400.,0.)
    mesh=SimpleNamespace(_detail=((a,b,c),(a,c,d),(e,f,g),(e,g,h)),_detail_start=(0,2,4))
    pose=(148.44380187991518,1343.38757324221,0.)
    assert exact_detail_support(mesh,0,(pose[0],edge)).status=='supported'
    assert exact_detail_support(mesh,0,pose[:2]).status=='absent'
    assert exact_detail_support(mesh,1,pose[:2]).status=='absent'
    raw,_=synthetic_location(pose,0.,2.564,client_format=True)
    observed=(raw[1],raw[0])
    assert exact_detail_support(mesh,0,observed).status=='absent'
    assert exact_detail_support(mesh,1,observed).status=='supported'
    # Real or simulated points that actually print in a gap are still refused.
    assert exact_detail_support(mesh,1,pose[:2]).status=='absent'


def test_format_evidence_requires_all_retained_location_examples_to_agree():
    prefix='[Sat Nov 14 04:00:00 2026] '
    line=prefix+'Your Location is -12.30, 0.00, 4.20'
    assert observed_location_format(line)['examples']==1
    with pytest.raises(ValueError):observed_location_format(line+'\n'+prefix+'Your Location is 1.234, 2.00, 3.00')
    with pytest.raises(ValueError):observed_location_format(prefix+'You hit a rat.')
    with pytest.raises(ValueError):synthetic_location((0.,float('nan'),0.),0.,2.564,client_format=True)


def fixture():
    vertices=((0.,0.,0.),(0.,6.,0.),(6.,6.,0.),(6.,0.,0.))
    faces=(SourceFace(vertices[:3],0,'Diffuse',1,0),SourceFace((vertices[0],vertices[2],vertices[3]),0,'Diffuse',1,1))
    source=SimpleNamespace(wld_sha256='a'*64,source_faces_for_footprint=lambda footprint:faces)
    seed={'selected_ids':[[1,0],[1,1]]}
    evidence={'source_wld_sha256':source.wld_sha256,'seed':seed,'hypothetical_body_height':8.}
    chain=SourceFloorChain(inventory_sha256=source.wld_sha256,
        seed_evidence_sha256=sha256(json.dumps(seed,sort_keys=True).encode()).hexdigest(),
        seed_ids=((1,0),(1,1)),body_height=8.)
    footprints=[((x,1.),(x+1.,1.),(x+1.,3.),(x,3.)) for x in (1.,1.5,2.)]
    steps=[asdict(chain.advance(p,faces)) for p in footprints]
    assert all(step['candidate'] for step in steps)
    replay={'steps':2,'phase':'arrived','source_floor_trials':[],
        'static_floor_trials':[],'bsp_volume_trials':[],
        'conditional_source_floor_chain':{'initial':steps[0],'committed_cells':3,
            'last_proof_sha256':steps[-1]['proof_sha256']}}
    for i in range(2):
        identity={'step':i,'segment':0,'hold':.1}
        replay['source_floor_trials'].append({**identity,'trial':{'candidate':True,'floor_step':steps[i+1]}})
        for key in ('static_floor_trials','bsp_volume_trials'):
            replay[key].append({**identity,'footprint':footprints[i+1],'trial':{'candidate':True}})
    return source,json.loads(json.dumps(replay)),evidence,footprints[0]


def test_reconstruction_yields_initial_then_postcommit_cell_and_preserves_sampling():
    source,replay,evidence,initial=fixture()
    seen=[]
    for step,chain in reconstructed_cells(source,replay,evidence,initial):
        before=(chain.index,chain.previous,chain._expanded,chain._selected)
        # Observation order may repeat or move backward; sampling the current
        # cell twice must never advance it.
        point=(1.75 if step<1 else 2.5,2.)
        first=chain.floor_at(point)
        assert chain.floor_at(point)==first
        assert (chain.index,chain.previous,chain._expanded,chain._selected)==before
        seen.append((step,chain.index,chain.previous.proof_sha256))
    assert [(step,index) for step,index,_ in seen]==[(-1,1),(0,2),(1,3)]
    assert seen[-1][2]==replay['conditional_source_floor_chain']['last_proof_sha256']


@pytest.mark.parametrize('change',['duplicate','rejected','footprint','identity','count','not_arrived'])
def test_commit_reconstruction_refuses_ambiguous_trial_ledger(change):
    _,replay,_,_=fixture()
    if change=='duplicate':replay['source_floor_trials'][1]['step']=0
    elif change=='rejected':replay['bsp_volume_trials'][0]['trial']['candidate']=False
    elif change=='footprint':replay['static_floor_trials'][0]['footprint'][0][0]+=.01
    elif change=='identity':replay['static_floor_trials'][0]['hold']=.2
    elif change=='count':replay['source_floor_trials'].pop()
    elif change=='not_arrived':replay['phase']='halted'
    with pytest.raises(ValueError):committed_cells(replay)


@pytest.mark.parametrize('change',['initial','cell','last','source'])
def test_reconstruction_checks_actual_geometry_proof_and_final_identity(change):
    source,replay,evidence,initial=fixture()
    if change=='initial':replay['conditional_source_floor_chain']['initial']['proof_sha256']='0'*64
    elif change=='cell':replay['source_floor_trials'][1]['trial']['floor_step']['selected_ids']=[[1,99]]
    elif change=='last':replay['conditional_source_floor_chain']['last_proof_sha256']='0'*64
    elif change=='source':source.wld_sha256='0'*64
    with pytest.raises(ValueError):list(reconstructed_cells(source,replay,evidence,initial))
