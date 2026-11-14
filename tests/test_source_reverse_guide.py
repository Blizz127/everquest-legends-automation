from dataclasses import replace
from hashlib import sha256

import pytest

from eql_automation.native_region_policy import encoded
from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_itinerary import SourceItineraryPlan,SourceStepHint,plan_source_itinerary
from eql_automation.source_reverse_guide import reverse_source_plan
from test_source_itinerary import fixture,run


def test_reversed_steps_rebuild_from_current_prefix_with_previous_departure_landings():
    args=fixture();plan=run(args);data=plan.record();guide=reverse_source_plan(plan)
    old_steps=[c for c in data['cells'] if c['kind']=='step']
    reversed_steps=[op for op in guide.operations if type(op) is SourceStepHint]
    assert [op.landing_seed_ids for op in reversed_steps]==[
        tuple(tuple(k) for k in c['transfer']['evidence']['lower_endpoint']['selected_ids'])
        for c in reversed(old_steps)]
    start=tuple(data['goal']);terrain=args[2]
    prefix=SourceFloorChain(inventory_sha256='a'*64,seed_evidence_sha256='8'*64,
        seed_ids=((1,0),),body_height=6.)
    cap=swept_square(start,start,1.)
    assert prefix.advance(cap,terrain.source_faces_for_footprint(cap)).candidate
    before=_chain_snapshot(prefix)
    checked=plan_source_itinerary(prefix,start,guide,*args[2:],check_context=lambda:None).record()
    assert checked['goal']==data['start'] and not checked['real_client_accepted']
    assert checked['initial_seed_sha256']=='8'*64 and _chain_snapshot(prefix)==before


def test_reverse_suffix_retains_bounded_final_connection_and_rejects_gaps():
    plan=run(fixture());data=plan.record()
    guide=reverse_source_plan(plan,first_cell=len(data['cells'])-1,goal=(-3.,0.))
    assert len(guide.operations)==1 and guide.goal==(-3.,0.)
    with pytest.raises(ValueError,match='bounded final connector'):
        reverse_source_plan(plan,first_cell=len(data['cells'])-1,goal=(999.,0.))
    data['cells'][-1]['end'][0]+=1
    payload=encoded(data);broken=SourceItineraryPlan(payload,sha256(payload).hexdigest())
    with pytest.raises(ValueError,match='gap'):reverse_source_plan(broken)
    with pytest.raises(ValueError,match='changed'):reverse_source_plan(replace(plan,sha256='0'*64))
