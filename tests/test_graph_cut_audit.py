from eql_automation.graph_cut_audit import ground_reachability, portal_clearance_upper_bound


class Mesh:
    area = {0: 63, 1: 63, 2: 63, 3: 63}
    links = [
        [(1, (), ()), (2, (), ())],
        [(3, (), ())],
        [(3, (), ())],
        [],
    ]


def test_ground_bypass_and_cut_are_topological_only():
    mesh = Mesh()
    bypass = ground_reachability(mesh, 0, 3, blocked=frozenset({1}))
    assert bypass.reachable and bypass.path == (0, 2, 3)
    assert not bypass.real_client_accepted
    cut = ground_reachability(mesh, 0, 3, blocked=frozenset({1, 2}))
    assert not cut.reachable and cut.reason == "disconnected_in_copied_ground_graph"


def test_closed_endpoint_and_visit_budget_do_not_prove_disconnection():
    mesh = Mesh()
    mesh.area = dict(mesh.area)
    mesh.area[3] = 1
    assert ground_reachability(mesh, 0, 3).reason == "closed_endpoint"
    mesh.area[3] = 63
    budget = ground_reachability(mesh, 0, 3, max_visits=1)
    assert not budget.reachable and budget.reason == "graph_visit_budget_exceeded"


def test_portal_clearance_upper_bound_uses_half_step_margin():
    class PortalMesh:
        links = [[(1, (0.0, 0.0, 2.0), (10.0, 0.0, 2.0))], []]

        def clearance(self, x, y, z, *, limit):
            return min(limit, x, 10.0 - x)

    below = portal_clearance_upper_bound(PortalMesh(), 0, 1,
                                         height=2.0, required=6.0, sample_count=11)
    assert below.below_required and not below.real_client_accepted
    assert below.max_sample == 5.0 and below.upper_bound == 5.5
    not_proved = portal_clearance_upper_bound(PortalMesh(), 0, 1,
                                              height=2.0, required=5.0, sample_count=11)
    assert not not_proved.below_required


def test_missing_portal_cannot_prove_clearance_bound():
    result = portal_clearance_upper_bound(Mesh(), 3, 0, height=2.0)
    assert not result.below_required and result.reason == "missing_shared_portal"


def test_malformed_negative_link_is_not_a_valid_bypass():
    mesh = Mesh()
    mesh.links = list(mesh.links)
    mesh.links[0] = [(-1, (), ())]
    result = ground_reachability(mesh, 0, 3)
    assert not result.reachable and result.reason == "damaged_graph"
