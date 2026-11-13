from eql_automation.lateral_strip_audit import audit_segment_strip


class Grid:
    def __init__(self, count):
        self.count = count

    def near(self, x, y, radius):
        return list(range(self.count))


class StripMesh:
    def __init__(self, *, slope=0.0, overlay=False):
        corners = [(0.0, 0.0), (10.0, 0.0),
                   (10.0, 10.0), (0.0, 10.0)]
        def surface(offset):
            return [(x, y, 2.0 + slope * y + offset) for x, y in corners]
        base = surface(0.0)
        layers = [base, surface(0.5)] if overlay else [base]
        self.polys = layers
        self.area = [63] * len(layers)
        self.component = [1] * len(layers)
        self._detail = []
        self._detail_start = [0]
        for layer in layers:
            self._detail += [[layer[0], layer[1], layer[2]],
                             [layer[0], layer[2], layer[3]]]
            self._detail_start.append(len(self._detail))
        self._grid = Grid(len(layers))
        self._grid_ids = list(range(len(layers)))

    def clearance(self, x, y, z, *, limit):
        return limit


def test_flat_strip_is_only_one_segment_candidate():
    result = audit_segment_strip(StripMesh(), 0, (1.0, 5.0), (9.0, 5.0))
    assert result.candidate and not result.real_client_accepted
    assert result.samples == 51


def test_lateral_grade_rejects_a_centerline_that_looks_flat():
    result = audit_segment_strip(StripMesh(slope=1.1),
                                 0, (1.0, 5.0), (9.0, 5.0))
    assert not result.candidate and result.reason == "cross_grade_too_steep"


def test_overlapping_offset_surfaces_are_ambiguous():
    result = audit_segment_strip(StripMesh(overlay=True),
                                 0, (1.0, 5.0), (9.0, 5.0))
    assert not result.candidate and result.reason == "offset_surface_ambiguous"


def test_strip_work_cap_rejects_before_sampling():
    result = audit_segment_strip(StripMesh(), 0, (1.0, 5.0),
                                 (9.0, 5.0), max_samples=30)
    assert not result.candidate and result.reason == "strip_sample_budget_exceeded"


def test_unsupported_overlapping_forbidden_surface_rejects():
    mesh = StripMesh(overlay=True)
    mesh.area[1] = 1
    mesh._detail_start[2] = mesh._detail_start[1]
    result = audit_segment_strip(mesh, 0, (1.0, 5.0), (9.0, 5.0))
    assert not result.candidate
    assert result.reason == "offset_in_forbidden_or_other_component"
