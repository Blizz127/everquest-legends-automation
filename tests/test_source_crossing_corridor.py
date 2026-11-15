"""OS-pipe watchdog and synthetic-log tests for SourceCrossingCorridor."""
from dataclasses import replace
from datetime import datetime, timedelta
import os
import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest

from eql_automation.bsp_volume import BspVolumeView
from eql_automation.fixed_route_follower import RouteHalt
from eql_automation.portal_precision import SourceFace
from eql_automation.current_route_start import CurrentStartPlanner
from eql_automation.current_source_itinerary import plan_current_source_itinerary
from eql_automation.g2_safety_provider import GameWindowIdentity
from eql_automation.motion_collection import CommandReceipt, LocationRequest
from eql_automation.native_crossing_policy import NativeCrossingRegionPolicy, check_source_crossing_cell
from eql_automation.native_region_policy import NativeZeroRegionTrialPolicy
from eql_automation.observed_height import measure_current_height
from eql_automation.owner_input_observer import OwnerInputObservation
from eql_automation.owner_zone_tracker import LiveZoneTracker
from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_crossing_corridor import SourceCrossingCorridor
from eql_automation.source_crossing_sender import run_checked_source_crossing_step
from eql_automation.source_itinerary import SourceItineraryGuide, SourceWalkHint
from eql_automation.source_motion import SourceReceiptLedger
from eql_automation.source_observer import SourceItineraryObserver
from eql_automation.source_step_sender import run_checked_source_step
from eql_automation.supervised_corridor import SupervisedCorridorDeclaration
from eql_automation.supervised_route import SupervisedRouteDeclaration
from eql_automation.supervised_source import SupervisedSourcePolicy
from eql_automation.supervised_source_crossing import SupervisedSourceCrossingPolicy
from eql_automation.uinput_watchdog import _EVENT
from eql_automation.zone_line import ExpectedZoneLine
from test_client_classification import leaf, view
from test_current_route_start import WLD, fixture as base_fixture
from test_floor_bootstrap import fresh
from test_installed_region_model import files
from test_route_floor_commit import legacy
from test_route_step_sender import PipeSender, after_down


@pytest.fixture
def h(tmp_path, monkeypatch, legacy):
    model = files(tmp_path, monkeypatch)
    base_dir = tmp_path / 'base'
    base_dir.mkdir()
    f = base_fixture(base_dir)
    old = f.planner
    vertices = ((0., 0., .2), (10., 0., .2), (10., 15., .2), (0., 15., .2))
    old.source.sources = tuple(
        SourceFace(tuple((y, x, z) for x, y, z in points), 0, 'Diffuse', 10, index)
        for index, points in enumerate(((vertices[0], vertices[1], vertices[2]),
                                        (vertices[0], vertices[2], vertices[3])))
    )
    coords = np.asarray([s.vertices_wld for s in old.source.sources])[:, :, [1, 0, 2]]
    old.source.source_minimum = coords.min(axis=1)
    old.source.source_maximum = coords.max(axis=1)
    # Split plane at x_wld = 3.6 (which is y_game = 3.6):
    # y_game < 3.6 -> leaf(1) [region 0, ordinary zero]
    # y_game >= 3.6 -> leaf(3) [region 2, DRNTP00255000001 transition (0x80000000)]
    nodes = ((1., 0., 0., -3.6, 0, 2, 3), leaf(3), leaf(1))
    bsp = BspVolumeView(
        SimpleNamespace(nodes=nodes, labels_by_region={2: {'zoneline'}}),
        region_count=3,
        wld_sha256=WLD,
    )
    classifier = view(nodes, wld_pin=WLD)
    ordinary = NativeZeroRegionTrialPolicy(
        *old.pins, bsp.inventory_sha256,
        classifier.inventory_sha256, classifier, zone='butcher',
    )
    line = ExpectedZoneLine(
        'butcher-gfay-test', 'butcher', old.pins[0],
        old.pins[1], WLD, bsp.inventory_sha256, 'f' * 64,
        'DRNTP00255000001', 2, (1,), (2,),
    )
    crossing_policy = NativeCrossingRegionPolicy(ordinary, line)

    planner = CurrentStartPlanner(
        mesh=old.mesh, ground=old.ground, source=old.source,
        static=old.static, bsp=bsp, zone_short_name='butcher',
        expected_zone_id=68, expected_zone_name='Butcherblock Mountains',
        mesh_sha256=old.pins[0], source_archive_sha256=old.pins[1],
        source_wld_sha256=old.pins[2], static_inventory_sha256=old.pins[3],
        region_policy=ordinary,
    )

    time_state = {'offset': -2.5}
    clock = lambda: time.monotonic() + time_state['offset']
    wall = lambda: datetime.now() + timedelta(seconds=time_state['offset'])

    log = tmp_path / 'eqlog_Probe_private.txt'
    log.touch()
    catalog = tmp_path / 'ZoneNames.txt'
    catalog.write_text('68^Butcherblock Mountains^0^0\n54^The Greater Faydark^0^0\n58^Clan Crushbone^0^0\n')

    def append(body):
        with log.open('a') as out:
            out.write(wall().strftime('[%a %b %d %H:%M:%S %Y] ') + body + '\n')

    state = {'mode': 'measurement', 'generation': 1, 'focus': True, 'active': False, 'cancelled': False, 'ready': False}
    owner = ('synthetic-owner', 42, 10, 100)
    tracker = LiveZoneTracker(
        log, catalog,
        expected_character='Probe', expected_server='private',
        binding_reader=lambda: owner, clock=clock,
    )
    append('You have entered Butcherblock Mountains.')
    tracker.poll()
    lease = tracker.acquire()
    reader = lease.reader

    def pos(x=4.0, y=2.0, z=2.7):
        append(f'Your Location is {y:.6f}, {x:.6f}, {z:.6f}')
        return reader.poll(now=clock())[0]

    bounds = replace(
        f.options['bounds'],
        minimum_requested_hold=.01,
        maximum_requested_hold=.03,
        maximum_actual_hold=.06,
        forward_speed_upper_bound=18.,
        pivot_displacement_upper_bound=.02,
        post_release_drift=.01,
        heading_error_degrees=2.,
        body_radius=.1,
        body_height=6.,
    )
    time_state['offset'] = -2.0
    a0 = pos()
    time_state['offset'] = -1.5
    b0 = pos()
    guide = SourceItineraryGuide(
        'butcher', old.pins[2], old.pins[3], 'e' * 64, .1, 6., (4., 2.2),
        (SourceWalkHint((4., 2.0), (4., 2.2)),),
    )
    options = dict(
        heading=0.,
        motion_record_id='same-session-motion',
        bounds=bounds,
        half_width=.3,
        vertical_window=1.,
        maximum_source_z_difference=1.,
        owner_binding=owner,
        binding_reader=lambda: owner,
        released_at=a0.received_monotonic - .2,
        record_id='crossing-start',
        clock=clock,
        local_wall_clock=wall,
    )
    plan = plan_current_source_itinerary(planner, reader, a0, b0, guide=guide, **options)
    time_state['offset'] = -.9
    a1 = pos()
    time_state['offset'] = -.45
    b1 = pos()
    cal = measure_current_height(
        plan.initial.observer, reader, a1, b1,
        route=plan.initial.route,
        segment_index=0,
        floor_plan=plan.initial,
        owner_binding=owner, binding_reader=lambda: owner,
        clock=clock, record_id='crossing-height',
        released_at=a1.received_monotonic - .2,
        local_wall_clock=wall,
    )
    time_state['offset'] = -.42
    observer = SourceItineraryObserver(
        plan, reader,
        height_calibration=cal,
        binding_reader=lambda: owner,
        mode_reader=lambda: state['mode'],
        generation_reader=lambda: state['generation'],
        generation=1,
        clock=clock,
    )
    stop_lock = threading.RLock()
    ledger = SourceReceiptLedger(
        observer,
        terrain=planner.source, static=planner.static, bsp=planner.bsp,
        bounds=bounds, installed_model=model, legacy=legacy,
        motion=legacy.Motion(run_speed=16., turn_rate=90., right_sign=1, turn_latency=.005, back_speed=0.),
        heading=0., stop_lock=stop_lock,
    )

    # Precompute crossing cells from (4.0, 2.0) -> ... -> (4.0, 4.0) cap BEFORE
    # observing the live start pair so s_second stays <5ms fresh under host load:
    branch = ledger.chain
    cells = []
    for seg_a, seg_b in (((4., 2.0), (4., 2.0)),
                         ((4., 2.0), (4., 2.5)),
                         ((4., 2.5), (4., 3.0)),
                         ((4., 3.0), (4., 3.5)),
                         ((4., 3.5), (4., 4.0)),
                         ((4., 4.0), (4., 4.0))):
        branch, cell = check_source_crossing_cell(
            branch, seg_a, seg_b, radius=.1,
            terrain=planner.source, static=planner.static,
            bsp=planner.bsp, policy=crossing_policy,
        )
        cells.append(cell)
    crossing_cells = tuple(cells)

    window = SimpleNamespace(id=42)
    gate = SimpleNamespace(
        windows=lambda: [window],
        focused_window=lambda: window if state['focus'] else None,
        game_session=lambda: {'pid': 10, 'start_ticks': '100'},
        controls_ready=lambda: state['focus'],
    )

    def sample():
        now = clock()
        return OwnerInputObservation(now, now, 1, True, 1, 0, state['active'], 0, 'synthetic-device')

    owner_input = SimpleNamespace(sample=sample)
    rd, wr = os.pipe()
    sender = PipeSender(wr)

    def check_current():
        if state['cancelled'] or not state['focus']:
            raise ValueError('Owner cancelled or focus lost')

    def release():
        began = clock()
        for k in tuple(sender.held):
            sender.release(k)
        return CommandReceipt(began, clock())

    time_state['offset'] = -.41
    s_first = observer.observe(pos(), checked_chain=ledger.chain)
    time_state['offset'] = 0.0
    s_second = observer.observe(pos(), checked_chain=ledger.chain)
    ledger.start(s_first, s_second, released_at=s_first.raw_fix.received_monotonic - .2)

    corridor = SourceCrossingCorridor(
        ledger, crossing_policy, crossing_cells, lease, 'The Greater Faydark',
        release_controls=release,
        ready_for_location=lambda: state['ready'],
        check_current=check_current,
        maximum_source_seconds=60.,
        local_wall_clock=wall,
    )
    declaration = SupervisedCorridorDeclaration(
        line.crossing_id, corridor.corridor_sha256,
        bounds.calibration_record_id, bounds.record_id,
        True, 60., 16, 20., 2.,
        expected_zone_line_sha256=line.sha256,
        destination='The Greater Faydark',
    )
    policy = SupervisedSourceCrossingPolicy(
        corridor,
        declaration=declaration,
        gate=gate,
        owner_input=owner_input,
        expected_window=GameWindowIdentity(42, 10, 100),
        topology_generation=1,
        check_current=check_current,
    )

    def step():
        try:
            cmd = corridor.next_command()
            return run_checked_source_crossing_step(
                sender, corridor, policy=policy,
                kind=cmd.kind, requested_seconds=cmd.requested_seconds,
                command_state_clear=lambda: True, pump=lambda: None,
            )
        except Exception as error:
            error.add_note('Crossing refusal: ' + corridor.reason)
            raise

    ns = SimpleNamespace(
        clock=clock, wall=wall, offset=time_state, state=state,
        append=append, lease=lease, tracker=tracker,
        planner=planner, ledger=ledger, observer=observer,
        crossing_policy=crossing_policy, crossing_cells=crossing_cells,
        corridor=corridor, policy=policy, sender=sender,
        owner_input=owner_input, gate=gate, plan=plan,
        rd=rd, wr=wr, step=step,
    )
    yield ns
    lease.release()
    tracker.close()
    os.close(wr)
    data = b''
    while part := os.read(rd, 4096):
        data += part
    os.close(rd)
    events = [(kind, key, value) for _, _, kind, key, value in _EVENT.iter_unpack(data)]
    assert not sender.held
    if any(kind == 1 and value == 1 for kind, key, value in events):
        assert events[-1] == (0, 0, 0) and events[-2][0] == 1 and events[-2][2] == 0


def wait_until(h, at):
    time.sleep(max(0., at - h.clock()) + .002)


def collect_source_pair(h, *, loading_on_second=False):
    before_xy = h.corridor.reference.package_xyz[:2]
    dy = h.corridor.motion.run_speed * h.corridor.receipt.maximum_held_seconds
    y_new = before_xy[1] + dy
    wait_until(h, h.corridor.quiet_until)
    for idx in range(2):
        req = h.corridor.tick()
        assert isinstance(req, LocationRequest)
        h.corridor.command_sent(req, CommandReceipt(h.clock(), h.clock()))
        if loading_on_second and idx == 1:
            h.append('LOADING, PLEASE WAIT...')
            h.append('You have entered The Greater Faydark.')
        else:
            h.append(f'Your Location is {y_new:.6f}, {before_xy[0]:.6f}, 2.700000')
        assert h.corridor.tick() is None
        if idx == 0:
            time.sleep(.405)
    return y_new


def collect_destination_pair(h):
    h.state['ready'] = True
    h.offset['offset'] += .2
    for idx in range(2):
        req = h.corridor.tick()
        assert isinstance(req, LocationRequest)
        h.corridor.command_sent(req, CommandReceipt(h.clock(), h.clock()))
        h.append('Your Location is -2410.00, 2630.00, 5.00')
        assert h.corridor.tick() is None
        if idx == 0:
            h.offset['offset'] += .41
    assert h.corridor.phase == 'complete'


def test_dry_approach_then_transition_pulse_to_destination_arrival(h, monkeypatch):
    initial_chain_snap = _chain_snapshot(h.corridor.chain)
    # Pulse 1 from y=2.0: dry approach (does not yet reach y>=3.2), does NOT commit on release:
    r1 = h.step()
    assert r1['outcome'] == 'settling'
    assert not r1['touches_line']
    assert not r1['source_floor_committed']
    assert _chain_snapshot(h.corridor.chain) == initial_chain_snap
    assert h.corridor.steps == 0

    y1 = collect_source_pair(h)
    assert h.corridor.phase == 'ready' and h.corridor.steps == 1
    assert y1 > 2.0

    # Advance until y >= 2.45 so the next maximum-hold envelope overlaps y >= 3.6,
    # then trigger LOADING during DOWN:
    while h.corridor.reference.package_xyz[1] < 2.45:
        res = h.step()
        assert res['outcome'] == 'settling'
        collect_source_pair(h)

    steps_before_loading = h.corridor.steps
    snap_before_loading = _chain_snapshot(h.corridor.chain)
    after_down(monkeypatch, lambda: h.append('LOADING, PLEASE WAIT...'))
    final_res = h.step()
    assert final_res['outcome'] == 'await_arrival'
    assert final_res['touches_line'] is True
    assert final_res['source_floor_committed'] is False
    assert h.corridor.steps == steps_before_loading
    assert _chain_snapshot(h.corridor.chain) == snap_before_loading
    assert h.ledger.phase == 'stopped'

    h.append('You have entered The Greater Faydark.')
    h.corridor.tick()
    collect_destination_pair(h)
    assert h.corridor.arrival.collector.second.zone_id == 54
    assert h.corridor.arrival.collector.second.zone_display_name == 'The Greater Faydark'
    assert not h.corridor.snapshot()['real_client_accepted']


def test_loading_during_source_pair_discards_provisional_seal(h):
    while h.corridor.reference.package_xyz[1] < 2.45:
        h.step()
        collect_source_pair(h)

    steps_before = h.corridor.steps
    res = h.step()
    assert res['touches_line'] is True and res['outcome'] == 'settling'
    assert h.corridor.quiet_until == pytest.approx(h.corridor.receipt.up_completed_at + 2.5)
    # Simulate clock advancing past 2.5s quiet window, then LOADING during source pair:
    h.offset['offset'] += 2.55
    before_xy = h.corridor.reference.package_xyz[:2]
    y_new = before_xy[1] + h.corridor.motion.run_speed * h.corridor.receipt.maximum_held_seconds
    req1 = h.corridor.tick()
    assert isinstance(req1, LocationRequest)
    h.corridor.command_sent(req1, CommandReceipt(h.clock(), h.clock()))
    h.append(f'Your Location is {y_new:.6f}, {before_xy[0]:.6f}, 2.700000')
    assert h.corridor.tick() is None
    h.offset['offset'] += .42
    req2 = h.corridor.tick()
    assert isinstance(req2, LocationRequest)
    h.corridor.command_sent(req2, CommandReceipt(h.clock(), h.clock()))
    h.append('LOADING, PLEASE WAIT...')
    h.append('You have entered The Greater Faydark.')
    assert h.corridor.tick() is None
    assert h.corridor.phase == 'await_arrival'
    assert h.corridor.seal is None and h.corridor.steps == steps_before
    collect_destination_pair(h)


def test_uncorrelated_loading_on_dry_pulse_refuses_immediately(h, monkeypatch):
    # At y=2.0, pulse does NOT touch y>=3.6; LOADING must be refused as uncorrelated:
    after_down(monkeypatch, lambda: h.append('LOADING, PLEASE WAIT...'))
    with pytest.raises((ValueError, RuntimeError)):
        h.step()
    assert h.corridor.phase == 'stopped'
    assert h.corridor.steps == 0


@pytest.mark.parametrize('cause', ['owner', 'policy', 'mode', 'lease', 'hazard'])
def test_during_down_cancellation_stops_without_floor_commit(h, monkeypatch, cause):
    snap = _chain_snapshot(h.corridor.chain)

    def trigger():
        if cause == 'owner':
            h.state['cancelled'] = True
        elif cause == 'policy':
            h.policy.cancel('F9')
        elif cause == 'mode':
            h.state['mode'] = 'assist'
        elif cause == 'lease':
            h.lease.release()
        else:
            h.append('a goblin hits YOU for 4 points of damage.')

    after_down(monkeypatch, trigger)
    with pytest.raises((ValueError, RuntimeError)):
        h.step()
    assert h.corridor.phase == 'stopped'
    assert h.corridor.steps == 0
    assert _chain_snapshot(h.corridor.chain) == snap


def test_strict_type_separation_from_ordinary_source_sender(h):
    with pytest.raises(ValueError, match='Exact source ledger'):
        run_checked_source_step(
            h.sender, h.corridor, policy=h.policy,
            kind='forward', requested_seconds=.02,
            command_state_clear=lambda: True, pump=lambda: None,
        )
    # Also verify underlying ledger cannot run an ordinary step while leased by corridor:
    with pytest.raises((ValueError, RouteHalt)):
        h.ledger.prepare('forward')


def test_reaching_corridor_end_without_loading_refuses_cleanly(h):
    # Advance onto the final leg (y >= 3.52) so reaching y = 4.0 stays on its planned leg,
    # run a pulse without LOADING, then report a stopped source-zone pair at the corridor end (4.0, 4.0):
    while h.corridor.reference.package_xyz[1] < 3.52:
        h.step()
        collect_source_pair(h)

    res = h.step()
    assert res['touches_line'] is True and res['outcome'] == 'settling'
    h.offset['offset'] += 2.55
    req1 = h.corridor.tick()
    assert isinstance(req1, LocationRequest)
    h.corridor.command_sent(req1, CommandReceipt(h.clock(), h.clock()))
    h.append('Your Location is 4.000000, 4.000000, 2.700000')
    assert h.corridor.tick() is None
    h.offset['offset'] += .42
    req2 = h.corridor.tick()
    assert isinstance(req2, LocationRequest)
    h.corridor.command_sent(req2, CommandReceipt(h.clock(), h.clock()))
    h.append('Your Location is 4.000000, 4.000000, 2.700000')
    with pytest.raises((ValueError, RouteHalt), match='ended without expected loading|exceeded'):
        h.corridor.tick()
        h.corridor.next_command()
    assert h.corridor.phase == 'stopped'

