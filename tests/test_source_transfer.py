"""Conditional step input uses pipes; game feedback remains synthetic."""
from dataclasses import replace
import time

import pytest

from eql_automation.source_step_sender import run_checked_source_step
from eql_automation.source_transfer import SourceTransferController,SourceTransitionFix
from eql_automation.source_walk_driver import SourceWalkDriver,SourceStepBoundary
from eql_automation.uinput_watchdog import PulseReceipt
from test_source_motion import f,legacy
from test_route_step_sender import after_down


def begin(f,driver):
    boundary=driver.next_action();assert type(boundary) is SourceStepBoundary
    controller=SourceTransferController(driver,boundary)
    f.policy.bind_transfer(controller)
    return controller


def receipt(f,c):
    command=c.next_command();geometry=c.prepare(command.kind)
    ticket=c.stage(geometry,requested_seconds=command.requested_seconds)
    t=ticket.proposed_at;d=command.requested_seconds
    r=PulseReceipt(ticket.movement_key,d,t+.001,t+.001,t+.001+d,t+.001+d,'elapsed')
    f.now=r.up_completed_at+.001
    return c.seal_release(ticket,r)


def replies(f,c,seal,*,y,z):
    f.real=False;f.now=max(f.clock(),seal.receipt.up_completed_at+.2)
    first=c.observe_reply(seal,f.position(y=y,z=z));f.now+=.4
    second=c.observe_reply(seal,f.position(y=y,z=z))
    return first,second


@pytest.mark.parametrize('f',['step'],indirect=True)
@pytest.mark.parametrize('after_stair',[False,True])
def test_multiple_approaches_partial_step_then_landing_resume_ordinary_walk(f,after_stair):
    f.real=False;f.now=time.monotonic();driver=SourceWalkDriver(f.ledger)
    connector=None
    if after_stair:
        # The previous stair landed early on this same flat approach. Its
        # remaining connector must survive approach receipts, then retire
        # when the following step actually lands beyond it.
        from eql_automation.source_walk_driver import _Target
        connector=_Target('walk',f.ledger.reference.package_xyz,(4.,3.1,.2),None)
        driver._stair_connector=connector
        driver.index=next(i for i,row in enumerate(driver.targets) if row.kind=='step')
    initial_index=driver.index
    policy_started=f.policy.started;results=[];partial_chain=None
    c=begin(f,driver)
    for y,z in ((2.2,2.7),(2.4,2.7),(2.6,2.7),(2.8,2.7),(3.,2.7),(3.15,2.7),(3.35,3.01),(3.55,3.01)):
        old=f.ledger.chain;seal=receipt(f,c)
        assert f.ledger.chain is old and f.ledger.phase=='transfer'
        pair=replies(f,c,seal,y=y,z=z)
        result=c.acknowledge_stopped(seal,*pair);results.append(result.kind)
        if result.kind!='landed':assert driver._stair_connector is connector
        if result.kind=='in_transfer':
            assert isinstance(result.reference,SourceTransitionFix)
            assert f.ledger.chain is old and f.ledger.phase=='transfer'
            assert not result.reference.observed_grounded and driver.index==initial_index
            partial_chain=old
        else:
            assert result.kind in ('approach','landed') and f.ledger.phase=='ready'
            assert result.reference.raw_fix is pair[1].raw_fix
            assert result.reference.observed_at==pair[1].observed_at
            f.policy.finish_transfer(c)
            if result.kind=='approach':c=begin(f,driver)
    assert results==['approach']*6+['in_transfer','landed']
    assert f.ledger.chain is not partial_chain and f.ledger.steps==8
    assert f.policy.started==policy_started and driver._active_step is None
    assert driver._stair_connector is None
    command=driver.next_action()
    assert driver.index>0 and command.kind=='forward' and command.target[:2]==(4.,3.9)


@pytest.mark.parametrize('f',['step'],indirect=True)
def test_actual_transfer_pipe_uses_same_sender_and_does_not_commit_on_release(f):
    driver=SourceWalkDriver(f.ledger);c=begin(f,driver);old=f.ledger.chain
    seal=run_checked_source_step(f.sender,c,policy=f.policy,kind='forward',requested_seconds=.02,
        command_state_clear=lambda:True,pump=lambda:None)
    assert f.drain_events()[:4]==((1,103,1),(0,0,0),(1,103,0),(0,0,0))
    assert f.ledger.chain is old and f.ledger.phase=='transfer' and not f.sender.held
    result=c.acknowledge_stopped(seal,*replies(f,c,seal,y=2.2,z=2.7))
    assert result.kind=='approach'
    f.policy.finish_transfer(c)
    assert f.policy.ledger is f.ledger and f.ledger.steps==1


@pytest.mark.parametrize('change',('cancel','assist','generation'))
@pytest.mark.parametrize('f',['step'],indirect=True)
def test_transfer_scope_change_preserves_committed_floor(f,change):
    f.real=False;f.now=time.monotonic();c=begin(f,SourceWalkDriver(f.ledger))
    old=f.ledger.chain;seal=receipt(f,c)
    pair=replies(f,c,seal,y=2.2,z=2.7)
    if change=='cancel':c.cancel('owner stop')
    elif change=='assist':f.mode='assist'
    else:f.generation+=1
    with pytest.raises((RuntimeError,ValueError)):c.acknowledge_stopped(seal,*pair)
    assert f.ledger.chain is old and f.ledger.phase=='stopped' and f.ledger.steps==0


@pytest.mark.parametrize('f',['step'],indirect=True)
def test_copied_transition_fix_cannot_publish_a_cap(f):
    f.real=False;f.now=time.monotonic();c=begin(f,SourceWalkDriver(f.ledger));old=f.ledger.chain
    seal=receipt(f,c);a,b=replies(f,c,seal,y=2.2,z=2.7)
    with pytest.raises(RuntimeError):c.acknowledge_stopped(seal,a,replace(b))
    assert f.ledger.chain is old and f.ledger.steps==0


@pytest.mark.parametrize('f',['step'],indirect=True)
def test_off_after_transfer_down_releases_without_publishing(f,monkeypatch):
    c=begin(f,SourceWalkDriver(f.ledger));old=f.ledger.chain
    after_down(monkeypatch,lambda:c.cancel('OFF during step DOWN'))
    with pytest.raises(RuntimeError):
        run_checked_source_step(f.sender,c,policy=f.policy,kind='forward',requested_seconds=.02,
            command_state_clear=lambda:True,pump=lambda:None)
    assert not f.sender.held and f.sender.release_calls>=1
    assert f.ledger.chain is old and f.ledger.steps==0 and f.ledger.phase=='stopped'


@pytest.mark.parametrize('f',['step'],indirect=True)
def test_elevated_reply_settles_without_a_new_key_or_floor_publication(f):
    f.real=False;f.now=time.monotonic();c=begin(f,SourceWalkDriver(f.ledger));old=f.ledger.chain
    seal=receipt(f,c);outcome=c.acknowledge_stopped(seal,*replies(f,c,seal,y=2.2,z=3.1))
    assert outcome.kind=='settling' and f.ledger.chain is old and f.ledger.steps==0
    with pytest.raises(RuntimeError,match='await stopped'):c.next_command()
    outcome=c.acknowledge_stopped(seal,*replies(f,c,seal,y=2.2,z=2.7))
    assert outcome.kind=='approach' and f.ledger.steps==1


@pytest.mark.parametrize('f',['step'],indirect=True)
def test_shared_riser_height_stays_ambiguous_and_expires_without_input(f):
    f.real=False;f.now=time.monotonic();driver=SourceWalkDriver(f.ledger);c=begin(f,driver)
    for y in (2.2,2.4,2.6):
        seal=receipt(f,c);assert c.acknowledge_stopped(seal,*replies(f,c,seal,y=y,z=2.7)).kind=='approach'
        f.policy.finish_transfer(c);c=begin(f,driver)
    old=f.ledger.chain;seal=receipt(f,c)
    pair=replies(f,c,seal,y=3.3,z=2.85)
    assert all(len(fix.supports)==2 and not fix.height_matches_unique_support for fix in pair)
    assert c.acknowledge_stopped(seal,*pair).kind=='settling'
    f.now=seal.expires_at+.01
    with pytest.raises(RuntimeError):c.observe_reply(seal,f.position(y=3.3,z=2.85))
    assert f.ledger.chain is old and f.ledger.steps==3 and f.sender.release_calls==0


@pytest.mark.parametrize('f',['step'],indirect=True)
def test_body_footprint_is_not_used_as_a_larger_allowed_center_displacement(f):
    f.real=False;f.now=time.monotonic();c=begin(f,SourceWalkDriver(f.ledger));old=f.ledger.chain
    seal=receipt(f,c)
    with pytest.raises(RuntimeError,match='center left'):replies(f,c,seal,y=3.1,z=2.7)
    assert f.ledger.chain is old and f.ledger.steps==0


@pytest.mark.parametrize('f',['step'],indirect=True)
def test_changed_conditional_branch_cannot_be_staged(f):
    f.real=False;f.now=time.monotonic();c=begin(f,SourceWalkDriver(f.ledger))
    geometry=c.prepare('forward');c._prepared.branches[-1].index+=1
    with pytest.raises((RuntimeError,ValueError)):c.stage(geometry,requested_seconds=.02)
    assert f.ledger.steps==0 and f.ledger.phase=='stopped'


@pytest.mark.parametrize('change',('cancel','generation','assist'))
@pytest.mark.parametrize('f',['step'],indirect=True)
def test_final_transfer_seal_callback_cannot_resurrect_scope(f,monkeypatch,change):
    f.real=False;f.now=time.monotonic();c=begin(f,SourceWalkDriver(f.ledger));old=f.ledger.chain
    g=c.prepare('forward');t=c.stage(g,requested_seconds=.02);at=t.proposed_at
    r=PulseReceipt(103,.02,at+.001,at+.002,at+.021,at+.022,'elapsed');f.now=at+.03
    original=type(c.model).check_policy
    def mutate():
        if change=='cancel':c.cancel('OFF at final seal')
        elif change=='generation':f.generation+=1
        else:f.mode='assist'
    def check(model,policy):
        result=original(model,policy);f.clock_hook=mutate;return result
    monkeypatch.setattr(type(c.model),'check_policy',check)
    with pytest.raises((RuntimeError,ValueError)):c.seal_release(t,r)
    assert f.ledger.chain is old and f.ledger.steps==0 and c.phase=='stopped'


@pytest.mark.parametrize('f',['step'],indirect=True)
def test_policy_transfer_keeps_existing_time_origin_and_hold_budget(f):
    started=f.policy.started;f.policy.reserved_hold=.5;f.policy.origin=(4.,2.,.2)
    c=begin(f,SourceWalkDriver(f.ledger))
    assert f.policy.started==started and f.policy.reserved_hold==.5 and f.policy.origin==(4.,2.,.2)
    with pytest.raises(RuntimeError):f.policy.finish_transfer(c)
    assert f.policy.ledger is c


@pytest.mark.parametrize('f',['step'],indirect=True)
def test_final_observation_clock_cannot_publish_after_stop(f,monkeypatch):
    import inspect
    f.real=False;f.now=time.monotonic();c=begin(f,SourceWalkDriver(f.ledger))
    seal=receipt(f,c);f.now=seal.receipt.up_completed_at+.2
    raw=f.position(y=2.2,z=2.7);before=f.observer.last_seq;direct=[0]
    original=f.observer.check
    def check():
        if inspect.currentframe().f_back.f_code.co_name=='observe_reply':
            direct[0]+=1
            if direct[0]==2:f.clock_hook=lambda:c.cancel('OFF at final observation clock')
        return original()
    monkeypatch.setattr(f.observer,'check',check)
    with pytest.raises(RuntimeError):c.observe_reply(seal,raw)
    assert direct[0]==2 and f.observer.last_seq==before and not c._issued
    assert c.phase=='stopped' and f.ledger.steps==0


@pytest.mark.parametrize('f',['step'],indirect=True)
def test_finished_controller_cannot_cancel_a_new_lease(f):
    f.real=False;f.now=time.monotonic();driver=SourceWalkDriver(f.ledger);old=begin(f,driver)
    seal=receipt(f,old);assert old.acknowledge_stopped(seal,*replies(f,old,seal,y=2.2,z=2.7)).kind=='approach'
    f.policy.finish_transfer(old);current=begin(f,driver)
    old.cancel('late completed callback')
    assert current.phase=='ready' and f.ledger.phase=='transfer' and f.ledger._busy is current._lease
    assert current.next_command().kind=='forward'


@pytest.mark.parametrize('f',['down'],indirect=True)
def test_downward_step_landing_uses_lineage_instead_of_larger_height(f):
    f.real=False;f.now=time.monotonic();driver=SourceWalkDriver(f.ledger);c=begin(f,driver)
    for y in (2.2,2.4,2.6,2.8,3.,3.15):
        seal=receipt(f,c);assert c.acknowledge_stopped(seal,*replies(f,c,seal,y=y,z=2.7)).kind=='approach'
        f.policy.finish_transfer(c);c=begin(f,driver)
    old=f.ledger.chain;seal=receipt(f,c)
    assert c.acknowledge_stopped(seal,*replies(f,c,seal,y=3.35,z=2.39)).kind=='in_transfer'
    assert f.ledger.chain is old
    seal=receipt(f,c);result=c.acknowledge_stopped(seal,*replies(f,c,seal,y=3.55,z=2.39))
    assert result.kind=='landed' and result.reference.package_xyz[2]==pytest.approx(.2)
    assert f.ledger.steps==8 and driver._active_step is None
