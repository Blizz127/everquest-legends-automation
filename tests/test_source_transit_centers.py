from types import SimpleNamespace

import pytest

from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_itinerary import plan_source_itinerary
from eql_automation.source_transit_graph import SourceTransitGraph
from tools.source_transit_centers import filter_transit_centers
from test_source_itinerary import fixture
from test_source_step import face


def fan():
    _,_,terrain,static,bsp,policy=fixture()
    a,b,c,d,o=(-10.,-10.,0.),(10.,-10.,0.),(10.,14.,0.),(-10.,14.,0.),(0.,0.,0.)
    sources=tuple(face(vertices,i) for i,vertices in enumerate(((a,b,o),(b,c,o),(c,d,o),(d,a,o))))
    terrain.source_faces_for_footprint=lambda _:sources
    static.faces_for_footprint=lambda _:(face(((0.,8.7,.5),(0.,10.,.5),(0.,28/3,8.)),0,7),)
    start,goal=(-6.,1.),(6.,1.)
    prefix=SourceFloorChain(inventory_sha256='a'*64,seed_evidence_sha256='b'*64,
        seed_ids=((1,3),),body_height=6.)
    assert prefix.advance(swept_square(start,start,1.2),sources).candidate
    graph=SourceTransitGraph(sources,inventory_sha256='a'*64,radius=1.2)
    return prefix,start,goal,graph,SimpleNamespace(source=terrain,static=static),bsp,policy


@pytest.mark.parametrize('start_via_edges', (False, True))
def test_only_blocked_center_is_removed_and_alternative_rebuilds(start_via_edges):
    prefix,start,goal,graph,planner,bsp,policy=fan()
    before=_chain_snapshot(prefix);goal_layers=graph.components.goal(prefix,goal)
    original=graph.propose(prefix,start,goal,start_via_edges=start_via_edges)
    assert (1,2) in [e.destination for e in original.edges]
    def rebuild(proposal):
        guide=proposal.guide(static_inventory_sha256='d'*64,radius=1.2,body_height=6.)
        return plan_source_itinerary(prefix,start,guide,planner.source,planner.static,bsp,policy,
            check_context=lambda:None,max_connect_distance=0,max_connect_attempts=1).record()
    with pytest.raises(ValueError,match='static'):rebuild(original)
    snapshots=[]
    proposal=filter_transit_centers(graph,prefix,start,goal,planner,rounds=2,
        start_via_edges=start_via_edges,check=lambda:None,
        progress=lambda attempts,cache,count:snapshots.append((list(attempts),dict(cache),count)))
    attempts,cache,excluded=snapshots[-1]
    assert len(attempts)==2 and excluded
    assert {k for k,v in cache.items() if v['excluded_center']}=={(1,2)}
    assert all(e.destination!=(1,2) for e in proposal.edges)
    assert (1,0) in [e.destination for e in proposal.edges]
    result=rebuild(proposal)
    assert result['goal']==list(goal)
    assert all(c['native']['possible_flags']==[0] for c in result['cells'])
    assert not result['input_authorized'] and not result['real_client_accepted']
    assert _chain_snapshot(prefix)==before and graph.components.goal(prefix,goal)==goal_layers


def test_query_error_is_not_a_blocked_center_or_disconnection():
    prefix,start,goal,graph,planner,_,_=fan()
    def fail(_):raise ValueError('Source inventory changed')
    planner.source.source_faces_for_footprint=fail
    with pytest.raises(ValueError,match='Source inventory changed'):
        filter_transit_centers(graph,prefix,start,goal,planner,rounds=2,
            check=lambda:None,progress=lambda *_:None)


def test_center_budget_and_progress_scope_changes_refuse():
    prefix,start,goal,graph,planner,_,_=fan()
    before=_chain_snapshot(prefix)
    with pytest.raises(ValueError,match='query count exhausted'):
        filter_transit_centers(graph,prefix,start,goal,planner,rounds=2,
            maximum_caps=1,check=lambda:None,progress=lambda *_:None)
    assert _chain_snapshot(prefix)==before
    def changed(*_):prefix.index+=1
    with pytest.raises(ValueError,match='prefix changed|No committed conditional source floor'):
        filter_transit_centers(graph,prefix,start,goal,planner,rounds=2,
            check=lambda:None,progress=changed)
