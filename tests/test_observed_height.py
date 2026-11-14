"""Current height bootstrap using the real log reader; no game or device input."""
from dataclasses import replace
from datetime import datetime, timedelta
import json
from types import SimpleNamespace
import threading

import pytest

from eql_automation.fixed_route_follower import FixedRouteFollower, RouteHalt
from eql_automation.ground_observer import GroundObservationUnavailable
from eql_automation.location_log import LocationLogReader
from eql_automation.observed_height import measure_current_height, current_height_allowed
from eql_automation.route_floor_commit import RouteFloorCommit
from eql_automation.route_session import RouteSession
from test_ground_observer import fixture, ROUTE, GEOMETRY
from test_route_floor_commit import legacy, setup


@pytest.fixture
def current(tmp_path):
    observer, _, _, source = fixture()
    h = SimpleNamespace(observer=observer, source=source, now=100., mode='measurement',
        binding=(42,'Probe','private'), released=99.8)
    log = tmp_path/'eqlog_Probe_private.txt'; log.touch()
    zones = tmp_path/'ZoneNames.txt'; zones.write_text('54^Fixture^0^0\n')
    h.reader = LocationLogReader(log,zones,expected_character='Probe',expected_server='private')
    h.wall = lambda: datetime(2026,11,14,10)+timedelta(seconds=h.now-100.)
    def append(body):
        with log.open('a') as output:
            output.write(h.wall().strftime('[%a %b %d %H:%M:%S %Y] ')+body+'\n')
    h.append = append
    append('You have entered Fixture.'); h.reader.poll(now=h.now)
    def fix(z=2.7):
        append(f'Your Location is 2.00, 1.00, {z:.2f}')
        return h.reader.poll(now=h.now)[0]
    h.fix = fix
    h.first = fix(); h.now += .5; h.second = fix()
    h.options = lambda: dict(route=ROUTE,segment_index=0,owner_binding=h.binding,
        binding_reader=lambda:h.binding,clock=lambda:h.now,record_id='observed-fixture-height',
        released_at=h.released,local_wall_clock=h.wall)
    return h


def measure(h, **changes):
    options = h.options(); options.update(changes)
    return measure_current_height(h.observer,h.reader,h.first,h.second,**options)


def test_uses_independent_source_height_and_retains_samples_without_verification(current):
    h=current; cal=measure(h)
    assert cal.raw_z_minus_source_z==2.5  # 2.7 raw minus .2 SOURCE, not .6 baked.
    assert cal.last_calibration_log_line_seq==2
    assert cal.evidence.first.raw_fix is h.first and cal.evidence.second.raw_fix is h.second
    assert cal.evidence.first.source_surface_ids==('wld:1:face:0',)
    assert h.source.calls==[(1.,2.),(1.,2.)]
    assert not cal.live_verified and not cal.evidence.body_height_verified
    assert not cal.evidence.real_client_accepted
    assert current_height_allowed(cal,mode='measurement',route_sha256=ROUTE.artifact_sha256,
                                  owner_binding=h.binding)
    assert not current_height_allowed(cal,mode='full_auto')
    assert not current_height_allowed(replace(cal,live_verified=True),mode='full_auto')


def test_ground_consumer_uses_new_sequences_only_and_retains_observed_scope(current):
    h=current;cal=measure(h)
    args=dict(route=ROUTE,segment_index=0,height_calibration=cal,
              motion_calibration_record_id='fixture-motion',now=h.now,mode='measurement')
    with pytest.raises(GroundObservationUnavailable):h.observer.observe(h.second,**args)
    h.now+=.1; raw=h.fix();args['now']=h.now
    aligned=h.observer.observe(raw,**args)
    assert aligned.raw_fix is raw and aligned.height_calibration is cal
    assert not aligned.live_alignment_verified
    assert aligned.alignment_kind=='current_stopped_height_correspondence'
    for mode in ('full_auto','assist','off'):
        with pytest.raises(GroundObservationUnavailable):
            h.observer.observe(raw,**{**args,'mode':mode})
    with pytest.raises(GroundObservationUnavailable):
        h.observer.observe(raw,**{**args,'route':replace(ROUTE,artifact_sha256='f'*64)})


@pytest.mark.parametrize('change',[
    'stale','epoch','sequence','drift','release','old_wall','old_first_time','source_layer',
    'source_changed','reader_changed','partial','binding_changed','inconsistent_height'])
def test_invalid_or_changed_current_evidence_never_produces_calibration(current,change):
    h=current;options={}
    if change=='stale':h.now+=.51
    elif change=='epoch':h.first=replace(h.first,log_epoch=99)
    elif change=='sequence':h.first=replace(h.first,log_line_seq=0)
    elif change=='drift':h.first=replace(h.first,raw_coordinates=(3.,1.,2.7))
    elif change=='release':options['released_at']=100.
    elif change=='old_wall':options['local_wall_clock']=lambda:datetime(2000,1,1)
    elif change=='old_first_time':h.first=replace(h.first,log_local_time=datetime(2000,1,1))
    elif change=='source_layer':h.source.error='Copied source floor missing or layered at exact XY'
    elif change=='source_changed':h.source.wld_sha256='f'*64
    elif change=='reader_changed':h.reader.latest=replace(h.second)
    elif change=='partial':h.reader.tail.partial=b'pending'
    elif change=='binding_changed':options['binding_reader']=lambda:('other window',)
    elif change=='inconsistent_height':h.first=replace(h.first,raw_coordinates=(2.,1.,2.9))
    with pytest.raises(ValueError):measure(h,**options)


@pytest.mark.parametrize('change',['owner','source'])
def test_rechecks_external_context_after_source_lookup(current,change):
    h=current;lookup=h.source.source_floor_at
    def changing(xy):
        value=lookup(xy)
        if change=='owner':h.binding=(99,'Probe','private')
        else:h.source.wld_sha256='f'*64
        return value
    h.source.source_floor_at=changing
    with pytest.raises(ValueError):measure(h)


def runner(h,cal,legacy):
    return FixedRouteFollower(ROUTE,legacy=legacy,
        motion=legacy.Motion(run_speed=10.,turn_rate=170.,right_sign=-1,turn_latency=.03,back_speed=0.),
        heading=90.,calibration_record_id='fixture-motion',height_calibration=cal,
        geometry_evidence=GEOMETRY,generation=1,generation_reader=lambda:1,mode_reader=lambda:h.mode)


def test_bootstraps_existing_follower_then_revokes_on_full_auto_switch(current,legacy):
    h=current;cal=measure(h);r=runner(h,cal,legacy)
    fixes=[]
    release=h.now
    for delay in (.13,.41):
        h.now+=delay
        fixes.append(h.observer.observe(h.fix(),route=ROUTE,segment_index=0,
            height_calibration=cal,motion_calibration_record_id=r.calibration,now=h.now,
            mode='measurement'))
    r.observe_stopped(*fixes,released_at=release,now=h.now)
    assert r.phase=='ready'
    assert r.propose(h.now).forward is True
    h.mode='full_auto'
    with pytest.raises(RouteHalt,match='Height correspondence'):
        r._check(h.now)
    with pytest.raises(ValueError):runner(h,cal,legacy)


def test_route_session_requires_same_owner_log_and_plan(current,legacy):
    h=current;cal=measure(h)
    chain=setup(legacy).chain
    def session(binding):
        r=runner(h,cal,legacy)
        ledger=RouteFloorCommit(r,chain,stop_lock=threading.RLock(),clock=lambda:h.now)
        return RouteSession(ledger,h.reader,h.observer,initial_release_at=h.now,
            binding_reader=lambda:binding,record_id='fixture-observed-route',local_wall_clock=h.wall)
    created=session(h.binding)
    assert created.phase=='need_location'
    saved=json.loads(json.dumps(created.snapshot(),allow_nan=False))
    assert saved['height_calibration']['live_verified'] is False
    assert saved['height_calibration']['evidence']['second']['raw_fix']['log_line_seq']==2
    created.runner.height_calibration=replace(cal,evidence=replace(cal.evidence,owner_binding=('other',)))
    with pytest.raises(RouteHalt,match='session binding changed'):created.tick()
    assert created.snapshot()['height_calibration']['evidence']['owner_binding']==h.binding
    with pytest.raises(ValueError,match='another owner'):
        session((88,'Probe','private'))
    h.reader.tail.identity=(999,999)
    with pytest.raises(ValueError,match='another owner'):
        session(h.binding)


def test_observed_height_reaches_receipt_bound_floor_staging_without_input(current,legacy):
    h=current;cal=measure(h);r=runner(h,cal,legacy)
    f=setup(legacy,clock=lambda:h.now)
    ledger=RouteFloorCommit(r,f.chain,stop_lock=f.lock,clock=lambda:h.now)
    release=h.now;fixes=[]
    for delay in (.13,.41):
        h.now+=delay
        fixes.append(h.observer.observe(h.fix(),route=ROUTE,segment_index=0,
            height_calibration=cal,motion_calibration_record_id=r.calibration,now=h.now,
            mode='measurement',floor_chain=f.chain))
    r.observe_stopped(*fixes,released_at=release,now=h.now)
    ticket=ledger.stage(r.propose(h.now),reference_fix=fixes[-1],footprint=f.footprint,
        sources=f.sources,requested_seconds=.02,maximum_actual_hold=.08,movement_key=103,
        motion_bounds_record_id='synthetic-only-body-and-motion',check_geometry=f.check)
    assert ticket.preparation.reference_fix.height_calibration is cal
    assert not ticket.preparation.input_authorized
    assert ledger.chain is f.chain  # No receipt means no committed floor change.


@pytest.mark.parametrize('change',['sequence','surfaces','observation_time','offsets'])
def test_malformed_measured_records_are_refused_without_exceptions(current,change):
    cal=measure(current);e=cal.evidence
    if change=='sequence':e=replace(e,first=replace(e.first,raw_fix=replace(e.first.raw_fix,log_line_seq=None)))
    elif change=='surfaces':e=replace(e,first=replace(e.first,source_surface_ids=()))
    elif change=='observation_time':
        e=replace(e,observed_at=0.);cal=replace(cal,valid_from_monotonic=0.)
    elif change=='offsets':e=replace(e,offsets=None)
    assert not current_height_allowed(replace(cal,evidence=e),mode='measurement')
