"""Synthetic bounds and surfaces; no client input or measurement claims."""
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from eql_automation.bsp_volume import BspVolumeView
from eql_automation.fixed_route_follower import RouteHalt
from eql_automation.ground_sweep_view import GroundSweepView
from eql_automation.portal_precision import SourceFace
from eql_automation.route_geometry import RouteGeometryPreparer, RouteMotionBounds
from test_route_floor_commit import legacy, setup, receipt
from test_ground_observer import GEOMETRY, rectangle


def build(legacy, *, wall=False, water=False, bounds_changes=None, clock=None):
    f = setup(legacy, clock=clock)
    ground = GroundSweepView(np.asarray(rectangle(0., 2.) + rectangle(2., 4.)),
        np.asarray((0, 0, 1, 1)), np.asarray((63, 63)), np.asarray((7, 7)))
    ground.mesh_sha256 = GEOMETRY.mesh_sha256
    source = SimpleNamespace(ground=ground, seams=(), by_polygon={},
        mesh_sha256=GEOMETRY.mesh_sha256, archive_sha256=GEOMETRY.source_archive_sha256,
        wld_sha256=GEOMETRY.source_wld_sha256, source_faces_for_footprint=lambda _: f.sources)
    faces = (SourceFace(((1., 1.5, 0.), (3., 1.5, 0.), (2., 1.5, 10.)),
                       16, 'TransparentMasked', 101, 0),) if wall else ()
    static = SimpleNamespace(inventory_sha256='d'*64, faces_for_footprint=lambda _: faces)
    bsp = BspVolumeView(SimpleNamespace(nodes=((0., 0., 0., 0., 1, 0, 0),),
        labels_by_region={0: {'water'}} if water else {}), region_count=1,
        wld_sha256=GEOMETRY.source_wld_sha256)
    bounds = RouteMotionBounds('synthetic-envelope', f.runner.calibration,
        .01, .03, .1, 10., .4, .02, 2., .01, .1, 8.)
    if bounds_changes: bounds = replace(bounds, **bounds_changes)
    prepare = RouteGeometryPreparer(f.ledger, ground=ground, source=source,
        static=static, bsp=bsp, bounds=bounds, static_inventory_sha256='d'*64,
        vertical_window=1., maximum_source_z_difference=1.)
    f.prepare, f.scene = prepare, SimpleNamespace(reference_fix=f.reference)
    return f


def stage(f):
    f.prepare.precompute(f.scene)
    return f.prepare(f.runner.propose(f.clock()), f.scene)


def test_complete_checks_cover_actual_hold_and_bind_to_ticket(legacy):
    f = build(legacy); before = f.chain.previous
    ticket = stage(f); record = f.prepare.record_for(ticket)
    assert all(x.candidate for x in (record.terrain, record.static, record.bsp))
    assert not record.input_authorized and not record.real_client_accepted
    assert record.bsp.geometry_sha256 == ticket.preparation.geometry_sha256
    # Requested travel is at most .3, but the footprint covers 1.0 plus body/drift.
    assert ticket.preparation.requested_seconds <= .03
    assert max(p[0] for p in ticket.preparation.footprint) > 2.1
    assert f.chain.previous is before
    with pytest.raises((RouteHalt, ValueError)):
        f.prepare.record_for(replace(ticket))


@pytest.mark.parametrize('hazard', ['wall', 'water'])
def test_hazard_refuses_without_floor_commit(legacy, hazard):
    f = build(legacy, **{hazard: True}); before = f.chain.previous
    with pytest.raises(ValueError, match='Static geometry|BSP volume'):
        stage(f)
    assert f.ledger.chain.previous is before and f.runner.steps == 0
    assert f.ledger._pending is None and f.prepare._record is None


def test_pivot_encloses_lateral_displacement_and_still_checks_volume(legacy):
    f = build(legacy, bounds_changes={'maximum_requested_hold': .05})
    f.runner.pose.heading = 0.
    ticket = stage(f)
    assert ticket.preparation.movement_key in (105, 106)
    footprint = ticket.preparation.footprint
    assert min(p[0] for p in footprint) < .47
    assert max(p[0] for p in footprint) > 1.53


@pytest.mark.parametrize('changes', [
    {'body_height': 7.}, {'calibration_record_id': 'wrong'},
    {'forward_speed_upper_bound': float('nan')}, {'pivot_displacement_upper_bound': -1.},
    {'maximum_actual_hold': .3}, {'minimum_requested_hold': .04},
])
def test_missing_or_wrong_bounds_refuse(legacy, changes):
    with pytest.raises(ValueError): build(legacy, bounds_changes=changes)


@pytest.mark.parametrize('change', ['mesh', 'archive', 'wld', 'bsp', 'static'])
def test_changed_source_binding_refuses(legacy, change):
    f = build(legacy); p = f.prepare
    if change == 'mesh': p.ground.mesh_sha256 = 'f'*64
    elif change == 'archive': p.source.archive_sha256 = 'f'*64
    elif change == 'wld': p.source.wld_sha256 = 'f'*64
    elif change == 'bsp': p.bsp.wld_sha256 = 'f'*64
    else: p.static.inventory_sha256 = 'f'*64
    with pytest.raises(ValueError): stage(f)
    assert f.runner.phase == 'halted' and f.ledger._pending is None


def test_slow_check_expires_without_new_timestamp(legacy):
    f = build(legacy); original = f.prepare.static.faces_for_footprint
    def slow(footprint):
        f.state['now'] += .51
        return original(footprint)
    f.prepare.static.faces_for_footprint = slow
    with pytest.raises(ValueError, match='context changed or expired'): stage(f)
    assert f.runner.steps == 0 and f.ledger._pending is None


def test_record_expires_on_receipt_commit(legacy):
    f = build(legacy); ticket = stage(f); result = receipt(ticket)
    # Existing receipt helper's synthetic hold is .022, within this envelope.
    f.state['now'] = result.up_completed_at + .001
    f.ledger.commit(ticket, result)
    with pytest.raises(RouteHalt): f.prepare.record_for(ticket)


def test_record_cannot_be_reinterpreted_with_different_bounds(legacy):
    f = build(legacy); ticket = stage(f)
    f.prepare.bounds = replace(f.prepare.bounds, position_error=.2)
    with pytest.raises(ValueError): f.prepare.record_for(ticket)


@pytest.mark.parametrize('change', ['reference', 'pose', 'chain', 'bounds', 'deadline'])
def test_precomputed_geometry_cannot_survive_changed_context(legacy, change):
    f = build(legacy); f.prepare.precompute(f.scene)
    if change == 'pose': f.runner.pose.heading += .1
    elif change == 'chain': f.chain._selected.clear()
    elif change == 'bounds': f.prepare.bounds = replace(f.prepare.bounds, record_id='changed')
    elif change == 'reference': f.scene.reference_fix = replace(f.reference)
    proposal = f.runner.propose(f.clock())
    if change == 'deadline': f.state['now'] += .06
    with pytest.raises((RouteHalt, ValueError)): f.prepare(proposal, f.scene)
    assert f.ledger._pending is None and f.prepare._cache is None


def test_forward_query_failure_does_not_replace_successful_pivot(legacy):
    f = build(legacy, bounds_changes={'maximum_requested_hold': .05})
    f.runner.pose.heading = 0.
    query = f.prepare.source.source_faces_for_footprint
    def budget(footprint):
        if max(y for x, y in footprint) > 2.8:
            raise ValueError('synthetic complete-source query budget')
        return query(footprint)
    f.prepare.source.source_faces_for_footprint = budget
    ticket = stage(f)
    assert ticket.preparation.movement_key in (105, 106)


def test_other_thread_can_cancel_during_expensive_geometry(legacy):
    import threading
    f = build(legacy)
    stopped = threading.Event()
    def query(_):
        def cancel():
            f.ledger.cancel('owner OFF during geometry')
            stopped.set()
        thread = threading.Thread(target=cancel, daemon=True)
        thread.start()
        assert stopped.wait(.5), 'geometry must not retain the stop lock'
        thread.join()
        return f.sources
    f.prepare.source.source_faces_for_footprint = query
    with pytest.raises(RouteHalt): f.prepare.precompute(f.scene)
    assert f.runner.steps == 0 and f.prepare._cache is None


def test_actual_step_sender_uses_precomputed_checks_on_pipe(legacy):
    import os
    import time
    from eql_automation.g2_pulse_budget import G2Scene
    from eql_automation.route_step_sender import RouteStepScene, RouteStepAuthorization, run_checked_route_step
    from eql_automation.uinput_watchdog import _EVENT
    from test_route_step_sender import PipeSender
    f = build(legacy, clock=time.monotonic)
    rd, wr = os.pipe()
    sender = PipeSender(wr)
    def scene():
        raw = f.reference.raw_fix
        return RouteStepScene(f.reference, G2Scene(time.monotonic(), f.runner.route.zone,
            raw.raw_coordinates, raw.log_epoch, raw.log_line_seq, raw.zone_generation,
            True, True, True, True, True, True, True))
    def authorize(ticket, observed):
        checked = f.prepare.record_for(ticket)
        assert all(x.candidate for x in (checked.terrain, checked.static, checked.bsp))
        return RouteStepAuthorization(ticket, observed.reference_fix, time.monotonic(),
            ticket.preparation.proposal.at + .05, 'SYNTHETIC-pipe-guard')
    try:
        result = run_checked_route_step(sender, f.ledger, scene_provider=scene,
            prepare_step=f.prepare, authorize_step=authorize, still_authorized=lambda *_: True,
            command_state_clear=lambda: True, pump=lambda: None)
        assert f.runner.steps == 1 and f.ledger.chain.index == 2
        assert result.real_client_accepted is False and not sender.held
        assert f.prepare._cache is None
    finally:
        os.close(wr)
        data = os.read(rd, 65536)
        os.close(rd)
    events = [(kind, key, value) for _, _, kind, key, value in _EVENT.iter_unpack(data)]
    assert (1, 103, 1) in events and (1, 103, 0) in events
