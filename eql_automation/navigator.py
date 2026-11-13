"""Pure waypoint controller over explicitly confirmed movement edges.

It emits intents only. Client map drawing lines and POI labels are never used
as verified movement or zone transitions by this controller.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import dist, isfinite

from .nav import Point, ProgressMonitor, RouteNotFound
from .world_nav import RouteStep, WorldNav


MoveKey = tuple[str, str, str]
ZoneKey = tuple[str, str, str, str]


@dataclass(frozen=True)
class NavigationObservation:
    zone: str
    point: Point
    now: float


@dataclass(frozen=True)
class NavigationDirective:
    kind: str  # MOVE_TOWARD, WAIT_FOR_ZONE, ARRIVED, PAUSE
    zone: str | None = None
    node: str | None = None
    point: Point | None = None
    reason: str = ""


class WorldNavigator:
    def __init__(self, world: WorldNav, *, start_zone: str, start_node: str,
                 goal_zone: str, goal_node: str, level: int,
                 verified_moves: set[MoveKey], verified_zones: set[ZoneKey],
                 avoid_water: bool = True, max_aggro: float = 0.0,
                 stall_timeout: float = 8.0, zone_timeout: float = 15.0,
                 arrival_radius: float = 0.5, min_progress: float = 0.1,
                 max_replans: int = 2) -> None:
        if (not isfinite(stall_timeout) or stall_timeout <= 0 or
                not isfinite(zone_timeout) or zone_timeout <= 0 or
                not isfinite(arrival_radius) or arrival_radius <= 0 or
                not isfinite(min_progress) or min_progress <= 0 or
                max_replans < 0):
            raise ValueError("Invalid navigation safety limits")
        all_moves = {(zone, source, edge.target)
                     for zone, graph in world.zones.items()
                     for source, edges in graph.edges.items() for edge in edges}
        all_zones = {(item.source_zone, item.exit_node,
                      item.destination_zone, item.entry_node)
                     for item in world.transitions}
        if not verified_moves <= all_moves or not verified_zones <= all_zones:
            raise ValueError("Verified traversal reference is absent from the graph")
        self.world = world
        self.all_moves = all_moves
        self.all_zones = all_zones
        self.verified_moves = set(verified_moves)
        self.verified_zones = set(verified_zones)
        self.goal_zone, self.goal_node = goal_zone, goal_node
        self.confirmed_zone, self.confirmed_node = start_zone, start_node
        self.level = level
        self.avoid_water, self.max_aggro = avoid_water, max_aggro
        self.stall_timeout, self.zone_timeout = stall_timeout, zone_timeout
        self.arrival_radius, self.min_progress = arrival_radius, min_progress
        self.max_replans = max_replans
        self.replans = 0
        self.quarantined: set[MoveKey] = set()
        self.steps: list[RouteStep] = []
        self.monitor: ProgressMonitor | None = None
        self.step_started_at: float | None = None
        self.last_observed_at: float | None = None
        self.status = "ACTIVE"
        self.reason = ""
        self._plan()
        self.awaiting_start = self.status != "PAUSED"

    def _pause(self, reason: str) -> NavigationDirective:
        self.status = "PAUSED"
        self.reason = reason
        self.steps.clear()
        self.monitor = None
        self.awaiting_start = False
        return self.directive()

    def _plan(self) -> None:
        blocked_moves = (self.all_moves - self.verified_moves) | self.quarantined
        blocked_zones = self.all_zones - self.verified_zones
        try:
            self.steps = self.world.route(
                self.confirmed_zone, self.confirmed_node,
                self.goal_zone, self.goal_node, level=self.level,
                avoid_water=self.avoid_water, max_aggro=self.max_aggro,
                blocked_edges=blocked_moves,
                blocked_transitions=blocked_zones)
        except (RouteNotFound, KeyError) as exc:
            self._pause(f"No verified route: {exc}")
            return
        if not self.steps:
            self.status = "ARRIVED"
            self.monitor = None
        else:
            self.status = "ACTIVE"
            self._reset_step()

    def _reset_step(self) -> None:
        self.step_started_at = None
        step = self.steps[0]
        self.monitor = (ProgressMonitor(
            self.world.zones[step.to_zone].points[step.to_node],
            timeout=self.stall_timeout, min_progress=self.min_progress)
            if step.kind == "move" else None)

    def directive(self) -> NavigationDirective:
        if self.status == "PAUSED":
            return NavigationDirective("PAUSE", reason=self.reason)
        if self.awaiting_start:
            return NavigationDirective(
                "WAIT_FOR_START", self.confirmed_zone, self.confirmed_node,
                self.world.zones[self.confirmed_zone].points[self.confirmed_node])
        if self.status == "ARRIVED":
            return NavigationDirective("ARRIVED", self.goal_zone, self.goal_node,
                                       self.world.zones[self.goal_zone].points[self.goal_node])
        step = self.steps[0]
        return NavigationDirective(
            "MOVE_TOWARD" if step.kind == "move" else "WAIT_FOR_ZONE",
            step.to_zone, step.to_node,
            self.world.zones[step.to_zone].points[step.to_node])

    def _advance(self, now: float) -> NavigationDirective:
        step = self.steps.pop(0)
        self.confirmed_zone, self.confirmed_node = step.to_zone, step.to_node
        if not self.steps:
            self.status = "ARRIVED"
            self.monitor = None
        else:
            self._reset_step()
            if self.steps[0].kind == "zone":
                self.step_started_at = now
        return self.directive()

    def observe(self, observation: NavigationObservation) -> NavigationDirective:
        if self.status == "PAUSED":
            return self.directive()
        point = observation.point
        if (not isfinite(observation.now) or
                not all(isfinite(value) for value in (point.x, point.y, point.z)) or
                (self.last_observed_at is not None and
                 observation.now < self.last_observed_at)):
            return self._pause("Invalid or nonmonotonic position observation")
        self.last_observed_at = observation.now
        if self.awaiting_start:
            source = self.world.zones[self.confirmed_zone].points[self.confirmed_node]
            source_distance = dist((point.x, point.y, point.z),
                                   (source.x, source.y, source.z))
            if (observation.zone != self.confirmed_zone or
                    source_distance > self.arrival_radius):
                return self._pause("Start position is not confirmed")
            self.awaiting_start = False
            if self.status == "ACTIVE":
                if self.steps[0].kind == "move":
                    assert self.monitor is not None
                    self.monitor.observe(point, observation.now)
                else:
                    self.step_started_at = observation.now
            return self.directive()
        if self.status != "ACTIVE":
            return self.directive()
        step = self.steps[0]
        target = self.world.zones[step.to_zone].points[step.to_node]
        target_distance = dist((point.x, point.y, point.z),
                               (target.x, target.y, target.z))
        if step.kind == "zone":
            if observation.zone == step.to_zone:
                if target_distance <= self.arrival_radius:
                    return self._advance(observation.now)
                return self._pause("Zone changed but entry position is unverified")
            if observation.zone != step.from_zone:
                return self._pause("Unexpected zone during transition")
            source = self.world.zones[step.from_zone].points[step.from_node]
            if dist((point.x, point.y, point.z),
                    (source.x, source.y, source.z)) > self.arrival_radius:
                return self._pause("Moved away from confirmed zone exit")
            if self.step_started_at is None:
                self.step_started_at = observation.now
            elif observation.now - self.step_started_at >= self.zone_timeout:
                return self._pause("Zone transition timed out")
            return self.directive()
        if observation.zone != step.from_zone:
            return self._pause("Unexpected zone during movement")
        if target_distance <= self.arrival_radius:
            return self._advance(observation.now)
        assert self.monitor is not None
        if not self.monitor.observe(point, observation.now):
            return self.directive()
        source = self.world.zones[step.from_zone].points[step.from_node]
        source_distance = dist((point.x, point.y, point.z),
                               (source.x, source.y, source.z))
        if source_distance > self.arrival_radius:
            return self._pause("Stalled mid-edge; no confirmed replan anchor")
        self.replans += 1
        if self.replans > self.max_replans:
            return self._pause("Stuck retry budget exhausted")
        self.quarantined.add((step.from_zone, step.from_node, step.to_node))
        self.quarantined.add((step.from_zone, step.to_node, step.from_node))
        self._plan()
        return self.directive()
