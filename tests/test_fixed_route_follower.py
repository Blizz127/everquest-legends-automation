"""Focused real retained-class integration; no input devices or game access."""
from dataclasses import replace
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

from eql_automation.fixed_route_follower import FixedRoute, FixedRouteFollower, FixedSegment, RouteHalt
import ground_binding_fixture as ground


MESH = "a" * 64
CALIBRATION = "synthetic-stopped-route-test"
HELPER = Path.home() / ".local/share/eql-automation/owner-assist/0.39.4"
PINS = {
    "eqnav/steer.py": "6bb94a7d52e61840f6e2dfed3be712d2a1378424f57cf78f9151e969a688e358",
    "eqnav/mesh.py": "89682ac2f6ee6ad4fc4e4530d946e4d7d883d860573a958d45f7cd7a074fef85",
}


class FixedRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not HELPER.exists():
            raise unittest.SkipTest("Retained owner helper is required for this integration test")
        for name, expected in PINS.items():
            if sha256((HELPER / name).read_bytes()).hexdigest() != expected:
                raise RuntimeError("Retained helper source changed")
        sys.path.insert(0, str(HELPER))
        import eqnav.steer as legacy
        cls.legacy = legacy

    def setUp(self):
        self.generation, self.mode, self.seq = 7, "measurement", 0
        self.motion = self.legacy.Motion(run_speed=10., turn_rate=170., right_sign=-1,
                                         turn_latency=.03, back_speed=5.)
        self.route = FixedRoute("gfaydark", MESH, "b" * 64, 1.2,
            (FixedSegment(1, (0., 0., 0.), (0., .6, 0.)),
             FixedSegment(2, (0., .6, 0.), (0., 1.2, 0.))))

    def runner(self, **changes):
        options = dict(legacy=self.legacy, motion=self.motion, heading=0.,
                       calibration_record_id=CALIBRATION, generation=7,
                       height_calibration=ground.HEIGHT, geometry_evidence=ground.GEOMETRY,
                       generation_reader=lambda: self.generation, mode_reader=lambda: self.mode)
        options.update(changes)
        return FixedRouteFollower(self.route, **options)

    def fix(self, point, at):
        self.seq += 1
        def distance(segment):
            ax, ay = segment.start[:2]
            dx, dy = segment.end[0] - ax, segment.end[1] - ay
            t = min(1., max(0., ((point[0]-ax)*dx + (point[1]-ay)*dy) / segment.length**2))
            return math.hypot(point[0]-ax-t*dx, point[1]-ay-t*dy)
        index = min(range(len(self.route.segments)), key=lambda i: distance(self.route.segments[i]))
        neighbors = tuple(self.route.segments[i].polygon for i in (index-1, index+1)
                          if 0 <= i < len(self.route.segments))
        return ground.aligned(point, at=at, seq=self.seq,
                              polygon=self.route.segments[index].polygon, neighbors=neighbors)

    def pair(self, point, release):
        return self.fix(point, release + .13), self.fix(point, release + .53)

    def start(self, runner):
        first, second = self.pair((0., 0., 0.), 100.)
        runner.observe_stopped(first, second, released_at=100., now=100.53)
        return 100.53

    def step(self, runner, point, seconds):
        proposal = runner.propose(runner.last_at + .01)
        start, release = proposal.at + .01, proposal.at + .01 + seconds
        runner.record_release(proposal, started_at=start, released_at=release)
        first, second = self.pair(point, release)
        runner.observe_stopped(first, second, released_at=release, now=second.raw_fix.received_monotonic)
        return proposal

    def test_short_segments_require_actual_new_raw_positions(self):
        runner = self.runner()
        self.start(runner)
        self.assertTrue(self.step(runner, (0., .6, 0.), .06).forward)
        self.assertEqual(runner.index, 1)
        self.assertEqual(runner.phase, "ready")
        self.step(runner, (0., 1.2, 0.), .06)
        self.assertEqual(runner.phase, "arrived")
        self.assertEqual(runner.index, 2)

    def test_forward_pivot_only_needs_no_backward_speed_measurement(self):
        motion = replace(self.motion, back_speed=0.)
        runner = self.runner(motion=motion)
        self.start(runner)
        self.assertTrue(self.step(runner, (0., .6, 0.), .06).forward)
        self.step(runner, (0., 1.2, 0.), .06)
        self.assertEqual(runner.phase, "arrived")
        pivot = self.runner(motion=motion, heading=350.)
        self.start(pivot)
        proposal = pivot.propose(100.54)
        self.assertIsNotNone(proposal.turn)
        self.assertFalse(proposal.forward)

    def test_invalid_unused_backward_speed_is_still_rejected(self):
        for speed in (-1., float("nan"), True):
            with self.subTest(speed=speed), self.assertRaises(ValueError):
                self.runner(motion=replace(self.motion, back_speed=speed))

    def test_predicted_endpoint_with_unchanged_raw_fix_does_not_advance(self):
        runner = self.runner()
        self.start(runner)
        proposal = runner.propose(100.54)
        runner.record_release(proposal, started_at=100.55, released_at=100.61)
        self.assertAlmostEqual(runner.pose.y, .6)
        first, second = self.pair((0., 0., 0.), 100.61)
        runner.observe_stopped(first, second, released_at=100.61, now=101.14)
        self.assertEqual(runner.index, 0)
        self.assertEqual(runner.pose.y, 0.)
        self.assertTrue(runner.propose(101.15).forward)

    def test_one_fix_at_endpoint_and_one_short_cannot_advance(self):
        runner = self.runner()
        self.start(runner)
        proposal = runner.propose(100.54)
        runner.record_release(proposal, started_at=100.55, released_at=100.60)
        first = self.fix((0., .3, 0.), 100.73)
        second = self.fix((0., .5, 0.), 101.13)
        runner.observe_stopped(first, second, released_at=100.60, now=101.13)
        self.assertEqual(runner.index, 0)

    def test_rejected_control_never_integrates_or_reuses_follower(self):
        runner = self.runner()
        self.start(runner)
        runner.propose(100.54)
        self.assertEqual(runner.pose.y, 0.)
        with self.assertRaises(RouteHalt): runner.halt("external swept guard rejected")
        with self.assertRaises(RouteHalt): runner.propose(100.55)
        self.assertEqual(runner.pose.y, 0.)

    def test_actual_shorter_hold_is_integrated_without_requested_time(self):
        runner = self.runner()
        self.start(runner)
        proposal = runner.propose(100.54)
        runner.record_release(proposal, started_at=100.55, released_at=100.57)
        self.assertAlmostEqual(runner.pose.y, .2)
        self.assertEqual(runner.phase, "await_stopped")

    def test_turn_is_a_pivot_without_forward_or_implicit_probe(self):
        runner = self.runner(heading=350.)
        self.start(runner)
        proposal = runner.propose(100.54)
        self.assertIsNotNone(proposal.turn)
        self.assertFalse(proposal.forward)
        self.assertEqual((runner.pose.x, runner.pose.y), (0., 0.))

    def test_mode_change_and_cancel_invalidate_pending_proposal(self):
        for kind in ("assist", "off", "cancel"):
            with self.subTest(kind=kind):
                self.mode, self.generation = "measurement", 7
                runner = self.runner()
                self.start(runner)
                proposal = runner.propose(100.54)
                if kind == "cancel": self.generation += 1
                else: self.mode = kind
                with self.assertRaises(RouteHalt):
                    runner.record_release(proposal, started_at=100.55, released_at=100.57)
                self.assertEqual(runner.phase, "halted")
                self.assertEqual(runner.pose.y, 0.)

    def test_invalid_receipt_or_duplicate_decision_halts(self):
        for kind in ("long", "stale", "replacement", "duplicate"):
            with self.subTest(kind=kind):
                runner = self.runner()
                self.start(runner)
                proposal = runner.propose(100.54)
                with self.assertRaises(RouteHalt):
                    if kind == "duplicate": runner.propose(100.55)
                    else:
                        runner.record_release(replace(proposal) if kind == "replacement" else proposal,
                            started_at=100.61 if kind == "stale" else 100.55,
                            released_at=100.8 if kind == "long" else 100.63)

    def test_unchanged_wrong_zone_log_generation_or_alignment_rejects(self):
        for kind in ("zone", "epoch", "generation", "calibration", "mesh", "unaligned"):
            with self.subTest(kind=kind):
                runner = self.runner()
                self.start(runner)
                proposal = runner.propose(100.54)
                runner.record_release(proposal, started_at=100.55, released_at=100.61)
                first, second = self.pair((0., .6, 0.), 100.61)
                if kind in ("zone", "epoch", "generation"):
                    change = {"zone_id": 55} if kind == "zone" else {
                        "log_epoch" if kind == "epoch" else "zone_generation": 2}
                    second = replace(second, raw_fix=replace(second.raw_fix, **change))
                else:
                    change = ({"calibration_record_id": "different"} if kind == "calibration"
                              else {"mesh_projection": replace(second.mesh_projection, mesh_sha256="c" * 64)} if kind == "mesh"
                              else {"live_alignment_verified": False})
                    second = replace(second, **change)
                with self.assertRaises(RouteHalt):
                    runner.observe_stopped(first, second, released_at=100.61, now=101.14)

    def test_stale_sample_is_not_refreshed_by_processing_time(self):
        runner = self.runner()
        first, second = self.pair((0., 0., 0.), 100.)
        runner.observe_stopped(first, second, released_at=100., now=100.9)
        with self.assertRaises(RouteHalt): runner.propose(101.04)

    def test_no_skip_ahead_or_wrong_floor_endpoint(self):
        for point in ((0., 1.2, 0.), (0., .6, 2.)):
            with self.subTest(point=point):
                runner = self.runner()
                self.start(runner)
                proposal = runner.propose(100.54)
                runner.record_release(proposal, started_at=100.55, released_at=100.67)
                first, second = self.pair(point, 100.67)
                if point[2] == 0:
                    with self.assertRaises(RouteHalt):
                        runner.observe_stopped(first, second, released_at=100.67, now=101.20)
                else:
                    runner.observe_stopped(first, second, released_at=100.67, now=101.20)
                    self.assertEqual(runner.index, 0)  # Geometry caller still checks intermediate floor.

    def test_overlapping_endpoint_disks_invalid_plan(self):
        with self.assertRaises(ValueError): self.runner(endpoint_radius=.3)
        self.route = replace(self.route, segments=(self.route.segments[0],
                             FixedSegment(2, (0., .7, 0.), (0., 2., 0.))))
        with self.assertRaises(ValueError): self.runner()

    def test_missing_heading_never_enters_legacy_probe(self):
        runner = self.runner()
        self.start(runner)
        runner.pose.heading = None
        with self.assertRaises(RouteHalt): runner.propose(100.54)
        self.assertEqual(runner.pose.y, 0.)

    def test_pulse_partition_avoids_stranding_a_subminimum_final_step(self):
        self.motion = replace(self.motion, run_speed=30.77)
        self.route = replace(self.route, segments=(FixedSegment(1, (0., 0., 0.), (0., 3.4, 0.)),))
        runner = self.runner()
        self.start(runner)
        first = runner.propose(100.54)
        seconds = runner.suggest_hold(first, minimum_seconds=.02, maximum_seconds=.1)
        self.assertAlmostEqual(seconds * 30.77, 1.7)
        runner.record_release(first, started_at=100.55, released_at=100.55 + seconds)
        p1, p2 = self.pair((0., 1.7, 0.), 100.55 + seconds)
        runner.observe_stopped(p1, p2, released_at=100.55 + seconds, now=p2.raw_fix.received_monotonic)
        second = runner.propose(runner.last_at + .01)
        self.assertAlmostEqual(runner.suggest_hold(second, minimum_seconds=.02, maximum_seconds=.1), seconds)

    def test_pulse_minimum_cannot_force_unreachable_endpoint(self):
        self.motion = replace(self.motion, run_speed=50.)
        runner = self.runner()
        self.start(runner)
        proposal = runner.propose(100.54)
        with self.assertRaises(RouteHalt):
            runner.suggest_hold(proposal, minimum_seconds=.02, maximum_seconds=.1)

    def test_reseeded_legacy_progress_on_long_segment_does_not_turn_back(self):
        self.route = replace(self.route, segments=(FixedSegment(1, (0., 0., 0.), (0., 120., 0.)),))
        runner = self.runner()
        self.start(runner)
        for i in range(40):
            proposal = self.step(runner, (0., 1.9 * (i + 1), 0.), .19)
            self.assertTrue(proposal.forward)
            self.assertIsNone(proposal.turn)
        proposal = runner.propose(runner.last_at + .01)
        self.assertTrue(proposal.forward)
        self.assertIsNone(proposal.turn)

    def test_narrow_corridor_corrects_small_heading_error_before_leaving_strip(self):
        self.route = replace(self.route, segments=(FixedSegment(1, (0., 0., 0.), (0., 120., 0.)),))
        runner = self.runner(heading=3.)
        self.start(runner)
        point, heading, turned = [0., 0., 0.], 3., False
        for _ in range(400):
            if runner.phase == "arrived": break
            proposal = runner.propose(runner.last_at + .01)
            seconds = runner.suggest_hold(proposal, minimum_seconds=.02, maximum_seconds=.1)
            if proposal.turn:
                turned = True
                sign = -1 if proposal.turn == "right" else 1
                heading = (heading + sign * 170. * max(0., seconds - .03)) % 360
            elif proposal.forward:
                point[0] += math.sin(math.radians(heading)) * 10. * seconds
                point[1] += math.cos(math.radians(heading)) * 10. * seconds
            self.assertLessEqual(abs(point[0]), self.route.half_width)
            start = proposal.at + .01
            release = start + seconds
            runner.record_release(proposal, started_at=start, released_at=release)
            first, second = self.pair(point, release)
            runner.observe_stopped(first, second, released_at=release, now=second.raw_fix.received_monotonic)
        self.assertTrue(turned)
        self.assertEqual(runner.phase, "arrived")

    def test_loader_pin_and_frame_preserve_selected_portals(self):
        data = dict(format="eql-fixed-segment-plan-v1", frame="helper_package_WLD_Y_X_Z",
                    offline_only=True, route_accepted=False, real_client_accepted=False,
                    zone="gfaydark", half_width=1.2, pins={"mesh": MESH},
                    segments=[dict(index=0, polygon=1, points=[[0, 0, 0], [0, .6, 0]])])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'route.json'
            path.write_text(json.dumps(data))
            pin = sha256(path.read_bytes()).hexdigest()
            route = FixedRoute.load(path, expected_sha256=pin, mesh_sha256=MESH)
            self.assertEqual(route.segments[0].end, (0, .6, 0))
            path.write_text(json.dumps({**data, "frame": "wrong"}))
            with self.assertRaises(ValueError): FixedRoute.load(path, expected_sha256=pin, mesh_sha256=MESH)
            with self.assertRaises(ValueError): FixedRoute.load(path, expected_sha256=sha256(path.read_bytes()).hexdigest(), mesh_sha256=MESH)

    def test_fast_short_pulses_do_not_overshoot_the_steering_aim(self):
        self.motion=replace(self.motion,run_speed=30.,turn_rate=169.2,turn_latency=.0296)
        self.route=replace(self.route,half_width=.3,
            segments=(FixedSegment(1,(0.,0.,0.),(0.,40.,0.)),))
        runner=self.runner(heading=4.)
        self.start(runner)
        point=[0.,0.,0.];actual_heading=3.;delayed=False
        for _ in range(160):
            if runner.phase=='arrived':break
            proposal=runner.propose(runner.last_at+.01)
            seconds=runner.suggest_hold(proposal,minimum_seconds=.02,maximum_seconds=.1)
            # The receipt, rather than the requested duration, controls both
            # the synthetic actor and the estimator. One pivot releases late
            # but remains below the existing 0.2-second bound.
            if proposal.turn and not delayed:seconds+=.06;delayed=True
            if proposal.turn:
                sign=-1 if proposal.turn=='right' else 1
                actual_heading=(actual_heading+sign*170.*max(0.,seconds-.03))%360
            elif proposal.forward:
                point[0]+=math.sin(math.radians(actual_heading))*30.*seconds
                point[1]+=math.cos(math.radians(actual_heading))*30.*seconds
            self.assertLessEqual(abs(point[0]),self.route.half_width)
            began=proposal.at+.01;released=began+seconds
            runner.record_release(proposal,started_at=began,released_at=released)
            first,second=self.pair(point,released)
            runner.observe_stopped(first,second,released_at=released,now=second.raw_fix.received_monotonic)
        self.assertTrue(delayed)
        self.assertEqual(runner.phase,'arrived')

    def test_neighbor_projection_only_within_shared_endpoint_disk(self):
        for y, accepted in ((.6, True), (.3, False)):
            with self.subTest(y=y):
                runner = self.runner()
                self.start(runner)
                proposal = runner.propose(100.54)
                runner.record_release(proposal, started_at=100.55, released_at=100.61)
                pair = [ground.aligned((0., y, 0.), at=at, seq=self.seq+i+1,
                                       polygon=2, neighbors=(1,))
                        for i, at in enumerate((100.74, 101.14))]
                if accepted:
                    runner.observe_stopped(*pair, released_at=100.61, now=101.14)
                    self.assertEqual(runner.index, 1)
                else:
                    with self.assertRaises(RouteHalt):
                        runner.observe_stopped(*pair, released_at=100.61, now=101.14)

    def test_raw_and_source_motion_cannot_be_hidden_by_stationary_baked_pair(self):
        runner = self.runner()
        first = ground.aligned(at=100.13, seq=1, source_z=-.3)
        second = ground.aligned(at=100.53, seq=2, source_z=-.6)
        # Both raw heights fit calibration and the same baked point; the
        # independent raw/source changes still disqualify a stopped pair.
        with self.assertRaisesRegex(RouteHalt, 'stationary pair'):
            runner.observe_stopped(first, second, released_at=100., now=100.53)

    def test_component_cannot_change_between_stopped_pairs(self):
        runner = self.runner()
        self.start(runner)
        proposal = runner.propose(100.54)
        runner.record_release(proposal, started_at=100.55, released_at=100.61)
        pair = [ground.aligned((0., .6, 0.), at=at, seq=self.seq+i+1, component=3)
                for i, at in enumerate((100.74, 101.14))]
        with self.assertRaisesRegex(RouteHalt, 'component'):
            runner.observe_stopped(*pair, released_at=100.61, now=101.14)

    def test_source_bake_delta_does_not_widen_endpoint_height_tolerance(self):
        runner = self.runner()
        self.start(runner)
        # Consistent raw/source calibration with baked endpoint Z off by .26.
        self.step(runner, (0., .6, .26), .06)
        self.assertEqual(runner.index, 0)
        self.assertEqual(runner.height_tolerance, .25)
