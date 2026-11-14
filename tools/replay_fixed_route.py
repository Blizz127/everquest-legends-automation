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
PINS = {
    PLAN: PLAN_SHA, MESH: MESH_SHA,
    MESH.with_suffix(".json"): "ac9591eb63e1394363ad37d7d0ca6609a1ebe11fd8786bedb5b165b833e2eb82",
    HELPER / "eqnav/steer.py": "6bb94a7d52e61840f6e2dfed3be712d2a1378424f57cf78f9151e969a688e358",
    HELPER / "eqnav/mesh.py": "89682ac2f6ee6ad4fc4e4530d946e4d7d883d860573a958d45f7cd7a074fef85",
}


def run(output, *, speed, min_hold, ground_sweep=False):
    began = time.monotonic()
    sys.path[:0] = [str(PROJECT), str(HELPER)]
    from eql_automation.fixed_route_follower import FixedRoute, FixedRouteFollower, RouteHalt
    from eql_automation.bsp_detail_view import BspDetailMeshView
    from eql_automation.portal_surface_audit import _supported_detail_height
    from eql_automation.g2_start_gate import AlignedWldFix
    from eql_automation.location_log import RawLocationFix
    from eqnav import steer
    pins = dict(PINS)
    for path in (Path(__file__), PROJECT / "eql_automation/fixed_route_follower.py",
                 PROJECT / "eql_automation/bsp_detail_view.py",
                 PROJECT / "eql_automation/portal_surface_audit.py"):
        pins[path] = sha256(path.read_bytes()).hexdigest()
    if ground_sweep:
        for path in (PROJECT / 'eql_automation/ground_sweep.py', PROJECT / 'eql_automation/ground_sweep_view.py'):
            pins[path] = sha256(path.read_bytes()).hexdigest()
    def verify():
        if any(p.is_symlink() or sha256(p.read_bytes()).hexdigest() != h for p, h in pins.items()):
            raise ValueError("Replay source changed")
    verify()
    route = FixedRoute.load(PLAN, expected_sha256=PLAN_SHA, mesh_sha256=MESH_SHA)
    mesh = BspDetailMeshView.load(MESH, zone=route.zone)
    sweep_view = None
    if ground_sweep:
        from eql_automation.ground_sweep import motion_footprint
        from eql_automation.ground_sweep_view import GroundSweepView
        sweep_view = GroundSweepView.load(MESH, zone=route.zone)
    start = route.segments[0].start
    heading = steer.bearing(*start[:2], *route.segments[0].end[:2])
    calibration = "synthetic-replay-not-live-alignment"
    motion = steer.Motion(run_speed=speed, turn_rate=170., right_sign=-1,
                          turn_latency=.03, back_speed=speed / 2)
    runner = FixedRouteFollower(route, legacy=steer, motion=motion, heading=heading,
                               calibration_record_id=calibration, generation=1,
                               generation_reader=lambda: 1, mode_reader=lambda: "measurement")
    position, seq, clock = list(start), 0, 100.
    history, recent, portal_samples = [], [], []
    sweep_checks, sweep_failure = 0, None
    def stopped_pair(release):
        nonlocal seq, clock
        aligned = []
        for offset in (.13, .53):
            seq += 1
            clock = release + offset
            ground_wld = (position[1], position[0], position[2])
            raw = RawLocationFix(54, "Greater Faydark", ground_wld, datetime(2026, 11, 14),
                                 clock, 1, seq, 1)
            aligned.append(AlignedWldFix(raw, ground_wld, route.zone, MESH_SHA, calibration, True))
        runner.observe_stopped(*aligned, released_at=release, now=clock)
    stopped_pair(clock)
    error = None
    try:
        for step in range(10000):
            if runner.phase == "arrived":
                break
            if time.monotonic() - began > 35:
                raise RouteHalt("Offline replay wall-clock budget exceeded")
            index = runner.index
            segment = route.segments[index]
            proposal = runner.propose(clock + .01)
            seconds = runner.suggest_hold(proposal, minimum_seconds=min_hold,
                                          maximum_seconds=.15 if proposal.turn else .1)
            if sweep_view is not None:
                # Deliberately hypothetical: these are NOT current client
                # speed, heading, latency, body-size or drift measurements.
                reach = (speed * 1.2 * (seconds + .02)) if proposal.forward else 0.
                footprint = motion_footprint(tuple(position[:2]), heading, reach,
                    position_error=.05, heading_error_degrees=2., post_release_drift=.05, extra_radius=.2)
                window = max(math.dist(position[:2], p) for p in footprint) + .05
                check, detail_ids = sweep_view.check(footprint, reference=tuple(position),
                    component=int(sweep_view.components[segment.polygon]), vertical_window=window)
                sweep_checks += 1
                if not check.candidate:
                    sweep_failure = {'step': step, 'segment': index, 'proposal': asdict(proposal),
                        'reach': reach, 'footprint': footprint, 'reference': list(position),
                        'detail_ids': detail_ids, 'result': asdict(check)}
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
                              ("continuous_detail_ground_only_no_wall_BSP_dynamic_guard" if ground_sweep else
                               "endpoint_detail_sample_only_not_swept_guard")],
              "ground_sweep_assumptions": ({"speed_upper": speed * 1.2, "release_overrun_seconds": .02,
                    "heading_error_degrees": 2., "position_error": .05, "post_release_drift": .05,
                    "extra_radius": .2, "verified_live_calibration": False} if ground_sweep else None),
              "phase": runner.phase, "error": error, "segments_reached": runner.index,
              "total_segments": len(route.segments), "steps": runner.steps,
              "simulated_seconds": clock - 100., "wall_seconds": time.monotonic() - began,
              "position": position, "history": history, "recent": recent,
              "adjacent_portal_samples": portal_samples,
              "continuous_ground_sweep": ground_sweep, "sweep_checks": sweep_checks,
              "sweep_failure": sweep_failure,
              "pins": {str(p): h for p, h in pins.items()}}
    with output.open("x") as out:
        json.dump(report, out, indent=2); out.write("\n")
    print(json.dumps({k: report[k] for k in ("phase", "error", "segments_reached", "steps", "wall_seconds")}))
    print(json.dumps({"artifact": str(output), "sha256": sha256(output.read_bytes()).hexdigest()}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--speed", type=float, default=30.77,
                        help="Explicit idealized speed; default is historical G0, not current calibration")
    parser.add_argument("--min-hold", type=float, default=.02,
                        help="Hypothetical pulse granularity; not a live timing guarantee")
    parser.add_argument('--ground-sweep', action='store_true',
                        help='Check full detail-ground footprints with hypothetical uncertainty bounds')
    args = parser.parse_args()
    output = args.output.expanduser()
    if (output.parent.resolve() != (STORE / "nav-candidates").resolve() or output.exists()
            or output.is_symlink() or output.suffix != ".json"
            or not math.isfinite(args.speed) or not 0 < args.speed <= 100
            or not math.isfinite(args.min_hold) or not 0 < args.min_hold <= .1):
        parser.error("use a new private nav-candidates JSON and finite bounded motion parameters")
    os.umask(0o077)
    os.nice(15)
    run(output, speed=args.speed, min_hold=args.min_hold, ground_sweep=args.ground_sweep)


if __name__ == "__main__":
    main()
