from types import SimpleNamespace
from dataclasses import replace
import pytest

from eql_automation.native_region_policy import NativeZeroRegionTrialPolicy
from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_detour import swept_square
from tools.source_stair_plan import plan_stair_flight
from eql_automation.source_stair_plan import extend_stair_landing
from test_source_stair_topology import fixture
from test_source_step import face,rectangle
from test_bsp_volume import view as bsp_view,leaf
from test_client_classification import view as native_view


def setup(*,descending=False,upstairs=False,omitted_wall=False):
    sources,groups=fixture()
    full=sources
    if upstairs:
        full=(*full,*rectangle(-5.,0.,20.,90));sources=full
    if omitted_wall:
        full=(*full,face(((1.,-5.,0.),(1.,5.,0.),(1.,0.,10.)),99))
    start,end=((-2.,0.),(6.,0.)) if not descending else ((6.,0.),(-2.,0.))
    if descending:groups=tuple(reversed(groups))
    terrain=SimpleNamespace(wld_sha256='a'*64,archive_sha256='c'*64,sources=sources,
                            source_faces_for_footprint=lambda _:full)
    static=SimpleNamespace(inventory_sha256='d'*64,faces_for_footprint=lambda _:())
    prefix=SourceFloorChain(inventory_sha256='a'*64,seed_evidence_sha256='b'*64,
        seed_ids=((1,90),) if upstairs else groups[0][:1],body_height=6.)
    assert prefix.advance(swept_square(start,start,1.2),full).candidate
    bsp=bsp_view((leaf(1),));native=native_view((leaf(1),),wld_pin='a'*64)
    policy=NativeZeroRegionTrialPolicy('e'*64,'c'*64,'a'*64,'d'*64,
        bsp.inventory_sha256,native.inventory_sha256,native)
    return prefix,start,end,groups,terrain,static,bsp,policy


@pytest.mark.parametrize('descending',[False,True])
def test_only_final_planning_landing_links_to_original_floor(descending):
    args=setup(descending=descending);prefix=args[0];before=_chain_snapshot(prefix)
    plan,branch=plan_stair_flight(*args,radius=1.2,check_context=lambda:None)
    record=plan.record()
    assert _chain_snapshot(prefix)==before
    assert branch.previous.previous_sha256==prefix.previous.proof_sha256
    assert branch.previous.reason=='conditional_stair_flight_landing_only'
    assert branch.index==prefix.index+1
    assert branch.floor_at(args[2])[0] == (0. if descending else 3.)
    assert len(record['complete_phase_queries'])==record['flight']['phase_count']==9
    assert record['planned_landing_only'] and not record['executable_itinerary']
    with pytest.raises(ValueError,match='seal changed'):
        replace(plan,payload=plan.payload+b' ').record()


def test_same_xy_upstairs_prefix_cannot_be_replaced_by_lower_stair_floor():
    args=setup(upstairs=True);before=_chain_snapshot(args[0])
    with pytest.raises(ValueError,match='first stair tread'):
        plan_stair_flight(*args,radius=1.2,check_context=lambda:None)
    assert _chain_snapshot(args[0])==before


def test_complete_local_query_catches_a_wall_missing_from_whole_flight_list():
    args=setup(omitted_wall=True);before=_chain_snapshot(args[0])
    with pytest.raises(ValueError,match='query differs from flight inventory'):
        plan_stair_flight(*args,radius=1.2,check_context=lambda:None)
    assert _chain_snapshot(args[0])==before


def test_same_id_landing_geometry_cannot_change_after_phase_checks():
    args=setup();prefix,_,end,_,terrain,_,_,_=args
    before=_chain_snapshot(prefix);original_query=terrain.source_faces_for_footprint
    final_cap=swept_square(end,end,1.2)
    changed=[]
    def query(cap):
        sources=original_query(cap)
        if cap != final_cap:
            return sources
        changed.append(True)
        # Same height and IDs, with a changed shared diagonal and outer edge.
        # It still supports the full landing, so identity must be checked too.
        return tuple(replace(s,vertices_wld=tuple((x,10. if y==9. else y,z)
            for x,y,z in s.vertices_wld)) if s.face in (6,7) else s for s in sources)
    terrain.source_faces_for_footprint=query
    with pytest.raises(ValueError,match='Final landing query differs from flight inventory'):
        plan_stair_flight(*args,radius=1.2,check_context=lambda:None)
    assert changed and _chain_snapshot(prefix)==before


@pytest.mark.parametrize('hazard',[None,'gap','wall','height'])
def test_lookahead_checks_connected_landing_faces_and_full_far_cap(hazard):
    prefix,start,target,groups,terrain,static,bsp,policy=setup()
    old=_chain_snapshot(prefix)
    sources=tuple(s for s in terrain.sources if s.face not in (6,7))
    sources+=rectangle(4.,7.5,3.,6)
    sources+=rectangle(7.51 if hazard=='gap' else 7.5,12.,3.1 if hazard=='height' else 3.,100)
    if hazard=='wall':sources+=(face(((8.,-5.,3.),(8.,5.,3.),(8.,0.,12.)),200),)
    terrain.sources=sources;terrain.source_faces_for_footprint=lambda _:sources
    def extend():return extend_stair_landing(prefix,target,(9.,0.),groups,terrain,static,bsp,policy,
        radius=1.2,check_context=lambda:None)
    if hazard:
        with pytest.raises(ValueError):extend()
    else:
        extended,evidence=extend()
        assert extended[-1]==((1,6),(1,7),(1,100),(1,101))
        assert target==(6.,0.) and evidence['checked_end']==(9.,0.)
        plan,branch=plan_stair_flight(prefix,start,(9.,0.),extended,terrain,static,bsp,policy,
            radius=1.2,body_radius=.1,vertical_model='bounded_source_contacts',check_context=lambda:None)
        assert branch.floor_at((9.,0.))[0]==3.
        assert set(plan.record()['landing']['selected_ids'][0])=={1,100}
    assert _chain_snapshot(prefix)==old
