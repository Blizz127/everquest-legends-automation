"""Numerical tile model tests, with synthetic provenance and no game input."""
from dataclasses import replace
import struct

import pytest

from eql_automation.tile_rounding import TileGrid,f32,grid_from_metadata
from eql_automation.portal_precision import PortalLink,collect_seams,retry_precision_gap
from eql_automation.ground_sweep import GroundFace,check_ground_coverage
from test_portal_precision import fixture


def grid(origin=(-2693.15625,-2803.8125)):
    return TileGrid('synthetic','a'*64,'b'*64,'c'*64,'d'*64,origin,
                    f32(.6),f32(1.2),256,(36,36))


def test_float32_border_and_known_tile_sides():
    model=grid()
    assert model.border_cells==5
    assert model.sides(1,14)==(-653.412353515625,-499.8123474121094)
    assert model.sides(1,15)[0]==-499.8125
    assert model.sides(0,25)[1]==1300.4439697265625
    assert model.sides(0,26)[0]==1300.44384765625


def test_exact_model_recognizes_40_steps_without_a_global_ulp_cap():
    model=grid()
    first,second=-39.012298583984375,-39.012451171875
    bits=lambda n:struct.unpack('<I',struct.pack('<f',n))[0]
    assert abs(bits(first)-bits(second))==40
    boundary=model.match(1,first,second)
    assert boundary is not None and boundary.lower_tile==17
    assert model.match(0,first,second) is None
    assert replace(model,origin_xy=(model.origin_xy[0],model.origin_xy[1]+1.)).match(1,first,second) is None
    # Nearby arbitrary coordinates are never accepted because they are close.
    assert model.match(1,first+1e-6,second) is None


def test_both_boundary_orders_use_same_inferred_tile_pair():
    model=grid();a,b=model.sides(1,14)[1],model.sides(1,15)[0]
    assert model.match(1,a,b)==model.match(1,b,a)
    assert model.match(1,a,a) is None
    assert model.match(1,a,model.sides(1,16)[0]) is None


def test_metadata_package_axes_are_not_recast_axes():
    manifest=dict(format=1,zone='test',mesh_sha256='a'*64,
        params=dict(cell_size=.6,agent_radius=1.2,tile_size=256),
        extra=dict(geometry=dict(bounds=[[12.,34.,0.],[100.,200.,10.]])),
        sources={'test.s3d':'d'*64},tiles=dict(x=3,z=7))
    meta={**manifest,'baker_sha256':'c'*64}
    model=grid_from_metadata(manifest,meta,manifest_sha256='b'*64,mesh_sha256='a'*64,zone='test')
    assert model.origin_xy==(12.,34.) and model.tile_counts_xy==(7,3)
    with pytest.raises(ValueError):
        grid_from_metadata(manifest,meta,manifest_sha256='b'*64,mesh_sha256='f'*64,zone='test')
    with pytest.raises(ValueError):
        grid_from_metadata(manifest,{**meta,'params':{**meta['params'],'tile_size':128}},
                           manifest_sha256='b'*64,mesh_sha256='a'*64,zone='test')


@pytest.mark.parametrize('changes',({'cell_size':float('inf')},{'cell_size':0.},
    {'tile_size':True},{'tile_counts_xy':(513,1)},{'manifest_sha256':'bad'}))
def test_invalid_grid_does_not_issue_boundary_evidence(changes):
    with pytest.raises(ValueError):replace(grid(),**changes)


def test_five_step_overlap_requires_model_and_actual_polygon_side_orientation():
    # Put the known numerical Y origin on synthetic X; this is analytic
    # geometry and uses no copied client vertices.
    model=grid(origin=(-2803.8125,-2693.15625))
    a,b=model.sides(0,14)[1],model.sides(0,15)[0]
    data=fixture(a,steps=5)
    faces,links,footprint,sources,ref,original=data
    assert links[1].edge[0][0]==b
    assert not collect_seams(links,{1:63,2:63},{1:2,2:2},maximum_ulp_steps=2)
    seams=collect_seams(links,{1:63,2:63},{1:2,2:2},tile_grid=model)
    assert len(seams)==1 and seams[0].tile_boundary is not None
    assert seams[0].maximum_ulp_steps is None
    assert seams[0].actual_ulp_steps==5 and seams[0].classifier=='exact_tile_side'
    kwargs=dict(reference=ref,component=2,vertical_window=3.,maximum_source_z_difference=.6,allow_overlap=True)
    result=retry_precision_gap(original,footprint,faces,(1,1,2,2),seams,sources,**kwargs)
    assert result.candidate and not result.input_authorized
    bad=list(faces)
    p=bad[0].vertices
    bad[0]=GroundFace(((a+.1,p[0][1],p[0][2]),*p[1:]),63,2)
    result=retry_precision_gap(original,footprint,tuple(bad),(1,1,2,2),seams,sources,**kwargs)
    assert result.reason=='detail_polygon_disagrees_with_predicted_tile_side'


def test_tile_model_still_requires_unique_reciprocity_and_exact_other_endpoints():
    model=grid();a,b=model.sides(1,14)[1],model.sides(1,15)[0]
    left=PortalLink(1,2,((0.,a,0.),(10.,a,0.)))
    right=PortalLink(2,1,((10.,b,0.),(0.,b,0.)))
    args=({1:63,2:63},{1:2,2:2})
    assert len(collect_seams((left,right),*args,tile_grid=model))==1
    assert not collect_seams((left,left,right),*args,tile_grid=model)
    assert not collect_seams((left,replace(right,edge=((10.001,b,0.),(0.,b,0.)))),*args,tile_grid=model)
