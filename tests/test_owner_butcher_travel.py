"""Butcher owner cancellation through the existing pipe-backed helper."""
from test_motion_collection import retained
from test_owner_journey_runtime import h, start
from test_owner_source_travel import configure
from test_owner_route_trial import finish


def test_butcher_f9_during_movement_releases_without_starting_camp(h,monkeypatch):
    configure(h,monkeypatch,stop='movement',destination_id='newbie-hills')
    start(h,'newbie-hills');h.due_trial();record=finish(h,timeout=80.)
    assert h.source_stopped and record['outcome']=='stopped',h.notices
    assert not h.sender.held and h.observer_closed and not h.commands
    assert h.engine.camp_session is None and h.engine.live_zone_tracker.lease is None
    before=len(h.events);h.tick();h.drain();assert len(h.events)==before
