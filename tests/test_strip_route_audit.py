from types import SimpleNamespace

from eql_automation import strip_route_audit as route
from eql_automation.strip_route_audit import audit_route_strips


class Grid:
    def near(self, x, y, radius):
        return [0, 1]


class TwoTileMesh:
    def __init__(self, *, second_height=2.0):
        left = [(0.0, 0.0, 2.0), (10.0, 0.0, 2.0),
                (10.0, 10.0, 2.0), (0.0, 10.0, 2.0)]
        right = [(10.0, 0.0, second_height), (20.0, 0.0, second_height),
                 (20.0, 10.0, second_height), (10.0, 10.0, second_height)]
        self.polys = [left, right]
        self.area = [63, 63]
        self.component = [0, 0]
        self._detail_start = [0, 2, 4]
        self._detail = [[left[0], left[1], left[2]],
                        [left[0], left[2], left[3]],
                        [right[0], right[1], right[2]],
                        [right[0], right[2], right[3]]]
        self.links = [[(1, (10.0, 10.0, 2.0), (10.0, 0.0, 2.0))], []]
        self._grid = Grid()
        self._grid_ids = [0, 1]
        self.narrow_second = False

    def clearance(self, x, y, z, *, limit):
        return 2.0 if self.narrow_second and x >= 14 else limit


POINTS = ((1.0, 5.0), (10.0, 5.0), (19.0, 5.0))


def test_two_flat_segments_are_still_only_an_offline_candidate():
    result = audit_route_strips(TwoTileMesh(), (0, 1), POINTS)
    assert result.candidate and not result.real_client_accepted
    assert result.checked_segments == 2


def test_second_segment_clearance_rejects_the_route():
    mesh = TwoTileMesh()
    mesh.narrow_second = True
    result = audit_route_strips(mesh, (0, 1), POINTS)
    assert not result.candidate and result.failed_segment == 1
    assert result.failed_polygon == 1


def test_discontinuous_seam_and_invalid_shape_fail_closed():
    seam = audit_route_strips(TwoTileMesh(second_height=10.0), (0, 1), POINTS)
    assert not seam.candidate and seam.reason == "seam_height_step_too_large"
    malformed = audit_route_strips(TwoTileMesh(), (0, 1), POINTS[:2])
    assert not malformed.candidate and malformed.reason == "invalid_route_limits"


class LongTileMesh:
    def __init__(self):
        ring = [(0.0, 0.0, 2.0), (180.0, 0.0, 2.0),
                (180.0, 10.0, 2.0), (0.0, 10.0, 2.0)]
        self.polys = [ring]
        self.area = [63]
        self.component = [0]
        self._detail_start = [0, 2]
        self._detail = [[ring[0], ring[1], ring[2]],
                        [ring[0], ring[2], ring[3]]]
        self.links = [[]]
        self._grid = self
        self._grid_ids = [0]

    def near(self, x, y, radius):
        return [0]

    def clearance(self, x, y, z, *, limit):
        return limit


def test_long_ground_strip_needs_explicit_bounded_sample_budget():
    points = ((1.0, 5.0), (179.0, 5.0))
    default = audit_route_strips(LongTileMesh(), (0,), points)
    assert not default.candidate and default.reason == "segment_strip_sample_budget_exceeded"
    extended = audit_route_strips(LongTileMesh(), (0,), points,
                                  sample_spacing=1.0, max_segment_samples=2048,
                                  max_segment_seconds=10.0, max_seconds=12.0)
    assert extended.candidate and not extended.real_client_accepted
    assert extended.checked_segments == 1
    invalid = audit_route_strips(LongTileMesh(), (0,), points,
                                 max_segment_samples=True)
    assert not invalid.candidate and invalid.reason == "invalid_route_limits"


def test_final_route_segment_cannot_pass_after_elapsed_limit(monkeypatch):
    calls = 0

    def tick():
        nonlocal calls
        calls += 1
        return 1.0 if calls >= 3 else 0.0

    monkeypatch.setattr(route, "time", SimpleNamespace(monotonic=tick))
    result = audit_route_strips(LongTileMesh(), (0,),
                                ((1.0, 5.0), (9.0, 5.0)),
                                max_seconds=0.5)
    assert not result.candidate and result.reason == "route_work_budget_exceeded"
    assert result.checked_segments == 1
