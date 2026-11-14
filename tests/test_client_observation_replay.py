"""Printed position feedback must not teleport the simulated physical pose."""
from dataclasses import replace
from hashlib import sha256
import importlib.util
import math
import sys

import pytest

from eql_automation.fixed_route_follower import FixedRouteFollower,FixedSegment
from tools.replay_fixed_route import ClientObservationError,client_observation_pair
from test_ground_observer import fixture,rectangle,HEIGHT,GEOMETRY,ROUTE


def pair(observer,position,**changes):
    options=dict(route=ROUTE,segment_index=0,height_calibration=HEIGHT,
        motion_calibration_record_id='synthetic-print-feedback',floor_chain=None,
        release=100.,sequence=0)
    options.update(changes)
    return client_observation_pair(observer,position,**options)


def test_printed_feedback_preserves_physical_pose_and_resamples_observed_xy():
    observer,_,_,source=fixture()
    position=[1.23456,2.34567,.6]
    fixes,metadata=pair(observer,position)
    assert position==[1.23456,2.34567,.6]
    assert metadata['physical_source_z']==.2
    assert metadata['synthetic_log_body']=='Your Location is 2.35, 1.23, 2.70'
    assert [f.raw_fix.log_line_seq for f in fixes]==[1,2]
    assert [f.raw_fix.received_monotonic for f in fixes]==[100.13,100.53]
    assert all(f.mesh_projection.package_xyz==(1.23,2.35,.6) for f in fixes)
    assert source.calls==[(1.23456,2.34567),(1.23,2.35),(1.23,2.35)]


def test_printed_neighbor_uses_existing_portal_bounds_and_retains_refusal():
    observer,*_=fixture(first=rectangle(0.,2.004),second=rectangle(2.006,4.))
    # Synthetic physical support comes from the source; printed XY lies in
    # the selected adjacent polygon and remains within the existing disk.
    position=[2.008,2.,.6]
    fixes,_=pair(observer,position)
    assert all(f.mesh_projection.polygon==1 for f in fixes)
    assert position==[2.008,2.,.6]
    with pytest.raises(ClientObservationError):pair(observer,[2.3,2.,.6])
    observer,*_=fixture(first=rectangle(0.,1.995),second=rectangle(2.005,4.))
    position=[1.996,2.,.6]
    with pytest.raises(ClientObservationError) as failure:pair(observer,position)
    assert failure.value.evidence['raw_coordinates']==(2.,2.,2.7)
    assert failure.value.evidence['physical_source_z']==.2
    assert position==[1.996,2.,.6]


@pytest.mark.parametrize('last_y',[2.004,3.004])
def test_real_retained_follower_moves_physical_pose_using_printed_feedback(last_y):
    if importlib.util.find_spec('numpy') is None:pytest.skip('Retained helper requires numpy')
    from test_fixed_route_follower import HELPER,PINS
    if not HELPER.exists():pytest.skip('Retained helper source is required')
    for name,digest in PINS.items():assert sha256((HELPER/name).read_bytes()).hexdigest()==digest
    sys.path.insert(0,str(HELPER))
    from eqnav import steer
    observer,*_=fixture()
    route=replace(ROUTE,segments=(FixedSegment(0,(1.003,2.004,.6),(2.003,2.004,.6)),
        FixedSegment(1,(2.003,2.004,.6),(3.003,last_y,.6))))
    motion=steer.Motion(run_speed=10.,turn_rate=170.,right_sign=-1,turn_latency=.03,back_speed=5.)
    runner=FixedRouteFollower(route,legacy=steer,motion=motion,heading=90.,
        calibration_record_id='synthetic-print-feedback',height_calibration=HEIGHT,
        geometry_evidence=GEOMETRY,generation=1,generation_reader=lambda:1,
        mode_reader=lambda:'measurement')
    position=list(route.segments[0].start);heading=90.;sequence=0;differences=[]
    def stopped(release):
        nonlocal sequence
        before=list(position)
        fixes,_=pair(observer,position,route=route,segment_index=runner.index,
            release=release,sequence=sequence)
        assert position==before
        sequence=fixes[-1].raw_fix.log_line_seq
        runner.observe_stopped(*fixes,released_at=release,now=release+.53)
        differences.append(math.dist(position[:2],fixes[-1].mesh_projection.package_xyz[:2]))
    stopped(100.)
    for _ in range(50):
        if runner.phase=='arrived':break
        proposal=runner.propose(runner.last_at+.01)
        seconds=runner.suggest_hold(proposal,minimum_seconds=.02,
            maximum_seconds=.15 if proposal.turn else .1)
        if proposal.turn:
            sign=motion.right_sign*(1 if proposal.turn=='right' else -1)
            heading=(heading+sign*motion.turn_rate*max(0.,seconds-motion.turn_latency))%360
        elif proposal.forward:
            position[0]+=math.sin(math.radians(heading))*10.*seconds
            position[1]+=math.cos(math.radians(heading))*10.*seconds
        start=proposal.at+.01;release=start+seconds
        runner.record_release(proposal,started_at=start,released_at=release)
        stopped(release)
    assert runner.phase=='arrived' and runner.index==2 and runner.steps>0
    assert max(differences)>0 and max(differences)<=math.sqrt(2)*.005+1e-12
    assert math.dist(position[:2],route.segments[-1].end[:2])<.26
