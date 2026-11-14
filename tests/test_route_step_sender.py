"""Actual watchdog subprocesses on pipes, with explicitly synthetic guards."""
from dataclasses import replace
import os
import time
from types import SimpleNamespace

import pytest

from eql_automation.fixed_route_follower import RouteHalt
from eql_automation.g2_pulse_budget import G2Scene
from eql_automation.route_step_sender import (RouteStepAuthorization, RouteStepScene,
                                            run_checked_route_step)
from eql_automation.uinput_watchdog import _EVENT
import eql_automation.uinput_watchdog as watchdog
import eql_automation.route_step_sender as bridge
from test_route_floor_commit import legacy, setup


class PipeSender:
    def __init__(self, fd):
        self.ui = SimpleNamespace(fileno=lambda:fd)
        self.codes = SimpleNamespace(KEY_UP=103, KEY_LEFT=105, KEY_RIGHT=106)
        self.held = set()
        self.unfinished = self.dismissed = False
        self.on_check = self.on_release = lambda:None
        self.release_calls = 0

    def check(self):
        self.on_check()

    def release(self, code):
        self.release_calls += 1
        self.on_release()
        os.write(self.ui.fileno(), _EVENT.pack(0,0,1,code,0))
        os.write(self.ui.fileno(), _EVENT.pack(0,0,0,0,0))
        self.held.discard(code)


@pytest.fixture
def harness(legacy):
    f = setup(legacy, clock=time.monotonic)
    rd, wr = os.pipe()
    sender = PipeSender(wr)
    f.sender, f.events, f.extra_fds = sender, [], []
    f.scene_calls = 0
    def scene():
        f.scene_calls += 1
        raw = f.reference.raw_fix
        return RouteStepScene(f.reference, G2Scene(time.monotonic(), f.runner.route.zone,
            raw.raw_coordinates, raw.log_epoch, raw.log_line_seq, raw.zone_generation,
            True, True, True, True, True, True, True))
    def prepare(proposal, observed):
        return f.ledger.stage(proposal, reference_fix=observed.reference_fix,
            footprint=f.footprint, sources=f.sources, requested_seconds=.02,
            maximum_actual_hold=.15, movement_key=103,
            motion_bounds_record_id='synthetic-only-guard', check_geometry=f.check)
    def authorize(ticket, observed):
        return RouteStepAuthorization(ticket, observed.reference_fix, time.monotonic(),
            ticket.preparation.proposal.at+.05, 'synthetic-only-full-guard')
    f.options = dict(scene_provider=scene, prepare_step=prepare, authorize_step=authorize,
                     still_authorized=lambda *_:True, command_state_clear=lambda:True,
                     pump=lambda:None)
    f.run = lambda:run_checked_route_step(sender, f.ledger, **f.options)
    f.rd, f.wr = rd, wr
    yield f
    for fd in [wr, *f.extra_fds]:
        try:os.close(fd)
        except OSError:pass
    data = b''
    while chunk := os.read(rd,4096):data += chunk
    os.close(rd)
    f.events.extend((kind,key,value) for _,_,kind,key,value in _EVENT.iter_unpack(data))


def read_available(f):
    os.set_blocking(f.rd,False)
    try:data=os.read(f.rd,65536)
    except BlockingIOError:data=b''
    finally:os.set_blocking(f.rd,True)
    return [(kind,key,value) for _,_,kind,key,value in _EVENT.iter_unpack(data)]


def assert_refused(f, *, down=False, retained=False):
    assert f.runner.phase=='halted' and f.runner.steps==0
    assert f.ledger.chain is f.chain and f.chain.index==1
    sent=read_available(f)
    assert ((1,103,1) in sent) is down
    if down:assert (1,103,0) in sent
    assert bool(f.sender.held) is retained
    assert f.sender._eql_route_operation is None


def test_success_releases_before_commit_then_requires_new_observation(harness):
    f=harness;original=f.ledger.commit
    def commit(ticket,receipt):
        assert f.sender.release_calls==1 and not f.sender.held
        assert f.ledger.chain is f.chain
        return original(ticket,receipt)
    f.ledger.commit=commit
    result=f.run()
    assert result.real_client_accepted is False
    assert result.guard_record_id=='synthetic-only-full-guard'
    assert result.floor_proof_sha256==f.ledger.chain.previous.proof_sha256
    assert f.runner.phase=='await_stopped' and f.runner.steps==1
    assert f.ledger.chain.index==2 and f.chain.index==1
    assert f.scene_calls>=4 and f.sender._eql_route_operation is None
    assert read_available(f)[:4]==[(1,103,1),(0,0,0),(1,103,0),(0,0,0)]


@pytest.mark.parametrize('change',['draft','dismissed','recovery','assist','held','keymap','missing_guard'])
def test_invalid_initial_state_sends_no_down(harness,change):
    f=harness
    if change=='draft':f.sender.unfinished=True
    elif change=='dismissed':f.sender.dismissed=True
    elif change=='recovery':f.options['command_state_clear']=lambda:False
    elif change=='assist':f.state['mode']='assist'
    elif change=='held':f.sender.held.add(105)
    elif change=='keymap':f.sender.codes.KEY_UP=17
    else:f.options['authorize_step']=None
    with pytest.raises((RouteHalt,ValueError)):f.run()
    if change=='missing_guard':
        assert f.runner.phase=='ready' and not read_available(f)
    else:assert_refused(f,retained=change=='held')


@pytest.mark.parametrize('change',['scene','reference','guard','generation','mode','floor','slow_guard','late_permit'])
def test_changed_or_untrusted_authorization_never_sends_down(harness,change):
    f=harness;original=f.options['authorize_step']
    def authorize(ticket,observed):
        result=original(ticket,observed)
        if change=='scene':
            f.reference=replace(f.reference,raw_fix=replace(f.reference.raw_fix,raw_coordinates=(0.,0.,0.)))
        elif change=='reference':f.reference=replace(f.reference)
        elif change=='guard':return f.evaluated[-1][2]  # Offline candidate cannot authorize.
        elif change=='generation':f.state['generation']=2
        elif change=='mode':f.state['mode']='full_auto'
        elif change=='floor':f.evaluated[-1][1]._selected.clear()
        elif change=='slow_guard':time.sleep(.06)
        elif change=='late_permit':return replace(result,expires_at=result.expires_at+.01)
        return result
    f.options['authorize_step']=authorize
    with pytest.raises(RuntimeError):f.run()
    assert_refused(f)


def after_down(monkeypatch, action):
    original=watchdog._read_status
    def wrapped(*args,**kwargs):
        result=original(*args,**kwargs)
        if result=='DOWN':action()
        return result
    monkeypatch.setattr(watchdog,'_read_status',wrapped)


@pytest.mark.parametrize('change',['off','rearm','unsafe','revoked','new_fix','device'])
def test_revocation_after_down_releases_and_never_commits(harness,monkeypatch,change):
    f=harness
    def action():
        if change=='off':f.ledger.cancel('owner OFF')
        elif change=='rearm':f.state['generation']+=1
        elif change=='unsafe':f.sender.dismissed=True
        elif change=='revoked':f.options['revoked']=True
        elif change=='new_fix':f.reference=replace(f.reference)
        elif change=='device':f.sender.ui=SimpleNamespace(fileno=lambda:f.wr)
    f.options['still_authorized']=lambda *_:not f.options.get('revoked',False)
    after_down(monkeypatch,action)
    with pytest.raises(RuntimeError):f.run()
    assert_refused(f,down=True,retained=change=='device')


@pytest.mark.parametrize('when', ['before_down', 'after_down', 'final_release'])
def test_latched_log_veto_releases_without_floor_commit(harness,monkeypatch,tmp_path,when):
    from eql_automation.scene_log_veto import SceneLogVeto
    from eql_automation.g2_scene_observer import G2ObservationUnavailable
    f=harness
    path=tmp_path/'eqlog_Probe_private.txt'
    path.touch()
    veto=SceneLogVeto(path,expected_character='Probe',expected_server='private',
                      cancel_generation=1)
    original=f.options['scene_provider']
    def scene():
        observation=veto.poll()
        if observation.reason or not observation.continuity_available:
            raise G2ObservationUnavailable(observation.reason)
        # UI, motion and geometry remain explicitly synthetic in this pipe test.
        return original()
    def hazard():
        with path.open('a') as output:
            output.write('[Sat Nov 14 01:00:00 2026] Training dummy hits YOU for 2 points of damage.\n')
    f.options['scene_provider']=scene
    if when=='before_down':hazard()
    elif when=='after_down':after_down(monkeypatch,hazard)
    else:f.sender.on_release=hazard
    with pytest.raises(RuntimeError):f.run()
    assert veto.poll().reason=='incoming_attack'
    assert_refused(f,down=when!='before_down')


def test_final_release_failure_retains_key_and_old_floor(harness):
    f=harness
    def fail():raise OSError('UP/SYN failed')
    f.sender.on_release=fail
    with pytest.raises(OSError,match='UP/SYN'):f.run()
    assert_refused(f,down=True,retained=True)


def test_descriptor_reuse_cannot_redirect_watchdog_cleanup(harness,monkeypatch):
    f=harness;other_rd,other_wr=os.pipe();f.extra_fds.append(other_rd)
    def replace_fd():
        os.dup2(other_wr,f.wr)
        os.close(other_wr)
    after_down(monkeypatch,replace_fd)
    with pytest.raises(RuntimeError):f.run()
    # Original pipe still receives watchdog UP through the pinned duplicate.
    assert_refused(f,down=True,retained=True)
    os.set_blocking(other_rd,False)
    with pytest.raises(BlockingIOError):os.read(other_rd,4096)


def test_reentrant_call_cancels_outer_without_second_down(harness):
    f=harness;original=f.options['authorize_step']
    def nested(ticket,scene):
        with pytest.raises(RouteHalt,match='active'):f.run()
        return original(ticket,scene)
    f.options['authorize_step']=nested
    with pytest.raises(RouteHalt):f.run()
    assert_refused(f)


def test_off_in_final_release_cannot_commit(harness):
    f=harness
    f.sender.on_release=lambda:f.ledger.cancel('OFF during final release')
    with pytest.raises(RuntimeError):f.run()
    assert_refused(f,down=True)


def test_key_readded_by_post_release_callback_cannot_commit(harness):
    f=harness
    def revocation_check(*_):
        if f.sender.release_calls:f.sender.held.add(103)
        return True
    f.options['still_authorized']=revocation_check
    with pytest.raises(RuntimeError):f.run()
    assert_refused(f,down=True,retained=True)


def test_pinned_descriptor_close_failure_does_not_commit_or_leave_busy(harness,monkeypatch):
    f=harness;original_pulse=bridge.selected_key_pulse_receipt;original_close=os.close
    pinned=None;failed=False
    def pulse(fd,*args,**kwargs):
        nonlocal pinned
        pinned=fd
        return original_pulse(fd,*args,**kwargs)
    def close(fd):
        nonlocal failed
        if fd==pinned and not failed:
            failed=True
            raise OSError('pinned close failed')
        return original_close(fd)
    monkeypatch.setattr(bridge,'selected_key_pulse_receipt',pulse)
    monkeypatch.setattr(os,'close',close)
    with pytest.raises(OSError,match='pinned close failed'):f.run()
    assert_refused(f,down=True)
