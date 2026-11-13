from types import SimpleNamespace

from eql_automation.nov12_path_quality import audit_path


class Mesh:
    def __init__(self, *, area=63, slope=0, blocked=False, clearance=None):
        self.area = {0: area}
        self.slope = {0: slope}
        self.blocked = blocked
        self.clearance_at = clearance or (lambda x: 10.0)

    def raycast(self, start, goal, *, water, zone_lines):
        return (not self.blocked, goal)

    def locate(self, point, *, radius):
        return 0, point

    def clearance(self, x, y, z, *, limit):
        return min(limit, self.clearance_at(x))


PATH = SimpleNamespace(points=((0.0, 0.0, 0.0), (10.0, 0.0, 0.0)),
                       polys=(0,))


def test_no_follow_error_never_accepts_geometry():
    result = audit_path(Mesh(), PATH, agent_radius=1.2, follower_error=None)
    assert not result.geometrically_clear
    assert result.reason == "follower_error_unmeasured"


def test_dense_clearance_rejects_mid_segment_pinch():
    # Distance to a vertical wall changes by at most distance walked.
    mesh = Mesh(clearance=lambda x: 0.5 + abs(x - 5))
    result = audit_path(mesh, PATH, agent_radius=1.2, follower_error=0,
                        sample_spacing=2)
    assert not result.geometrically_clear
    assert result.reason == "clearance_below_budget"
    assert result.min_clearance == 1.5
    assert result.required_clearance == 2.2


def test_forbidden_or_steep_corridor_and_blocked_raycast_fail_closed():
    for mesh, reason in ((Mesh(area=1), "forbidden_corridor_area"),
                         (Mesh(slope=81), "steep_corridor_needs_review"),
                         (Mesh(blocked=True), "segment_not_walkable")):
        result = audit_path(mesh, PATH, agent_radius=1.2, follower_error=0)
        assert not result.geometrically_clear
        assert result.reason == reason


def test_sample_budget_and_clear_geometry_still_do_not_prove_client():
    budget = audit_path(Mesh(), PATH, agent_radius=1.2, follower_error=0,
                        max_samples=2)
    assert not budget.geometrically_clear
    assert budget.reason == "sample_budget_exceeded"
    clear = audit_path(Mesh(), PATH, agent_radius=1.2, follower_error=0)
    assert clear.geometrically_clear
    assert not clear.real_client_accepted
    assert clear.min_clearance == 3.2  # Queries are capped at required + 1.
