"""Generic offline navigation graph and progress monitor.

All coordinates supplied to this module must come from an authorized source.
This repository ships only synthetic demonstration coordinates.
"""
from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from math import dist
from pathlib import Path
import json


MAP_STORE = Path.home() / ".local/share/eql-automation/map-store"


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    z: float = 0.0


@dataclass(frozen=True)
class Edge:
    target: str
    length: float
    aggro: float = 0.0
    water: bool = False


class RouteNotFound(ValueError):
    pass


class NavGraph:
    def __init__(self) -> None:
        self.points: dict[str, Point] = {}
        self.edges: dict[str, list[Edge]] = {}

    def add_point(self, name: str, point: Point) -> None:
        if not name:
            raise ValueError("Point name is empty")
        self.points[name] = point
        self.edges.setdefault(name, [])

    def connect(self, left: str, right: str, *, aggro: float = 0.0,
                water: bool = False) -> None:
        if left not in self.points or right not in self.points:
            raise KeyError("Both endpoints must exist")
        if left == right or aggro < 0:
            raise ValueError("Invalid edge")
        length = dist(vars(self.points[left]).values(), vars(self.points[right]).values())
        if length <= 0:
            raise ValueError("Edge length must be positive")
        self.edges[left].append(Edge(right, length, aggro, water))
        self.edges[right].append(Edge(left, length, aggro, water))

    def route(self, start: str, goal: str, *, avoid_water: bool = True,
              max_aggro: float = 0.0, blocked: set[frozenset[str]] | None = None,
              risk_weight: float = 10.0) -> list[str]:
        if start not in self.points or goal not in self.points:
            raise KeyError("Unknown route endpoint")
        blocked = blocked or set()
        best = {start: 0.0}
        previous: dict[str, str] = {}
        todo = [(0.0, start)]
        while todo:
            cost, name = heappop(todo)
            if cost != best.get(name):
                continue
            if name == goal:
                path = [goal]
                while path[-1] != start:
                    path.append(previous[path[-1]])
                return list(reversed(path))
            for edge in self.edges.get(name, []):
                if edge.water and avoid_water or edge.aggro > max_aggro:
                    continue
                if frozenset((name, edge.target)) in blocked:
                    continue
                new_cost = cost + edge.length + edge.aggro * risk_weight
                if new_cost < best.get(edge.target, float("inf")):
                    best[edge.target] = new_cost
                    previous[edge.target] = name
                    heappush(todo, (new_cost, edge.target))
        raise RouteNotFound(f"No route from {start} to {goal} under current constraints")

    def save(self, name: str, store: Path = MAP_STORE) -> Path:
        if not name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for c in name):
            raise ValueError("Unsafe graph name")
        store.mkdir(parents=True, exist_ok=True)
        path = store / f"{name}.json"
        payload = {
            "points": {key: vars(value) for key, value in self.points.items()},
            "edges": {key: [vars(edge) for edge in values] for key, values in self.edges.items()},
        }
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2) + "\n")
        temporary.replace(path)
        return path

    @classmethod
    def load(cls, path: Path) -> "NavGraph":
        raw = json.loads(path.read_text())
        graph = cls()
        for key, point in raw["points"].items():
            graph.add_point(key, Point(**point))
        graph.edges = {key: [Edge(**edge) for edge in values]
                       for key, values in raw["edges"].items()}
        for key, values in graph.edges.items():
            if key not in graph.points or any(edge.target not in graph.points for edge in values):
                raise ValueError("Graph has an unknown endpoint")
        return graph


class ProgressMonitor:
    def __init__(self, goal: Point, timeout: float = 8.0, min_progress: float = 1.0) -> None:
        self.goal = goal
        self.timeout = timeout
        self.min_progress = min_progress
        self.best_distance = float("inf")
        self.last_progress_at: float | None = None

    def observe(self, point: Point, now: float) -> bool:
        """Return True when progress toward the current waypoint has stalled."""

        distance = dist(vars(point).values(), vars(self.goal).values())
        if self.last_progress_at is None or distance <= self.best_distance - self.min_progress:
            self.best_distance = distance
            self.last_progress_at = now
            return False
        return distance > self.min_progress and now - self.last_progress_at >= self.timeout
