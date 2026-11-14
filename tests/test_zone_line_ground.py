"""Explicit transition observations retain actual areas; no input is issued."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from eql_automation.ground_binding import validate_ground_binding
from eql_automation.ground_observer import RouteGroundObserver,GroundObservationUnavailable
from eql_automation.zone_line import ExpectedZoneLine
from test_ground_observer import fixture,GEOMETRY,HEIGHT,ROUTE,raw


def context():
    _,mesh,ground,source=fixture()
    mesh.area=ground.areas=(63,4)
    mesh.mesh_sha256=ground.mesh_sha256=GEOMETRY.mesh_sha256
    line=ExpectedZoneLine('ground-fixture','fixture',GEOMETRY.mesh_sha256,
        GEOMETRY.source_archive_sha256,GEOMETRY.source_wld_sha256,'f'*64,'e'*64,
        'DRNTP00255000004_ZONE',4,(1,),(0,))
    geometry=replace(GEOMETRY,expected_zone_line=line)
    observer=RouteGroundObserver(mesh=mesh,ground=ground,source=source,
        geometry_evidence=geometry,reciprocal_links=((0,1),(1,0)))
    return SimpleNamespace(observer=observer,mesh=mesh,ground=ground,source=source,line=line,geometry=geometry)


def observe(f,*,x=2.1,index=1):
    return f.observer.observe(raw(x=x),route=ROUTE,segment_index=index,height_calibration=HEIGHT,
        motion_calibration_record_id='synthetic-test-motion',now=100.,mode='measurement')


def check(f,value,geometry=None):
    return validate_ground_binding(value,height_calibration=HEIGHT,
        geometry_evidence=f.geometry if geometry is None else geometry,mesh_sha256=GEOMETRY.mesh_sha256,
        zone_short_name='fixture',now=100.,motion_calibration_record_id='synthetic-test-motion',mode='measurement')


@pytest.mark.parametrize('index',[0,1])
def test_exact_line_support_and_adjacent_fallback_keep_actual_area(index):
    f=context();value=observe(f,index=index)
    assert value.mesh_projection.area==4 and value.mesh_projection.polygon==1
    assert value.mesh_projection.expected_zone_line_sha256==f.line.sha256
    assert value.mesh_projection.package_xyz[:2]==(2.1,2.) and check(f,value).candidate
    assert not check(f,value).input_authorized


@pytest.mark.parametrize('change',['area','hash','polygon','context','source'])
def test_transition_observation_cannot_be_relabelled_or_detached(change):
    f=context();value=observe(f);projection=value.mesh_projection
    geometry=f.geometry
    if change=='area':projection=replace(projection,area=63)
    elif change=='hash':projection=replace(projection,expected_zone_line_sha256=None)
    elif change=='polygon':projection=replace(projection,polygon=0)
    elif change=='context':geometry=GEOMETRY
    else:geometry=replace(geometry,expected_zone_line=replace(f.line,wld_sha256='d'*64))
    assert not check(f,replace(value,mesh_projection=projection),geometry).candidate


def test_dry_prefix_retains_same_context_and_default_stays_dry_only():
    f=context();value=observe(f,x=1.,index=0)
    assert value.mesh_projection.area==63 and check(f,value).candidate
    assert value.mesh_projection.expected_zone_line_sha256==f.line.sha256
    with pytest.raises(GroundObservationUnavailable):
        RouteGroundObserver(mesh=f.mesh,ground=f.ground,source=f.source,
            geometry_evidence=GEOMETRY,reciprocal_links=((0,1),(1,0)))


@pytest.mark.parametrize('change',['water','mesh_disagrees','line_changed'])
def test_changed_or_unexpected_area_is_not_observed(change):
    f=context()
    if change=='water':f.mesh.area=f.ground.areas=(63,1)
    elif change=='mesh_disagrees':f.mesh.area=(63,63)
    else:f.observer.geometry=replace(f.geometry,expected_zone_line=replace(f.line,crossing_id='other'))
    with pytest.raises(GroundObservationUnavailable):observe(f)
