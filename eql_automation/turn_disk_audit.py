"""Conservative offline ground check around one copied-mesh portal turn.

A disk is stronger than the particular turn arc. Passing it is still sampled
geometry only: thin terrain changes, dynamics and client motion are unknown.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import time

from .lateral_strip_audit import _ground_height
from .portal_surface_audit import audit_portal_seam


@dataclass(frozen=True)
class TurnDiskCheck:
    candidate: bool
    reason: str
    samples: int = 0
    radius: float | None = None
    direction: int | None = None
    center_height: float | None = None
    offset_height: float | None = None
    real_client_accepted: bool = False


def audit_turn_disk(mesh, source_poly: int, target_poly: int,
                    crossing_xy: tuple[float, float], *,
                    radii: tuple[float, ...] = (0.6, 1.2),
                    directions: int = 32,
                    maximum_grade: float = 1.0,
                    edge_clearance: float = 0.5,
                    max_candidates: int = 24,
                    max_seconds: float = 3.0) -> TurnDiskCheck:
    """Sample a whole turn disk; reject any unknown or steep radial/arc cell."""
    if (not isinstance(radii, tuple) or not 1 <= len(radii) <= 4 or
            any(not isinstance(r, (int, float)) or isinstance(r, bool) or
                not math.isfinite(r) or r <= 0 for r in radii) or
            any(a >= b for a, b in zip(radii, radii[1:])) or
            not isinstance(directions, int) or isinstance(directions, bool) or
            not 8 <= directions <= 64 or
            not isinstance(max_candidates, int) or isinstance(max_candidates, bool) or
            max_candidates < 1 or
            any(not isinstance(v, (int, float)) or isinstance(v, bool) or
                not math.isfinite(v) or v <= 0
                for v in (maximum_grade, edge_clearance, max_seconds))):
        return TurnDiskCheck(False, "invalid_turn_limits")
    started = time.monotonic()
    seam = audit_portal_seam(mesh, source_poly, target_poly, crossing_xy)
    if not seam.candidate:
        return TurnDiskCheck(False, "seam_" + seam.reason)
    try:
        component = int(mesh.component[source_poly])
        if component < 0 or component != int(mesh.component[target_poly]):
            return TurnDiskCheck(False, "seam_component_unknown")
    except (AttributeError, IndexError, KeyError, TypeError):
        return TurnDiskCheck(False, "seam_component_unknown")
    center_z = seam.source_height
    previous_radius = 0.0
    previous_heights = [center_z] * directions
    samples = 0
    for radius in radii:
        heights = []
        radial_gap = radius - previous_radius
        angular_half_chord = radius * math.sin(math.pi / directions)
        clearance_floor = edge_clearance + math.hypot(radial_gap / 2, angular_half_chord)
        for direction in range(directions):
            if time.monotonic() - started > max_seconds:
                return TurnDiskCheck(False, "turn_work_budget_exceeded", samples,
                                     radius, direction, center_z)
            angle = 2 * math.pi * direction / directions
            x = crossing_xy[0] + radius * math.cos(angle)
            y = crossing_xy[1] + radius * math.sin(angle)
            reason, z = _ground_height(mesh, x, y, center_z, component,
                                       max_candidates, radius * maximum_grade + 0.5)
            samples += 1
            if z is None:
                return TurnDiskCheck(False, reason, samples, radius, direction,
                                     center_z)
            if (abs(z - center_z) / radius > maximum_grade or
                    abs(z - previous_heights[direction]) / radial_gap > maximum_grade):
                return TurnDiskCheck(False, "radial_grade_too_steep", samples,
                                     radius, direction, center_z, z)
            clearance = float(mesh.clearance(x, y, z, limit=edge_clearance + 1))
            if not math.isfinite(clearance) or clearance < clearance_floor:
                return TurnDiskCheck(False, "turn_clearance_below_budget", samples,
                                     radius, direction, center_z, z)
            heights.append(z)
        chord = 2 * radius * math.sin(math.pi / directions)
        for direction, z in enumerate(heights):
            if abs(z - heights[(direction + 1) % directions]) / chord > maximum_grade:
                return TurnDiskCheck(False, "angular_grade_too_steep", samples,
                                     radius, direction, center_z, z)
        previous_radius = radius
        previous_heights = heights
    return TurnDiskCheck(True, "sampled_turn_disk_candidate_only", samples,
                         center_height=center_z)
