from eql_automation.turn_disk_audit import audit_turn_disk


class Grid:
    def near(self, x, y, radius):
        return [0, 1]


class Mesh:
    def __init__(self, grade=0.0):
        def ring(left, right):
            return [(left, 0.0, grade * left), (right, 0.0, grade * right),
                    (right, 10.0, grade * right), (left, 10.0, grade * left)]
        first, second = ring(0.0, 10.0), ring(10.0, 20.0)
        self.polys = [first, second]
        self.area = [63, 63]
        self.component = [0, 0]
        self._detail_start = [0, 2, 4]
        self._detail = [[first[0], first[1], first[2]],
                        [first[0], first[2], first[3]],
                        [second[0], second[1], second[2]],
                        [second[0], second[2], second[3]]]
        self.links = [[(1, (10.0, 10.0, grade * 10),
                        (10.0, 0.0, grade * 10))], []]
        self._grid = Grid()
        self._grid_ids = [0, 1]

    def clearance(self, x, y, z, *, limit):
        return limit


def test_flat_portal_disk_is_only_an_offline_candidate():
    result = audit_turn_disk(Mesh(), 0, 1, (10.0, 5.0))
    assert result.candidate and not result.real_client_accepted
    assert result.samples == 64


def test_turn_disk_rejects_steep_radial_surface_and_bad_limits():
    steep = audit_turn_disk(Mesh(grade=1.5), 0, 1, (10.0, 5.0))
    assert not steep.candidate and steep.reason == "radial_grade_too_steep"
    invalid = audit_turn_disk(Mesh(), 0, 1, (10.0, 5.0), radii=(1.2, 0.6))
    assert not invalid.candidate and invalid.reason == "invalid_turn_limits"


def test_turn_disk_rejects_forbidden_destination():
    mesh = Mesh()
    mesh.area[1] = 4
    result = audit_turn_disk(mesh, 0, 1, (10.0, 5.0))
    assert not result.candidate and result.reason == "seam_forbidden_area"
