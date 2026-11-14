from dataclasses import asdict
from types import SimpleNamespace

import pytest

from eql_automation.portal_precision import SourceFace
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_detour import find_source_detour,swept_square


FLOOR=SourceFace(((-100.,-100.,0.),(-100.,100.,0.),(100.,0.,0.)),0,'Diffuse',1,0)


def fixture(obstacles=(),terrain=(FLOOR,)):
    view=SimpleNamespace(wld_sha256='a'*64,source_faces_for_footprint=lambda _:terrain)
    static=SimpleNamespace(inventory_sha256='d'*64,faces_for_footprint=lambda _:obstacles)
    start=(-4.,0.);goal=(4.,0.)
    chain=SourceFloorChain(inventory_sha256=view.wld_sha256,seed_evidence_sha256='b'*64,
                           seed_ids=((1,0),),body_height=4.)
    assert chain.advance(swept_square(start,start,.5),terrain).candidate
    return chain,start,goal,view,static


def wall(y_low=-1.5,y_high=1.5):
    # WLD X is helper Y; this upright wall crosses helper X=0.
    return SourceFace(((y_low,0.,-1.),(y_high,0.,-1.),(0.,0.,20.)),16,'TransparentMasked',2,0)


def solve(args,**kwargs):
    return find_source_detour(*args,radius=.5,spacing=1.,padding=3.,**kwargs)


def test_direct_path_returns_a_new_chained_prefix_and_no_live_authority():
    args=fixture();original=args[0];before=asdict(original.previous)
    result,final=solve(args)
    assert result.candidate and result.points==((-4.,0.),(4.,0.))
    assert len(result.cells)==3 and final.previous==result.cells[-1].terrain
    previous=original.previous.proof_sha256
    for cell in result.cells:
        assert cell.terrain.candidate and cell.static.candidate
        assert cell.terrain.previous_sha256==previous
        previous=cell.terrain.proof_sha256
    assert asdict(original.previous)==before and not original.halted
    assert not result.bsp_classified and not result.input_authorized and not result.real_client_accepted


def test_finds_bypass_around_static_wall_and_checks_entire_turn_footprints():
    args=fixture((wall(),));result,final=solve(args)
    assert result.candidate and final is not None
    assert len(result.points)>2 and max(abs(y) for _,y in result.points)>=2.
    assert dict(result.refusals)['other_source_surface_intersects_body_band']>0
    # Each move has a swept square and canonical endpoint cap, not merely
    # point samples that could miss this thin wall between lattice points.
    for i in range(1,len(result.cells),2):
        sweep,cap=result.cells[i:i+2]
        assert sweep.footprint==swept_square(sweep.start,sweep.end,.5)
        assert cap.start==cap.end==sweep.end
        assert cap.footprint==swept_square(cap.start,cap.end,.5)


def test_solid_barrier_or_exhausted_budget_returns_no_partial_route():
    args=fixture((wall(-100.,100.),))
    result,final=solve(args,max_expansions=12)
    assert not result.candidate and final is None and not result.points and not result.cells
    assert result.reason=='detour_expansion_budget_exceeded'
    assert not args[0].halted and args[0].index==1


def test_overhead_terrain_is_never_selected_as_a_reseeded_floor():
    roof=SourceFace(tuple((x,y,z+10.) for x,y,z in FLOOR.vertices_wld),0,'Diffuse',3,0)
    result,final=solve(fixture(terrain=(FLOOR,roof)))
    assert result.candidate
    assert all(c.terrain.selected_ids==((1,0),) for c in result.cells)
    assert final.floor_at((4.,0.))[0]==0.


def test_query_refusal_does_not_reuse_a_partial_candidate_or_damage_prefix():
    args=fixture()
    def refused(_):raise ValueError('inventory budget')
    args[3].source_faces_for_footprint=refused
    result,final=solve(args)
    assert not result.candidate and result.reason=='detour_start_refused'
    assert final is None and not args[0].halted


def test_fork_refusal_isolated_and_bad_inventory_rejected():
    args=fixture();original=args[0];branch=original.fork()
    assert not branch.advance(swept_square((500.,0.),(500.,0.),.5),(FLOOR,)).candidate
    assert branch.halted and not original.halted
    with pytest.raises(ValueError):branch.fork()
    args[3].wld_sha256='e'*64
    with pytest.raises(ValueError):solve(args)


def test_arbitrary_goal_rejoins_suffix_without_reseeding_or_switching_floor():
    roof=SourceFace(tuple((x,y,z+10.) for x,y,z in FLOOR.vertices_wld),0,'Diffuse',3,0)
    lower,start,_,view,static=fixture(terrain=(FLOOR,roof))
    goal=(3.25,.375)
    for seed,chain in ((((1,0),),lower),(((3,0),),None)):
        if chain is None:
            chain=SourceFloorChain(inventory_sha256=view.wld_sha256,seed_evidence_sha256='b'*64,
                                   seed_ids=seed,body_height=4.)
            assert chain.advance(swept_square(start,start,.5),(FLOOR,roof)).candidate
        result,final=solve((chain,start,goal,view,static))
        assert result.candidate and final.previous.selected_ids==seed
        suffix,continued=solve((final,goal,(6.,.375),view,static))
        assert suffix.candidate and continued.previous.selected_ids==seed
        assert suffix.cells[0].terrain.previous_sha256==final.previous.proof_sha256
        assert final.seed_evidence_sha256==continued.seed_evidence_sha256==chain.seed_evidence_sha256
