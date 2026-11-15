from copy import deepcopy
from dataclasses import replace

import pytest

from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_itinerary import SourceWalkHint, plan_source_itinerary
from tools.source_walk_prefix import replay_walk_prefix
from tools.source_walk_repairs import repair_walks
from test_source_walk_repairs import context


def repaired_prefix():
    prefix,guide,planner=context()
    guide=replace(guide,goal=(4.,0.),operations=(*guide.operations,
        SourceWalkHint((2.,0.),(3.,0.)),SourceWalkHint((3.,0.),(4.,0.))))
    snapshots=[]
    repair_walks(prefix,guide,planner,check_context=lambda:None,
        maximum_rejoin_distance=4.,progress=lambda e:snapshots.append(deepcopy(e)))
    evidence=next(e for e in snapshots if e['completed_operations']==1)
    assert evidence['repairs'][0]['adopted']
    return prefix,guide,evidence,planner


def test_replayed_detour_caps_reproduce_proofs_and_rebuild_complete_suffix():
    prefix,guide,evidence,p=repaired_prefix();before=_chain_snapshot(prefix)
    branch,position,operations=replay_walk_prefix(prefix,guide,evidence,p,check_context=lambda:None)
    assert position==(2.,0.) and branch.previous.proof_sha256==evidence['reached_proof_sha256']
    assert len(operations)>evidence['completed_operations'] and any(op.start==op.end for op in operations)
    assert _chain_snapshot(prefix)==before
    full=replace(guide,operations=operations+guide.operations[1:])
    plan=plan_source_itinerary(prefix,guide.operations[0].start,full,p.source,p.static,p.bsp,p.region_policy,
        check_context=lambda:None,max_connect_distance=0,max_connect_attempts=1).record()
    assert plan['goal']==[4.,0.] and not plan['input_authorized'] and not plan['real_client_accepted']


@pytest.mark.parametrize('change', ('proof','path','goal','guide'))
def test_changed_saved_expectations_cannot_supply_a_floor(change):
    prefix,guide,evidence,p=repaired_prefix();before=_chain_snapshot(prefix)
    if change=='proof':evidence['checked_cells'][0]['proof_sha256']='0'*64
    if change=='path':evidence['checked_cells'][0]['start']=(90.,90.)
    if change=='goal':evidence['next_position']=(4.,0.)
    if change=='guide':evidence['source_guide_sha256']='0'*64
    with pytest.raises(ValueError):replay_walk_prefix(prefix,guide,evidence,p,check_context=lambda:None)
    assert _chain_snapshot(prefix)==before


def test_scope_change_during_replay_stops_without_adopting_cells():
    prefix,guide,evidence,p=repaired_prefix();calls=0
    def changed():
        nonlocal calls
        calls+=1
        if calls==2:evidence['next_position']=(99.,99.)
    with pytest.raises(ValueError,match='evidence changed'):
        replay_walk_prefix(prefix,guide,evidence,p,check_context=changed)
