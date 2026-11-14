"""Production plan provider; synthetic game/geometry and real watchdog pipe."""
from dataclasses import asdict,replace
from hashlib import sha256
import json
from types import SimpleNamespace

import pytest

import eql_automation.owner_camp_plan_provider as provider
from eql_automation.camp_motion_continuity import CampInputContinuity
from eql_automation.native_region_policy import encoded
from eql_automation.route_geometry import RouteMotionBounds
from eql_automation.source_itinerary import SourceItineraryGuide,SourceWalkHint
from test_owner_camp_level_recheck import ding
from test_owner_camp_position import camp
from test_owner_camp_standard_route import standard_execution,finish_standard
from test_camp_floor_checkpoint import checkpoint
from test_source_motion import f
from test_route_floor_commit import legacy
from test_motion_collection import retained
from test_owner_journey_runtime import h,start
from test_owner_source_travel import configure


@pytest.fixture
def annotation_file(tmp_path,monkeypatch):
    data=(b'P -426, -74, -17, 0, 0, 0, 2, L07-10_Slave_Mines\n'
          b'P 95, 78, 0, 0, 0, 0, 2, L13-17_North_Wall_and_Castle\n'
          b'P -106, -154, 16, 0, 0, 0, 2, L17-22_Throne_Room\n')
    (tmp_path/'crushbone_3.txt').write_bytes(data)
    monkeypatch.setitem(provider.DATA_PINS,'crushbone_3.txt',sha256(data).hexdigest())
    return tmp_path


def test_map_ranges_keep_current_camp_and_never_fill_unbuilt_level_gaps(annotation_file):
    root=annotation_file
    for level in (1,7,10,11,12,23,50):
        assert provider.choose_next_destination(root,'slave-mines',level) is None
    selected,evidence=provider.choose_next_destination(root,'slave-mines',13)
    assert selected.identifier=='north-wall'
    record=json.loads(evidence)
    assert record['level_hint']==[13,17] and record['observed_level']==13
    assert not record['live_suitability_verified'] and not record['label_z_used_for_floor']
    assert provider.choose_next_destination(root,'north-wall',17) is None
    for level in (18,20):
        selected,evidence=provider.choose_next_destination(root,'north-wall',level)
        assert selected.identifier=='throne-room' and json.loads(evidence)['level_hint']==[17,22]
    assert provider.choose_next_destination(root,'throne-room',20) is None
    assert provider.choose_next_destination(root,'throne-stair-landing',17) is None
    with pytest.raises(ValueError):provider.choose_next_destination(root,'slave-mines',True)
    (root/'crushbone_3.txt').write_text('changed')
    with pytest.raises(ValueError):provider.choose_next_destination(root,'slave-mines',13)


def test_butcher_level_increase_cannot_select_a_crushbone_route(tmp_path,monkeypatch):
    from eql_automation import butcher_assets
    data=b'P 650, -2700, 0, 0, 0, 0, 2, L01-04_Newbie_Hills\n'
    (tmp_path/'butcher_3.txt').write_bytes(data)
    monkeypatch.setitem(butcher_assets.DATA_PINS,'butcher_3.txt',sha256(data).hexdigest())
    for level in (1,4,5,7,10,13,18,20):
        assert provider.choose_next_destination(tmp_path,'newbie-hills',level) is None
    assert provider.choose_next_destination(tmp_path,'newbie-hills-stop',1) is None


def test_butcher_default_continuation_root_uses_its_own_copied_maps(monkeypatch):
    from pathlib import Path
    from eql_automation.camp_session import CampLevelAdvance
    advance=CampLevelAdvance(4,5,10,3)
    pending=SimpleNamespace(journey=SimpleNamespace(continue_camps=True,destination_id='newbie-hills'),
        level_advance=advance,generation=3,
        camp=SimpleNamespace(last_level_advance=advance,level_source='client_log',level=5))
    engine=SimpleNamespace(_camp_position_current=lambda p:None,settings=SimpleNamespace(level=5),
                           trace=lambda *a,**k:None)
    seen=[]
    monkeypatch.setattr(provider,'choose_next_destination',lambda root,*a:seen.append(root))
    assert provider.owner_camp_probe_plan(engine,pending) is None
    assert seen==[Path.home()/'.local/share/eql-automation/owner-route-data/butcher-camps-20261114']


def install_historical_basis(h):
    e=h.engine;j=e.journey;m=j.camp_motion;floor=j.arrival_floor
    historical=floor.snapshot(include_evidence=True)['evidence']
    # Synthetic arrival assumptions. Real producer keeps the owner's original
    # arrival bounds; this fixture's floor is deliberately much smaller.
    bounds=RouteMotionBounds('synthetic-arrival','synthetic-old-motion',
        .01,.1,.16,11.,.02,.01,2.,.01,.1,6.)
    basis={name:historical[name] for name in ('itinerary_sha256','floor_proof_sha256',
        'arrival_position','arrival_log_seq','arrival_received_at')}
    basis.update(format='eql-camp-arrival-motion-v1',bounds=asdict(bounds),
        calibration_record_id=bounds.calibration_record_id,arrival_heading_estimate=180.,
        motion={'run_speed':1.},current_heading_verified=False,current_motion_verified=False,
        movement_authorized=False)
    j.camp_motion=CampInputContinuity(m.observer,topology=m.topology,basis=encoded(basis),
        binding=m.binding,clock=m.clock,floor=floor)
    return bounds


def test_probe_bounds_preserve_assumptions_and_match_the_actual_arrival(camp):
    h=camp;old=install_historical_basis(h);j=h.engine.journey
    p=SimpleNamespace(monitor=j.camp_motion,floor=j.arrival_floor,journey=j,
        reader=j.arrival_floor._reader,result=SimpleNamespace(sha256='a'*64))
    bounds,evidence=provider.retained_probe_bounds(p)
    assert replace(bounds,record_id=old.record_id,maximum_requested_hold=old.maximum_requested_hold)==old
    assert bounds.maximum_requested_hold==.15
    record=json.loads(evidence)
    assert not record['current_motion_verified'] and record['original_bounds']==asdict(old)
    m=p.monitor;basis=json.loads(m.basis);basis['arrival_log_seq']+=1
    p.monitor=j.camp_motion=CampInputContinuity(m.observer,topology=m.topology,basis=encoded(basis),
        binding=m.binding,clock=m.clock,floor=p.floor)
    with pytest.raises(ValueError,match='arrival_log_seq'):provider.retained_probe_bounds(p)
    assert not h.events and not h.commands


@pytest.mark.parametrize('f',['compact_long'],indirect=True)
def test_production_plan_uses_fresh_fit_and_same_scope_through_route(camp,monkeypatch,legacy):
    h=camp;e=h.engine;standard_execution(h,monkeypatch,legacy)
    original_bounds=install_historical_basis(h)
    e.journey.continue_camps=e.journey._continue_camps=True
    ding(h,13);e.camp_session.preparation_due=False
    floor=e.journey.arrival_floor
    guide=SourceItineraryGuide('crushbone',floor._terrain.wld_sha256,
        floor._static.inventory_sha256,'f'*64,.1,6.,(5.,8.),
        (SourceWalkHint((4.,2.),(5.,8.)),))
    monkeypatch.setattr(provider,'choose_next_destination',lambda *a:
        (provider.destination_spec('north-wall'),encoded({'kind':'synthetic-next-destination'})))
    monkeypatch.setattr(provider,'load_source_guide',lambda *a:guide)
    def plan(p):
        result=provider.owner_camp_probe_plan(e,p)
        assert result.destination_id=='north-wall'
        execution=result.route_plan_factory
        def onward(runtime,calibration):
            # A callback cannot edit the freshly sealed numeric estimate.
            fit=calibration['estimate'];old=fit['estimate']['run_speed']
            fit['estimate']['run_speed']=1.
            with pytest.raises(ValueError,match='sealed'):execution(runtime,calibration)
            fit['estimate']['run_speed']=old
            result=execution(runtime,calibration)
            h.used_fit=fit['estimate']
            assert result.bounds.calibration_record_id==original_bounds.calibration_record_id
            assert result.bounds.maximum_requested_hold==.1
            assert result.motion.run_speed!=1. and result.heading!=180.
            return result
        return replace(result,route_plan_factory=onward)
    e._camp_probe_plan=plan
    p=finish_standard(h,camp_handoff=True)
    assert p.route_runtime.policy.log_veto is p.probe_log_veto
    assert p.route_runtime.policy.owner_input is p.monitor.observer
    assert p.route_runtime.policy.declaration.maximum_seconds<=1500.
    assert p.route_runtime.policy.declaration.owner_supervised_continuation is True
    assert p.route_runtime.policy.declaration.open_flat_clear is False
    assert p.probe_plan.bounds.forward_speed_upper_bound==original_bounds.forward_speed_upper_bound
    assert not json.loads(p.probe_plan.bounds_basis)['motion_bounds_verified']


def test_queued_continuation_choice_is_copied_and_stripped_before_motion_handler(h,monkeypatch):
    configure(h,monkeypatch);e=h.engine
    from eql_automation.owner_route_trial import SOURCE_JOB
    declaration=dict(open_flat_clear=True,destination_id='slave-mines',continue_camps=True)
    e.read_log();e.post(SOURCE_JOB,declaration);declaration['continue_camps']=False
    e.handle_job(*e.jobs.get_nowait())
    assert e.journey.continue_camps is True and e._owner_navigation_active()
    assert e.supervised_motion['declaration']=={'open_flat_clear':True}
    e.journey.continue_camps=False
    assert not e._owner_navigation_active()
    assert not h.events and not h.commands


@pytest.mark.parametrize('choice',(1,'yes',None))
def test_invalid_continuation_choice_never_starts_input(h,choice):
    e=h.engine
    from eql_automation.owner_route_trial import SOURCE_JOB
    e.post(SOURCE_JOB,dict(open_flat_clear=True,continue_camps=choice))
    e.handle_job(*e.jobs.get_nowait())
    assert e.journey is None and not h.events and not h.commands
