"""Actual retained helper lifecycle, synthetic route feedback and pipe only."""
import json
import time

import pytest

from eql_automation.owner_position_adapter import make_owner_nov12_engine
from eql_automation.owner_route_adapter import make_route_session_engine
from test_motion_collection import retained
from test_route_floor_commit import legacy
from test_route_session import make


def setup(tmp_path,retained,legacy,*,real=False):
    Engine,Settings,_=retained
    base=make_owner_nov12_engine(Engine)
    engine=make_route_session_engine(base,output_root=tmp_path/'saved')(
        Settings(game_dir=str(tmp_path/'game'),character='Probe',server='private'),
        lambda *_:None,lambda *_:None,measurement_only=True)
    engine.selector.close()
    engine.trace=lambda *a,**k:None
    engine.emit=lambda *a,**k:None
    def forbidden(*a,**k):raise AssertionError('No device creation, capture or legacy movement')
    engine.send=engine.hold=engine.ensure_sender=engine.ensure_pointer=forbidden
    h=make(tmp_path,legacy,real=real,lock=engine.g0_stop_lock)
    h.engine=engine
    engine.sender=h.sender
    h.sender.release_all=lambda:[h.sender.release(key) for key in tuple(h.sender.held)]
    engine.attach_route_session(h.driver)
    def location(request):
        from eql_automation.motion_collection import CommandReceipt
        began=h.clock();h.commands.append(request)
        x,y,z=h.point
        h.append('Your Location is %.2f, %.2f, %.2f'%(y,x,z+2.1))
        h.hook()
        engine.autopilot_tick(h.clock())
        return CommandReceipt(began,h.clock())
    h.driver.request_location=location
    h.driver.pump=lambda:engine.autopilot_tick(h.clock())
    def tick():
        if real:time.sleep(.01)
        else:h.now+=.025
        before=len(h.session.steps)
        engine.autopilot_tick(h.clock())
        if len(h.session.steps)>before:
            r=h.session.steps[-1]['receipt']
            h.point=(h.point[0]+10*(r['up_completed_at']-r['down_started_at']),h.point[1],h.point[2])
    h.tick=tick
    return h


@pytest.mark.parametrize('action',['f9','job','close','assist','sender','motion'])
def test_retained_engine_cancels_route_and_saves_partial_record(tmp_path,retained,legacy,action):
    h=setup(tmp_path,retained,legacy)
    try:
        e=h.engine;h.now+=.13;e.autopilot_tick(h.clock())
        assert h.session.phase=='await_location'
        if action=='f9':e.stop_action('F9 owner stop')
        elif action=='job':e.post('settings',e.settings)
        elif action=='close':e.stopping=True
        elif action=='assist':e.measurement_only=False
        elif action=='sender':e.sender=None
        elif action=='motion':e.motion_collection_driver=object()
        e.autopilot_tick(h.clock())
        assert e.route_session_driver is None and h.session.phase=='stopped'
        record=json.loads(e.last_route_session_path.read_text())
        assert record['outcome']=='stopped' and not record['steps']
        assert not record['real_client_accepted'] and not h.sender.held
    finally:h.close()


def test_assist_helper_refuses_route_attachment(tmp_path,retained,legacy):
    h=setup(tmp_path,retained,legacy)
    try:
        e=h.engine;e.route_session_driver=None;e.measurement_only=False
        with pytest.raises(ValueError,match='measurement'):e.attach_route_session(h.driver)
        assert e.route_session_driver is None and not h.commands
    finally:h.close()


def test_f9_during_actual_pipe_down_releases_without_next_pair(tmp_path,retained,legacy,monkeypatch):
    from test_route_step_sender import after_down
    h=setup(tmp_path,retained,legacy,real=True)
    try:
        after_down(monkeypatch,lambda:h.engine.stop_action('F9 during route pulse'))
        deadline=time.monotonic()+4
        while h.engine.route_session_driver is not None and time.monotonic()<deadline:h.tick()
        assert h.engine.route_session_driver is None
        assert h.session.phase=='stopped' and h.runner.steps==0
        assert h.ledger.chain is h.f.chain and not h.sender.held
        assert len(h.commands)==2 and len(h.session.pairs)==1
        assert h.session.step_attempts[-1]['outcome']=='failed'
        assert h.session.step_attempts[-1]['input_delivery']=='unknown'
    finally:h.close()
    assert (1,103,1) in h.events and (1,103,0) in h.events


def test_retained_engine_ticks_finish_route_and_save_evidence(tmp_path,retained,legacy):
    h=setup(tmp_path,retained,legacy,real=True)
    try:
        deadline=time.monotonic()+20
        while h.engine.route_session_driver is not None and time.monotonic()<deadline:h.tick()
        assert h.engine.route_session_driver is None
        record=json.loads(h.engine.last_route_session_path.read_text())
        assert record['outcome']=='arrived' and record['segment_index']==2
        assert len(record['stopped_pairs'])==len(record['steps'])+1
        assert len(record['command_requests'])==2*len(record['stopped_pairs'])
        assert not record['real_client_accepted'] and not h.sender.held
    finally:h.close()
