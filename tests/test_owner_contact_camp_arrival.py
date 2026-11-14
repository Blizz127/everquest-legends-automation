"""Contact token -> new camp replacement, virtual game/transport observations.

These exercise post-release engine ownership, not a live onward journey.
"""
import pytest

from eql_automation.camp_contact_checkpoint import CampContactCheckpoint
from eql_automation.camp_floor_checkpoint import CampFloorCheckpoint
from test_source_motion import f,legacy
from test_motion_collection import retained
from test_owner_journey_runtime import h
from test_owner_source_runtime import setup
from test_source_contact_itinerary import simulated_transport,simulated_finish
import test_owner_camp_arrival as ordinary

pytestmark=pytest.mark.parametrize('f',['contact_route'],indirect=True)


@pytest.fixture
def arrival(h,f,tmp_path,monkeypatch):
    f.checkpoint=CampFloorCheckpoint(f.ledger)
    feedback=((2.4,2.7),(2.8,2.7),(3.2,2.7),(3.6,2.79))
    r,_,state=setup(f,tmp_path,monkeypatch,scope='destination_travel',feedback=feedback)
    simulated_transport(f,r,state,feedback,monkeypatch);simulated_finish(f,r)
    receipt=r.completed_arrival;reached=CampContactCheckpoint(r.transfer,receipt)
    r.lease.release()
    h.engine.live_zone_tracker.clock=f.clock
    return ordinary.make_arrival(h,f,monkeypatch,reached,r,receipt)


def test_contact_camp_replacement_keeps_actual_arrival_and_reuses_input_observer(arrival):
    ordinary.test_arrival_replaces_camp_then_prepares_without_reusing_target_or_moving(arrival)


@pytest.mark.parametrize('mode',['F8','F9'])
def test_contact_camp_replacement_cancellation_during_transfer(arrival,mode):
    ordinary.test_owner_cancel_during_new_camp_setup_never_resumes_combat(arrival,'input_transfer',mode)
