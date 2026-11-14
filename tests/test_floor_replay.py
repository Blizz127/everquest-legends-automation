from types import SimpleNamespace

from eql_automation.floor_replay import check_floor_trial
from eql_automation.portal_precision import SourceFace,collect_seams
from eql_automation.source_floor_chain import SourceFloorChain
from test_portal_precision import fixture


def setup(extra=()):
    faces,links,footprint,sources,reference,original=fixture()
    chain=SourceFloorChain(inventory_sha256='a'*64,seed_evidence_sha256='b'*64,
                          seed_ids=((9,0),(9,1)),body_height=8.)
    assert chain.advance(footprint,sources).candidate
    ground=SimpleNamespace(polys=(1,1,2,2),triangles=tuple(f.vertices for f in faces),
                           areas={1:63,2:63},components={1:2,2:2})
    view=SimpleNamespace(ground=ground,seams=collect_seams(links,ground.areas,ground.components),
        by_polygon={1:{0},2:{0}},source_faces_for_footprint=lambda _:sources+extra)
    return chain,view,footprint,reference,original


def trial(data,limit=.6):
    chain,view,footprint,reference,original=data
    return check_floor_trial(view,chain,original,footprint,(0,1,2,3),reference=reference,
        component=2,vertical_window=3.,maximum_source_z_difference=limit)


def test_precision_retry_under_high_platform_checks_all_surfaces_then_uses_selected_floor():
    roof=SourceFace(((-10.,20.,70.),(-10.,50.,70.),(10.,35.,70.)),0,'TransparentMasked',10,1)
    data=setup((roof,));chain=data[0];before=chain.previous
    proposed,result=trial(data)
    assert result.candidate and result.precision_retry.candidate
    assert result.floor_step.occupancy.faces[0].classification=='overhead'
    assert not result.input_authorized and not result.real_client_accepted
    assert proposed is not chain and proposed.index==chain.index+1
    assert chain.previous is before and chain.index==1
    assert proposed.floor_at(tuple(data[3][:2]))[0]==0.


def test_wall_refusal_does_not_poison_previous_chain_or_allow_a_filtered_retry():
    wall=SourceFace(((-2.,32.,-1.),(2.,32.,-1.),(0.,32.,10.)),0,'Diffuse',10,2)
    data=setup((wall,));chain=data[0];before=chain.previous
    proposed,result=trial(data)
    assert proposed is None and not result.candidate and result.precision_retry is None
    assert result.reason=='other_source_surface_intersects_body_band'
    assert not chain.halted and chain.previous is before
    assert chain.floor_at(tuple(data[3][:2]))[0]==0.


def test_missing_seam_is_not_hidden_by_source_support():
    data=setup();data[1].by_polygon={}
    proposed,result=trial(data)
    assert proposed is None and result.reason=='no_bounded_reciprocal_seam_set'
    assert data[0].index==1 and not data[0].halted


def test_whole_footprint_source_baked_height_limit_is_still_required():
    data=setup();ground=data[1].ground
    ground.triangles=tuple(tuple((x,y,z+1.) for x,y,z in tri) for tri in ground.triangles)
    data=(*data[:3],(*data[3][:2],1.),data[4])
    proposed,result=trial(data,limit=.6)
    assert proposed is None and not result.candidate
    assert result.reason=='source_baked_height_mismatch'
    assert not data[0].halted
