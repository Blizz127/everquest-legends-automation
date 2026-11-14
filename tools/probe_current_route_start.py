#!/usr/bin/env python3
"""Create a new current-XY trial using copied GFay data and synthetic positions.

The retained route supplies only a reproducible fixture location or polygon
whose center supplies a second fixture. Its route/geometry proof is never
reused as current-start evidence. No client, device or character is accessed.
"""
import argparse
from datetime import datetime, timedelta
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
from tools.probe_route_ground_observer import REPLAY, REPLAY_SHA, PLAN, MESH, ARCHIVE, STORE
from tools.audit_static_source import HELPER, PINS as STATIC_PINS
from eql_automation.bsp_detail_view import BspDetailMeshView
from eql_automation.bsp_volume import BspVolumeView
from eql_automation.current_route_start import CurrentStartPlanner
from eql_automation.fixed_route_follower import FixedRoute
from eql_automation.ground_sweep_view import GroundSweepView
from eql_automation.observed_height import measure_current_height, height_record
from eql_automation.owner_zone_tracker import LiveZoneTracker
from eql_automation.pfs_archive import PFSArchive
from eql_automation.portal_precision_view import PortalPrecisionView
from eql_automation.route_geometry import RouteMotionBounds
from eql_automation.static_source_view import StaticSourceView
from eql_automation.wld_inventory import WLDInventory


def run(output, *, polygon_center=False):
    if output.exists() or output.is_symlink() or not output.resolve().is_relative_to((STORE/'nav-candidates').resolve()):
        raise ValueError('Use a new private nav-candidates directory')
    if sha256(REPLAY.read_bytes()).hexdigest()!=REPLAY_SHA:
        raise ValueError('Retained input manifest changed')
    replay=json.loads(REPLAY.read_text());fixture=replay['ground_binding_fixture']
    zones=STORE/'client-data/retail-sample/Resources/ZoneNames.txt'
    pins=dict(STATIC_PINS)
    pins.update({REPLAY:REPLAY_SHA,PLAN:fixture['plan'],MESH:fixture['mesh'],zones:sha256(zones.read_bytes()).hexdigest()})
    for path in (Path(__file__), *(PROJECT/'eql_automation'/name for name in (
            'current_route_start.py','bsp_detail_view.py','route_geometry.py','ground_observer.py',
            'source_floor_chain.py','source_occupancy.py','static_floor_guard.py','bsp_floor_guard.py'))):
        pins[path]=sha256(path.read_bytes()).hexdigest()
    def verify():
        if any(p.is_symlink() or sha256(p.read_bytes()).hexdigest()!=pin for p,pin in pins.items()):
            raise ValueError('Copied probe input changed')
    verify()
    sys.path.insert(1,str(HELPER))
    from eqnav import zonegeom
    main=PFSArchive(ARCHIVE)
    terrain=WLDInventory(main.read_member('gfaydark.wld'))
    objects=WLDInventory(main.read_member('objects.wld'))
    library=WLDInventory(PFSArchive(ARCHIVE.with_name('gfaydark_obj.s3d')).read_member('gfaydark_obj.wld'))
    static=StaticSourceView.from_wld(objects,(library,),terrain_fragment_max=max(f.index for f in terrain.fragments),
        transform=zonegeom.place_vertices,transform_sha256=pins[HELPER/'eqnav/zonegeom.py'])
    if static.inventory_sha256!=replay['static_source']['inventory_sha256']:
        raise ValueError('Complete static inventory differs from audited placements')
    mesh=BspDetailMeshView.load(MESH,zone='gfaydark')
    ground=GroundSweepView.load(MESH,zone='gfaydark')
    source=PortalPrecisionView(ground,MESH,ARCHIVE,zone='gfaydark')
    bsp=BspVolumeView.from_wld(terrain)
    old=FixedRoute.load(PLAN,expected_sha256=fixture['plan'],mesh_sha256=fixture['mesh'])
    leg=old.segments[0]
    dx,dy=(leg.end[i]-leg.start[i] for i in (0,1));distance=math.hypot(dx,dy)
    xy=tuple(round(leg.start[i]+4.*(dx,dy)[i]/distance,2) for i in (0,1))
    if polygon_center:
        import numpy as np
        with np.load(MESH,allow_pickle=False) as data:
            ring=data['poly_verts'][leg.polygon,:int(data['poly_nv'][leg.polygon])]
            xy=tuple(round(float(v),2) for v in ring.mean(axis=0)[:2])
    heading=math.degrees(math.atan2(dx,dy))%360
    source_z,_=source.source_floor_at(xy)
    body=f'Your Location is {xy[1]:.2f}, {xy[0]:.2f}, {source_z+2.564:.2f}'
    offset=[0.];clock=lambda:time.monotonic()+offset[0]
    wall=lambda:datetime.now()+timedelta(seconds=offset[0])
    owner=('synthetic-owner','Probe','private')
    began=time.monotonic();result=None;error=None;cal=None
    with TemporaryDirectory(prefix='eql-current-start-') as directory:
        log=Path(directory)/'eqlog_Probe_private.txt';log.touch()
        tracker=LiveZoneTracker(log,zones,expected_character='Probe',expected_server='private',
            binding_reader=lambda:owner,clock=clock)
        names=[name for name,zone in tracker.reader.zone_ids.items() if zone==54]
        if len(names)!=1:raise ValueError('GFay catalog identity is not unique')
        def append(body):
            with log.open('a') as stream:stream.write(wall().strftime('[%a %b %d %H:%M:%S %Y] ')+body+'\n')
        append('You have entered '+names[0]+'.');tracker.poll();lease=tracker.acquire();reader=lease.reader
        def position():
            append(body);return reader.poll(now=clock())[0]
        first=position();offset[0]+=.5;second=position()
        planner=CurrentStartPlanner(mesh=mesh,ground=ground,source=source,static=static,bsp=bsp,
            zone_short_name='gfaydark',expected_zone_id=54,expected_zone_name=names[0],
            mesh_sha256=fixture['mesh'],source_archive_sha256=fixture['source_archive'],
            source_wld_sha256=fixture['source_wld'],static_inventory_sha256=static.inventory_sha256)
        bounds=RouteMotionBounds('copied-gfay-explicit-hypotheses','synthetic-motion',
            .01,.1,.2,30.,.4,.01,2.,.1,1.2,6.)
        try:
            result=planner.plan(reader,first,second,heading=heading,motion_record_id='synthetic-motion',
                bounds=bounds,length=2.,half_width=.3,vertical_window=3.,maximum_source_z_difference=2.,
                owner_binding=owner,binding_reader=lease.check,released_at=first.received_monotonic-.2,
                record_id='copied-gfay-current-start',clock=clock,local_wall_clock=wall)
            # Obtain a NEW pair after full geometry planning, never reuse or retime it.
            released=clock();offset[0]+=.2;a=position();offset[0]+=.5;b=position()
            cal=measure_current_height(result.observer,reader,a,b,route=result.route,segment_index=0,
                owner_binding=owner,binding_reader=lease.check,clock=clock,record_id='copied-gfay-new-height',
                released_at=released,local_wall_clock=wall)
        except ValueError as exc:error=type(exc).__name__+': '+str(exc)
        finally:lease.release()
    verify();output.mkdir(parents=True)
    if result is not None:
        (output/'plan.json').write_bytes(result.plan_bytes)
        (output/'geometry.json').write_bytes(result.evidence_bytes)
        assert FixedRoute.load(output/'plan.json',expected_sha256=result.route.artifact_sha256,
                               mesh_sha256=fixture['mesh'])==result.route
    record=dict(format='eql-copied-current-start-probe-v1',simulation_only=True,
        pins={str(p):pin for p,pin in pins.items()},
        fixture_location_source=('center of retained first polygon' if polygon_center else
            'retained first segment shifted four source units')+'; synthetic actor height',
        package_xy=xy,heading=heading,synthetic_location_body=body,
        old_start=leg.start,old_geometry_proof_reused=False,planning_seconds=time.monotonic()-began,
        current_plan_produced=result is not None,height_produced=cal is not None,error=error,
        plan_sha256=None if result is None else result.route.artifact_sha256,
        geometry_sha256=None if result is None else sha256(result.evidence_bytes).hexdigest(),
        height=None if cal is None else height_record(cal),
        real_client_accepted=False,route_accepted=False,game_input_sent=False)
    path=output/'probe.json';path.write_text(json.dumps(record,indent=2)+'\n')
    return dict(path=str(path),sha256=sha256(path.read_bytes()).hexdigest(),
        current_plan_produced=record['current_plan_produced'],height_produced=record['height_produced'],
        error=error,planning_seconds=record['planning_seconds'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--polygon-center',action='store_true')
    args=parser.parse_args()
    print(json.dumps(run(args.output,polygon_center=args.polygon_center),indent=2))
