"""Source route control with synthetic positions; no game or input device."""
import math
import time

import pytest

from eql_automation.source_walk_driver import (
    SourceWalkDriver,SourceWalkCommand,SourceStepBoundary,SourceWalkFinished)
from eql_automation.uinput_watchdog import PulseReceipt
from eql_automation.source_step_approach import source_step_supports
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


@pytest.mark.parametrize('f',['step'],indirect=True)
def test_actual_stopped_handoff_prepares_full_step_envelope_without_publishing_floor(f):
    ticket,receipt=proposed_receipt(f);seal=f.ledger.seal_release(ticket,receipt)
    f.ledger.acknowledge_stopped(seal,*f.replies(seal))
    driver=SourceWalkDriver(f.ledger);boundary=driver.next_action();chain=f.ledger.chain
    prepared=driver.prepare_step_approach(boundary);data=prepared.record()
    assert data['start']==[4.,2.2] and data['initial_proof_sha256']==chain.previous.proof_sha256
    assert data['checked_radius']>f.ledger.bounds.body_radius
    assert data['full_motion_envelope_covered'] and not data['input_authorized']
    assert f.ledger.chain is chain and f.ledger.phase=='ready' and f.ledger.steps==1
    supports=source_step_supports(prepared,(4.,2.4),f.ledger.terrain,f.ledger.static,check_context=lambda:None)
    assert len(supports)==1 and not supports[0].observed_grounded
    assert f.sender.release_calls==0


@pytest.mark.parametrize('f',['step'],indirect=True)
def test_stop_during_step_preparation_keeps_old_cap_and_no_sender_input(f,monkeypatch):
    import eql_automation.source_walk_driver as module
    ticket,receipt=proposed_receipt(f);seal=f.ledger.seal_release(ticket,receipt)
    f.ledger.acknowledge_stopped(seal,*f.replies(seal))
    driver=SourceWalkDriver(f.ledger);boundary=driver.next_action();chain=f.ledger.chain
    original=module.plan_source_step_approach
    def prepare(*args,**options):
        import threading
        stopped=threading.Event()
        def stop():f.ledger.cancel('owner OFF during step preparation');stopped.set()
        worker=threading.Thread(target=stop);worker.start()
        assert stopped.wait(.5);worker.join()
        return original(*args,**options)
    monkeypatch.setattr(module,'plan_source_step_approach',prepare)
    with pytest.raises(RuntimeError):driver.prepare_step_approach(boundary)
    assert f.ledger.chain is chain and f.ledger.phase=='stopped' and f.sender.release_calls==0


@pytest.mark.parametrize('f',['step'],indirect=True)
def test_boundary_cannot_adopt_a_replaced_hint_map(f):
    from dataclasses import replace
    driver=SourceWalkDriver(f.ledger);boundary=driver.next_action()
    with pytest.raises(TypeError):driver._steps[boundary.cell_index]=driver._steps[boundary.cell_index]
    driver._steps=dict(driver._steps)
    driver._steps[boundary.cell_index]=replace(driver._steps[boundary.cell_index],end=(4.,3.7))
    with pytest.raises(RuntimeError,match='handoff'):driver.prepare_step_approach(boundary)
    assert f.ledger.steps==0 and f.sender.release_calls==0
