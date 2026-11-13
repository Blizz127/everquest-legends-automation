"""Offline route planning across supplied zone graphs and zone lines.

No zone or transition data is bundled. A future authorized adapter must supply
verified client observations before any plan can represent a real route.
"""
from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from math import isfinite

from .nav import NavGraph, RouteNotFound


@dataclass(frozen=True)
class ZoneTransition:
    source_zone: str
    exit_node: str
    destination_zone: str
    entry_node: str
    cost: float = 1.0
    risk: float = 0.0
    min_level: int = 1
    max_level: int = 50


@dataclass(frozen=True)
class RouteStep:
    kind: str  # "move" within a zone or "zone" through a verified zone line
    from_zone: str
    from_node: str
    to_zone: str
    to_node: str


class WorldNav:
    def __init__(self) -> None:
        self.zones: dict[str, NavGraph] = {}
        self.transitions: list[ZoneTransition] = []

    def add_zone(self, name: str, graph: NavGraph) -> None:
        if not name or name in self.zones:
            raise ValueError("Zone name is empty or duplicated")
        self.zones[name] = graph

    def add_transition(self, transition: ZoneTransition) -> None:
        source = self.zones.get(transition.source_zone)
        target = self.zones.get(transition.destination_zone)
        if source is None or target is None:
            raise KeyError("Both zone graphs must exist")
        if transition.exit_node not in source.points or transition.entry_node not in target.points:
            raise KeyError("Zone line endpoint is absent from its graph")
        if (not isfinite(transition.cost) or transition.cost <= 0 or
                not isfinite(transition.risk) or transition.risk < 0):
            raise ValueError("Invalid zone line cost or risk")
        if not 1 <= transition.min_level <= transition.max_level <= 50:
            raise ValueError("Invalid level range")
        self.transitions.append(transition)

    def route(self, start_zone: str, start_node: str,
              goal_zone: str, goal_node: str, *, level: int,
              avoid_water: bool = True, max_aggro: float = 0.0,
              blocked_edges: set[tuple[str, str, str]] | None = None,
              risk_weight: float = 10.0) -> list[RouteStep]:
        if not 1 <= level <= 50:
            raise ValueError("Level must be 1–50")
        if not isfinite(max_aggro) or max_aggro < 0 or not isfinite(risk_weight) or risk_weight < 0:
            raise ValueError("Risk constraints must be finite and nonnegative")
        for zone, node in ((start_zone, start_node), (goal_zone, goal_node)):
            if zone not in self.zones or node not in self.zones[zone].points:
                raise KeyError(f"Unknown route endpoint: {zone}:{node}")
        start, goal = (start_zone, start_node), (goal_zone, goal_node)
        transitions_by_source: dict[tuple[str, str], list[ZoneTransition]] = {}
        for transition in self.transitions:
            transitions_by_source.setdefault((transition.source_zone,
                                               transition.exit_node), []).append(transition)
        blocked_edges = blocked_edges or set()
        best = {start: 0.0}
        previous: dict[tuple[str, str], tuple[tuple[str, str], RouteStep]] = {}
        todo = [(0.0, start)]
        while todo:
            cost, state = heappop(todo)
            if cost != best.get(state):
                continue
            if state == goal:
                result = []
                while state != start:
                    state, step = previous[state]
                    result.append(step)
                return list(reversed(result))
            zone, node = state
            for edge in self.zones[zone].edges.get(node, []):
                if (edge.water and avoid_water) or edge.aggro > max_aggro:
                    continue
                if (zone, node, edge.target) in blocked_edges:
                    continue
                next_state = (zone, edge.target)
                next_cost = cost + edge.length + edge.aggro * risk_weight
                if next_cost < best.get(next_state, float("inf")):
                    best[next_state] = next_cost
                    previous[next_state] = (state, RouteStep("move", zone, node, zone, edge.target))
                    heappush(todo, (next_cost, next_state))
            for transition in transitions_by_source.get(state, []):
                if not transition.min_level <= level <= transition.max_level:
                    continue
                if transition.risk > max_aggro:
                    continue
                next_state = (transition.destination_zone, transition.entry_node)
                next_cost = cost + transition.cost + transition.risk * risk_weight
                if next_cost < best.get(next_state, float("inf")):
                    best[next_state] = next_cost
                    previous[next_state] = (state, RouteStep(
                        "zone", zone, node, transition.destination_zone, transition.entry_node))
                    heappush(todo, (next_cost, next_state))
        raise RouteNotFound(f"No world route from {start_zone}:{start_node} to {goal_zone}:{goal_node}")
