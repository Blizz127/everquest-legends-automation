"""Explicit camp observation provenance, source ledger and driver; synthetic positions."""
from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from eql_automation.camp_floor_checkpoint import CampFloorCheckpoint
from eql_automation.camp_source_observer import CampSourceObserver
from eql_automation.fixed_route_follower import RouteHalt
from eql_automation.observed_height import height_record,current_height_allowed
from eql_automation.source_motion import SourceReceiptLedger
from eql_automation.source_walk_driver import SourceWalkDriver,SourceWalkCommand
from eql_automation.uinput_watchdog import PulseReceipt
from test_camp_route_preparation import route,fresh
from test_camp_probe_preparation import probe
from test_camp_floor_checkpoint import checkpoint
from test_source_motion import f
from test_route_floor_commit import legacy


@pytest.fixture
def adopted(route):
    h=route;p=h.route;p.prepare();start=fresh(h)
    h.source_mode='camp_route';h.source_generation=1;h.source_expiry=h.now+60.
    def scope():
        h.lease.check()
        if h.clock()>h.source_expiry:raise ValueError('Original scope expired')
    h.observer_options=dict(scope_check=scope,mode_reader=lambda:h.source_mode,
        generation_reader=lambda:h.source_generation,generation=1,
        expires_at=h.source_expiry,walk_half_width=.25,stop_lock=h.route_tx.lock,route_bounds=p.bounds)
    h.camp_observer=CampSourceObserver(p,start,**h.observer_options)
    return h


def observe(h,*,x=4.5,y=2.):
    h.now+=.2
    return h.camp_observer.observe(h.position(x=x,y=y),checked_chain=h.camp_observer.initial_floor_chain)


def start_ledger(h,legacy):
    o=h.camp_observer;p=h.route;h.source_release=h.now
    first=observe(h);h.now+=.3;second=observe(h)
    l=SourceReceiptLedger(o,terrain=o.terrain,static=p.checkpoint._static,bsp=p.checkpoint._bsp,
        bounds=o.planning_bounds,installed_model=p.checkpoint._model,legacy=legacy,
        motion=legacy.Motion(run_speed=10.,turn_rate=170.,right_sign=1,turn_latency=.005,back_speed=0.),
        heading=90.,stop_lock=h.route_tx.lock)
    l.start(first,second,released_at=h.source_release)
    return l


def test_new_observer_uses_fresh_height_and_starts_existing_source_driver(adopted,legacy):
    h=adopted;o=h.camp_observer;p=h.route
    assert not hasattr(o,'initial') and p.phase=='observing'
    assert o.calibration.measured_height_sha256==p.start.height.sha256
    assert o.calibration.measured_pair_expires_at==p.start.expires_at
    assert not current_height_allowed(o.calibration,mode='measurement')
    l=start_ledger(h,legacy);driver=SourceWalkDriver(l);action=driver.next_action()
    assert type(action) is SourceWalkCommand and action.kind=='forward'
    assert action.target==(6.,2.,.2) and action.reference is l.reference
    assert h.now>p.start.expires_at  # Height correspondence is distinct from fresh position.
    assert l.reference.raw_fix.log_line_seq>o.calibration.last_calibration_log_line_seq
    assert h.drain_events()==()


def test_source_motion_acknowledges_new_camp_observer_and_recaptures_arrival(adopted,legacy):
    h=adopted;o=h.camp_observer;l=start_ledger(h,legacy)
    geometry=l.prepare('forward');ticket=l.stage(geometry,requested_seconds=.02)
    at=ticket.proposed_at;h.now=at+.026
    seal=l.seal_release(ticket,PulseReceipt(103,.02,at+.001,at+.002,at+.024,at+.025,'elapsed'))
    h.now+=.2;first=l.observe_reply(seal,h.position(x=4.7))
    h.now+=.5;second=l.observe_reply(seal,h.position(x=4.7))
    ack=l.acknowledge_stopped(seal,first,second)
    assert ack.reference.package_xyz==(4.7,2.,.2) and l.steps==1
    reached=CampFloorCheckpoint(l)
    record=reached.snapshot(include_evidence=True)['evidence']['historical_height']
    assert record['format']=='eql-camp-source-height-v1'
    assert record['second']['log_line_seq']==o.calibration.last_calibration_log_line_seq
    assert json.loads(json.dumps(height_record(o.calibration)))['live_verified'] is False
    assert not reached.snapshot()['input_authorized'] and h.drain_events()==()


def test_route_start_pair_cannot_be_replayed_as_issued_startup(adopted):
    h=adopted;o=h.camp_observer
    with pytest.raises(ValueError,match='replayed'):
        o.observe(h.route.start.height.second,checked_chain=o.initial_floor_chain)
    first=observe(h)
    with pytest.raises(ValueError):o.validate(replace(first),o.initial_floor_chain)


@pytest.mark.parametrize('fault',('assist','generation','deadline','lease','ancestor','height','width','floor','start'))
def test_observer_stops_when_scope_or_measured_provenance_changes(adopted,fault):
    h=adopted;o=h.camp_observer
    if fault=='assist':h.source_mode='assist'
    elif fault=='generation':h.source_generation+=1
    elif fault=='deadline':h.now=h.source_expiry+.01
    elif fault=='lease':h.lease.release()
    elif fault=='ancestor':h.route_tx.cancel('F9 ancestor')
    elif fault=='height':object.__setattr__(o.calibration,'raw_z_minus_source_z',3.)
    elif fault=='width':o._width=5.
    elif fault=='floor':o.initial_floor_chain.seed_evidence_sha256='a'*64
    else:object.__setattr__(o.start,'expires_at',o.start.expires_at+2.)
    with pytest.raises(ValueError):o.check()
    assert o.cancelled


def test_start_adoption_is_single_use_and_does_not_renew_age(adopted):
    h=adopted;expiry=h.route.start.expires_at
    with pytest.raises(ValueError):
        CampSourceObserver(h.route,h.route.start,**h.observer_options)
    assert h.camp_observer.calibration.measured_pair_expires_at==expiry
    with pytest.raises(ValueError):h.camp_observer.check()


def test_classifier_callback_cannot_cancel_ancestor_after_full_scan(adopted,monkeypatch):
    h=adopted;o=h.camp_observer;p=h.route;checked=[]
    prepare_check=p.check
    def checked_preparation(*args,**kwargs):
        result=prepare_check(*args,**kwargs);checked.append(True);return result
    monkeypatch.setattr(p,'check',checked_preparation)
    classify=type(o.policy).check_classifier
    def cancelled(policy):
        result=classify(policy)
        if checked:h.route_tx.cancel('Ancestor stopped in final classifier callback')
        return result
    monkeypatch.setattr(type(o.policy),'check_classifier',cancelled)
    with pytest.raises(ValueError):o.check()
    assert o.cancelled and h.route_tx.phase=='stopped'


def test_new_start_must_still_be_fresh_when_adopted(route):
    h=route;p=h.route;p.prepare();start=fresh(h);h.now=start.expires_at+.01
    with pytest.raises(ValueError):
        CampSourceObserver(p,start,scope_check=lambda:None,mode_reader=lambda:'camp_route',
            generation_reader=lambda:1,generation=1,expires_at=h.now+60.,
            walk_half_width=.25,stop_lock=h.route_tx.lock,route_bounds=p.bounds)
    assert p.phase=='stopped'


def test_long_source_trip_keeps_its_original_deadline(route):
    h=route;p=h.route;p.prepare();start=fresh(h);expires=h.now+1000.
    observer=CampSourceObserver(p,start,scope_check=lambda:None,mode_reader=lambda:'camp_route',
        generation_reader=lambda:1,generation=1,expires_at=expires,
        walk_half_width=.25,stop_lock=h.route_tx.lock,route_bounds=p.bounds)
    assert observer.calibration.valid_until_monotonic==expires
    h.now=expires+.01
    with pytest.raises(ValueError):observer.check()
    assert observer.cancelled


@pytest.mark.parametrize('provider',('scope','mode','generation'))
def test_slow_final_provider_cannot_adopt_an_expired_start(route,provider):
    h=route;p=h.route;p.prepare();start=fresh(h);calls=[]
    def scope():
        if p.phase=='observing':
            calls.append(1)
            if provider=='scope' and len(calls)==2:h.now+=.6
    def mode():
        if provider=='mode':h.now+=.6
        return 'camp_route'
    def generation():
        if provider=='generation':h.now+=.6
        return 1
    with pytest.raises(ValueError,match='expired'):
        CampSourceObserver(p,start,scope_check=scope,mode_reader=mode,
            generation_reader=generation,generation=1,expires_at=h.now+60.,
            walk_half_width=.25,stop_lock=h.route_tx.lock,route_bounds=p.bounds)
    assert p.phase=='stopped'


def test_ledger_rejects_a_different_stop_lock(adopted,legacy):
    import threading
    h=adopted;o=h.camp_observer;p=h.route
    with pytest.raises(ValueError,match='exact geometry and stop lock'):
        SourceReceiptLedger(o,terrain=o.terrain,static=p.checkpoint._static,bsp=p.checkpoint._bsp,
            bounds=o.planning_bounds,installed_model=p.checkpoint._model,legacy=legacy,
            motion=legacy.Motion(run_speed=10.,turn_rate=170.,right_sign=1,turn_latency=.005,back_speed=0.),
            heading=90.,stop_lock=threading.RLock())
    l=start_ledger(h,legacy);l.lock=threading.RLock()
    with pytest.raises(RouteHalt):l._check()


@pytest.mark.parametrize('fault',(None,'no_tightening','speed_changed','actual_hold_changed'))
def test_probe_hold_bounds_need_explicit_tighter_route_requests(route,legacy,fault):
    from eql_automation.camp_route_preparation import CampRoutePreparation
    h=route;old=h.route
    probe_bounds=replace(old.bounds,maximum_requested_hold=.15,maximum_actual_hold=.18)
    p=h.route=CampRoutePreparation(old.checkpoint,old.height,old.lease,
        **dict(h.route_options,bounds=probe_bounds))
    p.prepare();start=fresh(h)
    bounds=replace(probe_bounds,record_id='explicit-onward-request-limit',maximum_requested_hold=.1)
    if fault=='no_tightening':bounds=probe_bounds
    elif fault=='speed_changed':bounds=replace(bounds,forward_speed_upper_bound=bounds.forward_speed_upper_bound+1.)
    elif fault=='actual_hold_changed':bounds=replace(bounds,maximum_actual_hold=.19)
    options=dict(scope_check=lambda:None,mode_reader=lambda:'camp_route',generation_reader=lambda:1,
        generation=1,expires_at=h.now+60.,walk_half_width=.25,stop_lock=h.route_tx.lock,route_bounds=bounds)
    if fault:
        with pytest.raises(ValueError,match='only tighten'):CampSourceObserver(p,start,**options)
    else:
        h.camp_observer=CampSourceObserver(p,start,**options)
        ledger=start_ledger(h,legacy)
        assert ledger.bounds is bounds and probe_bounds.maximum_requested_hold==.15
        assert ledger.bounds.maximum_requested_hold==.1


def test_new_camp_observer_runs_actual_watchdog_pipe_and_confirms_movement(adopted,legacy):
    import time
    from eql_automation.scene_log_veto import SceneLogVeto
    from eql_automation.supervised_source import SupervisedSourcePolicy
    from eql_automation.source_step_sender import run_checked_source_step
    h=adopted;o=h.camp_observer;p=h.route
    # The fixture built real ledgers using a synthetic monotonic clock. Wait for
    # that small offset before switching to actual time; never retimestamp fixes.
    delay=max(0.,h.now-time.monotonic());assert delay<10.
    time.sleep(delay+.02);h.real=True
    l=SourceReceiptLedger(o,terrain=o.terrain,static=p.checkpoint._static,bsp=p.checkpoint._bsp,
        bounds=o.planning_bounds,installed_model=p.checkpoint._model,legacy=legacy,
        motion=legacy.Motion(run_speed=10.,turn_rate=170.,right_sign=1,turn_latency=.005,back_speed=0.),
        heading=90.,stop_lock=h.route_tx.lock)
    released=h.clock();time.sleep(.13);h.now=h.clock()
    first=o.observe(h.position(x=4.5),checked_chain=l.chain)
    time.sleep(.405);h.now=h.clock();second=o.observe(h.position(x=4.5),checked_chain=l.chain)
    l.start(first,second,released_at=released)
    old=h.policy
    veto=SceneLogVeto(h.reader.tail.path,expected_character='Probe',expected_server='private',
        cancel_generation=1,clock=h.clock)
    policy=SupervisedSourcePolicy(l,declaration=replace(old.declaration,
        route_sha256=o.itinerary.sha256,motion_record_id=l.bounds.calibration_record_id,
        planning_bounds_record_id=l.bounds.record_id),gate=h.gate,
        owner_input=old.owner_input,log_veto=veto,expected_window=old.window,
        topology_generation=old.topology,check_current=o.check)
    seal=run_checked_source_step(h.sender,l,policy=policy,kind='forward',requested_seconds=.02,
        command_state_clear=lambda:True,pump=lambda:None)
    time.sleep(.13);h.now=h.clock();first=l.observe_reply(seal,h.position(x=4.7))
    time.sleep(.405);h.now=h.clock();second=l.observe_reply(seal,h.position(x=4.7))
    ack=l.acknowledge_stopped(seal,first,second)
    events=h.drain_events()
    assert (1,103,1) in events and (1,103,0) in events and not h.sender.held
    assert ack.reference.package_xyz==(4.7,2.,.2) and not ack.real_client_accepted
