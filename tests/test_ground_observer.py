from dataclasses import replace
from datetime import datetime
from types import SimpleNamespace

import pytest

from eql_automation.fixed_route_follower import FixedRoute,FixedSegment
from eql_automation.ground_binding import HeightCalibration,GroundGeometryEvidence
from eql_automation.ground_observer import RouteGroundObserver,exact_detail_support,GroundObservationUnavailable
from eql_automation.location_log import RawLocationFix
from eql_automation.unbound_location_log import UnboundLocationObservation

MESH,ARCHIVE,WLD,PROOF=('a'*64,'b'*64,'c'*64,'d'*64)
HEIGHT=HeightCalibration('synthetic-test-height','fixture',54,'Fixture',1,1,ARCHIVE,WLD,
                         2.5,.05,0,0.,200.,live_verified=True)
GEOMETRY=GroundGeometryEvidence('fixture',MESH,ARCHIVE,WLD,PROOF,1.,((0,1),),True)
ROUTE=FixedRoute('fixture',MESH,'e'*64,1.2,(FixedSegment(0,(1.,2.,.6),(2.,2.,.6)),
                                        FixedSegment(1,(2.,2.,.6),(3.,2.,.6))))


def rectangle(left,right,z=.6):
    a,b,c,d=(left,0.,z),(right,0.,z),(right,4.,z),(left,4.,z)
    return ((a,b,c),(a,c,d))


class Source:
    archive_sha256=ARCHIVE;wld_sha256=WLD
    def __init__(self):self.calls=[];self.height=.2;self.error=None
    def source_floor_at(self,xy):
        self.calls.append(xy)
        if self.error:raise ValueError(self.error)
        return self.height,('wld:1:face:0',)


def fixture(first=None,second=None):
    first=rectangle(0.,2.) if first is None else first
    second=rectangle(2.,4.) if second is None else second
    mesh=SimpleNamespace(area=(63,63),_detail=first+second,_detail_start=(0,len(first),len(first)+len(second)))
    ground=SimpleNamespace(areas=(63,63),components=(7,7));source=Source()
    observer=RouteGroundObserver(mesh=mesh,ground=ground,source=source,
                                geometry_evidence=GEOMETRY,reciprocal_links=((0,1),(1,0)))
    return observer,mesh,ground,source


def raw(x=1.,y=2.,z=2.7,**kwargs):
    return replace(RawLocationFix(54,'Fixture',(y,x,z),datetime(2026,11,14),100.,1,1,1),**kwargs)


def observe(observer,fix=None,**kwargs):
    args=dict(route=ROUTE,segment_index=0,height_calibration=HEIGHT,
              motion_calibration_record_id='synthetic-test-motion',now=100.)
    args.update(kwargs)
    return observer.observe(raw() if fix is None else fix,**args)


def test_preserves_raw_calibration_identity_and_all_three_distinct_heights():
    observer,mesh,ground,source=fixture();fix=raw();aligned=observe(observer,fix)
    assert aligned.raw_fix is fix and aligned.source_floor.raw_fix is fix and aligned.mesh_projection.raw_fix is fix
    assert aligned.height_calibration is HEIGHT
    assert aligned.source_floor.ground_wld_xyz==(2.,1.,.2)
    assert aligned.mesh_projection.package_xyz==(1.,2.,.6)
    assert fix.raw_coordinates==(2.,1.,2.7) and source.calls==[(1.,2.)]
    assert aligned.mesh_projection.verified_neighbor_polygons==(1,)


def test_current_polygon_wins_at_shared_portal_even_when_neighbor_height_is_closer():
    observer,*_=fixture(second=rectangle(2.,4.,.2))
    aligned=observe(observer,raw(x=2.))
    assert aligned.mesh_projection.polygon==0 and aligned.mesh_projection.package_xyz[2]==.6


def test_absent_current_support_allows_only_selected_nearby_reciprocal_neighbor():
    observer,*_=fixture()
    aligned=observe(observer,raw(x=2.1))
    assert aligned.mesh_projection.polygon==1 and aligned.mesh_projection.package_xyz[:2]==(2.1,2.)
    with pytest.raises(GroundObservationUnavailable):observe(observer,raw(x=2.3))
    disconnected=replace(ROUTE,segments=(ROUTE.segments[0],))
    with pytest.raises(GroundObservationUnavailable):observe(observer,raw(x=2.1),route=disconnected)


def test_ambiguous_current_support_never_falls_through_to_neighbor():
    observer,*_=fixture(first=rectangle(0.,2.)+rectangle(0.,2.,.7))
    with pytest.raises(GroundObservationUnavailable,match='Current polygon has ambiguous'):
        observe(observer,raw(x=2.))


def test_supported_current_bad_height_never_chooses_convenient_neighbor():
    observer,*_=fixture(first=rectangle(0.,2.,4.),second=rectangle(2.,4.,.2))
    with pytest.raises(GroundObservationUnavailable,match='same_floor_bound'):
        observe(observer,raw(x=2.))


def test_exact_query_refuses_nearby_edge_projection_and_missing_mesh_data():
    observer,mesh,*_=fixture(second=rectangle(2.001,4.))
    assert exact_detail_support(mesh,0,(2.0001,2.)).status=='absent'
    with pytest.raises(GroundObservationUnavailable):observe(observer,raw(x=2.0001))
    mesh._detail_start=(0,0,4)
    with pytest.raises(GroundObservationUnavailable,match='Missing'):observe(observer)


@pytest.mark.parametrize('change',['layered','source_hash','raw_height','expired','unverified','epoch','stale','unbound'])
def test_unverified_calibration_source_or_fix_cannot_be_promoted(change):
    observer,mesh,ground,source=fixture();kwargs={};fix=raw()
    if change=='layered':source.error='layered source floor'
    elif change=='source_hash':source.wld_sha256='f'*64
    elif change=='raw_height':fix=raw(z=3.)
    elif change=='expired':kwargs['height_calibration']=replace(HEIGHT,valid_until_monotonic=99.)
    elif change=='unverified':kwargs['height_calibration']=replace(HEIGHT,live_verified=False)
    elif change=='epoch':fix=raw(log_epoch=2)
    elif change=='stale':kwargs['now']=100.51
    elif change=='unbound':fix=UnboundLocationObservation((2.,1.,2.7),datetime(2026,11,14),100.,1,1)
    with pytest.raises(GroundObservationUnavailable):observe(observer,fix,**kwargs)


def test_reciprocal_dry_same_component_context_is_checked():
    observer,mesh,ground,source=fixture()
    for links,areas,components in [(((0,1),),(63,63),(7,7)),(((0,1),(1,0)),(63,1),(7,7)),
                                    (((0,1),(1,0)),(63,63),(7,8))]:
        ground.areas=areas;ground.components=components
        with pytest.raises(GroundObservationUnavailable):
            RouteGroundObserver(mesh=mesh,ground=ground,source=source,
                                geometry_evidence=GEOMETRY,reciprocal_links=links)


def test_source_floor_chain_is_sampled_without_advancement_on_success_or_refusal():
    from eql_automation.source_floor_chain import SourceFloorChain
    from eql_automation.portal_precision import SourceFace
    source_vertices=rectangle(0.,4.,.2)
    faces=tuple(SourceFace(v,0,'Diffuse',1,i) for i,v in enumerate(source_vertices))
    chain=SourceFloorChain(inventory_sha256=WLD,seed_evidence_sha256='f'*64,
                           seed_ids=((1,0),(1,1)),body_height=8.)
    step=chain.advance(((.1,.1),(3.9,.1),(3.9,3.9),(.1,3.9)),faces)
    assert step.candidate
    before=(chain.index,chain.previous,chain._selected,chain._expanded)
    chain.advance=lambda *a,**k:pytest.fail('observation advanced source floor')
    observer,*_=fixture()
    aligned=observe(observer,floor_chain=chain)
    assert aligned.source_floor.source_surface_ids
    with pytest.raises(GroundObservationUnavailable):observe(observer,raw(z=5.),floor_chain=chain)
    assert (chain.index,chain.previous,chain._selected,chain._expanded)==before
    assert chain._selected is before[2] and chain.previous is before[1]
    chain.inventory_sha256='0'*64
    with pytest.raises(GroundObservationUnavailable,match='inventory'):observe(observer,floor_chain=chain)


def test_produced_observations_feed_the_actual_retained_follower():
    import importlib.util
    from hashlib import sha256
    from pathlib import Path
    import sys
    if importlib.util.find_spec('numpy') is None:pytest.skip('Retained helper requires numpy')
    from eql_automation.fixed_route_follower import FixedRouteFollower
    from test_fixed_route_follower import HELPER,PINS
    if not HELPER.exists():pytest.skip('Retained helper source is required')
    for name,expected in PINS.items():assert sha256((HELPER/name).read_bytes()).hexdigest()==expected
    sys.path.insert(0,str(HELPER))
    from eqnav import steer
    observer,*_=fixture()
    runner=FixedRouteFollower(ROUTE,legacy=steer,
        motion=steer.Motion(run_speed=10.,turn_rate=170.,right_sign=-1,turn_latency=.03,back_speed=5.),
        heading=90.,calibration_record_id='synthetic-test-motion',height_calibration=HEIGHT,
        geometry_evidence=GEOMETRY,generation=1,generation_reader=lambda:1,mode_reader=lambda:'measurement')
    seq=0
    def pair(x,release):
        nonlocal seq
        result=[]
        for delta in (.13,.53):
            seq+=1;at=release+delta
            fix=raw(x=x,received_monotonic=at,log_line_seq=seq)
            result.append(observe(observer,fix,segment_index=runner.index,now=at))
        return result
    runner.observe_stopped(*pair(1.,100.),released_at=100.,now=100.53)
    for target in (2.,3.):
        proposal=runner.propose(runner.last_at+.01)
        start=proposal.at+.01;released=start+.1
        runner.record_release(proposal,started_at=start,released_at=released)
        runner.observe_stopped(*pair(target,released),released_at=released,now=released+.53)
    assert runner.phase=='arrived' and runner.index==2
