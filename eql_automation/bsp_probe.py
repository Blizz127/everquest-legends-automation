"""Fail-closed point lookup in a copied WLD BSP tree, for offline review.

The plane test and child direction follow EQEmu's water_map_v1.cpp:
https://github.com/EQEmu/EQEmu/blob/master/zone/water_map_v1.cpp#L493-L537
Inputs are raw WLD XYZ, not EQEmu server XYZ or untransformed map XY.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import hypot, isfinite
from struct import unpack_from

from .map_alignment import map_to_wld_xy
from .nav import Point
from .region_audit import audit_bsp_regions
from .wld_inventory import WLDInventory


@dataclass(frozen=True)
class BspProbe:
    region_id: int | None
    labels: tuple[str, ...]
    steps: int
    reason: str
    zoneline_candidate: bool
    collision_verified: bool = False
    live_transition_verified: bool = False


@dataclass(frozen=True)
class BspSegmentSpan:
    start_fraction: float
    end_fraction: float
    region_id: int | None
    labels: tuple[str, ...]
    reason: str


class BspPointLookup:
    def __init__(self, wld: WLDInventory) -> None:
        audit = audit_bsp_regions(wld)
        tree = next(fragment for fragment in wld.fragments if fragment.type_code == 0x21)
        body = wld.body(tree)
        self.nodes = tuple(unpack_from("<4f3I", body, 4 + index * 28)
                           for index in range(audit["bsp_node_count"]))
        self.labels_by_region: dict[int, set[str]] = {}
        for label, ids in audit["candidate_region_ids"].items():
            for region_id in ids:
                self.labels_by_region.setdefault(region_id, set()).add(label)

    def probe(self, x: float, y: float, z: float) -> BspProbe:
        if not all(isfinite(value) for value in (x, y, z)):
            raise ValueError("BSP point must be finite WLD XYZ")
        if not self.nodes:
            return BspProbe(None, (), 0, "empty tree", False)
        node_number = 1
        seen: set[int] = set()
        for steps in range(1, min(len(self.nodes), 256) + 1):
            if node_number in seen:
                return BspProbe(None, (), steps, "cycle", False)
            seen.add(node_number)
            nx, ny, nz, split, region_ref, left, right = self.nodes[node_number - 1]
            if left == 0 and right == 0:
                if region_ref == 0:
                    return BspProbe(None, (), steps, "leaf has no region", False)
                region_id = region_ref - 1
                labels = tuple(sorted(self.labels_by_region.get(region_id, ())))
                return BspProbe(region_id, labels, steps, "labelled leaf" if labels else
                                "unlabelled leaf", "zoneline" in labels)
            distance = x * nx + y * ny + z * nz + split
            if not isfinite(distance):
                return BspProbe(None, (), steps, "nonfinite BSP distance", False)
            if abs(distance) <= 1e-6:
                return BspProbe(None, (), steps, "on BSP plane", False)
            node_number = left if distance > 0 else right
            if node_number == 0:
                return BspProbe(None, (), steps, "missing BSP child", False)
        return BspProbe(None, (), min(len(self.nodes), 256), "depth limit", False)

    def trace_segment(self, start: tuple[float, float, float],
                      end: tuple[float, float, float], *,
                      max_visits: int = 4096) -> tuple[BspSegmentSpan, ...]:
        """Partition one copied BSP centerline; uncertain intervals stay unknown.

        This does not establish collision clearance or client movement. A plane
        endpoint is conservatively unknown because it has no unique BSP side.
        """
        if (not isinstance(start, (tuple, list)) or len(start) != 3 or
                not isinstance(end, (tuple, list)) or len(end) != 3 or
                not all(isinstance(value, (int, float)) and
                        not isinstance(value, bool) and isfinite(value)
                        for value in (*start, *end))):
            raise ValueError("BSP segment needs finite WLD XYZ endpoints")
        if not isinstance(max_visits, int) or isinstance(max_visits, bool) or not 1 <= max_visits <= 4096:
            raise ValueError("BSP segment visit cap is outside bounds")
        first = tuple(float(value) for value in start)
        last = tuple(float(value) for value in end)
        def unknown(left: float, right: float, reason: str) -> BspSegmentSpan:
            return BspSegmentSpan(left, right, None, (), reason)

        if first == last:
            probe = self.probe(*first)
            return (BspSegmentSpan(0.0, 1.0, probe.region_id, probe.labels,
                                   probe.reason),)
        if not self.nodes:
            return (unknown(0.0, 1.0, "empty tree"),)
        # LIFO entries are pushed in reverse path order to preserve intervals.
        stack = [(1, 0.0, 1.0, first, last, frozenset())]
        spans: list[BspSegmentSpan] = []
        visits = 0
        while stack:
            if visits >= max_visits or len(stack) + len(spans) > 1024:
                return (unknown(0.0, 1.0, "BSP segment budget exceeded"),)
            node_number, t0, t1, a, b, seen = stack.pop()
            visits += 1
            if node_number == 0:
                spans.append(unknown(t0, t1, "missing BSP child"))
                continue
            if node_number < 1 or node_number > len(self.nodes):
                spans.append(unknown(t0, t1, "BSP child out of range"))
                continue
            if node_number in seen:
                spans.append(unknown(t0, t1, "cycle"))
                continue
            if len(seen) >= 256:
                spans.append(unknown(t0, t1, "depth limit"))
                continue
            nx, ny, nz, split, region_ref, left, right = self.nodes[node_number - 1]
            if left == 0 and right == 0:
                if region_ref == 0:
                    spans.append(unknown(t0, t1, "leaf has no region"))
                else:
                    region_id = region_ref - 1
                    labels = tuple(sorted(self.labels_by_region.get(region_id, ())))
                    spans.append(BspSegmentSpan(
                        t0, t1, region_id, labels,
                        "labelled leaf" if labels else "unlabelled leaf"))
                continue
            d0 = a[0] * nx + a[1] * ny + a[2] * nz + split
            d1 = b[0] * nx + b[1] * ny + b[2] * nz + split
            if not isfinite(d0) or not isfinite(d1):
                spans.append(unknown(t0, t1, "nonfinite BSP distance"))
                continue
            if abs(d0) <= 1e-6 or abs(d1) <= 1e-6:
                spans.append(unknown(t0, t1, "endpoint on BSP plane"))
                continue
            next_seen = seen | {node_number}
            if (d0 > 0) == (d1 > 0):
                stack.append((left if d0 > 0 else right,
                              t0, t1, a, b, next_seen))
                continue
            denominator = d0 - d1
            if not isfinite(denominator) or denominator == 0:
                spans.append(unknown(t0, t1, "unstable BSP split"))
                continue
            fraction = d0 / denominator
            midpoint = tuple(a[index] + (b[index] - a[index]) * fraction
                             for index in range(3))
            tm = t0 + (t1 - t0) * fraction
            if (not 0 < fraction < 1 or not t0 < tm < t1 or
                    not all(isfinite(value) for value in midpoint)):
                spans.append(unknown(t0, t1, "unstable BSP split"))
                continue
            stack.append((left if d1 > 0 else right,
                          tm, t1, midpoint, b, next_seen))
            stack.append((left if d0 > 0 else right,
                          t0, tm, a, midpoint, next_seen))
        return tuple(spans)


def nearby_zoneline_candidate(lookup: BspPointLookup, map_label: Point,
                              surface_z: float | None, *,
                              transform: str, radius: int = 100,
                              step: int = 5) -> dict:
    """Sample a bounded XY grid; never certify a transition or nav edge."""
    if not 0 < radius <= 100 or not 1 <= step <= 10:
        raise ValueError("BSP label search exceeds safety bounds")
    x, y = map_to_wld_xy(map_label.x, map_label.y, transform)
    heights = [map_label.z]
    if surface_z is not None:
        if not isfinite(surface_z):
            raise ValueError("Candidate surface height is nonfinite")
        heights.extend((surface_z, surface_z + 1.0))
    samples = sorted(set(range(-radius, radius + 1, step)) | {0})
    offsets = sorted(((dx, dy) for dx in samples
                      for dy in samples
                      if dx * dx + dy * dy <= radius * radius),
                     key=lambda delta: (delta[0] * delta[0] + delta[1] * delta[1],
                                        delta[0], delta[1]))
    nearest = None
    for dx, dy in offsets:
        for z in heights:
            probe = lookup.probe(x + dx, y + dy, z)
            if probe.zoneline_candidate:
                nearest = {
                    "wld_xyz": [x + dx, y + dy, z],
                    "xy_distance_from_label": round(hypot(dx, dy), 4),
                    "region_id": probe.region_id,
                    "labels": list(probe.labels),
                }
                break
        if nearest is not None:
            break
    return {
        "map_label_xyz": [map_label.x, map_label.y, map_label.z],
        "wld_label_xy": [x, y],
        "label_probe": asdict(lookup.probe(x, y, map_label.z)),
        "search_radius": radius,
        "search_step": step,
        "nearest_zoneline_candidate": nearest,
        "transition_verified": False,
        "navigation_edge_accepted": False,
    }
