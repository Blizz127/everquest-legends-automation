"""Real watchdog/pipe input; explicitly synthetic policy, geometry and game replies."""
from dataclasses import replace
from datetime import datetime,timedelta
import os
import threading
import time
from types import SimpleNamespace

import pytest

from eql_automation.camp_probe_preparation import CampProbePreparation
from eql_automation.camp_probe_runtime import CampProbeRuntime
from eql_automation.camp_probe_sender import CampProbeAuthorization,CampProbeInputPolicy
from eql_automation.camp_stopped_height import measure_camp_stopped_height
from eql_automation.location_hotkey import OwnerLocationHotkey
from eql_automation.motion_calibration import Probe
from eql_automation.native_region_policy import encoded
from eql_automation.owner_input_observer import OwnerInputObservation
from eql_automation.owner_zone_tracker import LiveZoneTracker
from eql_automation.uinput_watchdog import _EVENT
from test_camp_floor_checkpoint import checkpoint
from test_source_motion import f
from test_route_floor_commit import legacy


class SyntheticPolicy(CampProbeInputPolicy):
    def __init__(self,transaction,h):
        super().__init__(transaction);self.h=h;self.authorization=None

    def check(self):
        self.h.current()
        return not self.h.refuse_policy

    def authorize(self,ticket):
        self.authorization=CampProbeAuthorization(ticket,time.monotonic(),
            ticket.proposed_at+.05,'synthetic-test-policy-only')
        return self.authorization

    def still_authorized(self,authorization):
        return authorization is self.authorization and self.check()


@pytest.fixture
def runtime_fixture(checkpoint,tmp_path):
    h=checkpoint;h.real=True
    # Preserve the fixture's log clock, advancing it with actual monotonic time.
    h.wall=lambda:datetime(2026,11,14,12)+timedelta(seconds=h.clock()-100.)
    h.scope=('camp-probe-runtime-test',1);h.mode='camp_probe';h.refuse_policy=False
    h.current=lambda:current(h)
    tracker=LiveZoneTracker(h.reader.tail.path,tmp_path/'ZoneNames.txt',
        expected_character='Probe',expected_server='private',binding_reader=lambda:h.owner,clock=h.clock)
    tracker.reader=h.reader;h.lease=tracker.acquire()
    h.current()
    baseline=h.reader.log_line_seq;released=time.monotonic()
    time.sleep(.13);a=h.position();time.sleep(.405);b=h.position()
    height=measure_camp_stopped_height(h.checkpoint,h.reader,a,b,minimum_log_seq=baseline,
        released_at=released,owner_binding=h.scope,binding_reader=lambda:h.scope,
        clock=h.clock,local_wall_clock=h.wall)
    # Explicit test hypotheses, not client-derived movement bounds.
    bounds=replace(h.ledger.bounds,forward_speed_upper_bound=3.,maximum_requested_hold=.02,
                   maximum_actual_hold=.15)
    h.preparation=CampProbePreparation(h.checkpoint,height,h.lease,probe_kind='forward',
        bounds=bounds,bounds_basis=encoded({'kind':'synthetic_pipe_fixture'}),
        owner_binding=h.scope,binding_reader=lambda:h.scope,clock=h.clock,local_wall_clock=h.wall)
    config=tmp_path/'hotbutton.ini';config.write_text('synthetic F1 = /location\n')
    h.hotkey=OwnerLocationHotkey.configured('F1',confirmation_id='synthetic-only',configuration_paths=(config,))
    h.sender.gate=SimpleNamespace(controls_ready=lambda:h.focus)
    h.sender.on_check=h.current
    def sample():
        at=time.monotonic()
        return OwnerInputObservation(at,at,1,True,1,0,h.active,0,'synthetic-input-monitor')
    h.owner_input=SimpleNamespace(sample=sample)
    h.x=4.;h.y=2.;h.down=set();h.pending_replies=0;h.stream=[];h.after_down=None
    h.runtime=None;h.reentrant_ticks=0;h.real_pump=None
    def pump():
        os.set_blocking(h.rd,False)
        try:
            while True:
                try:raw=os.read(h.rd,65536)
                except BlockingIOError:break
                if not raw:break
                for _,_,kind,key,value in _EVENT.iter_unpack(raw):
                    h.stream.append((kind,key,value))
                    if kind!=1:continue
                    if value==1:
                        h.down.add(key)
                        if key==59:h.pending_replies+=1
                        if key in (103,105,106) and h.after_down is not None:
                            callback=h.after_down;h.after_down=None;callback()
                    else:
                        if key==103 and key in h.down:h.x+=.2
                        h.down.discard(key)
        finally:os.set_blocking(h.rd,True)
        # Synthetic client feedback is appended only for the configured key.
        while h.pending_replies:
            h.append(f'Your Location is {h.y:.2f}, {h.x:.2f}, 2.70');h.pending_replies-=1
        if h.runtime is not None and h.runtime.busy:
            h.reentrant_ticks+=1;h.runtime.tick()
    h.real_pump=pump
    h.options=dict(sender=h.sender,hotkey=h.hotkey,owner_input=h.owner_input,
        stop_lock=threading.RLock(),movement_policy_factory=lambda tx:SyntheticPolicy(tx,h),
        check_current=h.current,command_state_clear=lambda:True,pump=pump,
        probes=(Probe('forward',103,.02),),maximum_seconds=120.)
    def create():
        h.runtime=CampProbeRuntime(h.preparation,**h.options);return h.runtime
    h.create=create
    yield h
    if h.runtime is not None:
        if h.runtime.phase not in ('complete','stopped'):h.runtime.cancel('test cleanup')
        if not h.runtime.closed and not h.runtime.busy and not h.sender.held:h.runtime.release()
    elif h.lease.active:h.lease.release()


def current(h):
    if not h.focus or h.active or h.mode!='camp_probe':raise ValueError('synthetic focus/input/mode stop')


def run(h):
    runtime=h.runtime;deadline=time.monotonic()+110.
    while runtime.phase not in ('complete','stopped'):
        assert time.monotonic()<deadline,'runtime did not terminate'
        h.real_pump();runtime.tick();h.real_pump()
        time.sleep(.005)
    return runtime.snapshot()


def test_seven_probes_use_real_pipe_sender_and_one_reader(runtime_fixture):
    h=runtime_fixture
    h.options['probes']=tuple(Probe(kind,{'forward':103,'right':106,'left':105}[kind],.02)
        for kind in ('forward','right','forward','right','forward','left','forward'))
    r=h.create();data=run(h)
    assert data['phase']=='complete' and data['completed_probes']==7
    assert len(data['collections'])==27  # three per probe plus six new planning pairs
    assert len([e for e in data['sender_events'] if e['kind']=='camp_probe_pulse'])==7
    assert [k for kind,k,v in h.stream if kind==1 and v==1 and k!=59]==[103,106,103,106,103,105,103]
    assert h.reentrant_ticks>0 and not h.sender.held and not h.down
    assert h.lease.active and h.reader.latest is r.results[-1].second
    assert not data['independent_scene_verified'] and not data['motion_bounds_verified']
    r.release();assert not h.lease.active and h.reader.latest is None and r.closed


@pytest.mark.parametrize('reason',('F8 assist','F9 stop'))
def test_stop_after_down_finishes_release_before_lease_or_assist(runtime_fixture,reason):
    h=runtime_fixture;r=h.create();observed=[]
    def stop():
        r.cancel(reason);observed.append(r.busy)
        with pytest.raises(ValueError,match='pending input'):r.release()
        assert h.reader.latest is not None
    h.after_down=stop
    with pytest.raises((RuntimeError,ValueError)):run(h)
    h.real_pump()
    assert observed==[True] and r.phase=='stopped' and not r.results
    assert (1,103,1) in h.stream and (1,103,0) in h.stream
    assert not h.sender.held and not h.down and h.sender._eql_route_operation is None
    assert not r.busy and not r.closed
    r.release();assert r.closed and h.reader.latest is None
    assert any(e['kind']=='camp_probe_pulse' and e['final_release_at'] is not None for e in r.events)


@pytest.mark.parametrize('fault',('policy_missing','policy_refused','bad_permit','command_busy','owner_input'))
def test_no_movement_with_missing_or_revoked_admission(runtime_fixture,fault):
    h=runtime_fixture
    if fault=='policy_missing':h.options['movement_policy_factory']=lambda tx:None
    elif fault=='policy_refused':h.refuse_policy=True
    elif fault=='bad_permit':
        class LatePermit(SyntheticPolicy):
            def authorize(self,ticket):
                return replace(super().authorize(ticket),expires_at=ticket.proposed_at+.1)
        h.options['movement_policy_factory']=lambda tx:LatePermit(tx,h)
    elif fault=='command_busy':h.options['command_state_clear']=lambda:False
    else:h.active=True
    try:
        h.create()
        with pytest.raises((RuntimeError,ValueError)):run(h)
    except ValueError:
        assert fault=='owner_input'
    h.real_pump()
    assert not [(k,v) for kind,k,v in h.stream if kind==1 and v==1 and k in (103,105,106)]
    assert not h.sender.held


def test_expired_start_after_watchdog_ready_is_not_renewed(runtime_fixture,monkeypatch):
    import eql_automation.camp_probe_sender as sender_module
    h=runtime_fixture;r=h.create();actual=sender_module.selected_key_pulse_receipt
    def delayed(fd,select,**options):
        def late_select():time.sleep(.55);return select()
        return actual(fd,late_select,**options)
    monkeypatch.setattr(sender_module,'selected_key_pulse_receipt',delayed)
    with pytest.raises((RuntimeError,ValueError)):run(h)
    h.real_pump()
    assert not [(k,v) for kind,k,v in h.stream if kind==1 and v==1 and k in (103,105,106)]
    assert r.phase=='stopped' and not r.results


@pytest.mark.parametrize('fault',('unfinished','policy_refused','owner_input'))
def test_watchdog_rechecks_admission_after_selection_before_go(runtime_fixture,monkeypatch,fault):
    import eql_automation.camp_probe_sender as sender_module
    h=runtime_fixture;r=h.create();actual=sender_module.selected_key_pulse_receipt
    selected=[]
    def changed(fd,select,**options):
        def after_selection():
            result=select();selected.append(result)
            if fault=='unfinished':h.sender.unfinished=True
            elif fault=='policy_refused':h.refuse_policy=True
            else:h.active=True
            return result
        return actual(fd,after_selection,**options)
    monkeypatch.setattr(sender_module,'selected_key_pulse_receipt',changed)
    with pytest.raises((RuntimeError,ValueError)):run(h)
    h.real_pump()
    assert len(selected)==1 and not [(k,v) for kind,k,v in h.stream if kind==1 and v==1 and k in (103,105,106)]
    assert not h.sender.held and not r.results


def test_device_replacement_after_down_releases_only_original_descriptor(runtime_fixture):
    h=runtime_fixture;r=h.create();original=h.sender.ui
    other_rd,other_wr=os.pipe()
    try:
        h.after_down=lambda:setattr(h.sender,'ui',SimpleNamespace(fileno=lambda:other_wr))
        with pytest.raises((RuntimeError,ValueError)):run(h)
        h.real_pump()
        assert (1,103,1) in h.stream and (1,103,0) in h.stream and not h.down
        assert h.sender.held=={103} and not r.results
        os.set_blocking(other_rd,False)
        with pytest.raises(BlockingIOError):os.read(other_rd,4096)
        with pytest.raises(ValueError):r.release()
    finally:
        h.sender.ui=original;h.sender.held.discard(103)
        os.close(other_wr);os.close(other_rd)


def test_focus_loss_after_down_stops_and_preserves_release(runtime_fixture):
    h=runtime_fixture;r=h.create();h.after_down=lambda:setattr(h,'focus',False)
    with pytest.raises((RuntimeError,ValueError)):run(h)
    h.real_pump()
    assert r.phase=='stopped' and not r.results and not h.down and not h.sender.held
    assert (1,103,0) in h.stream
