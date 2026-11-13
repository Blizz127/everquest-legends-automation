from eql_automation.portal_surface_audit import audit_portal_seam, audit_portal_surface


class Mesh:
    area = {0: 63}
    slope = {0: 89.19}  # Polygon-wide maximum may be away from the path.

    def __init__(self, *, height=None, clearance=None):
        self.surface = height or (lambda x, y: 2.0)
        self.wall_distance = clearance or (lambda x, y: 8.0)
        corners = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
        vertices = [(x, y, self.surface(x, y)) for x, y in corners]
        self._detail_start = [0, 2]
        self._detail = [[vertices[0], vertices[1], vertices[2]],
                        [vertices[0], vertices[2], vertices[3]]]

    def contains(self, poly, x, y, *, slack):
        return -slack <= x <= 10 + slack and -slack <= y <= 10 + slack

    def height(self, poly, x, y):
        return self.surface(x, y)

    def clearance(self, x, y, z, *, limit):
        return min(limit, self.wall_distance(x, y))


def test_flat_centerline_can_be_candidate_inside_steep_flagged_polygon():
    result = audit_portal_surface(Mesh(), 0, (1.0, 5.0), (9.0, 5.0))
    assert result.candidate and not result.real_client_accepted
    assert result.samples == 17
    assert result.max_local_grade == 0.0
    assert result.min_clearance == 4.0  # Bounded query does not measure beyond 4.


def test_local_grade_and_middle_clearance_reject_independently():
    steep = audit_portal_surface(Mesh(height=lambda x, y: 2 * x),
                                  0, (1.0, 5.0), (9.0, 5.0))
    assert not steep.candidate and steep.reason == "local_grade_too_steep"
    narrow = audit_portal_surface(
        Mesh(clearance=lambda x, y: 0.2 if 4.5 <= x <= 5.5 else 8.0),
        0, (1.0, 5.0), (9.0, 5.0))
    assert not narrow.candidate and narrow.reason == "clearance_below_budget"


def test_off_polygon_and_closed_area_do_not_pass():
    outside = audit_portal_surface(Mesh(), 0, (1.0, 5.0), (11.0, 5.0))
    assert not outside.candidate and outside.reason == "sample_left_polygon"
    closed = Mesh()
    closed.area = {0: 1}
    assert audit_portal_surface(closed, 0, (1.0, 5.0), (9.0, 5.0)).reason == "forbidden_area"


def test_bounded_samples_reject_longer_segment():
    result = audit_portal_surface(Mesh(), 0, (1.0, 5.0), (9.0, 5.0),
                                  sample_spacing=0.01, max_samples=20)
    assert not result.candidate and result.reason == "sample_budget_exceeded"


def test_missing_detail_support_does_not_use_height_fallback():
    mesh = Mesh()
    mesh._detail_start = [0, 0]
    result = audit_portal_surface(mesh, 0, (1.0, 5.0), (9.0, 5.0))
    assert not result.candidate and result.reason == "unsupported_detail_surface"


def test_clearance_between_samples_uses_half_spacing_margin():
    result = audit_portal_surface(
        Mesh(clearance=lambda x, y: 3.1), 0, (1.0, 5.0), (9.0, 5.0))
    assert not result.candidate and result.reason == "clearance_below_budget"


class TwoPolyMesh(Mesh):
    def __init__(self, *, target_z=2.0, target_shift=0.0):
        super().__init__()
        right = [(10.0 + target_shift, 0.0, target_z),
                 (20.0 + target_shift, 0.0, target_z),
                 (20.0 + target_shift, 10.0, target_z),
                 (10.0 + target_shift, 10.0, target_z)]
        self._detail += [[right[0], right[1], right[2]],
                         [right[0], right[2], right[3]]]
        self._detail_start = [0, 2, 4]
        self.area = {0: 63, 1: 63}
        self.links = [[(1, (10.0, 10.0, 2.0), (10.0, 0.0, 2.0))], []]


def test_seam_needs_shared_portal_and_detail_on_both_sides():
    mesh = TwoPolyMesh()
    pass_result = audit_portal_seam(mesh, 0, 1, (10.0, 5.0))
    assert pass_result.candidate and not pass_result.real_client_accepted
    assert pass_result.source_height == pass_result.target_height == 2.0
    assert audit_portal_seam(mesh, 0, 1, (9.0, 5.0)).reason == "crossing_outside_shared_portal"
    mesh._detail_start = [0, 2, 2]
    assert audit_portal_seam(mesh, 0, 1, (10.0, 5.0)).reason == "unsupported_detail_surface"


def test_seam_rejects_height_discontinuity_and_closed_area():
    mesh = TwoPolyMesh(target_z=3.0)
    assert audit_portal_seam(mesh, 0, 1, (10.0, 5.0)).reason == "height_step_too_large"
    mesh.area[1] = 1
    assert audit_portal_seam(mesh, 0, 1, (10.0, 5.0)).reason == "forbidden_area"


def test_detail_edge_projection_tolerates_quantization_only():
    micro_gap = TwoPolyMesh(target_shift=5e-6)
    result = audit_portal_seam(micro_gap, 0, 1, (10.0, 5.0))
    assert result.candidate and abs(result.target_height - 2.0) < 1e-8
    wider_gap = TwoPolyMesh(target_shift=1e-3)
    assert audit_portal_seam(wider_gap, 0, 1, (10.0, 5.0)).reason == "unsupported_detail_surface"
