"""Synthetic clock/input receipts; real destination readers, geometry and policies.

No game or real input device is opened. The pipe supplies descriptor identity
only; synthetic receipt producers are explicitly patched at the sender boundary.
"""
from dataclasses import replace
from copy import deepcopy
import math
import os
import threading
from types import SimpleNamespace

import pytest
import numpy as np

import eql_automation.camp_probe_runtime as probe_module
import eql_automation.destination_bootstrap_runtime as module
from eql_automation.camp_probe_runtime import CampProbeRuntime
from eql_automation.camp_probe_sender import SentCampProbe
from eql_automation.destination_floor_bootstrap import DestinationFloorBootstrap, DestinationFloorCheckpoint
from eql_automation.g2_safety_provider import GameWindowIdentity
from eql_automation.location_hotkey import HotkeyReceipt, OwnerLocationHotkey
from eql_automation.motion_calibration import PROBES
from eql_automation.native_region_policy import encoded
from eql_automation.owner_input_observer import OwnerInputObservation
from eql_automation.portal_precision import SourceFace
from eql_automation.scene_log_veto import SceneLogVeto
from eql_automation.source_itinerary import SourceItineraryGuide, SourceWalkHint
from eql_automation.supervised_camp_probe import SupervisedCampProbeDeclaration
from eql_automation.uinput_watchdog import PulseReceipt
from test_destination_floor_bootstrap import destination
from test_motion_calibration import legacy as fitter
from test_route_step_sender import PipeSender
from test_itinerary_policy_budget import root_budget, bootstrap_stage


@pytest.fixture
def runtime(destination, tmp_path, monkeypatch, fitter, request):
    f = destination
    # Give the synthetic destination a complete flat source/detail floor large
    # enough for the standard seven measurements and their all-heading disks.
    corners = ((-10., -10., .2), (20., -10., .2), (20., 20., .2), (-10., 20., .2))
    f.planner.source.sources = tuple(SourceFace(tuple((y, x, z) for x, y, z in tri), 0,
        'Diffuse', 10, i) for i, tri in enumerate(((corners[0], corners[1], corners[2]),
                                                  (corners[0], corners[2], corners[3]))))
    coords = np.asarray([s.vertices_wld for s in f.planner.source.sources])[:, :, [1, 0, 2]]
    f.planner.source.source_minimum = coords.min(axis=1)
    f.planner.source.source_maximum = coords.max(axis=1)
    detail = coords.copy()
    detail[:, :, 2] = .6
    f.planner.ground.triangles = f.planner.mesh._detail = detail
    f.planner.ground.minimum, f.planner.ground.maximum = detail.min(axis=1), detail.max(axis=1)
    f.bounds = replace(f.bounds, maximum_requested_hold=.15, maximum_actual_hold=.18,
                       forward_speed_upper_bound=11., heading_error_degrees=2.)
    f.clock_hook = None
    def clock():
        if f.clock_hook is not None:
            hook, f.clock_hook = f.clock_hook, None
            hook()
        return f.now
    f.clock = clock
    f.generation_hook = None
    def generation():
        if f.generation_hook is not None:
            hook, f.generation_hook = f.generation_hook, None
            hook()
        return f.generation
    f.bootstrap = DestinationFloorBootstrap(f.planner, f.lease, bounds=f.bounds, bounds_basis=f.basis,
        owner_binding=f.owner, binding_reader=f.binding, generation=f.generation,
        generation_reader=generation, record_id='synthetic-runtime-destination',
        clock=f.clock, local_wall_clock=f.wall, maximum_seconds=120.)
    f.x, f.y, f.heading = 4., 3., 0.
    f.focus, f.active, f.closed_observer = True, False, False
    f.sample_hook = f.current_hook = f.send_hook = f.movement_hook = None
    f.sent, f.movements = [], []
    f.rd, f.wr = os.pipe()
    f.sender = PipeSender(f.wr)
    def sample():
        if f.sample_hook is not None:
            hook, f.sample_hook = f.sample_hook, None
            hook()
        return OwnerInputObservation(f.now, f.now, 1, True, 1, 0, f.active, 0,
                                     'synthetic destination input')
    def close():
        f.closed_observer = True
    f.owner_input = SimpleNamespace(sample=sample, close=close)
    window = SimpleNamespace(id=7)
    f.gate = SimpleNamespace(windows=lambda:[window], focused_window=lambda:window if f.focus else None,
        game_session=lambda:dict(pid=8, start_ticks='9'), controls_ready=lambda:f.focus)
    config = tmp_path/'synthetic-destination-hotkey.ini'
    config.write_text('Synthetic test F1 = /location\n')
    f.hotkey = OwnerLocationHotkey.configured('F1', confirmation_id='synthetic-only',
                                             configuration_paths=(config,))
    f.veto = SceneLogVeto(f.reader.tail.path, expected_character='Probe', expected_server='private', cancel_generation=f.generation, clock=f.clock)
    f.lock = threading.RLock()
    def current():
        if f.current_hook is not None:
            hook, f.current_hook = f.current_hook, None
            hook()
    f.options = dict(sender=f.sender, hotkey=f.hotkey, owner_input=f.owner_input,
        declaration=SupervisedCampProbeDeclaration('synthetic-destination-supervision',
            f.bounds.record_id, True, 7*f.bounds.maximum_actual_hold),
        stop_lock=f.lock, gate=f.gate, expected_window=GameWindowIdentity(7, 8, 9),
        topology_generation=1, log_veto=f.veto, check_current=current,
        command_state_clear=lambda:True, pump=lambda:None, fit_library=fitter)
    f.budget = None
    if getattr(request, 'param', None) == 'budget':
        f.budget = root_budget(clock=f.clock, lock=f.lock, maximum_seconds=90.)
        bootstrap_stage(f.budget)
        f.options['journey_budget'] = f.budget
    f.runtime = module.DestinationBootstrapRuntime(f.bootstrap, **f.options)

    def location(sender, **options):
        options['ensure_current']()
        assert f.runtime.current_input_key() == 59
        start = f.now
        if f.send_hook is not None:
            hook, f.send_hook = f.send_hook, None
            hook()
        options['ensure_current']()
        f.now += .01
        pulse = PulseReceipt(59, .005, start, start+.001, start+.006, f.now, 'elapsed')
        f.sent.append(pulse)
        f.append(f'Your Location is {f.y:.2f}, {f.x:.2f}, 2.70')
        return HotkeyReceipt(pulse, f.now)

    def movement(sender, tx, start, *, policy, requested_seconds, **options):
        assert f.runtime.current_input_key() == {'forward':103, 'left':105, 'right':106}[tx.preparation.kind]
        assert policy.check() is True
        ticket = tx.stage(start, movement_key=f.runtime.current_input_key(), requested_seconds=requested_seconds)
        authorization = policy.authorize(ticket)
        assert policy.still_authorized(authorization) is True
        if f.movement_hook is not None:
            hook, f.movement_hook = f.movement_hook, None
            hook()
        assert policy.check() is True
        began = f.now
        pulse = PulseReceipt(ticket.movement_key, requested_seconds, began+.001, began+.0012,
            began+.0012+requested_seconds, began+.0014+requested_seconds, 'elapsed')
        f.now = pulse.up_completed_at+.001
        seconds = (pulse.maximum_held_seconds+ pulse.up_started_at-pulse.down_completed_at)/2
        if tx.preparation.kind == 'forward':
            f.y += math.cos(math.radians(f.heading))*10.*seconds
            f.x += math.sin(math.radians(f.heading))*10.*seconds
        else:
            f.heading += (1 if tx.preparation.kind == 'right' else -1)*170.*(seconds-.03)
        f.x, f.y = round(f.x, 2), round(f.y, 2)
        f.movements.append(pulse)
        return SentCampProbe(tx.seal_release(ticket, pulse), f.now)

    monkeypatch.setattr(module, 'send_location_hotkey', location)
    monkeypatch.setattr(probe_module, 'send_location_hotkey', location)
    monkeypatch.setattr(probe_module, 'send_camp_probe', movement)
    yield f
    if not f.runtime.closed:
        if f.runtime.phase not in ('complete', 'route_ready', 'stopped'):
            f.runtime.cancel('synthetic test cleanup')
        f.runtime.release()
    os.close(f.wr)
    os.close(f.rd)


def advance(f, predicate):
    for _ in range(2000):
        if predicate():
            return
        f.runtime.tick()
        f.now += .01
    pytest.fail('Synthetic destination bootstrap did not reach expected phase: '+f.runtime.phase)


def test_three_new_pairs_precede_any_movement_and_probe_start_is_separate(runtime):
    f = runtime; r = f.runtime; expiry = r.expires_at
    advance(f, lambda:r.phase == 'probes')
    assert type(r.floor) is DestinationFloorCheckpoint and type(r.runtime) is CampProbeRuntime
    assert [c['kind'] for c in r.collections] == ['planning', 'capture', 'height']
    assert len(f.sent) == 6 and f.movements == []
    assert r.height.first.log_line_seq > r.floor._anchor.second.log_line_seq
    assert r.runtime.root.checkpoint is r.floor and r.runtime.probes == PROBES
    assert r.runtime.started+r.runtime.maximum_seconds == pytest.approx(expiry)
    assert r.monitor.floor is None and r.runtime.log_veto is f.veto
    advance(f, lambda:r.runtime.phase == 'pulse')
    assert len(f.sent) == 8 and f.movements == []
    assert r.runtime.start.height.first.log_line_seq > r.height.second.log_line_seq
    assert r.scope.log_veto is f.veto and r.expires_at == expiry
    assert not r.snapshot()['source_zone_state_reused']
    assert not r.snapshot()['real_client_accepted']


def test_seven_synthetic_receipts_fit_new_destination_and_prepare_fresh_onward_start(runtime):
    f = runtime; r = f.runtime; expiry = r.expires_at
    advance(f, lambda:r.phase == 'complete')
    assert len(f.movements) == 7 and len(r.runtime.results) == 7
    assert r.calibration['estimate']['source_floor_sha256'] == r.floor.sha256
    assert r.calibration['estimate']['estimate']['run_speed'] == pytest.approx(10., abs=.05)
    assert r.calibration['estimate']['record_id'] == 'camp-'+r.runtime.results[-1].sha256
    assert r.scope.reserved_hold == pytest.approx(7*f.bounds.maximum_actual_hold)
    assert r.expires_at == expiry and f.lease.active
    old_confirmation = r.runtime.results[-1].second
    p = f.planner
    guide = SourceItineraryGuide('gfaydark', p.pins[2], p.pins[3], 'f'*64, .1, 6., (f.x, f.y+.5),
        (SourceWalkHint((f.x, f.y), (f.x, f.y+.5)),))
    r.prepare_route(guide)
    advance(f, lambda:r.phase == 'route_ready')
    fit = r.fresh_fit()
    assert fit is r.calibration['estimate']
    assert r.runtime.route_start.height.first.log_line_seq > old_confirmation.log_line_seq
    assert r.runtime.route_start.height.second is f.reader.latest
    assert r.runtime.started+r.runtime.maximum_seconds == pytest.approx(expiry)
    assert f.lease.active and not r.runtime.closed
    # A caller replacing both public fields cannot publish new steering while
    # retaining the genuine transaction ancestry and canonical evidence bytes.
    counterfeit = deepcopy(r.calibration)
    estimate = counterfeit['estimate']['estimate']
    estimate['final_heading'] = (estimate['final_heading']+1.) % 360.
    r.calibration = counterfeit
    r.calibration_seal = (counterfeit, encoded(counterfeit), r.runtime.reference,
                          tuple(r.runtime.transactions), tuple(r.runtime.results))
    with pytest.raises(ValueError, match='ownership'):
        r.fresh_fit()
    assert r.phase == 'stopped' and len(f.movements) == 7


@pytest.mark.parametrize('fault', ('generation', 'owner', 'focus', 'activity', 'attack', 'loading', 'expired',
                                  'descriptor', 'veto', 'cancel_callback'))
def test_changed_scope_refuses_before_first_location_or_movement(runtime, fault):
    f = runtime; r = f.runtime
    if fault == 'generation': f.generation += 1
    elif fault == 'owner': f.owner = ('changed', 'Probe')
    elif fault == 'focus': f.focus = False
    elif fault == 'activity': f.active = True
    elif fault == 'attack': f.append('Training dummy hits YOU for 2 points of damage.')
    elif fault == 'loading': f.append('LOADING, PLEASE WAIT...')
    elif fault == 'expired': f.now = r.expires_at+.001
    elif fault == 'descriptor': f.sender.ui = SimpleNamespace(fileno=lambda:f.wr)
    elif fault == 'veto': r.log_veto = SceneLogVeto(f.reader.tail.path, expected_character='Probe', expected_server='private', cancel_generation=f.generation, clock=f.clock)
    else: f.current_hook = lambda:r.cancel('F9 callback stop')
    with pytest.raises((ValueError, RuntimeError)):
        r.tick()
    assert r.phase == 'stopped' and not f.lease.active and f.sent == [] and f.movements == []
    assert r.bootstrap.phase == 'stopped' and not r.monitor.valid


@pytest.mark.parametrize('phase', ('collect_planning', 'collect_capture', 'collect_height', 'probes'))
def test_pending_location_cancellation_never_revives_parent_or_child(runtime, phase):
    f = runtime; r = f.runtime
    advance(f, lambda:r.phase == phase)
    sent = len(f.sent)
    f.send_hook = lambda:r.cancel('F8 takeover during location admission')
    with pytest.raises(ValueError):
        advance(f, lambda:len(f.sent)>sent)
    assert r.phase == 'stopped' and len(f.sent) == sent and not f.movements
    assert not f.lease.active
    if r.runtime is not None:
        assert r.runtime.phase == 'stopped'


def test_scope_expiry_after_floor_capture_does_not_restart_with_probe_child(runtime):
    f = runtime; r = f.runtime
    advance(f, lambda:r.phase == 'probes')
    child_expiry = r.runtime.started+r.runtime.maximum_seconds
    assert child_expiry == pytest.approx(r.expires_at)
    f.now = r.expires_at+.01
    with pytest.raises(ValueError): r.tick()
    assert r.phase == r.runtime.phase == 'stopped' and not f.movements


def test_callback_cancel_during_probe_admission_prevents_result(runtime):
    f = runtime; r = f.runtime
    advance(f, lambda:r.runtime is not None and r.runtime.phase == 'pulse')
    f.movement_hook = lambda:r.cancel('F9 during movement admission')
    with pytest.raises(ValueError): r.tick()
    assert r.phase == r.runtime.phase == 'stopped'
    assert f.movements == [] and r.runtime.results == [] and not f.lease.active


def test_release_requires_idle_and_can_preserve_observer_for_caller(runtime):
    f = runtime; r = f.runtime
    with pytest.raises(ValueError): r.release()
    r.cancel('finished synthetic scope')
    f.sender.held.add(103)
    with pytest.raises(ValueError): r.release()
    assert not r.closed
    f.sender.held.clear()
    r.release(close_observer=False)
    assert r.closed and f.lease._tracker.lease is None and not f.closed_observer
    assert f.reader.latest is None


@pytest.mark.parametrize('fault', ('closed', 'replace_sender', 'cancel'))
def test_generation_callback_cannot_preserve_generation_and_replace_scope(runtime, fault):
    f = runtime; r = f.runtime
    if fault == 'closed':
        f.generation_hook = lambda:setattr(r, 'closed', True)
    elif fault == 'replace_sender':
        f.generation_hook = lambda:setattr(r, 'sender', PipeSender(f.wr))
    else:
        f.generation_hook = lambda:r.cancel('Late F9 generation callback')
    with pytest.raises(ValueError): r.tick()
    assert r.phase == 'stopped' and f.movements == [] and f.sent == []
    r.closed = False  # Permit ordinary fixture cleanup after the intentional mutation.


def test_focus_changed_by_clear_input_sample_cannot_start_collection(runtime):
    f = runtime; r = f.runtime
    f.sample_hook = lambda:setattr(f, 'focus', False)
    with pytest.raises((ValueError, RuntimeError)): r.tick()
    assert r.phase == 'stopped' and not f.sent and not f.movements


def test_clock_callback_cannot_change_generation_after_earlier_owner_check(runtime):
    f = runtime; r = f.runtime
    f.clock_hook = lambda:setattr(f, 'generation', f.generation+1)
    with pytest.raises(ValueError): r.tick()
    assert r.phase == 'stopped' and not f.sent and not f.movements


@pytest.mark.parametrize('fault', ('absent', 'false', 'wrong_bounds', 'excess_hold'))
def test_explicit_supervision_is_required_before_claiming_or_sending(runtime, fault):
    f = runtime; options = dict(f.options)
    declaration = options['declaration']
    if fault == 'absent': options.pop('declaration')
    elif fault == 'false': options['declaration'] = replace(declaration, owner_supervised_continuation=False)
    elif fault == 'wrong_bounds': options['declaration'] = replace(declaration, bounds_record_id='other')
    else: options['declaration'] = replace(declaration, maximum_total_hold=100.)
    bootstrap = f.make_bootstrap()
    with pytest.raises((ValueError, TypeError)):
        module.DestinationBootstrapRuntime(bootstrap, **options)
    assert not hasattr(bootstrap, '_runtime_claim') and not f.movements and not f.sent


def test_one_bootstrap_cannot_be_claimed_by_a_second_runtime(runtime):
    f = runtime
    with pytest.raises(ValueError):
        module.DestinationBootstrapRuntime(f.bootstrap, **f.options)
    assert f.bootstrap._runtime_claim is f.runtime and not f.movements and not f.sent


@pytest.mark.parametrize('runtime', ['budget'], indirect=True)
def test_root_itinerary_clamps_lifetime_and_counts_actual_probe_tickets(runtime):
    f = runtime; r = f.runtime; budget = f.budget
    assert r.expires_at == budget.expires_at < f.bootstrap.expires_at
    advance(f, lambda:r.phase == 'complete')
    state = budget.snapshot()
    assert state['reserved_pulses'] == 7
    assert state['reserved_maximum_hold'] == pytest.approx(7*f.bounds.maximum_actual_hold)
    assert budget.stage.phase == 'bootstrap'
    assert r.runtime.started+r.runtime.maximum_seconds == pytest.approx(budget.expires_at)
    assert r.runtime.maximum_seconds < 90.
    assert r.scope.journey_budget is budget
    assert all(p._journey_reservation.ticket is t.ticket for p, t in zip(r.scope._policies, r.runtime.transactions))
    p = f.planner
    guide = SourceItineraryGuide('gfaydark', p.pins[2], p.pins[3], 'f'*64, .1, 6., (f.x, f.y+.5),
        (SourceWalkHint((f.x, f.y), (f.x, f.y+.5)),))
    r.prepare_route(guide)
    advance(f, lambda:r.phase == 'route_ready')
    budget.advance(budget.stage, 'walking', zone_id=54)
    assert r.fresh_fit() is r.calibration['estimate']
    assert r.expires_at == budget.expires_at
    f.now = budget.expires_at+.001
    with pytest.raises(ValueError): r.prepare_route(None)
    assert r.phase == 'stopped' and not budget.valid


@pytest.mark.parametrize('runtime', ['budget'], indirect=True)
def test_retired_bootstrap_stage_cannot_issue_destination_observations(runtime):
    f = runtime; r = f.runtime; budget = f.budget
    budget.advance(budget.stage, 'walking', zone_id=54)
    with pytest.raises(ValueError): r.tick()
    assert r.phase == 'stopped' and not budget.valid and not f.sent and not f.movements
