import time

import pytest

from eql_automation.map_zone_observer import MapZoneObservation
from eql_automation.owner_route_adapter import make_route_session_engine
import test_owner_location_hotkey_test as hotkey
from test_owner_location_hotkey_test import h, finish
from test_motion_collection import retained
from test_route_step_sender import after_down


@pytest.mark.parametrize('change', ['none','cancel','final_cancel','duplicate','logging','wrong_window','ocr_failure'])
def test_hotbutton_reply_can_bind_current_map_without_an_extra_key_or_old_zone(request, monkeypatch, change):
    original=hotkey.make_owner_nov12_engine
    def observe(engine,pending,*,still_current):
        still_current()
        if change=='cancel':engine.stop_action('F9 during OCR')
        elif change=='duplicate':state.append()
        elif change=='logging':state.append("Logging to 'eqlog.txt' is now *ON*.")
        elif change=='ocr_failure':raise ValueError('Map not visible')
        still_current()
        if change=='final_cancel':state.sample_hook=lambda:engine.stop_action('F9 during final observer callback')
        return MapZoneObservation(54,'The Greater Faydark',(1.,2.,3.),pending['fix'].raw_coordinates,
            time.monotonic(),time.monotonic(),'a'*64,43 if change=='wrong_window' else 42,
            (10,100),'b'*64,('The Greater Faydark','1','2','3'))
    monkeypatch.setattr(hotkey,'make_owner_nov12_engine',
        lambda *a,**kw:make_route_session_engine(original(*a,**kw),zone_observer=observe))
    state=request.getfixturevalue('h');engine=state.engine
    (state.game/'Resources').mkdir()
    (state.game/'Resources/ZoneNames.txt').write_text('54^The Greater Faydark^0^0\n')
    after_down(monkeypatch,state.append)
    state.start();state.due();result=finish(state)
    assert not state.sender.held and engine.cancelled and not engine.active
    assert [code for kind,code,value in state.events if kind==1 and value==1]==[62]
    reader=engine.live_zone_tracker.reader
    assert reader.latest is None
    if change=='none':
        assert reader.zone_id==54
        assert result['current_zone_observation']['status']=='observed'
        lease=engine.live_zone_tracker.acquire()
        assert lease.reader.latest is None  # Fresh route fixes still required.
        lease.release()
    else:
        assert reader.zone_id is None
        assert result.get('current_zone_observation',{}).get('status')!='observed'
