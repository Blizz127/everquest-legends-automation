"""Real location-hotkey pipe, synthetic contact arrival and game replies."""
import time
import pytest

from test_source_motion import f,legacy
from test_motion_collection import retained
from test_owner_journey_runtime import h
from test_camp_contact_checkpoint import contact_checkpoint
from test_owner_camp_position import camp,finish
from test_owner_camp_position import test_stop_after_second_down_releases_key_before_returning_reader

pytestmark=pytest.mark.parametrize('f',['contact_preflight'],indirect=True)


@pytest.fixture
def checkpoint(contact_checkpoint):
    # Contact feedback used a synthetic advancing clock; the retained owner
    # engine/pipe now runs wall time. Let it reach that history before polling
    # the same reader, whose monotonic cursor must never be rolled backward.
    time.sleep(max(0.,contact_checkpoint.now-time.monotonic()+.01))
    return contact_checkpoint


def test_first_recovery_on_contact_resumes_stationary_camp_without_probe(camp,monkeypatch):
    h=camp;e=h.engine;session=e.camp_session
    append=h.position_reply
    h.position_reply=lambda:append(y=3.6,z=2.79)
    monkeypatch.setattr(e,'_camp_probe_plan',lambda p:pytest.fail('Contact entered ordinary probe provider'))
    h.recovered();finish(h)
    assert e.camp_session is session and session.phase=='select',h.notices
    assert h.scope_journey.height_check_done and h.floor.valid
    record=e.camp_position_last_result
    assert record['contact']['original_raw_z_minus_source_z']==2.5
    assert not record['contact']['old_calibration_renewed'] and 'height' not in record
    assert not record['relocation_available'] and not record['movement_sent']
    assert not h.commands and not e.sender.held and e.live_zone_tracker.lease is None
    assert h.collection_replies==[0,1]
    assert [v for v in h.events if v[0]==1 and v[2]==1]==[(1,62,1)]*2
    assert all(kind!=1 or key==62 for kind,key,value in h.events)
    before=list(h.events);h.recovered(kills=2);h.drain()
    assert e.camp_position is None and h.events==before and session.phase=='select'
