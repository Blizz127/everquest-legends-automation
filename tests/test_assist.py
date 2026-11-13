from dataclasses import replace

from eql_automation.assist import AssistAdvisor, AssistObservation
from eql_automation.control import ControlPlane
from eql_automation.modes import ActionKind, Mode
from eql_automation.prior_rotation_core import Catalog, Spell
from eql_automation.sim import run_assist_demo


def advisor() -> tuple[AssistAdvisor, ControlPlane]:
    catalog = Catalog([
        Spell(14, "Strike", 1, 1, 1000, 500, 0, 10, 0, 0),
        Spell(200, "Minor Healing", 1, 1, 1500, 500, 0, 10, 0, 0),
        Spell(210, "Yaulp", 1, 9, 1000, 500, 0, 1, 0, 0),
    ])
    control = ControlPlane()
    return AssistAdvisor(catalog, character_name="SyntheticTester",
                         class_name="paladin", level=1,
                         known_spells={14, 200, 210}, control=control), control


def ready(at: float = 10.0) -> AssistObservation:
    return AssistObservation(observed_at=at, character_name="SyntheticTester",
                             class_name="Paladin", level=1,
                             game_focused=True, chat_open=False,
                             current_target_verified=True, hp=1.0, mana=1.0,
                             memorized={1: 200, 3: 14})


def test_assist_requires_mode_focus_target_fresh_gauges_and_memorized_gems():
    assist, control = advisor()
    observed = ready()
    assert assist.propose(observed, 10.0) is None
    control.switch(Mode.ASSIST)
    assert assist.propose(replace(observed, game_focused=False), 10.0) is None
    assert assist.propose(replace(observed, chat_open=True), 10.0) is None
    assert assist.propose(replace(observed, current_target_verified=False), 10.0) is None
    assert assist.propose(replace(observed, character_name="OtherCharacter"), 10.0) is None
    assert assist.propose(replace(observed, level=2), 10.0) is None
    assert assist.propose(replace(observed, hp=None), 10.0) is None
    assert assist.propose(replace(observed, mana=float("nan")), 10.0) is None
    assert assist.propose(replace(observed, memorized={1: 200}), 10.0) is None
    assert assist.propose(replace(observed, observed_at=8.0), 10.0) is None
    proposal = assist.propose(observed, 10.0)
    assert proposal is not None
    assert proposal.queued.action.kind == ActionKind.CAST
    assert proposal.queued.action.detail == "/cast 3"
    assert assist.still_allowed(proposal, observed, 10.0)
    assert not assist.still_allowed(proposal, replace(observed, chat_open=True), 10.0)
    control.handle_hotkey("F9")
    assert not assist.still_allowed(proposal, observed, 10.0)
    assert not assist.committed(proposal, observed, 10.0)


def test_assist_only_uses_observed_abilities_and_commits_after_check():
    assist, control = advisor()
    control.switch(Mode.ASSIST)
    observed = replace(ready(), available_abilities=frozenset({"/doability Bash"}))
    proposal = assist.propose(observed, 10.0)
    assert proposal is not None and proposal.queued.action.kind == ActionKind.ABILITY
    assert not assist.still_allowed(proposal, ready(), 10.0)
    assert assist.committed(proposal, observed, 10.0)
    assert assist.rotation.busy_until > 10.0


def test_assist_cli_demo_cancels_proposal_without_game_input():
    result = run_assist_demo()
    assert result["simulation_only"] and result["no_game_input"]
    assert result["proposed_action"] == "/cast 3"
    assert result["paladin_level_1_yaulp_excluded"]
    assert result["allowed_before_stop"]
    assert not result["old_proposal_allowed_after_stop"]
