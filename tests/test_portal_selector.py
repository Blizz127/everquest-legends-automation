from collections import Counter

from eql_automation.lateral_strip_audit import LateralStripCheck
from eql_automation.portal_selector import select_ground_portals
from eql_automation.strip_route_audit import StripRouteCheck
from eql_automation.turn_disk_audit import TurnDiskCheck
import eql_automation.portal_selector as selector


class Grid:
    def __init__(self, count):
        self.count = count

    def near(self, x, y, radius):
        return range(self.count)


class FlatMesh:
    def __init__(self, tiles=2):
        self.polys = []
        self._detail = []
        self._detail_start = [0]
        self.links = []
        for index in range(tiles):
            x = index * 10.0
            ring = [(x, 0.0, 2.0), (x + 10, 0.0, 2.0),
                    (x + 10, 10.0, 2.0), (x, 10.0, 2.0)]
            self.polys.append(ring)
            self._detail.extend(((ring[0], ring[1], ring[2]),
                                 (ring[0], ring[2], ring[3])))
            self._detail_start.append(len(self._detail))
            self.links.append([(index + 1, (x + 10, 10.0, 2.0),
                                (x + 10, 0.0, 2.0))] if index + 1 < tiles else [])
        self.area = [63] * tiles
        self.component = [0] * tiles
        self._grid = Grid(tiles)
        self._grid_ids = list(range(tiles))

    def clearance(self, x, y, z, *, limit):
        return limit


class InclinedMesh(FlatMesh):
    def __init__(self, grade=1.05):
        super().__init__()
        self.polys = [[(x, y, 2.0 + grade * y) for x, y, _ in ring]
                      for ring in self.polys]
        self._detail = []
        self._detail_start = [0]
        for ring in self.polys:
            self._detail.extend(((ring[0], ring[1], ring[2]),
                                 (ring[0], ring[2], ring[3])))
            self._detail_start.append(len(self._detail))


def test_flat_ground_corridor_selects_midpoint_but_never_accepts_live_route():
    result = select_ground_portals(FlatMesh(), (0, 1), (1.0, 5.0), (19.0, 5.0))
    assert result.candidate and result.fractions == (0.5,)
    assert len(result.points) == 3
    assert not result.route_accepted and not result.real_client_accepted


def test_select_only_retains_unverified_points_without_running_final_audit(monkeypatch):
    def forbidden_final_audit(*args, **kwargs):
        raise AssertionError("select-only must not run the final audit")

    monkeypatch.setattr(selector, "audit_route_strips", forbidden_final_audit)
    result = select_ground_portals(FlatMesh(), (0, 1), (1.0, 5.0),
                                   (19.0, 5.0), final_recheck=False)
    assert not result.candidate
    assert result.reason == "portal_sequence_selected_final_audit_required"
    assert result.points == () and result.fractions == ()
    assert len(result.unverified_points) == 3
    assert result.unverified_fractions == (0.5,)
    assert not result.route_accepted and not result.real_client_accepted


def test_turn_time_limit_is_configurable_but_still_bounded(monkeypatch):
    real = selector.audit_turn_disk
    limits = []

    def record_limit(mesh, a, b, xy, **kwargs):
        limits.append(kwargs["max_seconds"])
        return real(mesh, a, b, xy, **kwargs)

    monkeypatch.setattr(selector, "audit_turn_disk", record_limit)
    result = select_ground_portals(FlatMesh(), (0, 1), (1.0, 5.0),
                                   (19.0, 5.0), max_turn_seconds=7.0)
    assert result.candidate and limits and 0 < limits[0] <= 7.0
    assert limits[0] > 3.0
    invalid = select_ground_portals(FlatMesh(), (0, 1), (1.0, 5.0),
                                    (19.0, 5.0), max_turn_seconds=0.0)
    assert not invalid.candidate and invalid.reason == "invalid_selection_limits"


def test_explicit_grade_sensitivity_rechecks_turns_and_whole_strip():
    mesh = InclinedMesh()
    strict = select_ground_portals(mesh, (0, 1), (1.0, 5.0), (19.0, 5.0),
                                   alternates=(), maximum_grade=1.0)
    relaxed = select_ground_portals(mesh, (0, 1), (1.0, 5.0), (19.0, 5.0),
                                    alternates=(), maximum_grade=1.2)
    assert not strict.candidate and strict.reason == "no_sampled_turn_disk_candidate"
    assert relaxed.candidate and relaxed.fractions == (0.5,)
    assert not relaxed.route_accepted and not relaxed.real_client_accepted


def test_failed_turn_midpoint_expands_to_checked_alternate(monkeypatch):
    real = selector.audit_turn_disk

    def reject_midpoint(mesh, a, b, xy, **kwargs):
        if xy == (10.0, 5.0):
            return TurnDiskCheck(False, "radial_grade_too_steep")
        return real(mesh, a, b, xy, **kwargs)

    monkeypatch.setattr(selector, "audit_turn_disk", reject_midpoint)
    result = select_ground_portals(FlatMesh(), (0, 1), (1.0, 5.0),
                                   (19.0, 5.0), alternates=(0.6,))
    assert result.candidate and result.fractions == (0.6,)


def test_local_spatial_candidate_limit_rejects_fraction_without_ending_search(monkeypatch):
    real_turn = selector.audit_turn_disk

    def crowded_midpoint(mesh, a, b, xy, **kwargs):
        if xy == (10.0, 5.0):
            return TurnDiskCheck(False, "spatial_candidate_budget_exceeded")
        return real_turn(mesh, a, b, xy, **kwargs)

    monkeypatch.setattr(selector, "audit_turn_disk", crowded_midpoint)
    result = select_ground_portals(FlatMesh(), (0, 1), (1.0, 5.0),
                                   (19.0, 5.0), alternates=(0.6,))
    assert result.candidate and result.fractions == (0.6,)
    assert result.turn_checks == 2


def test_layered_search_recovers_when_adjacent_nearest_choices_conflict(monkeypatch):
    real_turn = selector.audit_turn_disk
    real_strip = selector.audit_segment_strip

    def reject_midpoint(mesh, a, b, xy, **kwargs):
        if xy[1] == 5.0:
            return TurnDiskCheck(False, "radial_grade_too_steep")
        return real_turn(mesh, a, b, xy, **kwargs)

    def reject_pair(mesh, poly, start, end, **kwargs):
        if poly == 1 and start[1] == end[1] == 4.5:
            return LateralStripCheck(False, "synthetic_obstacle")
        return real_strip(mesh, poly, start, end, **kwargs)

    monkeypatch.setattr(selector, "audit_turn_disk", reject_midpoint)
    monkeypatch.setattr(selector, "audit_segment_strip", reject_pair)
    result = select_ground_portals(FlatMesh(3), (0, 1, 2),
                                   (1.0, 5.0), (29.0, 5.0),
                                   alternates=(0.55, 0.6))
    assert result.candidate and result.fractions != (0.55, 0.55)
    assert set(result.fractions) <= {0.55, 0.6}


def test_strip_failure_expands_midpoint_safe_portal_under_bound(monkeypatch):
    real_strip = selector.audit_segment_strip

    def reject_midpoint_strip(mesh, poly, start, end, **kwargs):
        if poly == 0 and end == (10.0, 5.0):
            return LateralStripCheck(False, "spatial_candidate_budget_exceeded")
        return real_strip(mesh, poly, start, end, **kwargs)

    monkeypatch.setattr(selector, "audit_segment_strip", reject_midpoint_strip)
    result = select_ground_portals(FlatMesh(), (0, 1), (1.0, 5.0),
                                   (19.0, 5.0), alternates=(0.6,))
    assert result.candidate and result.fractions == (0.6,)
    assert result.turn_checks == 2 and result.strip_checks > 2
    assert not result.route_accepted and not result.real_client_accepted

    no_retry = select_ground_portals(FlatMesh(), (0, 1), (1.0, 5.0),
                                     (19.0, 5.0), alternates=(0.6,),
                                     max_strip_repair_rounds=0)
    assert not no_retry.candidate
    assert no_retry.reason == "strip_repair_round_budget_exceeded"


def test_middle_polygon_can_repair_either_adjacent_portal(monkeypatch):
    real_strip = selector.audit_segment_strip
    calls = Counter()

    def reject_midpoint_pair(mesh, poly, start, end, **kwargs):
        calls[(poly, start, end)] += 1
        if poly == 1 and start[1] == end[1] == 5.0:
            return LateralStripCheck(False, "synthetic_midpoint_obstacle")
        return real_strip(mesh, poly, start, end, **kwargs)

    monkeypatch.setattr(selector, "audit_segment_strip", reject_midpoint_pair)
    result = select_ground_portals(FlatMesh(3), (0, 1, 2),
                                   (1.0, 5.0), (29.0, 5.0),
                                   alternates=(0.55,))
    assert result.candidate and result.fractions in ((0.5, 0.55), (0.55, 0.5))
    assert result.turn_checks >= 3 and result.strip_checks > 3
    assert result.strip_checks == sum(calls.values()) == len(calls)
    assert not result.route_accepted and not result.real_client_accepted


def test_bounded_backtrack_can_revisit_upstream_portal_choice(monkeypatch):
    real_strip = selector.audit_segment_strip

    def upstream_choice_required(mesh, poly, start, end, **kwargs):
        # The second portal's alternate cannot be reached from the first
        # portal's midpoint; the third polygon needs that alternate.
        if ((poly == 1 and start[1] == 5.0 and end[1] == 4.5) or
                (poly == 2 and start[1] == 5.0)):
            return LateralStripCheck(False, "synthetic_connected_choice")
        return real_strip(mesh, poly, start, end, **kwargs)

    monkeypatch.setattr(selector, "audit_segment_strip", upstream_choice_required)
    options = dict(alternates=(0.55,), max_strip_repair_rounds=4)
    shallow = select_ground_portals(FlatMesh(4), (0, 1, 2, 3),
                                    (1.0, 5.0), (39.0, 5.0), **options)
    assert not shallow.candidate and shallow.reason == "no_sampled_strip_through_polygon"
    deeper = select_ground_portals(FlatMesh(4), (0, 1, 2, 3),
                                   (1.0, 5.0), (39.0, 5.0),
                                   repair_backtrack_depth=2, **options)
    assert deeper.candidate and deeper.fractions[:2] == (0.55, 0.55)
    assert not deeper.route_accepted and not deeper.real_client_accepted
    invalid = select_ground_portals(FlatMesh(1), (0,), (1.0, 5.0),
                                    (9.0, 5.0), repair_backtrack_depth=0)
    assert not invalid.candidate and invalid.reason == "invalid_selection_limits"
    too_many = select_ground_portals(FlatMesh(1), (0,), (1.0, 5.0),
                                     (9.0, 5.0), max_strip_repair_rounds=33)
    assert not too_many.candidate and too_many.reason == "invalid_selection_limits"


def test_single_polygon_failure_has_no_backtrack_portal(monkeypatch):
    monkeypatch.setattr(selector, "audit_segment_strip",
                        lambda *args, **kwargs: LateralStripCheck(False, "synthetic_block"))
    result = select_ground_portals(FlatMesh(1), (0,), (1.0, 5.0),
                                   (9.0, 5.0), repair_backtrack_depth=4)
    assert not result.candidate and result.reason == "no_sampled_strip_through_polygon"
    assert result.points == () and not result.real_client_accepted


def test_first_repair_choice_is_tried_before_later_budget_failure(monkeypatch):
    real_strip = selector.audit_segment_strip
    real_turn = selector.audit_turn_disk

    def reject_midpoint_strip(mesh, poly, start, end, **kwargs):
        if poly == 0 and end == (10.0, 5.0):
            return LateralStripCheck(False, "synthetic_midpoint_obstacle")
        return real_strip(mesh, poly, start, end, **kwargs)

    def later_choice_exhausts_budget(mesh, a, b, xy, **kwargs):
        if xy == (10.0, 4.0):
            return TurnDiskCheck(False, "synthetic_budget_exceeded")
        return real_turn(mesh, a, b, xy, **kwargs)

    monkeypatch.setattr(selector, "audit_segment_strip", reject_midpoint_strip)
    monkeypatch.setattr(selector, "audit_turn_disk", later_choice_exhausts_budget)
    result = select_ground_portals(FlatMesh(), (0, 1), (1.0, 5.0),
                                   (19.0, 5.0), alternates=(0.55, 0.6))
    assert result.candidate and result.fractions == (0.55,)
    assert result.turn_checks == 2


def test_missing_portal_and_exhausted_turn_budget_fail_closed(monkeypatch):
    mesh = FlatMesh()
    mesh.links[0] = []
    result = select_ground_portals(mesh, (0, 1), (1.0, 5.0), (19.0, 5.0))
    assert not result.candidate and result.reason == "missing_or_ambiguous_shared_portal"

    monkeypatch.setattr(selector, "audit_turn_disk",
                        lambda *args, **kwargs: TurnDiskCheck(False, "unsupported_detail_surface"))
    budget = select_ground_portals(FlatMesh(), (0, 1), (1.0, 5.0),
                                   (19.0, 5.0), max_turn_checks=1)
    assert not budget.candidate and budget.reason == "selection_work_budget_exceeded"
    assert not budget.route_accepted


def test_sample_budget_and_final_whole_route_refusal_cannot_promote(monkeypatch):
    tiny = select_ground_portals(FlatMesh(), (0, 1), (1.0, 5.0),
                                 (19.0, 5.0), max_total_samples=1)
    assert not tiny.candidate and tiny.reason == "selection_work_budget_exceeded"
    monkeypatch.setattr(selector, "audit_route_strips",
                        lambda *args, **kwargs: StripRouteCheck(False, "synthetic_final_refusal"))
    refused = select_ground_portals(FlatMesh(), (0, 1), (1.0, 5.0), (19.0, 5.0))
    assert not refused.candidate
    assert refused.reason == "whole_route_synthetic_final_refusal"
    assert refused.points == () and refused.fractions == ()
    assert len(refused.unverified_points) == 3
    assert refused.unverified_fractions == (0.5,)
    assert not refused.route_accepted and not refused.real_client_accepted


def test_turn_and_rechecked_centerline_samples_share_global_cap():
    turn_capped = select_ground_portals(FlatMesh(), (0, 1), (1.0, 5.0),
                                        (19.0, 5.0), max_total_samples=50)
    assert not turn_capped.candidate
    assert turn_capped.reason == "selection_work_budget_exceeded"
    assert turn_capped.strip_checks == 0

    strip_capped = select_ground_portals(FlatMesh(1), (0,), (1.0, 5.0),
                                         (9.0, 5.0), sample_spacing=1.0,
                                         max_total_samples=54)
    assert not strip_capped.candidate
    assert strip_capped.reason.startswith("whole_route_")
