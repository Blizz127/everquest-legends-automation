from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from eql_automation.bsp_volume import BspVolumeView
from eql_automation.route_geometry import RouteGeometryPreparer
from eql_automation.zone_line import ExpectedZoneLine
from test_bsp_volume import SQUARE,leaf,view
from test_ground_sweep import rectangle,check
from test_route_geometry import build,stage
from test_route_floor_commit import legacy


def expected(bsp,**changes):
    value=ExpectedZoneLine('fixture-crossing','fixture','b'*64,'c'*64,bsp.wld_sha256,
        bsp.inventory_sha256,'d'*64,'DRNTP00255000004_ZONE',4,(1,),(0,))
    return replace(value,**changes) if changes else value


def source_fixture():
    from test_region_audit import region_wld
    wld=region_wld();bsp=BspVolumeView.from_wld(wld)
    mesh=SimpleNamespace(sha256='b'*64,meta={'zone':'fixture'},area=(63,4))
    label='DRNTP00255000001'
    manifest=dict(zone='fixture',mesh_sha256=mesh.sha256,sources={'fixture.s3d':'c'*64},
        extra={'zone_lines':[{'area':4,'raw':label}]},areas={'4':{'raw':label}},area_polygons={'4':1})
    return wld,bsp,mesh,manifest


def test_factory_uses_native_effective_labels_and_exact_mesh_inventory():
    wld,bsp,mesh,manifest=source_fixture()
    line=ExpectedZoneLine.from_sources(crossing_id='fixture-crossing',wld=wld,bsp=bsp,
        mesh=mesh,manifest_bytes=json.dumps(manifest).encode(),area_id=4)
    assert line.region_ids==(2,) and line.polygon_ids==(1,)
    assert line.raw_label=='DRNTP00255000001' and line.wld_sha256==wld.sha256


@pytest.mark.parametrize('change',['mesh','zone','wld','raw','duplicate','count','missing_native'])
def test_factory_rejects_mismatched_or_ambiguous_sources(change):
    wld,bsp,mesh,manifest=source_fixture()
    if change=='mesh':mesh.sha256='f'*64
    elif change=='zone':mesh.meta={'zone':'other'}
    elif change=='wld':bsp.wld_sha256='f'*64
    elif change=='raw':manifest['areas']['4']['raw']='other'
    elif change=='duplicate':manifest['extra']['zone_lines']*=2
    elif change=='count':manifest['area_polygons']['4']=2
    else:
        manifest['areas']['4']['raw']='DRNTP00255000099'
        manifest['extra']['zone_lines'][0]['raw']='DRNTP00255000099'
    with pytest.raises(ValueError):
        ExpectedZoneLine.from_sources(crossing_id='fixture-crossing',wld=wld,bsp=bsp,
            mesh=mesh,manifest_bytes=json.dumps(manifest).encode(),area_id=4)


def test_exact_labelled_leaf_is_preserved_and_default_still_refuses():
    bsp=view(((1.,0.,0.,0.,0,2,3),leaf(1),leaf(2)),{0:{'zoneline'}})
    line=expected(bsp)
    assert not bsp.check_prism(SQUARE,(0.,6.)).candidate
    result=bsp.check_prism(SQUARE,(0.,6.),expected_zone_line=line)
    assert result.candidate and result.reason=='conditional_expected_zone_line_volume'
    assert result.labelled_regions==((0,('zoneline',)),)
    assert not result.input_authorized and not result.real_client_accepted
    assert not line.record()['destination_verified']


@pytest.mark.parametrize('other',['water','unknown','zoneline'])
def test_expected_region_does_not_hide_another_label(other):
    bsp=view(((1.,0.,0.,0.,0,2,3),leaf(1),leaf(2)),{0:{'zoneline'},1:{other}})
    result=bsp.check_prism(SQUARE,(0.,6.),expected_zone_line=expected(bsp))
    assert not result.candidate and result.reason=='labelled_bsp_volume'
    assert result.labelled_regions==((0,('zoneline',)),(1,(other,)))


def test_missing_branch_still_refuses_after_the_expected_leaf():
    bsp=view(((1.,0.,0.,0.,0,2,0),leaf(1)),{0:{'zoneline'}})
    result=bsp.check_prism(SQUARE,(0.,6.),expected_zone_line=expected(bsp))
    assert not result.candidate and result.reason=='missing_bsp_child'


@pytest.mark.parametrize('change',['wld','inventory','compound','water_label','nontransition'])
def test_wrong_source_or_raw_label_cannot_allow_a_region(change):
    bsp=view((leaf(1),),{0:{'zoneline'}});line=expected(bsp)
    with pytest.raises(ValueError):
        if change=='wld':line=replace(line,wld_sha256='f'*64)
        elif change=='inventory':line=replace(line,bsp_inventory_sha256='f'*64)
        elif change=='compound':bsp.labels=(('water','zoneline'),())
        elif change=='water_label':line=replace(line,raw_label='WTNTP00255000004_ZONE')
        else:line=replace(line,raw_label='DR_NORMAL_ZONE')
        bsp.check_prism(SQUARE,(0.,6.),expected_zone_line=line)


def test_coverage_needs_the_exact_polygon_and_actual_area():
    bsp=view((leaf(1),),{0:{'zoneline'}});line=expected(bsp)
    faces=tuple(replace(f,area_id=4) for f in rectangle(-2,-2,2,2))
    assert not check(faces).candidate
    assert check(faces,expected_zone_line=line,polygon_ids=(1,1)).candidate
    assert not check(faces,expected_zone_line=line,polygon_ids=(1,2)).candidate
    assert not check(faces,expected_zone_line=line).candidate
    assert not check(tuple(replace(f,area_id=1) for f in faces),
                     expected_zone_line=line,polygon_ids=(1,1)).candidate


def prepare_crossing(legacy,*,wall=False):
    f=build(legacy,wall=wall);p=f.prepare
    p.ground.areas[1]=4
    # Test fixture's package X is raw BSP Y; region0 occupies its right half.
    bsp=BspVolumeView(SimpleNamespace(nodes=((0.,1.,0.,-2.,0,2,3),leaf(1),leaf(2)),
        labels_by_region={0:{'zoneline'}}),region_count=2,wld_sha256=p.bsp.wld_sha256)
    g=f.runner.geometry_evidence
    line=expected(bsp,zone=f.runner.route.zone,mesh_sha256=g.mesh_sha256,
                  archive_sha256=g.source_archive_sha256)
    f.prepare=RouteGeometryPreparer(f.ledger,ground=p.ground,source=p.source,static=p.static,
        bsp=bsp,bounds=p.bounds,static_inventory_sha256=p.static_inventory_sha256,
        vertical_window=p.vertical_window,maximum_source_z_difference=p.maximum_source_z_difference,
        expected_zone_line=line)
    return f,line


def test_preparation_carries_exact_transition_with_terrain_and_static_checks(legacy):
    f,line=prepare_crossing(legacy)
    ticket=stage(f);record=f.prepare.record_for(ticket)
    assert record.expected_zone_line is line
    assert all(v.candidate for v in (record.terrain,record.static,record.bsp))
    assert record.bsp.traversal.labelled_regions==((0,('zoneline',)),)
    assert f.ledger.chain.index==1 and not record.input_authorized


def test_transition_permission_does_not_hide_static_collision(legacy):
    f,_=prepare_crossing(legacy,wall=True)
    with pytest.raises(ValueError,match='Static geometry'):stage(f)
    assert f.ledger._pending is None and f.runner.steps==0


@pytest.mark.parametrize('change',['identity','removed','polygons','region'])
def test_changed_expected_crossing_cannot_use_precomputed_ticket(legacy,change):
    f,line=prepare_crossing(legacy);f.prepare.precompute(f.scene)
    if change=='identity':f.prepare.expected_zone_line=replace(line,crossing_id='other')
    elif change=='removed':f.prepare.expected_zone_line=None
    elif change=='polygons':f.prepare.ground.areas[0]=4
    else:f.prepare.bsp.labels=(('water',),())
    with pytest.raises(ValueError):f.prepare(f.runner.propose(f.clock()),f.scene)
    assert f.ledger._pending is None and f.runner.steps==0


def test_ordinary_owner_route_policy_cannot_enable_crossing(tmp_path,legacy):
    from eql_automation.supervised_route import SupervisedRoutePolicy
    from test_supervised_route import setup
    ordinary=setup(tmp_path,legacy);policy=ordinary.policy
    crossing,_=prepare_crossing(legacy)
    with pytest.raises(ValueError,match='cannot authorize a zone crossing'):
        SupervisedRoutePolicy(crossing.prepare,declaration=policy.declaration,gate=policy.gate,
            owner_input=policy.owner_input,log_veto=policy.log_veto,
            expected_log_path=policy.log_path,expected_window=policy.window,
            topology_generation=policy.topology,check_current=lambda:None)
    assert crossing.runner.steps==0 and crossing.ledger._pending is None


@pytest.mark.parametrize('steps',[1,-1])
def test_precision_retry_retains_exact_area_and_polygon_permission(steps):
    from eql_automation.ground_sweep import check_ground_coverage
    from eql_automation.portal_precision import collect_seams,retry_precision_gap
    from test_portal_precision import fixture
    faces,links,footprint,sources,reference,_=fixture(steps=steps)
    # A previously proved reciprocal seam stays conditional on the same
    # complete face inventory. Deriving NEW area-4 seams remains unsupported.
    seams=collect_seams(links,{1:63,2:63},{1:2,2:2})
    faces=tuple(replace(f,area_id=4) if i<2 else f for i,f in enumerate(faces))
    polygons=(1,1,2,2);line=expected(view((leaf(1),),{0:{'zoneline'}}))
    original=check_ground_coverage(footprint,faces,reference=reference,component=2,
        expected_zone_line=line,polygon_ids=polygons)
    def retry(permission):
        return retry_precision_gap(original,footprint,faces,polygons,seams,sources,
            reference=reference,component=2,vertical_window=3.,
            maximum_source_z_difference=.6,allow_overlap=True,expected_zone_line=permission)
    assert retry(line).candidate
    assert not retry(None).candidate
    assert not retry(replace(line,polygon_ids=(3,))).candidate
    assert tuple(f.area_id for f in faces)==(4,4,63,63)
    assert not collect_seams(links,{1:4,2:63},{1:2,2:2})
