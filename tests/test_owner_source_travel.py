"""Full retained helper handoff; synthetic geometry/game with actual pipe input."""
import time
from hashlib import sha256

import pytest

from eql_automation.current_route_start import encoded
from eql_automation.owner_route_trial import SOURCE_JOB
from eql_automation.owner_source_assets import SourceDestinationAssets
from eql_automation.source_itinerary import SourceItineraryGuide, SourceWalkHint
from test_motion_collection import retained
from test_owner_native_route import configure as native
from test_owner_route_trial import h, finish
from test_route_step_sender import after_down


def configure(h, monkeypatch, *, stop=None,destination_id='slave-mines'):
    planner=native(h,monkeypatch)
    guide=SourceItineraryGuide('crushbone',planner.pins[2],planner.pins[3],'f'*64,
        1.2,6.,(400.,205.),(SourceWalkHint((400.,200.),(400.,204.)),))
    assets=SourceDestinationAssets(planner,guide,'Synthetic source destination',encoded(dict(synthetic=True,
        destination_id=destination_id,guide_sha256=sha256(encoded(guide.record())).hexdigest())),destination_id)
    h.source_loading[0]=lambda:assets
    e=h.engine;h.source_seen=[];h.source_stopped=False
    def down():
        p=e.route_trial;r=None if p is None else p.get('source_runtime')
        if r is None:return  # Earlier calibration/startup fixture callbacks remain.
        if not h.source_seen:h.source_seen.append(r)
        if stop=='movement' and any(key in h.sender.held for key in (103,105,106)):
            h.source_stopped=True;e.stop_action('F9 during source movement');return
        if r.collector is not None and r.collector.phase=='requesting':
            if stop=='location':
                h.source_stopped=True;e.stop_action('F9 during source location');return
            h.append('Your Location is '+', '.join(f'{v:.2f}' for v in h.point))
    after_down(monkeypatch,down)
    import eql_automation.owner_source_runtime as module
    pulse=module.run_checked_source_step
    def step(*args,**kwargs):
        result=pulse(*args,**kwargs);h.apply(result.receipt.key_code,result.receipt);return result
    monkeypatch.setattr(module,'run_checked_source_step',step)
    return assets


def start(h):
    e=h.engine;e.post(SOURCE_JOB,{'open_flat_clear':True});e.handle_job(*e.jobs.get_nowait())


def test_source_owner_calibrates_plans_observes_travels_and_cleans_up(h,monkeypatch):
    configure(h,monkeypatch)
    start(h);h.due_trial();record=finish(h,timeout=80.)
    assert record is not None, '\n'.join(map(str,h.notices))
    assert record is not None and record['outcome']=='arrived',(record,h.notices)
    assert record['format']=='eql-owner-source-travel-v1' and len(record['startup_pairs'])==3
    assert record['source_route']['phase']=='complete' and record['source_route']['completed_movements']>0
    assert record['source_itinerary'] and record['installed_region_model']['installed_file_hashes_verified']
    assert h.source_seen and not record['real_client_accepted']
    assert h.engine.cancelled and h.observer_closed and not h.sender.held
    assert h.engine.route_session_driver is None and h.engine.live_zone_tracker.lease is None
    before=len(h.events);h.tick();h.drain();assert len(h.events)==before


@pytest.mark.parametrize('stop',('movement','location'))
def test_source_owner_f9_releases_reader_and_never_restarts(h,monkeypatch,stop):
    configure(h,monkeypatch,stop=stop)
    start(h);h.due_trial();record=finish(h,timeout=80.)
    assert h.source_stopped and record['outcome']=='stopped',(record,h.notices)
    assert h.engine.cancelled and h.observer_closed and not h.sender.held
    assert h.engine.route_session_driver is None and h.engine.live_zone_tracker.lease is None
    before=len(h.events);h.tick();h.drain();assert len(h.events)==before


def test_source_owner_changed_installed_model_still_stops_before_route_down(h,monkeypatch):
    from eql_automation.owner_source_runtime import OwnerSourceRuntime
    configure(h,monkeypatch)
    tick=OwnerSourceRuntime.tick
    changed=[]
    def replace_model(runtime):
        if not changed:
            changed.append(True)
            (h.game/'EQGraphics.dll').write_bytes(b'changed after startup')
        return tick(runtime)
    monkeypatch.setattr(OwnerSourceRuntime,'tick',replace_model)
    start(h);h.due_trial();record=finish(h,timeout=80.)
    assert changed and record['outcome']=='stopped' and 'file changed' in record['reason']
    assert record['source_route']['completed_movements']==0 and not record['source_route']['executor_events']
    assert not h.sender.held and h.observer_closed and h.engine.live_zone_tracker.lease is None
