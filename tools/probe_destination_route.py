#!/usr/bin/env python3
"""Plan toward the copied client Crushbone map marker using synthetic fixes.

This sends no input. The map marker is an approach destination, not verified
zone-trigger geometry, and the suffix still requires per-movement checks.
"""
import argparse
from datetime import datetime,timedelta
from hashlib import sha256
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time

PROJECT=Path(__file__).resolve().parents[1]
STORE=Path.home()/'.local/share/eql-automation'
HELPER=STORE/'owner-assist/0.39.15'
sys.path[:0]=[str(PROJECT),str(HELPER)]
from eql_automation.destination_route import plan_destination
from eql_automation.owner_route_assets import load_gfay_planner,DATA_NAME,DATA_PINS
from eql_automation.owner_zone_tracker import LiveZoneTracker
from eql_automation.route_geometry import RouteMotionBounds
from eqnav.mesh import NavMesh


def run(output,xy,heading):
    if output.exists() or output.is_symlink() or not output.resolve().is_relative_to((STORE/'nav-candidates').resolve()):
        raise ValueError('Use a new private nav-candidates directory')
    labels=STORE/'client-data/retail-full/maps/gfaydark_1.txt'
    alignment=STORE/'nav-candidates/gfaydark.map-alignment.json'
    pins={labels:'84a1e1a655a73ddb13a71a7afc121acfe73d8737554a3ac1a5ad78249d0db882',
        alignment:'c3f9fb5ffdf8dc740d145c119b2c3522e22cb5f36617e575417176932620901f'}
    manifest=json.loads((HELPER/'SOURCE_HASHES.json').read_text())
    pins[HELPER/'eqnav/mesh.py']=manifest['eqnav/mesh.py']
    for path in (Path(__file__),*(PROJECT/'eql_automation').glob('*.py')):
        pins[path]=sha256(path.read_bytes()).hexdigest()
    def verify():
        if any(p.is_symlink() or sha256(p.read_bytes()).hexdigest()!=h for p,h in pins.items()):
            raise ValueError('Copied destination evidence changed')
    verify();context=json.loads(alignment.read_text())
    if (context['best_map_to_wld_xy_transform']!='-y,-x'
            or context['label_map_sha256']!=pins[labels]
            or context['archive_sha256']!=DATA_PINS['gfaydark.s3d']
            or not context['frame_supported_by_rounded_vertex_matches']):
        raise ValueError('Map destination frame is unsupported')
    found=[]
    for line_no,line in enumerate(labels.read_text().splitlines(),1):
        if not line.startswith('P '):continue
        fields=[v.strip() for v in line[2:].split(',')]
        if len(fields)==8 and fields[-1]=='to_Clan_Crushbone':
            found.append((line_no,tuple(map(float,fields[:3]))))
    if len(found)!=1:raise ValueError('No unique client Crushbone approach label')
    line_no,map_xyz=found[0];goal=(-map_xyz[0],-map_xyz[1])
    root=STORE/'owner-route-data'/DATA_NAME
    planner=load_gfay_planner(root)
    mesh=NavMesh.load(root/'gfaydark.npz',expected_sha256=DATA_PINS['gfaydark.npz'])
    offset=[0.];clock=lambda:time.monotonic()+offset[0]
    wall=lambda:datetime.now()+timedelta(seconds=offset[0])
    owner=('synthetic-owner','Probe','private')
    source_z,_=planner.source.source_floor_at(xy)
    result=None;error=None;began=time.monotonic()
    with TemporaryDirectory(prefix='eql-destination-probe-') as directory:
        log=Path(directory)/'eqlog_Probe_private.txt';log.touch()
        tracker=LiveZoneTracker(log,root/'ZoneNames.txt',expected_character='Probe',expected_server='private',
            binding_reader=lambda:owner,clock=clock)
        def append(body):
            with log.open('a') as out:out.write(wall().strftime('[%a %b %d %H:%M:%S %Y] ')+body+'\n')
        append('You have entered '+planner.zone_name+'.');tracker.poll();lease=tracker.acquire()
        def position():
            append(f'Your Location is {xy[1]:.2f}, {xy[0]:.2f}, {source_z+2.564:.2f}')
            return lease.reader.poll(now=clock())[0]
        first=position();offset[0]+=.5;second=position()
        bounds=RouteMotionBounds('explicit-copied-route-hypotheses','synthetic-motion',
            .01,.1,.2,30.,.4,.01,2.,.1,1.2,6.)
        try:
            result=plan_destination(planner,mesh,lease.reader,first,second,goal_xy=goal,heading=heading,
                motion_record_id='synthetic-motion',bounds=bounds,half_width=.3,vertical_window=3.,
                maximum_source_z_difference=2.,owner_binding=owner,binding_reader=lease.check,
                released_at=first.received_monotonic-.2,record_id='copied-destination-fixture',
                clock=clock,local_wall_clock=wall,maximum_seconds=180.)
        except (ValueError,RuntimeError) as exc:error=type(exc).__name__+': '+str(exc)
        finally:lease.release()
    verify();output.mkdir(parents=True)
    (output/'executed.py').write_bytes(Path(__file__).read_bytes())
    if result is not None:
        (output/'plan.json').write_bytes(result.plan_bytes)
        (output/'geometry.json').write_bytes(result.evidence_bytes)
    record=dict(format='eql-copied-destination-probe-v1',simulation_only=True,
        fixture_xy=xy,fixture_heading=heading,goal_client_label='to_Clan_Crushbone',
        goal_map_xyz=map_xyz,goal_package_xy=goal,label_line=line_no,pins={str(p):h for p,h in pins.items()},
        goal_is_verified_zone_trigger=False,current_plan_produced=result is not None,error=error,
        segments=0 if result is None else len(result.route.segments),
        length=0 if result is None else sum(s.length for s in result.route.segments),
        initial_chain_index=None if result is None else result.floor_chain.index,
        plan_sha256=None if result is None else result.route.artifact_sha256,
        geometry_sha256=None if result is None else sha256(result.evidence_bytes).hexdigest(),
        seconds=time.monotonic()-began,game_input_sent=False,real_client_accepted=False,
        whole_corridor_clearance_verified=False)
    path=output/'probe.json';path.write_text(json.dumps(record,indent=2)+'\n')
    return dict(path=str(path),sha256=sha256(path.read_bytes()).hexdigest(),
        current_plan_produced=record['current_plan_produced'],segments=record['segments'],
        length=record['length'],seconds=record['seconds'],error=error)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--fixture-xy',required=True,type=float,nargs=2)
    parser.add_argument('--fixture-heading',required=True,type=float)
    args=parser.parse_args()
    print(json.dumps(run(args.output,tuple(args.fixture_xy),args.fixture_heading),indent=2))
