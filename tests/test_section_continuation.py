"""Ordinary arrival -> seven measured probes -> onward route, with no camp.

All game data/observations are synthetic; movement goes only to isolated pipes.
"""
from dataclasses import replace
from types import SimpleNamespace
from copy import copy
import importlib
import math
import time

import pytest

from eql_automation.journey_input_budget import JourneyBudgetDeclaration,JourneyInputBudget
from eql_automation.owner_zone_tracker import ZoneReaderLease
from eql_automation.section_continuation import capture_section_arrival,SectionContinuation
from eql_automation.source_itinerary import SourceItineraryGuide,SourceWalkHint
from eql_automation.supervised_source import SupervisedSourcePolicy
from test_owner_source_runtime import setup,finish
from test_source_motion import f
from test_route_floor_commit import legacy
from test_route_step_sender import after_down
from test_motion_collection import retained


def prepare(f,tmp_path,monkeypatch):
    r,e,state=setup(f,tmp_path,monkeypatch,feedback=tuple((y,2.7) for y in (2.2,2.4,2.6,2.8,3.)))
    d=JourneyBudgetDeclaration('a'*64,'goblin-camp-stop','stop',2,300.,400,80.,1000.)
    b=JourneyInputBudget(d,clock=f.clock,stop_lock=f.ledger.lock,owner_binding=(1,),
        binding_reader=lambda:(f.generation,))
    p=r.policy
    r.policy=SupervisedSourcePolicy(f.ledger,declaration=p.declaration,gate=p.gate,
        owner_input=p.owner_input,log_veto=p.log_veto,expected_window=p.window,
        topology_generation=p.topology,check_current=p.check_current,journey_budget=b)
    r.owner_input.close=lambda:None
    try:finish(f,r)
    except Exception as error:
        error.add_note('Initial runtime: '+r.reason+'; ledger: '+f.ledger.reason)
        raise
    return r,e,b


def next_guide(r):
    return SourceItineraryGuide('crushbone',r.ledger.terrain.wld_sha256,
        r.ledger.static.inventory_sha256,'f'*64,.1,6.,(5.,8.),
        (SourceWalkHint((4.,3.25),(5.,8.)),))


def continuation(f,r,b,token,retained,legacy):
    r.lease.release()
    tracker=r.lease._tracker
    lease=ZoneReaderLease(tracker);tracker.lease=lease
    return SectionContinuation(token,lease,next_guide(r),owner_binding=('section-test',1),
        binding_reader=lambda:('section-test',f.generation),generation_reader=lambda:f.generation,
        fit_library=importlib.import_module('navigation'),steering_library=legacy,
        pump=lambda:None,command_state_clear=lambda:True)


def simulate(f,c,monkeypatch,*,stop=None):
    import eql_automation.camp_probe_runtime as probes
    import eql_automation.camp_source_runtime as route
    from eql_automation.source_motion import SourceReceiptLedger
    from dataclasses import asdict
    import json
    original_geometry=SourceReceiptLedger._geometry
    def geometry(ledger,chain,kind,footprint):
        try:return original_geometry(ledger,chain,kind,footprint)
        except ValueError as error:
            error.add_note('Synthetic geometry diagnostic: '+json.dumps(dict(
                kind=kind,reference=ledger.reference.package_xyz,heading=ledger.pose.heading,
                footprint=footprint,previous=[tuple(map(str,p)) for p in chain._expanded],
                selected=list(chain._selected),
                sources=[asdict(s) for s in ledger.terrain.source_faces_for_footprint(footprint)])))
            raise
    monkeypatch.setattr(SourceReceiptLedger,'_geometry',geometry)
    at=c.floor._reference.package_xyz
    state=SimpleNamespace(x=at[0],y=at[1],heading=0.,receipts=[],stopped=False)
    def movement(receipt):
        seconds=(receipt.maximum_held_seconds+receipt.up_started_at-receipt.down_completed_at)/2
        if receipt.key_code==103:
            state.x+=math.sin(math.radians(state.heading))*10.*seconds
            state.y+=math.cos(math.radians(state.heading))*10.*seconds
        else:state.heading=(state.heading+(1 if receipt.key_code==106 else -1)*170.*max(0.,seconds-.03))%360
        state.receipts.append(receipt)
    original_probe=probes.send_camp_probe
    def probe(*a,**kw):
        sent=original_probe(*a,**kw);movement(sent.seal.receipt);return sent
    monkeypatch.setattr(probes,'send_camp_probe',probe)
    original_source=route.run_checked_source_step
    def walk(*a,**kw):
        sent=original_source(*a,**kw);movement(sent.receipt);return sent
    monkeypatch.setattr(route,'run_checked_source_step',walk)
    def down():
        key=c.current_input_key()
        if stop==c.phase and key in (103,105,106):
            state.stopped=True;c.cancel('F9 at section '+stop);return
        if key==62:
            f.now=f.clock()
            f.append(f'Your Location is {state.y:.2f}, {state.x:.2f}, 2.7')
    after_down(monkeypatch,down)
    return state


def finish_section(f,c,*,timeout=100.):
    deadline=time.monotonic()+timeout
    while c.phase not in ('complete','stopped') and time.monotonic()<deadline:
        f.now=f.clock()
        try:c.tick()
        except Exception as error:
            r=c.runtime;start=None if r is None else r.start
            error.add_note('Section diagnostic: phase='+str(c.phase)+'; probe_index='+str(None if r is None else r.index)
                +'; start_age='+str(None if start is None else f.clock()-start.height.second.received_monotonic)
                +'; latest_seq='+str(c.reader.log_line_seq)
                +'; start_seq='+str(None if start is None else start.height.second.log_line_seq))
            raise
        f.drain_events();time.sleep(.01)
    assert c.phase in ('complete','stopped'),c.snapshot()


@pytest.mark.parametrize('f',['section_continuation'],indirect=True)
def test_stopped_section_runs_new_standard_probes_and_onward_walk_without_camp(f,tmp_path,monkeypatch,retained,legacy):
    r,e,b=prepare(f,tmp_path,monkeypatch)
    initial_count=b.snapshot()['reserved_pulses'];deadline=b.expires_at
    token=capture_section_arrival(r,b)
    c=continuation(f,r,b,token,retained,legacy);state=simulate(f,c,monkeypatch)
    finish_section(f,c)
    assert c.phase=='complete',c.snapshot()
    assert c.completed_arrival.checkpoint._reader is r.reader
    assert c.completed_arrival.runtime is c.route_runtime
    assert len(c.runtime.results)==7 and len(state.receipts)>7
    assert b.snapshot()['reserved_pulses']==initial_count+len(state.receipts)
    assert b.expires_at==deadline
    assert c.runtime.owner_input is r.owner_input and c.runtime.sender is r.sender
    assert c.runtime.log_veto is r.policy.log_veto and c.route_runtime.policy.journey_budget is b
    assert c.route_runtime.plan.motion.run_speed==c.calibration['estimate']['estimate']['run_speed']
    assert c.route_runtime.plan.heading==c.calibration['estimate']['estimate']['final_heading']
    assert not c.snapshot()['camp_started'] and not c.snapshot()['real_client_accepted']
    c.release();assert not f.sender.held and c.lease._tracker.lease is None
    reached=c.completed_arrival
    c.cancel('late callback from retired section')
    assert b.valid and reached.checkpoint.valid and c.completed_arrival is reached


@pytest.mark.parametrize('f',['section_continuation'],indirect=True)
@pytest.mark.parametrize('fault',('cancelled_parent','unfinished','not_terminal','duplicate_capture'))
def test_bad_completed_section_cannot_be_rearmed(f,tmp_path,monkeypatch,fault):
    r,e,b=prepare(f,tmp_path,monkeypatch)
    if fault=='cancelled_parent':b.cancel('parent cancelled')
    elif fault=='unfinished':r.sender.unfinished=True
    elif fault=='not_terminal':r.phase='ready'
    else:capture_section_arrival(r,b)
    before=f.drain_events()
    with pytest.raises((ValueError,RuntimeError)):capture_section_arrival(r,b)
    assert f.drain_events()==before


@pytest.mark.parametrize('f',['section_continuation'],indirect=True)
@pytest.mark.parametrize('phase',('probe','route'))
def test_stop_during_continuation_down_releases_without_another_handoff(f,tmp_path,monkeypatch,retained,legacy,phase):
    r,e,b=prepare(f,tmp_path,monkeypatch);token=capture_section_arrival(r,b)
    c=continuation(f,r,b,token,retained,legacy);state=simulate(f,c,monkeypatch,stop=phase)
    with pytest.raises((ValueError,RuntimeError)):finish_section(f,c)
    assert state.stopped and c.phase=='stopped' and c.completed_arrival is None
    assert not b.valid and not f.sender.held
    c.release();assert c.lease._tracker.lease is None
    before=f.drain_events();c.tick();assert f.drain_events()==before


@pytest.mark.parametrize('f',['section_continuation'],indirect=True)
def test_failed_constructor_releases_its_claimed_lease_and_observer(f,tmp_path,monkeypatch,retained,legacy):
    r,e,b=prepare(f,tmp_path,monkeypatch);token=capture_section_arrival(r,b)
    r.lease.release();tracker=r.lease._tracker;lease=ZoneReaderLease(tracker);tracker.lease=lease
    closed=[];r.owner_input.close=lambda:closed.append(True)
    with pytest.raises(ValueError):
        SectionContinuation(token,lease,next_guide(r),owner_binding=('section-test',1),
            binding_reader=lambda:('changed',1),generation_reader=lambda:1,
            fit_library=importlib.import_module('navigation'),steering_library=legacy,
            pump=lambda:None,command_state_clear=lambda:True)
    assert token._claim==[True] and not b.valid
    assert tracker.lease is None and not lease.active and closed==[True]


@pytest.mark.parametrize('f',['section_continuation'],indirect=True)
@pytest.mark.parametrize('field',('device','monitor','window'))
def test_changed_device_or_monitor_cannot_be_adopted_before_next_input(f,tmp_path,monkeypatch,retained,legacy,field):
    r,e,b=prepare(f,tmp_path,monkeypatch);token=capture_section_arrival(r,b)
    c=continuation(f,r,b,token,retained,legacy)
    if field=='device':c.sender.ui=SimpleNamespace(fileno=lambda:c.fd)
    elif field=='monitor':c.monitor=copy(c.monitor)
    else:c.window=replace(c.window,window_id=43)
    before=f.drain_events()
    with pytest.raises((ValueError,RuntimeError)):c.tick()
    assert f.drain_events()==before and not b.valid and c.phase=='stopped'
    c.sender.ui=c.ui;c.release()


@pytest.mark.parametrize('f',['section_continuation'],indirect=True)
def test_stop_inside_final_capture_discards_the_new_checkpoint(f,tmp_path,monkeypatch,retained,legacy):
    import eql_automation.section_continuation as module
    r,e,b=prepare(f,tmp_path,monkeypatch);token=capture_section_arrival(r,b)
    c=continuation(f,r,b,token,retained,legacy);simulate(f,c,monkeypatch)
    original=module.capture_section_arrival;seen=[]
    def stopped(runtime,budget):
        value=original(runtime,budget);seen.append(value)
        c.cancel('F9 during completed-section capture')
        return value
    monkeypatch.setattr(module,'capture_section_arrival',stopped)
    with pytest.raises((ValueError,RuntimeError)):finish_section(f,c)
    assert len(seen)==1 and not seen[0].checkpoint.valid
    assert c.completed_arrival is None and not b.valid and not f.sender.held
    c.release()


@pytest.mark.parametrize('f',['section_reserve_block'],indirect=True)
def test_whole_sequence_reserve_is_checked_before_first_probe(f,tmp_path,monkeypatch,retained,legacy):
    r,e,b=prepare(f,tmp_path,monkeypatch);token=capture_section_arrival(r,b)
    c=continuation(f,r,b,token,retained,legacy);state=simulate(f,c,monkeypatch)
    count=b.snapshot()['reserved_pulses']
    with pytest.raises(ValueError,match='other_source_surface_intersects_body_band'):
        finish_section(f,c)
    assert not state.receipts and c.runtime is None and b.snapshot()['reserved_pulses']==count
    assert not f.sender.held
    c.release()


@pytest.mark.parametrize('f',['section_continuation'],indirect=True)
@pytest.mark.parametrize('field',('position','bounds','basis','reserve'))
def test_checked_whole_reserve_cannot_change_during_fresh_confirmation(f,tmp_path,monkeypatch,retained,legacy,field):
    r,e,b=prepare(f,tmp_path,monkeypatch);token=capture_section_arrival(r,b)
    c=continuation(f,r,b,token,retained,legacy);state=simulate(f,c,monkeypatch)
    deadline=time.monotonic()+15.
    while c.phase=='collect_position' and time.monotonic()<deadline:
        f.now=f.clock();c.tick();f.drain_events();time.sleep(.01)
    assert c.phase=='confirm_reserve'
    count=b.snapshot()['reserved_pulses']
    if field=='position':c.reserve_position=(c.reserve_position[0]+1.,*c.reserve_position[1:])
    elif field=='bounds':c.bounds=replace(c.bounds)
    elif field=='basis':c.bounds_basis=b'changed'
    else:c.reserve=b'{}'
    with pytest.raises(ValueError,match='whole-probe reserve changed'):c.tick()
    assert not state.receipts and c.runtime is None and b.snapshot()['reserved_pulses']==count
    assert not f.sender.held and not b.valid
    c.release()
