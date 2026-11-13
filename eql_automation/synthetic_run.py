"""Closed-loop synthetic 1–50 exercise. It never reads or controls the game.

Every coordinate, camp, spell, fight outcome and XP gain in this module is
fabricated test data. Reaching level 50 here is not real-client evidence.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
import json

from .campaign import Camp, CampaignPlanner, WorldSnapshot
from .control import ControlPlane
from .dispatch import DispatchObservation, DryRunDispatcher
from .modes import Action, ActionKind, Mode, action_from_prior_rotation
from .nav import NavGraph, Point
from .navigator import NavigationDirective, NavigationObservation, WorldNavigator
from .prior_rotation_core import Rotation, Spell
from .sim import SimSink
from .spells import SpellPlanner, SpellSpec
from .telemetry import RunState, StatusWriter
from .world_nav import WorldNav, ZoneTransition


RUN_STORE = Path.home() / ".local/share/eql-automation/runs"


class SyntheticEnvironment:
    def __init__(self) -> None:
        self.control = ControlPlane()
        self.controller = self.control.controller
        self.control.switch(Mode.FULL_AUTO)
        self.sink = SimSink(self.controller)
        self.dispatcher = DryRunDispatcher(self.control, self.sink.submit)
        self.clock_at = 0.0
        self.world = WorldNav()
        self.camps = []
        self.spell_specs = []
        for index in range(1, 6):
            zone = f"synthetic_zone_{index}"
            camp = f"synthetic_camp_{index}"
            graph = NavGraph()
            graph.add_point("entry", Point(0, 0))
            graph.add_point("camp", Point(10, 0))
            graph.connect("entry", "camp")
            self.world.add_zone(zone, graph)
            minimum = 1 + (index - 1) * 10
            self.camps.append(Camp(camp, minimum, min(50, index * 10), 100))
            self.spell_specs.append(SpellSpec(100 + index,
                                              f"Synthetic Spell {index}",
                                              {"synthetic_cleric": minimum}))
            if index > 1:
                previous_zone = f"synthetic_zone_{index - 1}"
                self.world.add_transition(ZoneTransition(
                    previous_zone, "camp", zone, "entry"))
        self.campaign = CampaignPlanner(self.camps)
        self.spells = SpellPlanner(self.spell_specs)
        self.vendor_stock = {spell.id for spell in self.spell_specs}
        self.owned_scrolls: set[int] = set()
        self.learned: set[int] = set()
        self.memorized: dict[int, int] = {}
        self.rotation = Rotation({"nuke": Spell(14, "Synthetic Strike", 1, 1,
                                                1000, 1000, 0, 10, 0, 0)}, level=1)
        self.level = 1
        self.xp = 0
        self.hp = 1.0
        self.mana = 1.0
        self.bag_fullness = 0.0
        self.zone = "synthetic_zone_1"
        self.node = "entry"
        self.camp: str | None = None
        self.target_hp = 0
        self.target_token: str | None = None
        self.target_epoch = 0
        self.loot_available = False
        self.dead = False
        self.disconnected = False
        self.death_injected = False
        self.disconnect_injected = False
        self.metrics = RunState(
            level=1, xp=0, blocker="Synthetic simulation only; private target not verified",
            next_step="Verify private server endpoint/client configuration before real-client validation")
        self.metrics.observe_xp(0, now=0.0)
        self.counts: dict[str, int] = defaultdict(int)
        self.trace: list[dict] = []

    def record(self, tick: int, event: str, **details) -> None:
        self.trace.append({"simulation_only": True, "tick": tick,
                           "synthetic_level": self.level, "event": event, **details})

    def snapshot(self) -> WorldSnapshot:
        return WorldSnapshot(level=self.level, hp=self.hp, mana=self.mana,
                             bag_fullness=self.bag_fullness, dead=self.dead,
                             disconnected=self.disconnected,
                             target_present=self.target_hp > 0,
                             camp=self.camp, loot_available=self.loot_available,
                             verified_reachable_camps=frozenset(camp.name for camp in self.camps))

    def dispatch_observation(self, observed_at: float) -> DispatchObservation:
        return DispatchObservation(observed_at, self.snapshot(), self.zone,
                                   self.node, self.target_token, True, False)

    def accept(self, action: Action, tick: int) -> None:
        at = max(float(tick), self.clock_at) + 0.001
        plan = self.dispatcher.plan(action, self.dispatch_observation(at), at)
        if (plan is None or not self.dispatcher.dispatch(
                plan, self.dispatch_observation(at + 0.000001),
                at + 0.000001)):
            raise RuntimeError(f"Synthetic dispatch denied {action.kind.value}")
        self.clock_at = at + 0.000001
        self.counts[action.kind.value] += 1

    def inject_scripted_faults(self, tick: int) -> None:
        if self.level >= 12 and not self.death_injected:
            self.death_injected = True
            self.dead = True
            self.target_hp = 0
            self.target_token = None
            self.loot_available = False
            self.metrics.observe_log("[synthetic] You have been slain by a synthetic opponent.\n")
            self.record(tick, "scripted_death")
        if self.level >= 23 and not self.disconnect_injected:
            self.disconnect_injected = True
            self.disconnected = True
            self.record(tick, "scripted_disconnect")

    def prepare_spells(self, tick: int) -> bool:
        tier = min(5, (self.level - 1) // 10 + 1)
        spell_id = 100 + tier
        tasks = self.spells.plan(
            class_names={"synthetic_cleric"}, level=self.level,
            desired_slots={3: spell_id}, learned=self.learned,
            owned_scrolls=self.owned_scrolls, vendor_stock=self.vendor_stock,
            memorized=self.memorized)
        if not tasks:
            return False
        for task in tasks:
            if task.operation == "unavailable":
                raise RuntimeError(f"Synthetic spell unavailable: {task.spell_name}")
            kind = {"buy": ActionKind.VENDOR, "scribe": ActionKind.SCRIBE,
                    "memorize": ActionKind.MEMORIZE}[task.operation]
            self.accept(Action(kind, f"synthetic {task.operation} {task.spell_id}"), tick)
            if task.operation == "buy":
                self.owned_scrolls.add(task.spell_id)
            elif task.operation == "scribe":
                self.learned.add(task.spell_id)
                self.owned_scrolls.discard(task.spell_id)
            else:
                self.memorized[task.slot] = task.spell_id
            self.counts[f"spell_{task.operation}"] += 1
            self.record(tick, "spell_task", operation=task.operation,
                        synthetic_spell_id=task.spell_id)
        return True

    def observe_route_start(self, zone: str, point: Point,
                            now: float) -> NavigationObservation:
        """Fabricated start; a future adapter must supply measured position."""
        return NavigationObservation(zone, point, now)

    def observe_route_arrival(self, directive: NavigationDirective,
                              now: float) -> NavigationObservation:
        """Fabricated arrival; a future adapter must supply measured position."""
        assert directive.zone is not None and directive.point is not None
        return NavigationObservation(directive.zone, directive.point, now)

    def confirm_route_observation(self, navigator: WorldNavigator,
                                  observation: NavigationObservation,
                                  requested_at: float) -> NavigationDirective:
        if (not isinstance(observation, NavigationObservation) or
                not isinstance(observation.now, (int, float)) or
                isinstance(observation.now, bool) or
                not isfinite(observation.now) or
                observation.now < requested_at):
            raise RuntimeError("Synthetic route observation is missing or stale")
        directive = navigator.observe(observation)
        self.clock_at = max(self.clock_at, observation.now)
        return directive

    def move_to_camp(self, tick: int, name: str) -> None:
        index = int(name.rsplit("_", 1)[1])
        destination = f"synthetic_zone_{index}"
        verified_moves = {
            (zone, source, edge.target)
            for zone, graph in self.world.zones.items()
            for source, edges in graph.edges.items() for edge in edges}
        verified_zones = {
            (item.source_zone, item.exit_node, item.destination_zone, item.entry_node)
            for item in self.world.transitions}
        navigator = WorldNavigator(
            self.world, start_zone=self.zone, start_node=self.node,
            goal_zone=destination, goal_node="camp", level=self.level,
            verified_moves=verified_moves, verified_zones=verified_zones,
            stall_timeout=0.3, zone_timeout=1.0, arrival_radius=0.25,
            min_progress=0.1)
        try:
            start = self.world.zones[self.zone].points[self.node]
            at = max(float(tick), self.clock_at) + 0.001
            observation = self.observe_route_start(self.zone, start, at)
            directive = self.confirm_route_observation(navigator, observation, at)
            if directive.kind != "PAUSE":
                self.record(tick, "navigation_start_observed",
                            synthetic_zone=self.zone, synthetic_node=self.node)
            issued_step = None
            for _ in range(64):
                if directive.kind == "ARRIVED":
                    break
                if directive.kind == "PAUSE":
                    raise RuntimeError(f"Synthetic navigation paused: {directive.reason}")
                if directive.kind not in {"MOVE_TOWARD", "WAIT_FOR_ZONE"}:
                    raise RuntimeError(f"Synthetic navigation cannot handle {directive.kind}")
                previous = (navigator.confirmed_zone, navigator.confirmed_node)
                kind = (ActionKind.MOVE if directive.kind == "MOVE_TOWARD"
                        else ActionKind.ZONE)
                step_key = (directive.kind, previous, directive.zone,
                            directive.node, navigator.replans)
                if step_key != issued_step:
                    self.accept(Action(kind, f"synthetic {self.zone}:{self.node} to "
                                             f"{directive.zone}:{directive.node}"), tick)
                    issued_step = step_key
                at = max(float(tick), self.clock_at) + 0.1
                observation = self.observe_route_arrival(directive, at)
                directive = self.confirm_route_observation(navigator, observation, at)
                confirmed = (navigator.confirmed_zone, navigator.confirmed_node)
                if confirmed != previous:
                    issued_step = None
                    self.zone, self.node = confirmed
                    self.record(tick, "route_step", kind=kind.value,
                                synthetic_zone=self.zone, synthetic_node=self.node,
                                arrival_observed=True)
            else:
                raise RuntimeError("Synthetic navigation step limit reached")
            if navigator.status != "ARRIVED":
                raise RuntimeError("Synthetic camp arrival was not observed")
        except Exception:
            self.control.emergency_stop("Synthetic navigation failed")
            raise
        self.camp = name
        self.metrics.camp = name
        self.metrics.zone = destination

    def apply_intent(self, tick: int, action: Action) -> None:
        kind = action.kind
        if kind == ActionKind.PAUSE:
            self.control.emergency_stop(action.detail)
            raise RuntimeError("Synthetic safety pause latched OFF")
        self.accept(action, tick)
        if kind == ActionKind.CAMP:
            self.move_to_camp(tick, action.detail)
        elif kind == ActionKind.TARGET:
            self.target_hp = 2
            self.target_epoch += 1
            self.target_token = f"synthetic-selection-{self.target_epoch}"
        elif kind == ActionKind.LOOT:
            self.loot_available = False
            self.bag_fullness = min(1.0, self.bag_fullness + 0.2)
        elif kind == ActionKind.VENDOR:
            self.bag_fullness = 0.0
        elif kind == ActionKind.REST:
            self.hp = 1.0
            self.mana = 1.0
        elif kind == ActionKind.RECOVER:
            self.dead = False
            self.hp = self.mana = 1.0
            self.camp = None
            self.zone, self.node = "synthetic_zone_1", "entry"
            self.target_token = None
        elif kind == ActionKind.LOGIN:
            self.disconnected = False
            self.camp = None
        else:
            raise RuntimeError(f"Unhandled synthetic intent {kind}")
        self.record(tick, "intent", kind=kind.value, detail=action.detail)

    def fight_step(self, tick: int) -> bool:
        self.rotation.level = self.level
        choice = self.rotation.choose(float(tick), self.hp, self.mana)
        if choice is None:
            return False
        action = action_from_prior_rotation(choice.role, choice.command)
        self.accept(action, tick)
        self.rotation.committed(choice, float(tick))
        self.target_hp -= 1
        if action.kind == ActionKind.CAST:
            self.mana = max(0.0, self.mana - 0.2)
        self.record(tick, "combat_rotation", role=choice.role, kind=action.kind.value)
        if self.target_hp <= 0:
            self.target_hp = 0
            self.target_token = None
            self.loot_available = True
            self.hp = max(0.1, self.hp - 0.2)
            self.xp += 20
            self.metrics.observe_xp(self.xp, now=float(tick))
            new_level = min(50, 1 + self.xp // 100)
            if new_level > self.level:
                self.level = new_level
                self.metrics.observe_log(
                    f"[synthetic] You have gained a level! Welcome to level {new_level}!\n")
                if self.metrics.level != self.level:
                    raise AssertionError("Synthetic level and log-state level diverged")
                self.record(tick, "level_up")
            self.counts["synthetic_fights"] += 1
            self.record(tick, "synthetic_fight_finished", synthetic_xp=self.xp)
        return True

    def step(self, tick: int) -> bool:
        self.inject_scripted_faults(tick)
        decision = self.campaign.decide(self.snapshot())
        if decision and decision.kind in {ActionKind.LOGIN, ActionKind.RECOVER,
                                           ActionKind.PAUSE, ActionKind.REST}:
            self.apply_intent(tick, decision)
            return True
        if self.prepare_spells(tick):
            return True
        if decision is not None:
            self.apply_intent(tick, decision)
            return True
        if self.target_hp > 0:
            return self.fight_step(tick)
        return False


def run_synthetic_1_50(output_dir: Path | None = None,
                       max_ticks: int = 20000) -> dict:
    env = SyntheticEnvironment()
    idle_ticks = 0
    for tick in range(1, max_ticks + 1):
        if env.level >= 50:
            break
        progressed = env.step(tick)
        idle_ticks = 0 if progressed else idle_ticks + 1
        if idle_ticks >= 100:
            raise RuntimeError(f"Synthetic planner stalled at level {env.level}")
    if env.level != 50:
        raise RuntimeError(f"Synthetic level 50 not reached in {max_ticks} ticks")
    required = ("camp", "move", "zone", "target", "loot", "vendor",
                "rest", "recover", "login", "spell_buy", "spell_scribe",
                "spell_memorize", "cast", "synthetic_fights")
    missing = [name for name in required if env.counts[name] == 0]
    if missing:
        raise AssertionError(f"Synthetic path skipped capabilities: {missing}")
    env.target_hp = 2
    env.target_epoch += 1
    env.target_token = f"synthetic-selection-{env.target_epoch}"
    env.control.switch(Mode.ASSIST)
    observed_at = float(tick) + 1
    observed = env.dispatch_observation(observed_at)
    forbidden_in_assist = (ActionKind.MOVE, ActionKind.ZONE, ActionKind.TARGET,
                           ActionKind.LOOT, ActionKind.VENDOR, ActionKind.CAMP,
                           ActionKind.REST, ActionKind.LOGIN, ActionKind.RECOVER,
                           ActionKind.SCRIBE, ActionKind.MEMORIZE)
    assist_denied_nonrotation = all(
        env.dispatcher.plan(Action(kind, "synthetic mode probe"),
                            observed, observed_at) is None
        for kind in forbidden_in_assist)
    assist_plan = env.dispatcher.plan(
        Action(ActionKind.CAST, "/cast 3"), observed, observed_at)
    assist_cast_allowed = (assist_plan is not None and env.dispatcher.dispatch(
        assist_plan, env.dispatch_observation(observed_at + 0.1), observed_at + 0.1))
    env.control.switch(Mode.OFF)
    off_cancels_assist = (assist_plan is not None and not env.dispatcher.dispatch(
        assist_plan, env.dispatch_observation(observed_at + 0.2), observed_at + 0.2))
    if not (assist_denied_nonrotation and assist_cast_allowed and off_cancels_assist):
        raise AssertionError("Synthetic assist/off mode safety check failed")
    result = {
        "simulation_only": True,
        "real_client_level_verified": False,
        "synthetic_level_reached": env.level,
        "synthetic_xp": env.xp,
        "synthetic_virtual_xp_per_hour": env.metrics.xp_per_hour,
        "counts": dict(sorted(env.counts.items())),
        "trace_events": len(env.trace),
        "max_ticks": max_ticks,
        "assist_denied_nonrotation": assist_denied_nonrotation,
        "assist_cast_allowed": assist_cast_allowed,
        "off_cancels_assist": off_cancels_assist,
    }
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        trace_path = output_dir / "trace-synthetic.jsonl"
        trace_path.write_text("".join(json.dumps(event, sort_keys=True) + "\n"
                                      for event in env.trace))
        StatusWriter(output_dir / "STATUS-synthetic.md").maybe_write(
            env.metrics, now=float(tick), force=True)
        (output_dir / "summary-synthetic.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n")
        result["output_dir"] = str(output_dir)
    return result


def default_output_dir() -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return RUN_STORE / f"synthetic-1-50-{timestamp}"
