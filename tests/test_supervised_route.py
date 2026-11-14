"""Real source checks, log reader and pipe watchdog; observations are synthetic."""
from dataclasses import replace
import os
import time
from types import SimpleNamespace

import pytest

from eql_automation.fixed_route_follower import RouteHalt
from eql_automation.g2_safety_provider import GameWindowIdentity
from eql_automation.owner_input_observer import OwnerInputObservation
from eql_automation.route_step_sender import RouteStepScene, run_checked_route_step
from eql_automation.scene_log_veto import SceneLogVeto
from eql_automation.supervised_route import SupervisedRouteDeclaration, SupervisedRoutePolicy
from eql_automation.uinput_watchdog import _EVENT, PulseError
from test_route_floor_commit import legacy
from test_route_geometry import build
from test_route_step_sender import PipeSender, after_down


def setup(tmp_path, legacy, *, real=False, hazard=None, declaration_changes=None):
    f = build(legacy, clock=time.monotonic if real else None,
              **({hazard: True} if hazard else {}))
    f.focus = True; f.input_active = False; f.topology = 1; f.owner_cancelled = False
    f.window = SimpleNamespace(id=42)
    f.gate = SimpleNamespace(windows=lambda: [f.window],
        focused_window=lambda: f.window if f.focus else None,
        game_session=lambda: {'pid': 10, 'start_ticks': '100'},
        controls_ready=lambda: f.focus)
    def sample():
        now = f.clock()
        return OwnerInputObservation(now, now, f.topology, True, 1, 0,
                                     f.input_active, 0, 'synthetic-device')
    f.input = SimpleNamespace(sample=sample)
    f.log = tmp_path/'eqlog_Probe_private.txt'; f.log.touch()
    veto = SceneLogVeto(f.log, expected_character='Probe', expected_server='private',
                       cancel_generation=1, clock=f.clock)
    d = SupervisedRouteDeclaration('synthetic-owner-trial', f.runner.route.artifact_sha256,
        f.runner.calibration, f.prepare.bounds.record_id, True, 120., 32, 20., 2.)
    if declaration_changes: d = replace(d, **declaration_changes)
    def current():
        if f.owner_cancelled: raise ValueError('Owner scope cancelled')
    f.policy = SupervisedRoutePolicy(f.prepare, declaration=d, gate=f.gate,
        owner_input=f.input, log_veto=veto, expected_log_path=f.log,
        expected_window=GameWindowIdentity(42, 10, 100), topology_generation=1,
        check_current=current)
    f.scene = lambda: RouteStepScene(f.reference, f.policy.observe(f.reference))
    f.options = dict(scene_provider=f.scene, prepare_step=f.prepare,
        authorize_step=f.policy.authorize, still_authorized=f.policy.still_authorized,
        command_state_clear=lambda: True, pump=lambda: None, supervised_policy=f.policy)
    return f


def pipe(f):
    f.rd, f.wr = os.pipe()
    f.sender = PipeSender(f.wr)
    f.run = lambda: run_checked_route_step(f.sender, f.ledger, **f.options)
    def close():
        os.close(f.wr)
        data = b''
        while block := os.read(f.rd, 4096): data += block
        os.close(f.rd)
        f.events = [(kind, key, value) for _, _, kind, key, value in _EVENT.iter_unpack(data)]
    f.close = close


def test_positive_observations_do_not_fabricate_ui_or_bound_verification(tmp_path, legacy):
    f = setup(tmp_path, legacy)
    observed = f.scene()
    f.policy.validate_scene(observed, f.ledger)
    s = observed.scene
    assert s.focused and s.owner_keys_clear and s.log_observation.continuity_available
    assert s.log_observation.reason is None
    assert not any((s.chat_clear, s.target_absent, s.combat_clear, s.no_transition,
                    s.no_incoming_attack, s.independent_scene_verified, s.motion_bounds_verified))
    f.prepare.precompute(observed)
    ticket = f.prepare(f.runner.propose(f.clock()), observed)
    auth = f.policy.authorize(ticket, observed)
    assert f.policy.still_authorized(auth, observed)
    assert not auth.independent_scene_verified and not auth.motion_bounds_verified
    record = f.policy.snapshot()
    assert not record['dynamic_clearance_verified'] and not record['real_client_accepted']
    assert record['reserved_maximum_hold'] == f.prepare.bounds.maximum_actual_hold


def test_default_strict_sender_rejects_supervised_scene_without_input(tmp_path, legacy):
    f = setup(tmp_path, legacy); pipe(f)
    f.options['supervised_policy'] = None
    try:
        with pytest.raises(RouteHalt): f.run()
        assert f.runner.steps == 0 and f.ledger.chain is f.chain
    finally: f.close()
    assert not f.events


@pytest.mark.parametrize('change', ['assist', 'full_auto', 'off', 'owner_cancel',
                                  'input', 'topology', 'focus', 'process', 'log',
                                  'log_replaced', 'bounds', 'deadline', 'steps'])
def test_changed_scope_or_observation_refuses_before_key_submission(tmp_path, legacy, change):
    f = setup(tmp_path, legacy); pipe(f)
    if change in ('assist', 'full_auto', 'off'): f.state['mode'] = change
    elif change == 'owner_cancel': f.owner_cancelled = True
    elif change == 'input': f.input_active = True
    elif change == 'topology': f.topology += 1
    elif change == 'focus': f.focus = False
    elif change == 'process': f.gate.game_session = lambda: {'pid': 11, 'start_ticks': '100'}
    elif change == 'log':
        f.log.write_text('[Sat Nov 14 10:00:00 2026] A bat hits YOU for 1 point of damage.\n')
    elif change == 'log_replaced':
        replacement = f.log.with_suffix('.replacement'); replacement.touch(); replacement.replace(f.log)
    elif change == 'bounds': f.prepare.bounds = replace(f.prepare.bounds, body_radius=.2)
    elif change == 'deadline': f.state['now'] += 121
    elif change == 'steps': f.runner.steps = 32
    try:
        with pytest.raises((RouteHalt, ValueError)): f.run()
        assert f.ledger.chain is f.chain and not f.sender.held
    finally: f.close()
    assert not f.events


@pytest.mark.parametrize('changes', [
    {'open_flat_clear': False}, {'maximum_seconds': 121.}, {'maximum_steps': 33},
    {'maximum_distance': 21.}, {'maximum_total_hold': 2.1},
    {'route_sha256': 'wrong'}, {'motion_record_id': 'wrong'},
    {'planning_bounds_record_id': 'wrong'}, {'maximum_distance': .5},
])
def test_declaration_is_finite_and_bound_to_exact_plan(tmp_path, legacy, changes):
    with pytest.raises(ValueError): setup(tmp_path, legacy, declaration_changes=changes)


def test_destination_scope_has_explicit_limits_and_preserves_measurement_evidence(tmp_path, legacy):
    f=setup(tmp_path,legacy,declaration_changes=dict(scope='destination_travel',
        maximum_seconds=1500.,maximum_steps=3000,maximum_distance=10000.,maximum_total_hold=600.))
    # A destination may proceed beyond the former short-trial step budget.
    f.runner.steps=33
    observed=f.scene();f.policy.validate_scene(observed,f.ledger)
    assert not observed.scene.independent_scene_verified
    assert f.policy.snapshot()['declaration']['scope']=='destination_travel'
    f.runner.steps=3000
    with pytest.raises(RouteHalt):f.scene()


@pytest.mark.parametrize('changes',[
    {'maximum_seconds':1500.01},{'maximum_steps':3001},
    {'maximum_distance':10000.01},{'maximum_total_hold':600.01},{'scope':'unattended'},
])
def test_destination_scope_is_still_finite(tmp_path,legacy,changes):
    values=dict(scope='destination_travel',maximum_seconds=1500.,maximum_steps=3000,
                maximum_distance=10000.,maximum_total_hold=600.)
    values.update(changes)
    with pytest.raises(ValueError):setup(tmp_path,legacy,declaration_changes=values)


@pytest.mark.parametrize('hazard', ['wall', 'water'])
def test_supervised_scope_cannot_waive_source_geometry(tmp_path, legacy, hazard):
    f = setup(tmp_path, legacy, hazard=hazard)
    observed = f.scene(); f.prepare.precompute(observed)
    with pytest.raises(ValueError, match='Static geometry|BSP volume'):
        f.prepare(f.runner.propose(f.clock()), observed)
    assert f.ledger._pending is None and f.ledger.chain is f.chain


def test_hold_reservation_and_forged_verification_do_not_pass(tmp_path, legacy):
    f = setup(tmp_path, legacy)
    observed = f.scene()
    forged = replace(observed, scene=replace(observed.scene, chat_clear=True))
    with pytest.raises(RouteHalt): f.policy.validate_scene(forged, f.ledger)
    f.prepare.precompute(observed)
    ticket = f.prepare(f.runner.propose(f.clock()), observed)
    f.policy.reserved_hold = 1.95
    with pytest.raises(RouteHalt, match='hold budget'): f.policy.authorize(ticket, observed)
    assert f.ledger.chain is f.chain


@pytest.mark.parametrize('callback', ['scope', 'focus'])
def test_cancel_inside_observation_callback_cannot_return_clear_scope(tmp_path, legacy, callback):
    f = setup(tmp_path, legacy)
    if callback == 'scope':
        f.policy.check_current = lambda: f.policy.cancel('Stop within scope callback')
    else:
        def focus():
            f.policy.cancel('Stop within window lookup')
            return f.window
        f.gate.focused_window = focus
    with pytest.raises(RouteHalt): f.policy.observe(f.reference)


def test_cancel_inside_geometry_recheck_cannot_authorize_final_commit(tmp_path, legacy):
    f = setup(tmp_path, legacy); observed = f.scene()
    f.prepare.precompute(observed)
    ticket = f.prepare(f.runner.propose(f.clock()), observed)
    auth = f.policy.authorize(ticket, observed)
    original = f.prepare.record_for
    def changed(ticket):
        result = original(ticket)
        f.policy.cancel('Stop during geometry record lookup')
        return result
    f.prepare.record_for = changed
    with pytest.raises(RouteHalt): f.policy.still_authorized(auth, observed)
    assert f.ledger.chain is f.chain and f.runner.steps == 0


def test_slow_scope_callback_cannot_cross_whole_trial_deadline(tmp_path, legacy):
    f = setup(tmp_path, legacy)
    def slow():
        f.state['now'] += 61.
    f.policy.check_current = slow
    with pytest.raises(RouteHalt): f.policy._check()
    assert f.policy.last_at == f.policy.started


def test_one_actual_pipe_pulse_keeps_conditional_scope_and_commits_after_release(tmp_path, legacy):
    f = setup(tmp_path, legacy, real=True); pipe(f)
    try:
        result = f.run()
        assert result.authorization_scope == 'owner_supervised_conditional_trial'
        assert not result.real_client_accepted and not f.sender.held
        assert f.runner.steps == 1 and f.ledger.chain is not f.chain
        assert f.sender.release_calls == 1
    finally: f.close()
    assert (1, 103, 1) in f.events and f.events[-2:] == [(1, 103, 0), (0, 0, 0)]


def test_owner_cancel_during_actual_pipe_down_releases_and_never_commits(tmp_path, legacy, monkeypatch):
    f = setup(tmp_path, legacy, real=True); pipe(f)
    after_down(monkeypatch, lambda: f.policy.cancel('Owner stop'))
    try:
        with pytest.raises((RouteHalt, ValueError, PulseError)): f.run()
        assert not f.sender.held and f.runner.steps == 0 and f.ledger.chain is f.chain
    finally: f.close()
    assert (1, 103, 1) in f.events and f.events[-2:] == [(1, 103, 0), (0, 0, 0)]
