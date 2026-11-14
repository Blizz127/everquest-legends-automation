#!/usr/bin/env python3
"""Relocate explicit portals in a pinned copied GFay plan and audit the repair.

This offline tool keeps the polygon sequence and client/navmesh files intact.
It rechecks affected full ground tubes, old strip/turn constraints and the
entire centerline BSP trace. Export is a diagnostic plan, not movement approval.
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

PROJECT = Path(__file__).resolve().parents[1]
STORE = Path.home()/'.local/share/eql-automation'
sys.path.insert(0, str(PROJECT))


def run(args):
    import numpy as np
    from tools.replay_fixed_route import PINS, MESH, MESH_SHA, HELPER
    from eql_automation.fixed_route_follower import FixedRoute
    from eql_automation.ground_sweep import motion_footprint
    from eql_automation.ground_sweep_view import GroundSweepView
    from eql_automation.portal_precision_view import PortalPrecisionView
    from eql_automation.portal_surface_audit import _supported_detail_height
    from eql_automation.lateral_strip_audit import audit_segment_strip
    from eql_automation.turn_disk_audit import audit_turn_disk
    from eql_automation.ground_bsp_route import audit_ground_bsp_route, verify_helper_bsp_frame
    from eql_automation.bsp_probe import BspPointLookup
    from eql_automation.pfs_archive import PFSArchive
    from eql_automation.wld_inventory import WLDInventory
    began = time.monotonic()
    pins = dict(PINS)
    pins[args.plan] = args.plan_sha256
    archive = STORE/'client-data/retail-full/assets/gfaydark.s3d'
    pins[archive] = 'ea95f51a2d4645410223d24cc7da9eb0e7095310c6e9f8756e8c51d67df13d9f'
    pins[HELPER/'eqnav/world.py'] = '6441467623a49950af2549496ddb27c3c8c5e3889829d833293a604d9209cfb2'
    for module in ('fixed_route_follower', 'ground_sweep', 'ground_sweep_view', 'portal_surface_audit',
                   'lateral_strip_audit', 'turn_disk_audit', 'ground_bsp_route', 'bsp_probe',
                   'pfs_archive', 'wld_inventory', 'portal_precision', 'portal_precision_view',
                   'tile_rounding', 'mesh_geometry', 'material_audit', 'map_alignment'):
        path = PROJECT/'eql_automation'/(module+'.py')
        pins[path] = sha256(path.read_bytes()).hexdigest()
    pins[Path(__file__)] = sha256(Path(__file__).read_bytes()).hexdigest()
    def verify():
        if any(p.is_symlink() or sha256(p.read_bytes()).hexdigest() != h for p,h in pins.items()):
            raise ValueError('Pinned portal repair input changed')
    verify()
    original = FixedRoute.load(args.plan, expected_sha256=args.plan_sha256, mesh_sha256=MESH_SHA)
    if original.zone != 'gfaydark':
        raise ValueError('This source-bound diagnostic supports GFay only')
    changes = dict(args.portal)
    if len(changes) != len(args.portal) or any(i < 0 or i >= len(original.segments)-1 for i in changes):
        raise ValueError('Repeated or out-of-range portal index')
    sys.path.insert(0, str(HELPER))
    from eqnav.world import MeshStore
    mesh = MeshStore(MESH.parent).load('gfaydark')
    view = GroundSweepView.load(MESH, zone='gfaydark')
    precision = (PortalPrecisionView(view,MESH,archive,zone='gfaydark',tile_rounding=True)
                 if args.tile_rounding else None)
    proposed = json.loads(args.plan.read_text())
    segments = proposed['segments']
    relocations = []
    turns = []
    with np.load(MESH, allow_pickle=False) as arrays:
        for index, fraction in sorted(changes.items()):
            a, b = segments[index]['polygon'], segments[index+1]['polygon']
            hits = np.flatnonzero((arrays['link_a'] == a) & (arrays['link_b'] == b))
            if len(hits) != 1:
                raise ValueError('Missing or ambiguous directed portal')
            edge = np.asarray(arrays['link_pts'][hits[0]], dtype=np.float64)
            xy = tuple(float(v) for v in ((1-fraction)*edge[0]+fraction*edge[1])[:2])
            heights = [_supported_detail_height(mesh, poly, *xy) for poly in (a,b)]
            if any(z is None for z in heights) or abs(heights[0]-heights[1]) > .01:
                raise ValueError('Relocated portal has no consistent ground seam')
            relocations.append({'index':index, 'raw_endpoint_fraction':fraction,
                'old_xy':segments[index]['points'][1][:2], 'new_xy':xy,
                'source_polygon':a, 'target_polygon':b, 'heights':heights})
            segments[index]['points'][1] = [*xy, heights[0]]
            segments[index+1]['points'][0] = [*xy, heights[1]]
            turns.append({'index':index, 'check':asdict(audit_turn_disk(mesh,a,b,xy,max_seconds=10))})
    affected = sorted(set(changes) | {i+1 for i in changes})
    strips, tubes = [], []
    for index in affected:
        if time.monotonic()-began > 120:
            raise TimeoutError('Portal repair diagnostic exceeded 120 seconds')
        segment = segments[index]
        start, end = map(tuple, segment['points'])
        poly = segment['polygon']
        if math.dist(start[:2], end[:2]) <= .5:
            raise ValueError('Relocation would overlap endpoint acceptance disks')
        strips.append({'index':index, 'check':asdict(audit_segment_strip(mesh,poly,start[:2],end[:2],
            half_width=original.half_width, max_samples=4096,max_seconds=15))})
        distance = math.dist(start[:2], end[:2])
        heading = math.degrees(math.atan2(end[0]-start[0],end[1]-start[1])) % 360
        divisions = math.ceil(distance/2.)
        if divisions > 512:
            raise ValueError('Local tube exceeds bounded partition count')
        checks = []
        for j in range(divisions):
            if time.monotonic()-began > 120:
                raise TimeoutError('Portal repair diagnostic exceeded 120 seconds')
            xy = tuple(start[k]+(end[k]-start[k])*j/divisions for k in range(2))
            z = _supported_detail_height(mesh,poly,*xy)
            if z is None:
                raise ValueError('Local tube center left its selected polygon ground')
            footprint = motion_footprint(xy,heading,distance/divisions,
                position_error=original.half_width, heading_error_degrees=0.,post_release_drift=0.)
            check, ids = view.check(footprint,reference=(*xy,z),component=int(view.components[poly]),
                vertical_window=distance/divisions+original.half_width+.1)
            raw_check=check;retry=None
            if precision is not None and check.reason in ('uncovered_ground_area','overlapping_ground_faces'):
                retry=precision.retry(check,footprint,ids,reference=(*xy,z),
                    component=int(view.components[poly]),
                    vertical_window=distance/divisions+original.half_width+.1,
                    maximum_source_z_difference=args.source_z_limit,allow_overlap=True)
                if retry.candidate:check=retry.coverage
            checks.append({'partition':j, 'result':asdict(check),
                           'failed_detail_id':None if check.failed_face is None else ids[check.failed_face],
                           'original':asdict(raw_check),
                           'precision_retry':None if retry is None else asdict(retry)})
            if not check.candidate:
                break
        tubes.append({'index':index, 'radius':original.half_width, 'partitions':divisions,
                      'checked':len(checks), 'candidate':len(checks)==divisions and all(c['result']['candidate'] for c in checks),
                      'checks':checks})
    lookup = BspPointLookup(WLDInventory(PFSArchive(archive).read_member('gfaydark.wld')))
    frame_control = verify_helper_bsp_frame(lookup,json.loads(MESH.with_suffix('.json').read_text()))
    points = [s['points'][0][:2] for s in segments]+[segments[-1]['points'][1][:2]]
    bsp = audit_ground_bsp_route(mesh,lookup,[s['polygon'] for s in segments],points,max_segments=len(segments))
    candidate = all(t['check']['candidate'] for t in turns+strips) and all(t['candidate'] for t in tubes) and bsp.candidate
    verify()
    report = {'format':'eql-fixed-portal-repair-v1','candidate':candidate,
        'relocations':relocations,'affected_segments':affected,'turns':turns,'strips':strips,'continuous_ground_tubes':tubes,
        'full_centerline_bsp':bsp.to_dict(),'frame_control':frame_control,
        'proposed_segments_sha256':sha256(json.dumps(segments,sort_keys=True).encode()).hexdigest(),
        'scope':'affected_ground_tubes_and_legacy_clearance_plus_full_centerline_BSP',
        'tile_precision':None if precision is None else {
            'source_z_limit_diagnostic_only':args.source_z_limit,
            'source_wld_sha256':precision.wld_sha256,
            'eligible_seams':len(precision.seams),
            'source_checked_only_for_precision_retries':True},
        'not_checked':['full_follower_replay','continuous_source_wall_headroom_BSP_sweep','live_scene_and_movement','camp_mobs'],
        'source_or_mesh_modified':False,'route_accepted':False,'real_client_accepted':False,'game_input_sent':False,
        'pins':{str(p):h for p,h in pins.items()},'seconds':time.monotonic()-began}
    with args.output_report.open('x') as out:
        json.dump(report,out,indent=2);out.write('\n')
    report_sha = sha256(args.output_report.read_bytes()).hexdigest()
    plan_sha = None
    if candidate:
        proposed['pins'].update({str(p):h for p,h in pins.items()})
        proposed['pins'][str(args.output_report)] = report_sha
        proposed['parent_plan_sha256'] = args.plan_sha256
        proposed['repair_report_sha256'] = report_sha
        proposed['maximum_seam_height_difference'] = max(abs(a['points'][1][2]-b['points'][0][2]) for a,b in zip(segments,segments[1:]))
        proposed['seconds'] = report['seconds']
        with args.output_plan.open('x') as out:
            json.dump(proposed,out,indent=2);out.write('\n')
        plan_sha = sha256(args.output_plan.read_bytes()).hexdigest()
    print(json.dumps({'candidate':candidate,'report':str(args.output_report),'report_sha256':report_sha,
        'plan':str(args.output_plan) if candidate else None,'plan_sha256':plan_sha,
        'bsp_spans':bsp.bsp_spans,'seconds':report['seconds']}))


def portal(value):
    try:
        index, fraction = value.split(':')
        index,fraction = int(index),float(fraction)
        if index < 0 or not math.isfinite(fraction) or not 0 < fraction < 1:
            raise ValueError()
        return index,fraction
    except ValueError:
        raise argparse.ArgumentTypeError('Use nonnegative_index:fraction strictly between zero and one')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',required=True,type=Path)
    parser.add_argument('--plan-sha256',required=True)
    parser.add_argument('--portal',required=True,action='append',type=portal)
    parser.add_argument('--output-plan',required=True,type=Path)
    parser.add_argument('--output-report',required=True,type=Path)
    parser.add_argument('--tile-rounding',action='store_true',
        help='Offline source-supported exact tile-side correction for local coverage gaps/overlaps')
    parser.add_argument('--source-z-limit',type=float,default=.6,
        help='Explicit source/bake sensitivity for tile retries; not a live error bound (default .6)')
    args = parser.parse_args()
    for key in ('plan','output_plan','output_report'):
        value = getattr(args,key).expanduser()
        if value.parent.resolve() != (STORE/'nav-candidates').resolve() or value.is_symlink() or value.suffix != '.json':
            parser.error('Use regular JSON paths directly in private nav-candidates')
        setattr(args,key,value)
    if (not args.plan.is_file() or not 0 < args.plan.stat().st_size <= 10*1024*1024
            or args.output_plan.exists() or args.output_report.exists() or args.output_plan == args.output_report
            or len(args.plan_sha256) != 64 or any(c not in '0123456789abcdef' for c in args.plan_sha256)
            or len(args.portal) > 8 or not math.isfinite(args.source_z_limit)
            or not 0<args.source_z_limit<=2 or (args.source_z_limit!=.6 and not args.tile_rounding)):
        parser.error('Use a bounded pinned input, distinct new outputs and at most eight relocations')
    os.umask(0o077)
    os.nice(15)
    run(args)


if __name__ == '__main__':
    main()
