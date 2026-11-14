from dataclasses import replace

import pytest

from eql_automation.fixed_route_follower import FixedRoute,FixedSegment
from eql_automation.floor_replay import bind_floor_replay_seed


def baseline():
    return FixedRoute('gfaydark','a'*64,'b'*64,1.2,(
        FixedSegment(1,(0.,0.,0.),(0.,10.,0.)),
        FixedSegment(2,(0.,10.,0.),(10.,10.,0.))))


def test_relocated_suffix_uses_only_the_original_start_seed():
    old=baseline()
    new=replace(old,artifact_sha256='c'*64,segments=(old.segments[0],
        replace(old.segments[1],end=(15.,10.,0.))))
    binding=bind_floor_replay_seed(old,new)
    assert binding.unchanged_prefix_segments==1
    assert not binding.complete_static_chain_matches_replay_plan
    assert not binding.input_authorized and not binding.real_client_accepted
    assert 'initial_floor_seed_only' in binding.scope


def test_identical_plan_records_full_static_scan_identity_but_never_client_acceptance():
    binding=bind_floor_replay_seed(baseline(),baseline())
    assert binding.complete_static_chain_matches_replay_plan
    assert binding.unchanged_prefix_segments==2
    assert not binding.real_client_accepted


@pytest.mark.parametrize('change',(
    {'zone':'another'}, {'mesh_sha256':'d'*64}, {'half_width':1.3}, {'segments':()},
    {'segments':(FixedSegment(3,(0.,0.,0.),(0.,10.,0.)),)},
    {'segments':(FixedSegment(1,(0.,0.,1.),(0.,10.,0.)),)},
    {'segments':(FixedSegment(1,(0.,0.,0.),(0.,11.,0.)),)},
))
def test_changed_start_or_inventory_cannot_reuse_the_floor_seed(change):
    old=baseline()
    with pytest.raises(ValueError):bind_floor_replay_seed(old,replace(old,artifact_sha256='c'*64,**change))


def test_changed_suffix_cannot_claim_the_original_artifact_identity():
    old=baseline()
    with pytest.raises(ValueError):
        bind_floor_replay_seed(old,replace(old,segments=(old.segments[0],)))
