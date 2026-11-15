"""Tests for Greater Faydark native source assets, Orc Camps guides, and Crushbone crossing."""
from hashlib import sha256
import json
from pathlib import Path

import pytest

from eql_automation.gfay_assets import (
    CLASSIFICATION_PIN,
    DATA_NAME,
    DATA_PINS,
    STATIC_PIN,
    WLD_PIN,
    load_gfay_assets,
)
from eql_automation.gfay_crossing_assets import load_gfay_crushbone_crossing
from eql_automation.native_crossing_policy import NativeCrossingRegionPolicy, check_source_crossing_cell
from eql_automation.native_region_policy import encoded
from eql_automation.owner_section_assets import load_guide_walking_sections
from eql_automation.owner_source_crossing import (
    GFAY_BUTCHER_CRUSHBONE_CORRIDOR_SHA256,
    GFAY_CRUSHBONE_CORRIDOR_SHA256,
    load_source_crossing_spec,
)
from eql_automation.source_destinations import (
    destination_spec,
    load_source_guide,
    source_data_name,
)
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.source_itinerary import SourceItineraryGuide, SourceWalkHint

STORE = Path.home() / '.local/share/eql-automation'
ROOT = STORE / 'owner-route-data' / DATA_NAME
HELPER = STORE / 'owner-assist/0.39.10'


def _require_staged_gfay(monkeypatch):
    if not ROOT.is_dir() or not (HELPER / 'eqnav/zonegeom.py').is_file():
        pytest.skip('Staged Greater Faydark carbon route data not present on this host')
    monkeypatch.syspath_prepend(str(HELPER))


def test_gfay_assets_and_crushbone_crossing_descriptor_verify_pins_and_layers(monkeypatch):
    _require_staged_gfay(monkeypatch)
    assets = load_gfay_assets(ROOT, native_planning=True)
    assert assets.classification.inventory_sha256 == CLASSIFICATION_PIN
    report = assets.annotation_report(body_height=6.)
    assert (report['zone'], report['zone_id'], report['zone_name']) == (
        'gfaydark', 54, 'The Greater Faydark',
    )
    assert not report['label_z_used_for_floor_selection']
    assert not report['game_input_sent'] and not report['real_client_accepted']
    by_label = {r['annotation']['raw_label']: r for r in report['rows']}
    assert by_label['L04-07_Orc_Camps']['package_xy'] == (48., 1849.)
    assert 'floor_seed_proposal' in by_label['L04-07_Orc_Camps']
    assert by_label['L04-10_GO_TO_CRUSHBONE']['package_xy'] == (-52., 2597.)
    with pytest.raises(ValueError):
        assets.planner.ground.triangles[0, 0, 0] = 99.
    with pytest.raises(ValueError):
        assets.planner.source.source_minimum[0, 0] = 99.

    crossing = load_gfay_crushbone_crossing(ROOT, assets)
    line = crossing.policy.expected_zone_line
    assert line.region_ids == (2884,)
    assert line.polygon_ids == (19256,)
    assert line.raw_label == 'DRNTP00255000004_ZONE'
    assert crossing.destination == 'Clan Crushbone' and crossing.destination_id == 58
    rec = crossing.record()
    assert not rec['destination_server_verified'] and not rec['real_client_accepted']


@pytest.mark.parametrize(
    'identifier,mode,expected_start,expected_goal',
    [
        ('gfay-orc-camps', 'camp', (2642.0693, -1627.6870), (48., 1849.)),
        ('gfay-orc-camps-stop', 'stop', (2642.0693, -1627.6870), (48., 1849.)),
        ('gfay-crushbone-preline-stop', 'stop', (48., 1849.), (-52., 2597.)),
        ('gfay-crushbone-crossing', 'zone_crossing', (48., 1849.), (-52., 2597.)),
        ('gfay-butcher-crushbone-preline-stop', 'stop', (2642.0693, -1627.6870), (-52., 2597.)),
        ('gfay-butcher-crushbone-crossing', 'zone_crossing', (2642.0693, -1627.6870), (-52., 2597.)),
    ],
)
def test_staged_gfay_guides_and_walking_sections_load_with_pinned_hashes(
    monkeypatch, identifier, mode, expected_start, expected_goal,
):
    _require_staged_gfay(monkeypatch)
    spec = destination_spec(identifier)
    assert source_data_name(identifier) == DATA_NAME
    guide = load_source_guide(ROOT, identifier)
    assert spec.zone == guide.zone == 'gfaydark'
    assert spec.zone_id == 54
    assert spec.arrival_mode == mode
    assert guide.operations[0].start == expected_start
    assert guide.goal == expected_goal
    assert guide.radius == 1.2 and guide.body_height == 6.
    assert all(type(op) is SourceWalkHint for op in guide.operations)

    sections = load_guide_walking_sections(identifier, guide, root=ROOT)
    assert sections is not None and len(sections.guides) >= 2
    assert sections.guides[-1].goal == expected_goal


@pytest.mark.parametrize(
    'crossing_id,expected_pin',
    [
        ('gfay-crushbone-crossing', GFAY_CRUSHBONE_CORRIDOR_SHA256),
        ('gfay-butcher-crushbone-crossing', GFAY_BUTCHER_CRUSHBONE_CORRIDOR_SHA256),
    ],
)
def test_staged_gfay_crushbone_corridor_rebuilds_live_crossing_cells(
    monkeypatch, crossing_id, expected_pin,
):
    _require_staged_gfay(monkeypatch)
    corridor = load_source_crossing_spec(crossing_id, root=ROOT)
    assert corridor.corridor_file_sha256 == expected_pin
    assert corridor.zone == 'gfaydark'
    assert corridor.destination == 'Clan Crushbone'
    assert corridor.destination_zone == 'crushbone'
    assert corridor.destination_zone_id == 58
    assert corridor.start_xy == (-52., 2597.)
    assert len(corridor.cell_segments) == 13

    assets = load_gfay_assets(ROOT, native_planning=True)
    p = assets.planner
    crossing_policy = NativeCrossingRegionPolicy(p.region_policy, corridor.expected_zone_line)
    crossing_policy.check_context(p.source, p.static, p.bsp)

    chain = SourceFloorChain(
        inventory_sha256=p.source.wld_sha256,
        seed_evidence_sha256='b' * 64,
        seed_ids=((1707, 28),),
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
    assert len(cells) == 13
    assert cells[0].record()['departure_floor_sha256'] == chain.previous.proof_sha256
    assert cells[-1].record()['native']['possible_flags'] == [0x80000000]
    assert cells[-1].record()['possible_transition_regions'] == [2884]


def test_gfay_guide_and_corridor_loaders_refuse_missing_or_tampered_files(tmp_path):
    spec = destination_spec('gfay-orc-camps')
    with pytest.raises((OSError, ValueError)):
        load_source_guide(tmp_path, 'gfay-orc-camps')

    guide = SourceItineraryGuide(
        'gfaydark', WLD_PIN, STATIC_PIN, spec.provenance_sha256,
        1.2, 6., spec.goal, (SourceWalkHint((48., 1848.), spec.goal),),
    )
    bad_record = dict(
        format='eql-copied-source-guide-v1',
        client_data_pins=DATA_PINS,
        guide=guide.record(),
        guide_sha256=sha256(encoded(guide.record())).hexdigest(),
        arrival_mode='camp',
        input_authorized=False,
        real_client_accepted=False,
    )
    (tmp_path / spec.filename).write_bytes(encoded(bad_record))
    with pytest.raises(ValueError, match='hash mismatch'):
        load_source_guide(tmp_path, 'gfay-orc-camps')

    with pytest.raises((OSError, ValueError)):
        load_source_crossing_spec('gfay-crushbone-crossing', root=tmp_path)
    (tmp_path / 'gfay-crushbone-crossing-carbon-corridor-v1.json').write_text('{}')
    with pytest.raises(ValueError, match='hash mismatch'):
        load_source_crossing_spec('gfay-crushbone-crossing', root=tmp_path)
