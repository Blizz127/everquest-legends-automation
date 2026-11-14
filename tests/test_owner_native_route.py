"""Owner Crushbone pipeline, real pipe sender and synthetic client feedback."""
from types import SimpleNamespace

from eql_automation.bsp_volume import BspVolumeView
from eql_automation.current_route_start import CurrentStartPlanner
from eql_automation.native_region_policy import NativeZeroRegionTrialPolicy
from test_client_classification import view
from test_installed_region_model import files
from test_motion_collection import retained
from test_native_region_policy import MISSING
from test_owner_route_trial import h, finish


def configure(h,monkeypatch):
    model=files(h.game,monkeypatch)
    old=h.loader
    bsp=BspVolumeView(SimpleNamespace(nodes=MISSING,labels_by_region={}),
        region_count=3,wld_sha256=old.pins[2])
    classifier=view(MISSING,wld_pin=old.pins[2])
    policy=NativeZeroRegionTrialPolicy(*old.pins,bsp.inventory_sha256,
        classifier.inventory_sha256,classifier)
    planner=CurrentStartPlanner(mesh=old.mesh,ground=old.ground,source=old.source,
        static=old.static,bsp=bsp,zone_short_name='crushbone',expected_zone_id=58,
        expected_zone_name='Fixture',mesh_sha256=old.pins[0],source_archive_sha256=old.pins[1],
        source_wld_sha256=old.pins[2],static_inventory_sha256=old.pins[3],region_policy=policy)
    planner.installed_region_model=model
    h.loading[0]=lambda:planner
    h.engine._close_zone_tracker()
    (h.game/'Resources/ZoneNames.txt').write_text('58^Fixture^0^0\n')
    h.engine._service_zone_tracker();h.append('You have entered Fixture.');h.engine._service_zone_tracker()
    return planner


def test_owner_native_route_calibrates_plans_measures_and_moves(h,monkeypatch):
    configure(h,monkeypatch)
    h.start_trial();h.due_trial();record=finish(h)
    assert record is not None and record['outcome']=='arrived',(record,h.notices)
    assert record['geometry']['format']=='eql-current-start-geometry-v2'
    assert record['geometry']['bsp']['reason']=='missing_bsp_child'
    assert not record['geometry']['bsp']['candidate']
    assert record['route']['steps'] and record['installed_region_model']['installed_file_hashes_verified']
    assert not record['real_client_accepted'] and not h.sender.held
    assert h.engine.cancelled and h.observer_closed and h.engine.live_zone_tracker.lease is None


def test_installed_model_change_stops_before_calibration_down(h,monkeypatch):
    configure(h,monkeypatch)
    h.start_trial();h.drain();before=len(h.events)
    (h.game/'EQGraphics.dll').write_bytes(b'changed model')
    h.due_trial();finish(h);h.drain()
    assert not any(kind==1 and value==1 for kind,key,value in h.events[before:])
    assert h.engine.supervised_motion is None and not h.sender.held
    assert any('region-model file changed' in str(message) for message in h.notices)
