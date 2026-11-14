#!/usr/bin/env python3
"""Measure copied source/baked differences over complete route corridor cells.

This produces a diagnostic profile, not a live calibration or input permit.
A sampled prefix maximum is never labelled a complete regional bound.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys
import time

PROJECT=Path(__file__).resolve().parents[1]
STORE=Path.home()/'.local/share/eql-automation'
PLAN=STORE/'nav-candidates/gfay-west-portal-plan-0.41.53.json'
MESH=STORE/'navmesh/nov12-7e3cd28-store/gfaydark.npz'
SOURCE=STORE/'client-data/retail-full/assets/gfaydark.s3d'
PINS={PLAN:'9207b689d3ca462f0eb0b6d45af87deb902662c237dd33f5172ab613021e12f6',
      MESH:'5f8e16c5bcd2221ba273f681750ca480349780524d23609c059a3e817df6abd9',
      SOURCE:'ea95f51a2d4645410223d24cc7da9eb0e7095310c6e9f8756e8c51d67df13d9f'}


def run(output, *, seconds):
    sys.path.insert(0,str(PROJECT))
    from eql_automation.fixed_route_follower import FixedRoute
    from eql_automation.bsp_detail_view import BspDetailMeshView
    from eql_automation.ground_sweep import GroundFace,motion_footprint
    from eql_automation.ground_sweep_view import GroundSweepView
    from eql_automation.portal_precision_view import PortalPrecisionView
    from eql_automation.portal_precision import source_support
    from eql_automation.portal_surface_audit import _supported_detail_height
    began=time.monotonic()
    pins=dict(PINS)
    for name in ('fixed_route_follower','ground_binding','bsp_detail_view','ground_sweep','ground_sweep_view',
                 'portal_precision','portal_precision_view','portal_surface_audit','map_alignment',
                 'mesh_geometry','material_audit','pfs_archive','wld_inventory'):
        p=PROJECT/'eql_automation'/(name+'.py');pins[p]=sha256(p.read_bytes()).hexdigest()
    pins[Path(__file__)]=sha256(Path(__file__).read_bytes()).hexdigest()
    def verify():
        if any(p.is_symlink() or sha256(p.read_bytes()).hexdigest()!=h for p,h in pins.items()):
            raise ValueError('Source profile input changed')
    verify()
    route=FixedRoute.load(PLAN,expected_sha256=PINS[PLAN],mesh_sha256=PINS[MESH])
    mesh=BspDetailMeshView.load(MESH,zone=route.zone)
    ground=GroundSweepView.load(MESH,zone=route.zone)
    view=PortalPrecisionView(ground,MESH,SOURCE,zone=route.zone,maximum_ulp_steps=2)
    counts=[math.ceil(s.length/2.) for s in route.segments]
    total=sum(counts)
    if total>10000 or max(counts)>512:
        raise ValueError('Regional cell budget exceeded')
    rows=[];maximum=0.;failures=[];timed_out=False
    for index,segment in enumerate(route.segments):
        heading=math.degrees(math.atan2(segment.end[0]-segment.start[0],segment.end[1]-segment.start[1]))%360
        count=counts[index]
        for part in range(count):
            if time.monotonic()-began>seconds:
                timed_out=True;break
            xy=tuple(segment.start[k]+(segment.end[k]-segment.start[k])*part/count for k in range(2))
            z=_supported_detail_height(mesh,segment.polygon,*xy)
            row={'segment':index,'partition':part,'candidate':False}
            rows.append(row)
            if z is None:
                row['reason']='selected_polygon_ground_missing';failures.append((index,part));continue
            footprint=motion_footprint(xy,heading,segment.length/count,
                position_error=route.half_width,heading_error_degrees=0.,post_release_drift=0.)
            reference=(*xy,z);window=segment.length/count+route.half_width+.1
            component=int(ground.components[segment.polygon])
            check,ids=ground.check(footprint,reference=reference,component=component,vertical_window=window)
            faces=tuple(GroundFace(tuple(tuple(float(v) for v in p) for p in ground.triangles[i]),
                int(ground.areas[ground.polys[i]]),int(ground.components[ground.polys[i]])) for i in ids)
            row.update(footprint=footprint,reference=reference,detail_ids=ids,ground=asdict(check))
            try:
                sources=view.source_faces_for_footprint(footprint)
            except ValueError as error:
                row['reason']=str(error);failures.append((index,part));continue
            row['source_candidates']=[(s.fragment,s.face) for s in sources]
            if not faces or not sources:
                row['reason']='missing_local_geometry';failures.append((index,part));continue
            # A measurement envelope derived from all source/detail vertex Z
            # extrema replaces an arbitrary acceptance cap. This coarse value
            # is NOT exported as a useful same-floor/live binding limit.
            # The tight reported difference is computed on every intersection
            # vertex of the source and baked planes over the complete cell.
            baked_z=[p[2] for face in faces for p in face.vertices]
            source_z=[p[2] for face in sources for p in face.vertices_wld]
            envelope=math.nextafter(max(abs(max(baked_z)-min(source_z)),abs(min(baked_z)-max(source_z))),math.inf)
            support=None
            if check.candidate:
                support=source_support(footprint,sources,faces,maximum_z_difference=envelope)
            elif check.reason in ('uncovered_ground_area','overlapping_ground_faces'):
                retry=view.retry(check,footprint,ids,reference=reference,component=component,
                    vertical_window=window,maximum_source_z_difference=envelope,allow_overlap=True)
                row['precision_retry']=asdict(retry)
                support=retry.source_support if retry.candidate else None
            if support is None or not support.candidate:
                row['reason']=support.reason if support is not None else check.reason
                row['source_support']=None if support is None else asdict(support)
                failures.append((index,part));continue
            row.update(candidate=True,reason='copied_cell_height_difference_measured',source_support=asdict(support))
            maximum=max(maximum,support.maximum_source_baked_z_difference)
        if timed_out:break
    verify()
    complete=len(rows)==total and not timed_out
    all_pass=complete and not failures
    report={'format':'eql-copied-route-source-profile-v1','offline_only':True,
        'game_input_sent':False,'input_authorized':False,'real_client_accepted':False,'route_accepted':False,
        'source_or_mesh_modified':False,'zone':route.zone,'radius':route.half_width,'maximum_cell_length':2.,
        'expected_cells':total,'checked_cells':len(rows),'complete_cell_scan':complete,
        'all_cells_candidate':all_pass,'failed_cells':failures,'budget_exhausted':timed_out,
        'measured_maximum_on_passing_cells':maximum,
        'complete_region_measured_maximum':maximum if all_pass else None,
        'numerics':'float64 clipped plane extrema, not an outward-rounded certified bound',
        'cells':rows,'source_wld_sha256':view.wld_sha256,'pins':{str(p):h for p,h in pins.items()},
        'seconds':time.monotonic()-began}
    with output.open('x') as out:json.dump(report,out,indent=2);out.write('\n')
    print(json.dumps({'artifact':str(output),'sha256':sha256(output.read_bytes()).hexdigest(),
        'checked':len(rows),'expected':total,'failed':len(failures),'complete':complete,
        'maximum_on_passing_cells':maximum,'first_failures':failures[:12],'seconds':report['seconds']}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--seconds',type=float,default=90.)
    args=parser.parse_args();output=args.output.expanduser()
    if (output.parent.resolve()!=(STORE/'nav-candidates').resolve() or output.exists()
            or output.is_symlink() or output.suffix!='.json' or not math.isfinite(args.seconds) or not 1<=args.seconds<=300):
        parser.error('Use a new private nav-candidates JSON and wall budget 1–300 seconds')
    os.umask(0o077);os.nice(15);run(output,seconds=args.seconds)


if __name__=='__main__':main()
