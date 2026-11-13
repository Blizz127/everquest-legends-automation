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

    def reject_midpoint_pair(mesh, poly, start, end, **kwargs):
        if poly == 1 and start[1] == end[1] == 5.0:
            return LateralStripCheck(False, "synthetic_midpoint_obstacle")
        return real_strip(mesh, poly, start, end, **kwargs)

    monkeypatch.setattr(selector, "audit_segment_strip", reject_midpoint_pair)
    result = select_ground_portals(FlatMesh(3), (0, 1, 2),
                                   (1.0, 5.0), (29.0, 5.0),
                                   alternates=(0.55,))
    assert result.candidate and result.fractions in ((0.5, 0.55), (0.55, 0.5))
    assert result.turn_checks >= 3 and result.strip_checks > 3
    assert not result.route_accepted and not result.real_client_accepted


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
