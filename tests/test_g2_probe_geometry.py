from eql_automation.g2_probe_geometry import check_radial_area


class Mesh:
    area = {0: 63}

    def __init__(self, *, slope=0, blocked=False, clearance=None):
        self.slope = {0: slope}
        self.blocked = blocked
        self.clearance_at = clearance or (lambda x, y: 30.0)

    def locate(self, point, *, radius):
        return 0, point

    def raycast(self, start, goal, *, water, zone_lines):
        return not self.blocked, goal

    def clearance(self, x, y, z, *, limit):
        return min(limit, self.clearance_at(x, y))


def test_open_ground_is_only_an_offline_candidate():
    result = check_radial_area(Mesh(), (0.0, 0.0, 0.0))
    assert result.candidate and not result.real_client_accepted
    assert result.samples == 36 * 9
    assert result.clearance_lower_bound == 4.0


def test_unknown_facing_rejects_one_narrow_direction():
    mesh = Mesh(clearance=lambda x, y: 0.5 if x >= 7 and abs(y) < 0.1 else 30.0)
    result = check_radial_area(mesh, (0.0, 0.0, 0.0))
    assert not result.candidate
    assert result.reason == "insufficient_clearance"


def test_blocked_ray_or_steep_start_rejects_before_any_move():
    assert check_radial_area(Mesh(blocked=True), (0.0, 0.0, 0.0)).reason == "ray_blocked_or_steep"
    assert check_radial_area(Mesh(slope=50), (0.0, 0.0, 0.0)).reason == "start_not_safe_ground"


def test_sample_budget_is_bounded():
    result = check_radial_area(Mesh(), (0.0, 0.0, 0.0), max_samples=20)
    assert not result.candidate and result.reason == "sample_budget_exceeded"
