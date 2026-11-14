"""Distinct owner destination flow over the retained engine and synthetic world."""
import time

import numpy as np
import pytest

from eql_automation.current_route_start import encoded
from eql_automation.owner_destination_assets import DestinationRouteAssets
from eql_automation.owner_route_trial import DESTINATION_JOB
from test_destination_route import nav_module
from test_motion_collection import retained
from test_owner_route_trial import h,finish
from test_ground_observer import rectangle
from test_route_step_sender import after_down


def configure(h,nav_module):
    p=h.loader
    def rect(a,b):
        return tuple(tuple((x,a+y*(b-a)/4,z) for x,y,z in tri) for tri in rectangle(370.,410.,.6))
    triangles=np.asarray(rect(0.,220.)+rect(220.,400.))
    p.mesh.area=p.ground.areas=np.asarray([63,63])
    p.mesh._detail=p.ground.triangles=triangles;p.mesh._detail_start=np.asarray([0,2,4])
    p.ground.polys=np.asarray([0,0,1,1]);p.ground.components=np.asarray([7,7])
    p.ground.minimum=triangles.min(axis=1);p.ground.maximum=triangles.max(axis=1)
    rings=np.zeros((2,6,3))
    for i,(a,b) in enumerate(((0.,220.),(220.,400.))):
        rings[i,:4]=((370.,a,.6),(410.,a,.6),(410.,b,.6),(370.,b,.6))
    portals=np.asarray([((370.,220.,.6),(410.,220.,.6)),((410.,220.,.6),(370.,220.,.6))])
    nav=nav_module.NavMesh(rings,np.asarray([4,4]),p.mesh.area,np.asarray([0,1]),np.asarray([1,0]),
        portals,triangles,p.ground.polys,component=p.ground.components)
    nav.sha256=p.pins[0]
    # Calibration starts safely inside polygon0. It retains its actual final
    # heading and positions; the plan crosses the shared boundary to this goal.
    h.point[:2]=[200.,396.]
    assets=DestinationRouteAssets(p,nav,(388.,233.),'Synthetic destination',
        encoded(dict(kind='synthetic_fixture_destination',goal_xy=(388.,233.))))
    h.destination_loading[0]=lambda:assets
    return assets


def start(h):
    e=h.engine;e.post(DESTINATION_JOB,{'open_flat_clear':True});e.handle_job(*e.jobs.get_nowait())


def test_missing_destination_refuses_before_calibration(h):
    start(h)
    assert h.engine.supervised_motion is None and not h.sender.held
    assert any('pinned map and mesh' in message for message in h.notices)


def test_destination_changed_while_loading_refuses_before_calibration(h,nav_module):
    assets=configure(h,nav_module)
    def changed():
        h.append('LOADING, PLEASE WAIT...');return assets
    h.destination_loading[0]=changed
    start(h)
    assert h.engine.supervised_motion is None and not h.sender.held


def test_startup_budget_also_covers_countdown(h,nav_module):
    configure(h,nav_module);start(h)
    p=h.engine.supervised_motion
    p['continuation']['started']=time.monotonic()-181
    h.due_trial()
    assert h.engine.supervised_motion is None and not h.sender.held
    assert any('startup time budget' in message for message in h.notices)


def test_destination_uses_same_session_planning_scope_and_stops(h,nav_module):
    assets=configure(h,nav_module);start(h);h.due_trial()
    e=h.engine;seen=[];tick=h.tick
    def observed_tick():
        tick();p=e.route_trial
        if p is not None and p.get('policy') is not None and not seen:
            d=p['policy'].declaration;driver=p['driver'];cal=driver.session.runner.height_calibration
            assert d.scope=='destination_travel' and d.maximum_seconds==1500.
            assert d.maximum_steps==3000 and d.maximum_total_hold==600.
            assert cal.valid_until_monotonic>time.monotonic()+1500.
            assert p['continuation']['destination'] is assets
            assert len(p['plan'].route.segments)==2
            assert p['plan'].route.segments[-1].end[:2]==assets.goal_xy
            assert not e.last_motion_collection_result['real_client_accepted']
            seen.append(True)
    h.tick=observed_tick
    record=finish(h,timeout=50.)
    assert seen and record['scope']=='destination_travel',h.notices
    assert record['outcome']=='arrived',(record['reason'],record['route']['reason'],h.notices)
    assert record['route']['outcome']=='arrived' and record['route']['steps']
    assert record['destination']['kind']=='synthetic_fixture_destination'
    assert e.cancelled and h.observer_closed and not h.sender.held
    assert e.live_zone_tracker.lease is None


def test_f9_during_destination_down_releases_and_does_not_resume(h,nav_module,monkeypatch):
    configure(h,nav_module);fired=[]
    def stop():
        p=h.engine.route_trial
        if p is not None and p.get('driver') is not None and p['driver'].session.phase=='stepping' and not fired:
            fired.append(True);h.engine.stop_action('F9 during destination DOWN')
    after_down(monkeypatch,stop)
    start(h);h.due_trial();record=finish(h,timeout=35.)
    assert fired and record['scope']=='destination_travel' and record['outcome']=='stopped'
    assert h.engine.cancelled and h.observer_closed and not h.sender.held
    assert h.engine.live_zone_tracker.lease is None
    count=len(h.events);h.tick();h.drain();assert len(h.events)==count
