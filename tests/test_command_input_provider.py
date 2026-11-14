"""Real veto tails and command journals with explicitly synthetic UI/input."""
from dataclasses import replace

import pytest

from eql_automation.command_input_provider import CommandInputProvider, CommandUiObservation
from eql_automation.command_submission import CommandSubmissionJournal, LOCATION_EVENTS
from eql_automation.g2_scene_observer import G2ObservationUnavailable
from eql_automation.motion_collection import LocationRequest, MotionRequest
from test_g2_safety_provider import fixture


def journal(count):
    j = CommandSubmissionJournal('synthetic-command')
    for i, event in enumerate(LOCATION_EVENTS[:count*4]):
        at = 99. + i*.001
        attempt = j.begin(event, at, 24)
        j.finish(attempt, at+.0001, written_bytes=24, outcome='complete')
    return j.snapshot()


def setup(tmp_path):
    safety, gate, clock, generation, mode, inputs, frames = fixture(tmp_path)
    changes = []
    def observe(window, request, phase, submission):
        base = safety.ui_observer(window)
        drafting = phase == 'command_key'
        fields = dict(vars(base)); fields['chat_clear'] = not drafting
        visual = CommandUiObservation(**fields, request=request, phase=phase, submission=submission,
            input_focused=drafting, draft_absent=not drafting,
            visible_prefix=submission.submitted_prefix if drafting else None,
            text_complete=drafting, caret_at_end=drafting, selection_absent=drafting)
        return changes.pop(0)(visual) if changes else visual
    provider = CommandInputProvider(safety, ui_observer=observe)
    return provider, LocationRequest(1,0,99.,101.), changes, (safety, gate, clock, generation, mode, inputs, frames)


@pytest.mark.parametrize('phase,count', [('command_start',0),('command_first_key',0),
    *[('command_key',n) for n in range(1,10)],('command_end',10)])
def test_every_phase_preserves_exact_submission_and_oldest_time(tmp_path, phase, count):
    provider, request, _, context = setup(tmp_path)
    snapshot = journal(count)
    result = provider(request, phase, snapshot)
    assert result.request is request and result.submission is snapshot and result.phase == phase
    assert result.observed_at == 100. and result.valid_until == 100.1
    assert result.record_id.startswith('command-ui-')
    assert provider.last_observation.submission is snapshot
    assert context[0].last_ui is None  # Not a movement all-clear result.


@pytest.mark.parametrize('changes', [
    {'chat_clear':True}, {'input_focused':False}, {'input_focused':None},
    {'draft_absent':True}, {'visible_prefix':'/loot'}, {'visible_prefix':'/loc extra'},
    {'text_complete':False}, {'caret_at_end':False}, {'selection_absent':False},
    {'target_absent':False}, {'combat_clear':False}, {'no_transition':False},
    {'no_incoming_attack':False}, {'calibration_sha256':'d'*64},
])
def test_drafting_unknown_or_changed_state_refuses(tmp_path, changes):
    provider, request, mutations, _ = setup(tmp_path)
    mutations.append(lambda v: replace(v, **changes))
    with pytest.raises(G2ObservationUnavailable): provider(request, 'command_key', journal(4))
    assert provider.last_observation is None


@pytest.mark.parametrize('phase,count', [('command_start',0),('command_first_key',0),('command_end',10)])
@pytest.mark.parametrize('changes', [{'chat_clear':False}, {'input_focused':True},
    {'input_focused':None}, {'draft_absent':False}, {'visible_prefix':''}])
def test_closed_phases_do_not_infer_closure_from_blank_text(tmp_path, phase, count, changes):
    provider, request, mutations, _ = setup(tmp_path)
    mutations.append(lambda v: replace(v, **changes))
    with pytest.raises(G2ObservationUnavailable): provider(request, phase, journal(count))


@pytest.mark.parametrize('change', ['copied_request','copied_snapshot','phase','old_frame','candidate_dict'])
def test_wrong_identity_or_diagnostic_candidates_cannot_be_evidence(tmp_path, change):
    provider, request, mutations, _ = setup(tmp_path)
    def alter(v):
        if change == 'copied_request': return replace(v, request=replace(request))
        if change == 'copied_snapshot': return replace(v, submission=replace(v.submission))
        if change == 'phase': return replace(v, phase='command_end')
        if change == 'old_frame': return replace(v, started_at=98.)
        return {'status':'pixel_candidates_only','input_authorized':False}
    mutations.append(alter)
    with pytest.raises(G2ObservationUnavailable): provider(request, 'command_key', journal(4))


@pytest.mark.parametrize('change', ['prefix','keys','partial','uncertain','phase','wrong_command','early_enter'])
def test_snapshot_cannot_change_command_or_phase(tmp_path, change):
    provider, request, _, _ = setup(tmp_path); snapshot = journal(4); phase = 'command_key'
    if change == 'prefix': snapshot = replace(snapshot, submitted_prefix='/loot')
    elif change == 'keys': snapshot = replace(snapshot, attempted_key_codes=(53,))
    elif change == 'partial': snapshot = replace(snapshot, writes=snapshot.writes[:-1])
    elif change == 'uncertain': snapshot = replace(snapshot, uncertain=True)
    elif change == 'phase': phase = 'command_end'
    elif change == 'wrong_command': snapshot = replace(snapshot, command='/target')
    else: snapshot = replace(snapshot, enter_submitted=True)
    with pytest.raises(G2ObservationUnavailable): provider(request, phase, snapshot)


@pytest.mark.parametrize('change', ['owner','cancel','assist','focus','process','attack','slow','expired'])
def test_actual_scope_checks_remain_active_while_drafting(tmp_path, change):
    provider, request, mutations, context = setup(tmp_path)
    safety, gate, clock, generation, mode, inputs, frames = context
    def alter(v):
        if change == 'owner': inputs.append(lambda o: replace(o, activity=True))
        elif change == 'cancel': generation[0] += 1
        elif change == 'assist': mode[0] = 'assist'
        elif change == 'focus': gate.focused = False
        elif change == 'process': gate.window = replace(gate.window, start_ticks=601)
        elif change == 'attack':
            with safety.log_path.open('a') as f:
                f.write('[Sat Nov 14 08:00:00 2026] An orc hits YOU for 1 point of damage.\n')
        elif change == 'slow': clock[0] += .11
        else: clock[0] = request.expires_at + .01
        return v
    mutations.append(alter)
    with pytest.raises(G2ObservationUnavailable): provider(request, 'command_key', journal(4))
    assert provider.last_observation is None


def test_provider_cannot_supply_movement_evidence(tmp_path):
    provider, _, _, _ = setup(tmp_path)
    with pytest.raises(G2ObservationUnavailable):
        provider(MotionRequest(0, None, 99.,101.), 'movement', journal(0))


def test_missing_classifier_does_not_fall_back_to_engine_flags(tmp_path):
    safety, *_ = fixture(tmp_path)
    with pytest.raises(ValueError): CommandInputProvider(safety, ui_observer=None)
    safety()
    assert safety.last_ui is not None
    with pytest.raises(ValueError): safety.observe_ui(None)
    assert safety.last_ui is None
