#!/usr/bin/env python3
"""Exercise observed-height startup on copied GFay terrain with synthetic logs.

The actor-Z input is an explicit fixture. No current character is observed,
no native code executes, and neither route nor motion acceptance is issued.
"""
import argparse
from datetime import datetime, timedelta
from hashlib import sha256
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
from tools.probe_route_ground_observer import REPLAY,REPLAY_SHA,PLAN,MESH,ARCHIVE,STORE
from eql_automation.fixed_route_follower import FixedRoute
from eql_automation.ground_binding import GroundGeometryEvidence
from eql_automation.ground_observer import RouteGroundObserver
from eql_automation.location_log import LocationLogReader
from eql_automation.observed_height import measure_current_height,height_record,current_height_allowed

ZONES=STORE/'client-data/retail-sample/Resources/ZoneNames.txt'


def run(output):
    if (output.exists() or output.is_symlink()
            or not output.resolve().is_relative_to((STORE/'nav-candidates').resolve())):
        raise ValueError('Use a new output under the private nav-candidates store')
    assert sha256(REPLAY.read_bytes()).hexdigest()==REPLAY_SHA
    replay=json.loads(REPLAY.read_text()); fixture=replay['ground_binding_fixture']
    assert replay['simulation_only'] is True and fixture['simulation_only'] is True
    pins={REPLAY:REPLAY_SHA,PLAN:fixture['plan'],MESH:fixture['mesh'],ARCHIVE:fixture['source_archive'],
          ZONES:sha256(ZONES.read_bytes()).hexdigest()}
    for path in (Path(__file__),*(PROJECT/'eql_automation'/name for name in (
            'observed_height.py','ground_observer.py','ground_binding.py','location_log.py'))):
        pins[path]=sha256(path.read_bytes()).hexdigest()
    def verify():
        for path,pin in pins.items():
            if path.is_symlink() or sha256(path.read_bytes()).hexdigest()!=pin:
                raise ValueError('Changed copied input: '+str(path))
    verify()
    geometry=GroundGeometryEvidence('gfaydark',fixture['mesh'],fixture['source_archive'],
        fixture['source_wld'],sha256(json.dumps(fixture,sort_keys=True).encode()).hexdigest(),
        fixture['source_z_limit'],tuple(tuple(p) for p in fixture['portal_pairs']),True)
    route=FixedRoute.load(PLAN,expected_sha256=fixture['plan'],mesh_sha256=fixture['mesh'])
    observer=RouteGroundObserver.load(MESH,ARCHIVE,geometry_evidence=geometry)
    x,y,_=route.segments[0].start
    x,y=round(x,2),round(y,2)
    source_z,_=observer.source.source_floor_at((x,y))
    # This belongs only to this simulation; production measures the input.
    synthetic_actor_offset=2.564
    body=f'Your Location is {y:.2f}, {x:.2f}, {source_z+synthetic_actor_offset:.2f}'
    now=100.
    wall=lambda:datetime(2026,11,14,12)+timedelta(seconds=now-100.)
    owner=('synthetic-window','Probe','private')
    with TemporaryDirectory(prefix='eql-height-fixture-') as directory:
        log=Path(directory)/'eqlog_Probe_private.txt'; log.touch()
        reader=LocationLogReader(log,ZONES,expected_character='Probe',expected_server='private')
        def append(text):
            with log.open('a') as stream:
                stream.write(wall().strftime('[%a %b %d %H:%M:%S %Y] ')+text+'\n')
        names=[name for name,zone_id in reader.zone_ids.items() if zone_id==54]
        if len(names)!=1:raise ValueError('Copied zone catalog does not uniquely name GFay')
        append('You have entered '+names[0]+'.'); reader.poll(now=now)
        assert reader.zone_id==54
        append(body); first=reader.poll(now=now)[0]
        now+=.5;append(body);second=reader.poll(now=now)[0]
        cal=measure_current_height(observer,reader,first,second,route=route,segment_index=0,
            owner_binding=owner,binding_reader=lambda:owner,clock=lambda:now,
            record_id='copied-gfay-synthetic-height',released_at=99.8,local_wall_clock=wall)
        now+=.2;append(body);new_fix=reader.poll(now=now)[0]
        aligned=observer.observe(new_fix,route=route,segment_index=0,height_calibration=cal,
            motion_calibration_record_id='synthetic-motion-only',now=now,mode='measurement')
        assert aligned.raw_fix is new_fix and not aligned.live_alignment_verified
        assert current_height_allowed(cal,mode='measurement',route_sha256=route.artifact_sha256)
        assert not current_height_allowed(cal,mode='full_auto')
    verify()
    result=dict(format='eql-copied-observed-height-bootstrap-v1',simulation_only=True,
        pins={str(p):h for p,h in pins.items()},synthetic_actor_offset=synthetic_actor_offset,
        synthetic_location_body=body,height=height_record(cal),
        source_height=aligned.source_floor.ground_wld_xyz[2],
        baked_height=aligned.mesh_projection.package_xyz[2],
        fresh_sequence=aligned.raw_fix.log_line_seq,
        observed_scope_retained=True,full_auto_refused=True,game_input_sent=False,
        native_executed=False,real_client_accepted=False,route_accepted=False)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as stream:
        json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    return dict(path=str(output),sha256=sha256(output.read_bytes()).hexdigest(),
        observed_offset=cal.raw_z_minus_source_z,source_height=result['source_height'],
        baked_height=result['baked_height'],simulation_only=True,route_accepted=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    print(json.dumps(run(parser.parse_args().output),indent=2))
