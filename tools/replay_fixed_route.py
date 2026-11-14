#!/usr/bin/env python3
"""Replay the copied GFay plan with idealized motion and real retained steering.

This opens no game or device. Synthetic alignment/position observations test
controller behavior, not real-client timing, collisions, UI or acceptance.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from dataclasses import asdict
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys
import time

PROJECT = Path(__file__).resolve().parents[1]
STORE = Path.home() / ".local/share/eql-automation"
PLAN = STORE / "nav-candidates/gfay-fixed-segment-plan-0.41.48.json"
PLAN_SHA = "145679ec15111cf2d319ca630c66da693cc69863bdef594f67a46989c18592a4"
MESH = STORE / "navmesh/nov12-7e3cd28-store/gfaydark.npz"
MESH_SHA = "5f8e16c5bcd2221ba273f681750ca480349780524d23609c059a3e817df6abd9"
HELPER = STORE / "owner-assist/0.39.4"
SEAM_EXPERIMENT = STORE / "nav-candidates/gfay-source-seam-experiment-0.41.52.json"
SEAM_EXPERIMENT_SHA = "0ca4fa85769c8e94e236ce69f09da180e70597006d2cb4934fc191598d1eb076"
FLOOR_CHAIN = STORE/'nav-candidates/gfay-source-floor-chain-fast-0.41.58.json'
FLOOR_CHAIN_SHA = '06c0a1d0818826ca0913e94a05b26912f9be05b994fa328230857b42dd04a497'
SOURCE_PROFILE = STORE/'nav-candidates/gfay-tile-source-profile-0.41.57.json'
FLOOR_SEED_PLAN = STORE/'nav-candidates/gfay-west-portal-plan-0.41.53.json'
STATIC_EVIDENCE = STORE/'nav-candidates/gfay-static-source-inventory-0.41.60.json'
STATIC_EVIDENCE_SHA = '2fe5feee285285c36245d5fe96d4fc9e2e63b7bf25f94aceee71007c9014037a'
PINS = {
    PLAN: PLAN_SHA, MESH: MESH_SHA,
    MESH.with_suffix(".json"): "ac9591eb63e1394363ad37d7d0ca6609a1ebe11fd8786bedb5b165b833e2eb82",
    HELPER / "eqnav/steer.py": "6bb94a7d52e61840f6e2dfed3be712d2a1378424f57cf78f9151e969a688e358",
    HELPER / "eqnav/mesh.py": "89682ac2f6ee6ad4fc4e4530d946e4d7d883d860573a958d45f7cd7a074fef85",
}


def local_seam_diagnostic(view, footprint, reference, component, window, detail_ids, evidence):
    """Retry only inside the pinned source triangle; never modify the mesh.

    This is a diagnostic local XY correction for one known reciprocal portal.
    It neither changes source/baked heights nor generalizes to other gaps.
    """
    from eql_automation.ground_sweep import GroundFace, check_ground_coverage, cross, hull
    triangle = hull(tuple(p[:2]) for p in evidence['source_overlaps'][0]['vertices_wld'])
    if len(triangle) != 3:
        return None
    for x, y in footprint:
        if any(cross(a, triangle[(i+1) % 3], (y, x)) <= 0 for i, a in enumerate(triangle)):
            return None
    if not {31668, 32479}.issubset({int(view.polys[i]) for i in detail_ids}):
        return None
    west, east = 1761.2440185546875, 1761.244140625
    midpoint = (west + east) / 2
    faces = []
    for detail_id in detail_ids:
        polygon = int(view.polys[detail_id])
        vertices = []
        for x, y, z in view.triangles[detail_id]:
            if (polygon == 31668 and x == west) or (polygon == 32479 and x == east):
                x = midpoint
            vertices.append((float(x), float(y), float(z)))
        faces.append(GroundFace(tuple(vertices), int(view.areas[polygon]), int(view.components[polygon])))
    return check_ground_coverage(footprint, tuple(faces), reference=tuple(reference),
                                  component=component, vertical_window=window)


class ClientObservationError(ValueError):
    def __init__(self,message,evidence):
        super().__init__(message)
        self.evidence=evidence


def client_observation_pair(observer,physical_position,*,route,segment_index,
                            height_calibration,motion_calibration_record_id,floor_chain,
                            release,sequence):
    """Model two client log observations without modifying the simulated pose.

    The physical source floor generates raw Z. The real ground producer then
    independently samples source and baked heights at the printed XY. These
    synthetic observations exercise steering, never establish live calibration.
    """
    from eql_automation.location_log import RawLocationFix
    from tools.probe_route_ground_observer import synthetic_location
    physical_xy=tuple(physical_position[:2])
    source_z,_=(observer.source.source_floor_at(physical_xy) if floor_chain is None
                else floor_chain.floor_at(physical_xy))
    coordinates,body=synthetic_location(physical_position,source_z,
        height_calibration.raw_z_minus_source_z,client_format=True)
    pair=[]
    for index,offset in enumerate((.13,.53),1):
        at=release+offset
        raw=RawLocationFix(height_calibration.zone_id,height_calibration.zone_display_name,
            coordinates,datetime(2026,11,14),at,height_calibration.log_epoch,
            sequence+index,height_calibration.zone_generation)
        try:
            pair.append(observer.observe(raw,route=route,segment_index=segment_index,
                height_calibration=height_calibration,
                motion_calibration_record_id=motion_calibration_record_id,now=at,
                floor_chain=floor_chain))
        except ValueError as error:
            raise ClientObservationError(str(error),{
                'raw_coordinates':coordinates,'synthetic_log_body':body,
                'physical_source_z':source_z,'log_line_seq':sequence+index,
                'received_monotonic':at}) from error
    return tuple(pair),{'physical_source_z':source_z,'synthetic_log_body':body}


def run(output, *, speed, min_hold, ground_sweep=False, local_seam_experiment=False,
        shorten_ground_step=False, plan=PLAN, plan_sha256=PLAN_SHA, precision_portals=False,
        source_z_limit=.6, wall_budget=35., precision_overlaps=False, maximum_portal_ulp_steps=1,
        tile_rounding=False,source_floor_chain=False,static_objects=False,bsp_volume=False,
        client_observations=False):
    began = time.monotonic()
    began_cpu = time.process_time()
    sys.path[:0] = [str(PROJECT), str(HELPER)]
    from eql_automation.fixed_route_follower import FixedRoute, FixedRouteFollower, RouteHalt
    from eql_automation.bsp_detail_view import BspDetailMeshView
    from eql_automation.portal_surface_audit import _supported_detail_height
    from eql_automation.ground_binding import (AlignedWldFix, GroundGeometryEvidence,
        HeightCalibration, MeshProjection, SourceFloorObservation)
    from eql_automation.ground_sweep_view import GroundSweepView
    from eql_automation.portal_precision_view import PortalPrecisionView
    from eql_automation.source_floor_chain import SourceFloorChain
    from eql_automation.floor_replay import bind_floor_replay_seed,check_floor_trial
    from eql_automation.static_floor_guard import check_static_floor
    from eql_automation.bsp_floor_guard import check_bsp_floor
    from eql_automation.location_log import RawLocationFix
    import numpy as np
    from eqnav import steer
    if precision_overlaps and not precision_portals:
        raise ValueError('Overlap diagnostics require --precision-portals')
    if maximum_portal_ulp_steps not in (1,2) or (maximum_portal_ulp_steps!=1 and not precision_portals):
        raise ValueError('Two-ULP diagnostics require --precision-portals')
    if tile_rounding and (not precision_portals or maximum_portal_ulp_steps!=1):
        raise ValueError('Tile rounding requires precision portals and excludes ULP overrides')
    if source_floor_chain and not tile_rounding:
        raise ValueError('Conditional source floor requires the explicit tile diagnostic')
    if static_objects and not source_floor_chain:
        raise ValueError('Static occupancy requires a checked source-floor chain')
    if bsp_volume and not static_objects:
        raise ValueError('BSP volume requires terrain and static occupancy checks')
    if client_observations and not source_floor_chain:
        raise ValueError('Client-format observations require committed source-floor context')
    pins = dict(PINS)
    pins[plan] = plan_sha256
    for path in (Path(__file__), PROJECT / "eql_automation/fixed_route_follower.py",
                 PROJECT / "eql_automation/bsp_detail_view.py",
                 PROJECT / "eql_automation/portal_surface_audit.py",
                 PROJECT / "eql_automation/ground_binding.py"):
        pins[path] = sha256(path.read_bytes()).hexdigest()
    if ground_sweep:
        for path in (PROJECT / 'eql_automation/ground_sweep.py', PROJECT / 'eql_automation/ground_sweep_view.py'):
            pins[path] = sha256(path.read_bytes()).hexdigest()
    source_archive = STORE/'client-data/retail-full/assets/gfaydark.s3d'
    pins[source_archive] = 'ea95f51a2d4645410223d24cc7da9eb0e7095310c6e9f8756e8c51d67df13d9f'
    for module in ('portal_precision','portal_precision_view','pfs_archive','wld_inventory',
                   'mesh_geometry','material_audit','map_alignment','ground_sweep_view','tile_rounding'):
        path = PROJECT/'eql_automation'/(module+'.py')
        pins[path] = sha256(path.read_bytes()).hexdigest()
    format_evidence=None
    if client_observations:
        from eql_automation.ground_observer import RouteGroundObserver
        from tools.probe_route_ground_observer import LOCATION_LOG,LOCATION_LOG_SHA,observed_location_format
        pins[LOCATION_LOG]=LOCATION_LOG_SHA
        for path in (PROJECT/'tools/probe_route_ground_observer.py',
                     PROJECT/'eql_automation/ground_observer.py',PROJECT/'eql_automation/location_log.py'):
            pins[path]=sha256(path.read_bytes()).hexdigest()
    if precision_portals:
        if local_seam_experiment or not ground_sweep:
            raise ValueError('Precision retry requires ground checks and excludes the older seam experiment')
    floor_evidence=None;floor_seed_binding=None
    if source_floor_chain:
        if FLOOR_CHAIN.is_symlink() or sha256(FLOOR_CHAIN.read_bytes()).hexdigest()!=FLOOR_CHAIN_SHA:
            raise ValueError('Completed conditional floor-chain evidence changed')
        floor_evidence=json.loads(FLOOR_CHAIN.read_text())
        if (not floor_evidence['complete_conditional_source_chain'] or floor_evidence['budget_exhausted']
                or floor_evidence['passed_cells']!=floor_evidence['expected_cells']
                or str(FLOOR_SEED_PLAN) not in floor_evidence['pins']
                or str(SOURCE_PROFILE) not in floor_evidence['pins']):
            raise ValueError('Floor proof is incomplete or has no pinned seed plan')
        pins.update({Path(p):h for p,h in floor_evidence['pins'].items()})
        pins[FLOOR_CHAIN]=FLOOR_CHAIN_SHA
        path=PROJECT/'eql_automation/floor_replay.py';pins[path]=sha256(path.read_bytes()).hexdigest()
    static_evidence=None;static_view=None;static_trials=[]
    if static_objects:
        if STATIC_EVIDENCE.is_symlink() or sha256(STATIC_EVIDENCE.read_bytes()).hexdigest()!=STATIC_EVIDENCE_SHA:
            raise ValueError('Static parity evidence changed')
        static_evidence=json.loads(STATIC_EVIDENCE.read_text())
        if (static_evidence['exact_transformed_solid_multiset_matches_retained_baker'] is not True
                or static_evidence['missing_from_adapter']!=0 or static_evidence['extra_in_adapter']!=0):
            raise ValueError('Static inventory has no complete retained-bake parity')
        pins.update({Path(p):h for p,h in static_evidence['pins'].items()})
        pins[STATIC_EVIDENCE]=STATIC_EVIDENCE_SHA
        path=PROJECT/'eql_automation/static_floor_guard.py';pins[path]=sha256(path.read_bytes()).hexdigest()
    bsp_view=None;bsp_trials=[];bsp_frame=None
    if bsp_volume:
        for module in ('bsp_floor_guard','bsp_volume','bsp_probe','region_audit','ground_bsp_route'):
            path=PROJECT/'eql_automation'/(module+'.py');pins[path]=sha256(path.read_bytes()).hexdigest()
    seam_evidence = None
    if local_seam_experiment:
        pins[SEAM_EXPERIMENT] = SEAM_EXPERIMENT_SHA
        if sha256(SEAM_EXPERIMENT.read_bytes()).hexdigest() != SEAM_EXPERIMENT_SHA:
            raise ValueError('Local source-seam experiment changed')
        seam_evidence = json.loads(SEAM_EXPERIMENT.read_text())
        if (seam_evidence['source_continuity_supported'] is not True
                or len(seam_evidence['source_overlaps']) != 1
                or seam_evidence['source_or_mesh_modified'] is not False):
            raise ValueError('Unexpected local seam source evidence')
        pins.update({Path(path): digest for path, digest in seam_evidence['pins'].items()})
    def verify():
        if any(p.is_symlink() or sha256(p.read_bytes()).hexdigest() != h for p, h in pins.items()):
            raise ValueError("Replay source changed")
    verify()
    if client_observations:
        format_evidence=observed_location_format(LOCATION_LOG.read_text(errors='replace'))
    route = FixedRoute.load(plan, expected_sha256=plan_sha256, mesh_sha256=MESH_SHA)
    if floor_evidence is not None:
        baseline=FixedRoute.load(FLOOR_SEED_PLAN,
            expected_sha256=floor_evidence['pins'][str(FLOOR_SEED_PLAN)],mesh_sha256=MESH_SHA)
        floor_seed_binding=bind_floor_replay_seed(baseline,route)
    mesh = BspDetailMeshView.load(MESH, zone=route.zone)
    ground_view = GroundSweepView.load(MESH, zone=route.zone)
    source_view = PortalPrecisionView(ground_view,MESH,source_archive,zone=route.zone,
                                      maximum_ulp_steps=maximum_portal_ulp_steps,tile_rounding=tile_rounding)
    if static_evidence is not None:
        from eql_automation.static_source_view import StaticSourceView
        from eql_automation.pfs_archive import PFSArchive
        from eql_automation.wld_inventory import WLDInventory
        from eqnav import zonegeom
        archive=PFSArchive(source_archive)
        terrain=WLDInventory(archive.read_member('gfaydark.wld'))
        objects=WLDInventory(archive.read_member('objects.wld'))
        library=WLDInventory(PFSArchive(source_archive.with_name('gfaydark_obj.s3d')).read_member('gfaydark_obj.wld'))
        static_view=StaticSourceView.from_wld(objects,(library,),
            terrain_fragment_max=max(f.index for f in terrain.fragments),
            transform=zonegeom.place_vertices,transform_sha256=pins[HELPER/'eqnav/zonegeom.py'])
        if (static_view.inventory_sha256!=static_evidence['inventory_sha256']
                or len(static_view.sources)!=static_evidence['static_source_faces']):
            raise ValueError('Complete static inventory did not reproduce')
        if bsp_volume:
            from eql_automation.bsp_probe import BspPointLookup
            from eql_automation.bsp_volume import BspVolumeView
            from eql_automation.ground_bsp_route import verify_helper_bsp_frame
            lookup=BspPointLookup(terrain)
            bsp_frame=verify_helper_bsp_frame(lookup,json.loads(MESH.with_suffix('.json').read_text()))
            bsp_view=BspVolumeView(lookup,region_count=terrain.bsp_region_count,wld_sha256=terrain.sha256)
    # Check all selected route adjacencies against actual reciprocal links,
    # area and component arrays, independently of each synthetic observation.
    with np.load(MESH, allow_pickle=False) as data:
        links = set(zip(map(int,data['link_a'].reshape(-1)), map(int,data['link_b'].reshape(-1))))
    portal_pairs = set()
    for first,second in zip(route.segments,route.segments[1:]):
        a,b = first.polygon,second.polygon
        if ((a,b) not in links or (b,a) not in links or
                int(ground_view.areas[a]) != 63 or int(ground_view.areas[b]) != 63 or
                ground_view.components[a] != ground_view.components[b]):
            raise ValueError('Fixed replay route lacks a reciprocal dry same-component portal')
        portal_pairs.add(tuple(sorted((a,b))))
    sweep_view = ground_view if ground_sweep else None
    precision_view = source_view if precision_portals else None
    if ground_sweep:
        from eql_automation.ground_sweep import motion_footprint
    start = route.segments[0].start
    heading = steer.bearing(*start[:2], *route.segments[0].end[:2])
    calibration = "synthetic-replay-not-live-alignment"
    # Verification flags below are isolated test fixtures, NOT a live verifier.
    # Actual source Z is sampled independently; character height is an explicit
    # synthetic assumption. No historical G0 record becomes a live calibration.
    height_calibration = HeightCalibration('synthetic-source-height-not-live', route.zone,
        54, 'Greater Faydark', 1, 1, source_view.archive_sha256, source_view.wld_sha256,
        2.564, .05, 0, 0., 1e6, live_verified=True)
    proof = {'simulation_only':True, 'mesh':MESH_SHA, 'plan':plan_sha256,
        'source_archive':source_view.archive_sha256, 'source_wld':source_view.wld_sha256,
        'source_z_limit':source_z_limit, 'portal_pairs':sorted(portal_pairs)}
    if floor_evidence is not None:
        proof['conditional_source_chain_sha256']=FLOOR_CHAIN_SHA
        proof['seed_binding']=asdict(floor_seed_binding)
    proof_sha = sha256(json.dumps(proof,sort_keys=True).encode()).hexdigest()
    geometry = GroundGeometryEvidence(route.zone, MESH_SHA, source_view.archive_sha256,
        source_view.wld_sha256, proof_sha, source_z_limit, tuple(sorted(portal_pairs)), True)
    observer=(RouteGroundObserver(mesh=mesh,ground=ground_view,source=source_view,
        geometry_evidence=geometry,reciprocal_links=links) if client_observations else None)
    motion = steer.Motion(run_speed=speed, turn_rate=170., right_sign=-1,
                          turn_latency=.03, back_speed=speed / 2)
    runner = FixedRouteFollower(route, legacy=steer, motion=motion, heading=heading,
                               calibration_record_id=calibration, generation=1,
                               height_calibration=height_calibration, geometry_evidence=geometry,
                               generation_reader=lambda: 1, mode_reader=lambda: "measurement")
    position, seq, clock = list(start), 0, 100.
    history, recent, portal_samples = [], [], []
    sweep_checks, sweep_failure = 0, None
    local_seam_retries = []
    ground_shortening_trials = []
    precision_retries = []
    ground_observations = {'count':0, 'minimum_baked_minus_source_z':None,
                          'maximum_baked_minus_source_z':None, 'last':None}
    observation_failure=None
    observation_bounds={'maximum_physical_observed_xy_difference':0.,
                        'maximum_raw_height_residual':0.}
    floor_chain=None;floor_trials=[];initial_floor_step=None
    if floor_evidence is not None:
        if floor_evidence['source_wld_sha256']!=source_view.wld_sha256:
            raise ValueError('Conditional floor proof source identity changed')
        seed=floor_evidence['seed']
        floor_chain=SourceFloorChain(inventory_sha256=source_view.wld_sha256,
            seed_evidence_sha256=sha256(json.dumps(seed,sort_keys=True).encode()).hexdigest(),
            seed_ids=tuple(tuple(k) for k in seed['selected_ids']),
            body_height=floor_evidence['hypothetical_body_height'])
        initial_footprint=tuple(tuple(p) for p in json.loads(SOURCE_PROFILE.read_text())['cells'][0]['footprint'])
    def stopped_pair(release):
        nonlocal seq, clock, observation_failure
        if observer is not None:
            try:
                aligned,metadata=client_observation_pair(observer,position,route=route,
                    segment_index=runner.index,height_calibration=height_calibration,
                    motion_calibration_record_id=calibration,floor_chain=floor_chain,
                    release=release,sequence=seq)
            except ValueError as exception:
                observation_failure={**getattr(exception,'evidence',{}),
                    'physical_package_xyz':list(position),'segment':runner.index,
                    'floor_chain_index':floor_chain.index,'reason':str(exception)}
                raise RouteHalt('Client-format ground observation: '+str(exception)) from exception
            last=aligned[-1];observed=last.mesh_projection.package_xyz
            source_z=last.source_floor.ground_wld_xyz[2]
            delta=observed[2]-source_z
            ground_observations['count']+=1
            for key,operation in (('minimum_baked_minus_source_z',min),('maximum_baked_minus_source_z',max)):
                old=ground_observations[key]
                ground_observations[key]=delta if old is None else operation(old,delta)
            ground_observations['last']={**metadata,'physical_package_xyz':list(position),
                'package_xyz':observed,'raw_coordinates':last.raw_fix.raw_coordinates,
                'source_z':source_z,'source_surface_ids':last.source_floor.source_surface_ids,
                'polygon':last.mesh_projection.polygon,'floor_chain_index':floor_chain.index}
            observation_bounds['maximum_physical_observed_xy_difference']=max(
                observation_bounds['maximum_physical_observed_xy_difference'],math.dist(position[:2],observed[:2]))
            observation_bounds['maximum_raw_height_residual']=max(
                observation_bounds['maximum_raw_height_residual'],
                abs(last.raw_fix.raw_coordinates[2]-height_calibration.raw_z_minus_source_z-source_z))
            seq=last.raw_fix.log_line_seq;clock=last.raw_fix.received_monotonic
            runner.observe_stopped(*aligned,released_at=release,now=clock)
            return
        segment = route.segments[runner.index]
        support = None
        for other,portal in ((runner.index, None), (runner.index-1, segment.start),
                              (runner.index+1, segment.end)):
            if not 0 <= other < len(route.segments):
                continue
            if portal is not None and math.dist(position[:2], portal[:2]) > runner.radius:
                continue
            poly = route.segments[other].polygon
            z = _supported_detail_height(mesh, poly, *position[:2])
            if (z is not None and (portal is None or abs(z-portal[2]) <= runner.radius+runner.height_tolerance)):
                support = poly,z
                break
        if support is None:
            raise RouteHalt('No current/adjacent selected polygon supports stopped point')
        poly,z = support
        position[2] = z
        try:
            source_z,source_ids = (source_view.source_floor_at(position[:2]) if floor_chain is None else
                                  floor_chain.floor_at(tuple(position[:2])))
        except ValueError as exception:
            raise RouteHalt('Source ground observation: ' + str(exception)) from exception
        delta = z-source_z
        ground_observations['count'] += 1
        ground_observations['minimum_baked_minus_source_z'] = min(delta,
            delta if ground_observations['minimum_baked_minus_source_z'] is None else ground_observations['minimum_baked_minus_source_z'])
        ground_observations['maximum_baked_minus_source_z'] = max(delta,
            delta if ground_observations['maximum_baked_minus_source_z'] is None else ground_observations['maximum_baked_minus_source_z'])
        ground_observations['last'] = {'package_xyz':list(position), 'source_z':source_z,
                                     'source_surface_ids':source_ids,'polygon':poly}
        neighbors = tuple(sorted(b if a==poly else a for a,b in portal_pairs if poly in (a,b)))
        aligned = []
        for offset in (.13, .53):
            seq += 1
            clock = release + offset
            ground_wld = (position[1], position[0], source_z)
            raw_wld = (*ground_wld[:2], source_z + height_calibration.raw_z_minus_source_z)
            raw = RawLocationFix(54, "Greater Faydark", raw_wld, datetime(2026, 11, 14),
                                 clock, 1, seq, 1)
            source = SourceFloorObservation(raw,ground_wld,source_view.archive_sha256,
                source_view.wld_sha256,source_ids,1,True)
            projection = MeshProjection(raw,tuple(position),MESH_SHA,poly,int(ground_view.areas[poly]),
                int(ground_view.components[poly]),source_view.archive_sha256,source_view.wld_sha256,
                source_ids,proof_sha,source_z_limit,neighbors,True,True)
            aligned.append(AlignedWldFix(raw, source, projection, height_calibration,
                                        route.zone, calibration, True))
        runner.observe_stopped(*aligned, released_at=release, now=clock)
    error = None
    try:
        if floor_chain is not None:
            initial_floor_step=floor_chain.advance(initial_footprint,source_view.source_faces_for_footprint(initial_footprint))
            if not initial_floor_step.candidate:
                raise RouteHalt('Initial conditional floor: '+initial_floor_step.reason)
        stopped_pair(clock)
        for step in range(10000):
            if runner.phase == "arrived":
                break
            if time.monotonic() - began > wall_budget:
                raise RouteHalt("Offline replay wall-clock budget exceeded")
            index = runner.index
            segment = route.segments[index]
            proposal = runner.propose(clock + .01)
            seconds = runner.suggest_hold(proposal, minimum_seconds=min_hold,
                                          maximum_seconds=.15 if proposal.turn else .1)
            next_floor_chain=None
            if sweep_view is not None:
                # Deliberately hypothetical: these are NOT current client
                # speed, heading, latency, body-size or drift measurements.
                trials = []
                precision_last = None
                while True:
                    reach = (speed * 1.2 * (seconds + .02)) if proposal.forward else 0.
                    footprint = motion_footprint(tuple(position[:2]), heading, reach,
                        position_error=.05, heading_error_degrees=2., post_release_drift=.05, extra_radius=.2)
                    window = max(math.dist(position[:2], p) for p in footprint) + .05
                    check, detail_ids = sweep_view.check(footprint, reference=tuple(position),
                        component=int(sweep_view.components[segment.polygon]), vertical_window=window)
                    sweep_checks += 1
                    precision_last = None
                    if floor_chain is not None:
                        next_floor_chain,check=check_floor_trial(source_view,floor_chain,check,footprint,detail_ids,
                            reference=tuple(position),component=int(sweep_view.components[segment.polygon]),
                            vertical_window=window,maximum_source_z_difference=source_z_limit,
                            allow_overlap=precision_overlaps)
                        precision_last=check.precision_retry
                        floor_trials.append({'step':step,'segment':index,'hold':seconds,'trial':asdict(check)})
                        if check.candidate and static_view is not None:
                            cell_sources=source_view.source_faces_for_footprint(footprint)
                            static_check=check_static_floor(check,footprint,cell_sources,static_view)
                            static_trials.append({'step':step,'segment':index,'hold':seconds,
                                'footprint':footprint,'trial':asdict(static_check)})
                            if not static_check.candidate:
                                next_floor_chain=None
                                check=static_check
                            if check.candidate and bsp_view is not None:
                                bsp_check=check_bsp_floor(check,footprint,cell_sources,bsp_view)
                                bsp_trials.append({'step':step,'segment':index,'hold':seconds,
                                    'footprint':footprint,'trial':asdict(bsp_check)})
                                if not bsp_check.candidate:
                                    next_floor_chain=None
                                    check=bsp_check
                    elif (check.reason == 'uncovered_ground_area' or
                            (precision_overlaps and check.reason == 'overlapping_ground_faces')) and precision_view is not None:
                        precision_last = precision_view.retry(check,footprint,detail_ids,
                            reference=tuple(position),component=int(sweep_view.components[segment.polygon]),
                            vertical_window=window,maximum_source_z_difference=source_z_limit,
                            allow_overlap=precision_overlaps)
                        precision_retries.append({'step':step,'segment':index,'hold':seconds,
                            'original':asdict(check),'retry':asdict(precision_last)})
                        if precision_last.candidate:
                            check = precision_last.coverage
                    if check.reason == 'uncovered_ground_area' and seam_evidence is not None:
                        retry = local_seam_diagnostic(sweep_view, footprint, position,
                            int(sweep_view.components[segment.polygon]), window, detail_ids, seam_evidence)
                        if retry is not None:
                            local_seam_retries.append({'step': step, 'segment': index,
                                'original': asdict(check), 'local_retry': asdict(retry)})
                            check = retry
                    trials.append({'hold': seconds, 'candidate': check.candidate, 'reason': check.reason})
                    if (check.candidate or not shorten_ground_step or not proposal.forward
                            or seconds <= min_hold or len(trials) >= 8):
                        break
                    # Recheck every reduced footprint; never assume monotonic
                    # safety or integrate a rejected trial into predicted motion.
                    seconds = max(min_hold, seconds / 2)
                if len(trials) > 1:
                    ground_shortening_trials.append({'step': step, 'segment': index, 'trials': trials})
                if not check.candidate:
                    sweep_failure = {'step': step, 'segment': index, 'proposal': asdict(proposal),
                        'reach': reach, 'footprint': footprint, 'reference': list(position),
                        'detail_ids': detail_ids, 'result': asdict(check),
                        'precision_retry':None if precision_last is None else asdict(precision_last)}
                    raise RouteHalt('Ground sweep: ' + check.reason)
            # Independent idealized actuation. No actual sender or swept-volume
            # guard is exercised. Reject leaving the selected polygon's detail.
            if proposal.turn:
                sign = motion.right_sign * (1 if proposal.turn == "right" else -1)
                heading = (heading + sign * motion.turn_rate * max(0., seconds - motion.turn_latency)) % 360
            elif proposal.forward:
                direction = math.radians(heading)
                next_xy = (position[0] + math.sin(direction) * speed * seconds,
                           position[1] + math.cos(direction) * speed * seconds)
                height = _supported_detail_height(mesh, segment.polygon, *next_xy)
                # Endpoint acceptance is a disk around an audited portal, not
                # exact equality. A minimum pulse can land just across its
                # shared boundary. Consult only the adjacent selected polygon
                # and only inside that endpoint disk, preserving its own Z.
                if height is None:
                    for other, portal in ((index - 1, segment.start), (index + 1, segment.end)):
                        if not 0 <= other < len(route.segments) or math.dist(next_xy, portal[:2]) > runner.radius:
                            continue
                        candidate = _supported_detail_height(mesh, route.segments[other].polygon, *next_xy)
                        if candidate is not None and abs(candidate - portal[2]) <= runner.radius + runner.height_tolerance:
                            height = candidate
                            portal_samples.append({"step": step, "segment": index, "support_segment": other,
                                                   "xy": list(next_xy), "height": height})
                            break
                if height is None:
                    raise RouteHalt("Idealized step leaves selected polygon detail surface")
                position[:] = [*next_xy, height]
            started = proposal.at + .01
            released = started + seconds
            runner.record_release(proposal, started_at=started, released_at=released)
            if floor_chain is not None:
                if next_floor_chain is None:
                    raise RouteHalt('No successful conditional floor trial to commit')
                floor_chain=next_floor_chain
            stopped_pair(released)
            recent.append({"step": step, "segment": index, "next_segment": runner.index,
                           "forward": proposal.forward, "turn": proposal.turn,
                           "hold": seconds, "position": list(position), "heading": heading,
                           "estimated_heading": runner.pose.heading, "phase": runner.phase})
            recent = recent[-10:]
            if len(history) < 50 or index != runner.index:
                history.append({"step": step, "segment": index, "next_segment": runner.index,
                                "forward": proposal.forward, "turn": proposal.turn,
                                "hold": seconds, "position": list(position), "phase": runner.phase})
            if client_observations:
                record={'observed_package_xyz':ground_observations['last']['package_xyz'],
                        'raw_coordinates':ground_observations['last']['raw_coordinates']}
                recent[-1].update(record)
                if history and history[-1]['step']==step:history[-1].update(record)
            if step%250==0:
                print(json.dumps({'replay_step':step,'segment':runner.index,
                                  'client_observations':client_observations}),flush=True)
        else:
            raise RouteHalt("Offline replay step budget exceeded")
    except RouteHalt as exception:
        error = str(exception)
        try:
            runner.halt(error)
        except RouteHalt:
            pass
    verify()
    report = {"format": "eql-fixed-route-replay-v1", "simulation_only": True,
              "game_input_sent": False, "real_client_accepted": False, "route_accepted": False,
              "speed": speed, "minimum_hold_seconds": min_hold,
              "assumptions": ["ideal_timed_motion", "synthetic_alignment_and_fixes", "no_dynamic_obstacles",
                              "source_ground_sampled_independently_from_copied_terrain",
                              "synthetic_character_height_above_source_2.564",
                              "mesh_detail_edge_projection_up_to_0.0005",
                              ("conditional_terrain_static_and_BSP_volume_no_dynamic_guard" if bsp_volume else
                               "conditional_terrain_and_static_occupancy_no_BSP_dynamic_guard" if static_objects else
                               "continuous_detail_ground_only_no_wall_BSP_dynamic_guard" if ground_sweep else
                               "endpoint_detail_sample_only_not_swept_guard")],
              "ground_sweep_assumptions": ({"speed_upper": speed * 1.2, "release_overrun_seconds": .02,
                    "heading_error_degrees": 2., "position_error": .05, "post_release_drift": .05,
                    "extra_radius": .2, "verified_live_calibration": False} if ground_sweep else None),
              "phase": runner.phase, "error": error, "segments_reached": runner.index,
              "wall_budget":wall_budget,"budget_exhausted":error=='Offline replay wall-clock budget exceeded',
              "total_segments": len(route.segments), "steps": runner.steps,
              "simulated_seconds": clock - 100., "wall_seconds": time.monotonic() - began,
              "cpu_seconds": time.process_time() - began_cpu,
              "position": position, "history": history, "recent": recent,
              "ground_observations":ground_observations,
              "client_observations":client_observations,
              "client_location_format":format_evidence,
              "observation_bounds":observation_bounds if client_observations else None,
              "observation_failure":observation_failure,
              "sweep_pose_source":"simulated physical pose and heading; not live observation guard integration",
              "ground_binding_fixture":proof,
              "adjacent_portal_samples": portal_samples,
              "continuous_ground_sweep": ground_sweep, "sweep_checks": sweep_checks,
              "sweep_failure": sweep_failure,
              "local_seam_experiment": local_seam_experiment,
              "local_seam_retries": local_seam_retries,
              "shorten_ground_step": shorten_ground_step,
              "ground_shortening_trials": ground_shortening_trials,
              "precision_portals":precision_portals,"precision_retries":precision_retries,
              "precision_overlaps":precision_overlaps,
              "conditional_source_floor_chain":None if floor_evidence is None else {
                  'evidence_sha256':FLOOR_CHAIN_SHA,'body_height_hypothesis':floor_evidence['hypothetical_body_height'],
                  'seed_binding':asdict(floor_seed_binding),
                  'initial':None if initial_floor_step is None else asdict(initial_floor_step),
                  'committed_cells':floor_chain.index,'last_proof_sha256':floor_chain.previous.proof_sha256 if floor_chain.previous else None,
                  'terrain_only':True,'live_verified':False},
              "source_floor_trials":floor_trials,
              "static_source":None if static_evidence is None else {
                  'parity_evidence_sha256':STATIC_EVIDENCE_SHA,
                  'inventory_sha256':static_view.inventory_sha256,
                  'source_faces':len(static_view.sources),'placements':len(static_view.identities),
                  'all_flags_retained':True,'dynamics_included':False,'live_collision_verified':False},
              "static_floor_trials":static_trials,
              "bsp_volume":None if bsp_view is None else {
                  'inventory_sha256':bsp_view.inventory_sha256,'wld_sha256':bsp_view.wld_sha256,
                  'frame_control':bsp_frame,'conservative_unclipped_traversal':True,
                  'maximum_node_visits_per_prism':4096,'maximum_depth':256,
                  'live_hazards_verified':False,'dynamics_included':False},
              "bsp_volume_trials":bsp_trials,
              "maximum_portal_ulp_steps":maximum_portal_ulp_steps,
              "tile_rounding":None if source_view.tile_grid is None else asdict(source_view.tile_grid),
              "precision_limits":({"maximum_source_baked_z_difference":source_z_limit,"source_boundary_margin":.002,
                    "vertical_bound_is_diagnostic_not_proven_bake_error":True,
                    "eligible_seams":len(precision_view.seams),"source_faces":len(precision_view.sources),
                    "source_wld_sha256":precision_view.wld_sha256} if precision_view is not None else None),
              "pins": {str(p): h for p, h in pins.items()}}
    with output.open("x") as out:
        json.dump(report, out, indent=2); out.write("\n")
    print(json.dumps({k: report[k] for k in ("phase", "error", "segments_reached", "steps", "wall_seconds")}))
    print(json.dumps({"artifact": str(output), "sha256": sha256(output.read_bytes()).hexdigest()}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument('--plan', type=Path, help='Optional explicitly pinned private fixed-plan candidate')
    parser.add_argument('--plan-sha256', help='Required SHA-256 when --plan is supplied')
    parser.add_argument("--speed", type=float, default=30.77,
                        help="Explicit idealized speed; default is historical G0, not current calibration")
    parser.add_argument("--min-hold", type=float, default=.02,
                        help="Hypothetical pulse granularity; not a live timing guarantee")
    parser.add_argument('--ground-sweep', action='store_true',
                        help='Check full detail-ground footprints with hypothetical uncertainty bounds')
    parser.add_argument('--local-seam-experiment', action='store_true',
                        help='Offline only: try one pinned source-supported XY seam correction')
    parser.add_argument('--precision-portals', action='store_true',
                        help='Offline only: retry bounded reciprocal rounding gaps with full source-ground support')
    parser.add_argument('--precision-overlaps', action='store_true',
                        help='Offline only: also attribute and retry bounded reciprocal detail overlaps')
    parser.add_argument('--maximum-portal-ulp-steps', type=int, choices=(1,2), default=1,
                        help='Explicit copied-data diagnostic portal rounding bound (default one float32 step)')
    parser.add_argument('--tile-rounding',action='store_true',
                        help='Offline only: require exact predicted adjacent float32 tile-side coordinates')
    parser.add_argument('--source-floor-chain',action='store_true',
                        help='Offline only: seed from pinned source-floor proof and recheck every proposed footprint')
    parser.add_argument('--static-objects',action='store_true',
                        help='Offline only: add parity-checked all-flag static occupancy to every accepted terrain trial')
    parser.add_argument('--bsp-volume',action='store_true',
                        help='Offline only: require no copied BSP labels in each complete possible-motion prism')
    parser.add_argument('--client-observations',action='store_true',
                        help='Drive steering with client-formatted raw positions through the exact ground producer')
    parser.add_argument('--source-z-limit',type=float,default=.6,
                        help='Diagnostic source/baked height-difference limit, not live calibration (default .6)')
    parser.add_argument('--wall-budget',type=float,default=35.,
                        help='Bounded offline wall-clock budget in seconds (default 35; maximum 600)')
    parser.add_argument('--shorten-ground-step', action='store_true',
                        help='Offline only: recheck successively shorter forward holds down to --min-hold')
    args = parser.parse_args()
    plan, plan_sha256 = PLAN, PLAN_SHA
    if args.plan is not None or args.plan_sha256 is not None:
        if (args.plan is None or args.plan_sha256 is None or len(args.plan_sha256) != 64
                or any(c not in '0123456789abcdef' for c in args.plan_sha256)):
            parser.error('--plan and its lowercase --plan-sha256 must be supplied together')
        plan, plan_sha256 = args.plan.expanduser(), args.plan_sha256
        if (plan.parent.resolve() != (STORE/'nav-candidates').resolve() or plan.is_symlink()
                or not plan.is_file() or not 0 < plan.stat().st_size <= 10*1024*1024):
            parser.error('Plan must be a bounded regular private nav-candidates file')
    if (args.local_seam_experiment or args.shorten_ground_step or args.precision_portals) and not args.ground_sweep:
        parser.error('Ground experiments require --ground-sweep')
    if args.local_seam_experiment and args.precision_portals:
        parser.error('Use only one precision experiment')
    if args.precision_overlaps and not args.precision_portals:
        parser.error('--precision-overlaps requires --precision-portals')
    if args.maximum_portal_ulp_steps!=1 and not args.precision_portals:
        parser.error('--maximum-portal-ulp-steps 2 requires --precision-portals')
    if args.tile_rounding and (not args.precision_portals or args.maximum_portal_ulp_steps!=1):
        parser.error('--tile-rounding requires --precision-portals and excludes ULP overrides')
    if args.source_floor_chain and not args.tile_rounding:
        parser.error('--source-floor-chain requires --tile-rounding')
    if args.static_objects and not args.source_floor_chain:
        parser.error('--static-objects requires --source-floor-chain')
    if args.bsp_volume and not args.static_objects:
        parser.error('--bsp-volume requires --static-objects')
    if args.client_observations and not args.source_floor_chain:
        parser.error('--client-observations requires --source-floor-chain')
    output = args.output.expanduser()
    if (output.parent.resolve() != (STORE / "nav-candidates").resolve() or output.exists()
            or output.is_symlink() or output.suffix != ".json"
            or not math.isfinite(args.speed) or not 0 < args.speed <= 100
            or not math.isfinite(args.min_hold) or not 0 < args.min_hold <= .1
            or not math.isfinite(args.source_z_limit) or not 0 < args.source_z_limit <= 2
            or not math.isfinite(args.wall_budget) or not 1 <= args.wall_budget <= 600):
        parser.error("use a new private nav-candidates JSON and finite bounded motion parameters")
    os.umask(0o077)
    os.nice(15)
    run(output, speed=args.speed, min_hold=args.min_hold, ground_sweep=args.ground_sweep,
        local_seam_experiment=args.local_seam_experiment, shorten_ground_step=args.shorten_ground_step,
        plan=plan, plan_sha256=plan_sha256,precision_portals=args.precision_portals,
        source_z_limit=args.source_z_limit,wall_budget=args.wall_budget,
        precision_overlaps=args.precision_overlaps,maximum_portal_ulp_steps=args.maximum_portal_ulp_steps,
        tile_rounding=args.tile_rounding,source_floor_chain=args.source_floor_chain,
        static_objects=args.static_objects,bsp_volume=args.bsp_volume,
        client_observations=args.client_observations)


if __name__ == "__main__":
    main()
