"""Zone identity survives current planning, height and source observations."""
from dataclasses import replace

import pytest

from eql_automation.camp_floor_checkpoint import CampFloorCheckpoint
from eql_automation.source_itinerary import SourceStepHint
from test_current_source_itinerary import fixture, run
from test_source_motion import f
from test_route_floor_commit import legacy


@pytest.mark.parametrize('fault', ('guide', 'reader', 'catalog', 'policy'))
def test_butcher_start_cannot_adopt_crushbone_identity(tmp_path, fault):
    context = fixture(tmp_path, 'butcher')
    if fault == 'guide': context.guide = replace(context.guide, zone='crushbone')
    elif fault == 'reader': context.reader.zone_id = 58
    elif fault == 'catalog': context.planner.zone_id = 58
    else: context.planner.region_policy = replace(context.planner.region_policy, zone='crushbone')
    with pytest.raises(ValueError): run(context)


def test_butcher_cannot_enable_crushbone_step_contacts(tmp_path):
    context = fixture(tmp_path, 'butcher')
    guide = replace(context.guide, operations=(SourceStepHint((4.,2.),(4.,3.),((10,0),),.5,1.),))
    with pytest.raises(ValueError, match='walking only'): guide.validate()


@pytest.mark.parametrize('f', ('butcher',), indirect=True)
def test_butcher_observer_and_retained_camp_floor_keep_same_zone(f):
    f.real=False; f.now=f.observer.last_at
    assert f.observer.calibration.zone_short_name == f.observer.policy.zone == 'butcher'
    assert f.observer.calibration.zone_id == f.reader.zone_id == 68
    checkpoint = CampFloorCheckpoint(f.ledger)
    checkpoint.check()
    assert checkpoint.snapshot(include_evidence=True)['evidence']['policy']['zone'] == 'butcher'
    f.reader.zone_id=58
    with pytest.raises(ValueError): checkpoint.check()
    assert not checkpoint.valid
    assert not f.drain_events()


@pytest.mark.parametrize('f', ('butcher',), indirect=True)
def test_butcher_final_callback_zone_change_revokes_observation(f):
    f.real=False; f.now=f.observer.last_at
    f.clock_hook=lambda:setattr(f.reader,'zone_id',58)
    with pytest.raises(ValueError):f.observer.check()
    assert not f.drain_events()
