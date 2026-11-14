"""Ordered terrain support, with synthetic surfaces and no input devices."""
from dataclasses import replace

import pytest

from eql_automation.portal_precision import SourceFace
from eql_automation.source_floor_chain import SourceFloorChain


def face(vertices,index,material='Diffuse'):
    return SourceFace(tuple((y,x,z) for x,y,z in vertices),0,material,1,index)


FLOOR=(face(((-4.,-4.,0.),(4.,-4.,0.),(4.,4.,0.)),1),
       face(((-4.,-4.,0.),(4.,4.,0.),(-4.,4.,0.)),2))
ROOF=face(((-5.,-5.,70.),(5.,-5.,70.),(0.,5.,70.)),3,'TransparentMasked')


def cell(x,y,radius=.25):
    return ((x-radius,y-radius),(x+radius,y-radius),(x+radius,y+radius),(x-radius,y+radius))


def chain(**changes):
    options=dict(inventory_sha256='a'*64,seed_evidence_sha256='b'*64,seed_ids=((1,1),),body_height=8.)
    return SourceFloorChain(**{**options,**changes})


def test_same_face_under_overhead_then_exact_edge_transition_keeps_a_proof_chain():
    c=chain();first=c.advance(cell(1.,-1.),(*FLOOR,ROOF))
    assert first.candidate and first.selected_ids==((1,1),)
    second=c.advance(cell(.5,-.5,1.),(*FLOOR,ROOF))
    assert second.candidate and second.selected_ids==((1,1),(1,2))
    assert len(second.joins)==1 and second.carried_ids==((1,1),)
    assert second.previous_sha256==first.proof_sha256
    assert second.geometry_sha256!=first.geometry_sha256
    assert not second.real_client_accepted and not second.input_authorized
    assert c.floor_at((0.,0.))==(0.,('wld:1:face:1','wld:1:face:2'))


def test_entire_cell_must_overlap_previous_cell_even_on_the_same_large_triangle():
    c=chain();assert c.advance(cell(1.,-1.),FLOOR).candidate
    r=c.advance(cell(3.,-3.),FLOOR)
    assert r.reason=='successive_cells_do_not_overlap'
    assert c.index==1
    assert c.advance(cell(1.,-1.),FLOOR).reason=='source_floor_chain_already_halted'
    with pytest.raises(ValueError):c.floor_at((1.,-1.))


def test_geometry_change_cannot_reuse_a_previous_source_identity():
    c=chain();assert c.advance(cell(1.,-1.),FLOOR).candidate
    shifted=replace(FLOOR[0],vertices_wld=tuple((x,y,z+.01) for x,y,z in FLOOR[0].vertices_wld))
    assert c.advance(cell(1.,-1.),(shifted,FLOOR[1])).reason=='source_identity_changed'


def test_missing_support_cannot_jump_to_a_new_floor_or_reseed():
    c=chain();assert c.advance(cell(1.,-1.),FLOOR).candidate
    alternate=replace(FLOOR[0],face=4)
    assert c.advance(cell(1.,-1.),(alternate,)).reason=='no_shared_source_floor_with_previous_cell'


def test_one_exact_edge_with_three_incident_floors_is_ambiguous():
    branch=face(((-4.,-4.,0.),(4.,4.,0.),(-4.,4.,.1)),4)
    r=chain().advance(cell(0.,0.,1.),(*FLOOR,branch))
    assert r.reason=='ambiguous_source_edge_branch'


def test_vertical_wall_and_low_platform_remain_in_the_occupancy_check():
    wall=face(((0.,-3.,-1.),(0.,3.,-1.),(0.,0.,10.)),4)
    assert not chain().advance(cell(0.,0.,1.),(*FLOOR,wall)).candidate
    low=replace(ROOF,vertices_wld=tuple((x,y,4.) for x,y,_ in ROOF.vertices_wld))
    assert not chain().advance(cell(1.,-1.),(*FLOOR,low)).candidate


def test_seed_requires_supported_material_and_full_exact_partition():
    assert not chain().advance(cell(0.,0.,1.),(FLOOR[0],)).candidate
    assert not chain().advance(cell(1.,-1.),(replace(FLOOR[0],material_class='Water'),)).candidate
    assert not chain().advance(cell(1.,-1.),(FLOOR[0],FLOOR[0])).candidate


def test_point_only_contact_cannot_join_two_floors():
    a=face(((0.,0.,0.),(2.,0.,0.),(0.,2.,0.)),1)
    b=face(((2.,0.,0.),(4.,0.,0.),(2.,2.,0.)),2)
    c=chain();assert c.advance(cell(1.5,.15,.1),(a,b)).candidate
    r=c.advance(cell(1.9,.15,.35),(a,b))
    assert not r.candidate and not r.joins


def test_selected_floor_query_is_confined_to_current_cell_and_has_correct_axes():
    ramp=face(((-4.,-4.,-2.),(4.,-4.,0.),(4.,4.,2.)),1)
    c=chain();assert c.advance(cell(1.,-1.),(ramp,)).candidate
    assert c.floor_at((1.,-1.))[0]==0.
    assert c.floor_at((1.1,-1.))[0]==pytest.approx(.025)
    with pytest.raises(ValueError):c.floor_at((3.,-3.))
    with pytest.raises(ValueError):c.floor_at((float('nan'),0.))


def test_seed_multiple_faces_must_be_edge_connected():
    detached=face(((-4.,-4.,.0000001),(4.,4.,.0000001),(-4.,4.,.0000001)),2)
    r=chain(seed_ids=((1,1),(1,2))).advance(cell(0.,0.,1.),(FLOOR[0],detached))
    assert r.reason=='seed_faces_not_edge_connected'


@pytest.mark.parametrize('options',({'seed_evidence_sha256':''},{'body_height':0.},{'seed_ids':((1,1),(1,1))}))
def test_invalid_seed_context_refuses_before_tracking(options):
    with pytest.raises(ValueError):chain(**options)
