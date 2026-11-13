"""Synthetic-only click checks; no screen capture or game mouse input."""
from dataclasses import replace

import pytest

from eql_automation.assist import AssistAdvisor, AssistObservation, TargetRelation
from eql_automation.control import ControlPlane
from eql_automation.gem_bridge import (
    GemHitboxObservation, RecordingGemClickBridge,
)
from eql_automation.modes import Action, ActionKind, Mode
from eql_automation.prior_rotation_core import Catalog, Spell


def setup():
    catalog = Catalog([Spell(14, "Strike", 1, 1, 1000, 500, 0, 10, 0, 5)])
    control = ControlPlane()
    advisor = AssistAdvisor(catalog, character_name="SyntheticTester",
                            class_name="paladin", level=1,
                            known_spells={14}, control=control)
    control.switch(Mode.ASSIST)
    scene = AssistObservation(
        observed_at=10.0, character_name="SyntheticTester", class_name="Paladin",
        level=1, game_focused=True, chat_open=False,
        current_target_verified=True, target_token="synthetic-selection-1",
        hp=1.0, mana=1.0, memorized={3: 14},
        target_relation=TargetRelation.HOSTILE_NPC, target_is_undead=False)
    proposal = advisor.propose(scene, 10.0)
    assert proposal is not None and proposal.source.command == "/cast 3"
    scene = replace(scene, observed_at=10.1)
    hitbox = GemHitboxObservation(
        observed_at=10.1, window_size=(800, 600),
        layout_fingerprint="synthetic-active-layout", gem_slot=3,
        gem_spell_id=14, box=(40, 80, 80, 120), gem_visible=True,
        unobstructed=True, game_focused=True)
    return control, advisor, proposal, scene, hitbox


def send(control, advisor, proposal, scene, hitbox, events):
    bridge = RecordingGemClickBridge(control, events.append)
    return bridge.send(advisor, proposal, observe=lambda: (scene, hitbox),
                       clock=lambda: 10.1,
                       layout_fingerprint="synthetic-active-layout")


def test_one_spell_gem_click_avoids_chat_draft_and_movement():
    control, advisor, proposal, scene, hitbox = setup()
    events = []
    result = send(control, advisor, proposal, scene, hitbox, events)
    assert result.recorded_complete
    assert [(event.x, event.y, event.down) for event in events] == [
        (60, 100, True), (60, 100, False)]
    assert not control.command_draft_uncertain
    assert control.controller.mode == Mode.ASSIST


def test_unknown_gem_or_changed_target_fails_closed():
    for scene_change, hitbox_change in (
            ({"target_token": "synthetic-selection-2"}, {}),
            ({"chat_open": True}, {}),
            ({}, {"gem_spell_id": 15}),
            ({}, {"gem_visible": False}),
            ({}, {"unobstructed": False}),
            ({}, {"layout_fingerprint": "different-layout"}),
            ({}, {"box": (0, 0, 900, 20)}),
            ({}, {"gem_visible": "yes"}),
            ({}, {"gem_slot": True}),
            ({}, {"observed_at": 10.05}),
            ({}, {"observed_at": 10.0})):
        control, advisor, proposal, scene, hitbox = setup()
        events = []
        result = send(control, advisor, proposal,
                      replace(scene, **scene_change),
                      replace(hitbox, **hitbox_change), events)
        assert not result.recorded_complete
        assert events == []
        assert control.controller.mode == Mode.OFF


def test_off_during_click_releases_button_and_blocks_completion():
    control, advisor, proposal, scene, hitbox = setup()
    events = []
    def record(event):
        events.append(event)
        if event.down:
            control.switch(Mode.OFF)
    bridge = RecordingGemClickBridge(control, record)
    result = bridge.send(advisor, proposal,
                         observe=lambda: (scene, hitbox), clock=lambda: 10.1,
                         layout_fingerprint="synthetic-active-layout")
    assert not result.recorded_complete
    assert [event.down for event in events] == [True, False]
    assert control.controller.mode == Mode.OFF


def test_uncleared_chat_command_blocks_spell_gem_click():
    control, advisor, proposal, scene, hitbox = setup()
    control.set_command_draft_uncertain(True)
    events = []
    result = send(control, advisor, proposal, scene, hitbox, events)
    assert not result.recorded_complete and events == []


def test_ability_command_is_never_treated_as_a_gem_click():
    control, advisor, proposal, scene, hitbox = setup()
    forged = replace(proposal, queued=replace(
        proposal.queued, action=Action(ActionKind.ABILITY, "/doability Bash")))
    events = []
    result = send(control, advisor, forged, scene, hitbox, events)
    assert result.reason == "Only a spell-gem cast can be clicked"
    assert events == []


def test_gem_click_shared_channel_blocks_nested_cast():
    control, advisor, proposal, scene, hitbox = setup()
    nested = []
    events = []
    other = RecordingGemClickBridge(control, events.append)
    def record(event):
        events.append(event)
        if event.down:
            nested.append(other.send(
                advisor, proposal, observe=lambda: (scene, hitbox),
                clock=lambda: 10.1,
                layout_fingerprint="synthetic-active-layout"))
    bridge = RecordingGemClickBridge(control, record)
    assert bridge.send(advisor, proposal,
                       observe=lambda: (scene, hitbox), clock=lambda: 10.1,
                       layout_fingerprint="synthetic-active-layout").recorded_complete
    assert len(nested) == 1
    assert nested[0].reason == "Another assist input is in flight"
    assert [event.down for event in events] == [True, False]


def test_mouse_down_recorder_failure_attempts_release_and_latches_off():
    control, advisor, proposal, scene, hitbox = setup()
    events = []
    def record(event):
        events.append(event)
        if event.down:
            raise RuntimeError("mouse down failed")
    bridge = RecordingGemClickBridge(control, record)
    with pytest.raises(RuntimeError, match="mouse down failed"):
        bridge.send(advisor, proposal, observe=lambda: (scene, hitbox),
                    clock=lambda: 10.1,
                    layout_fingerprint="synthetic-active-layout")
    assert [event.down for event in events] == [True, False]
    assert control.controller.mode == Mode.OFF
