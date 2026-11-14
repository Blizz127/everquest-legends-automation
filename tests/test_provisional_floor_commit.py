"""Delayed source decisions preserve release freshness and cancellation."""
from dataclasses import replace
import os
import threading
import time

import pytest

from eql_automation.fixed_route_follower import RouteHalt
from eql_automation.provisional_floor_commit import ProvisionalRouteFloorCommit
from test_ground_observer import raw
from test_route_floor_commit import setup,receipt,legacy
from eql_automation.uinput_watchdog import PulseSelection,selected_key_pulse_receipt,_EVENT


def fixture(legacy):
    context=[('owner','reader',54,'Fixture',1,'line-hash')]
    f=setup(legacy,ledger_factory=lambda *a,**kw:
        ProvisionalRouteFloorCommit(*a,context_reader=lambda:context[0],**kw))
    f.context=context
    return f


def seal(f,**changes):
    ticket=f.stage();r=receipt(ticket,**changes)
    f.state['now']=r.up_completed_at+.001
    return f.ledger.seal_release(ticket,r)


def pair(f,sealed,*,x=1.22):
    samples=[]
    for seq,delay in ((3,2.6),(4,3.05)):
        f.state['now']=sealed.receipt.up_completed_at+delay
        provisional=f.ledger.floor_for_observation(sealed)
        fix=raw(x=x,log_line_seq=seq,received_monotonic=f.clock())
        samples.append(f.observer.observe(fix,route=f.runner.route,segment_index=0,
            height_calibration=f.runner.height_calibration,
            motion_calibration_record_id=f.runner.calibration,now=f.clock(),floor_chain=provisional))
    return samples


def test_release_seals_without_advancing_pose_then_fresh_source_pair_commits_once(legacy):
    f=fixture(legacy);before=dict(vars(f.runner.pose));sealed=seal(f)
    assert not sealed.input_authorized and not sealed.real_client_accepted
    assert f.ledger.chain is f.chain and f.chain.index==1
    assert f.runner.phase=='proposed' and f.runner.steps==0 and vars(f.runner.pose)==before
    assert sealed.expires_at==sealed.receipt.up_completed_at+10.
    observations=pair(f,sealed)
    assert f.clock()-sealed.receipt.up_completed_at>3.
    step=f.ledger.resolve_source(sealed,*observations)
    assert f.ledger.chain.index==2 and step is f.ledger.chain.previous
    assert f.chain.index==1 and f.runner.phase=='ready' and f.runner.steps==1
    assert f.runner.last_seq==4 and f.runner.pose.x==1.22
    assert f.ledger._sealed is f.ledger._pending is f.ledger._busy is None
    with pytest.raises(RouteHalt):f.ledger.resolve_source(sealed,*observations)
    assert f.ledger.chain.index==2


@pytest.mark.parametrize('change',['stale','interrupted','wrong_key','overrun','late_down'])
def test_receipt_must_still_be_fresh_and_complete_at_seal(legacy,change):
    f=fixture(legacy);ticket=f.stage();r=receipt(ticket)
    f.state['now']=r.up_completed_at+.001
    if change=='stale':f.state['now']=r.up_completed_at+.301
    elif change=='interrupted':r=replace(r,completion='interrupted')
    elif change=='wrong_key':r=replace(r,key_code=105)
    elif change=='overrun':
        r=replace(r,up_started_at=r.down_started_at+.11,up_completed_at=r.down_started_at+.111)
        f.state['now']=r.up_completed_at+.001
    else:
        r=replace(r,down_started_at=r.down_started_at+.1,down_completed_at=r.down_completed_at+.1,
            up_started_at=r.up_started_at+.1,up_completed_at=r.up_completed_at+.1)
        f.state['now']=r.up_completed_at+.001
    with pytest.raises(RouteHalt):f.ledger.seal_release(ticket,r)
    assert f.ledger.chain is f.chain and f.runner.steps==0 and f.ledger._sealed is None


@pytest.mark.parametrize('change',['stop','context','generation','assist','pose','fork','expiry','replaced_seal'])
def test_loading_stop_or_changed_context_discards_seal_without_floor_commit(legacy,change):
    f=fixture(legacy);sealed=seal(f);observations=pair(f,sealed)
    if change=='stop':f.ledger.cancel('loading observed')
    elif change=='context':f.context[0]=('changed source',)
    elif change=='generation':f.state['generation']+=1
    elif change=='assist':f.state['mode']='assist'
    elif change=='pose':f.runner.pose.x+=.1
    elif change=='fork':f.evaluated[0][1]._selected.clear()
    elif change=='expiry':f.state['now']=sealed.expires_at+.001
    else:sealed=replace(sealed)
    with pytest.raises(RouteHalt):f.ledger.resolve_source(sealed,*observations)
    assert f.ledger.chain is f.chain and f.chain.index==1 and f.ledger._sealed is None
    assert f.runner.phase=='halted' and f.runner.steps==0


@pytest.mark.parametrize('change',['foreign_zone','outside','source_height','stale_pair','moving','old_pair'])
def test_source_resolution_requires_the_sealed_floor_and_fresh_stopped_pair(legacy,change):
    f=fixture(legacy);sealed=seal(f);a,b=pair(f,sealed)
    if change=='foreign_zone':
        r=replace(b.raw_fix,zone_id=58)
        b=replace(b,raw_fix=r,source_floor=replace(b.source_floor,raw_fix=r),
            mesh_projection=replace(b.mesh_projection,raw_fix=r))
    elif change=='outside':
        r=replace(b.raw_fix,raw_coordinates=(2.,2.4,2.7))
        b=replace(b,raw_fix=r,source_floor=replace(b.source_floor,raw_fix=r,ground_wld_xyz=(2.,2.4,.2)),
            mesh_projection=replace(b.mesh_projection,raw_fix=r,package_xyz=(2.4,2.,.6)))
    elif change=='source_height':b=replace(b,source_floor=replace(b.source_floor,ground_wld_xyz=(2.,1.22,.21)))
    elif change=='stale_pair':f.state['now']+=.6
    elif change=='moving':
        r=replace(b.raw_fix,raw_coordinates=(2.,1.6,2.7))
        b=replace(b,raw_fix=r,source_floor=replace(b.source_floor,raw_fix=r,ground_wld_xyz=(2.,1.6,.2)),
            mesh_projection=replace(b.mesh_projection,raw_fix=r,package_xyz=(1.6,2.,.6)))
    else:a=b=f.reference
    with pytest.raises((RouteHalt,ValueError)):f.ledger.resolve_source(sealed,a,b)
    assert f.ledger.chain is f.chain and f.chain.index==1 and f.runner.phase=='halted'


@pytest.mark.parametrize('operation',['commit','second_seal','check_pending'])
def test_seal_cannot_be_reused_as_an_ordinary_step(legacy,operation):
    f=fixture(legacy);sealed=seal(f)
    with pytest.raises(RouteHalt):
        if operation=='commit':f.ledger.commit(sealed.ticket,sealed.receipt)
        elif operation=='second_seal':f.ledger.seal_release(sealed.ticket,sealed.receipt)
        else:f.ledger.check_pending(sealed.ticket)
    assert f.ledger.chain is f.chain and f.runner.steps==0


@pytest.mark.parametrize('where',['seal_context','seal_clock','release','observe','resolve_context'])
def test_reentrant_stop_cannot_be_overwritten_into_a_committed_source_floor(legacy,where):
    f=fixture(legacy)
    if where.startswith('seal_'):
        ticket=f.stage();r=receipt(ticket);f.state['now']=r.up_completed_at+.001
        if where=='seal_context':
            def context():f.ledger.cancel('stop during source callback');return f.context[0]
            f.ledger.context_reader=f.ledger._context_reader=context
        else:
            def clock():f.ledger.cancel('stop during clock');return f.state['now']
            f.ledger.clock=clock
        with pytest.raises(RouteHalt):f.ledger.seal_release(ticket,r)
    else:
        sealed=seal(f);observations=pair(f,sealed)
        if where=='release':
            original=f.runner.record_release
            def release(*a,**kw):original(*a,**kw);f.ledger.cancel('stop after release')
            f.runner.record_release=release
        elif where=='observe':
            original=f.runner.observe_stopped
            def observe(*a,**kw):
                original(*a,**kw);f.ledger.cancel('stop after observation');f.runner.phase='ready'
            f.runner.observe_stopped=observe
        else:
            def context():f.ledger.cancel('stop during source callback');return f.context[0]
            f.ledger.context_reader=f.ledger._context_reader=context
        with pytest.raises(RouteHalt):f.ledger.resolve_source(sealed,*observations)
    assert f.ledger.chain is f.chain and f.chain.index==1 and f.ledger._sealed is None
    assert f.runner.phase=='halted'


def test_actual_pipe_receipt_seals_then_synthetic_delayed_pair_resolves(legacy):
    offset=[0.];clock=lambda:time.monotonic()+offset[0]
    lock=threading.RLock();rd,wr=os.pipe();pending={}
    def select():
        f=setup(legacy,clock=clock,lock=lock,ledger_factory=lambda *a,**kw:
            ProvisionalRouteFloorCommit(*a,context_reader=lambda:('synthetic-source',54,1),**kw))
        ticket=f.stage();pending.update(fixture=f,ticket=ticket)
        p=ticket.preparation
        return PulseSelection(p.movement_key,p.requested_seconds,p.proposal.at+.05)
    try:
        actual=selected_key_pulse_receipt(wr,select,go_lock=lock)
        f=pending['fixture'];sealed=f.ledger.seal_release(pending['ticket'],actual)
        assert f.ledger.chain.index==1 and f.runner.steps==0
        fixes=[];x=1.+10.*actual.maximum_held_seconds
        for seq,delay in ((3,2.6),(4,3.05)):
            # Real DOWN/UP only; subsequent elapsed time and positions are
            # explicitly simulated, never a claim of client consumption.
            offset[0]=actual.up_completed_at+delay-time.monotonic()
            at=clock();fork=f.ledger.floor_for_observation(sealed)
            fixes.append(f.observer.observe(raw(x=x,log_line_seq=seq,received_monotonic=at),
                route=f.runner.route,segment_index=0,height_calibration=f.runner.height_calibration,
                motion_calibration_record_id=f.runner.calibration,now=clock(),floor_chain=fork))
        f.ledger.resolve_source(sealed,*fixes)
        assert f.ledger.chain.index==2 and f.runner.steps==1 and f.runner.phase=='ready'
    finally:
        os.close(wr);data=b''
        while part:=os.read(rd,4096):data+=part
        os.close(rd)
    events=[(kind,key,value) for _,_,kind,key,value in _EVENT.iter_unpack(data)]
    assert events[:4]==[(1,103,1),(0,0,0),(1,103,0),(0,0,0)]


@pytest.mark.parametrize('change',['generation','context','assist'])
def test_final_clock_cannot_publish_after_external_scope_changed(legacy,change):
    f=fixture(legacy);sealed=seal(f);observations=pair(f,sealed);calls=[]
    def clock():
        if f.runner.phase=='ready' and f.ledger._busy=='resolve':
            calls.append(1)
            if len(calls)==2:
                if change=='generation':f.state['generation']+=1
                elif change=='context':f.context[0]=('changed source',)
                else:f.state['mode']='assist'
        return f.state['now']
    f.ledger.clock=clock
    with pytest.raises(RouteHalt):f.ledger.resolve_source(sealed,*observations)
    assert calls==[1,1] and f.ledger.chain is f.chain and f.runner.phase=='halted'


def test_clockwise_footprint_uses_the_same_hull_as_staging(legacy):
    f=fixture(legacy);ticket=f.stage(footprint=tuple(reversed(f.footprint)))
    r=receipt(ticket);f.state['now']=r.up_completed_at+.001
    sealed=f.ledger.seal_release(ticket,r)
    f.ledger.resolve_source(sealed,*pair(f,sealed))
    assert f.ledger.chain.index==2 and f.runner.phase=='ready'


@pytest.mark.parametrize('change',['generation','context'])
def test_final_seal_clock_rechecks_source_scope(legacy,change):
    f=fixture(legacy);ticket=f.stage();r=receipt(ticket);f.state['now']=r.up_completed_at+.001
    calls=[]
    def clock():
        calls.append(1)
        if len(calls)==3:
            if change=='generation':f.state['generation']+=1
            else:f.context[0]=('different source',)
        return f.state['now']
    f.ledger.clock=clock
    with pytest.raises(RouteHalt):f.ledger.seal_release(ticket,r)
    assert f.ledger.chain is f.chain and f.ledger._sealed is None and f.runner.steps==0
