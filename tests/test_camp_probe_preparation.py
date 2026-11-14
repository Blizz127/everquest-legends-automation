"""Genuine camp-height producer and copied synthetic geometry; no input."""
from dataclasses import replace
import json

import pytest

from eql_automation.camp_probe_preparation import CampProbePreparation
from eql_automation.camp_stopped_height import measure_camp_stopped_height
from eql_automation.native_region_policy import encoded
from eql_automation.owner_zone_tracker import LiveZoneTracker
from eql_automation.route_floor_commit import _chain_snapshot
from test_camp_floor_checkpoint import checkpoint
from test_camp_stopped_height import pair
from test_source_motion import f
from test_route_floor_commit import legacy


@pytest.fixture
def probe(checkpoint,tmp_path):
    f=checkpoint
    tracker=LiveZoneTracker(f.reader.tail.path,tmp_path/'ZoneNames.txt',
        expected_character='Probe',expected_server='private',binding_reader=lambda:f.owner,clock=f.clock)
    tracker.reader=f.reader;f.lease=tracker.acquire()
    a,b,options=pair(f);f.camp_binding=options['owner_binding'];f.binding_hook=lambda:None
    def binding():f.binding_hook();return f.camp_binding
    options['binding_reader']=binding
    f.height=measure_camp_stopped_height(f.checkpoint,f.reader,a,b,**options)
    f.probe=CampProbePreparation(f.checkpoint,f.height,f.lease,probe_kind='forward',
        bounds=f.ledger.bounds,bounds_basis=encoded({'kind':'explicit_test_hypotheses','source':'synthetic fixture'}),
        owner_binding=f.camp_binding,binding_reader=binding,clock=f.clock,local_wall_clock=f.wall)
    return f


def start(f,*,x=4.):
    minimum=f.reader.log_line_seq;released=f.now
    f.now+=.2;a=f.position(x=x)
    f.now+=.5;b=f.position(x=x)
    return f.probe.observe_start(a,b,minimum_log_seq=minimum,released_at=released)


def test_slow_geometry_needs_new_pair_and_never_renews_planning_height(probe):
    f=probe;p=f.probe;original=_chain_snapshot(f.checkpoint._chain)
    old_expiry=f.height.expires_at;old_calibration=f.checkpoint._calibration.valid_until_monotonic
    calls=[]
    def delay():
        calls.append(1)
        if len(calls)==3:f.now+=.6
    f.binding_hook=delay
    record=p.prepare()
    assert f.now>old_expiry and record['phase']=='prepared'
    assert record['evidence']['planning_expires_at']==old_expiry
    assert record['evidence']['geometry']['all_headings']
    assert not record['input_authorized'] and not record['evidence']['motion_bounds_verified']
    assert _chain_snapshot(f.checkpoint._chain)==original
    fresh=start(f);envelope=p.check_start(fresh)
    assert fresh.height.second is f.reader.latest and fresh.height is not f.height
    assert fresh.expires_at==fresh.height.second.received_monotonic+.5
    assert not fresh.input_authorized and not fresh.current_motion_verified
    assert envelope.branch is not f.checkpoint._chain
    assert f.height.expires_at==old_expiry
    assert f.checkpoint._calibration.valid_until_monotonic==old_calibration


def test_old_planning_pair_cannot_become_a_probe_start(probe):
    f=probe;p=f.probe;p.prepare()
    with pytest.raises(ValueError):
        p.observe_start(f.height.first,f.height.second,
            minimum_log_seq=f.height.second.log_line_seq,released_at=f.now)
    assert p.phase=='stopped' and p._envelope is None and f.checkpoint.valid


def test_new_start_shift_requires_replanning_even_inside_arrival_cap(probe):
    f=probe;f.probe.prepare()
    with pytest.raises(ValueError,match='replan'):start(f,x=4.01)
    assert f.probe.phase=='stopped' and f.checkpoint.valid


@pytest.mark.parametrize('fault',('lease','binding','cancel','floor','bounds','clock','envelope','record'))
def test_preparation_is_discarded_when_its_context_changes(probe,fault):
    f=probe;p=f.probe;p.prepare()
    if fault=='lease':f.lease.release()
    elif fault=='binding':f.camp_binding=('another-camp',2)
    elif fault=='cancel':p.cancel('F9')
    elif fault=='floor':f.checkpoint.invalidate('camp ended')
    elif fault=='bounds':p.bounds=replace(p.bounds,forward_speed_upper_bound=1.)
    elif fault=='clock':f.now-=.01
    elif fault=='envelope':p._envelope.branch.seed_evidence_sha256='f'*64
    else:p.payload=b'{}'
    with pytest.raises(ValueError):p.check()
    assert p.phase=='stopped' and p._envelope is None


def test_stop_during_geometry_cannot_publish_candidate(probe):
    f=probe;p=f.probe;calls=[]
    def stop():
        calls.append(1)
        if len(calls)==3:p.cancel('F9 during full source check')
    f.binding_hook=stop
    with pytest.raises(ValueError):p.prepare()
    assert p.phase=='stopped' and p.payload is None and p._envelope is None


@pytest.mark.parametrize('change',('expired','replaced','new_reply'))
def test_ready_start_is_exact_current_and_short_lived(probe,change):
    f=probe;p=f.probe;p.prepare();fresh=start(f)
    if change=='expired':f.now=fresh.expires_at+.01
    elif change=='replaced':fresh=replace(fresh)
    else:f.now+=.01;f.position()
    with pytest.raises(ValueError):p.check_start(fresh)


def test_height_object_and_report_must_describe_same_position(probe):
    f=probe
    false=replace(f.height,package_xyz=(4.,2.,2.7))
    with pytest.raises(ValueError,match='differs|differ'):
        CampProbePreparation(f.checkpoint,false,f.lease,probe_kind='forward',bounds=f.ledger.bounds,
            bounds_basis=encoded({'source':'synthetic'}),owner_binding=f.camp_binding,
            binding_reader=lambda:f.camp_binding,clock=f.clock,local_wall_clock=f.wall)
