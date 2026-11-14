from types import SimpleNamespace
import struct

from eql_automation.floor_replay import check_floor_trial
from eql_automation.ground_sweep import GroundFace,check_ground_coverage
from eql_automation.portal_precision import SourceFace,collect_seams
from eql_automation.source_floor_chain import SourceFloorChain
from test_portal_precision import fixture
from test_tile_rounding import grid


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
    return check_floor_trial(view,chain,original,footprint,tuple(range(len(view.ground.polys))),reference=reference,
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


def add_baked_face(data,vertices):
    ground=data[1].ground
    ground.triangles=(*ground.triangles,vertices)
    ground.polys=(*ground.polys,3)
    ground.areas[3]=63;ground.components[3]=2
    faces=tuple(GroundFace(v,63,2) for v in ground.triangles)
    original=check_ground_coverage(data[2],faces,reference=data[3],component=2,vertical_window=3.)
    return (*data[:4],original)


def test_distant_baked_platform_is_excluded_from_support_but_kept_in_source_occupancy():
    roof=SourceFace(((-10.,20.,70.),(-10.,50.,70.),(10.,35.,70.)),0,'TransparentMasked',10,1)
    data=setup((roof,))
    data=add_baked_face(data,tuple((y,x,z) for x,y,z in roof.vertices_wld))
    proposed,result=trial(data)
    assert result.candidate and result.precision_retry.candidate
    assert result.excluded_baked_detail_ids==(4,)
    assert result.floor_step.occupancy.faces[0].classification=='overhead'
    assert result.source_support.maximum_source_baked_z_difference==0.


def test_continuous_ground_support_ignores_only_wholly_distant_baked_triangles():
    roof=SourceFace(((-10.,20.,70.),(-10.,50.,70.),(10.,35.,70.)),0,'TransparentMasked',10,1)
    data=setup((roof,));ground=data[1].ground
    gap=ground.triangles[2][0][0]-32.
    ground.triangles=ground.triangles[:2]+tuple(
        tuple((x-gap,y,z) for x,y,z in tri) for tri in ground.triangles[2:])
    data=add_baked_face(data,tuple((y,x,z) for x,y,z in roof.vertices_wld))
    assert data[4].candidate
    proposed,result=trial(data)
    assert result.candidate and result.precision_retry is None
    assert result.excluded_baked_detail_ids==(4,)
    assert result.floor_step.occupancy.faces[0].classification=='overhead'


def test_baked_triangle_crossing_height_window_cannot_be_excluded():
    data=setup()
    # This crosses the complete footprint and the explicit ground-height band.
    data=add_baked_face(data,((20.,-10.,-20.),(50.,-10.,20.),(35.,10.,20.)))
    proposed,result=trial(data)
    assert proposed is None and not result.candidate
    assert result.excluded_baked_detail_ids==()
    assert data[0].index==1


def reference_gap_fixture():
    model=grid()
    a,b=next((model.sides(0,i)[1],model.sides(0,i+1)[0]) for i in range(35)
             if 0<model.sides(0,i)[1]<model.sides(0,i+1)[0])
    bits=lambda n:struct.unpack('<I',struct.pack('<f',n))[0]
    faces,links,footprint,sources,_,_=fixture(a,steps=bits(b)-bits(a))
    reference=((a+b)/2,0.,0.)
    original=check_ground_coverage(footprint,faces,reference=reference,component=2,vertical_window=3.)
    assert original.reason=='reference_ground_not_supported'
    chain=SourceFloorChain(inventory_sha256='a'*64,seed_evidence_sha256='b'*64,
                          seed_ids=((9,0),(9,1)),body_height=8.)
    assert chain.advance(footprint,sources).candidate
    ground=SimpleNamespace(polys=(1,1,2,2),triangles=tuple(f.vertices for f in faces),
                           areas={1:63,2:63},components={1:2,2:2})
    view=SimpleNamespace(ground=ground,seams=collect_seams(links,ground.areas,ground.components,tile_grid=model),
        by_polygon={1:{0},2:{0}},source_faces_for_footprint=lambda _:sources)
    return chain,view,footprint,reference,original


def test_reference_inside_exact_tile_gap_requires_full_corrected_support():
    data=reference_gap_fixture()
    proposed,result=trial(data)
    assert result.candidate and result.reference_gap_seam_indices==(0,)
    assert result.precision_retry.coverage.candidate
    assert data[0].index==1 and proposed.index==2


def test_wrong_reference_z_is_not_fixed_by_an_exact_gap():
    data=reference_gap_fixture()
    data=(*data[:3],(*data[3][:2],.25),data[4])
    proposed,result=trial(data)
    assert proposed is None and not result.candidate
    assert result.reason=='corrected_footprint_reference_ground_not_supported'


def test_existing_xy_support_with_wrong_height_cannot_be_reclassified_as_a_gap():
    data=reference_gap_fixture()
    reference=(data[3][0]-.25,0.,.25)
    faces=tuple(GroundFace(v,63,2) for v in data[1].ground.triangles)
    original=check_ground_coverage(data[2],faces,reference=reference,component=2,vertical_window=3.)
    assert original.reason=='reference_ground_not_supported'
    proposed,result=trial((*data[:3],reference,original))
    assert proposed is None and result.reason=='reference_not_in_exact_tile_gap'


def test_no_exact_tile_evidence_means_no_missing_reference_retry():
    data=reference_gap_fixture();data[1].by_polygon={}
    proposed,result=trial(data)
    assert proposed is None and result.reason=='reference_not_in_exact_tile_gap'
