"""Fresh destination bootstrap using real contracts and synthetic copied views."""
from dataclasses import replace
import json
from pathlib import Path
import threading

import pytest

from eql_automation.camp_probe_floor import camp_floor_anchor, assert_camp_ancestry
from eql_automation.camp_probe_preparation import CampProbePreparation
from eql_automation.camp_probe_transaction import CampProbeTransaction
from eql_automation.camp_stopped_height import measure_camp_stopped_height
from eql_automation.destination_floor_bootstrap import (
    DestinationFloorBootstrap, DestinationFloorCheckpoint,
)
from eql_automation.native_region_policy import encoded
from eql_automation.owner_zone_tracker import LiveZoneTracker
from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.uinput_watchdog import PulseReceipt
from test_installed_region_model import files
from test_native_region_policy import setup


@pytest.fixture
def destination(tmp_path, monkeypatch):
    f = setup(tmp_path, zone='gfaydark', native_zone='gfaydark', zone_id=54)
    f.planner.installed_region_model = files(tmp_path, monkeypatch)
    tracker = LiveZoneTracker(f.reader.tail.path, tmp_path/'ZoneNames.txt',
        expected_character='Probe', expected_server='private',
        binding_reader=lambda: f.owner, clock=f.clock)
    tracker.reader = f.reader
    f.lease = tracker.acquire()
    f.generation = 0
    f.binding_hook = lambda: None
    def binding():
        f.binding_hook()
        return f.owner
    f.binding = binding
    f.bounds = replace(f.options['bounds'], forward_speed_upper_bound=10.)
    f.basis = encoded(dict(kind='independent_destination_hypotheses',
                          source_zone_calibration_reused=False))
    def bootstrap():
        return DestinationFloorBootstrap(f.planner, f.lease,
            bounds=f.bounds, bounds_basis=f.basis, owner_binding=f.owner,
            binding_reader=f.binding, generation=f.generation,
            generation_reader=lambda:f.generation, record_id='fresh-gfay-destination',
            clock=f.clock, local_wall_clock=f.wall, maximum_seconds=120.)
    f.make_bootstrap = bootstrap
    f.bootstrap = bootstrap()
    def position(*, x=4., y=2., z=2.7):
        f.append(f'Your Location is {y:.2f}, {x:.2f}, {z:.2f}')
        return f.reader.poll(now=f.now)[0]
    f.position = position
    return f


def pair(f, **position):
    baseline, released = f.reader.log_line_seq, f.now
    f.now += .2
    first = f.position(**position)
    f.now += .5
    second = f.position(**position)
    return first, second, dict(minimum_log_seq=baseline, released_at=released)


def prepared(f):
    a, b, args = pair(f)
    f.bootstrap.prepare(a, b, **args)
    return a, b, args


def captured(f):
    prepared(f)
    a, b, args = pair(f)
    return f.bootstrap.capture(a, b, **args)


def test_claim_is_fresh_destination_floor_without_old_motion_or_input(destination):
    f = destination
    old_pair = prepared(f)
    p = f.bootstrap
    assert p.phase == 'prepared'
    assert p._envelope.source_reference == (4., 2., .2)
    assert p._envelope.reference == (4., 2., .6)
    proof = _chain_snapshot(p._envelope.floor_chain)
    a, b, args = pair(f)
    root = p.capture(a, b, **args)
    assert type(root) is DestinationFloorCheckpoint and p.phase == 'claimed'
    anchor, raw, xyz = camp_floor_anchor(root)
    assert raw is b and xyz == (4., 2., .2)
    assert anchor.raw_z_minus_source_z == 2.5
    assert root._chain is not p._envelope.floor_chain
    assert _chain_snapshot(root._chain)[1:] == proof[1:]
    assert not hasattr(root, '_calibration')
    assert root.snapshot(include_evidence=True)['evidence']['source_zone_state_reused'] is False
    assert not root.snapshot()['input_authorized']
    # This is historical ancestry; later log entries do not renew the anchor.
    expiry = anchor.expires_at
    f.now += 5.
    f.position(x=4.3)
    root.check()
    assert anchor.expires_at == expiry < f.now
    assert_camp_ancestry(root)
    assert old_pair[1].received_monotonic < anchor.first.received_monotonic
    with pytest.raises(ValueError, match='Unclaimed'):
        p.capture(a, b, **args)
    root.check()


def test_slow_planning_requires_new_pair_and_preserves_fixed_deadline(destination):
    f = destination
    deadline = f.bootstrap.expires_at
    original = f.planner.source.source_faces_for_footprint
    first_query = []
    def slow(footprint):
        if not first_query:
            first_query.append(True)
            f.now += 1.
        return original(footprint)
    # Changing the provider before construction is permitted; it is pinned.
    f.planner.source.source_faces_for_footprint = slow
    f.bootstrap.cancel('replace the unused scope with the deliberately slow provider')
    f.bootstrap = f.make_bootstrap()
    a, b, args = prepared(f)
    assert f.now > b.received_monotonic + .5
    a, b, args = pair(f)
    root = f.bootstrap.capture(a, b, **args)
    assert root._anchor.expires_at == b.received_monotonic + .5
    assert f.bootstrap.expires_at == deadline


@pytest.mark.parametrize('fault', ('old_pair', 'shift', 'height', 'stale', 'sequence',
    'extra_reply', 'early_release', 'backdated_release', 'zone_fix'))
def test_capture_refuses_nonmatching_or_unowned_pair(destination, fault):
    f = destination
    old_a, old_b, old_args = prepared(f)
    a, b, args = pair(f, x=4.01 if fault == 'shift' else 4., z=2.71 if fault == 'height' else 2.7)
    if fault == 'old_pair':
        a, b, args = old_a, old_b, old_args
        f.reader.latest, f.reader.log_line_seq = b, b.log_line_seq
    elif fault == 'stale': f.now += .51
    elif fault == 'sequence': a = replace(a, log_line_seq=a.log_line_seq-1)
    elif fault == 'extra_reply': f.position()
    elif fault == 'early_release': args['released_at'] = a.received_monotonic
    elif fault == 'backdated_release': args['released_at'] = f.bootstrap.prepared_at-.01
    elif fault == 'zone_fix': a = replace(a, zone_id=58)
    with pytest.raises(ValueError):
        f.bootstrap.capture(a, b, **args)
    assert f.bootstrap.phase == 'stopped' and f.bootstrap._checkpoint is None


@pytest.mark.parametrize('fault', ('owner', 'generation', 'generation_bool', 'lease', 'epoch', 'zone', 'catalog',
    'source', 'query', 'bounds', 'clock', 'deadline', 'envelope', 'replaced_envelope',
    'evidence', 'planning_pair', 'prepared_time', 'offset', 'model'))
def test_prepared_scope_and_geometry_mutations_refuse(destination, fault):
    f = destination
    prepared(f)
    p = f.bootstrap
    if fault == 'owner': f.owner = ('other',)
    elif fault == 'generation': f.generation += 1
    elif fault == 'generation_bool': f.generation = False
    elif fault == 'lease': f.lease.release()
    elif fault == 'epoch': f.reader.tail.epoch += 1
    elif fault == 'zone': f.reader.zone_generation += 1
    elif fault == 'catalog': f.reader.zone_ids['Fixture'] = 58
    elif fault == 'source': f.planner.source.wld_sha256 = 'f'*64
    elif fault == 'query': f.planner.source.source_faces_for_footprint = lambda _: ()
    elif fault == 'bounds': p.bounds = replace(p.bounds, body_height=7.)
    elif fault == 'clock': f.now -= .01
    elif fault == 'deadline': f.now = p.expires_at+.01
    elif fault == 'envelope': p._envelope.floor_chain.seed_evidence_sha256 = 'f'*64
    elif fault == 'replaced_envelope': p._envelope = replace(p._envelope)
    elif fault == 'evidence': object.__setattr__(p._envelope, 'evidence_bytes', b'{}')
    elif fault == 'planning_pair': p._planning_pair = (replace(p._planning_pair[0]), p._planning_pair[1])
    elif fault == 'prepared_time': p.prepared_at -= 1.
    elif fault == 'offset': p._planning_offset += .01
    elif fault == 'model': Path(f.planner.installed_region_model.game_dir, 'eqgame.exe').write_bytes(b'changed')
    with pytest.raises((ValueError, OSError)):
        p.check()
    assert p.phase == 'stopped'


@pytest.mark.parametrize('where', ('planning', 'capture_model', 'capture_binding'))
def test_reentrant_cancel_never_publishes_checkpoint(destination, monkeypatch, where):
    f = destination
    p = f.bootstrap
    if where != 'planning': prepared(f)
    if where == 'capture_model':
        model_type = type(p.model)
        original = model_type.check_policy
        def stop_model(model, policy):
            original(model, policy)
            if p.phase == 'capturing': p.cancel('F9 in destination model check')
        monkeypatch.setattr(model_type, 'check_policy', stop_model)
    elif where == 'capture_binding':
        def cancel():
            if p.phase == 'capturing': p.cancel('F9 before publication')
        f.binding_hook = cancel
    else:
        f.binding_hook = lambda: p.cancel('F9 during geometry') if p.phase == 'preparing' else None
    a, b, args = pair(f)
    with pytest.raises(ValueError):
        (p.prepare if where == 'planning' else p.capture)(a, b, **args)
    assert p.phase == 'stopped'
    assert p._checkpoint is None or not p._checkpoint.valid


@pytest.mark.parametrize('fault', ('owner', 'generation', 'stale', 'cancel'))
def test_final_wall_callback_cannot_publish_revoked_or_expired_capture(destination, fault):
    f = destination
    original_wall = f.wall
    def wall():
        if f.bootstrap.phase == 'claimed':
            if fault == 'owner': f.owner = ('other',)
            elif fault == 'generation': f.generation += 1
            elif fault == 'stale': f.now += .51
            else: f.bootstrap.cancel('F9 at final wall observation')
        return original_wall()
    f.bootstrap.cancel('replace unused scope with callback fixture')
    f.wall = wall
    f.bootstrap = f.make_bootstrap()
    prepared(f)
    a, b, args = pair(f)
    with pytest.raises(ValueError): f.bootstrap.capture(a, b, **args)
    assert f.bootstrap.phase == 'stopped'
    assert f.bootstrap._checkpoint is None or not f.bootstrap._checkpoint.valid


def test_model_mutation_during_real_geometry_refuses_before_preparation(destination):
    f = destination
    original = f.planner.source.source_faces_for_footprint
    def changed(footprint):
        result = original(footprint)
        Path(f.planner.installed_region_model.game_dir, 'eqgame.exe').write_bytes(b'changed during query')
        return result
    f.bootstrap.cancel('replace unused scope with callback fixture')
    f.planner.source.source_faces_for_footprint = changed
    f.bootstrap = f.make_bootstrap()
    a, b, args = pair(f)
    with pytest.raises(ValueError, match='Installed region-model file changed'):
        f.bootstrap.prepare(a, b, **args)
    assert f.bootstrap.phase == 'stopped' and f.bootstrap._envelope is None


def test_real_probe_transaction_can_continue_from_destination_root(destination):
    f = destination
    root = captured(f)
    a, b, args = pair(f)
    height = measure_camp_stopped_height(root, f.reader, a, b, **args,
        owner_binding=f.owner, binding_reader=f.binding, clock=f.clock, local_wall_clock=f.wall)
    prep = CampProbePreparation(root, height, f.lease, probe_kind='forward',
        bounds=f.bounds, bounds_basis=f.basis, owner_binding=f.owner,
        binding_reader=f.binding, clock=f.clock, local_wall_clock=f.wall)
    prep.prepare()
    a, b, args = pair(f)
    start = prep.observe_start(a, b, **args)
    tx = CampProbeTransaction(prep, stop_lock=threading.RLock())
    ticket = tx.stage(start, movement_key=103, requested_seconds=.02)
    at = ticket.proposed_at
    f.now = at+.026
    receipt = PulseReceipt(103, .02, at+.001, at+.002, at+.024, at+.025, 'elapsed')
    seal = tx.seal_release(ticket, receipt)
    a, b, _ = pair(f, x=4.2)
    tx.prepare_endpoint(seal, a, b)
    a, b, args = pair(f, x=4.2)
    result = tx.confirm_endpoint(a, b, minimum_log_seq=args['minimum_log_seq'])
    continued = tx.retain_endpoint(result)
    continued.check()
    assert_camp_ancestry(continued)
    assert continued._parent is root
    assert continued._chain.floor_at((4.2, 2.))[0] == .2
    assert json.loads(result.payload)['sender_origin_verified'] is False
    f.generation += 1
    with pytest.raises(ValueError): continued.check()
    assert not root.valid and not continued.valid


def test_unowned_checkpoint_cannot_be_constructed(destination):
    with pytest.raises(ValueError, match='owning'):
        DestinationFloorCheckpoint(destination.bootstrap)
