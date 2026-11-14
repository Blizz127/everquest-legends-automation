#!/usr/bin/env python3
"""Exercise retained follower corner/arrival behavior offline, with no input."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

ROOT = Path.home() / ".local/share/eql-automation"
HELPER = ROOT / "owner-assist/0.39.4"
PINS = {
    HELPER / "eqnav/steer.py": "6bb94a7d52e61840f6e2dfed3be712d2a1378424f57cf78f9151e969a688e358",
    HELPER / "eqnav/mesh.py": "89682ac2f6ee6ad4fc4e4530d946e4d7d883d860573a958d45f7cd7a074fef85",
}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def run(output):
    pins = dict(PINS)
    pins[Path(__file__)] = digest(Path(__file__))
    def verify():
        if any(p.is_symlink() or digest(p) != h for p, h in pins.items()):
            raise ValueError("retained follower source changed")
    verify()
    sys.path.insert(0, str(HELPER))
    from eqnav.steer import Controls, FollowTuning, Motion, PathFollower, PoseEstimator, bearing

    motion = Motion(run_speed=10, turn_rate=170, right_sign=-1, turn_latency=.03, back_speed=5)
    def at_corner(points):
        pose = PoseEstimator(motion)
        pose.x, pose.y, pose.z = 0., 5., 0.
        pose.heading = bearing(0, 5, 10, 10)
        pose.last_fix = (0., 5.)
        pose.sign_verified = True
        return PathFollower(points, motion, estimator=pose, last_fix_at=0.)
    whole = at_corner([(0, 0, 0), (0, 10, 0), (10, 10, 0)])
    segment = at_corner([(0, 0, 0), (0, 10, 0)])
    whole_controls, segment_controls = whole.update(.1), segment.update(.1)
    assert whole_controls.forward and not whole_controls.turn
    assert not segment_controls.forward and segment_controls.turn is not None

    pose = PoseEstimator(motion)
    pose.x, pose.y, pose.z, pose.heading = 0., 8., 0., 0.
    pose.last_fix = (0., 8.)
    delayed = PathFollower([(0, 0, 0), (0, 10, 0)], motion, estimator=pose,
                           fix_mode="hotkey", tuning=FollowTuning(arrive_radius=1), last_fix_at=0)
    delayed._asked_at, delayed._asked_clock = 0., 0.
    pose.predict(.1, Controls(forward=True))
    delayed.on_fix(.1, 0., 9., 0.)
    assert delayed.status == "arrived" and math.isclose(pose.y, 10.)

    short_pose = PoseEstimator(motion)
    short_pose.x, short_pose.y, short_pose.z, short_pose.heading = 0., 0., 0., 0.
    short_pose.last_fix = (0., 0.)
    short = PathFollower([(0, 0, 0), (0, .6, 0)], motion,
                         estimator=short_pose, last_fix_at=0.)
    first_short, second_short = short.update(.1), short.update(.3)
    assert not first_short.forward and not second_short.forward and second_short.fix
    short.on_fix(.31, 0., 0., 0.)
    assert short.status == "arrived"
    tuned_pose = PoseEstimator(motion)
    tuned_pose.x, tuned_pose.y, tuned_pose.z, tuned_pose.heading = 0., 0., 0., 0.
    tuned_pose.last_fix = (0., 0.)
    tuned = PathFollower([(0, 0, 0), (0, .6, 0)], motion,
                         estimator=tuned_pose, tuning=FollowTuning(arrive_radius=.25),
                         last_fix_at=0.)
    tuned_controls = tuned.update(.1)
    tuned.on_fix(.11, 0., 0., 0.)
    assert tuned_controls.forward and tuned.status == "running"
    verify()
    record = {"format": "eql-retained-follower-probe-v1", "offline_only": True,
              "game_input_sent": False, "route_accepted": False,
              "pins": {str(p): h for p, h in pins.items()},
              "whole_L_controls": asdict(whole_controls),
              "single_segment_controls": asdict(segment_controls),
              "shortcut_chord_midpoint": [5., 7.5],
              "shortcut_distance_from_L": 2.5, "audited_half_width": 1.2,
              "delayed_fix": {"raw_xyz": [0., 9., 0.], "predicted_xyz": [pose.x, pose.y, pose.z],
                              "follower_status": delayed.status, "portal_xyz": [0., 10., 0.]},
              "short_segment": {"raw_xyz": [0., 0., 0.], "portal_xyz": [0., .6, 0.],
                                "forward_requested": False, "follower_status": short.status,
                                "external_endpoint_radius_example": .25,
                                "external_endpoint_check_accepts": False,
                                "tuned_arrival_radius": .25,
                                "tuned_controls": asdict(tuned_controls),
                                "tuned_unchanged_fix_status": tuned.status},
              "conclusions": ["use_one_selected_segment_per_follower",
                              "raw_stopped_fix_required_for_portal_advance",
                              "arrival_radius_must_not_skip_short_segments",
                              "independent_swept_control_guard_still_required"]}
    with output.open("x") as destination:
        json.dump(record, destination, indent=2, sort_keys=True)
        destination.write("\n")
    return {"artifact": str(output), "sha256": digest(output),
            "single_segment_avoids_shortcut": True, "predicted_arrival_reproduced": True,
            "game_input_sent": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.expanduser()
    if (output.parent.resolve() != (ROOT / "nav-candidates").resolve()
            or output.suffix != ".json" or output.exists() or output.is_symlink()):
        parser.error("use a new JSON in the private nav-candidates store")
    try:
        print(json.dumps(run(output), sort_keys=True))
    except (OSError, ValueError, ImportError, AssertionError) as error:
        parser.exit(1, f"Retained follower probe failed: {error}\n")


if __name__ == "__main__":
    main()
