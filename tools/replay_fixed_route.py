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


def run(output, *, speed, min_hold, ground_sweep=False, local_seam_experiment=False,
        shorten_ground_step=False, plan=PLAN, plan_sha256=PLAN_SHA, precision_portals=False,
        source_z_limit=.6, wall_budget=35., precision_overlaps=False, maximum_portal_ulp_steps=1,
        tile_rounding=False):
    began = time.monotonic()
    sys.path[:0] = [str(PROJECT), str(HELPER)]
    from eql_automation.fixed_route_follower import FixedRoute, FixedRouteFollower, RouteHalt
    from eql_automation.bsp_detail_view import BspDetailMeshView
    from eql_automation.portal_surface_audit import _supported_detail_height
    from eql_automation.ground_binding import (AlignedWldFix, GroundGeometryEvidence,
        HeightCalibration, MeshProjection, SourceFloorObservation)
    from eql_automation.ground_sweep_view import GroundSweepView
    from eql_automation.portal_precision_view import PortalPrecisionView
    from eql_automation.location_log import RawLocationFix
    import numpy as np
    from eqnav import steer
    if precision_overlaps and not precision_portals:
        raise ValueError('Overlap diagnostics require --precision-portals')
    if maximum_portal_ulp_steps not in (1,2) or (maximum_portal_ulp_steps!=1 and not precision_portals):
        raise ValueError('Two-ULP diagnostics require --precision-portals')
    if tile_rounding and (not precision_portals or maximum_portal_ulp_steps!=1):
        raise ValueError('Tile rounding requires precision portals and excludes ULP overrides')
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
    if precision_portals:
        if local_seam_experiment or not ground_sweep:
            raise ValueError('Precision retry requires ground checks and excludes the older seam experiment')
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
    route = FixedRoute.load(plan, expected_sha256=plan_sha256, mesh_sha256=MESH_SHA)
    mesh = BspDetailMeshView.load(MESH, zone=route.zone)
    ground_view = GroundSweepView.load(MESH, zone=route.zone)
    source_view = PortalPrecisionView(ground_view,MESH,source_archive,zone=route.zone,
                                      maximum_ulp_steps=maximum_portal_ulp_steps,tile_rounding=tile_rounding)
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
    proof_sha = sha256(json.dumps(proof,sort_keys=True).encode()).hexdigest()
    geometry = GroundGeometryEvidence(route.zone, MESH_SHA, source_view.archive_sha256,
        source_view.wld_sha256, proof_sha, source_z_limit, tuple(sorted(portal_pairs)), True)
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
    def stopped_pair(release):
        nonlocal seq, clock
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
            source_z,source_ids = source_view.source_floor_at(position[:2])
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
                    if (check.reason == 'uncovered_ground_area' or
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
                              ("continuous_detail_ground_only_no_wall_BSP_dynamic_guard" if ground_sweep else
                               "endpoint_detail_sample_only_not_swept_guard")],
              "ground_sweep_assumptions": ({"speed_upper": speed * 1.2, "release_overrun_seconds": .02,
                    "heading_error_degrees": 2., "position_error": .05, "post_release_drift": .05,
                    "extra_radius": .2, "verified_live_calibration": False} if ground_sweep else None),
              "phase": runner.phase, "error": error, "segments_reached": runner.index,
              "wall_budget":wall_budget,"budget_exhausted":error=='Offline replay wall-clock budget exceeded',
              "total_segments": len(route.segments), "steps": runner.steps,
              "simulated_seconds": clock - 100., "wall_seconds": time.monotonic() - began,
              "position": position, "history": history, "recent": recent,
              "ground_observations":ground_observations,
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
    parser.add_argument('--source-z-limit',type=float,default=.6,
                        help='Diagnostic source/baked height-difference limit, not live calibration (default .6)')
    parser.add_argument('--wall-budget',type=float,default=35.,
                        help='Bounded offline wall-clock budget in seconds (default 35; maximum 120)')
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
    output = args.output.expanduser()
    if (output.parent.resolve() != (STORE / "nav-candidates").resolve() or output.exists()
            or output.is_symlink() or output.suffix != ".json"
            or not math.isfinite(args.speed) or not 0 < args.speed <= 100
            or not math.isfinite(args.min_hold) or not 0 < args.min_hold <= .1
            or not math.isfinite(args.source_z_limit) or not 0 < args.source_z_limit <= 2
            or not math.isfinite(args.wall_budget) or not 1 <= args.wall_budget <= 120):
        parser.error("use a new private nav-candidates JSON and finite bounded motion parameters")
    os.umask(0o077)
    os.nice(15)
    run(output, speed=args.speed, min_hold=args.min_hold, ground_sweep=args.ground_sweep,
        local_seam_experiment=args.local_seam_experiment, shorten_ground_step=args.shorten_ground_step,
        plan=plan, plan_sha256=plan_sha256,precision_portals=args.precision_portals,
        source_z_limit=args.source_z_limit,wall_budget=args.wall_budget,
        precision_overlaps=args.precision_overlaps,maximum_portal_ulp_steps=args.maximum_portal_ulp_steps,
        tile_rounding=args.tile_rounding)


if __name__ == "__main__":
    main()
