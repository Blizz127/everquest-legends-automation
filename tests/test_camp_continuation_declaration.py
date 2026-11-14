"""Continuation supervision never renews the earlier open-ground statement."""
from dataclasses import replace

import pytest

from eql_automation.supervised_source import SupervisedSourcePolicy
from test_source_motion import f
from test_route_floor_commit import legacy


@pytest.mark.parametrize('fault',(None,'missing_supervision','renewed_clearance','wrong_scope'))
def test_source_continuation_has_distinct_explicit_declaration(f,fault):
    f.real=False;f.now=max(f.observer.last_at,f.second.raw_fix.received_monotonic+.01)
    old=f.policy
    declaration=replace(old.declaration,scope='camp_continuation',open_flat_clear=False,
        owner_supervised_continuation=True)
    if fault=='missing_supervision':declaration=replace(declaration,owner_supervised_continuation=False)
    elif fault=='renewed_clearance':declaration=replace(declaration,open_flat_clear=True)
    elif fault=='wrong_scope':declaration=replace(declaration,scope='destination_travel')
    options=dict(declaration=declaration,gate=old.gate,owner_input=old.owner_input,
        log_veto=old.log_veto,expected_window=old.window,topology_generation=old.topology,
        check_current=old.check_current)
    if fault is None:
        policy=SupervisedSourcePolicy(f.ledger,**options)
        result=policy.snapshot()
        assert result['declaration']['owner_supervised_continuation'] is True
        assert result['declaration']['open_flat_clear'] is False
        assert not result['independent_scene_verified'] and not result['motion_bounds_verified']
    else:
        with pytest.raises(ValueError):SupervisedSourcePolicy(f.ledger,**options)
    assert f.drain_events()==()
