"""Continuous XY ground coverage for a convex possible-motion footprint.

Clipped detail faces must cover the footprint without holes, overlapping
floors, steep planes or discontinuous seams (within explicit numerical
tolerances). This is a copied-navmesh ground check, not a proof of body
clearance, BSP hazards, dynamic obstacles, calibrated movement or live input
permission. The caller must supply every local intersecting detail face.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


def finite(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def area(points):
    if len(points) < 3:
        return 0.
    return abs(sum(cross(points[0], points[i], points[i + 1]) for i in range(1, len(points) - 1))) / 2


def hull(points):
    points = sorted(set(points))
    def half(seq):
        out = []
        for point in seq:
            while len(out) >= 2 and cross(out[-2], out[-1], point) <= 0:
                out.pop()
            out.append(point)
        return out
    return tuple(half(points)[:-1] + half(reversed(points))[:-1])


def clip(subject, boundary):
    """Intersect convex polygons; boundary is counter-clockwise."""
    result = list(subject)
    for i, a in enumerate(boundary):
        b = boundary[(i + 1) % len(boundary)]
        source, result = result, []
        if not source:
            break
        previous = source[-1]
        old = cross(a, b, previous)
        for point in source:
            new = cross(a, b, point)
            if (new >= 0) != (old >= 0):
                fraction = old / (old - new)
                result.append((previous[0] + fraction * (point[0] - previous[0]),
                               previous[1] + fraction * (point[1] - previous[1])))
            if new >= 0:
                result.append(point)
            previous, old = point, new
    return tuple(result)


def motion_footprint(origin, heading_degrees, reach, *, position_error,
                     heading_error_degrees, post_release_drift, extra_radius=0., sides=16):
    """Circumscribe a forward uncertainty capsule (reach=0 also covers pivots).

    For any heading error ≤theta and travel ≤reach, deviation from the
    nominal ray is at most 2*reach*sin(theta/2). Adding initial-position,
    residual-drift and optional extra-radius bounds encloses all times, not
    just the endpoint. These are caller-supplied bounds, never calibration.
    """
    if (not isinstance(origin, tuple) or len(origin) != 2 or not all(finite(v) for v in origin)
            or not all(finite(v) for v in (heading_degrees, reach, position_error,
                                           heading_error_degrees, post_release_drift, extra_radius))
            or not 0 <= heading_degrees < 360 or reach < 0
            or min(position_error, post_release_drift, extra_radius) < 0
            or not 0 <= heading_error_degrees <= 180
            or not isinstance(sides, int) or isinstance(sides, bool) or not 8 <= sides <= 64):
        raise ValueError("Invalid motion uncertainty bounds")
    radius = position_error + post_release_drift + extra_radius + 2 * reach * math.sin(math.radians(heading_error_degrees) / 2)
    if radius <= 0:
        raise ValueError("A nonzero footprint radius is required")
    angle = math.radians(heading_degrees)
    end = (origin[0] + reach * math.sin(angle), origin[1] + reach * math.cos(angle))
    outer = radius / math.cos(math.pi / sides)
    if not all(finite(v) for v in (*end, outer)):
        raise ValueError("Motion footprint overflow")
    points = [(p[0] + outer * math.cos(2 * math.pi * i / sides),
               p[1] + outer * math.sin(2 * math.pi * i / sides))
              for p in (origin, end) for i in range(sides)]
    return hull(points)


@dataclass(frozen=True)
class GroundFace:
    vertices: tuple[tuple[float, float, float], ...]
    area_id: int
    component: int


@dataclass(frozen=True)
class GroundCoverage:
    candidate: bool
    reason: str
    footprint_area: float = 0.
    covered_area: float = 0.
    used_faces: int = 0
    max_grade: float = 0.
    real_client_accepted: bool = False
    input_authorized: bool = False
    failed_face: int | None = None
    overlap_area: float = 0.


def check_ground_coverage(footprint, faces, *, reference, component,
                          maximum_grade=1., vertical_window=3.,
                          height_tolerance=.01, area_tolerance=1e-7,
                          max_faces=96):
    """Check complete local face coverage, including clipped-face overlaps.

    Face triangles outside the explicit height window are ignored, so this
    function does not check overhang/headroom. Partially intersecting height
    windows, invalid data and excessive candidate counts refuse.
    """
    if (not isinstance(footprint, tuple) or not 3 <= len(footprint) <= 128
            or any(not isinstance(p, tuple) or len(p) != 2 or not all(finite(v) for v in p) for p in footprint)
            or not isinstance(reference, tuple) or len(reference) != 3 or not all(finite(v) for v in reference)
            or not isinstance(component, int) or isinstance(component, bool) or component < 0
            or any(not finite(v) or v <= 0 for v in (maximum_grade, vertical_window, height_tolerance, area_tolerance))
            or not isinstance(max_faces, int) or isinstance(max_faces, bool) or not 1 <= max_faces <= 256
            or not isinstance(faces, tuple) or len(faces) > max_faces):
        return GroundCoverage(False, "invalid_footprint_or_face_budget")
    boundary = hull(footprint)
    if len(boundary) != len(footprint) or area(boundary) <= area_tolerance:
        return GroundCoverage(False, "footprint_must_be_convex_and_nondegenerate")
    if any(cross(boundary[i], boundary[(i + 1) % len(boundary)], reference[:2]) < -1e-10 for i in range(len(boundary))):
        return GroundCoverage(False, "reference_outside_footprint")
    expected, covered, highest, overlap, used = area(boundary), 0., 0., 0., []
    origin_heights = []
    current = None
    def result(ok, reason):
        # Subtract all pair overlaps: a conservative union-area lower bound.
        # Many individually tiny overlaps must not compensate for a hole.
        return GroundCoverage(ok, reason, expected, max(0., covered - overlap), len(used), highest,
                              failed_face=current, overlap_area=overlap)
    for current, face in enumerate(faces):
        if (not isinstance(face, GroundFace) or not isinstance(face.vertices, tuple) or len(face.vertices) != 3
                or not isinstance(face.area_id, int) or isinstance(face.area_id, bool)
                or not isinstance(face.component, int) or isinstance(face.component, bool)
                or any(not isinstance(v, tuple) or len(v) != 3 or not all(finite(n) for n in v) for v in face.vertices)):
            return result(False, "invalid_detail_face")
        a, b, c = face.vertices
        determinant = cross(a, b, c)
        if abs(determinant) < 1e-12:
            continue  # No XY ground area; not a collision-wall test.
        triangle = tuple(v[:2] for v in (a, b, c))
        if determinant < 0:
            triangle = tuple(reversed(triangle))
        patch = clip(triangle, boundary)
        patch_area = area(patch)
        if patch_area <= area_tolerance:
            continue
        dx = ((b[2] - a[2]) * (c[1] - a[1]) - (c[2] - a[2]) * (b[1] - a[1])) / determinant
        dy = ((b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2])) / determinant
        plane = (a[0], a[1], a[2], dx, dy)
        def height(p, plane=plane):
            x, y, z, gx, gy = plane
            return z + (p[0] - x) * gx + (p[1] - y) * gy
        heights = [height(p) for p in patch]
        low, high = reference[2] - vertical_window, reference[2] + vertical_window
        if max(heights) < low or min(heights) > high:
            continue
        if min(heights) < low or max(heights) > high:
            return result(False, "surface_crosses_height_window")
        if face.area_id != 63 or face.component != component:
            return result(False, "forbidden_area_or_other_component")
        grade = math.hypot(dx, dy)
        highest = max(highest, grade)
        if grade > maximum_grade:
            return result(False, "steep_detail_plane")
        for previous, previous_height in used:
            intersection = clip(patch, previous)
            overlap += area(intersection)
            if overlap > area_tolerance:
                return result(False, "overlapping_ground_faces")
            if any(abs(height(p) - previous_height(p)) > height_tolerance for p in intersection):
                return result(False, "discontinuous_ground_seam")
        if all(cross(triangle[i], triangle[(i + 1) % 3], reference[:2]) >= -1e-10 for i in range(3)):
            origin_heights.append(height(reference[:2]))
        used.append((patch, height))
        covered += patch_area
    current = None
    if not origin_heights or any(abs(z - reference[2]) > height_tolerance for z in origin_heights):
        return result(False, "reference_ground_not_supported")
    if abs(covered - overlap - expected) > area_tolerance:
        return result(False, "uncovered_ground_area")
    return result(True, "continuous_detail_ground_candidate_only")
