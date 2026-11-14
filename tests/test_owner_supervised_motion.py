"""Runnable owner helper, real bounded watchdog pulses on pipes; synthetic feedback."""
from dataclasses import asdict
import json
import math
import time

import pytest

from eql_automation.location_hotkey import OwnerLocationHotkey
from eql_automation.owner_navigation_preflight import window_identity
from eql_automation.owner_supervised_motion import MOTION_JOB, make_owner_nov12_engine
from eql_automation.supervised_motion import SupervisedMotionExecutors
from test_motion_collection import retained
import test_owner_location_hotkey_test as setup
from test_route_step_sender import after_down


@pytest.fixture
def h(tmp_path, retained, monkeypatch):
    def factory(engine, *, observer_factory, output):
        return make_owner_nov12_engine(engine, observer_factory=observer_factory,
            output_root=output/'motion', hotkey_output=output/'hotkey')
    monkeypatch.setattr(setup, 'make_owner_nov12_engine', factory)
    generator=setup.h.__wrapped__(tmp_path, retained)
    h=next(generator)
    e=h.engine
    h.sender.codes.EV_KEY=1
    def seed_setup():
        # Most refusal tests start from a synthetic successful setup record;
        # the complete experiment test instead runs the actual setup path.
        binding=OwnerLocationHotkey.configured('F4', confirmation_id='fixture-owner-declaration',
            configuration_paths=(h.game/'eqclient.ini', h.game/'Probe_private_LO1.ini'))
        e.sender=h.sender
        e.last_hotkey_test=dict(outcome='observed_location', window_identity=window_identity(h.gate,require_focus=False),
            expected_character='Probe',expected_server='private',owner_setup=asdict(binding),record_id='fixture-setup')
        e.cancelled=True
    h.seed=seed_setup
    def start_motion(declaration=None):
        e.post(MOTION_JOB, {'open_flat_clear':True} if declaration is None else declaration)
        e.handle_job(*e.jobs.get_nowait())
    h.motion=start_motion
    def due_motion():
        e.supervised_motion['due']=time.monotonic()-.001
        h.tick()
    h.motion_due=due_motion
    yield h
    e._cancel_motion('test teardown')
    e._finish_motion('test teardown')
    e._close_supervised('test teardown')
    generator.close()


def complete(h, timeout=12):
    until=time.monotonic()+timeout
    while h.engine.supervised_motion is not None and time.monotonic()<until:
        h.tick(); h.drain(); time.sleep(.01)
    assert h.engine.supervised_motion is None, h.notices
    h.drain()
    return h.engine.last_motion_collection_result


def feedback(h, monkeypatch):
    point=[0.,0.,0.]; heading=[350.]
    def reply():
        if h.engine.motion_collection_driver is None or h.engine.motion_collection_driver.session.phase=='requesting':
            h.append('Your Location is '+', '.join(f'{v:.2f}' for v in point))
    after_down(monkeypatch, reply)
    original=SupervisedMotionExecutors.run_pulse
    def pulse(self, request):
        result=original(self,request)
        r=result.receipt
        held=((r.up_started_at-r.down_completed_at)+r.maximum_held_seconds)/2
        if request.probe.key=='forward':
            rad=math.radians(heading[0])
            point[0]+=math.cos(rad)*30*held;point[1]+=math.sin(rad)*30*held
        else:
            heading[0]=(heading[0]+(-1 if request.probe.key=='right' else 1)*170*max(0.,held-.03))%360
        return result
    monkeypatch.setattr(SupervisedMotionExecutors,'run_pulse',pulse)


def test_actual_helper_hotbutton_then_finite_relative_calibration(h, monkeypatch):
    feedback(h,monkeypatch)
    h.start();h.due()
    assert setup.finish(h)['outcome']=='observed_location'
    h.motion();assert h.engine.supervised_motion['stage']=='countdown'
    h.motion_due();result=complete(h)
    assert result['outcome']=='complete', (result['reason'],h.notices)
    assert len(result['receipts'])==7 and len(result['raw_fixes'])==16
    assert result['relative_measurement'] and result['absolute_zone_binding']=='unbound'
    assert result['estimate']['zone_binding']==dict(zone=None,generation=None,source='unbound')
    assert result['executor_events'][0]['movement_clearance']=='owner_declared_open_flat_ground'
    assert not result['real_client_accepted'] and not result['input_authorized']
    downs=[code for kind,code,value in h.events if kind==1 and value==1]
    assert downs.count(62)==17 and [c for c in downs if c!=62]==[103,106,103,106,103,105,103]
    assert not h.sender.held and h.engine.cancelled and h.observer_closed
    assert json.loads(h.engine.last_motion_collection_path.read_text())['outcome']=='complete'


@pytest.mark.parametrize('failure',['missing_setup','different_session','assist','missing_confirmation','numeric_confirmation'])
def test_no_movement_without_explicit_same_session_setup(h,failure):
    if failure!='missing_setup':h.seed()
    if failure=='different_session':h.engine.last_hotkey_test['window_identity']=('other',)
    if failure=='assist':h.engine.measurement_only=False
    declaration={'open_flat_clear':False} if failure=='missing_confirmation' else {'open_flat_clear':1} if failure=='numeric_confirmation' else None
    h.motion(declaration);h.drain()
    assert h.engine.supervised_motion is None and not h.events


@pytest.mark.parametrize('change',['f9','f11','job','focus','settings','source','owner_activity','assist','log_veto'])
def test_countdown_revocation_never_sends_a_key(h,change):
    h.seed();h.motion()
    if change=='f9':h.engine.stop_action('F9')
    elif change=='f11':h.engine.stop_autopilot('F11')
    elif change=='job':h.engine.post('settings',h.engine.settings)
    elif change=='focus':h.focused=False
    elif change=='settings':h.engine.settings.level+=1
    elif change=='source':(h.game/'eqclient.ini').write_text('changed')
    elif change=='owner_activity':h.sample_hook=lambda:(_ for _ in ()).throw(ValueError('activity'))
    elif change=='assist':h.engine.measurement_only=False
    else:h.append('Auto attack is on.')
    h.motion_due();h.drain()
    assert h.engine.supervised_motion is None and h.engine.cancelled and not h.events


@pytest.mark.parametrize('phase',['hotkey_down','motion_down','waiting_reply','final_pair'])
def test_f9_or_owner_activity_stops_and_releases_in_each_phase(h,monkeypatch,phase):
    h.seed();feedback(h,monkeypatch)
    stopped=[False]
    def stop():
        driver=h.engine.motion_collection_driver
        if stopped[0] or driver is None:return
        if ((phase=='hotkey_down' and driver.session.phase=='requesting')
                or (phase=='motion_down' and driver.session.phase=='pulsing')):
            stopped[0]=True;h.engine.stop_action('F9 during DOWN')
    after_down(monkeypatch,stop)
    h.motion();h.motion_due()
    if phase in ('waiting_reply','final_pair'):
        def activity():
            driver=h.engine.motion_collection_driver
            if driver and ((phase=='waiting_reply' and driver.session.phase=='await_location')
                    or (phase=='final_pair' and len(driver.session.receipts)==7)):
                stopped[0]=True
                raise ValueError('physical owner activity between operations')
        h.sample_hook=activity
    result=complete(h)
    assert stopped[0] and result['outcome']=='stopped'
    assert not h.sender.held and h.engine.cancelled
    assert result['estimate'] is None
    down_codes={code for kind,code,value in h.events if kind==1 and value==1}
    assert all((1,code,0) in h.events for code in down_codes)
    before=len(h.events);h.tick();h.drain();assert len(h.events)==before


def test_observer_close_error_still_finishes_stopped(h):
    h.seed();h.motion()
    h.engine.supervised_motion['observer'].close=lambda:(_ for _ in ()).throw(OSError('close failed'))
    h.engine.stop_action('F9');h.tick()
    assert h.engine.supervised_motion is None and h.engine.cancelled
    assert any('close failed' in str(v) for v in h.notices)
