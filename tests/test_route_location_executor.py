"""Retained command sender, route loop and engine ticks, with pipe-only I/O."""
from dataclasses import replace
import os
from pathlib import Path
import re
import time
from types import SimpleNamespace

import pytest

from eql_automation.command_submission import LOCATION_KEYS
from eql_automation.motion_collection import CollectionStopped
from eql_automation.motion_executors import MeasurementInputEvidence,_Scope
from eql_automation.route_location_executor import RouteLocationExecutor
from eql_automation.uinput_watchdog import _EVENT
from test_motion_collection import retained
from test_motion_executors import PipeUI
from test_route_floor_commit import legacy
from test_owner_route_adapter import setup as route_setup


def setup(tmp_path,retained,legacy):
    h=route_setup(tmp_path,retained,legacy,real=True)
    import rotation_engine
    codes={name:int(value) for name,value in re.findall(
        r'^#define\s+(KEY_\w+|EV_KEY)\s+(\d+)\b',
        Path('/usr/include/linux/input-event-codes.h').read_text(),re.M)}
    codes['EV_KEY']=1
    sender=rotation_engine.KeySender.__new__(rotation_engine.KeySender)
    sender.codes=SimpleNamespace(**codes);sender.ui=PipeUI(h.wr)
    sender.held=set();sender.unfinished=sender.dismissed=False
    h.focus=True;h.chat=False;h.draft='';h.submissions=[];h.guard_hook=lambda *args:None
    sender.gate=SimpleNamespace(controls_ready=lambda:h.focus)
    sender.allowed=h.engine.allowed
    h.sender=h.engine.sender=h.driver.sender=sender
    h.engine.input_events=h.engine.read_log=lambda:None
    h.engine.blocked_keys=lambda:False
    os.set_blocking(h.rd,False)
    def drain():
        try:data=os.read(h.rd,65536)
        except BlockingIOError:return
        assert len(data)%_EVENT.size==0
        for event in (row[2:] for row in _EVENT.iter_unpack(data)):
            h.events.append(event)
            if event==(1,53,1):h.chat=True;h.draft='/'
            elif event==(1,28,1):h.chat=False;h.draft=''
            elif event[0]==1 and event[2]==1 and h.chat:
                h.draft+={38:'l',24:'o',46:'c',30:'a',20:'t',23:'i',49:'n'}.get(event[1],'?')
    h.drain=drain
    def guard(request,phase,submission):
        drain();h.submissions.append(submission)
        if phase=='command_key':assert h.chat and submission.submitted_prefix==h.draft
        else:assert not h.chat
        h.guard_hook(request,phase)
        now=h.clock()
        return MeasurementInputEvidence(request,phase,now,now+.1,'synthetic-route-command-scene',submission)
    h.executor=RouteLocationExecutor(h.engine,h.session,check_input=guard)
    def location(request):
        receipt=h.executor.request_location(request)
        h.commands.append(request)
        x,y,z=h.point
        h.append('Your Location is %.2f, %.2f, %.2f'%(y,x,z+2.1))
        return receipt
    h.driver.request_location=location
    def first_command():
        time.sleep(max(0,h.session.due-h.clock())+.001)
        request=h.session.tick();h.driver.busy=True
        try:return h.executor.request_location(request)
        finally:h.driver.busy=False;drain()
    h.first_command=first_command
    old_close=h.close
    def close():
        drain();events=list(h.events);os.set_blocking(h.rd,True)
        old_close();h.events=events+h.events
    h.close=close
    return h


@pytest.fixture
def h(tmp_path,retained,legacy):
    h=setup(tmp_path,retained,legacy)
    yield h
    h.close()


def test_route_command_reuses_actual_retained_keys_and_exact_prefixes(h):
    receipt=h.first_command()
    assert receipt.completed_at>=receipt.started_at
    assert [code for kind,code,value in h.events if kind==1 and value==1]==list(LOCATION_KEYS)
    assert len(h.events)==40 and not h.sender.held and not h.sender.unfinished
    assert not hasattr(h.executor,'run_pulse')
    assert [s.submitted_prefix for s in h.submissions]==['','']+['/location'[:i] for i in range(1,10)]+['/location']
    assert len({s.operation_id for s in h.submissions})==1
    assert h.submissions[-1].enter_submitted and not h.submissions[-1].client_delivery_verified
    record=h.session.snapshot()['executor_events'][-1]
    assert record['operation']=='location' and record['pending_releases']==[]
    assert record['command_submission']['submitted_prefix']=='/location'


@pytest.mark.parametrize('change',['assist','engine_assist','recovery','draft','held','driver_missing','wrong_sender','busy'])
def test_route_binding_refuses_before_any_down(h,change):
    if change=='assist':h.mode='assist'
    elif change=='engine_assist':h.engine.measurement_only=False
    elif change=='recovery':h.engine.command_recovery_pending=True
    elif change=='draft':h.sender.unfinished=True
    elif change=='held':h.sender.held.add(103)
    elif change=='driver_missing':h.engine.route_session_driver=None
    elif change=='wrong_sender':h.driver.sender=object()
    elif change=='busy':
        original=h.executor._bound_driver
        def idle():h.driver.busy=False;return original()
        h.executor._bound_driver=idle
    with pytest.raises(RuntimeError):h.first_command()
    assert not h.events


@pytest.mark.parametrize('phase',['command_start','command_first_key','command_key','command_end'])
def test_actual_helper_stop_at_command_boundary_keeps_partial_journal(h,phase):
    def stop(request,current):
        if current==phase:h.engine.stop_action('owner F9 at '+phase)
    h.guard_hook=stop
    with pytest.raises(RuntimeError):h.first_command()
    assert not h.sender.held and h.session.phase=='stopped'
    assert not any(event==(1,1,1) for event in h.events)
    assert h.sender.unfinished==(phase in ('command_key','command_end'))
    event=h.session.executor_events[-1]
    assert event['error'] is not None and not event['pending_releases']
    assert event['command_submission']['client_delivery_verified'] is False


def test_driver_replacement_during_command_is_not_adopted(h):
    from copy import copy
    h.guard_hook=lambda *args:setattr(h.engine,'route_session_driver',copy(h.driver))
    with pytest.raises(CollectionStopped,match='binding changed'):h.first_command()
    assert not h.events


def test_copied_submission_cannot_authorize_route_key(h):
    original=h.executor.check_input
    def changed(request,phase,submission):
        evidence=original(request,phase,submission)
        return replace(evidence,submission=replace(submission))
    h.executor.check_input=changed
    with pytest.raises(CollectionStopped,match='evidence'):h.first_command()
    assert not h.events


def test_route_failed_up_retries_original_descriptor_and_latches_draft(h,monkeypatch):
    rd,wr=os.pipe();original=_Scope.raw_write_event;failed=[]
    def write(scope,kind,code,value):
        if (kind,code,value)==(1,53,0) and not failed:
            failed.append(True);h.sender.ui=PipeUI(wr);h.sender.held.clear()
            raise OSError('original UP failed')
        return original(scope,kind,code,value)
    monkeypatch.setattr(_Scope,'raw_write_event',write)
    try:
        with pytest.raises(OSError,match='UP failed'):h.first_command()
        assert h.events==[(1,53,1),(0,0,0),(1,53,0),(0,0,0)]
        assert h.sender.unfinished and not h.session.executor_events[-1]['pending_releases']
        assert h.session.executor_events[-1]['command_submission']['uncertain']
        os.set_blocking(rd,False)
        with pytest.raises(BlockingIOError):os.read(rd,4096)
    finally:os.close(rd);os.close(wr)


def test_complete_route_uses_retained_commands_and_watchdog_without_game_input(h):
    deadline=time.monotonic()+30
    while h.engine.route_session_driver is not None and time.monotonic()<deadline:
        h.tick();h.drain()
    record=h.engine.last_route_session_result
    assert record is not None and record['outcome']=='arrived',record
    assert record['segment_index']==2 and len(record['steps'])>=2
    assert len(record['command_requests'])==2*(len(record['steps'])+1)
    commands=[e for e in record['executor_events'] if e['kind']=='executor_result']
    assert len(commands)==len(record['command_requests'])
    assert all(e['error'] is None and e['cleanup_error'] is None and not e['pending_releases'] for e in commands)
    assert all(e['command_submission']['enter_submitted'] and not e['command_submission']['uncertain'] for e in commands)
    downs=[code for kind,code,value in h.events if kind==1 and value==1]
    assert downs.count(103)==len(record['steps'])
    assert downs.count(53)==len(record['command_requests'])
    assert len(h.events)==40*len(record['command_requests'])+8*len(record['steps'])
    assert not h.sender.held and not h.sender.unfinished and not record['real_client_accepted']


@pytest.mark.parametrize('fault', [None, 'draft', 'attack', 'owner', 'unknown'])
def test_retained_command_uses_phase_provider_with_independent_veto_tail(h, fault):
    from eql_automation.command_input_provider import CommandInputProvider, CommandUiObservation
    from eql_automation.g2_safety_provider import G2SafetyProvider
    from eql_automation.g2_scene_observer import G2ObservationUnavailable
    from eql_automation.owner_input_observer import OwnerInputObservation
    from eql_automation.scene_log_veto import SceneLogVeto
    from test_g2_safety_provider import Gate, WINDOW
    active = [False]; observed = []
    def sample():
        started = h.clock()
        return OwnerInputObservation(started, h.clock(), 1, True, 2, 0, active[0], 0, 'synthetic-pipe')
    def ui(window, request, phase, submission):
        began = h.clock(); h.drain()
        observed.append((phase, submission.submitted_prefix))
        if phase == 'command_key' and submission.submitted_key_count == 3:
            if fault == 'draft': h.draft = '/say'
            if fault == 'attack': h.append('Auto attack is on.')
            if fault == 'owner': active[0] = True
            if fault == 'unknown': return {'status': 'pixel_candidates_only'}
        return CommandUiObservation(began, h.clock(), window, 'f'*64, 'c'*64,
            chat_clear=not h.chat, target_absent=True, combat_clear=True,
            no_transition=True, no_incoming_attack=True, request=request, phase=phase,
            submission=submission, input_focused=h.chat, draft_absent=not h.chat,
            visible_prefix=h.draft if h.chat else None, text_complete=h.chat,
            caret_at_end=h.chat, selection_absent=h.chat)
    veto = SceneLogVeto(h.log, expected_character='Probe', expected_server='private',
                       cancel_generation=1, clock=h.clock)
    safety = G2SafetyProvider(gate=Gate(), input_observer=SimpleNamespace(sample=sample),
        ui_observer=lambda _: None, log_veto=veto, expected_log_path=h.log, expected_window=WINDOW,
        calibration_sha256='c'*64, cancel_generation=1, generation_reader=lambda:1,
        mode_reader=lambda:'measurement', clock=h.clock)
    provider = CommandInputProvider(safety, ui_observer=ui)
    h.executor.check_input = provider
    if fault is None:
        h.first_command()
        assert observed == [('command_start',''),('command_first_key',''),
            *[('command_key','/location'[:n]) for n in range(1,10)],
            ('command_end','/location')]
        assert [code for kind,code,value in h.events if kind==1 and value==1] == list(LOCATION_KEYS)
        assert not h.sender.unfinished and provider.last_observation.phase == 'command_end'
    else:
        with pytest.raises(G2ObservationUnavailable): h.first_command()
        assert (1,28,1) not in h.events
        assert h.sender.unfinished and provider.last_observation is None
    assert not h.sender.held and not h.session.executor_events[-1]['pending_releases']
