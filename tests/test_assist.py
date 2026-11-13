from dataclasses import replace

from eql_automation.assist import AssistAdvisor, AssistObservation, TargetRelation
from eql_automation.control import ControlPlane
from eql_automation.modes import Action, ActionKind, Mode
from eql_automation.prior_rotation_core import Catalog, Spell
from eql_automation.sim import run_assist_demo


def advisor(*, level: int = 1,
            verified_self_heal_spell_ids: frozenset[int] = frozenset(),
            verified_self_buff_spell_ids: frozenset[int] = frozenset(),
            verified_self_lay_hands: bool = False) -> tuple[AssistAdvisor, ControlPlane]:
    catalog = Catalog([
        Spell(14, "Strike", 1, 1, 1000, 500, 0, 10, 0, 5),
        Spell(200, "Minor Healing", 1, 1, 1500, 500, 0, 10, 0, 51),
        Spell(210, "Yaulp", 1, 9, 1000, 500, 0, 1, 0, 6),
        Spell(77, "Ward Undead", 1, 1, 1500, 500, 0, 10, 0, 10),
    ])
    control = ControlPlane()
    return AssistAdvisor(catalog, character_name="SyntheticTester",
                         class_name="paladin", level=level,
                         known_spells={14, 200, 210, 77}, control=control,
                         verified_self_heal_spell_ids=verified_self_heal_spell_ids,
                         verified_self_buff_spell_ids=verified_self_buff_spell_ids,
                         verified_self_lay_hands=verified_self_lay_hands), control


def ready(at: float = 10.0) -> AssistObservation:
    return AssistObservation(observed_at=at, character_name="SyntheticTester",
                             class_name="Paladin", level=1,
                             game_focused=True, chat_open=False,
                             current_target_verified=True,
                             target_token="synthetic-target-selection-1",
                             target_relation=TargetRelation.HOSTILE_NPC,
                             target_is_undead=False,
                             hp=1.0, mana=1.0,
                             memorized={1: 200, 3: 14, 4: 77})


def test_assist_requires_mode_focus_target_fresh_gauges_and_memorized_gems():
    assist, control = advisor()
    observed = ready()
    assert assist.propose(observed, 10.0) is None
    control.switch(Mode.ASSIST)
    assert assist.propose(replace(observed, game_focused=False), 10.0) is None
    assert assist.propose(replace(observed, chat_open=True), 10.0) is None
    assert assist.propose(replace(observed, current_target_verified=False), 10.0) is None
    assert assist.propose(replace(observed, target_token=None), 10.0) is None
    assert assist.propose(replace(observed, target_token="   "), 10.0) is None
    assert assist.propose(replace(observed, character_name="OtherCharacter"), 10.0) is None
    assert assist.propose(replace(observed, level=2), 10.0) is None
    assert assist.propose(replace(observed, hp=None), 10.0) is None
    assert assist.propose(replace(observed, hp="half"), 10.0) is None
    assert assist.propose(replace(observed, mana=float("nan")), 10.0) is None
    assert assist.propose(replace(observed, observed_at="old"), 10.0) is None
    assert assist.propose(replace(observed, memorized={1: 200}), 10.0) is None
    assert assist.propose(replace(observed, observed_at=8.0), 10.0) is None
    assert assist.propose(replace(observed, target_relation=TargetRelation.UNKNOWN), 10.0) is None
    assert assist.propose(replace(observed, target_relation=TargetRelation.FRIENDLY), 10.0) is None
    assert assist.propose(replace(observed, target_relation=TargetRelation.HOSTILE_PLAYER), 10.0) is None
    proposal = assist.propose(observed, 10.0)
    assert proposal is not None
    assert proposal.queued.action.kind == ActionKind.CAST
    assert proposal.queued.action.detail == "/cast 3"
    assert not assist.still_allowed(proposal, observed, 10.0)
    refreshed = replace(observed, observed_at=10.1)
    assert assist.still_allowed(proposal, refreshed, 10.1)
    assert proposal.target_token == observed.target_token
    assert not assist.still_allowed(
        proposal, replace(refreshed, target_token="synthetic-target-selection-2"), 10.1)
    assert not assist.still_allowed(
        proposal, replace(refreshed, target_relation=TargetRelation.FRIENDLY), 10.1)
    assert not assist.still_allowed(
        proposal, replace(refreshed, target_is_undead=True), 10.1)
    assert not assist.still_allowed(
        proposal, replace(refreshed, memorized={1: 200, 4: 77}), 10.1)
    assert not assist.still_allowed(
        replace(proposal, queued=replace(
            proposal.queued, action=Action(ActionKind.CAST, "/cast 4"))),
        refreshed, 10.1)
    assert not assist.committed(
        proposal, replace(refreshed, target_token="synthetic-target-selection-2"), 10.1)
    assert assist.rotation.busy_until == 0.0
    assert not assist.still_allowed(proposal, replace(refreshed, chat_open=True), 10.1)
    control.handle_hotkey("F9")
    assert not assist.still_allowed(proposal, refreshed, 10.1)
    assert not assist.committed(proposal, refreshed, 10.1)


def test_assist_only_uses_observed_abilities_and_commits_after_check():
    assist, control = advisor()
    control.switch(Mode.ASSIST)
    observed = replace(ready(), available_abilities=frozenset({"/doability Bash"}))
    proposal = assist.propose(observed, 10.0)
    assert proposal is not None and proposal.queued.action.kind == ActionKind.ABILITY
    refreshed = replace(observed, observed_at=10.1)
    assert not assist.still_allowed(
        proposal, replace(refreshed, available_abilities=frozenset()), 10.1)
    assert assist.committed(proposal, refreshed, 10.1)
    assert assist.rotation.busy_until > 10.0


def test_assist_cli_demo_cancels_proposal_without_game_input():
    result = run_assist_demo()
    assert result["simulation_only"] and result["no_game_input"]
    assert result["proposed_action"] == "/cast 3"
    assert result["recorded_command_complete"]
    assert result["recorded_key_down_count"] == len("/cast 3") + 1
    assert not result["recorded_draft_uncertain"]
    assert result["paladin_level_1_yaulp_excluded"]
    assert result["allowed_before_stop"]
    assert not result["old_proposal_allowed_after_stop"]


def test_assist_pauses_at_low_self_hp_without_retargeting_or_unverified_heal():
    assist, control = advisor()
    control.switch(Mode.ASSIST)
    assert assist.propose(replace(ready(), hp=0.5), 10.0) is None
    self_selected = replace(ready(), hp=0.5, target_relation=TargetRelation.SELF)
    assert assist.propose(self_selected, 10.0) is None  # Client type 51 is unverified.
    buff_only, control = advisor(verified_self_buff_spell_ids=frozenset({210}), level=9)
    control.switch(Mode.ASSIST)
    assert buff_only.propose(replace(self_selected, level=9,
                                    memorized={1: 200, 3: 14, 4: 77, 7: 210}), 10.0) is None
    approved, control = advisor(verified_self_heal_spell_ids=frozenset({200}))
    control.switch(Mode.ASSIST)
    proposal = approved.propose(self_selected, 10.0)
    assert proposal is not None and proposal.queued.action.detail == "/cast 1"
    assert not approved.still_allowed(
        proposal, replace(self_selected, observed_at=10.1,
                          target_relation=TargetRelation.HOSTILE_NPC), 10.1)


def test_assist_skips_unverified_buff_and_requires_undead_observation():
    assist, control = advisor(level=9)
    control.switch(Mode.ASSIST)
    observed = replace(ready(), level=9,
                       memorized={1: 200, 3: 14, 4: 77, 7: 210})
    assist.rotation.mode = "undead"
    normal = assist.propose(observed, 10.0)
    assert normal is not None and normal.queued.action.detail == "/cast 3"
    undead = assist.propose(replace(observed, target_is_undead=True), 10.0)
    assert undead is not None and undead.queued.action.detail == "/cast 4"
    approved, control = advisor(level=9,
                                verified_self_buff_spell_ids=frozenset({210}))
    control.switch(Mode.ASSIST)
    buff = approved.propose(observed, 10.0)
    assert buff is not None and buff.queued.action.detail == "/cast 7"


def test_assist_rejects_unverified_ability_and_target_type_mismatch():
    assist, control = advisor()
    control.switch(Mode.ASSIST)
    self_selected = replace(ready(), hp=0.2,
                            target_relation=TargetRelation.SELF,
                            available_abilities=frozenset({"/alt activate 6001"}))
    assert assist.propose(self_selected, 10.0) is None
    approved, control = advisor(verified_self_lay_hands=True)
    control.switch(Mode.ASSIST)
    lay_hands = approved.propose(self_selected, 10.0)
    assert lay_hands is not None and lay_hands.queued.action.detail == "/alt activate 6001"
    # A client catalog mismatch must never turn a heal into a hostile cast.
    assist.rotation.profile["nuke"] = replace(assist.rotation.profile["nuke"],
                                                target_type=51)
    assert assist.propose(ready(), 10.0) is None


def test_hybrid_assist_requires_matching_observed_class_set_and_gem():
    catalog = Catalog([
        Spell(14, "Strike", 1, 1, 1000, 500, 0, 10, 0, 5),
        Spell(560, "Furor", 5, 8, 1000, 500, 0, 10, 0, 5),
        Spell(200, "Minor Healing", 1, 1, 1500, 500, 0, 10, 0, 51),
        Spell(210, "Yaulp", 1, 9, 1000, 500, 0, 1, 0, 6),
    ])
    control = ControlPlane()
    assist = AssistAdvisor(catalog, character_name="SyntheticTester",
                           class_name="Paladin", class_names=frozenset({"Paladin", "Cleric"}),
                           level=7, known_spells={14, 560, 200, 210}, control=control)
    control.switch(Mode.ASSIST)
    observed = replace(ready(), level=7, class_names=frozenset({"Paladin", "Cleric"}),
                       memorized={1: 200, 3: 560, 7: 210})
    assert assist.rotation.profile["nuke"].id == 560
    assert assist.rotation.profile["yaulp"].id == 210
    assert assist.propose(replace(observed, class_names=None), 10.0) is None
    assert assist.propose(replace(observed, class_names=frozenset({"Paladin"})), 10.0) is None
    assert assist.propose(replace(observed, memorized={1: 200, 3: 14}), 10.0) is None
    proposal = assist.propose(observed, 10.0)
    assert proposal is not None and proposal.queued.action.detail == "/cast 3"
