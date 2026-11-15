from dataclasses import replace
import math
from types import SimpleNamespace

import pytest

from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_detour import swept_square,find_source_detour
from eql_automation.source_itinerary import plan_source_itinerary,SourceStepHint
from eql_automation.source_step_links import discover_step_links
from eql_automation.source_transit_graph import SourceTransitGraph,SourceTransitProposal,TransitEdge
from test_source_step import rectangle,setup,face
from test_source_itinerary import fixture as checked_fixture


@pytest.mark.parametrize('zone', ('crushbone', 'butcher'))
def test_long_connected_surface_builds_short_cells_and_rebuilds_without_changing_prefix(zone):
    _,_,terrain,static,bsp,policy=checked_fixture()
    policy=replace(policy,zone=zone)
    sources=rectangle(0.,200.,0.,0)
    terrain.source_faces_for_footprint=lambda _:sources
    start=(10.,0.);goal=(190.,0.)
    chain=SourceFloorChain(inventory_sha256='a'*64,seed_evidence_sha256='b'*64,seed_ids=((1,1),),body_height=6.)
    assert chain.advance(swept_square(start,start,.5),sources).candidate
    before=_chain_snapshot(chain)
    with pytest.raises(ValueError,match='bounded'):find_source_detour(chain,start,goal,terrain,static,radius=.5)
    proposal=SourceTransitGraph(sources,inventory_sha256='a'*64,radius=.5).propose(chain,start,goal)
    guide=proposal.guide(static_inventory_sha256='d'*64,radius=.5,body_height=6.,zone=zone)
    assert all(math.dist(op.start,op.end)<=2.0000001 for op in guide.operations)
    plan=plan_source_itinerary(chain,start,guide,terrain,static,bsp,policy,check_context=lambda:None).record()
    assert plan['goal']==list(goal) and plan['goal_floor_height']==0 and plan['zone']==zone
    assert all(row['native']['possible_flags']==[0] for row in plan['cells'])
    assert _chain_snapshot(chain)==before and not proposal.input_authorized and not plan['real_client_accepted']


def test_generated_step_and_reverse_routes_keep_explicit_landings_and_full_checks():
    chain,_,terrain,static,bsp,policy=checked_fixture()
    sources=terrain.source_faces_for_footprint(())
    links=discover_step_links(sources,inventory_sha256='a'*64,max_step_height=.5)
    graph=SourceTransitGraph(sources,inventory_sha256='a'*64,step_links=links,radius=1.,max_step_height=.5,max_lift=1.)
    proposal=graph.propose(chain,(-2.,0.),(2.,0.))
    guide=proposal.guide(static_inventory_sha256='d'*64,radius=1.,body_height=6.)
    assert any(type(op) is SourceStepHint for op in guide.operations)
    with pytest.raises(ValueError,match='ordinary walking only'):
        proposal.guide(static_inventory_sha256='d'*64,radius=1.,body_height=6.,zone='butcher')
    plan=plan_source_itinerary(chain,(-2.,0.),guide,terrain,static,bsp,policy,check_context=lambda:None).record()
    assert plan['goal_floor_height']==.3125
    assert [row['transfer']['evidence']['direction'] for row in plan['cells'] if row['kind']=='step']==['up']
    upper=SourceFloorChain(inventory_sha256='a'*64,seed_evidence_sha256='c'*64,seed_ids=((1,2),),body_height=6.)
    assert upper.advance(swept_square((2.,0.),(2.,0.),1.),sources).candidate
    back=graph.propose(upper,(2.,0.),(-2.,0.)).guide(static_inventory_sha256='d'*64,radius=1.,body_height=6.)
    plan=plan_source_itinerary(upper,(2.,0.),back,terrain,static,bsp,policy,check_context=lambda:None).record()
    assert plan['goal_floor_height']==0
    assert [row['transfer']['evidence']['direction'] for row in plan['cells'] if row['kind']=='step']==['down']


@pytest.mark.parametrize('start_via_edges', (False, True))
def test_coincident_projected_edges_do_not_connect_different_height_layers(start_via_edges):
    chain,start,goal,terrain,_=setup()
    sources=tuple(replace(f,vertices_wld=tuple((x,y,z+10) for x,y,z in f.vertices_wld))
                  if f.face in (2,3) else f for f in terrain.source_faces_for_footprint(()))
    graph=SourceTransitGraph(sources,inventory_sha256='a'*64)
    before=_chain_snapshot(chain)
    assert graph.propose(chain,start,goal,start_via_edges=start_via_edges) is None
    assert _chain_snapshot(chain)==before


@pytest.mark.parametrize('start_via_edges', (False, True))
def test_graph_proposal_does_not_bypass_a_static_wall_or_make_it_walkable(start_via_edges):
    chain,_,terrain,static,bsp,policy=checked_fixture()
    sources=rectangle(-5.,5.,0.,0);terrain.source_faces_for_footprint=lambda _:sources
    chain=SourceFloorChain(inventory_sha256='a'*64,seed_evidence_sha256='b'*64,seed_ids=((1,1),),body_height=6.)
    start=(-2.,0.);goal=(2.,0.)
    assert chain.advance(swept_square(start,start,.5),sources).candidate
    static.faces_for_footprint=lambda _:(face(((0.,-20.,-1.),(0.,20.,-1.),(0.,0.,20.)),0,7),)
    proposal=SourceTransitGraph(sources,inventory_sha256='a'*64,radius=.5).propose(
        chain,start,goal,start_via_edges=start_via_edges)
    assert proposal is not None
    guide=proposal.guide(static_inventory_sha256='d'*64,radius=.5,body_height=6.)
    with pytest.raises(ValueError,match='static|connector'):
        plan_source_itinerary(chain,start,guide,terrain,static,bsp,policy,check_context=lambda:None)


def test_start_can_leave_current_face_without_visiting_its_blocked_center():
    _,_,terrain,static,bsp,policy=checked_fixture()
    sources=rectangle(0.,20.,0.,0);terrain.source_faces_for_footprint=lambda _:sources
    start=(8.,0.);goal=(17.,0.)
    chain=SourceFloorChain(inventory_sha256='a'*64,seed_evidence_sha256='b'*64,
        seed_ids=((1,1),),body_height=6.)
    assert chain.advance(swept_square(start,start,.25),sources).candidate
    assert chain.previous.selected_ids==((1,1),)
    before=_chain_snapshot(chain)
    static.faces_for_footprint=lambda _:(face(((20/3,0.,0.),(20/3,4.,0.),(20/3,2.,12.)),0,7),)
    graph=SourceTransitGraph(sources,inventory_sha256='a'*64,radius=.25)
    ordinary=graph.propose(chain,start,goal)
    assert ordinary==graph.propose(chain,start,goal,start_via_edges=False)
    assert ordinary.edges[0].identity==('start',(1,1))
    def rebuild(proposal):
        guide=proposal.guide(static_inventory_sha256='d'*64,radius=.25,body_height=6.)
        return plan_source_itinerary(chain,start,guide,terrain,static,bsp,policy,
            check_context=lambda:None,max_connect_distance=0.,max_connect_attempts=1).record()
    with pytest.raises(ValueError,match='static|connector'):rebuild(ordinary)
    alternate=graph.propose(chain,start,goal,start_via_edges=True)
    attachment=alternate.edges[0]
    shared=graph.adjacent[(1,1)][0]
    assert attachment.identity==('start-via-edge',shared.identity)
    assert attachment.origin==('start',) and attachment.destination==(1,0)
    assert attachment.points==((*start,0.),*shared.points[1:])
    plan=rebuild(alternate)
    assert plan['goal']==list(goal) and plan['goal_floor_height']==0
    assert all(row['native']['possible_flags']==[0] for row in plan['cells'])
    assert not plan['input_authorized'] and not plan['real_client_accepted']
    assert _chain_snapshot(chain)==before
    # An excluded crossing cannot be reintroduced through the new root edge.
    assert graph.propose(chain,start,goal,start_via_edges=True,
        excluded=(shared.identity,)) is None
    centroid=graph.propose(chain,start,goal,start_via_edges=True,
        excluded=(attachment.identity,))
    assert centroid.edges[0].identity==ordinary.edges[0].identity


@pytest.mark.parametrize('invalid', (None, 1, 'yes'))
def test_start_edge_option_requires_an_explicit_boolean(invalid):
    chain,start,goal,terrain,_=setup()
    graph=SourceTransitGraph(terrain.source_faces_for_footprint(()),inventory_sha256='a'*64)
    with pytest.raises(ValueError,match='bounded'):
        graph.propose(chain,start,goal,start_via_edges=invalid)


def test_excluded_directed_crossing_changes_proposal_without_claiming_disconnection():
    chain,start,goal,terrain,_=setup();sources=terrain.source_faces_for_footprint(())
    links=discover_step_links(sources,inventory_sha256='a'*64,max_step_height=.5)
    graph=SourceTransitGraph(sources,inventory_sha256='a'*64,step_links=links,radius=1.,max_step_height=.5,max_lift=1.)
    first=graph.propose(chain,start,goal)
    step=next(e for e in first.edges if e.step is not None)
    second=graph.propose(chain,start,goal,excluded=(step.identity,))
    assert second is not None and all(e.identity!=step.identity for e in second.edges)
    with pytest.raises(TimeoutError,match='budget'):graph.propose(chain,start,goal,max_expansions=1)


def test_subdivision_preserves_exact_endpoint_after_fractional_center():
    start=(-4030.3333333333335,0.);goal=(211.25,0.)
    edge=TransitEdge(('walk',),(1,0),(2,0),((*start,0.),(*goal,0.)))
    proposal=SourceTransitProposal(start,goal,(edge,),'a'*64,'b'*64,1)
    guide=proposal.guide(static_inventory_sha256='d'*64,radius=1.,body_height=6.)
    assert guide.operations[-1].end==goal
    assert all(a.end==b.start for a,b in zip(guide.operations,guide.operations[1:]))


@pytest.mark.parametrize('times',[(float('nan'),),(0.,-1.),(0.,float('inf'))])
def test_invalid_clock_refuses_proposal(times):
    chain,start,goal,terrain,_=setup()
    graph=SourceTransitGraph(terrain.source_faces_for_footprint(()),inventory_sha256='a'*64)
    clock=iter(times)
    with pytest.raises(ValueError,match='clock'):graph.propose(chain,start,goal,clock=lambda:next(clock))


def test_construction_checks_edge_budget_before_building_quadratic_adjacency():
    with pytest.raises(ValueError,match='edge budget'):
        SourceTransitGraph(rectangle(-5.,5.,0.,0),inventory_sha256='a'*64,max_edges=1)
