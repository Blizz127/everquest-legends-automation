"""Actual checked sender/watchdog on pipes; all game observations synthetic."""
from datetime import datetime,timedelta
import os
from types import SimpleNamespace
import time

import pytest

from eql_automation.crossing_pulse import CrossingPulseHandoff
from eql_automation.g2_safety_provider import GameWindowIdentity
from eql_automation.motion_collection import CommandReceipt,LocationRequest
from eql_automation.owner_input_observer import OwnerInputObservation
from eql_automation.owner_zone_tracker import LiveZoneTracker
from eql_automation.route_step_sender import (RouteStepScene,run_checked_crossing_step,
    run_checked_route_step)
from eql_automation.supervised_crossing import SupervisedCrossingDeclaration,SupervisedCrossingPolicy
from eql_automation.uinput_watchdog import _EVENT
from test_route_floor_commit import legacy
from test_route_step_sender import PipeSender,after_down
from test_zone_line import prepare_crossing


@pytest.fixture
def h(tmp_path,legacy):
    clock_state={'offset':0.}
    clock=lambda:time.monotonic()+clock_state['offset']
    h,line=prepare_crossing(legacy,clock=clock)
    h.clock_state=clock_state;h.ready=False;h.cancelled=False;h.focus=True
    h.log=tmp_path/'eqlog_Probe_private.txt';h.log.touch()
    catalog=tmp_path/'ZoneNames.txt';catalog.write_text('54^Fixture^0^0\n58^Clan Crushbone^0^0\n')
    h.wall=lambda:datetime.now()+timedelta(seconds=clock_state['offset'])
    def append(body):
        with h.log.open('a') as out:out.write(h.wall().strftime('[%a %b %d %H:%M:%S %Y] ')+body+'\n')
    h.append=append
    tracker=LiveZoneTracker(h.log,catalog,expected_character='Probe',expected_server='private',
        binding_reader=lambda:('synthetic-owner',42,10,100),clock=clock)
    append('You have entered Fixture.');tracker.poll()
    # The synthetic accepted source fixture has historical epoch1/sequence2.
    # A new hazard tail has its own epoch0; counters must not be conflated.
    tracker.reader.tail.epoch=1;tracker.reader.log_line_seq=2
    tracker.reader.latest=h.reference.raw_fix
    h.lease=tracker.acquire()
    h.rd,h.wr=os.pipe();h.sender=PipeSender(h.wr)
    def current():
        if h.cancelled or not h.focus:raise ValueError('Owner cancelled or focus changed')
    h.current=current
    def release():
        began=clock()
        for key in tuple(h.sender.held):h.sender.release(key)
        return CommandReceipt(began,clock())
    h.crossing=CrossingPulseHandoff(h.prepare,h.lease,'Clan Crushbone',release_controls=release,
        ready_for_location=lambda:h.ready,check_current=current,local_wall_clock=h.wall)
    window=SimpleNamespace(id=42)
    gate=SimpleNamespace(windows=lambda:[window],focused_window=lambda:window if h.focus else None,
        game_session=lambda:{'pid':10,'start_ticks':'100'},controls_ready=lambda:h.focus)
    def sample():
        now=clock()
        return OwnerInputObservation(now,now,1,True,1,0,False,0,'synthetic-device')
    declaration=SupervisedCrossingDeclaration(line.crossing_id,h.runner.route.artifact_sha256,
        h.runner.calibration,h.prepare.bounds.record_id,True,15.,1,10.,.2,
        scope='zone_crossing',expected_zone_line_sha256=line.sha256,destination='Clan Crushbone')
    h.policy=SupervisedCrossingPolicy(h.prepare,declaration=declaration,gate=gate,
        owner_input=SimpleNamespace(sample=sample),log_veto=h.crossing.arrival.veto,
        expected_log_path=h.log,expected_window=GameWindowIdentity(42,10,100),
        topology_generation=1,check_current=current)
    h.scene=lambda:RouteStepScene(h.reference,h.policy.observe(h.reference))
    h.run=lambda:run_checked_crossing_step(h.sender,h.crossing,policy=h.policy,
        scene_provider=h.scene,command_state_clear=lambda:True,pump=lambda:None)
    yield h
    h.lease.release();tracker.close()
    os.close(h.wr);data=b''
    while chunk:=os.read(h.rd,4096):data+=chunk
    os.close(h.rd)
    h.events=[(kind,key,value) for _,_,kind,key,value in _EVENT.iter_unpack(data)]
    assert not h.sender.held
    assert h.runner.steps==0 and h.ledger.chain is h.chain and h.chain.index==1
    if (1,103,1) in h.events:assert h.events[-2:]==[(1,103,0),(0,0,0)]


def send_pair(h):
    h.ready=True;h.clock_state['offset']+=.2
    for index in range(2):
        request=h.crossing.tick();assert isinstance(request,LocationRequest)
        began=h.clock();h.clock_state['offset']+=.01
        h.crossing.command_sent(request,CommandReceipt(began,h.clock()))
        h.append('Your Location is -12, 34, 5');assert h.crossing.tick() is None
        if index==0:h.clock_state['offset']+=.41
    assert h.crossing.phase=='complete'
    assert h.crossing.arrival.collector.second.zone_id==58


def test_loading_during_actual_down_releases_then_collects_new_zone(h,monkeypatch):
    after_down(monkeypatch,lambda:h.append('LOADING, PLEASE WAIT...'))
    result=h.run()
    assert result.loading_observed and not result.source_floor_committed
    assert result.receipt.completion in ('interrupted','elapsed')
    assert h.runner.phase=='halted' and h.ledger._pending is None
    h.append('You have entered Clan Crushbone.');assert h.crossing.tick() is None
    send_pair(h)
    record=h.crossing.snapshot()
    assert not record['source_navigation_state_reused'] and not record['real_client_accepted']


def test_elapsed_pulse_waits_stopped_for_delayed_loading_without_floor_commit(h):
    result=h.run();assert not result.loading_observed and result.receipt.completion=='elapsed'
    assert h.crossing.tick() is None and h.runner.phase=='halted'
    h.append('LOADING, PLEASE WAIT...');h.crossing.tick()
    h.append('You have entered Clan Crushbone.');h.crossing.tick()
    send_pair(h)


@pytest.mark.parametrize('late_loading',[False,True])
def test_no_loading_times_out_without_another_pulse_or_position(h,late_loading):
    h.run();h.clock_state['offset']+=2.6
    if late_loading:h.append('LOADING, PLEASE WAIT...')
    with pytest.raises(ValueError,match='No loading'):h.crossing.tick()
    assert h.crossing.phase=='stopped' and h.crossing.arrival.collector is None


@pytest.mark.parametrize('cause',['owner','policy','mode','lease','hazard','wrong_zone','release_failure'])
def test_cancellation_or_other_failure_during_down_never_transfers_to_arrival(h,monkeypatch,cause):
    def fail():
        if cause=='owner':h.cancelled=True
        elif cause=='policy':
            h.policy.cancel('F9 revokes crossing policy');h.append('LOADING, PLEASE WAIT...')
        elif cause=='mode':h.state['mode']='assist'
        elif cause=='lease':h.lease.release()
        elif cause=='hazard':
            h.append('LOADING, PLEASE WAIT...');h.append('a bat hits YOU for 3 points of damage.')
        elif cause=='wrong_zone':
            h.append('LOADING, PLEASE WAIT...');h.append('You have entered Wrong Zone.')
        else:
            h.append('LOADING, PLEASE WAIT...')
            original=h.sender.release
            def release(key):original(key);raise OSError('synthetic release acknowledgment failure')
            h.sender.release=release
    after_down(monkeypatch,fail)
    with pytest.raises((RuntimeError,ValueError,OSError)):h.run()
    assert h.crossing.phase=='stopped' and h.crossing.arrival.collector is None


def test_loading_before_down_cannot_claim_a_crossing_pulse(h):
    h.append('LOADING, PLEASE WAIT...')
    with pytest.raises((RuntimeError,ValueError)):h.run()
    assert h.crossing.receipt is None and h.crossing.phase=='stopped'


def test_ordinary_route_sender_rejects_crossing_policy(h):
    with pytest.raises(ValueError,match='typed policy'):
        run_checked_route_step(h.sender,h.ledger,scene_provider=h.scene,prepare_step=h.prepare,
            authorize_step=h.policy.authorize,still_authorized=h.policy.still_authorized,
            command_state_clear=lambda:True,pump=lambda:None,supervised_policy=h.policy)


def test_invalid_position_after_loading_cannot_be_reported_as_arrival(h,monkeypatch):
    def malformed():
        h.append('LOADING, PLEASE WAIT...');h.append('Your Location is malformed')
    after_down(monkeypatch,malformed)
    with pytest.raises((ValueError,RuntimeError)):h.run()
    assert h.crossing.phase=='stopped' and h.crossing.arrival.phase=='stopped'


def test_cancel_in_final_receipt_clock_cannot_resurrect_arrival(h,monkeypatch):
    after_down(monkeypatch,lambda:h.append('LOADING, PLEASE WAIT...'))
    original=h.crossing.released
    def finish(receipt):
        old_clock=h.crossing.clock;calls=0
        def clock():
            nonlocal calls
            calls+=1
            if calls==2:h.crossing.cancel('F9 at final receipt commit')
            return old_clock()
        h.crossing.clock=clock
        try:return original(receipt)
        finally:h.crossing.clock=old_clock
    h.crossing.released=finish
    with pytest.raises(ValueError,match='cancelled'):h.run()
    assert h.crossing.phase=='stopped' and h.crossing.receipt is None


def test_generation_callback_cancellation_is_rechecked_after_callback(h):
    def generation():
        h.crossing.cancel('F9 during generation callback')
        return h.state['generation']
    h.runner.generation_reader=generation
    with pytest.raises(ValueError,match='cancelled'):h.crossing._current()
    assert h.crossing.phase=='stopped'
