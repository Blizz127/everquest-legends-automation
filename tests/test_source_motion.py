"""Actual watchdog pipe writes; all game positions/scenes are synthetic."""
from dataclasses import replace
from copy import deepcopy
import os
import threading
import time
from types import SimpleNamespace

import pytest
import numpy as np

from eql_automation.current_source_itinerary import plan_current_source_itinerary
from eql_automation.g2_safety_provider import GameWindowIdentity
from eql_automation.observed_height import measure_current_height
from eql_automation.owner_input_observer import OwnerInputObservation
from eql_automation.scene_log_veto import SceneLogVeto
from eql_automation.source_itinerary import SourceItineraryGuide,SourceWalkHint,SourceStepHint
from eql_automation.portal_precision import SourceFace
from eql_automation.source_motion import SourceReceiptLedger
from eql_automation.source_observer import SourceItineraryObserver
from eql_automation.source_step_sender import run_checked_source_step
from eql_automation.supervised_route import SupervisedRouteDeclaration
from eql_automation.supervised_source import SupervisedSourcePolicy
from eql_automation.uinput_watchdog import _EVENT, PulseReceipt
from test_floor_bootstrap import fresh
from test_installed_region_model import files
from test_native_region_policy import setup
from test_route_floor_commit import legacy
from test_route_step_sender import PipeSender,after_down


@pytest.fixture
def f(tmp_path,monkeypatch,legacy,request):
    model=files(tmp_path,monkeypatch)
    f=setup(tmp_path);f.real=False;f.mode='measurement';f.generation=1;f.focus=True;f.active=False
    f.clock_hook=None
    def clock():
        hook=f.clock_hook
        if hook is not None:
            f.clock_hook=None;hook()
        return time.monotonic() if f.real else f.now
    f.clock=clock
    f.options['clock']=f.clock
    f.options['bounds']=replace(f.options['bounds'],maximum_requested_hold=.02,
        maximum_actual_hold=.05,forward_speed_upper_bound=20.)
    f.now=time.monotonic()-2.;f.a=f.position();f.now+=.5;f.b=f.position()
    f.options['released_at']=f.a.received_monotonic-.2
    p=f.planner
    guide=SourceItineraryGuide('crushbone',p.pins[2],p.pins[3],'f'*64,.1,6.,(4.,3.25),
        (SourceWalkHint((4.,2.),(4.,3.)),))
    if getattr(request,'param',None)=='step':
        def face(points,index):
            return SourceFace(tuple((y,x,z) for x,y,z in points),0,'Diffuse',10,index)
        def rect(y0,y1,z,index):
            a,b,c,d=(0.,y0,z),(10.,y0,z),(10.,y1,z),(0.,y1,z)
            return face((a,b,c),index),face((a,c,d),index+1)
        p.source.sources=(*rect(0.,3.3,.2,0),*rect(3.3,5.,.5125,2),
            face(((0.,3.3,.2),(10.,3.3,.2),(10.,3.3,.5125)),4),
            face(((0.,3.3,.2),(10.,3.3,.5125),(0.,3.3,.5125)),5))
        coords=np.asarray([s.vertices_wld for s in p.source.sources])[:,:,[1,0,2]]
        p.source.source_minimum=coords.min(axis=1);p.source.source_maximum=coords.max(axis=1)
        guide=replace(guide,goal=(4.,3.9),operations=(SourceWalkHint((4.,2.),(4.,3.1)),
            SourceStepHint((4.,3.1),(4.,3.5),((10,2),),.5,1.),SourceWalkHint((4.,3.5),(4.,3.9))))
    plan=plan_current_source_itinerary(p,f.reader,f.a,f.b,guide=guide,
        **{k:v for k,v in f.options.items() if k!='length'})
    a,b,options=fresh(f,plan.initial)
    cal=measure_current_height(plan.initial.observer,f.reader,a,b,**options)
    observer=SourceItineraryObserver(plan,f.reader,height_calibration=cal,binding_reader=lambda:f.owner,
        mode_reader=lambda:f.mode,generation_reader=lambda:f.generation,generation=1,clock=f.clock)
    ledger=SourceReceiptLedger(observer,terrain=p.source,static=p.static,bsp=p.bsp,
        bounds=f.options['bounds'],installed_model=model,legacy=legacy,
        motion=legacy.Motion(run_speed=10.,turn_rate=90.,right_sign=1,turn_latency=.005,back_speed=0.),
        heading=0.,stop_lock=threading.RLock())
    def position(x=4.,y=2.,z=2.7):
        f.append(f'Your Location is {y:.2f}, {x:.2f}, {z:.2f}')
        return f.reader.poll(now=f.clock())[0]
    f.position=position;f.now=time.monotonic()-.4
    first=observer.observe(position(),checked_chain=ledger.chain)
    f.now=time.monotonic()
    second=observer.observe(position(),checked_chain=ledger.chain)
    ledger.start(first,second,released_at=first.raw_fix.received_monotonic-.2)
    f.observer,f.ledger,f.plan,f.first,f.second=observer,ledger,plan,first,second
    f.real=True
    window=SimpleNamespace(id=42)
    f.gate=SimpleNamespace(windows=lambda:[window],focused_window=lambda:window if f.focus else None,
        game_session=lambda:{'pid':10,'start_ticks':'100'},controls_ready=lambda:f.focus)
    def sample():
        now=f.clock();return OwnerInputObservation(now,now,1,True,1,0,f.active,0,'synthetic-device')
    owner_input=SimpleNamespace(sample=sample)
    veto=SceneLogVeto(f.reader.tail.path,expected_character='Probe',expected_server='private',
        cancel_generation=1,clock=f.clock)
    d=SupervisedRouteDeclaration('source-pipe-trial',plan.itinerary.sha256,
        ledger.bounds.calibration_record_id,ledger.bounds.record_id,True,120.,32,20.,2.)
    f.policy=SupervisedSourcePolicy(ledger,declaration=d,gate=f.gate,owner_input=owner_input,log_veto=veto,
        expected_window=GameWindowIdentity(42,10,100),topology_generation=1,check_current=lambda:None)
    f.rd,f.wr=os.pipe();f.sender=PipeSender(f.wr);f.events=[]
    def drain_events():
        data=b'';os.set_blocking(f.rd,False)
        try:
            while True:
                try:part=os.read(f.rd,65536)
                except BlockingIOError:break
                if not part:break
                data+=part
        finally:os.set_blocking(f.rd,True)
        f.events.extend((kind,key,value) for _,_,kind,key,value in _EVENT.iter_unpack(data))
        return tuple(f.events)
    f.drain_events=drain_events
    def run():
        try:
            return run_checked_source_step(f.sender,ledger,policy=f.policy,kind='forward',
                requested_seconds=.02,command_state_clear=lambda:True,pump=lambda:None)
        except Exception as error:
            error.add_note('Source refusal: '+ledger.reason);raise
    f.run=run
    def replies(seal,*,y=2.2,z=2.7):
        f.real=False;f.now=max(time.monotonic(),seal.receipt.up_completed_at+.2)
        chain=ledger.floor_for_observation(seal)
        first=ledger.observe_reply(seal,position(y=y,z=z))
        f.now+=.4
        second=ledger.observe_reply(seal,position(y=y,z=z))
        return first,second
    f.replies=replies
    yield f
    os.close(f.wr);data=b''
    while block:=os.read(f.rd,65536):data+=block
    os.close(f.rd)
    f.events.extend((kind,key,value) for _,_,kind,key,value in _EVENT.iter_unpack(data))


def test_source_pulse_keeps_floor_and_pose_until_fresh_observed_cap_acknowledgment(f):
    chain=f.ledger.chain;pose=deepcopy(vars(f.ledger.pose));reference=f.ledger.reference
    seal=f.run()
    events=f.drain_events()
    assert events[:4]==((1,103,1),(0,0,0),(1,103,0),(0,0,0))
    assert all(kind!=1 or key==103 for kind,key,value in events)
    assert f.ledger.chain is chain and vars(f.ledger.pose)==pose and f.ledger.reference is reference
    assert f.ledger.phase=='await_stopped' and not f.sender.held
    pair=f.replies(seal);ack=f.ledger.acknowledge_stopped(seal,*pair)
    assert f.ledger.phase=='ready' and f.ledger.steps==1
    assert ack.floor_index==chain.index+2 and f.ledger.chain.index==ack.floor_index
    assert ack.reference.raw_fix is pair[1].raw_fix
    assert ack.reference.observed_at==pair[1].observed_at
    assert ack.reference.package_xyz==(4.,2.2,.2)
    assert ack.floor_proof_sha256==f.ledger.chain.previous.proof_sha256
    assert not ack.real_client_accepted and not ack.reference.input_authorized
    assert f.policy.snapshot()['dynamic_clearance_verified'] is False
    with pytest.raises(RuntimeError):f.ledger.acknowledge_stopped(seal,*pair)


@pytest.mark.parametrize('change',('off','assist','full_auto','generation','focus','input','model'))
def test_revocation_before_down_sends_no_input(f,change,tmp_path):
    if change in ('off','assist','full_auto'):f.mode=change
    elif change=='generation':f.generation+=1
    elif change=='focus':f.focus=False
    elif change=='input':f.active=True
    elif change=='model':(tmp_path/'EQGraphics.dll').write_bytes(b'changed')
    with pytest.raises((RuntimeError,ValueError)):f.run()
    assert f.sender.release_calls==0 and not f.sender.held
    assert f.ledger.steps==0


@pytest.mark.parametrize('change',('cancel','focus','input'))
def test_revocation_after_down_releases_and_does_not_commit(f,monkeypatch,change):
    chain=f.ledger.chain
    def stop():
        if change=='cancel':f.ledger.cancel('owner OFF')
        elif change=='focus':f.focus=False
        else:f.active=True
    after_down(monkeypatch,stop)
    with pytest.raises(RuntimeError):f.run()
    assert f.sender.release_calls>=1 and not f.sender.held
    assert f.ledger.chain is chain and f.ledger.steps==0
    assert f.ledger.phase=='stopped' and f.sender._eql_route_operation is None


def test_geometry_runs_without_stop_lock_and_cancel_does_not_publish(f):
    original=f.ledger._geometry;done=threading.Event()
    def geometry(*args):
        def stop():f.ledger.cancel('OFF during geometry');done.set()
        thread=threading.Thread(target=stop);thread.start()
        assert done.wait(.5);thread.join()
        return original(*args)
    f.ledger._geometry=geometry
    with pytest.raises(RuntimeError):f.run()
    assert not f.sender.held and f.sender.release_calls==0


@pytest.mark.parametrize('change',('wrong_height','outside','duplicate','moving','cancel_cap','slow_cap'))
def test_invalid_stopped_landing_preserves_old_floor(f,change):
    chain=f.ledger.chain;seal=f.run()
    if change in ('wrong_height','outside'):
        with pytest.raises(ValueError):f.replies(seal,**({'z':5.} if change=='wrong_height' else {'y':8.}))
        assert f.ledger.chain is chain;return
    pair=f.replies(seal)
    if change=='duplicate':pair=(pair[0],pair[0])
    elif change=='moving':pair=(pair[0],replace(pair[1],package_xyz=(4.,3.,.2)))
    else:
        original=f.ledger._geometry
        def geometry(*args):
            result=original(*args)
            if change=='cancel_cap':f.ledger.cancel('OFF while checking endpoint')
            else:f.now+=.6
            return result
        f.ledger._geometry=geometry
    with pytest.raises((RuntimeError,ValueError)):f.ledger.acknowledge_stopped(seal,*pair)
    assert f.ledger.chain is chain and f.ledger.steps==0


def test_source_observer_preserves_identity_and_does_not_call_mesh_observer(f):
    f.plan.initial.observer.observe=lambda *a,**k:(_ for _ in ()).throw(AssertionError('baked query'))
    f.observer.validate(f.second,f.ledger.chain,maximum_age=.5)
    with pytest.raises(ValueError):f.observer.validate(replace(f.second),f.ledger.chain)
    with pytest.raises(ValueError):f.observer.observe(f.second.raw_fix,checked_chain=f.ledger.chain)


def test_reference_expiry_after_preparation_does_not_renew_timestamp(f):
    original=f.ledger.prepare
    def delayed(kind):
        result=original(kind);f.real=False;f.now=time.monotonic()+.6;return result
    f.ledger.prepare=delayed
    with pytest.raises(ValueError):f.run()
    assert not f.sender.held and f.sender.release_calls==0


def proposed_receipt(f):
    """Synthetic timing only, for publication-boundary regression checks."""
    f.real=False;f.now=time.monotonic()
    geometry=f.ledger.prepare('forward')
    ticket=f.ledger.stage(geometry,requested_seconds=.02)
    at=ticket.proposed_at
    receipt=PulseReceipt(103,.02,at+.001,at+.002,at+.021,at+.022,'elapsed')
    f.now=at+.03
    return ticket,receipt


def change_scope(f,change):
    if change=='cancel':f.ledger.cancel('OFF at final publication callback')
    elif change=='generation':f.generation+=1
    elif change=='owner':f.owner=('Changed owner',)
    else:f.mode='assist'


@pytest.mark.parametrize('change',('cancel','generation','owner','assist'))
def test_final_seal_callback_cannot_resurrect_or_publish_changed_scope(f,monkeypatch,change):
    ticket,receipt=proposed_receipt(f);chain=f.ledger.chain
    original=type(f.ledger.model).check_policy
    def check(model,policy):
        result=original(model,policy)
        f.clock_hook=lambda:change_scope(f,change)
        return result
    monkeypatch.setattr(type(f.ledger.model),'check_policy',check)
    with pytest.raises((RuntimeError,ValueError)):
        f.ledger.seal_release(ticket,receipt)
    assert f.ledger.phase=='stopped' and f.ledger._sealed is None
    assert f.ledger.chain is chain and f.ledger.steps==0


@pytest.mark.parametrize('change',('generation','owner','assist'))
def test_observer_checks_scope_after_its_clock_callback(f,change):
    f.clock_hook=lambda:change_scope(f,change)
    with pytest.raises(ValueError):f.observer.check()


@pytest.mark.parametrize('change',('cancel','generation','owner','assist'))
def test_final_cap_validation_cannot_publish_changed_scope(f,monkeypatch,change):
    ticket,receipt=proposed_receipt(f)
    seal=f.ledger.seal_release(ticket,receipt);chain=f.ledger.chain
    pair=f.replies(seal);branch=f.ledger.floor_for_observation(seal)
    original=f.observer.validate
    def validate(observation,selected,**options):
        if selected is not chain and selected is not branch:
            calls=[0]
            def hook():
                calls[0]+=1
                if calls[0]==2:change_scope(f,change)
                else:f.clock_hook=hook
            f.clock_hook=hook
        return original(observation,selected,**options)
    monkeypatch.setattr(f.observer,'validate',validate)
    with pytest.raises((RuntimeError,ValueError)):
        f.ledger.acknowledge_stopped(seal,*pair)
    assert f.ledger.phase=='stopped' and f.ledger.chain is chain and f.ledger.steps==0


@pytest.mark.parametrize('change',('motion','terrain_query','terrain_array','static_query'))
def test_prepared_geometry_cannot_outlive_replaced_source_or_pose_motion(f,change):
    f.real=False;f.now=time.monotonic()
    geometry=f.ledger.prepare('forward')
    if change=='motion':f.ledger.pose.motion=deepcopy(f.ledger.motion)
    elif change=='terrain_query':f.ledger.terrain.source_faces_for_footprint=lambda _:()
    elif change=='terrain_array':f.ledger.terrain.source_minimum=f.ledger.terrain.source_minimum.copy()
    else:f.ledger.static.faces_for_footprint=lambda _:()
    with pytest.raises(RuntimeError):f.ledger.stage(geometry,requested_seconds=.02)
    assert f.ledger.phase=='stopped' and f.ledger.steps==0 and f.sender.release_calls==0
