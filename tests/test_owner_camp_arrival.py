"""Focused camp replacement with a genuine floor and synthetic arrival token.

These checks exercise the retained engine but do not claim route execution.
The separate standard-route test owns the complete watchdog/pipe path.
"""
from types import SimpleNamespace

import pytest

from eql_automation.camp_floor_checkpoint import CampFloorCheckpoint
from eql_automation.camp_motion_continuity import camp_route_motion_basis
from eql_automation.native_region_policy import encoded
from eql_automation.owner_camp_arrival import CampArrival,CampDestination,continue_camp_arrival,check_camp_arrival
from eql_automation.owner_input_observer import OwnerInputObservation
from eql_automation.owner_route_trial import zone_binding
from eql_automation.scene_log_veto import SceneLogVeto
from eql_automation.source_walk_driver import SourceWalkFinished
from test_owner_camp_position import camp
from test_camp_floor_checkpoint import checkpoint
from test_source_motion import f
from test_route_floor_commit import legacy
from test_motion_collection import retained
from test_owner_journey_runtime import h


@pytest.fixture
def arrival(h,checkpoint,monkeypatch):
    f=checkpoint;reached=CampFloorCheckpoint(f.ledger)
    receipt=SourceWalkFinished(f.ledger.observer.itinerary.sha256,f.ledger.reference)
    runtime=SimpleNamespace(phase='complete',completed_arrival=receipt,ledger=f.ledger)
    return make_arrival(h,f,monkeypatch,reached,runtime,receipt)


def make_arrival(h,f,monkeypatch,reached,runtime,receipt):
    camp.__wrapped__(h,f,monkeypatch)
    e=h.engine;j=e.journey;old=e.camp_session
    h.now=f.now;clock=lambda:h.now
    j.continue_camps=j._continue_camps=True
    observer=j.camp_motion.observer
    observer.sample=lambda:OwnerInputObservation(h.now,h.now,1,True,1,0,False,0,'synthetic arrival')
    plan_motion=f.ledger.motion
    calibration=dict(status='conditional',estimate=dict(record_id='synthetic-fresh-fit',
        estimate={k:getattr(plan_motion,k) for k in ('run_speed','turn_rate','right_sign','turn_latency')}))
    basis=camp_route_motion_basis(runtime,calibration,reached)
    p=SimpleNamespace(journey=j,camp=old,monitor=j.camp_motion,floor=j.arrival_floor,
        hotkey=j.location_binding,tracker=e.live_zone_tracker,reader=f.reader,
        lease=SimpleNamespace(active=False),runtime=SimpleNamespace(closed=True),
        route_runtime=runtime,_route_runtime=runtime,generation=e.cancel_generation,
        sender=e.sender,ui=e.sender.ui,gate=e.gate,window=(42,10,100),cancelled=False,
        probe_log_veto=SceneLogVeto(h.log,expected_character=e.settings.character,
            expected_server=e.settings.server,cancel_generation=e.cancel_generation,clock=clock))
    destination=CampDestination('north-wall',encoded({'destination_id':'north-wall'}))
    token=CampArrival(p,runtime,receipt,reached,destination,basis,j.settings,
        zone_binding(f.reader),old.candidates)
    j.phase='handoff';j.destination_id='north-wall';j.destination_assets=destination
    j.arrival_floor=reached;j.candidates=token.candidates
    old.phase='probe_measurement';e.active=False;e.target_ready=False
    h.arrival=token;h.arrival_clock=clock
    return h


def test_arrival_replaces_camp_then_prepares_without_reusing_target_or_moving(arrival):
    h=arrival;e=h.engine;t=h.arrival;p=t.pending;old=p.camp;generation=e.cancel_generation
    result=continue_camp_arrival(e,t,h.arrival_clock)
    assert result['camp_started'] and result['fresh_preparation_due']
    assert e.camp_session is not old and not old.running and e.cancel_generation==generation+1
    assert e.camp_session.preparation_due and e.camp_session.requested is None
    assert e.journey.destination_id=='north-wall' and e.journey.phase=='camp'
    assert not e.journey.height_check_done and e.journey.last_considered_level_advance is None
    assert e.journey.camp_motion.observer is p.monitor.observer
    assert p.monitor.closed and not p.monitor.valid and not p.floor.valid
    assert e.journey.arrival_floor is t.checkpoint and t.checkpoint.valid
    assert not h.commands and not h.events and not h.observer_closed
    # A late close of the retired wrapper must not close its successor's device.
    p.monitor.close('late ancestor cleanup');assert not h.observer_closed
    h.tick();assert e.camp_session.phase=='preparing' and not h.commands
    e.stop_action('F9');assert h.observer_closed and not t.checkpoint.valid


@pytest.mark.parametrize('fault',('expired','destination','input','lease','settings','queued','observer_regression'))
def test_changed_arrival_cannot_start_a_new_camp(arrival,fault):
    h=arrival;e=h.engine;t=h.arrival;p=t.pending
    if fault=='expired':h.now=t.receipt.reference.raw_fix.received_monotonic+.501
    elif fault=='destination':e.journey.destination_id='slave-mines'
    elif fault=='input':p.monitor.observer.sample=lambda:OwnerInputObservation(h.now,h.now,1,True,1,1,False,0,'owner key')
    elif fault=='lease':p.tracker.lease=object()
    elif fault=='settings':e.settings.level+=1
    elif fault=='queued':e.jobs.put(('arm',e.cancel_generation))
    else:p.monitor.last_observed_at=h.now+.01
    with pytest.raises(ValueError):check_camp_arrival(e,t,h.arrival_clock)
    assert e.camp_session is p.camp and not h.commands and not h.events
    if fault=='lease':p.tracker.lease=None


@pytest.mark.parametrize('where',('gauges','start_stop','input_transfer','handoff_trace'))
@pytest.mark.parametrize('mode',('F8','F9'))
def test_owner_cancel_during_new_camp_setup_never_resumes_combat(arrival,where,mode):
    h=arrival;e=h.engine;t=h.arrival;fired=[]
    def stop():
        if fired:return
        fired.append(True)
        if mode=='F8':e.handle_job('arm',e.cancel_generation)
        else:e.stop_action('F9 during next camp setup')
    if where=='gauges':
        original=e.gate.read_gauges
        def gauges(*args):stop();return original(*args)
        e.gate.read_gauges=gauges
    elif where=='start_stop':
        original=e.emit
        def notice(text=None):
            if text and 'Camp starting' in text:stop()
            return original(text)
        e.emit=notice
    elif where=='input_transfer':
        original=e._camp_motion_binding
        def binding():
            result=original()
            if e.camp_session is not t.pending.camp:stop()
            return result
        e._camp_motion_binding=binding
    else:
        original=e.trace
        def trace(event,**kwargs):
            original(event,**kwargs)
            if event=='journey_next_camp_handoff':stop()
        e.trace=trace
    result=None
    try:result=continue_camp_arrival(e,t,h.arrival_clock)
    except ValueError:pass
    assert fired and e.journey is None and e.camp_session is None
    assert not e.active and not h.commands and not h.events
    assert h.observer_closed and not t.checkpoint.valid
    if result is not None:assert not result['camp_started']
    if mode=='F8':assert e._journey_assist is not None


def test_callback_cannot_replace_the_old_camp_before_controlled_stop(arrival):
    h=arrival;e=h.engine;t=h.arrival;old=t.pending.camp
    ready=e.gate.controls_ready;foreign=SimpleNamespace(running=True)
    def replace():
        e.camp_session=e.autopilot=foreign
        return ready()
    e.gate.controls_ready=replace
    with pytest.raises(ValueError):continue_camp_arrival(e,t,h.arrival_clock)
    assert e.camp_session is foreign and old.running and not h.commands and not h.events
    e.gate.controls_ready=ready;e.camp_session=e.autopilot=old


def test_new_camp_trace_cannot_replace_the_created_session(arrival):
    from copy import copy
    h=arrival;e=h.engine;t=h.arrival;trace=e.trace;replaced=[]
    def change(event,**kwargs):
        trace(event,**kwargs)
        if event=='camp_start':
            replaced.append(e.camp_session)
            e.camp_session=e.autopilot=copy(e.camp_session)
    e.trace=change
    result=continue_camp_arrival(e,t,h.arrival_clock)
    assert replaced and not result['camp_started']
    assert e.journey is None and e.camp_session is None
    assert not h.commands and not h.events and h.observer_closed
