"""Actual source transactions and fitter; deterministic log/receipt simulation."""
from types import SimpleNamespace

import pytest

from eql_automation.camp_probe_calibration import reduce_camp_probes
from eql_automation.camp_route_preparation import CampRoutePreparation
from eql_automation.native_region_policy import encoded
from eql_automation.owner_camp_plan_provider import checked_fresh_fit
from eql_automation.source_itinerary import SourceItineraryGuide,SourceWalkHint
from test_camp_probe_calibration import completed,fitter
from test_camp_probe_continuation import new_height
from test_camp_probe_preparation import probe
from test_camp_probe_transaction import pair
from test_camp_floor_checkpoint import checkpoint
from test_source_motion import f
from test_route_floor_commit import legacy


@pytest.fixture
def ready_fit(completed,fitter):
    h=completed;r=h.runtime
    calibration=dict(status='conditional',estimate=reduce_camp_probes(r,legacy=fitter,
        record_id='camp-'+r.results[-1].sha256))
    p=SimpleNamespace(runtime=r,floor=r.root.checkpoint,
        calibration_seal=(calibration,encoded(calibration),r.reference,tuple(r.transactions),tuple(r.results)))
    xy=r.reference._result.package_xyz[:2]
    guide=SourceItineraryGuide('crushbone',r.reference._terrain.wld_sha256,
        r.reference._static.inventory_sha256,'f'*64,.1,6.,(5.,8.),(SourceWalkHint(xy,(5.,8.)),))
    r.prepare_route(guide)
    height=new_height(h,r.reference)
    preparation=CampRoutePreparation(r.reference,height,r.lease,guide=guide,bounds=r.root.bounds,
        owner_binding=r.root.owner_binding,binding_reader=r.root.binding_reader,
        clock=r.clock,local_wall_clock=r.wall)
    r.route_preparation=r._route_preparation=preparation
    preparation.prepare()
    released=h.now;a,b,baseline=pair(h,x=xy[0],y=xy[1])
    r.route_start=preparation.observe_start(a,b,minimum_log_seq=baseline,released_at=released)
    r.collector=None;r.phase='route_ready'
    return h,p,calibration


@pytest.mark.parametrize('f',['compact_long'],indirect=True)
@pytest.mark.parametrize('completed',['provider'],indirect=True)
def test_fresh_fit_survives_new_route_pairs_but_cannot_be_edited_or_reused(ready_fit):
    h,p,calibration=ready_fit;r=h.runtime
    old_confirmation=r.results[-1].second
    assert h.reader.latest is r.route_start.height.second and h.reader.latest is not old_confirmation
    assert h.now>r.results[-1].expires_at
    fit=checked_fresh_fit(p,r,calibration)
    assert fit['estimate']['run_speed']==pytest.approx(10.,abs=.05)
    assert fit['estimate']['right_sign']==1
    assert not fit['current_heading_verified'] and h.drain_events()==()
    saved=fit['estimate']['final_heading'];fit['estimate']['final_heading']=180.
    with pytest.raises(ValueError,match='sealed'):checked_fresh_fit(p,r,calibration)
    fit['estimate']['final_heading']=saved
    assert checked_fresh_fit(p,r,calibration) is fit
    h.now=r.route_start.expires_at+.01
    with pytest.raises(ValueError):checked_fresh_fit(p,r,calibration)


@pytest.mark.parametrize('f',['compact_long'],indirect=True)
@pytest.mark.parametrize('completed',['provider'],indirect=True)
def test_conditional_speed_cannot_expand_preserved_hypotheses(ready_fit):
    h,p,calibration=ready_fit;r=h.runtime
    speed=calibration['estimate']['conditional_intervals']['speed']
    calibration['estimate']['conditional_intervals']['speed']=(speed[0],r.root.bounds.forward_speed_upper_bound+1.)
    # Simulate a producer returning a different (but still conditional) fit.
    # Sealing it must not silently increase the retained geometry envelope.
    p.calibration_seal=(calibration,encoded(calibration),*p.calibration_seal[2:])
    with pytest.raises(ValueError,match='envelope'):checked_fresh_fit(p,r,calibration)
    assert h.drain_events()==()


@pytest.mark.parametrize('f',['compact_long'],indirect=True)
@pytest.mark.parametrize('completed',['provider'],indirect=True)
def test_route_start_callback_cannot_replace_the_sealed_sequence(ready_fit,monkeypatch):
    h,p,calibration=ready_fit;r=h.runtime
    check=r.route_preparation.check_start
    def replace_sequence(start):
        result=check(start);r.results=list(reversed(r.results));return result
    monkeypatch.setattr(r.route_preparation,'check_start',replace_sequence)
    with pytest.raises(ValueError,match='adoption'):checked_fresh_fit(p,r,calibration)
    assert h.drain_events()==()


@pytest.mark.parametrize('f',['compact_long'],indirect=True)
@pytest.mark.parametrize('completed',['provider'],indirect=True)
def test_long_trip_budget_does_not_extend_probe_measurement_window(completed):
    h=completed;r=h.runtime
    assert r.maximum_seconds==1500.
    h.now=r.started+121.
    r._check_scope()  # Completed probes may retain the original route budget.
    r.index=6;r.phase='collect_start'
    with pytest.raises(ValueError,match='budget expired'):r._check_scope()
    r.index=7;r.phase='complete';h.now=r.started+1500.01
    with pytest.raises(ValueError,match='budget expired'):r._check_scope()
