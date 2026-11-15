#!/usr/bin/env python3
"""Stage checked Goblin -> GFay pre-line guides, walking sections, and crossing corridor."""
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from eql_automation.butcher_assets import DATA_NAME, DATA_PINS, STATIC_PIN, WLD_PIN, load_butcher_assets
from eql_automation.butcher_crossing_assets import load_butcher_crossing
from eql_automation.native_region_policy import encoded
from eql_automation.owner_route_assets import checked_bytes
from eql_automation.source_itinerary import SourceItineraryGuide
from eql_automation.source_section_manifest import parse_walking_sections

CARBON_DATA_NAME = 'butcher-gfay-carbon-20261115'
PRIOR_NAME = 'butcher-goblin-gfay-preline-carbon-0.42.89-run3.json'
PRIOR_PIN = 'f4945481f3e26004c2038714be5ce646027bdcbcadfee2be62e4dbcfb00c655e'
PLAN_NAME = 'butcher-goblin-gfay-preline-carbon-0.42.89-run3.plan.json'
PLAN_PIN = '4786b62f28ffe2f997c8e9c0e281f0a7dc1ffd107bfc9f257133504cdc453343'

STOP_GUIDE_FILE = 'butcher-goblin-gfay-preline-stop-carbon-source-guide-v1.json'
CROSSING_GUIDE_FILE = 'butcher-goblin-gfay-crossing-carbon-source-guide-v1.json'
SECTIONS_FILE = 'butcher-goblin-gfay-preline-carbon-sections-v1.json'
CORRIDOR_FILE = 'butcher-gfay-crossing-carbon-corridor-v1.json'


def _write_pinned(path: Path, blob: bytes) -> dict:
    digest = sha256(blob).hexdigest()
    if path.exists() or path.is_symlink():
        checked_bytes(path, digest)
    else:
        with path.open('xb') as stream:
            stream.write(blob)
    return dict(name=path.name, path=str(path), sha256=digest)


def prepare(store: Path) -> dict:
    store = Path(store)
    source_root = store / 'owner-route-data' / DATA_NAME
    out_root = store / 'owner-route-data' / CARBON_DATA_NAME
    data = json.loads(checked_bytes(store / 'nav-candidates' / PRIOR_NAME, PRIOR_PIN))
    plan = json.loads(checked_bytes(store / 'nav-candidates' / PLAN_NAME, PLAN_PIN))
    assets = load_butcher_assets(source_root, native_planning=True)
    crossing = load_butcher_crossing(source_root, assets)
    guide = SourceItineraryGuide.from_record(data['guide'])
    guide_pin = sha256(encoded(guide.record())).hexdigest()
    sections = parse_walking_sections(guide, data['walk_sections'])
    carried = data['carried_crossing']
    if (data['status'] != 'checked'
            or data['completed'] is not True
            or data['source_candidate'] is not True
            or data['zone_transition_checked'] is not True
            or data['synthetic_preline_floor_seed'] is not False
            or data['input_authorized'] is not False
            or data['game_input_sent'] is not False
            or data['real_client_accepted'] is not False
            or data['data_sha256'] != DATA_PINS
            or data['checked_plan']['sha256'] != PLAN_PIN
            or guide.zone != 'butcher'
            or guide.wld_sha256 != WLD_PIN
            or guide.static_inventory_sha256 != STATIC_PIN
            or guide.radius != 1.2
            or guide.body_height != 6.
            or guide.operations[0].start != (-2069., -298.)
            or guide.goal != (-3084.646484375, -1328.2936706542969)
            or plan['guide_sha256'] != guide_pin
            or plan['geometry_candidate'] is not True
            or plan['input_authorized'] is not False
            or plan['game_input_sent'] is not False
            or len(sections.guides) != 2
            or encoded(carried['descriptor']) != encoded(crossing.record())
            or carried['preline_floor_proof_sha256'] != data['checked_plan']['final_proof_sha256']
            or carried['first_cell_previous_sha256'] != data['checked_plan']['final_proof_sha256']
            or len(carried['cells']) != 8
            or tuple(carried['cells'][0]['start']) != guide.goal
            or tuple(carried['cells'][-1]['end']) != tuple(carried['transition_endpoint'])
            or carried['cells'][-1]['native']['possible_flags'] != [0x80000000]):
        raise ValueError('Pinned Goblin -> GFay pre-line guide, sections, or carried crossing changed')

    out_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if out_root.is_symlink() or not out_root.is_dir():
        raise ValueError('Invalid Carbon Butcher -> GFay output directory')

    staged = []
    for mode, filename in (('stop', STOP_GUIDE_FILE), ('zone_crossing', CROSSING_GUIDE_FILE)):
        record = dict(
            format='eql-copied-source-guide-v1',
            client_data_pins=DATA_PINS,
            guide=guide.record(),
            guide_sha256=guide_pin,
            prior_sha256=PRIOR_PIN,
            checked_plan_sha256=PLAN_PIN,
            arrival_mode=mode,
            input_authorized=False,
            real_client_accepted=False,
        )
        staged.append(dict(
            **_write_pinned(out_root / filename, encoded(record)),
            arrival_mode=mode,
            guide_sha256=guide_pin,
            provenance_sha256=guide.provenance_sha256,
            goal=guide.goal,
        ))

    sections_record = dict(
        format='eql-offline-goblin-sections-audit-v1',
        prior_sha256=PRIOR_PIN,
        checked_plan_sha256=PLAN_PIN,
        source_candidate=True,
        current_character_observation=False,
        input_authorized=False,
        real_client_accepted=False,
        runtime_continuation_enabled=False,
        result=data['walk_sections'],
    )
    staged.append(dict(
        **_write_pinned(out_root / SECTIONS_FILE, encoded(sections_record)),
        section_count=len(sections.guides),
        section_manifest_sha256=sections.record_sha256,
    ))

    line_record = crossing.policy.expected_zone_line.record()
    corridor_record = dict(
        format='eql-copied-source-crossing-corridor-v1',
        zone='butcher',
        destination_id='butcher-gfay-crossing',
        destination=crossing.destination,
        destination_zone_id=crossing.destination_id,
        destination_zone='gfaydark',
        provenance_sha256=guide.provenance_sha256,
        start_xy=list(guide.goal),
        transition_endpoint=carried['transition_endpoint'],
        cell_segments=[[c['start'], c['end']] for c in carried['cells']],
        expected_zone_line=line_record,
        expected_zone_line_sha256=crossing.policy.expected_zone_line.sha256,
        prior_sha256=PRIOR_PIN,
        checked_plan_sha256=PLAN_PIN,
        destination_server_verified=False,
        spawn_coordinate_verified=False,
        input_authorized=False,
        real_client_accepted=False,
    )
    staged.append(dict(
        **_write_pinned(out_root / CORRIDOR_FILE, encoded(corridor_record)),
        expected_zone_line_sha256=crossing.policy.expected_zone_line.sha256,
        cell_count=len(carried['cells']),
    ))
    return dict(directory=str(out_root), files=staged)


if __name__ == '__main__':
    os.umask(0o077)
    print(json.dumps(prepare(Path.home() / '.local/share/eql-automation'), indent=2))
