"""Actual retained command code and watchdog, using pipes and synthetic scenes."""
from dataclasses import replace
import json
import math
import os
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_motion_collection import retained, setup
from eql_automation.motion_collection import CollectionStopped
from eql_automation.motion_executors import MeasurementExecutors, MeasurementInputEvidence, _Scope
from eql_automation.uinput_watchdog import _EVENT


class PipeUI:
    def __init__(self, fd): self.fd = fd
    def fileno(self): return self.fd
    def write(self, kind, code, value): os.write(self.fd, _EVENT.pack(0,0,kind,code,value))
    def syn(self): self.write(0,0,0)


@pytest.fixture
def h(tmp_path, retained):
    h = setup(tmp_path, retained, real=True)
    import rotation_engine
    # Linux constants only; no evdev import or UInput constructor.
    codes = dict((name,int(value)) for name,value in re.findall(
        r'^#define\s+(KEY_\w+|EV_KEY)\s+(0x[\da-fA-F]+|\d+)\b',
        Path('/usr/include/linux/input-event-codes.h').read_text(), re.M)
        if not value.startswith('0x'))
    codes['EV_KEY'] = 1
    h.rd,h.wr = os.pipe(); os.set_blocking(h.rd,False)
    h.events=[]; h.chat=False; h.focus=True; h.guard_hook=lambda request,phase:None
    sender=rotation_engine.KeySender.__new__(rotation_engine.KeySender)
    sender.codes=SimpleNamespace(**codes);sender.ui=PipeUI(h.wr)
    sender.held=set();sender.unfinished=sender.dismissed=False
    sender.gate=SimpleNamespace(controls_ready=lambda:h.focus)
    sender.allowed=h.engine.allowed
    h.sender=h.engine.sender=sender
    h.engine.input_events=h.engine.read_log=lambda:None
    h.engine.blocked_keys=lambda:False
    def drain():
        try: raw=os.read(h.rd,65536)
        except BlockingIOError:return
        assert len(raw)%_EVENT.size==0
        for at in range(0,len(raw),_EVENT.size):
            event=_EVENT.unpack(raw[at:at+_EVENT.size])[2:]
            h.events.append(event)
            if event==(1,53,1):h.chat=True
            if event==(1,28,1):h.chat=False
    h.drain=drain
    def guard(request,phase):
        drain()
        if phase=='command_key':assert h.chat
        else:assert not h.chat
        h.guard_hook(request,phase)
        now=h.clock()
        return MeasurementInputEvidence(request,phase,now,now+.1,'synthetic-scene')
    h.executors=MeasurementExecutors(h.engine,h.session,check_input=guard)
    def location(request):
        receipt=h.executors.request_location(request)
        h.commands.append(request)
        h.append('Your Location is '+', '.join(f'{v:.2f}' for v in h.point))
        return receipt
    def pulse(request):
        released=h.executors.run_pulse(request)
        h.pulses.append(request)
        r=released.receipt
        held=((r.up_started_at-r.down_completed_at)+r.maximum_held_seconds)/2
        if request.probe.key=='forward':
            angle=math.radians(h.heading)
            h.point=(h.point[0]+math.cos(angle)*30*held,h.point[1]+math.sin(angle)*30*held,0.)
        else:h.heading=(h.heading+(-1 if request.probe.key=='right' else 1)*170*max(0,held-.03))%360
        return released
    h.driver.request_location=location;h.driver.run_pulse=pulse
    def first_command():
        request=h.session.tick();h.driver.busy=True
        try:return h.executors.request_location(request)
        finally:h.driver.busy=False;drain()
    h.first_command=first_command
    yield h
    os.close(h.wr);os.close(h.rd)


def test_retained_command_exact_keys_and_receipt(h):
    receipt=h.first_command()
    assert receipt.completed_at>=receipt.started_at
    assert [code for kind,code,value in h.events if kind==1 and value==1]==[53,38,24,46,30,20,23,24,49,28]
    assert len(h.events)==40 and not h.sender.held and not h.sender.unfinished
    assert h.engine.sender is h.sender and h.sender.ui.fileno()==h.wr
    assert h.session.executor_events[-1]['pending_releases']==[]


@pytest.mark.parametrize('change',['draft','dismissed','held','cancelled','assist','recovery','marker'])
def test_existing_uncertainty_refuses_before_down(h,change):
    if change=='draft':h.sender.unfinished=True
    elif change=='dismissed':h.sender.dismissed=True
    elif change=='held':h.sender.held.add(103)
    elif change=='cancelled':h.engine.cancelled=True
    elif change=='assist':h.mode='assist'
    elif change=='recovery':h.engine.command_recovery_pending=True
    else:h.sender._eql_route_operation=object()
    with pytest.raises(CollectionStopped):h.first_command()
    assert not h.events


@pytest.mark.parametrize('phase',['command_start','command_first_key','command_key','command_end'])
def test_cancel_at_command_boundaries_releases_without_escape(h,phase):
    def cancel(request,current):
        if current==phase:h.session.cancel('cancelled at '+phase)
    h.guard_hook=cancel
    with pytest.raises(CollectionStopped):h.first_command()
    assert not h.sender.held
    assert not any(event==(1,1,1) for event in h.events)
    assert h.sender.unfinished==(phase in ('command_key','command_end'))


@pytest.mark.parametrize('field',['held','unfinished','dismissed'])
@pytest.mark.parametrize('phase',['command_end','pulse_end'])
def test_final_callback_cannot_change_sender_state_and_return_success(h,field,phase):
    def dirty(request,current):
        if current==phase:
            if field=='held':h.sender.held.add(42)
            else:setattr(h.sender,field,True)
    h.guard_hook=dirty
    if phase=='command_end':
        with pytest.raises(CollectionStopped,match='end is not clear'):h.first_command()
    else:
        record=h.run()
        assert record['outcome']=='stopped' and 'end is not clear' in record['reason']
        assert not record['receipts']
        assert any(e.get('child_receipt') for e in record['executor_events'])


def test_release_retry_does_not_depend_on_shared_held_bookkeeping(h,monkeypatch):
    rd,wr=os.pipe();replacement=PipeUI(wr)
    original=_Scope.write_event
    failed=[]
    def write(scope,kind,code,value):
        if (kind,code,value)==(1,53,0) and not failed:
            failed.append(True)
            h.sender.ui=replacement
            h.sender.held.clear()  # A concurrent stop used a replacement UI.
            raise OSError('transient original UP failure')
        return original(scope,kind,code,value)
    monkeypatch.setattr(_Scope,'write_event',write)
    try:
        with pytest.raises(OSError,match='transient'):h.first_command()
        assert h.events==[(1,53,1),(0,0,0),(1,53,0),(0,0,0)]
        assert h.sender.unfinished and h.session.executor_events[-1]['pending_releases']==[]
        os.set_blocking(rd,False)
        with pytest.raises(BlockingIOError):os.read(rd,4096)
    finally:os.close(rd);os.close(wr)


def test_first_down_failure_retains_uncertain_draft_and_releases(h,monkeypatch):
    original=_Scope.write_event
    def write(scope,kind,code,value):
        if (kind,code,value)==(1,53,1):raise OSError('DOWN delivery unknown')
        return original(scope,kind,code,value)
    monkeypatch.setattr(_Scope,'write_event',write)
    with pytest.raises(OSError,match='unknown'):h.first_command()
    assert h.sender.unfinished and not h.sender.held
    assert h.events==[(1,53,0),(0,0,0)]


def test_wrong_request_evidence_refuses_before_input(h):
    def wrong(request,phase):
        now=h.clock()
        return MeasurementInputEvidence(replace(request,serial=999),phase,now,now+.1,'wrong')
    h.executors.check_input=wrong
    with pytest.raises(CollectionStopped,match='evidence'):h.first_command()
    assert not h.events


@pytest.mark.parametrize('field',['held','unfinished','dismissed'])
def test_per_key_callback_cannot_change_command_ownership(h,field):
    def dirty(request,phase):
        if phase=='command_key':
            if field=='held':h.sender.held.add(42)
            elif field=='unfinished':h.sender.unfinished=False
            else:h.sender.dismissed=True
    h.guard_hook=dirty
    with pytest.raises(CollectionStopped,match='ownership'):h.first_command()
    assert [e for e in h.events if e[0]==1 and e[2]==1]==[(1,53,1)]


def test_expired_command_stops_after_slash_without_restamping(h):
    def expire(request,phase):
        if phase=='command_key':h.session.clock=lambda:request.expires_at+.01
    h.guard_hook=expire
    with pytest.raises(CollectionStopped):h.first_command()
    assert h.sender.unfinished and not h.sender.held
    assert [e for e in h.events if e[0]==1 and e[2]==1]==[(1,53,1)]


def test_engine_stop_during_real_pulse_releases_and_keeps_partial_evidence(h):
    def stop(request,phase):
        if phase=='pulse_held' and (1,103,1) in h.events:
            h.engine.stop_action('owner F9 during pulse')
    h.guard_hook=stop
    record=h.run();h.drain()
    assert record['outcome']=='stopped' and not record['receipts']
    assert not h.sender.held
    assert [e for e in h.events if e[0]==1 and e[1]==103 and e[2]==1]==[(1,103,1)]
    assert any(e==(1,103,0) for e in h.events)
    pulse=[e for e in record['executor_events'] if e.get('operation')=='pulse']
    assert len(pulse)==1 and not pulse[0]['pending_releases']


def test_full_retained_sender_and_watchdog_collection(h,tmp_path):
    record=h.run();h.drain()
    (tmp_path/'executor-evidence.json').write_text(json.dumps(dict(record=record,events=h.events),indent=2)+'\n')
    assert record['outcome']=='complete',record['reason']
    assert len(record['pairs'])==8 and len(record['receipts'])==7
    assert len(record['command_requests'])==16 and len(h.events)==696
    results=[e for e in record['executor_events'] if e['kind']=='executor_result']
    assert len(results)==23 and all(e['final_release_at'] is not None for e in results)
    assert all(not e['pending_releases'] and not e['held_keys'] and e['error'] is None for e in results)
    assert not record['real_client_accepted'] and not record['input_authorized']
