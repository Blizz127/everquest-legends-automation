"""Bounded offline portal-fraction selection for a supplied ground corridor.

This selects sampled geometry candidates only. The caller must separately
bind the copied mesh hash, prove the zone transition and measure client motion.
No result from this module is an F11 movement permit.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import time

from .lateral_strip_audit import audit_segment_strip
from .strip_route_audit import audit_route_strips
from .turn_disk_audit import audit_turn_disk


@dataclass(frozen=True)
class PortalChoice:
    fraction: float
    xy: tuple[float, float]


@dataclass(frozen=True)
class PortalSelection:
    candidate: bool
    reason: str
    points: tuple[tuple[float, float], ...] = ()
    fractions: tuple[float, ...] = ()
    turn_checks: int = 0
    strip_checks: int = 0
    failed_polygon: int | None = None
    route_accepted: bool = False
    real_client_accepted: bool = False


DEFAULT_ALTERNATES = (0.55, 0.45, 0.60, 0.40, 0.65, 0.35,
                      0.70, 0.30, 0.75, 0.25, 0.80, 0.20)


def select_ground_portals(mesh, polygons: tuple[int, ...],
                          start_xy: tuple[float, float],
                          standoff_xy: tuple[float, float], *,
                          alternates: tuple[float, ...] = DEFAULT_ALTERNATES,
                          max_polygons: int = 220,
                          max_candidates_per_portal: int = 6,
                          max_turn_checks: int = 500,
                          max_strip_checks: int = 1000,
                          max_total_samples: int = 100000,
                          max_seconds: float = 180.0,
                          max_strip_repair_rounds: int = 8,
                          sample_spacing: float = 1.0,
                          half_width: float = 1.2,
                          max_segment_samples: int = 2048,
                          max_segment_seconds: float = 10.0) -> PortalSelection:
    """Find a sampled strip-connected portal sequence, then recheck it whole.

    Midpoints that pass the conservative disk start as a single candidate.
    When a polygon strip fails, adjacent portals get bounded alternative
    crossings and the layered search retries. All alternatives pass their
    turn disks before entering the search.
    """
    coords = (*start_xy, *standoff_xy) if (isinstance(start_xy, tuple) and
                                        isinstance(standoff_xy, tuple)) else ()
    if (not isinstance(polygons, tuple) or not polygons or
            any(not isinstance(p, int) or isinstance(p, bool) or p < 0
                for p in polygons) or
            not isinstance(max_polygons, int) or isinstance(max_polygons, bool) or
            not 1 <= len(polygons) <= max_polygons or
            len(coords) != 4 or any(not isinstance(v, (int, float)) or
                                    isinstance(v, bool) or not math.isfinite(v)
                                    for v in coords) or
            not isinstance(alternates, tuple) or len(alternates) > 32 or
            any(not isinstance(t, (int, float)) or isinstance(t, bool) or
                not math.isfinite(t) or not 0 < t < 1 for t in alternates) or
            any(not isinstance(n, int) or isinstance(n, bool) or n < 1
                for n in (max_candidates_per_portal, max_turn_checks,
                          max_strip_checks, max_total_samples, max_segment_samples)) or
            not isinstance(max_strip_repair_rounds, int) or
            isinstance(max_strip_repair_rounds, bool) or
            not 0 <= max_strip_repair_rounds <= 16 or
            any(not isinstance(n, (int, float)) or isinstance(n, bool) or
                not math.isfinite(n) or n <= 0
                for n in (max_seconds, sample_spacing, half_width,
                          max_segment_seconds))):
        return PortalSelection(False, "invalid_selection_limits")
    started = time.monotonic()
    turns = 0
    strips = 0
    samples = 0
    links = []
    for a, b in zip(polygons, polygons[1:]):
        try:
            matching = [(left, right) for neighbor, left, right
                        in mesh.links[a] if neighbor == b]
        except (AttributeError, IndexError, KeyError, TypeError):
            matching = []
        if len(matching) != 1:
            return PortalSelection(False, "missing_or_ambiguous_shared_portal",
                                   turn_checks=turns, failed_polygon=a)
        links.append(matching[0])

    layers: list[list[PortalChoice]] = []
    tried_by_portal: list[set[float]] = []
    for index, (a, b) in enumerate(zip(polygons, polygons[1:])):
        left, right = links[index]
        choices = []
        tried = set()
        for t in (0.5, *alternates):
            if t != 0.5 and choices and choices[0].fraction == 0.5:
                break  # A checked midpoint needs no speculative expansion.
            if t in tried:
                continue
            tried.add(t)
            if turns >= max_turn_checks or time.monotonic() - started >= max_seconds:
                return PortalSelection(False, "selection_work_budget_exceeded",
                                       turn_checks=turns, failed_polygon=a)
            x = float((1 - t) * left[0] + t * right[0])
            y = float((1 - t) * left[1] + t * right[1])
            if not math.isfinite(x) or not math.isfinite(y):
                return PortalSelection(False, "invalid_shared_portal_geometry",
                                       turn_checks=turns, failed_polygon=a)
            remaining = max_seconds - (time.monotonic() - started)
            turns += 1
            disk = audit_turn_disk(mesh, a, b, (x, y),
                                   max_seconds=min(remaining, 3.0))
            if disk.reason.endswith("budget_exceeded"):
                return PortalSelection(False, "selection_work_budget_exceeded",
                                       turn_checks=turns, failed_polygon=a)
            if disk.candidate:
                choices.append(PortalChoice(float(t), (x, y)))
                if len(choices) >= max_candidates_per_portal:
                    break
        if not choices:
            return PortalSelection(False, "no_sampled_turn_disk_candidate",
                                   turn_checks=turns, failed_polygon=a)
        layers.append(choices)
        tried_by_portal.append(tried)

    def expand_portal(index: int) -> tuple[bool, str | None]:
        nonlocal turns
        a, b = polygons[index:index + 2]
        left, right = links[index]
        added = False
        for t in alternates:
            if len(layers[index]) >= max_candidates_per_portal:
                break
            if t in tried_by_portal[index]:
                continue
            tried_by_portal[index].add(t)
            if turns >= max_turn_checks or time.monotonic() - started >= max_seconds:
                return added, "selection_work_budget_exceeded"
            x = float((1 - t) * left[0] + t * right[0])
            y = float((1 - t) * left[1] + t * right[1])
            if not math.isfinite(x) or not math.isfinite(y):
                return added, "invalid_shared_portal_geometry"
            remaining = max_seconds - (time.monotonic() - started)
            turns += 1
            disk = audit_turn_disk(mesh, a, b, (x, y),
                                   max_seconds=min(remaining, 3.0))
            if disk.reason.endswith("budget_exceeded"):
                return added, "selection_work_budget_exceeded"
            if disk.candidate:
                layers[index].append(PortalChoice(float(t), (x, y)))
                added = True
                break  # Retry the strip before spending budget on another choice.
        return added, None

    # Layered shortest-path search. A failed polygon expands only its two
    # bounding portals, then retries under the same global work budgets.
    best_path: tuple[PortalChoice, ...] | None = None
    for repair_round in range(max_strip_repair_rounds + 1):
        states: dict[PortalChoice, tuple[float, tuple[PortalChoice, ...]]] = {
            PortalChoice(0.0, start_xy): (0.0, ())}
        failed_index: int | None = None
        for index, poly in enumerate(polygons):
            exits = layers[index] if index < len(layers) else (
                PortalChoice(1.0, standoff_xy),)
            next_states = {}
            for entry, (cost, path) in states.items():
                for exit_choice in exits:
                    if strips >= max_strip_checks or samples >= max_total_samples or \
                            time.monotonic() - started >= max_seconds:
                        return PortalSelection(False, "selection_work_budget_exceeded",
                                               turn_checks=turns, strip_checks=strips,
                                               failed_polygon=poly)
                    remaining = max_seconds - (time.monotonic() - started)
                    strips += 1
                    result = audit_segment_strip(
                        mesh, poly, entry.xy, exit_choice.xy,
                        sample_spacing=sample_spacing, half_width=half_width,
                        max_samples=max_segment_samples,
                        max_seconds=min(remaining, max_segment_seconds))
                    samples += result.samples
                    if samples > max_total_samples or result.reason.endswith("budget_exceeded"):
                        return PortalSelection(False, "selection_work_budget_exceeded",
                                               turn_checks=turns, strip_checks=strips,
                                               failed_polygon=poly)
                    if not result.candidate:
                        continue
                    total = cost + math.dist(entry.xy, exit_choice.xy)
                    if not math.isfinite(total):
                        return PortalSelection(False, "invalid_strip_cost",
                                               turn_checks=turns, strip_checks=strips,
                                               failed_polygon=poly)
                    previous = next_states.get(exit_choice)
                    if previous is None or total < previous[0]:
                        next_states[exit_choice] = (total, path + (exit_choice,))
            if not next_states:
                failed_index = index
                break
            states = next_states
        if failed_index is None:
            best_path = min(states.values(), key=lambda item: item[0])[1]
            break
        if repair_round >= max_strip_repair_rounds:
            return PortalSelection(False, "strip_repair_round_budget_exceeded",
                                   turn_checks=turns, strip_checks=strips,
                                   failed_polygon=polygons[failed_index])
        expanded = False
        neighbors = (failed_index - 1, failed_index)
        if repair_round % 2:
            neighbors = neighbors[::-1]
        for portal_index in neighbors:
            if 0 <= portal_index < len(layers):
                added, stop_reason = expand_portal(portal_index)
                if stop_reason is not None:
                    return PortalSelection(False, stop_reason,
                                           turn_checks=turns, strip_checks=strips,
                                           failed_polygon=polygons[portal_index])
                if added:
                    expanded = True
                    break  # Try the newly checked choice before expanding again.
        if not expanded:
            return PortalSelection(False, "no_sampled_strip_through_polygon",
                                   turn_checks=turns, strip_checks=strips,
                                   failed_polygon=polygons[failed_index])
    if best_path is None:
        return PortalSelection(False, "selection_internal_path_missing",
                               turn_checks=turns, strip_checks=strips)
    points = (start_xy,) + tuple(choice.xy for choice in best_path)
    fractions = tuple(choice.fraction for choice in best_path[:-1])
    remaining = max_seconds - (time.monotonic() - started)
    remaining_samples = max_total_samples - samples
    if remaining <= 0 or remaining_samples < 1:
        return PortalSelection(False, "selection_work_budget_exceeded",
                               turn_checks=turns, strip_checks=strips)
    complete = audit_route_strips(
        mesh, polygons, points, max_segments=max_polygons,
        max_total_samples=remaining_samples, max_seconds=remaining,
        sample_spacing=sample_spacing, half_width=half_width,
        max_segment_samples=max_segment_samples,
        max_segment_seconds=max_segment_seconds)
    if time.monotonic() - started > max_seconds:
        return PortalSelection(False, "selection_work_budget_exceeded",
                               turn_checks=turns, strip_checks=strips)
    if not complete.candidate:
        return PortalSelection(False, "whole_route_" + complete.reason,
                               turn_checks=turns, strip_checks=strips,
                               failed_polygon=complete.failed_polygon)
    return PortalSelection(True, "sampled_ground_approach_candidate_only",
                           points, fractions, turns, strips)
