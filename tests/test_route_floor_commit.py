"""Receipt-bound floor state; actual watchdog integration uses a pipe only."""
from dataclasses import replace
from hashlib import sha256
import importlib.util
import os
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from eql_automation.fixed_route_follower import FixedRouteFollower,RouteHalt
from eql_automation.floor_replay import check_floor_trial
from eql_automation.ground_sweep import GroundFace,check_ground_coverage
from eql_automation.portal_precision import SourceFace
from eql_automation.route_floor_commit import RouteFloorCommit
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.uinput_watchdog import PulseReceipt,PulseSelection,selected_key_pulse_receipt,_EVENT
from test_ground_observer import fixture as observer_fixture,rectangle,HEIGHT,GEOMETRY,ROUTE,raw


@pytest.fixture(scope='module')
def legacy():
    if importlib.util.find_spec('numpy') is None:pytest.skip('Retained helper requires numpy')
    from test_fixed_route_follower import HELPER,PINS
    if not HELPER.exists():pytest.skip('Retained helper source is required')
    for name,digest in PINS.items():assert sha256((HELPER/name).read_bytes()).hexdigest()==digest
    sys.path.insert(0,str(HELPER))
    from eqnav import steer
    return steer


def setup(legacy,*,clock=None,lock=None):
    state={'now':100.,'mode':'measurement','generation':1}
    clock=(lambda:state['now']) if clock is None else clock
    observer,mesh,_,_=observer_fixture()
    sources=tuple(SourceFace(tuple((y,x,z) for x,y,z in triangle),0,'Diffuse',1,i)
                  for i,triangle in enumerate(rectangle(0.,4.,.2)))
    chain=SourceFloorChain(inventory_sha256=GEOMETRY.source_wld_sha256,
        seed_evidence_sha256='f'*64,seed_ids=((1,0),(1,1)),body_height=8.)
    assert chain.advance(((.2,.2),(2.8,.2),(2.8,2.8),(.2,2.8)),sources).candidate
    at=clock();height=replace(HEIGHT,valid_from_monotonic=max(0.,at-5.),valid_until_monotonic=at+200.)
    motion=legacy.Motion(run_speed=10.,turn_rate=170.,right_sign=-1,turn_latency=.03,back_speed=5.)
    runner=FixedRouteFollower(ROUTE,legacy=legacy,motion=motion,heading=90.,
        calibration_record_id='synthetic-receipt-motion',height_calibration=height,
        geometry_evidence=GEOMETRY,generation=1,generation_reader=lambda:state['generation'],
        mode_reader=lambda:state['mode'])
    fixes=[observer.observe(raw(received_monotonic=at+offset,log_line_seq=i),
        route=ROUTE,segment_index=0,height_calibration=height,
        motion_calibration_record_id=runner.calibration,now=at+offset,floor_chain=chain)
        for i,offset in ((1,-.4),(2,0.))]
    runner.observe_stopped(*fixes,released_at=at-.53,now=at)
    lock=threading.RLock() if lock is None else lock
    ledger=RouteFloorCommit(runner,chain,stop_lock=lock,clock=clock)
    ground=SimpleNamespace(polys=(0,0,1,1),triangles=mesh._detail,areas=(63,63),components=(7,7))
    view=SimpleNamespace(ground=ground,seams=(),by_polygon={},source_faces_for_footprint=lambda _:sources)
    footprint=((.5,1.5),(2.2,1.5),(2.2,2.5),(.5,2.5))
    evaluated=[]
    def check(request,base):
        assert request.input_authorized is False
        assert base is not chain and base.previous is chain.previous
        faces=tuple(GroundFace(v,63,7) for v in ground.triangles)
        reference=request.reference_fix.mesh_projection.package_xyz
        original=check_ground_coverage(request.footprint,faces,reference=reference,component=7,vertical_window=1.)
        fork,trial=check_floor_trial(view,base,original,request.footprint,(0,1,2,3),
            reference=reference,component=7,vertical_window=1.,maximum_source_z_difference=1.)
        assert trial.candidate and not trial.input_authorized
        evaluated.append((request,fork,trial))
        return fork,trial
    def stage(**changes):
        state['now']+=.01
        proposal=runner.propose(clock())
        options=dict(reference_fix=fixes[-1],footprint=footprint,sources=sources,
            requested_seconds=.02,maximum_actual_hold=.1,movement_key=103,
            motion_bounds_record_id='synthetic-checked-hold-bound',check_geometry=check)
        options.update(changes)
        return ledger.stage(proposal,**options)
    return SimpleNamespace(state=state,clock=clock,observer=observer,chain=chain,runner=runner,
        ledger=ledger,stage=stage,check=check,evaluated=evaluated,lock=lock,
        reference=fixes[-1],footprint=footprint,sources=sources)


def receipt(ticket,**changes):
    p=ticket.preparation;down=p.proposal.at+.01
    return replace(PulseReceipt(p.movement_key,p.requested_seconds,down,down+.001,
        down+.021,down+.022,'elapsed'),**changes)


def test_matching_release_commits_once_and_does_not_claim_input_authority(legacy):
    f=setup(legacy);before=f.chain.previous;ticket=f.stage()
    assert not ticket.input_authorized and f.ledger.chain is f.chain and f.chain.previous is before
    result=receipt(ticket);f.state['now']=result.up_completed_at+.001
    step=f.ledger.commit(ticket,result)
    assert f.runner.phase=='await_stopped' and f.runner.steps==1
    assert f.ledger.chain is f.evaluated[0][1] and step is f.ledger.chain.previous
    assert f.chain.previous is before and f.chain.index==1
    with pytest.raises(RouteHalt):f.ledger.commit(ticket,result)
    assert f.ledger.chain.index==2 and f.runner.phase=='halted'


@pytest.mark.parametrize('change',['mode','full_auto','generation','calibration','height','geometry',
    'motion','pose','radius','fork_faces','fork_area','base_faces','proposal'])
def test_changed_context_discards_fork_and_halts(legacy,change):
    f=setup(legacy);ticket=f.stage();fork=f.evaluated[0][1]
    if change=='mode':f.state['mode']='assist'
    elif change=='full_auto':f.state['mode']='full_auto'
    elif change=='generation':f.state['generation']=2
    elif change=='calibration':f.runner.calibration='different'
    elif change=='height':f.runner.height_calibration=replace(f.runner.height_calibration)
    elif change=='geometry':f.runner.geometry_evidence=replace(f.runner.geometry_evidence)
    elif change=='motion':f.runner.motion=replace(f.runner.motion,turn_rate=200.)
    elif change=='pose':f.runner.pose._turn_held['left']=.1
    elif change=='radius':f.runner.radius=.2
    elif change=='fork_faces':fork._selected.clear()
    elif change=='fork_area':fork._expanded=()
    elif change=='base_faces':f.chain._selected.clear()
    elif change=='proposal':f.runner.pending=replace(f.runner.pending)
    result=receipt(ticket);f.state['now']=result.up_completed_at+.001
    with pytest.raises(RouteHalt):f.ledger.commit(ticket,result)
    assert f.ledger.chain is f.chain and f.runner.steps==0 and f.runner.phase=='halted'


@pytest.mark.parametrize('change',['key','duration','completion','order','future','stale','overrun','late_down','nan'])
def test_invalid_receipt_never_advances_committed_floor(legacy,change):
    f=setup(legacy);ticket=f.stage();r=receipt(ticket)
    f.state['now']=r.up_completed_at+.001
    if change=='key':r=replace(r,key_code=105)
    elif change=='duration':r=replace(r,requested_seconds=.03)
    elif change=='completion':r=replace(r,completion='stopped')
    elif change=='order':r=replace(r,up_started_at=r.down_started_at-.01)
    elif change=='future':f.state['now']=r.up_completed_at-.001
    elif change=='stale':f.state['now']=r.up_completed_at+.301
    elif change=='overrun':
        r=replace(r,up_started_at=r.down_started_at+.11,up_completed_at=r.down_started_at+.111)
        f.state['now']=r.up_completed_at+.001
    elif change=='late_down':
        r=replace(r,down_started_at=r.down_started_at+.05,down_completed_at=r.down_completed_at+.05,
            up_started_at=r.up_started_at+.05,up_completed_at=r.up_completed_at+.05)
        f.state['now']=r.up_completed_at+.001
    elif change=='nan':r=replace(r,down_completed_at=float('nan'))
    with pytest.raises(RouteHalt):f.ledger.commit(ticket,r)
    assert f.ledger.chain is f.chain and f.chain.index==1 and f.runner.steps==0


@pytest.mark.parametrize('change',['footprint','hold','wrong_fork','elapsed','reference','cancel','record_failure'])
def test_staging_and_release_errors_preserve_previous_commit(legacy,change):
    f=setup(legacy)
    if change=='hold':
        with pytest.raises(RouteHalt):f.stage(maximum_actual_hold=.3)
    elif change=='reference':
        with pytest.raises(RouteHalt):f.stage(reference_fix=None)
    elif change in ('footprint','wrong_fork','elapsed'):
        def altered(request,base):
            if change=='footprint':request=replace(request,footprint=((.4,1.4),(2.3,1.4),(2.3,2.6),(.4,2.6)))
            fork,trial=f.check(request,base)
            if change=='wrong_fork':fork.index+=1
            if change=='elapsed':f.state['now']+=.06
            return fork,trial
        with pytest.raises(RouteHalt):f.stage(check_geometry=altered)
    else:
        ticket=f.stage();r=receipt(ticket);f.state['now']=r.up_completed_at+.001
        if change=='cancel':f.ledger.cancel('owner stop')
        else:
            def fail(*args,**kwargs):raise RuntimeError('receipt integration failed')
            f.runner.record_release=fail
        with pytest.raises(RouteHalt):f.ledger.commit(ticket,r)
    assert f.ledger.chain is f.chain and f.chain.index==1 and f.runner.phase=='halted'


def test_nonreentrant_lock_is_rejected_before_any_watchdog_use(legacy):
    with pytest.raises(ValueError,match='reentrant'):setup(legacy,lock=threading.Lock())


def test_down_cannot_precede_completed_geometry_staging(legacy):
    f=setup(legacy)
    def check(request,base):
        result=f.check(request,base)
        f.state['now']+=.015
        return result
    ticket=f.stage(check_geometry=check)
    r=receipt(ticket);assert r.down_started_at<ticket.staged_at
    f.state['now']=r.up_completed_at+.001
    with pytest.raises(RouteHalt,match='Receipt'):f.ledger.commit(ticket,r)
    assert f.ledger.chain is f.chain and f.runner.steps==0


@pytest.mark.parametrize('operation',['stage','commit','cancel'])
def test_reentrant_operation_during_geometry_cannot_publish_or_overwrite_ticket(legacy,operation):
    f=setup(legacy)
    def reenter(request,base):
        if operation=='stage':
            with pytest.raises(RouteHalt):
                f.ledger.stage(request.proposal,reference_fix=request.reference_fix,
                    footprint=request.footprint,sources=request.sources,
                    requested_seconds=request.requested_seconds,maximum_actual_hold=request.maximum_actual_hold,
                    movement_key=request.movement_key,motion_bounds_record_id=request.motion_bounds_record_id,
                    check_geometry=f.check)
        elif operation=='commit':
            with pytest.raises(RouteHalt):f.ledger.commit(None,None)
        else:f.ledger.cancel('stop during geometry')
        return f.check(request,base)  # Even swallowing the inner error cannot revive this stage.
    with pytest.raises(RouteHalt):f.stage(check_geometry=reenter)
    assert f.ledger._pending is None and f.ledger._busy is None
    assert f.ledger.chain is f.chain and f.chain.index==1 and f.runner.phase=='halted'


@pytest.mark.parametrize('operation',['nested_commit','cancel_after_release','no_op'])
def test_receipt_integration_cannot_reenter_or_silently_skip_release(legacy,operation):
    f=setup(legacy);ticket=f.stage();r=receipt(ticket)
    f.state['now']=r.up_completed_at+.001
    original=f.runner.record_release
    def integrate(*args,**kwargs):
        if operation=='nested_commit':
            with pytest.raises(RouteHalt):f.ledger.commit(ticket,r)
        elif operation=='cancel_after_release':
            original(*args,**kwargs);f.ledger.cancel('owner stop during receipt')
        # A swallowed cancellation or no-op must not commit the source fork.
    f.runner.record_release=integrate
    with pytest.raises(RouteHalt):f.ledger.commit(ticket,r)
    assert f.ledger.chain is f.chain and f.chain.index==1 and f.runner.phase=='halted'
    assert f.ledger._pending is None and f.ledger._busy is None


def test_actual_pipe_watchdog_receipt_drives_commit(legacy):
    lock=threading.RLock();rd,wr=os.pipe();pending={}
    def select():
        # Build fresh synthetic observations after child READY, so startup
        # cannot age the proposal. No UI/device/live scene is being simulated.
        f=setup(legacy,clock=time.monotonic,lock=lock)
        ticket=f.stage();pending.update(fixture=f,ticket=ticket)
        p=ticket.preparation
        return PulseSelection(p.movement_key,p.requested_seconds,p.proposal.at+.05)
    try:
        actual=selected_key_pulse_receipt(wr,select,go_lock=lock)
        f=pending['fixture'];f.ledger.commit(pending['ticket'],actual)
        assert f.ledger.chain.index==2 and f.runner.phase=='await_stopped'
        assert f.runner.released_at==actual.up_completed_at
        # Only the receipt is real pipe I/O. Hypothetical post-release fixes
        # use the newly committed chain and the actual ground producer.
        x=1.+10.*actual.maximum_held_seconds
        fixes=[f.observer.observe(raw(x=x,received_monotonic=actual.up_completed_at+offset,
                    log_line_seq=seq),route=ROUTE,segment_index=f.runner.index,
                height_calibration=f.runner.height_calibration,
                motion_calibration_record_id=f.runner.calibration,
                now=actual.up_completed_at+offset,floor_chain=f.ledger.chain)
            for seq,offset in ((3,.13),(4,.53))]
        f.runner.observe_stopped(*fixes,released_at=actual.up_completed_at,
            now=actual.up_completed_at+.53)
        assert f.runner.phase=='ready' and f.runner.last_seq==4
    finally:
        os.close(wr);data=b''
        while chunk:=os.read(rd,4096):data+=chunk
        os.close(rd)
    events=[(kind,key,value) for _,_,kind,key,value in _EVENT.iter_unpack(data)]
    assert events[:4]==[(1,103,1),(0,0,0),(1,103,0),(0,0,0)]
