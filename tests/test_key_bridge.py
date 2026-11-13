"""Focused recording-only checks for per-key assist cancellation."""
from dataclasses import replace
from threading import Event, Thread

import pytest

from eql_automation.assist import AssistAdvisor, AssistObservation, TargetRelation
from eql_automation.control import ControlPlane
from eql_automation.key_bridge import (
    RecordingAssistKeyBridge, assist_command_keys,
)
from eql_automation.modes import Action, ActionKind, Mode, Permit
from eql_automation.prior_rotation_core import Catalog, Spell


def setup():
    catalog = Catalog([Spell(14, "Strike", 1, 1, 1000, 500, 0, 10, 0, 5)])
    control = ControlPlane()
    advisor = AssistAdvisor(catalog, character_name="SyntheticTester",
                            class_name="paladin", level=1,
                            known_spells={14}, control=control)
    control.switch(Mode.ASSIST)
    observation = AssistObservation(
        observed_at=10.0, character_name="SyntheticTester",
        class_name="Paladin", level=1, game_focused=True,
        chat_open=False, current_target_verified=True,
        target_token="synthetic-target-selection-1",
        hp=1.0, mana=1.0, memorized={3: 14},
        target_relation=TargetRelation.HOSTILE_NPC,
        target_is_undead=False)
    proposal = advisor.propose(observation, 10.0)
    assert proposal is not None and proposal.queued.action.detail == "/cast 3"
    return control, advisor, observation, proposal


def observations(base, *, swap_after=None, stale_after=None):
    counter = 0
    last = 10.0
    def observe():
        nonlocal counter, last
        counter += 1
        if stale_after is None or counter < stale_after:
            last = 10.0 + counter * 0.1
        result = replace(base, observed_at=last)
        if swap_after is not None and counter >= swap_after:
            result = replace(result, target_token="synthetic-target-selection-2")
        return result
    def clock():
        return last
    return observe, clock


def test_recorded_assist_command_rechecks_every_key_without_game_input():
    control, advisor, base, proposal = setup()
    events = []
    bridge = RecordingAssistKeyBridge(control, events.append)
    observe, clock = observations(base)
    result = bridge.send(advisor, proposal, observe=observe, clock=clock)
    assert result.recorded_complete and not result.draft_uncertain
    assert result.key_down_count == len("/cast 3") + 1
    assert [event.key for event in events if event.down] == list("/cast 3") + ["ENTER"]
    assert all(events[index].down and not events[index + 1].down and
               events[index].key == events[index + 1].key
               for index in range(0, len(events), 2))
    assert control.controller.mode == Mode.ASSIST


def test_off_during_key_releases_it_and_blocks_uncleared_draft():
    control, advisor, base, proposal = setup()
    events = []
    def record(event):
        events.append(event)
        if event.down and event.key == "/":
            control.switch(Mode.OFF)
    bridge = RecordingAssistKeyBridge(control, record)
    observe, clock = observations(base)
    result = bridge.send(advisor, proposal, observe=observe, clock=clock)
    assert not result.recorded_complete and result.draft_uncertain
    assert [(event.key, event.down) for event in events] == [("/", True), ("/", False)]
    control.switch(Mode.ASSIST)
    replacement_bridge = RecordingAssistKeyBridge(control, record)
    assert replacement_bridge.send(advisor, proposal, observe=observe,
                                   clock=clock).reason == "Previous command draft is uncleared"
    assert len(events) == 2
    assert not bridge.confirm_draft_cleared(replace(base, observed_at=20.0),
                                            20.0, explicit_clear=True)
    control.switch(Mode.OFF)
    assert not bridge.confirm_draft_cleared(replace(base, observed_at=20.0,
                                                    chat_open=True),
                                            20.0, explicit_clear=True)
    assert bridge.confirm_draft_cleared(replace(base, observed_at=20.0),
                                        20.0, explicit_clear=True)
    assert not bridge.draft_uncertain and not replacement_bridge.draft_uncertain


@pytest.mark.parametrize("change", ["target", "stale"])
def test_changed_or_stale_target_observation_stops_before_next_key(change):
    control, advisor, base, proposal = setup()
    events = []
    bridge = RecordingAssistKeyBridge(control, events.append)
    observe, clock = observations(base, swap_after=2 if change == "target" else None,
                                  stale_after=2 if change == "stale" else None)
    result = bridge.send(advisor, proposal, observe=observe, clock=clock)
    assert not result.recorded_complete and result.draft_uncertain
    assert result.key_down_count == 1
    assert control.controller.mode == Mode.OFF and control.safety_latched
    assert [(event.key, event.down) for event in events] == [("/", True), ("/", False)]


def test_chat_open_after_slash_stops_and_keeps_draft_uncertain():
    control, advisor, base, proposal = setup()
    events = []
    bridge = RecordingAssistKeyBridge(control, events.append)
    observe, clock = observations(base)
    calls = 0
    def chat_observe():
        nonlocal calls
        calls += 1
        result = observe()
        return replace(result, chat_open=calls > 1)
    result = bridge.send(advisor, proposal, observe=chat_observe, clock=clock)
    assert result.key_down_count == 1
    assert result.draft_uncertain
    assert control.controller.mode == Mode.OFF
    assert [(event.key, event.down) for event in events] == [("/", True), ("/", False)]


def test_key_allowlist_excludes_prior_attack_and_nonrotation_actions():
    for action in (Action(ActionKind.ATTACK, "/attack on"),
                   Action(ActionKind.MOVE, "north"),
                   Action(ActionKind.TARGET, "/target enemy"),
                   Action(ActionKind.CAST, "/cast 3; /target enemy"),
                   Action(ActionKind.MEMORIZE, "/memspellslot 3 14")):
        with pytest.raises(ValueError, match="assist key allowlist"):
            assist_command_keys(action)


def test_foreign_permit_or_advisor_cannot_authorize_key_sequence():
    control, advisor, base, proposal = setup()
    permit = control.controller.permit()
    forged = Permit(permit.mode, permit.generation, Event())
    assert not control.controller.allows(forged, proposal.queued.action)
    other_control, other_advisor, _, other_proposal = setup()
    events = []
    bridge = RecordingAssistKeyBridge(control, events.append)
    observe, clock = observations(base)
    with pytest.raises(ValueError, match="share one control plane"):
        bridge.send(other_advisor, other_proposal, observe=observe, clock=clock)
    assert events == [] and other_control.controller.mode == Mode.ASSIST


def test_second_send_cannot_interleave_with_unfinished_first_command():
    control, advisor, base, proposal = setup()
    events = []
    nested = []
    observe, clock = observations(base)
    def record(event):
        events.append(event)
        if event.down and event.key == "/":
            nested.append(bridge.send(advisor, proposal, observe=observe,
                                      clock=clock))
    bridge = RecordingAssistKeyBridge(control, record)
    result = bridge.send(advisor, proposal, observe=observe, clock=clock)
    assert result.recorded_complete
    assert len(nested) == 1
    assert nested[0].reason == "Another assist command is in flight"
    assert [event.key for event in events if event.down] == list("/cast 3") + ["ENTER"]


def test_two_bridges_share_one_key_channel():
    control, advisor, base, proposal = setup()
    events = []
    nested = []
    observe, clock = observations(base)
    other = RecordingAssistKeyBridge(control, events.append)
    def record(event):
        events.append(event)
        if event.down and event.key == "/":
            nested.append(other.send(advisor, proposal, observe=observe,
                                     clock=clock))
    bridge = RecordingAssistKeyBridge(control, record)
    assert bridge.send(advisor, proposal, observe=observe,
                       clock=clock).recorded_complete
    assert len(nested) == 1
    assert nested[0].reason == "Another assist command is in flight"
    assert [event.key for event in events if event.down] == list("/cast 3") + ["ENTER"]


def test_off_request_cancels_permit_before_stalled_recorder_returns():
    control, advisor, base, proposal = setup()
    entered, release = Event(), Event()
    events = []
    result = []
    observe, clock = observations(base)
    def record(event):
        events.append(event)
        if event.down:
            entered.set()
            release.wait(timeout=2)
    bridge = RecordingAssistKeyBridge(control, record)
    sender = Thread(target=lambda: result.append(
        bridge.send(advisor, proposal, observe=observe, clock=clock)))
    sender.start()
    assert entered.wait(timeout=1)
    stopper = Thread(target=lambda: control.switch(Mode.OFF))
    stopper.start()
    try:
        assert proposal.queued.permit.cancelled.wait(timeout=1)
    finally:
        release.set()
        sender.join(timeout=2)
        stopper.join(timeout=2)
    assert not sender.is_alive() and not stopper.is_alive()
    assert control.controller.mode == Mode.OFF
    assert result and not result[0].recorded_complete
    assert [(event.key, event.down) for event in events] == [("/", True), ("/", False)]


def test_down_failure_attempts_release_even_when_indicator_publish_fails():
    control, advisor, base, proposal = setup()
    events = []
    def record(event):
        events.append(event)
        if event.down:
            raise RuntimeError("down recorder failed")
    bridge = RecordingAssistKeyBridge(control, record)
    control.notify = lambda _indicator: (_ for _ in ()).throw(
        RuntimeError("indicator failed"))
    observe, clock = observations(base)
    with pytest.raises(RuntimeError, match="down recorder failed"):
        bridge.send(advisor, proposal, observe=observe, clock=clock)
    assert [(event.key, event.down) for event in events] == [("/", True), ("/", False)]
    assert control.controller.mode == Mode.OFF
    assert bridge.draft_uncertain
