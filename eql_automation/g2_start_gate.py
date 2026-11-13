"""Fail-closed copied-mesh preflight for a future supervised G2 pulse.

This produces an offline sampled geometry candidate only. It cannot validate
live dynamic obstacles, establish a log-to-WLD transform or send movement.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import re

from .g2_probe_geometry import check_radial_area
from .g2_pulse_budget import (G2Scene, MAX_ACTUAL_HOLD, MAX_DISPLACEMENT,
                              MIN_SPEED_UPPER_BOUND)
from .g2_scene_observer import MAX_FIX_AGE
from .location_log import RawLocationFix


MAX_G2_GEOMETRY_SAMPLES = 4096


@dataclass(frozen=True)
class AlignedWldFix:
    """A live-calibrated ground point bound to one exact raw log fix.

    A future independent verifier must create this after checking the
    transform against the real client. Merely scoring historical terrain or
    finding a nearby mesh polygon does not satisfy ``live_alignment_verified``.
    """

    raw_fix: RawLocationFix
    ground_wld_xyz: tuple[float, float, float]
    zone_short_name: str
    mesh_sha256: str
    calibration_record_id: str
    live_alignment_verified: bool = False


@dataclass(frozen=True)
class G2StartCheck:
    candidate: bool
    reason: str
    sampled_radius: float | None = None
    samples: int = 0
    real_client_accepted: bool = False
    budget_authorized: bool = False


def check_g2_start(mesh, scene: G2Scene, fix: RawLocationFix, *,
                   aligned_fix: AlignedWldFix | None, mesh_sha256: str,
                   expected_zone_id: int, expected_zone_display_name: str,
                   speed_upper_bound: float, radius: float = 18.0,
                   directions: int = 36, sample_spacing: float = 1.0,
                   max_samples: int = 1024) -> G2StartCheck:
    """Check provenance and a bounded disk; never grant a live input permit."""
    if (not isinstance(scene, G2Scene) or not isinstance(fix, RawLocationFix) or
            not isinstance(aligned_fix, AlignedWldFix) or
            aligned_fix.raw_fix is not fix or
            aligned_fix.live_alignment_verified is not True or
            not isinstance(aligned_fix.calibration_record_id, str) or
            not aligned_fix.calibration_record_id or
            not isinstance(mesh_sha256, str) or
            re.fullmatch(r"[0-9a-f]{64}", mesh_sha256) is None or
            aligned_fix.mesh_sha256 != mesh_sha256 or
            not isinstance(expected_zone_id, int) or
            isinstance(expected_zone_id, bool) or expected_zone_id < 0 or
            not isinstance(expected_zone_display_name, str) or
            not expected_zone_display_name or
            fix.zone_id != expected_zone_id or
            fix.zone_display_name != expected_zone_display_name or
            not isinstance(aligned_fix.zone_short_name, str) or
            aligned_fix.zone_short_name != scene.zone or
            scene.log_epoch != fix.log_epoch or
            scene.fix_seq != fix.log_line_seq or
            scene.zone_generation != fix.zone_generation or
            scene.raw_location != fix.raw_coordinates or
            not isinstance(scene.at, (int, float)) or isinstance(scene.at, bool) or
            not math.isfinite(scene.at) or
            not 0 <= scene.at - fix.received_monotonic <= MAX_FIX_AGE or
            not all(value is True for value in
                    (scene.focused, scene.owner_keys_clear, scene.chat_clear,
                     scene.target_absent, scene.combat_clear,
                     scene.no_transition, scene.no_incoming_attack))):
        return G2StartCheck(False, "missing_live_alignment_or_fresh_scene")
    point = aligned_fix.ground_wld_xyz
    if (not isinstance(point, tuple) or len(point) != 3 or
            any(not isinstance(value, (int, float)) or isinstance(value, bool) or
                not math.isfinite(value) for value in point)):
        return G2StartCheck(False, "invalid_aligned_ground_point")
    if (not isinstance(speed_upper_bound, (int, float)) or
            isinstance(speed_upper_bound, bool) or
            not math.isfinite(speed_upper_bound) or
            speed_upper_bound < MIN_SPEED_UPPER_BOUND or
            not isinstance(radius, (int, float)) or isinstance(radius, bool) or
            not math.isfinite(radius) or
            not 0 < radius <= MAX_DISPLACEMENT or
            speed_upper_bound * MAX_ACTUAL_HOLD > radius):
        return G2StartCheck(False, "radius_cannot_cover_worst_case_pulse")
    if (not isinstance(directions, int) or isinstance(directions, bool) or
            directions < 4 or
            not isinstance(sample_spacing, (int, float)) or
            isinstance(sample_spacing, bool) or
            not math.isfinite(sample_spacing) or sample_spacing <= 0 or
            not isinstance(max_samples, int) or isinstance(max_samples, bool) or
            not 1 <= max_samples <= MAX_G2_GEOMETRY_SAMPLES or
            directions * (math.ceil(radius / sample_spacing) + 1) > max_samples):
        return G2StartCheck(False, "radial_sample_budget_insufficient")
    try:
        radial = check_radial_area(mesh, point, radius=radius,
                                   directions=directions,
                                   sample_spacing=sample_spacing,
                                   max_samples=max_samples)
    except Exception:
        return G2StartCheck(False, "mesh_geometry_unavailable")
    if not radial.candidate:
        return G2StartCheck(False, radial.reason, samples=radial.samples)
    if (not isinstance(radial.center, tuple) or len(radial.center) != 3 or
            any(not isinstance(value, (int, float)) or not math.isfinite(value)
                for value in radial.center)):
        return G2StartCheck(False, "start_snapped_away_from_verified_point",
                            samples=radial.samples)
    snap_distance = math.dist(radial.center, point)
    if snap_distance > 0.0005:
        return G2StartCheck(False, "start_snapped_away_from_verified_point",
                            samples=radial.samples)
    usable_radius = radius - snap_distance
    if speed_upper_bound * MAX_ACTUAL_HOLD > usable_radius:
        return G2StartCheck(False, "radius_cannot_cover_worst_case_pulse",
                            samples=radial.samples)
    return G2StartCheck(True, "offline_sampled_open_area_candidate",
                        float(usable_radius), radial.samples)
