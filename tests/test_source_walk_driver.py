"""Source route control with synthetic positions; no game or input device."""
import math
import time

import pytest

from eql_automation.source_walk_driver import (
    SourceWalkDriver,SourceWalkCommand,SourceStepBoundary,SourceWalkFinished)
from eql_automation.uinput_watchdog import PulseReceipt
from test_source_motion import f,legacy,proposed_receipt


def test_repeated_forward_receipts_require_stopped_ack_before_reaching_exact_goal(f):
    driver=SourceWalkDriver(f.ledger)
    f.real=False;f.now=time.monotonic()
    index=f.ledger.chain.index
    for count in range(16):
        action=driver.next_action()
        if type(action) is SourceWalkFinished:break
        assert type(action) is SourceWalkCommand and action.kind=='forward'
        old=f.ledger.chain;start=f.ledger.reference.package_xyz
        geometry=f.ledger.prepare(action.kind)
        ticket=f.ledger.stage(geometry,requested_seconds=action.requested_seconds)
        at=ticket.proposed_at;duration=action.requested_seconds
        receipt=PulseReceipt(103,duration,at+.001,at+.001,at+.001+duration,at+.001+duration,'elapsed')
        f.now=receipt.up_completed_at+.001
        seal=f.ledger.seal_release(ticket,receipt)
        assert f.ledger.chain is old and f.ledger.phase=='await_stopped'
        f.now=receipt.up_completed_at+.2
        y=start[1]+f.ledger.pose.speed*duration
        first=f.ledger.observe_reply(seal,f.position(y=y))
        f.now+=.4
        second=f.ledger.observe_reply(seal,f.position(y=y))
        f.ledger.acknowledge_stopped(seal,first,second)
    else:pytest.fail('Source route did not terminate within the finite pulse budget')
    assert count>=4 and f.ledger.steps==count
    assert f.ledger.chain.index==index+2*count
    assert math.dist(action.reference.package_xyz[:2],(4.,3.25))<=.25
    assert not action.real_client_accepted and f.sender.release_calls==0


def test_driver_turns_before_forward_and_cannot_run_without_acknowledgment(f):
    driver=SourceWalkDriver(f.ledger);f.ledger.pose.heading=45.
    action=driver.next_action()
    assert action.kind=='left'
    geometry=f.ledger.prepare(action.kind)
    f.ledger.stage(geometry,requested_seconds=action.requested_seconds)
    with pytest.raises(RuntimeError,match='stopped acknowledgment'):driver.next_action()
    assert f.ledger.phase=='stopped' and f.ledger.steps==0


@pytest.mark.parametrize('f',['step'],indirect=True)
def test_early_step_handoff_preserves_actual_cap_and_unconsumed_approach(f):
    ticket,receipt=proposed_receipt(f)
    seal=f.ledger.seal_release(ticket,receipt)
    f.ledger.acknowledge_stopped(seal,*f.replies(seal))
    driver=SourceWalkDriver(f.ledger);before=driver.index;chain=f.ledger.chain
    steps=f.ledger.steps
    action=driver.next_action()
    assert type(action) is SourceStepBoundary
    assert action.start==f.ledger.reference.package_xyz
    assert action.start!=action.planned_start
    assert action.planned_start==(4.,3.1,.2) and action.end==(4.,3.5,.5125)
    assert action.approach_cell_indices and action.cell_index>before
    assert driver.index==before and f.ledger.chain is chain and f.ledger.steps==steps
    assert action.reference is f.ledger.reference and not action.input_authorized
    # Same unresolved boundary remains pending; no endpoint is silently consumed.
    assert driver.next_action()==action
    # The original ordinary maximum-hold sweep really does touch the riser.
    with pytest.raises(ValueError,match='terrain'):f.ledger.prepare('forward')
    assert f.ledger.chain is chain and f.sender.release_calls==0
