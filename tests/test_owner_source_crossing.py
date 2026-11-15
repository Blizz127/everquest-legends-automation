"""Tests for staged Butcherblock -> GFay crossing assets and OwnerSourceCrossingRuntime."""
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import time
from types import SimpleNamespace

import pytest

from eql_automation.bsp_volume import BspVolumeView
from eql_automation.butcher_assets import DATA_NAME, load_butcher_assets
from eql_automation.camp_floor_checkpoint import CampFloorCheckpoint
from eql_automation.current_route_start import CurrentStartPlanner
from eql_automation.native_crossing_policy import NativeCrossingRegionPolicy, check_source_crossing_cell
from eql_automation.native_region_policy import NativeZeroRegionTrialPolicy, encoded
from eql_automation.owner_section_assets import load_guide_walking_sections
from eql_automation.owner_source_assets import SourceDestinationAssets
from eql_automation.owner_source_crossing import (
    BUTCHER_GFAY_CORRIDOR_SHA256,
    PinnedSourceCrossingSpec,
    load_source_crossing_spec,
)
from eql_automation.route_geometry import RouteMotionBounds
from eql_automation.source_destinations import (
    CARBON_BUTCHER_GFAY_DATA_NAME,
    destination_spec,
    load_source_guide,
    source_data_name,
)
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_itinerary import SourceWalkHint
from eql_automation.source_section_manifest import parse_walking_sections
from eql_automation.source_walk_sections import plan_walk_sections
from eql_automation.zone_line import ExpectedZoneLine
from test_client_classification import leaf, view
from test_installed_region_model import files
from test_motion_collection import retained
from test_owner_journey_runtime import h, start
from test_route_step_sender import after_down

STORE = Path.home() / '.local/share/eql-automation/owner-route-data'


@pytest.mark.parametrize(
    'identifier,mode',
    [('butcher-gfay-preline-stop', 'stop'), ('butcher-gfay-crossing', 'zone_crossing')],
)
def test_staged_butcher_gfay_guides_and_sections_load_with_pinned_hashes(identifier, mode):
    spec = destination_spec(identifier)
    assert source_data_name(identifier) == CARBON_BUTCHER_GFAY_DATA_NAME
    root = STORE / source_data_name(identifier)
    guide = load_source_guide(root, identifier)
    assert spec.zone == guide.zone == 'butcher'
    assert spec.arrival_mode == mode
    assert guide.operations[0].start == (-2069., -298.)
    assert guide.goal == (-3084.646484375, -1328.2936706542969)
    assert len(guide.operations) == 314
    assert all(type(op) is SourceWalkHint for op in guide.operations)

    sections = load_guide_walking_sections(identifier, guide)
    assert sections is not None and len(sections.guides) == 2
    assert sections.guides[0].goal == (-2587.4125, -892.10625)
    assert sections.guides[1].goal == guide.goal


def test_staged_butcher_gfay_corridor_spec_rebuilds_live_crossing_cells_on_butcher_assets():
    corridor = load_source_crossing_spec('butcher-gfay-crossing')
    assert corridor.corridor_file_sha256 == BUTCHER_GFAY_CORRIDOR_SHA256
    assert corridor.destination == 'The Greater Faydark'
    assert corridor.destination_zone == 'gfaydark'
    assert corridor.destination_zone_id == 54
    assert corridor.start_xy == (-3084.646484375, -1328.2936706542969)
    assert corridor.transition_endpoint == (-3093.57493953125, -1322.3650056635743)
    assert len(corridor.cell_segments) == 8

    assets = load_butcher_assets(STORE / DATA_NAME, native_planning=True)
    p = assets.planner
    crossing_policy = NativeCrossingRegionPolicy(p.region_policy, corridor.expected_zone_line)
    crossing_policy.check_context(p.source, p.static, p.bsp)

    chain = SourceFloorChain(
        inventory_sha256=p.source.wld_sha256,
        seed_evidence_sha256='a' * 64,
        seed_ids=((1644, 5),),
        body_height=6.,
    )
    cap = swept_square(corridor.start_xy, corridor.start_xy, 1.2)
    assert chain.advance(cap, p.source.source_faces_for_footprint(cap)).candidate
    cells = []
    branch = chain.fork()
    for seg_a, seg_b in corridor.cell_segments:
        branch, cell = check_source_crossing_cell(
            branch, seg_a, seg_b,
            radius=1.2, terrain=p.source, static=p.static, bsp=p.bsp, policy=crossing_policy,
        )
        cells.append(cell)
    assert len(cells) == 8
    assert cells[0].record()['departure_floor_sha256'] == chain.previous.proof_sha256
    assert cells[-1].record()['native']['possible_flags'] == [0x80000000]
    assert cells[-1].record()['possible_transition_regions'] == [3077]


def _configure_sectioned_crossing(h, monkeypatch, *, sectioned=False):
    model = files(h.game, monkeypatch)
    old = h.loader
    split_y = 278. if sectioned else 228.
    # Split plane at x_wld = split_y (y_game = split_y):
    # y_game < split_y -> leaf(1) [region 0, ordinary dry ground]
    # y_game >= split_y -> leaf(3) [region 2, DRNTP00255000001 (0x80000000)]
    nodes = ((1., 0., 0., -split_y, 0, 2, 3), leaf(3), leaf(1))
    bsp = BspVolumeView(
        SimpleNamespace(nodes=nodes, labels_by_region={2: {'zoneline'}}),
        region_count=3,
        wld_sha256=old.pins[2],
    )
    classifier = view(nodes, wld_pin=old.pins[2])
    ordinary = NativeZeroRegionTrialPolicy(
        *old.pins, bsp.inventory_sha256, classifier.inventory_sha256, classifier, zone='butcher',
    )
    line = ExpectedZoneLine(
        'butcher-gfay-synthetic-v1', 'butcher',
        old.pins[0], old.pins[1], old.pins[2], bsp.inventory_sha256, 'f' * 64,
        'DRNTP00255000001', 2, (1,), (2,),
    )
    planner = CurrentStartPlanner(
        mesh=old.mesh, ground=old.ground, source=old.source, static=old.static, bsp=bsp,
        zone_short_name='butcher', expected_zone_id=68, expected_zone_name='Fixture',
        mesh_sha256=old.pins[0], source_archive_sha256=old.pins[1],
        source_wld_sha256=old.pins[2], static_inventory_sha256=old.pins[3],
        region_policy=ordinary,
    )
    planner.installed_region_model = model
    h.loading[0] = lambda: planner
    h.engine._close_zone_tracker()
    (h.game / 'Resources/ZoneNames.txt').write_text(
        '68^Fixture^0^0\n54^The Greater Faydark^0^0\n'
    )
    h.engine._service_zone_tracker()
    h.append('You have entered Fixture.')
    h.engine._service_zone_tracker()

    from eql_automation.source_itinerary import SourceItineraryGuide
    if sectioned:
        waypoints = (212., 224., 237., 239.)
        goal_y = 239.
        end_y = 279.5
        cell_segments = (
            ((396.5, 239.), (396.5, 239.)),
            ((396.5, 239.), (396.5, 250.)),
            ((396.5, 250.), (396.5, 261.)),
            ((396.5, 261.), (396.5, 271.)),
            ((396.5, 271.), (396.5, 279.5)),
            ((396.5, 279.5), (396.5, 279.5)),
        )
    else:
        waypoints = (212., 214.)
        goal_y = 214.
        end_y = 229.5
        cell_segments = (
            ((396.5, 214.), (396.5, 214.)),
            ((396.5, 214.), (396.5, 222.)),
            ((396.5, 222.), (396.5, 229.5)),
            ((396.5, 229.5), (396.5, 229.5)),
        )

    itinerary_guide = SourceItineraryGuide(
        'butcher', planner.pins[2], planner.pins[3], 'e' * 64, 1.2, 6.,
        (396.5, goal_y),
        tuple(SourceWalkHint((396.5, a), (396.5, b)) for a, b in zip(waypoints, waypoints[1:])),
    )
    assets = SourceDestinationAssets(
        planner, itinerary_guide, 'Synthetic Butcher -> GFay crossing',
        encoded(dict(
            synthetic=True,
            destination_id='butcher-gfay-crossing',
            guide_sha256=sha256(encoded(itinerary_guide.record())).hexdigest(),
        )),
        'butcher-gfay-crossing',
    )
    if sectioned:
        prefix = SourceFloorChain(
            inventory_sha256=planner.source.wld_sha256,
            seed_evidence_sha256='b' * 64,
            seed_ids=((10, 1),),
            body_height=6.,
        )
        cap = swept_square((396.5, 212.), (396.5, 212.), 1.2)
        assert prefix.advance(cap, planner.source.source_faces_for_footprint(cap)).candidate
        bounds = RouteMotionBounds(
            'synthetic-section-reserve', 'synthetic-motion',
            .01, .15, .2, 60., .3, .1, 10., .2, 1.2, 6.,
        )
        partition = plan_walk_sections(
            prefix, itinerary_guide, planner, bounds=bounds,
            maximum_length=16., minimum_length=11., candidate_spacing=1., check_context=lambda: None,
        )
        sections = parse_walking_sections(itinerary_guide, partition)
        assert len(sections.guides) == 2
        h.engine._test_walking_partition = lambda d: sections if d is assets else None
    else:
        h.engine._test_walking_partition = lambda _d: None

    corridor_spec = PinnedSourceCrossingSpec(
        destination_id='butcher-gfay-crossing',
        zone='butcher',
        destination='The Greater Faydark',
        destination_zone_id=54,
        destination_zone='gfaydark',
        provenance_sha256='e' * 64,
        start_xy=(396.5, goal_y),
        transition_endpoint=(396.5, end_y),
        cell_segments=cell_segments,
        expected_zone_line=line,
        corridor_file_sha256='d' * 64,
        source_evidence=encoded(dict(synthetic=True, destination='The Greater Faydark')),
    )

    h.source_loading[0] = lambda: assets
    monkeypatch.setattr(
        h.engine, '_source_crossing_spec',
        lambda dest_id: corridor_spec if dest_id == 'butcher-gfay-crossing' else None,
    )

    import eql_automation.owner_source_runtime as initial_route
    import eql_automation.camp_probe_runtime as probes
    import eql_automation.camp_source_runtime as section_route
    import eql_automation.owner_source_crossing as crossing_mod

    old_initial = initial_route.run_checked_source_step
    old_probe = probes.send_camp_probe
    old_section = section_route.run_checked_source_step
    old_crossing = crossing_mod.run_checked_source_crossing_step
    zoned = [False]

    def step_initial(*a, **kw):
        res = old_initial(*a, **kw)
        h.apply(res.receipt.key_code, res.receipt)
        return res

    def step_probe(*a, **kw):
        res = old_probe(*a, **kw)
        h.apply(res.seal.receipt.key_code, res.seal.receipt)
        return res

    def step_section(*a, **kw):
        res = old_section(*a, **kw)
        h.apply(res.receipt.key_code, res.receipt)
        return res

    def step_crossing(*a, **kw):
        res = old_crossing(*a, **kw)
        from eql_automation.uinput_watchdog import PulseReceipt
        r = h.engine.source_crossing_run
        receipt = PulseReceipt(**res['receipt'])
        h.apply(receipt.key_code, receipt)
        if not zoned[0] and res['touches_line']:
            zoned[0] = True
            h.append('LOADING, PLEASE WAIT...')
            h.append('You have entered The Greater Faydark.')
            # Destination spawn coordinates in GFaydark:
            h.point = [-1628., 2642., .5]
        return res

    monkeypatch.setattr(initial_route, 'run_checked_source_step', step_initial)
    monkeypatch.setattr(probes, 'send_camp_probe', step_probe)
    monkeypatch.setattr(section_route, 'run_checked_source_step', step_section)
    monkeypatch.setattr(crossing_mod, 'run_checked_source_crossing_step', step_crossing)

    def reply():
        p = h.engine.route_trial
        sr = None if p is None else p.get('source_runtime')
        if sr is not None and sr.collector is not None and sr.collector.phase == 'requesting':
            h.append('Your Location is ' + ', '.join(f'{v:.2f}' for v in h.point))
            return
        sec = h.engine.section_run
        if sec is not None and sec.current_input_key() == 62:
            h.append('Your Location is ' + ', '.join(f'{v:.2f}' for v in h.point))
            return
        cr = h.engine.source_crossing_run
        if cr is not None and cr.current_input_key() == 62:
            h.append('Your Location is ' + ', '.join(f'{v:.2f}' for v in h.point))

    after_down(monkeypatch, reply)
    return corridor_spec


def _finish_journey(h, timeout=240.):
    deadline = time.monotonic() + timeout
    e = h.engine
    while time.monotonic() < deadline:
        e.read_log()
        h.tick()
        h.drain()
        if not e._navigation_busy():
            return e.journey_last_result
        time.sleep(.01)
    raise AssertionError(('Crossing journey timed out', e.autopilot_payload(), h.notices[-8:]))


@pytest.mark.parametrize('h', ['walking_sections'], indirect=True)
@pytest.mark.parametrize('sectioned', [False, True])
def test_owner_sectioned_travel_crosses_zone_and_discards_source_floor(h, monkeypatch, sectioned):
    _configure_sectioned_crossing(h, monkeypatch, sectioned=sectioned)
    e = h.engine
    captured_runs = []
    orig_start = e._start_source_crossing_from_arrival

    def capture_start(p, token):
        res = orig_start(p, token)
        captured_runs.append(e.source_crossing_run)
        return res

    monkeypatch.setattr(e, '_start_source_crossing_from_arrival', capture_start)

    start(h, 'butcher-gfay-crossing')
    h.due_trial()
    result = _finish_journey(h)

    assert result is not None and result['phase'] == 'crossed_zone', (
        '\n'.join(map(str, h.notices)) + '\n' + str(result)
    )
    assert result['destination'] == 'The Greater Faydark'
    assert result['destination_zone'] == 'gfaydark'
    assert result['destination_zone_id'] == 54
    assert result['source_floor_discarded'] is True
    assert result['source_navigation_state_reused'] is False
    assert result['camp_started'] is False
    assert result['real_client_accepted'] is False
    assert len(captured_runs) == 1
    cr = captured_runs[0]
    assert cr.closed and cr.monitor.closed and not cr.checkpoint.valid
    assert e.zone == 'gfaydark'
    assert e.journey is None and e.source_crossing_run is None and e.section_run is None
    assert e.live_zone_tracker.lease is None
    assert e.live_zone_tracker.reader.zone_id == 54
    assert not h.sender.held and h.observer_closed and not h.commands


@pytest.mark.parametrize('h', ['walking_sections'], indirect=True)
@pytest.mark.parametrize('action', ('stop', 'arm'))
def test_owner_stop_and_assist_cancel_active_source_crossing_immediately(h, monkeypatch, action):
    _configure_sectioned_crossing(h, monkeypatch, sectioned=False)
    e = h.engine
    e.prepared = True
    e.prepared_level = 7
    seen = []

    def stop_on_crossing_pulse():
        cr = e.source_crossing_run
        if not seen and cr is not None and cr.current_input_key() in (103, 105, 106):
            seen.append(cr)
            if action == 'arm':
                e.handle_job('arm', e.cancel_generation)
            else:
                e.stop_action('F9 during source crossing pulse')

    after_down(monkeypatch, stop_on_crossing_pulse)
    start(h, 'butcher-gfay-crossing')
    h.due_trial()
    _finish_journey(h)

    assert seen, '\n'.join(map(str, h.notices))
    cr = seen[0]
    assert cr.closed and cr.monitor.closed and not cr.checkpoint.valid
    assert e.journey is None and e.source_crossing_run is None
    assert e.live_zone_tracker.lease is None and not h.sender.held and h.observer_closed
    h.tick()
    h.drain()
    assert e.active is (action == 'arm')
    assert not h.commands
