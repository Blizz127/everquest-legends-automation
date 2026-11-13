from eql_automation.portal_corridor_audit import audit_fixed_corridor


class TwoTileMesh:
    def __init__(self):
        left = [(0.0, 0.0, 2.0), (10.0, 0.0, 2.0),
                (10.0, 10.0, 2.0), (0.0, 10.0, 2.0)]
        right = [(10.0, 0.0, 2.0), (20.0, 0.0, 2.0),
                 (20.0, 10.0, 2.0), (10.0, 10.0, 2.0)]
        self.polys = [left, right]
        self.area = [63, 63]
        self._detail_start = [0, 2, 4]
        self._detail = [[left[0], left[1], left[2]],
                        [left[0], left[2], left[3]],
                        [right[0], right[1], right[2]],
                        [right[0], right[2], right[3]]]
        self.links = [[(1, (10.0, 10.0, 2.0), (10.0, 0.0, 2.0))], []]
        self.wall_clearance = lambda x, y: 8.0

    def clearance(self, x, y, z, *, limit):
        return min(limit, self.wall_clearance(x, y))


def test_connected_centerlines_are_only_offline_candidate():
    result = audit_fixed_corridor(TwoTileMesh(), (0, 1),
                                  (1.0, 5.0), (19.0, 5.0), fractions=(0.5,))
    assert result.candidate and not result.real_client_accepted
    assert result.points == ((1.0, 5.0), (10.0, 5.0), (19.0, 5.0))
    assert result.processed_polygons == 2


def test_narrow_second_tile_rejects_end_to_end_candidate():
    mesh = TwoTileMesh()
    mesh.wall_clearance = lambda x, y: 2.0 if x >= 14.0 else 8.0
    result = audit_fixed_corridor(mesh, (0, 1),
                                  (1.0, 5.0), (19.0, 5.0), fractions=(0.5,))
    assert not result.candidate
    assert result.reason == "no_sampled_segment_through_polygon"
    assert result.failing_polygon == 1


def test_missing_portal_and_small_budget_fail_closed():
    mesh = TwoTileMesh()
    mesh.links[0] = []
    assert audit_fixed_corridor(mesh, (0, 1), (1.0, 5.0),
                                (19.0, 5.0)).reason == "missing_shared_portal"
    mesh = TwoTileMesh()
    assert audit_fixed_corridor(mesh, (0, 1), (1.0, 5.0),
                                (19.0, 5.0), fractions=(0.5,),
                                max_checks=1).reason == "corridor_work_budget_exceeded"


def test_invalid_budget_is_refused_without_querying_mesh():
    result = audit_fixed_corridor(TwoTileMesh(), (0, 1),
                                  (1.0, 5.0), (19.0, 5.0),
                                  max_polygons="many")
    assert not result.candidate and result.reason == "invalid_corridor_limits"


def test_bounded_link_override_can_sample_a_clear_portal_position():
    mesh = TwoTileMesh()
    mesh.wall_clearance = lambda x, y: 8.0 if abs(y - 5.0) < 1.0 else 2.0
    blocked = audit_fixed_corridor(mesh, (0, 1), (1.0, 5.0),
                                   (19.0, 5.0), fractions=(0.1,))
    assert not blocked.candidate and blocked.reason == "no_sampled_portal_crossing"
    clear = audit_fixed_corridor(mesh, (0, 1), (1.0, 5.0),
                                 (19.0, 5.0), fractions=(0.1,),
                                 fractions_by_link={(0, 1): (0.5,)})
    assert clear.candidate and not clear.real_client_accepted
    invalid = audit_fixed_corridor(mesh, (0, 1), (1.0, 5.0),
                                   (19.0, 5.0), fractions_by_link={(0, 1): (True,)})
    assert invalid.reason == "invalid_corridor_limits"
    typo = audit_fixed_corridor(mesh, (0, 1), (1.0, 5.0),
                                (19.0, 5.0), fractions_by_link={(1, 0): (0.5,)})
    assert not typo.candidate and typo.reason == "override_not_on_corridor"
