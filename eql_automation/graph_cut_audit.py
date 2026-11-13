"""Bounded, read-only ground-graph reachability for copied client navmeshes.

Graph connectivity is only a topological hint. It does not verify clearance,
terrain, a traversable route, or real-client movement.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class GroundReachability:
    reachable: bool
    reason: str
    visited: int = 0
    path: tuple[int, ...] = ()
    real_client_accepted: bool = False


@dataclass(frozen=True)
class PortalClearanceBound:
    below_required: bool
    reason: str
    samples: int = 0
    max_sample: float | None = None
    upper_bound: float | None = None
    real_client_accepted: bool = False


def portal_clearance_upper_bound(mesh, source_poly: int, target_poly: int, *,
                                 height: float, required: float = 3.0,
                                 sample_count: int = 1001) -> PortalClearanceBound:
    """Bound maximum clearance along one portal at a fixed surface height.

    A distance to a fixed set of wall segments is 1-Lipschitz in XY. At a
    fixed height, the copied mesh's wall-height filter selects that same set
    everywhere, so the largest unsampled value is at most half a sample step
    above the largest sampled value. This says nothing about movement safety.
    """
    if (any(not isinstance(p, int) or isinstance(p, bool) or p < 0
            for p in (source_poly, target_poly)) or
            any(not isinstance(v, (int, float)) or isinstance(v, bool) or
                not math.isfinite(v) for v in (height, required)) or required <= 0 or
            not isinstance(sample_count, int) or isinstance(sample_count, bool) or
            not 2 <= sample_count <= 5001):
        return PortalClearanceBound(False, "invalid_portal_limits")
    try:
        left, right = next((left, right) for neighbor, left, right
                           in mesh.links[source_poly] if neighbor == target_poly)
    except (AttributeError, IndexError, KeyError, TypeError, StopIteration):
        return PortalClearanceBound(False, "missing_shared_portal")
    distance = math.hypot(right[0] - left[0], right[1] - left[1])
    if not math.isfinite(distance) or distance <= 1e-9:
        return PortalClearanceBound(False, "degenerate_portal")
    highest = -math.inf
    for index in range(sample_count):
        fraction = index / (sample_count - 1)
        x = (1 - fraction) * left[0] + fraction * right[0]
        y = (1 - fraction) * left[1] + fraction * right[1]
        clearance = float(mesh.clearance(x, y, height, limit=required + 1))
        if not math.isfinite(clearance) or clearance < 0:
            return PortalClearanceBound(False, "invalid_clearance", index)
        highest = max(highest, clearance)
    upper = highest + distance / (sample_count - 1) / 2
    return PortalClearanceBound(upper < required, "fixed_height_mesh_clearance_bound_only",
                                sample_count, highest, upper)


def ground_reachability(mesh, start: int, goal: int, *,
                        blocked: frozenset[int] = frozenset(),
                        max_visits: int = 10000) -> GroundReachability:
    if (any(not isinstance(v, int) or isinstance(v, bool) or v < 0
            for v in (start, goal)) or
            not isinstance(blocked, frozenset) or
            any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in blocked) or
            not isinstance(max_visits, int) or isinstance(max_visits, bool) or max_visits < 1):
        return GroundReachability(False, "invalid_graph_limits")
    try:
        if int(mesh.area[start]) != 63 or int(mesh.area[goal]) != 63:
            return GroundReachability(False, "closed_endpoint")
        mesh.links[start]
    except (AttributeError, IndexError, KeyError, TypeError):
        return GroundReachability(False, "unknown_endpoint")
    if start in blocked or goal in blocked:
        return GroundReachability(False, "blocked_endpoint")
    queue = deque([start])
    parent = {start: None}
    while queue:
        if len(parent) > max_visits:
            return GroundReachability(False, "graph_visit_budget_exceeded", len(parent))
        current = queue.popleft()
        if current == goal:
            path = [goal]
            while parent[path[-1]] is not None:
                path.append(parent[path[-1]])
            return GroundReachability(True, "connected_ground_graph_only",
                                      len(parent), tuple(reversed(path)))
        try:
            links = mesh.links[current]
        except (AttributeError, IndexError, KeyError, TypeError):
            return GroundReachability(False, "damaged_graph", len(parent))
        for neighbor, _, _ in links:
            if not isinstance(neighbor, int) or isinstance(neighbor, bool) or neighbor < 0:
                return GroundReachability(False, "damaged_graph", len(parent))
            if neighbor in parent or neighbor in blocked:
                continue
            try:
                if int(mesh.area[neighbor]) != 63:
                    continue
                mesh.links[neighbor]
            except (AttributeError, IndexError, KeyError, TypeError):
                return GroundReachability(False, "damaged_graph", len(parent))
            parent[neighbor] = current
            queue.append(neighbor)
    return GroundReachability(False, "disconnected_in_copied_ground_graph", len(parent))
