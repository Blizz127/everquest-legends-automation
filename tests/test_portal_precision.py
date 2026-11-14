"""Analytic geometry fixtures; no copied game geometry or input devices."""
from dataclasses import replace
import struct

import pytest

from eql_automation.ground_sweep import GroundCoverage,GroundFace,check_ground_coverage
from eql_automation.portal_precision import PortalLink,SourceFace,collect_seams,retry_precision_gap


def neighbor(value,steps=1):
    bits=struct.unpack('<I',struct.pack('<f',value))[0]
    return struct.unpack('<f',struct.pack('<I',bits+steps))[0]


def fixture(x=32.,steps=1):
    y=neighbor(x,steps)
    faces=(GroundFace(((x-2,-2.,0.),(x,-2.,0.),(x,2.,0.)),63,2),
           GroundFace(((x-2,-2.,0.),(x,2.,0.),(x-2,2.,0.)),63,2),
           GroundFace(((y,-2.,0.),(y+2,-2.,0.),(y+2,2.,0.)),63,2),
           GroundFace(((y,-2.,0.),(y+2,2.,0.),(y,2.,0.)),63,2))
    links=(PortalLink(1,2,((x,-2.,0.),(x,2.,0.))),PortalLink(2,1,((y,2.,0.),(y,-2.,0.))))
    mid=(x+y)/2
    footprint=((mid-.5,-.5),(mid+.5,-.5),(mid+.5,.5),(mid-.5,.5))
    # Two adjacent source triangles sharing an exact 3D diagonal.
    def source(points,index):
        return SourceFace(tuple((b,a,z) for a,b,z in points),0,'Diffuse',9,index)
    sources=(source(((x-4,-4.,0.),(x+4,-4.,0.),(x+4,4.,0.)),0),
             source(((x-4,-4.,0.),(x+4,4.,0.),(x-4,4.,0.)),1))
    reference=(mid-.25,0.,0.)
    original=check_ground_coverage(footprint,faces,reference=reference,component=2)
    assert original.reason=='uncovered_ground_area'
    return faces,links,footprint,sources,reference,original


def retry(data,*,links=None,sources=None,original=None,areas=None,components=None,limit=.6):
    faces,default_links,footprint,default_sources,reference,default_original=data
    seams=collect_seams(default_links if links is None else links,
                        {1:63,2:63} if areas is None else areas,
                        {1:2,2:2} if components is None else components)
    return retry_precision_gap(default_original if original is None else original,footprint,faces,(1,1,2,2),
        seams,default_sources if sources is None else sources,reference=reference,component=2,
        vertical_window=3.,maximum_source_z_difference=limit)


@pytest.mark.parametrize('x',(32.,1607.6439208984375,1761.2440185546875))
def test_one_ulp_gap_passes_with_continuous_two_face_source_partition(x):
    data=fixture(x);before=repr(data)
    result=retry(data)
    assert result.candidate and len(result.source_support.source_faces)==2
    assert result.coverage.covered_area==pytest.approx(result.coverage.footprint_area)
    assert not result.input_authorized and not result.real_client_accepted
    assert repr(data)==before
    midpoint=result.seams[0].midpoint
    assert struct.unpack('<f',struct.pack('<f',midpoint))[0]!=midpoint


def test_two_ulp_gap_is_never_corrected():
    assert not retry(fixture(steps=2)).candidate


def test_negative_float32_coordinates_keep_the_correct_midpoint():
    assert retry(fixture(neighbor(-32.),steps=-1)).candidate


def test_y_axis_portal_uses_the_same_source_frame_conversion():
    faces,links,footprint,sources,reference,_=fixture()
    swap=lambda p:(p[1],p[0],p[2])
    faces=tuple(replace(f,vertices=tuple(swap(p) for p in f.vertices)) for f in faces)
    links=tuple(replace(link,edge=tuple(swap(p) for p in link.edge)) for link in links)
    footprint=tuple((y,x) for x,y in footprint)
    sources=tuple(replace(s,vertices_wld=tuple(swap(p) for p in s.vertices_wld)) for s in sources)
    reference=swap(reference)
    original=check_ground_coverage(footprint,faces,reference=reference,component=2)
    result=retry((faces,links,footprint,sources,reference,original))
    assert result.candidate and result.seams[0].axis==1


def test_nonreciprocal_and_duplicate_links_are_refused():
    data=fixture();a,b=data[1]
    for links in ((a,),(a,replace(b,target=3)),(a,a,b)):
        assert not retry(data,links=links).candidate


@pytest.mark.parametrize('edge',(((neighbor(32.),2.001,0.),(neighbor(32.),-2.,0.)),
                                  ((neighbor(32.),2.,.001),(neighbor(32.),-2.,0.))))
def test_other_axis_or_height_endpoint_mismatch_refuses(edge):
    data=fixture();a,b=data[1]
    assert not retry(data,links=(a,replace(b,edge=edge))).candidate


@pytest.mark.parametrize('areas,components',(({1:63,2:1},{1:2,2:2}),({1:63,2:63},{1:2,2:3})))
def test_forbidden_area_and_other_component_refuse(areas,components):
    assert not retry(fixture(),areas=areas,components=components).candidate


@pytest.mark.parametrize('reason',('steep_detail_plane','forbidden_area_or_other_component',
                                  'overlapping_ground_faces','discontinuous_ground_seam'))
def test_noncoverage_failures_cannot_be_repaired(reason):
    result=retry(fixture(),original=GroundCoverage(False,reason))
    assert not result.candidate and result.reason=='original_failure_is_not_a_coverage_gap'


def test_source_partition_hole_refuses():
    data=fixture()
    assert not retry(data,sources=data[3][:1]).candidate


def test_overlapping_source_floor_is_not_discarded_by_height_filter():
    data=fixture();sources=data[3]
    upper=replace(sources[0],vertices_wld=tuple((x,y,z+20.) for x,y,z in sources[0].vertices_wld))
    assert not retry(data,sources=(*sources,upper)).candidate


def test_partial_overhead_surface_away_from_reference_is_still_ambiguous():
    data=fixture()
    # This raised triangle overlaps the right of the footprint but does not
    # contain its center/reference. A reference-only floor check would miss it.
    upper=SourceFace(((-.4,32.2,20.),(-.4,32.6,20.),(.4,32.6,20.)),0,'Diffuse')
    result=retry(data,sources=(*data[3],upper))
    assert not result.candidate and result.reason=='source_overlapping_ground_faces'


def test_unique_source_floor_far_below_baked_surface_refuses():
    data=fixture()
    sources=tuple(replace(s,vertices_wld=tuple((x,y,z-5.) for x,y,z in s.vertices_wld)) for s in data[3])
    result=retry(data,sources=sources)
    assert not result.candidate and result.reason=='source_baked_height_mismatch'


def test_whole_patch_height_difference_is_checked_not_just_reference():
    data=fixture()
    # Slope is allowed but its far patch edge exceeds the diagnostic Z bound.
    sources=tuple(replace(s,vertices_wld=tuple((x,y,.55+.5*(y-32.)) for x,y,z in s.vertices_wld)) for s in data[3])
    result=retry(data,sources=sources)
    assert not result.candidate and result.reason=='source_baked_height_mismatch'


def test_source_step_and_source_steep_plane_refuse():
    data=fixture();a,b=data[3]
    raised=replace(b,vertices_wld=tuple((x,y,z+.2) for x,y,z in b.vertices_wld))
    assert not retry(data,sources=(a,raised)).candidate
    steep=tuple(replace(s,vertices_wld=tuple((x,y,2*(y-32.)) for x,y,z in s.vertices_wld)) for s in (a,b))
    assert not retry(data,sources=steep).candidate


@pytest.mark.parametrize('change',({'flag':16},{'material_class':'Boundary'}))
def test_source_flag_or_material_refuses(change):
    data=fixture()
    assert not retry(data,sources=tuple(replace(s,**change) for s in data[3])).candidate


def test_source_external_edge_must_have_margin_beyond_footprint():
    data=fixture();footprint=data[2]
    sources=tuple(SourceFace(tuple((y,x,0.) for x,y in tri),0,'Diffuse')
                  for tri in ((footprint[0],footprint[1],footprint[2]),
                              (footprint[0],footprint[2],footprint[3])))
    assert not retry(data,sources=sources).candidate


def test_source_raw_xy_must_be_converted_at_the_frame_boundary():
    data=fixture()
    swapped=tuple(replace(s,vertices_wld=tuple((y,x,z) for x,y,z in s.vertices_wld)) for s in data[3])
    assert not retry(data,sources=swapped).candidate


def test_portal_span_does_not_authorize_shifting_other_boundary_vertices():
    data=fixture();a,b=data[1]
    links=(replace(a,edge=((32.,-.2,0.),(32.,.2,0.))),
           replace(b,edge=((neighbor(32.),.2,0.),(neighbor(32.),-.2,0.))))
    result=retry(data,links=links)
    assert not result.candidate and result.reason=='both_local_boundary_edges_required'
