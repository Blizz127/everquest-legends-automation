"""Real ledger/geometry; synthetic positions/receipts except explicit pipe tests."""
from copy import deepcopy
from dataclasses import replace
import time

import pytest

from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_stair_controller import SourceStairController,SourceStairFix
from eql_automation.source_stair_preflight import SourceStairPreflight,SourceStairHint
from eql_automation.source_step_sender import run_checked_source_step
from eql_automation.uinput_watchdog import PulseReceipt
from test_route_step_sender import after_down
from test_source_motion import f,legacy

pytestmark=pytest.mark.parametrize('f',['stair_preflight'],indirect=True)


def begin(f,*,real=False):
    f.real=real;f.now=f.clock() if real else time.monotonic()
    pre=SourceStairPreflight(f.ledger,policy=f.policy,
        hint=SourceStairHint((4.,2.),(4.,10.),f.stair_groups,1.2,vertical_model='bounded_source_contacts'),
        released_at=f.first.raw_fix.received_monotonic-.2)
    pre.prepare()
    f.now=f.clock();a=pre.observe_reply(f.position())
    if real:time.sleep(.4)
    else:f.now+=.4
    f.now=f.clock();b=pre.observe_reply(f.position())
    start=pre.bind_start(a,b)
    return SourceStairController.from_preflight(pre,start),pre


def pulse(f,c):
    command=c.next_command();g=c.prepare(command.kind)
    ticket=c.stage(g,requested_seconds=command.requested_seconds)
    # Synthetic elapsed receipt: requested duration and maximum actual hold
    # remain distinct. This is not transport or game-client acceptance.
    at=ticket.proposed_at
    receipt=PulseReceipt(ticket.movement_key,ticket.requested_seconds,at+.001,at+.002,at+.04,at+.041,'elapsed')
    f.now=at+.042
    return c.seal_release(ticket,receipt)


def pair(f,c,seal,*,y,z,second_y=None):
    f.now=seal.receipt.up_completed_at+.2
    a=c.observe_reply(seal,f.position(y=y,z=z));f.now+=.4
    b=c.observe_reply(seal,f.position(y=y if second_y is None else second_y,z=z))
    return a,b


def climb(f,c,*,finish=True):
    rows=((2.4,2.7),(2.8,2.7),(3.2,2.7),(3.6,2.7),(3.98,3.2),
          (4.38,3.7),(4.78,3.7),(5.18,3.7),(5.58,3.7),(5.98,4.2),
          (6.38,4.7),(6.78,4.7),(7.18,4.7),(7.58,4.7),(7.98,5.2),(8.38,5.7))
    original=f.ledger._state();half=[]
    for y,z in rows if finish else rows[:-1]:
        seal=pulse(f,c);a,b=pair(f,c,seal,y=y,z=z)
        outcome=c.acknowledge_stopped(seal,a,b)
        if y in (3.98,5.98,7.98):
            assert type(outcome.reference) is SourceStairFix
            assert all(c.index.states[i].kind=='transition' for i in b.compatible_states)
            half.append(b)
        if outcome.kind=='landed':return outcome,(a,b),original,half
        assert outcome.kind=='in_transfer' and f.ledger._state()==original
        assert f.ledger.phase=='stair_transfer'
    return None


def test_receipt_feedback_traverses_ground_and_half_rise_without_committing_early(f):
    c,pre=begin(f);old=f.ledger.chain;old_proof=old.previous.proof_sha256
    started=f.policy.started;cal=f.observer.calibration;seed=f.observer._seed
    record=pre.cache.record()
    assert record['checked_end']==[4.,11.] and c.hint.end==(4.,10.)
    result,(a,b),original,half=climb(f,c)
    assert len(half)==3 and result.kind=='landed' and f.ledger.steps==16
    assert f.ledger.chain is not old and f.ledger.chain.previous.previous_sha256==old_proof
    assert f.ledger.chain.previous.joins==() and _chain_snapshot(old)==original[0]
    assert f.observer._seed==seed and f.observer.calibration is cal
    assert f.ledger.reference.raw_fix is b.raw_fix and f.ledger.reference.observed_at==b.observed_at
    assert f.ledger.reference.package_xyz[:2]==(4.,8.38)
    f.observer._sample(a.raw_fix,f.ledger.chain,a.observed_at)
    assert f.observer.validate(f.ledger.reference,f.ledger.chain)==f.now
    with pytest.raises(ValueError):f.ledger.chain.floor_at(c.hint.end)
    f.policy.finish_transfer(c)
    assert f.policy.ledger is f.ledger and f.policy.started==started
    pre.cancel('late preflight');c.cancel('late controller')
    assert f.ledger.phase=='ready' and not f.drain_events()


@pytest.mark.parametrize('change',['height','center','clone','expiry','cancel'])
def test_bad_receipt_feedback_keeps_original_floor(f,change):
    c,_=begin(f);old=f.ledger._state();seal=pulse(f,c)
    with pytest.raises((RuntimeError,ValueError)):
        if change=='height':pair(f,c,seal,y=2.4,z=100.)
        elif change=='center':pair(f,c,seal,y=3.1,z=2.7)
        else:
            a,b=pair(f,c,seal,y=2.4,z=2.7)
            if change=='clone':b=replace(b)
            elif change=='expiry':f.now=seal.expires_at+.01
            else:c.cancel('F9')
            c.acknowledge_stopped(seal,a,b)
    assert f.ledger._state()==old and f.ledger.phase=='stopped' and not f.drain_events()


@pytest.mark.parametrize('change',['cancel','focus','input'])
def test_actual_pair_cap_uses_only_overlapping_final_faces_and_cancellation_cannot_publish(f,monkeypatch,change):
    c,_=begin(f);climb(f,c,finish=False);old=f.ledger._state()
    seal=pulse(f,c);a,b=pair(f,c,seal,y=8.38,z=5.7,second_y=8.48)
    cap=c._landing(a,b,'a'*64)[0]
    assert len(cap.previous.selected_ids)==1 and len(c.hint.tread_ids[-1])==2
    assert cap.floor_at(a.package_xyz[:2]) and cap.floor_at(b.package_xyz[:2])
    landing=c._landing
    def cancelled(*args):
        result=landing(*args)
        if change=='cancel':c.cancel('F9 during actual landing')
        elif change=='focus':f.focus=False
        else:f.active=True
        return result
    monkeypatch.setattr(c,'_landing',cancelled)
    with pytest.raises(RuntimeError):c.acknowledge_stopped(seal,a,b)
    assert f.ledger._state()==old and f.ledger.phase=='stopped'


@pytest.mark.parametrize('change',['geometry','ticket','receipt'])
def test_stair_control_and_receipt_fields_cannot_diverge_from_checked_coverage(f,change):
    c,_=begin(f);old=f.ledger._state()
    with pytest.raises((RuntimeError,ValueError)):
        if change=='geometry':
            geometry=c.prepare('forward');object.__setattr__(geometry,'kind','right')
            c.stage(geometry,requested_seconds=.02)
        else:
            seal=pulse(f,c)
            if change=='ticket':object.__setattr__(seal.ticket,'movement_key',106)
            else:object.__setattr__(seal.receipt,'up_completed_at',seal.receipt.up_completed_at+.001)
            pair(f,c,seal,y=2.4,z=2.7)
    assert f.ledger._state()==old and f.ledger.phase=='stopped' and not f.drain_events()


@pytest.mark.parametrize('cancel',[False,True])
def test_real_pipe_stair_sender_releases_and_never_commits_on_up(f,monkeypatch,cancel):
    c,_=begin(f,real=True);old=f.ledger._state()
    if cancel:after_down(monkeypatch,lambda:c.cancel('F9 after stair DOWN'))
    def send():return run_checked_source_step(f.sender,c,policy=f.policy,kind='forward',
        requested_seconds=.02,command_state_clear=lambda:True,pump=lambda:None)
    if cancel:
        with pytest.raises(RuntimeError):send()
    else:
        seal=send();assert seal.receipt.completion=='elapsed'
    events=f.drain_events()
    assert events[:4]==((1,103,1),(0,0,0),(1,103,0),(0,0,0))
    assert not f.sender.held and f.ledger._state()==old
    assert f.ledger.phase==('stopped' if cancel else 'stair_transfer')
