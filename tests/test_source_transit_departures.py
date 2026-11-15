from dataclasses import replace

import pytest

from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_itinerary import plan_source_itinerary
from tools.source_transit_departures import filter_transit_departures
from test_source_transit_centers import fan
from test_source_step import face


def blocked_exit():
    prefix,start,goal,graph,p,bsp,policy=fan()
    # North centroid is clear; its shared-edge approach is obstructed.
    p.static.faces_for_footprint=lambda _:(face(((-6.,6.5,0.),(-4.,6.5,0.),(-5.,6.5,10.)),0,7),)
    p.bsp=bsp;p.region_policy=policy
    return prefix,start,goal,graph,p


def test_clear_centers_can_use_another_checked_departure():
    prefix,start,goal,graph,p=blocked_exit();before=_chain_snapshot(prefix)
    first=graph.propose(prefix,start,goal,start_via_edges=True)
    assert first.edges[0].destination==(1,2)
    evidence=[]
    proposal=filter_transit_departures(graph,prefix,start,goal,p,
        check_context=lambda:None,progress=evidence.append)
    data=evidence[-1]
    assert any('refusal' in row for row in data['attempts'])
    assert data['attempts'][-1]['candidate']
    assert all(row['refusal']['geometric_exclusion'] for row in data['attempts'] if 'refusal' in row)
    assert proposal.edges[0].destination==(1,0)
    assert _chain_snapshot(prefix)==before
    guide=proposal.guide(static_inventory_sha256='d'*64,radius=1.2,body_height=6.)
    plan=plan_source_itinerary(prefix,start,guide,p.source,p.static,p.bsp,p.region_policy,
        check_context=lambda:None,max_connect_distance=0,max_connect_attempts=1).record()
    assert plan['goal']==list(goal) and not plan['input_authorized']
    assert not data['physical_disconnection_proven'] and data['requires_complete_rebuild']


@pytest.mark.parametrize('reason', ('Source query changed',
    'Source motion terrain: floor_patch_budget_exceeded',
    'Source itinerary contains nonzero or unresolved native regions'))
def test_non_geometric_failures_are_not_exclusions(monkeypatch,reason):
    import tools.source_transit_departures as module
    prefix,start,goal,graph,p=blocked_exit();evidence=[]
    def refused(*a,**k):raise ValueError(reason)
    monkeypatch.setattr(module,'check_source_footprint',refused)
    with pytest.raises(ValueError,match=reason):
        filter_transit_departures(graph,prefix,start,goal,p,
            check_context=lambda:None,progress=evidence.append)
    assert not evidence[-1]['excluded_identities']
    assert not evidence[-1]['attempts'][-1]['refusal']['geometric_exclusion']


def test_departure_budget_and_changed_prefix_stop_search():
    prefix,start,goal,graph,p=blocked_exit();before=_chain_snapshot(prefix)
    with pytest.raises(TimeoutError,match='query count'):
        filter_transit_departures(graph,prefix,start,goal,p,maximum_queries=1,check_context=lambda:None)
    assert _chain_snapshot(prefix)==before
    def changed(_):prefix.index+=1
    with pytest.raises(ValueError,match='source prefix|No committed'):
        filter_transit_departures(graph,prefix,start,goal,p,check_context=lambda:None,progress=changed)


def test_clear_xy_must_reach_the_proposed_destination_face(monkeypatch):
    prefix,start,goal,graph,p=blocked_exit();p.static.faces_for_footprint=lambda _:()
    original=graph.propose(prefix,start,goal,start_via_edges=True)
    # Clear north travel cannot establish the unrelated east-face identity.
    changed=replace(original,edges=(replace(original.edges[0],destination=(1,1)),*original.edges[1:]))
    monkeypatch.setattr(graph,'propose',lambda *a,**k:changed)
    evidence=[];before=_chain_snapshot(prefix)
    with pytest.raises(ValueError,match='actual carried source layer'):
        filter_transit_departures(graph,prefix,start,goal,p,check_context=lambda:None,progress=evidence.append)
    assert evidence[-1]['attempts'][-1]['layer_refusal']['expected_face']==(1,1)
    assert not evidence[-1]['excluded_identities'] and _chain_snapshot(prefix)==before
