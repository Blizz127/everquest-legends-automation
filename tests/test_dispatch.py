"""Focused checks for the recording-only runtime dispatch boundary."""
from dataclasses import replace

from eql_automation.campaign import WorldSnapshot
from eql_automation.control import ControlPlane
from eql_automation.dispatch import DispatchObservation, DryRunDispatcher
from eql_automation.modes import Action, ActionKind, Mode
from eql_automation.sim import SimSink


def setup() -> tuple[DryRunDispatcher, ControlPlane, SimSink]:
    control = ControlPlane()
    sink = SimSink(control.controller)
    return DryRunDispatcher(control, sink.submit), control, sink


def observed(at: float = 10.0) -> DispatchObservation:
    return DispatchObservation(
        at, WorldSnapshot(level=1, hp=1.0, mana=1.0,
                          bag_fullness=0.0, target_present=True),
        "synthetic_zone", "camp", "synthetic-selection-1", True, False)


def test_dispatch_rechecks_newer_observation_and_original_mode_permit():
    dispatch, control, sink = setup()
    control.switch(Mode.FULL_AUTO)
    action = Action(ActionKind.CAST, "/cast 3")
    plan = dispatch.plan(action, observed(), 10.0)
    assert plan is not None
    assert not dispatch.dispatch(plan, observed(), 10.0)
    assert not dispatch.dispatch(plan, replace(observed(10.1), state=replace(
        observed().state, hp=0.2)), 10.1)
    assert not dispatch.dispatch(plan, replace(observed(10.1),
                                               target_token="synthetic-selection-2"), 10.1)
    assert dispatch.dispatch(plan, observed(10.1), 10.1)
    assert sink.accepted == [action]
    second = dispatch.plan(action, observed(11.0), 11.0)
    assert second is not None
    control.switch(Mode.OFF)
    assert not dispatch.dispatch(second, observed(11.1), 11.1)
    assert sink.accepted == [action]


def test_dispatch_refuses_unknown_stale_or_changed_scene_and_unsafe_loot():
    dispatch, control, sink = setup()
    control.switch(Mode.FULL_AUTO)
    action = Action(ActionKind.MOVE, "synthetic waypoint")
    assert dispatch.plan(action, replace(observed(), state=replace(
        observed().state, hp=None)), 10.0) is None
    assert dispatch.plan(action, replace(observed(), game_focused=False), 10.0) is None
    assert dispatch.plan(action, observed(), 12.0) is None
    plan = dispatch.plan(action, observed(), 10.0)
    assert plan is not None
    assert not dispatch.dispatch(plan, replace(observed(10.1), node="other"), 10.1)
    assert dispatch.plan(Action(ActionKind.LOOT, "synthetic corpse"),
                         observed(), 10.0) is None
    assert sink.accepted == []


def test_assist_dispatch_permits_only_fresh_rotation_intents():
    dispatch, control, sink = setup()
    control.switch(Mode.ASSIST)
    assert dispatch.plan(Action(ActionKind.MOVE, "synthetic waypoint"),
                         observed(), 10.0) is None
    assert dispatch.plan(Action(ActionKind.CAST, "/cast 3"),
                         replace(observed(), target_token=None), 10.0) is None
    plan = dispatch.plan(Action(ActionKind.CAST, "/cast 3"), observed(), 10.0)
    assert plan is not None and dispatch.dispatch(plan, observed(10.1), 10.1)
    assert len(sink.accepted) == 1
