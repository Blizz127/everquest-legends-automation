"""Actual retained owner engine and pipe sender; all game feedback is synthetic."""
import time
from types import SimpleNamespace

import pytest

from eql_automation.bsp_volume import BspVolumeView
from eql_automation.current_route_start import CurrentStartPlanner,encoded
from eql_automation.owner_crossing_assets import CrossingDestinationAssets
from eql_automation.owner_route_trial import CROSSING_JOB
from eql_automation.zone_line import ExpectedZoneLine
from test_destination_route import nav_module
from test_motion_collection import retained
from test_owner_route_trial import h,finish
from test_owner_destination import configure as configure_destination
from test_route_step_sender import after_down


def configure(h,nav_module,retained,monkeypatch,*,stop=None,wrong_zone=False):
    old=configure_destination(h,nav_module);p=old.planner
    p.ground.areas[1]=4
    old.navigation_mesh.area[1]=4
    bsp=BspVolumeView(SimpleNamespace(nodes=((1.,0.,0.,-220.,0,2,3),
        (0.,0.,0.,0.,1,0,0),(0.,0.,0.,0.,2,0,0)),labels_by_region={0:{'zoneline'}}),
        region_count=2,wld_sha256=p.pins[2])
    planner=CurrentStartPlanner(mesh=p.mesh,ground=p.ground,source=p.source,static=p.static,bsp=bsp,
        zone_short_name=p.zone,expected_zone_id=p.zone_id,expected_zone_name=p.zone_name,
        mesh_sha256=p.pins[0],source_archive_sha256=p.pins[1],source_wld_sha256=p.pins[2],
        static_inventory_sha256=p.pins[3])
    line=ExpectedZoneLine('synthetic-owner-crossing',p.zone,*p.pins[:3],bsp.inventory_sha256,
        'e'*64,'DRNTP00255000004_ZONE',4,(1,),(0,))
    assets=CrossingDestinationAssets(planner,old.navigation_mesh,old.goal_xy,'Synthetic crossing',
        encoded(dict(kind='synthetic_source_crossing')),line,'Clan Crushbone')
    h.crossing_loading[0]=lambda:assets
    e=h.engine
    (h.game/'Resources/ZoneNames.txt').write_text('54^Fixture^0^0\n58^Clan Crushbone^0^0\n59^Wrong Zone^0^0\n')
    e._close_zone_tracker();e._service_zone_tracker()
    h.append('You have entered Fixture.');e._service_zone_tracker()
    h.crossing_seen=[];h.crossing_loaded=False;h.crossing_stopped=False
    original_read=retained[0].read_log
    from rotation_core import LogTail
    e.tail=LogTail(h.log)
    def read():
        # Enable the actual inherited log path once the new corridor owns the
        # reader; earlier fixture startup intentionally stubs unrelated logs.
        if e.route_trial is not None and e.route_trial.get('corridor_runtime') is not None:
            return original_read(e)
    e.read_log=read
    def down():
        pending=e.route_trial
        runtime=None if pending is None else pending.get('corridor_runtime')
        if runtime is None:return
        c=runtime.corridor
        if not h.crossing_seen:
            # Pin the inherited log tail to now, so old synthetic setup entries
            # do not replay as transitions in that independent legacy reader.
            e.tail.poll()
            h.crossing_seen.append(runtime)
        if stop=='down' and c.phase=='pulsing' and not h.crossing_stopped:
            h.crossing_stopped=True;e.stop_action('F9 during crossing DOWN');return
        if c.phase=='pulsing' and c.touches_line and not h.crossing_loaded:
            h.crossing_loaded=True
            h.append('LOADING, PLEASE WAIT...')
            h.append('You have entered '+('Wrong Zone' if wrong_zone else 'Clan Crushbone')+'.')
            e.read_log()
        elif c.phase in ('source_positions','await_arrival'):
            collector=c.arrival.source_collector or c.arrival.collector
            if collector is not None and collector.phase=='requesting':
                if stop==c.phase and not h.crossing_stopped:
                    h.crossing_stopped=True;e.stop_action('F9 during '+c.phase);return
                if c.phase=='await_arrival':h.append('Your Location is -12, 34, 5')
                else:h.append('Your Location is '+', '.join(f'{v:.2f}' for v in h.point))
    after_down(monkeypatch,down)
    import eql_automation.owner_crossing_runtime as runtime_module
    pulse=runtime_module.run_checked_corridor_step
    def step(*args,**kwargs):
        result=pulse(*args,**kwargs)
        runtime=e.route_trial['corridor_runtime']
        if not h.crossing_loaded:h.apply(runtime.corridor.receipt.key_code,runtime.corridor.receipt)
        return result
    monkeypatch.setattr(runtime_module,'run_checked_corridor_step',step)
    return assets


def start(h):
    e=h.engine;e.post(CROSSING_JOB,{'open_flat_clear':True});e.handle_job(*e.jobs.get_nowait())


def test_owner_crossing_calibrates_travels_and_stops_after_fresh_arrival(h,nav_module,retained,monkeypatch):
    configure(h,nav_module,retained,monkeypatch)
    start(h);h.due_trial();record=finish(h,timeout=80.)
    assert record is not None,h.notices
    assert record['outcome']=='arrived',(record['reason'],h.notices)
    assert h.crossing_loaded and len(record['startup_pairs'])==3
    result=record['crossing']
    assert result['outcome']=='complete' and not result['ordinary_route_driver_used']
    assert result['arrival']['positions']['outcome']=='complete'
    assert h.crossing_seen[0].corridor.arrival.collector.second.zone_id==58
    assert h.engine.route_session_driver is None and h.engine.cancelled
    assert h.observer_closed and not h.sender.held and h.engine.live_zone_tracker.lease is None
    assert any(event=='owner_crossing_transition_seen' for event,_ in h.traces)
    before=len(h.events);h.tick();h.drain();assert len(h.events)==before


@pytest.mark.parametrize('stop',['down','source_positions','await_arrival'])
def test_f9_cancels_owner_crossing_and_never_restarts(h,nav_module,retained,monkeypatch,stop):
    configure(h,nav_module,retained,monkeypatch,stop=stop)
    start(h);h.due_trial();record=finish(h,timeout=80.)
    assert h.crossing_stopped and record['outcome']=='stopped',(record,h.notices)
    assert not h.sender.held and h.engine.cancelled and h.observer_closed
    assert h.engine.live_zone_tracker.lease is None and h.engine.route_session_driver is None
    before=len(h.events);h.tick();h.drain();assert len(h.events)==before


def test_wrong_destination_stops_inherited_owner_log_path(h,nav_module,retained,monkeypatch):
    configure(h,nav_module,retained,monkeypatch,wrong_zone=True)
    start(h);h.due_trial();record=finish(h,timeout=80.)
    assert h.crossing_loaded and record['outcome']=='stopped',(record,h.notices)
    assert not h.sender.held and h.engine.cancelled and h.observer_closed


def test_loading_before_source_hotbutton_prevents_location_down(h,nav_module,retained,monkeypatch):
    configure(h,nav_module,retained,monkeypatch)
    import eql_automation.owner_crossing_runtime as runtime_module
    send=runtime_module.send_location_hotkey;seen=[]
    def loading(*args,**kwargs):
        c=h.engine.route_trial['corridor_runtime'].corridor
        assert c.phase=='source_positions'
        h.drain();before=len(h.events)
        h.append('LOADING, PLEASE WAIT...');h.engine.read_log()
        try:return send(*args,**kwargs)
        finally:
            h.drain();seen.append(h.events[before:])
    monkeypatch.setattr(runtime_module,'send_location_hotkey',loading)
    start(h);h.due_trial();record=finish(h,timeout=80.)
    assert seen and not any(kind==1 and value==1 for batch in seen for kind,key,value in batch)
    assert record['outcome']=='stopped' and not h.sender.held
