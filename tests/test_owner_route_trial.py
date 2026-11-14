"""Retained engine, actual pipe inputs, simulated physical/log feedback only."""
from dataclasses import asdict, replace
import math
import time

import numpy as np
import pytest

from eql_automation.location_hotkey import OwnerLocationHotkey
from eql_automation.owner_navigation_preflight import window_identity
from eql_automation.owner_route_trial import TRIAL_JOB, DESTINATION_JOB, make_owner_route_trial_engine
from eql_automation.supervised_motion import SupervisedMotionExecutors
from test_motion_collection import retained
from test_current_route_start import fixture as geometry_fixture
import test_owner_location_hotkey_test as setup
from test_route_step_sender import after_down


@pytest.fixture
def h(tmp_path,retained,monkeypatch):
    root=tmp_path/'geometry';root.mkdir()
    geometry=geometry_fixture(root)
    p=geometry.planner
    # A complete, deliberately wide synthetic plane for the whole experiment.
    triangles=p.ground.triangles.copy();triangles[:,:,:2]*=100
    p.ground.triangles=p.mesh._detail=triangles
    p.ground.minimum=triangles.min(axis=1);p.ground.maximum=triangles.max(axis=1)
    p.source.sources=tuple(replace(s,vertices_wld=tuple((x*100,y*100,z)
        for x,y,z in s.vertices_wld)) for s in p.source.sources)
    xyz=np.asarray([s.vertices_wld for s in p.source.sources])[:,:,[1,0,2]]
    p.source.source_minimum=xyz.min(axis=1);p.source.source_maximum=xyz.max(axis=1)
    loading=[lambda:p];destination_loading=[lambda:None];crossing_loading=[lambda:None]
    def factory(engine,*,observer_factory,output):
        return make_owner_route_trial_engine(engine,planner_loader=lambda _:loading[0](),
            destination_loader=lambda _:destination_loading[0](),
            crossing_loader=lambda _:crossing_loading[0](),
            observer_factory=observer_factory,output_root=output/'trials',
            motion_output=output/'motion',hotkey_output=output/'hotkey')
    monkeypatch.setattr(setup,'make_owner_nov12_engine',factory)
    generator=setup.h.__wrapped__(tmp_path,retained);h=next(generator);e=h.engine
    h.sender.codes.EV_KEY=1
    (h.game/'Resources').mkdir();(h.game/'Resources/ZoneNames.txt').write_text('54^Fixture^0^0\n')
    e._service_zone_tracker();h.append('You have entered Fixture.');e._service_zone_tracker()
    binding=OwnerLocationHotkey.configured('F4',confirmation_id='synthetic-owner-test',
        configuration_paths=(h.game/'eqclient.ini',h.game/'Probe_private_LO1.ini'))
    e.sender=h.sender;e.cancelled=True
    e.last_hotkey_test=dict(outcome='observed_location',window_identity=window_identity(h.gate,require_focus=False),
        expected_character='Probe',expected_server='private',owner_setup=asdict(binding),record_id='synthetic-setup')
    h.point=[200.,400.,2.7];h.heading=350.;h.loader=p;h.loading=loading
    h.destination_loading=destination_loading
    h.crossing_loading=crossing_loading
    def start():
        e.post(TRIAL_JOB,{'open_flat_clear':True});e.handle_job(*e.jobs.get_nowait())
    h.start_trial=start
    h.due_trial=lambda:(e.supervised_motion.update(due=time.monotonic()-.001),h.tick())
    def physically_apply(key,receipt):
        held=((receipt.up_started_at-receipt.down_completed_at)+receipt.maximum_held_seconds)/2
        if key in ('forward',103):
            angle=math.radians(h.heading)
            h.point[0]+=math.cos(angle)*30.*held;h.point[1]+=math.sin(angle)*30.*held
        else:h.heading=(h.heading+(-1 if key in ('right',106) else 1)*170.*max(0.,held-.03))%360
    h.apply=physically_apply
    def reply():
        motion=e.motion_collection_driver;trial=e.route_trial;route=e.route_session_driver
        if ((motion is not None and motion.session.phase=='requesting')
                or (trial is not None and trial.get('collector') is not None
                    and trial['collector'].phase=='requesting' and trial['stage'].startswith('startup_'))
                or (route is not None and route.session.phase=='requesting')):
            h.append('Your Location is '+', '.join(f'{v:.2f}' for v in h.point))
    after_down(monkeypatch,reply)
    pulse=SupervisedMotionExecutors.run_pulse
    def motion_pulse(self,request):
        result=pulse(self,request);h.apply(request.probe.key,result.receipt);return result
    monkeypatch.setattr(SupervisedMotionExecutors,'run_pulse',motion_pulse)
    import eql_automation.route_session as route_module
    step=route_module.run_checked_route_step
    def route_step(*args,**kwargs):
        result=step(*args,**kwargs);h.apply(result.receipt.key_code,result.receipt);return result
    monkeypatch.setattr(route_module,'run_checked_route_step',route_step)
    yield h
    e._cancel_trial('test teardown');e._cancel_motion('test teardown')
    e._finish_motion('test teardown');e._finish_route('test teardown')
    e._finish_trial('test teardown');e._close_supervised('test teardown');e._close_zone_tracker()
    generator.close()


def finish(h,timeout=25.):
    e=h.engine;deadline=time.monotonic()+timeout
    while (e.supervised_motion is not None or e.route_trial is not None) and time.monotonic()<deadline:
        h.tick();h.drain();time.sleep(.01)
    h.drain()
    assert e.supervised_motion is None and e.route_trial is None,h.notices
    return e.last_route_trial_result


def test_actual_same_action_motion_startup_route_and_release(h):
    h.start_trial();assert h.engine.supervised_motion is not None
    h.due_trial();record=finish(h)
    assert record is not None,h.notices
    assert record['outcome']=='arrived',(record['reason'],h.notices)
    assert record['motion_record']['outcome']=='complete'
    assert len(record['motion_record']['receipts'])==7
    assert len(record['startup_pairs'])==2 and all(p['outcome']=='complete' for p in record['startup_pairs'])
    assert record['route']['outcome']=='arrived' and record['route']['steps']
    assert not record['real_client_accepted'] and not h.sender.held
    assert h.engine.cancelled and h.observer_closed
    assert h.engine.live_zone_tracker.lease is None
    assert h.engine.last_route_trial_path.is_file()
    assert all(s['authorization_scope']=='owner_supervised_conditional_trial'
               for s in record['route']['steps'])


def test_active_plan_replacement_during_height_binding_stops(h, monkeypatch):
    import eql_automation.owner_route_trial as module
    measure = module.measure_current_height
    binding = h.engine._trial_binding
    armed = []; fired = []
    def during_height(*args, **kwargs):
        armed.append(True)
        try: return measure(*args, **kwargs)
        finally: armed.clear()
    def changed_plan(p):
        value = binding(p)
        if armed and not fired:
            p['plan'] = replace(p['plan'])
            fired.append(True)
        return value
    monkeypatch.setattr(module, 'measure_current_height', during_height)
    monkeypatch.setattr(h.engine, '_trial_binding', changed_plan)
    h.start_trial(); h.due_trial(); record = finish(h)
    assert fired and record['outcome'] == 'stopped', h.notices
    assert 'Active route plan' in record['reason']
    assert not h.sender.held and h.observer_closed and h.engine.cancelled
    assert h.engine.route_session_driver is None and h.engine.live_zone_tracker.lease is None


def test_route_countdown_payload_uses_observed_zone(h):
    h.engine.zone='historical-zone'
    h.start_trial()
    state=h.engine.autopilot_payload()
    assert state['state']=='running' and state['trial_stage']=='countdown'
    assert state['zone']=='Fixture' and 'route trial' in state['phase'].lower()


@pytest.mark.parametrize('missing',['zone','assets','transition_during_loading'])
def test_missing_start_dependency_refuses_before_any_motion(h,missing):
    if missing=='zone':h.engine.live_zone_tracker.reader._clear_zone()
    elif missing=='assets':h.loader.zone_id=99
    else:h.loading[0]=lambda:(h.append('You have entered Fixture.'),h.loader)[1]
    h.start_trial();h.drain()
    assert h.engine.supervised_motion is None and h.engine.route_trial is None
    assert not h.events and h.engine.cancelled


@pytest.mark.parametrize('phase',['startup','route'])
def test_f9_during_handoff_followup_key_releases_and_closes_scope(h,monkeypatch,phase):
    fired=[]
    def stop():
        p=h.engine.route_trial
        if p is None or fired:return
        if (phase=='startup' and p['busy'] and p['stage']=='startup_plan') or (
                phase=='route' and p.get('driver') is not None and p['driver'].session.phase=='stepping'):
            fired.append(True);h.engine.stop_action('F9 during '+phase+' DOWN')
    after_down(monkeypatch,stop)
    h.start_trial();h.due_trial();record=finish(h)
    assert fired and record is not None and record['outcome']=='stopped',h.notices
    assert not h.sender.held and h.engine.cancelled and h.observer_closed
    assert h.engine.live_zone_tracker.lease is None
    before=len(h.events);h.tick();h.drain();assert len(h.events)==before


def test_stop_from_completed_motion_trace_cannot_start_continuation(h):
    original=h.engine.trace;fired=[]
    def trace(event,**values):
        original(event,**values)
        if event=='motion_collection_result':
            fired.append(True);h.engine.stop_action('F9 during completion persistence')
    h.engine.trace=trace
    h.start_trial();h.due_trial();record=finish(h)
    assert fired and record is None
    assert h.engine.last_motion_collection_result['outcome']=='complete'
    assert h.engine.route_session_driver is None and h.engine.cancelled and h.observer_closed
    assert not h.sender.held
