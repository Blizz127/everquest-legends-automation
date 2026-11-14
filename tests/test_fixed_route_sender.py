"""Actual watchdog child + retained follower, with pipe input and fake fixes."""
import os
import threading
import time
import unittest

import test_fixed_route_follower as fixtures
from eql_automation.fixed_route_follower import RouteHalt
from eql_automation.uinput_watchdog import (
    PulseError, PulseSelection, selected_key_pulse_receipt, _EVENT,
)


class FixedRouteSenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.FixedRouteTests.setUpClass()

    def setUp(self):
        self.fixture = fixtures.FixedRouteTests()
        self.fixture.setUp()
        self.runner = self.fixture.runner()
        now = time.monotonic()
        first, second = self.fixture.pair((0., 0., 0.), now - .6)
        self.runner.observe_stopped(first, second, released_at=now - .6, now=now)

    def events(self, rd, wr):
        os.close(wr)
        data = bytearray()
        while chunk := os.read(rd, 4096): data.extend(chunk)
        os.close(rd)
        return [(kind, key, value) for _, _, kind, key, value in _EVENT.iter_unpack(data)]

    def test_post_ready_proposal_uses_child_write_times_then_new_stopped_fixes(self):
        rd, wr = os.pipe()
        proposals = []
        def select():
            proposal = self.runner.propose(time.monotonic())
            self.assertTrue(proposal.forward)
            self.assertIsNone(proposal.turn)
            proposals.append(proposal)
            seconds = self.runner.suggest_hold(proposal, minimum_seconds=.02, maximum_seconds=.08)
            return PulseSelection(103, seconds, proposal.at + .05)
        try:
            receipt = selected_key_pulse_receipt(wr, select, go_lock=threading.RLock())
            self.runner.record_release(proposals[0], started_at=receipt.down_started_at,
                                        released_at=receipt.up_completed_at)
            self.assertEqual(self.runner.phase, "await_stopped")
            self.assertEqual(self.runner.index, 0)
            # Only these observations are synthetic. Receipt times and the
            # input-event pipe came from the real separate watchdog process.
            ideal_point = (0., receipt.maximum_held_seconds * 10., 0.)
            time.sleep(.55)
            first, second = self.fixture.pair(ideal_point, receipt.up_completed_at)
            self.runner.observe_stopped(first, second, released_at=receipt.up_completed_at,
                                         now=time.monotonic())
            self.assertEqual(self.runner.index, 1)
            self.assertEqual(self.runner.phase, "ready")
        finally:
            events = self.events(rd, wr)
        self.assertEqual(events[:4], [(1, 103, 1), (0, 0, 0), (1, 103, 0), (0, 0, 0)])

    def test_assist_switch_after_selection_cannot_send_down_or_accept_progress(self):
        rd, wr = os.pipe()
        def select():
            proposal = self.runner.propose(time.monotonic())
            self.fixture.mode = "assist"
            return PulseSelection(103, .02, proposal.at + .05)
        try:
            with self.assertRaises(PulseError):
                selected_key_pulse_receipt(wr, select,
                    should_stop=lambda: self.fixture.mode == "assist", go_lock=threading.RLock())
            with self.assertRaises(RouteHalt): self.runner.halt("assist switch")
            self.assertEqual(self.runner.index, 0)
            self.assertEqual(self.runner.pose.y, 0.)
        finally:
            events = self.events(rd, wr)
        self.assertNotIn((1, 103, 1), events)
