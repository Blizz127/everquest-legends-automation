from dataclasses import replace
from datetime import datetime

from eql_automation.g2_pulse_budget import G2Scene
from eql_automation.g2_start_gate import AlignedWldFix, check_g2_start
from eql_automation.location_log import RawLocationFix


HASH = "a" * 64


class Mesh:
    area = {0: 63}
    slope = {0: 0.0}

    def __init__(self, *, snap=0.0):
        self.calls = 0
        self.snap = snap

    def locate(self, point, *, radius):
        self.calls += 1
        return 0, (point[0] + self.snap, point[1], point[2])

    def raycast(self, start, goal, *, water, zone_lines):
        self.calls += 1
        return True, goal

    def clearance(self, x, y, z, *, limit):
        self.calls += 1
        return limit


def evidence():
    fix = RawLocationFix(54, "Greater Faydark", (1.0, 2.0, 3.0),
                         datetime(2026, 11, 13, 14, 20), 100.0, 1, 7, 3)
    scene = G2Scene(100.1, "gfaydark", fix.raw_coordinates, 1, 7, 3,
                    True, True, True, True, True, True, True)
    aligned = AlignedWldFix(fix, (10.0, 20.0, 30.0), "gfaydark", HASH,
                            "synthetic-only-calibration", True)
    return scene, fix, aligned


def check(mesh, scene, fix, aligned, **changes):
    options = dict(aligned_fix=aligned, mesh_sha256=HASH,
                   expected_zone_id=54, expected_zone_display_name="Greater Faydark",
                   speed_upper_bound=60)
    options.update(changes)
    return check_g2_start(mesh, scene, fix, **options)


def test_unaligned_raw_location_never_queries_mesh():
    scene, fix, aligned = evidence()
    mesh = Mesh()
    assert not check(mesh, scene, fix, None).candidate
    assert not check(mesh, scene, fix, replace(aligned, live_alignment_verified=False)).candidate
    assert mesh.calls == 0


def test_identity_hash_and_stale_scene_refuse_before_geometry():
    scene, fix, aligned = evidence()
    mesh = Mesh()
    assert not check(mesh, scene, fix, replace(aligned, mesh_sha256="b" * 64)).candidate
    assert not check(mesh, replace(scene, fix_seq=8), fix, aligned).candidate
    assert not check(mesh, replace(scene, at=100.6), fix, aligned).candidate
    assert not check(mesh, scene, replace(fix), aligned).candidate
    wrong_zone = replace(fix, zone_id=99, zone_display_name="Other Zone")
    assert not check(mesh, replace(scene, raw_location=wrong_zone.raw_coordinates,
                                   log_epoch=wrong_zone.log_epoch,
                                   fix_seq=wrong_zone.log_line_seq,
                                   zone_generation=wrong_zone.zone_generation),
                     wrong_zone, replace(aligned, raw_fix=wrong_zone)).candidate
    assert mesh.calls == 0


def test_pulse_radius_and_explicit_sample_budget_must_fit():
    scene, fix, aligned = evidence()
    mesh = Mesh()
    assert check(mesh, scene, fix, aligned, radius=8).reason == "radius_cannot_cover_worst_case_pulse"
    assert check(mesh, scene, fix, aligned, radius=18, max_samples=512).reason == "radial_sample_budget_insufficient"
    assert mesh.calls == 0


def test_synthetic_18_unit_disk_is_sampled_only_and_large_snap_refuses():
    scene, fix, aligned = evidence()
    result = check(Mesh(), scene, fix, aligned)
    assert result.candidate and result.sampled_radius == 18
    assert result.samples == 36 * 19
    assert not result.real_client_accepted and not result.budget_authorized
    assert check(Mesh(snap=0.25), scene, fix, aligned).reason == "start_snapped_away_from_verified_point"
    assert check(Mesh(snap=0.0002), scene, fix, aligned,
                 speed_upper_bound=90).reason == "radius_cannot_cover_worst_case_pulse"
