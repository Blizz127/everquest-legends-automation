"""Completed crossing transfer on real log/arrival objects, with no game input.

The terminal crossing shell is synthetic: only its completed boundary is under
test here. The lease, pair collector, log observers, hotkey binding, descriptor,
runtime checks and transfer implementation are real.
"""
from dataclasses import replace
import os
import threading
from types import SimpleNamespace

import pytest

from eql_automation.camp_floor_checkpoint import CampFloorCheckpoint
from eql_automation.camp_motion_continuity import CampInputContinuity
from eql_automation.g2_safety_provider import GameWindowIdentity
from eql_automation.location_hotkey import OwnerLocationHotkey
from eql_automation.native_region_policy import encoded
from eql_automation.owner_input_observer import OwnerInputObservation
from eql_automation.owner_source_crossing import OwnerSourceCrossingRuntime, PinnedSourceCrossingSpec
from eql_automation.route_step_sender import _fd_identity
from eql_automation.scene_log_veto import SceneLogVeto
from eql_automation.zone_arrival import ZoneArrivalHandoff
from test_itinerary_policy_budget import root_budget
from test_destination_arrival_veto import complete
from test_route_step_sender import PipeSender, read_available
from test_route_floor_commit import legacy
from test_zone_arrival import h


@pytest.fixture
def completed(h, tmp_path, request):
    has_root = getattr(request, 'param', None) == 'root'
    if has_root:
        old = h.session
        h.append('You have entered Butcherblock Mountains.')
        h.lease.reader.poll(now=h.now)
        h.session = ZoneArrivalHandoff(h.lease, 'The Greater Faydark',
            release_controls=old.release_controls, ready_for_location=old.ready_for_location,
            check_current=lambda: h.current(), clock=h.clock, local_wall_clock=h.wall)
        h.append('LOADING, PLEASE WAIT...')
        h.tick()
        h.tick(2)
        h.append('You have entered The Greater Faydark.')
        h.tick()
        h.ready = True
        h.send(h.tick(.13))
        h.tick()
        h.send(h.tick(.41))
        h.tick()
    else:
        complete(h)
    h.generation = 0
    h.focus, h.active = True, False
    h.observer_closed = False
    h.current_hook = h.binding_hook = h.sample_hook = None
    h.owner_binding = ('synthetic-crossing-owner', 0)
    h.old_binding_calls = h.current_calls = 0
    h.rd, h.wr = os.pipe()
    h.sender = PipeSender(h.wr)
    window = SimpleNamespace(id=42)
    h.gate = SimpleNamespace(windows=lambda: [window],
        focused_window=lambda: window if h.focus else None,
        game_session=lambda: dict(pid=10, start_ticks='100'),
        controls_ready=lambda: h.focus)

    def sample():
        if h.sample_hook is not None:
            hook, h.sample_hook = h.sample_hook, None
            hook()
        return OwnerInputObservation(h.now, h.now, 1, True, 1, 0, h.active, 0,
                                     'synthetic transfer observer')

    def close():
        h.observer_closed = True

    h.observer = SimpleNamespace(sample=sample, close=close)
    config = tmp_path/'synthetic-transfer-hotkey.ini'
    config.write_text('Synthetic F1 = /location\n')
    h.hotkey = OwnerLocationHotkey.configured('F1', confirmation_id='synthetic-transfer',
                                             configuration_paths=(config,))
    r = OwnerSourceCrossingRuntime.__new__(OwnerSourceCrossingRuntime)
    h.runtime = r
    r.clock, r.wall = h.clock, h.wall
    r.lease, r.reader = h.lease, h.lease.reader
    r.sender, r.ui = h.sender, h.sender.ui
    r.fd, r.fd_identity = h.wr, _fd_identity(h.wr)
    r.hotkey, r.owner_input, r.topology = h.hotkey, h.observer, 1
    r.gate, r.window = h.gate, GameWindowIdentity(42, 10, 100)
    r.generation, r.generation_reader = 0, lambda: h.generation
    r.lock = threading.RLock()
    r.owner_binding = h.owner_binding

    def binding():
        h.old_binding_calls += 1
        if h.binding_hook is not None:
            hook, h.binding_hook = h.binding_hook, None
            hook()
        return h.owner_binding

    def current():
        h.current_calls += 1
        if h.current_hook is not None:
            hook, h.current_hook = h.current_hook, None
            hook()

    h.current = current
    r.binding_reader = binding
    r.command_clear, r.pump = lambda: True, lambda: None
    r.started, r.last_at, r.expires_at = 100., h.now, h.now+30.
    r._times = r.started, r.expires_at
    r.phase, r.reason, r.closed, r.busy = 'complete', '', False, False
    r.destination_id = 'butcher-gfay-crossing' if has_root else 'gfay-crushbone-crossing'
    r.corridor_spec = SimpleNamespace(destination=h.session.destination,
        destination_zone='gfaydark' if has_root else 'crushbone',
        destination_zone_id=h.session.destination_id,
        zone='butcher' if has_root else 'gfaydark', corridor_file_sha256='a'*64,
        expected_zone_line=SimpleNamespace(sha256='b'*64))
    r.source_zone = (*h.session.source, *h.session.log_binding, h.session.source_generation)
    r.checkpoint = CampFloorCheckpoint.__new__(CampFloorCheckpoint)
    r.checkpoint.valid, r.checkpoint.reason = False, 'source floor discarded at loading'
    r.journey = SimpleNamespace(arrival_floor=None, generation=0, phase='source_crossing')
    r.engine = SimpleNamespace(g0_stop_lock=r.lock, journey=r.journey,
                               cancel_generation=0, source_crossing_run=r)
    r.collector = r.preparation = r.source_observer = r.ledger = r.policy = None
    r.sending_location, r.location_request, r.sending_movement = False, None, None
    r.events, r.observations = [], []
    r.monitor = CampInputContinuity(h.observer, topology=1, basis=encoded({'synthetic': True}),
        binding=r._monitor_binding(), clock=h.clock, floor=r.checkpoint)
    r.corridor = SimpleNamespace(arrival=h.session, phase='complete', reason='',
        corridor_sha256='a'*64, line=SimpleNamespace(sha256='b'*64),
        snapshot=lambda: {'phase': 'complete', 'arrival': h.session.snapshot()},
        cancel=lambda reason: h.session.cancel(reason))
    h.session.check_current = r._check_context
    r.journey_budget = r._journey_root = None
    r._journey_stage = None
    r.startup_veto = SceneLogVeto(h.log, expected_character='Probe', expected_server='private',
                                 cancel_generation=h.generation, clock=h.clock)
    r._startup_veto = (r.startup_veto, r.startup_veto.tail, r.startup_veto.tail.path,
                       r.startup_veto.clock, r.startup_veto.cancel_generation)
    r._destination_transfer = r._destination_transfer_state = None
    r._destination_transfer_pending = r._destination_reader_state = None
    r._destination_transfer_claimed = r._destination_transfer_busy = r._destination_claim_busy = False
    h.root = None
    if has_root:
        h.root = root_budget(clock=h.clock, lock=r.lock, maximum_seconds=20.)
        h.root.advance(h.root.stage, 'crossing', zone_id=68)
        r.journey_budget = r._journey_root = h.root
        r._journey_stage = h.root.stage
        r.expires_at = min(r.expires_at, h.root.expires_at)
        r._times = r.started, r.expires_at
    yield h
    if not r.closed:
        r.cancel('synthetic transfer test cleanup')
        r.release()
    os.close(h.wr)
    os.close(h.rd)


def transfer(h):
    return h.runtime.transfer_destination(check_current=h.current)


def test_completed_transfer_preserves_resources_and_retires_old_runtime(completed):
    h = completed
    r, arrival = h.runtime, h.session
    final = arrival.collector.second
    token = transfer(h)
    assert r.closed and r.phase == 'transferred'
    assert r.monitor.closed and not r.monitor.valid and not h.observer_closed
    assert token.lease is h.lease and token.reader is h.lease.reader
    assert token.sender is h.sender and token.hotkey is h.hotkey
    assert token.owner_input is h.observer and token.generation == h.generation
    assert token.source_generation == arrival.source_generation
    assert token.first is arrival.collector.first and token.second is final
    assert token.reader.latest is final and h.lease.active
    assert type(token.log_veto) is SceneLogVeto
    assert token.expires_at == r.expires_at
    old_calls = h.old_binding_calls
    token.check()
    assert h.old_binding_calls == old_calls
    token.claim()
    with pytest.raises(ValueError):
        token.claim()
    with pytest.raises(ValueError):
        transfer(h)
    r.cancel('stale old owner cancellation')
    r.release()
    r.tick()
    assert h.lease.active and token.reader.latest is final
    assert not h.observer_closed and not read_available(h)


@pytest.mark.parametrize('body', ['a bat hits YOU for 3 points of damage.',
    'LOADING, PLEASE WAIT...', 'You have entered Clan Crushbone.'])
@pytest.mark.parametrize('when', ['before', 'callback', 'after_transfer'])
def test_transfer_or_claim_never_skips_late_hazard_bytes(completed, body, when):
    h = completed
    if when == 'before':
        h.append(body)
    elif when == 'callback':
        h.current_hook = lambda: h.append(body)
    if when == 'after_transfer':
        token = transfer(h)
        h.append(body)
        with pytest.raises(ValueError):
            token.claim()
    else:
        with pytest.raises((ValueError, RuntimeError)):
            transfer(h)
        assert not h.runtime.closed
        assert h.runtime.phase == 'stopped'
    assert not read_available(h) and not h.sender.held


@pytest.mark.parametrize('change', ['generation', 'owner', 'focus', 'physical_input',
    'reader_generation', 'source_generation', 'reader_latest', 'lease', 'deadline', 'sender'])
@pytest.mark.parametrize('when', ['before_transfer', 'claim_callback'])
def test_changed_destination_binding_cannot_be_adopted(completed, change, when):
    h = completed
    def mutate():
        if change == 'generation':
            h.generation += 1
        elif change == 'owner':
            h.owner = ('different character',)
        elif change == 'focus':
            h.focus = False
        elif change == 'physical_input':
            h.active = True
        elif change == 'reader_generation':
            h.lease.reader.zone_generation += 1
        elif change == 'source_generation':
            h.session.source_generation += 1
        elif change == 'reader_latest':
            h.lease.reader.latest = replace(h.lease.reader.latest, raw_coordinates=(0., 0., 0.))
        elif change == 'lease':
            h.lease.active = False
        elif change == 'deadline':
            h.now = h.runtime.expires_at+1.
        else:
            h.runtime.sender.ui = SimpleNamespace(fileno=lambda: h.wr)
    if when == 'before_transfer':
        mutate()
        with pytest.raises((ValueError, RuntimeError)):
            transfer(h)
    else:
        token = transfer(h)
        h.current_hook = mutate
        with pytest.raises((ValueError, RuntimeError)):
            token.claim()
    assert not read_available(h)


@pytest.mark.parametrize('action', ['F8', 'F9'])
def test_owner_cancel_from_transfer_callback_leaves_normal_cleanup_available(completed, action):
    h = completed
    def stop():
        h.generation += 1
        h.runtime.cancel(action+' during destination transfer')
    h.current_hook = stop
    with pytest.raises(ValueError):
        transfer(h)
    assert h.runtime.phase == 'stopped' and not h.runtime.closed
    h.runtime.release()
    assert h.runtime.closed and not h.lease.active and h.observer_closed
    assert not read_available(h)


@pytest.mark.parametrize('change', ['focus', 'physical_input', 'expiry', 'expiry_and_pin'])
def test_third_transfer_callback_cannot_change_scene_or_extend_deadline(completed, change):
    h = completed
    r = h.runtime
    assert r.journey_budget is None
    original_expiry = r.expires_at
    calls = []
    def independent_current():
        calls.append(True)
        if len(calls) != 3:
            return
        if change == 'focus':
            h.focus = False
        elif change == 'physical_input':
            h.active = True
        else:
            r.expires_at = original_expiry+100.
            if change == 'expiry_and_pin':
                r._times = (r.started, r.expires_at)
    with pytest.raises((ValueError, RuntimeError)):
        r.transfer_destination(check_current=independent_current)
    assert len(calls) >= 3
    assert r.phase == 'stopped' and not r.closed and r._destination_transfer is None
    r.release()
    assert r.closed and not h.lease.active and h.observer_closed
    assert not read_available(h)


@pytest.mark.parametrize('change', ['expiry', 'time_pin', 'expiry_and_pin'])
def test_retired_runtime_deadline_mutation_cannot_extend_pending_claim(completed, change):
    h = completed
    r = h.runtime
    token = transfer(h)
    original_expiry = token.expires_at
    if change in ('expiry', 'expiry_and_pin'):
        r.expires_at = original_expiry+100.
    if change in ('time_pin', 'expiry_and_pin'):
        r._times = (r.started, original_expiry+100.)
    with pytest.raises(ValueError):
        token.claim()
    assert token.expires_at == original_expiry and not r._destination_transfer_claimed
    assert not read_available(h)


def test_copied_token_expiry_cannot_renew_or_consume_original_claim(completed):
    h = completed
    token = transfer(h)
    original_expiry = token.expires_at
    renewed = replace(token, expires_at=original_expiry+100.)
    with pytest.raises(ValueError):
        renewed.claim()
    assert token.expires_at == h.runtime.expires_at == original_expiry
    assert not h.runtime._destination_transfer_claimed
    assert token.claim() is token
    assert not read_available(h)


@pytest.mark.parametrize('change', ['attack', 'loading', 'focus'])
def test_final_claim_callback_cannot_hide_hazard_or_focus_change(completed, change):
    h = completed
    token = transfer(h)
    calls = []
    def second_callback():
        calls.append(True)
        if len(calls) == 2:
            if change == 'focus':
                h.focus = False
            else:
                h.append('LOADING, PLEASE WAIT...' if change == 'loading'
                         else 'a bat hits YOU for 3 points of damage.')
        elif len(calls) < 2:
            h.current_hook = second_callback
    h.current_hook = second_callback
    with pytest.raises((ValueError, RuntimeError)):
        token.claim()
    assert len(calls) == 2 and not h.runtime._destination_transfer_claimed
    assert not read_available(h)


def test_reentrant_claim_cannot_duplicate_ownership(completed):
    h = completed
    token = transfer(h)
    reentered = []
    def reenter():
        with pytest.raises(ValueError, match='claim'):
            token.claim()
        reentered.append(True)
    h.current_hook = reenter
    assert token.claim() is token and reentered == [True]
    with pytest.raises(ValueError, match='claim'):
        token.claim()
    assert h.lease.active and not h.observer_closed and not read_available(h)


def test_reentrant_transfer_cannot_duplicate_destination_observer(completed):
    h = completed
    nested = []
    def reenter():
        with pytest.raises(ValueError, match='transfer'):
            transfer(h)
        nested.append(True)
    h.current_hook = reenter
    token = transfer(h)
    assert nested == [True]
    assert token.log_veto is h.session._destination_log_veto
    assert h.lease.active and not h.observer_closed and not read_available(h)


def test_benign_bytes_between_arrival_and_transfer_are_observed(completed):
    h = completed
    previous = h.session.veto._line_seq
    h.append('You say, first late line.')
    h.append('You say, second late line.')
    token = transfer(h)
    assert token.log_veto._line_seq == previous+2
    h.append('a bat hits YOU for 3 points of damage.')
    with pytest.raises(ValueError):
        token.claim()
    assert token.log_veto._line_seq == previous+3


@pytest.mark.parametrize('body,reason', [
    ('a bat hits YOU for 3 points of damage.', 'incoming_attack'),
    ('LOADING, PLEASE WAIT...', 'zone_transition'),
])
def test_crossing_observer_setup_cannot_skip_bytes_behind_new_baseline(completed, monkeypatch,
                                                                     body, reason):
    import eql_automation.owner_source_crossing as module
    h = completed
    r, corridor = h.runtime, h.runtime.corridor
    r.ledger = SimpleNamespace(start=lambda *args, **kwargs: None)
    r.source_observer = SimpleNamespace(calibration=SimpleNamespace(valid_until_monotonic=h.now+60.))
    r.collector = SimpleNamespace(released_at=h.now)
    r.walk_half_width, r.crossing_policy, r.crossing_cells = .25, None, ()
    def setup_observer(*args, **kwargs):
        h.append(body)
        return corridor
    monkeypatch.setattr(module, 'SourceCrossingCorridor', setup_observer)
    try:
        with pytest.raises(ValueError, match='observer handoff veto'):
            r._complete_startup_corridor()
        assert r.startup_veto.poll().reason == reason and r.policy is None
        assert not read_available(h)
    finally:
        r.ledger = r.source_observer = r.collector = None


@pytest.mark.parametrize('completed', ['root'], indirect=True)
def test_root_progress_is_evidence_bound_and_transfer_keeps_original_deadline(completed):
    h = completed
    r, root = h.runtime, h.root
    original_expiry = root.expires_at
    assert r.observed_itinerary_phase() == 'arrival'
    assert root.stage.phase == 'crossing'  # Reporting never mutates the root.
    root.advance(root.stage, 'loading', zone_id=None)
    r._check_context()
    root.advance(root.stage, 'arrival', zone_id=54)
    token = transfer(h)
    assert token.journey_budget is root and token.stage is root.stage
    assert token.expires_at == original_expiry == r.expires_at
    root.advance(root.stage, 'bootstrap', zone_id=54)
    token.claim()
    assert root.expires_at == original_expiry and h.lease.active
    assert not h.observer_closed and not read_available(h)


@pytest.mark.parametrize('completed', ['root'], indirect=True)
@pytest.mark.parametrize('missing', ['loading', 'pair', 'current_zone'])
def test_root_stage_cannot_replace_actual_crossing_evidence(completed, missing):
    h = completed
    root = h.root
    root.advance(root.stage, 'loading', zone_id=None)
    if missing == 'loading':
        h.session.loading = None
    else:
        root.advance(root.stage, 'arrival', zone_id=54)
        if missing == 'pair':
            h.session.collector.phase = 'await_location'
        else:
            h.lease.reader.zone_generation += 1
    with pytest.raises(ValueError):
        h.runtime._check_context()
    assert not read_available(h)


@pytest.mark.parametrize('completed', ['root'], indirect=True)
def test_completed_transfer_advances_only_observed_root_boundaries(completed):
    h = completed
    before = h.root.stage
    expiry = h.root.expires_at
    token = transfer(h)
    assert h.root.stage.phase == 'arrival' and h.root.stage.leg_index == before.leg_index
    assert h.root.stage.epoch == before.epoch+2
    assert token.stage is h.root.stage and token.expires_at == expiry
    assert not read_available(h)


@pytest.mark.parametrize('completed', ['root'], indirect=True)
@pytest.mark.parametrize('fault', ['deadline', 'cancel', 'next_leg'])
def test_root_changed_during_pending_destination_claim_is_rejected(completed, fault):
    h = completed
    h.root.advance(h.root.stage, 'loading', zone_id=None)
    h.root.advance(h.root.stage, 'arrival', zone_id=54)
    token = transfer(h)
    if fault == 'deadline':
        h.now = h.root.expires_at+.01
    elif fault == 'cancel':
        h.root.cancel('F9 while destination transfer pending')
    else:
        h.root.advance(h.root.stage, 'bootstrap', zone_id=54)
        h.root.advance(h.root.stage, 'walking', zone_id=54)
    with pytest.raises(ValueError):
        token.claim()
    assert not read_available(h)


@pytest.mark.parametrize('completed', ['root'], indirect=True)
def test_copy_of_original_crossing_stage_does_not_rebind_runtime(completed):
    h = completed
    h.runtime._journey_stage = replace(h.runtime._journey_stage)
    with pytest.raises(ValueError):
        transfer(h)
    assert not h.runtime.closed and not read_available(h)


@pytest.fixture
def crossing_start(tmp_path, monkeypatch, legacy):
    import test_source_crossing_corridor as geometry
    original = geometry.SourceCrossingCorridor
    captured = []
    def capture_before_corridor(ledger, *args, **kwargs):
        # Capture the real historical floor before the corridor exclusively
        # claims this ledger. No phase or private movement state is reset.
        captured.append(CampFloorCheckpoint(ledger))
        return original(ledger, *args, **kwargs)
    monkeypatch.setattr(geometry, 'SourceCrossingCorridor', capture_before_corridor)
    generator = geometry.h.__wrapped__(tmp_path, monkeypatch, legacy)
    result = next(generator)
    result.checkpoint = captured[0]
    yield result
    generator.close()


def constructor_scope(h, tmp_path):
    checkpoint = h.checkpoint
    spec = PinnedSourceCrossingSpec(
        destination_id='butcher-gfay-crossing', zone='butcher',
        destination='The Greater Faydark', destination_zone_id=54, destination_zone='gfaydark',
        provenance_sha256='e'*64, start_xy=(4., 2.), transition_endpoint=(4., 4.),
        cell_segments=(((4., 2.), (4., 2.)), ((4., 2.), (4., 2.5)),
            ((4., 2.5), (4., 3.)), ((4., 3.), (4., 3.5)),
            ((4., 3.5), (4., 4.)), ((4., 4.), (4., 4.))),
        expected_zone_line=h.corridor.line, corridor_file_sha256='a'*64,
        source_evidence=encoded({'synthetic': True}))
    root = root_budget(clock=h.clock, lock=h.ledger.lock,
        first_line_sha256=h.corridor.line.sha256, maximum_seconds=10.)
    root.advance(root.stage, 'crossing', zone_id=68)
    engine = SimpleNamespace(g0_stop_lock=h.ledger.lock)
    journey = SimpleNamespace(arrival_floor=checkpoint)
    config = tmp_path/'constructor-hotkey.ini'
    config.write_text('Synthetic F1 = /location\n')
    hotkey = OwnerLocationHotkey.configured('F1', confirmation_id='synthetic-root-constructor',
                                           configuration_paths=(config,))
    closed = []
    h.owner_input.close = lambda: closed.append(True)
    options = dict(
        destination_id=spec.destination_id, corridor_spec=spec, checkpoint=checkpoint,
        motion_basis=encoded({'synthetic': True}), motion=h.ledger.motion,
        heading=0., bounds=h.ledger.bounds, legacy=h.ledger.legacy, lease=h.lease,
        sender=h.sender, hotkey=hotkey, owner_input=h.owner_input, topology=1,
        gate=h.gate, window=GameWindowIdentity(42, 10, 100), released_at=h.clock()-.2,
        owner_binding=h.lease.owner_binding, binding_reader=lambda: h.lease.owner_binding,
        generation_reader=lambda: h.state['generation'], pump=lambda: None,
        command_state_clear=lambda: True, clock=h.clock, local_wall_clock=h.wall,
        journey_budget=root)
    return engine, journey, root, closed, options


@pytest.mark.parametrize('invalid', [None, 'root_duck', 'veto_duck', 'expected_transition_veto'])
def test_real_crossing_constructor_checks_exact_providers_and_root_deadline(crossing_start, tmp_path, invalid):
    h = crossing_start
    engine, journey, root, closed, options = constructor_scope(h, tmp_path)
    if invalid is not None:
        if invalid == 'root_duck':
            options['journey_budget'] = SimpleNamespace(clock=h.clock, lock=h.ledger.lock)
        elif invalid == 'veto_duck':
            options['log_veto'] = SimpleNamespace(clock=h.clock, tail=h.lease.reader.tail)
        else:
            options['log_veto'] = h.corridor.arrival.veto
        with pytest.raises(ValueError):
            OwnerSourceCrossingRuntime(engine, journey, **options)
        assert h.lease.active and not closed and not read_available(h)
        return
    runtime = OwnerSourceCrossingRuntime(engine, journey, **options)
    try:
        assert runtime.journey_budget is root and runtime._journey_stage is root.stage
        assert runtime.expires_at == root.expires_at
        assert runtime.observed_itinerary_phase() == 'crossing'
        assert root.stage.phase == 'crossing'
        assert not read_available(h)
    finally:
        runtime.cancel('synthetic constructor test cleanup')
        runtime.release()
    assert closed == [True] and not h.lease.active


def test_constructor_retains_inherited_log_observer_and_appended_bytes(crossing_start, tmp_path):
    h = crossing_start
    engine, journey, root, closed, options = constructor_scope(h, tmp_path)
    inherited = SceneLogVeto(h.lease.reader.tail.path, expected_character='Probe',
        expected_server='private', cancel_generation=h.state['generation'], clock=h.clock)
    tail, sequence = inherited.tail, inherited._line_seq
    h.append('You say, appended after inherited observer baseline.')
    options['log_veto'] = inherited
    runtime = OwnerSourceCrossingRuntime(engine, journey, **options)
    try:
        assert runtime.startup_veto is inherited and runtime.startup_veto.tail is tail
        assert inherited._line_seq == sequence+1
        assert inherited.tail.position == h.lease.reader.tail.path.stat().st_size
        assert not inherited.poll().reason and not read_available(h)
    finally:
        runtime.cancel('synthetic inherited observer cleanup')
        runtime.release()
    assert closed == [True] and not h.lease.active


@pytest.mark.parametrize('pre_latched', [False, True])
def test_constructor_rejects_attack_after_inherited_baseline_without_reset(crossing_start, tmp_path,
                                                                        pre_latched):
    h = crossing_start
    engine, journey, root, closed, options = constructor_scope(h, tmp_path)
    inherited = SceneLogVeto(h.lease.reader.tail.path, expected_character='Probe',
        expected_server='private', cancel_generation=h.state['generation'], clock=h.clock)
    sequence = inherited._line_seq
    h.append('a bat hits YOU for 3 points of damage.')
    before = inherited.poll() if pre_latched else None
    options['log_veto'] = inherited
    with pytest.raises(ValueError, match='hazard'):
        OwnerSourceCrossingRuntime(engine, journey, **options)
    observed = inherited.poll()
    assert observed.reason == 'incoming_attack' and inherited._line_seq == sequence+1
    assert observed is inherited._latched
    if pre_latched:
        assert observed is before
    assert closed == [True] and not h.lease.active and not root.valid
    assert not read_available(h)


def test_already_stopped_crossing_releases_keys_despite_cancelled_root(crossing_start, tmp_path):
    h = crossing_start
    engine, journey, root, closed, options = constructor_scope(h, tmp_path)
    runtime = OwnerSourceCrossingRuntime(engine, journey, **options)
    try:
        runtime.phase = 'stopped'
        root.cancel('F9 root cancellation already handled')
        h.sender.held.update({103, 105})
        receipt = runtime._release_controls()
        assert receipt.started_at <= receipt.completed_at <= h.clock()
        assert not h.sender.held and h.sender.release_calls == 2
        events = read_available(h)
        assert sorted(event for event in events if event[0] == 1) == [(1, 103, 0), (1, 105, 0)]
        assert not any(event[0] == 1 and event[2] == 1 for event in events)
    finally:
        runtime.release()
    assert closed == [True] and not h.lease.active
