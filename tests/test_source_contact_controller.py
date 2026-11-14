"""Real contact geometry/ledger; synthetic client feedback, no game input."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace
import time

import pytest

from eql_automation.source_contact_controller import SourceContactController,SourceContactFix,common_contact_heights
from eql_automation.source_contact_preflight import SourceContactPreflight,SourceContactHint
from eql_automation.uinput_watchdog import PulseReceipt
from test_source_motion import f,legacy

pytestmark=pytest.mark.parametrize('f',['contact_preflight'],indirect=True)


def begin(f,*,real=False,waypoints=((4.,2.),(4.,3.8))):
    f.real=real;f.now=time.monotonic()
    pre=SourceContactPreflight(f.ledger,policy=f.policy,
        hint=SourceContactHint(waypoints,((20,0),(20,1)),.2),
        released_at=f.first.raw_fix.received_monotonic-.2)
    pre.prepare();a=pre.observe_reply(f.position())
    if real:time.sleep(.4)
    else:f.now+=.4
    b=pre.observe_reply(f.position())
    return SourceContactController(pre,pre.bind_start(a,b)),pre


def pulse(f,c,kind=None):
    command=c.next_command();g=c.prepare(kind or command.kind)
    ticket=c.stage(g,requested_seconds=command.requested_seconds);at=ticket.proposed_at
    receipt=PulseReceipt(ticket.movement_key,ticket.requested_seconds,at+.001,at+.002,at+.04,at+.041,'elapsed')
    f.now=at+.042
    return c.seal_release(ticket,receipt)


def pair(f,c,seal,*,y,z=2.7,second_y=None,second_z=None):
    f.now=max(f.now,seal.receipt.up_completed_at+.2)
    a=c.observe_reply(seal,f.position(y=y,z=z));f.now+=.4
    b=c.observe_reply(seal,f.position(y=y if second_y is None else second_y,z=z if second_z is None else second_z))
    return a,b


def traverse(f,c):
    old=f.ledger._state()
    for y,z in ((2.4,2.7),(2.8,2.7),(3.2,2.7),(3.6,2.79)):
        seal=pulse(f,c);fixes=pair(f,c,seal,y=y,z=z)
        result=c.acknowledge_stopped(seal,*fixes)
        assert f.ledger._state()==old and f.ledger.phase=='contact_transfer'
        if y<3.6:assert result.kind=='in_contact'
    return result,fixes


def test_actual_rug_arrival_preserves_original_floor_calibration_and_scope(f):
    c,pre=begin(f);old=f.ledger._state();cal=f.observer.calibration;started=f.policy.started
    result,(a,b)=traverse(f,c)
    assert result.kind=='arrived' and result.arrival is c.arrival and type(b) is SourceContactFix
    assert b.package_xyz[1]==3.6 and b.package_xyz[2]!=.2
    assert [s[0] for s in b.compatible_states]==['sheet_top']
    record=c.validate_arrival(result.arrival).record()
    assert record['goal']==[4.,3.8] and record['actual_pair'][1]['xyz'][1]==3.6
    assert record['original_floor_unchanged'] and not record['ordinary_grounded']
    assert not record['real_client_accepted'] and not result.real_client_accepted
    assert c.reference is b and c.local_steps==4 and c.cursor==len(c.targets)
    assert f.ledger._state()==old and f.observer.calibration is cal and f.policy.started==started
    assert f.ledger.reference is not b and f.ledger.steps==0 and f.ledger.pose.y==2.
    with pytest.raises(RuntimeError):f.policy.finish_transfer(c)
    with pytest.raises(RuntimeError):c.next_command()
    assert c.validate_arrival(result.arrival) is result.arrival
    pre.cancel('late ancestor');assert c.phase=='arrived'
    c.cancel('owner OFF');assert f.ledger.phase=='stopped' and not f.drain_events()


@pytest.mark.parametrize('change',['height','center','clone','expiry','cancel','geometry','ticket','receipt'])
def test_bad_contact_feedback_or_transport_keeps_original_floor(f,change):
    c,_=begin(f);old=f.ledger._state()
    with pytest.raises((RuntimeError,ValueError)):
        if change=='geometry':
            g=c.prepare('forward');object.__setattr__(g,'kind','right');c.stage(g,requested_seconds=.02)
        else:
            seal=pulse(f,c)
            if change=='ticket':object.__setattr__(seal.ticket,'movement_key',106)
            if change=='receipt':object.__setattr__(seal.receipt,'up_completed_at',seal.receipt.up_completed_at+.001)
            fixes=pair(f,c,seal,y=3.1 if change=='center' else 2.4,z=100. if change=='height' else 2.7)
            if change=='clone':fixes=(fixes[0],replace(fixes[1]))
            if change=='expiry':f.now=seal.expires_at+.01
            if change=='cancel':c.cancel('F9')
            c.acknowledge_stopped(seal,*fixes)
    assert f.ledger._state()==old and f.ledger.phase=='stopped' and not f.drain_events()


def test_pair_requires_common_possible_height_without_filling_gap(f):
    def states(*intervals):return SimpleNamespace(compatible_states=tuple(('test',(),v) for v in intervals))
    a=states((F(0),F(0)),(F(1,10),F(1,10)))
    assert common_contact_heights(a,states((F(4,100),F(6,100))))==()
    assert common_contact_heights(a,states((F(0),F(1,10))))==((F(0),F(0)),(F(1,10),F(1,10)))
    c,_=begin(f)
    for y in (2.4,2.8,3.2):
        seal=pulse(f,c);c.acknowledge_stopped(seal,*pair(f,c,seal,y=y))
    seal=pulse(f,c);fixes=pair(f,c,seal,y=3.6,z=2.7,second_z=2.79)
    steps=c.local_steps;old=f.ledger._state()
    assert c.acknowledge_stopped(seal,*fixes).kind=='settling'
    assert c.phase=='settling' and c._sealed is seal and c.local_steps==steps
    with pytest.raises(RuntimeError):c.next_command()
    result=c.acknowledge_stopped(seal,*pair(f,c,seal,y=3.6,z=2.79))
    assert result.kind=='arrived' and f.ledger._state()==old


@pytest.mark.parametrize('change',['clone','fix_clone','payload','expired','focus','input','mode','calibration'])
def test_contact_arrival_requires_current_issued_pair_and_original_context(f,change):
    c,_=begin(f);result,_=traverse(f,c);arrival=result.arrival;old=f.ledger._state()
    if change=='clone':arrival=replace(arrival)
    elif change=='fix_clone':object.__setattr__(arrival,'second',replace(arrival.second))
    elif change=='payload':object.__setattr__(arrival,'payload',b'{}')
    elif change=='expired':f.now+=.501
    elif change=='focus':f.focus=False
    elif change=='input':f.active=True
    elif change=='mode':f.mode='assist'
    else:object.__setattr__(f.observer.calibration,'raw_z_minus_source_z',3.)
    with pytest.raises((RuntimeError,ValueError)):c.validate_arrival(arrival)
    assert f.ledger._state()==old and c.phase=='stopped' and not f.drain_events()


@pytest.mark.parametrize('change',['cancel','focus','input','receipt','fix','scope','cursor'])
def test_final_physical_callback_cannot_publish_changed_contact_state(f,monkeypatch,change):
    c,_=begin(f);seal=pulse(f,c);fixes=pair(f,c,seal,y=2.4);old=f.ledger._state()
    observe=f.policy.observe_transfer
    def changed(*args):
        result=observe(*args)
        if change=='cancel':c.cancel('F9 during final observation')
        elif change=='focus':f.focus=False
        elif change=='input':f.active=True
        elif change=='receipt':object.__setattr__(seal.receipt,'key_code',106)
        elif change=='fix':object.__setattr__(fixes[1],'compatible_states',())
        elif change=='scope':object.__setattr__(f.policy.declaration,'maximum_distance',200.)
        else:c.cursor+=1
        return result
    # Physical changes must occur inside the provider, before its final
    # checks. Pure receipt/data mutations additionally probe the return seam.
    if change in ('focus','input'):
        sample=f.policy.owner_input.sample
        def changed_sample():
            result=sample()
            if change=='focus':f.focus=False
            else:f.active=True
            return result
        monkeypatch.setattr(f.policy.owner_input,'sample',changed_sample)
    else:monkeypatch.setattr(f.policy,'observe_transfer',changed)
    with pytest.raises((RuntimeError,ValueError)):c.acknowledge_stopped(seal,*fixes)
    assert f.ledger._state()==old and f.ledger.phase=='stopped' and c.arrival is None
    assert not f.drain_events()


def test_new_pair_cannot_cross_the_original_displacement_budget(f):
    object.__setattr__(f.policy.declaration,'maximum_distance',.3)
    c,_=begin(f);old=f.ledger._state();seal=pulse(f,c)
    with pytest.raises(RuntimeError,match='displacement budget'):pair(f,c,seal,y=2.4)
    assert c.phase=='stopped' and f.ledger._state()==old


def test_reference_cannot_change_after_it_leaves_recent_reply_queue(f):
    c,_=begin(f);seal=pulse(f,c);c.acknowledge_stopped(seal,*pair(f,c,seal,y=2.4))
    reference=c.reference;seal=pulse(f,c);fixes=pair(f,c,seal,y=2.8)
    assert all(v[0] is not reference for v in c._issued)
    object.__setattr__(reference,'package_xyz',(4.,100.,.2))
    with pytest.raises(RuntimeError,match='lease, cache'):c.acknowledge_stopped(seal,*fixes)
    assert c.phase=='stopped' and f.ledger.reference.package_xyz==(4.,2.,.2)


def test_both_goal_samples_are_required_and_arrival_cannot_send_again(f):
    c,_=begin(f)
    for y in (2.4,2.8,3.2):
        seal=pulse(f,c);c.acknowledge_stopped(seal,*pair(f,c,seal,y=y))
    seal=pulse(f,c);result=c.acknowledge_stopped(seal,*pair(f,c,seal,y=3.5,z=2.79,second_y=3.6))
    assert result.kind=='in_contact' and c.cursor==0 and c.arrival is None
    seal=pulse(f,c);result=c.acknowledge_stopped(seal,*pair(f,c,seal,y=3.8,z=2.79))
    assert result.kind=='arrived'
    old=f.ledger._state()
    with pytest.raises(RuntimeError):c.prepare('forward')
    assert f.ledger._state()==old and not f.drain_events()


@pytest.mark.parametrize('change',['cancel','focus','input'])
def test_contact_geometry_does_not_block_stop_and_cannot_publish_after_revoke(f,monkeypatch,change):
    import threading
    c,_=begin(f);old=f.ledger._state();cover=c.index.cover_pulse;done=threading.Event()
    def changed(*args,**kwargs):
        def revoke():
            with c.lock:
                if change=='cancel':c.cancel('F9 during contact geometry')
                elif change=='focus':f.focus=False
                else:f.active=True
                done.set()
        thread=threading.Thread(target=revoke);thread.start()
        assert done.wait(.5);thread.join()
        return cover(*args,**kwargs)
    monkeypatch.setattr(c.index,'cover_pulse',changed)
    if change=='cancel':
        with pytest.raises(RuntimeError):c.prepare('forward')
    else:
        # Geometric preparation supplies no physical permit. The existing
        # sender/policy still denies input when focus or owner activity changes.
        c.prepare('forward')
        with pytest.raises(RuntimeError):f.policy.observe()
        c.cancel('revoked before input')
    assert c.phase=='stopped' and f.ledger._state()==old and not f.drain_events()


@pytest.mark.parametrize('change',['arrival_clone','fix_clone','scope','cancel'])
def test_arrival_validation_rechecks_final_provider_return(f,monkeypatch,change):
    c,_=begin(f);result,_=traverse(f,c);arrival=result.arrival;old=f.ledger._state()
    observe=f.policy.observe_contact_arrival
    def changed(*args):
        value=observe(*args)
        if change=='arrival_clone':c.arrival=replace(arrival)
        elif change=='fix_clone':object.__setattr__(arrival,'second',replace(arrival.second))
        elif change=='scope':object.__setattr__(f.policy.declaration,'maximum_seconds',200.)
        else:c.cancel('F9 during arrival validation')
        return value
    monkeypatch.setattr(f.policy,'observe_contact_arrival',changed)
    with pytest.raises(RuntimeError):c.validate_arrival(arrival)
    assert c.phase=='stopped' and f.ledger._state()==old and not f.drain_events()


def test_raw_reply_cannot_change_after_contact_classification(f,monkeypatch):
    c,_=begin(f);seal=pulse(f,c);old=f.ledger._state()
    f.now=seal.receipt.up_completed_at+.2;raw=f.position(y=2.4)
    compatible=c.index.compatible
    def changed(*args,**kwargs):
        result=compatible(*args,**kwargs)
        f.clock_hook=lambda:object.__setattr__(raw,'raw_coordinates',(2.4,4.,99.))
        return result
    monkeypatch.setattr(c.index,'compatible',changed)
    with pytest.raises(RuntimeError):c.observe_reply(seal,raw)
    assert c.phase=='stopped' and f.ledger._state()==old and not c._issued


def test_near_goal_with_only_second_sample_reached_keeps_existing_up_seal(f):
    c,_=begin(f)
    for y in (2.4,2.8,3.2):
        seal=pulse(f,c);c.acknowledge_stopped(seal,*pair(f,c,seal,y=y))
    seal=pulse(f,c);f.now=seal.receipt.up_completed_at+.2
    a=c.observe_reply(seal,f.position(x=4.01,y=3.55,z=2.79));f.now+=.4
    b=c.observe_reply(seal,f.position(x=4.01,y=3.8,z=2.79))
    old=f.ledger._state();steps=c.local_steps
    result=c.acknowledge_stopped(seal,a,b)
    assert result.kind=='settling' and c._sealed is seal and c.local_steps==steps
    result=c.acknowledge_stopped(seal,*pair(f,c,seal,y=3.8,z=2.79))
    assert result.kind=='arrived' and f.ledger._state()==old


def test_final_allowed_pulse_can_publish_and_validate_terminal_arrival(f):
    object.__setattr__(f.policy.declaration,'maximum_steps',4)
    c,_=begin(f);result,_=traverse(f,c)
    assert c.steps==4
    assert c.validate_arrival(result.arrival) is result.arrival
    with pytest.raises(RuntimeError):f.policy.observe()
    with pytest.raises(RuntimeError):c.next_command()
