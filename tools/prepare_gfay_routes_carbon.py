#!/usr/bin/env python3
"""Stage checked Greater Faydark Orc Camps and Crushbone crossing guides/sections/corridor."""
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from eql_automation.gfay_assets import DATA_NAME, DATA_PINS, STATIC_PIN, WLD_PIN, load_gfay_assets
from eql_automation.gfay_crossing_assets import load_gfay_crushbone_crossing
from eql_automation.native_region_policy import encoded
from eql_automation.owner_route_assets import checked_bytes
from eql_automation.source_itinerary import SourceItineraryGuide
from eql_automation.source_section_manifest import parse_walking_sections

ORC_CAMPS_GUIDE_FILE = 'gfay-orc-camps-carbon-source-guide-v1.json'
ORC_CAMPS_STOP_GUIDE_FILE = 'gfay-orc-camps-stop-carbon-source-guide-v1.json'
ORC_CAMPS_SECTIONS_FILE = 'gfay-orc-camps-carbon-sections-v1.json'

CB_STOP_GUIDE_FILE = 'gfay-crushbone-preline-stop-carbon-source-guide-v1.json'
CB_CROSSING_GUIDE_FILE = 'gfay-crushbone-crossing-carbon-source-guide-v1.json'
CB_SECTIONS_FILE = 'gfay-crushbone-preline-carbon-sections-v1.json'
CB_CORRIDOR_FILE = 'gfay-crushbone-crossing-carbon-corridor-v1.json'

FULL_CB_STOP_GUIDE_FILE = 'gfay-butcher-crushbone-preline-stop-carbon-source-guide-v1.json'
FULL_CB_CROSSING_GUIDE_FILE = 'gfay-butcher-crushbone-crossing-carbon-source-guide-v1.json'
FULL_CB_SECTIONS_FILE = 'gfay-butcher-crushbone-preline-carbon-sections-v1.json'
FULL_CB_CORRIDOR_FILE = 'gfay-butcher-crushbone-crossing-carbon-corridor-v1.json'


def _write_pinned(path: Path, blob: bytes) -> dict:
    digest = sha256(blob).hexdigest()
    if path.exists() or path.is_symlink():
        checked_bytes(path, digest)
    else:
        with path.open('xb') as stream:
            stream.write(blob)
    return dict(name=path.name, path=str(path), sha256=digest)


def stage_gfay_routes(store: Path, *, orc_prior_name: str, orc_prior_pin: str,
                      orc_plan_name: str, orc_plan_pin: str,
                      cb_prior_name: str, cb_prior_pin: str,
                      cb_plan_name: str, cb_plan_pin: str,
                      full_prior_name: str, full_prior_pin: str,
                      full_plan_name: str, full_plan_pin: str) -> dict:
    store = Path(store)
    root = store / 'owner-route-data' / DATA_NAME
    candidates = store / 'nav-candidates'

    orc_data = json.loads(checked_bytes(candidates / orc_prior_name, orc_prior_pin))
    orc_plan = json.loads(checked_bytes(candidates / orc_plan_name, orc_plan_pin))
    cb_data = json.loads(checked_bytes(candidates / cb_prior_name, cb_prior_pin))
    cb_plan = json.loads(checked_bytes(candidates / cb_plan_name, cb_plan_pin))
    full_data = json.loads(checked_bytes(candidates / full_prior_name, full_prior_pin))
    full_plan = json.loads(checked_bytes(candidates / full_plan_name, full_plan_pin))

    assets = load_gfay_assets(root, native_planning=True)
    crossing = load_gfay_crushbone_crossing(root, assets)

    orc_guide = SourceItineraryGuide.from_record(orc_data['guide'])
    orc_guide_pin = sha256(encoded(orc_guide.record())).hexdigest()
    orc_sections = parse_walking_sections(orc_guide, orc_data['walk_sections'])

    cb_guide = SourceItineraryGuide.from_record(cb_data['guide'])
    cb_guide_pin = sha256(encoded(cb_guide.record())).hexdigest()
    cb_sections = parse_walking_sections(cb_guide, cb_data['walk_sections'])
    carried = cb_data['carried_crossing']

    full_guide = SourceItineraryGuide.from_record(full_data['guide'])
    full_guide_pin = sha256(encoded(full_guide.record())).hexdigest()
    full_sections = parse_walking_sections(full_guide, full_data['walk_sections'])
    full_carried = full_data['carried_crossing']

    if (orc_data['status'] != 'checked' or orc_data['completed'] is not True
            or orc_data['source_candidate'] is not True
            or orc_data['input_authorized'] is not False
            or orc_data['game_input_sent'] is not False
            or orc_data['real_client_accepted'] is not False
            or orc_data['data_sha256'] != DATA_PINS
            or orc_data['checked_plan']['sha256'] != orc_plan_pin
            or orc_guide.zone != 'gfaydark'
            or orc_guide.wld_sha256 != WLD_PIN
            or orc_guide.static_inventory_sha256 != STATIC_PIN
            or orc_guide.radius != 1.2 or orc_guide.body_height != 6.
            or orc_guide.operations[0].start != (2642.0693, -1627.6870)
            or orc_guide.goal != (48.0, 1849.0)
            or orc_plan['guide_sha256'] != orc_guide_pin
            or orc_plan['geometry_candidate'] is not True):
        raise ValueError('Pinned GFay Butcher-exit -> Orc Camps guide or sections changed')

    if (cb_data['status'] != 'checked' or cb_data['completed'] is not True
            or cb_data['source_candidate'] is not True
            or cb_data['zone_transition_checked'] is not True
            or cb_data['synthetic_preline_floor_seed'] is not False
            or cb_data['input_authorized'] is not False
            or cb_data['game_input_sent'] is not False
            or cb_data['real_client_accepted'] is not False
            or cb_data['data_sha256'] != DATA_PINS
            or cb_data['checked_plan']['sha256'] != cb_plan_pin
            or cb_guide.zone != 'gfaydark'
            or cb_guide.wld_sha256 != WLD_PIN
            or cb_guide.static_inventory_sha256 != STATIC_PIN
            or cb_guide.radius != 1.2 or cb_guide.body_height != 6.
            or cb_guide.operations[0].start != (48.0, 1849.0)
            or cb_guide.goal != (-52.0, 2597.0)
            or cb_plan['guide_sha256'] != cb_guide_pin
            or cb_plan['geometry_candidate'] is not True
            or encoded(carried['descriptor']) != encoded(crossing.record())
            or carried['preline_floor_proof_sha256'] != cb_data['checked_plan']['final_proof_sha256']
            or carried['first_cell_previous_sha256'] != cb_data['checked_plan']['final_proof_sha256']
            or tuple(carried['cells'][0]['start']) != cb_guide.goal
            or tuple(carried['cells'][-1]['end']) != tuple(carried['transition_endpoint'])
            or carried['cells'][-1]['native']['possible_flags'] != [0x80000000]):
        raise ValueError('Pinned GFay Orc Camps -> Crushbone pre-line or carried crossing changed')

    if (full_data['status'] != 'checked' or full_data['completed'] is not True
            or full_data['source_candidate'] is not True
            or full_data['zone_transition_checked'] is not True
            or full_data['synthetic_preline_floor_seed'] is not False
            or full_data['input_authorized'] is not False
            or full_data['game_input_sent'] is not False
            or full_data['real_client_accepted'] is not False
            or full_data['data_sha256'] != DATA_PINS
            or full_data['checked_plan']['sha256'] != full_plan_pin
            or full_guide.zone != 'gfaydark'
            or full_guide.wld_sha256 != WLD_PIN
            or full_guide.static_inventory_sha256 != STATIC_PIN
            or full_guide.radius != 1.2 or full_guide.body_height != 6.
            or full_guide.operations != orc_guide.operations + cb_guide.operations
            or full_guide.operations[0].start != (2642.0693, -1627.6870)
            or full_guide.goal != (-52.0, 2597.0)
            or full_plan['guide_sha256'] != full_guide_pin
            or full_plan['geometry_candidate'] is not True
            or encoded(full_carried['descriptor']) != encoded(crossing.record())
            or full_carried['preline_floor_proof_sha256'] != full_data['checked_plan']['final_proof_sha256']
            or full_carried['first_cell_previous_sha256'] != full_data['checked_plan']['final_proof_sha256']
            or tuple(full_carried['cells'][0]['start']) != full_guide.goal
            or tuple(full_carried['cells'][-1]['end']) != tuple(full_carried['transition_endpoint'])
            or full_carried['cells'][-1]['native']['possible_flags'] != [0x80000000]):
        raise ValueError('Pinned GFay Butcher-exit -> Crushbone pre-line or carried crossing changed')

    staged = []
    for mode, filename in (('camp', ORC_CAMPS_GUIDE_FILE), ('stop', ORC_CAMPS_STOP_GUIDE_FILE)):
        record = dict(
            format='eql-copied-source-guide-v1',
            client_data_pins=DATA_PINS,
            guide=orc_guide.record(),
            guide_sha256=orc_guide_pin,
            prior_sha256=orc_prior_pin,
            checked_plan_sha256=orc_plan_pin,
            arrival_mode=mode,
            input_authorized=False,
            real_client_accepted=False,
        )
        staged.append(dict(
            **_write_pinned(root / filename, encoded(record)),
            arrival_mode=mode,
            guide_sha256=orc_guide_pin,
            provenance_sha256=orc_guide.provenance_sha256,
            goal=orc_guide.goal,
        ))

    orc_sections_record = dict(
        format='eql-offline-goblin-sections-audit-v1',
        prior_sha256=orc_prior_pin,
        checked_plan_sha256=orc_plan_pin,
        source_candidate=True,
        current_character_observation=False,
        input_authorized=False,
        real_client_accepted=False,
        runtime_continuation_enabled=False,
        result=orc_data['walk_sections'],
    )
    staged.append(dict(
        **_write_pinned(root / ORC_CAMPS_SECTIONS_FILE, encoded(orc_sections_record)),
        section_count=len(orc_sections.guides),
        section_manifest_sha256=orc_sections.record_sha256,
    ))

    for mode, filename in (('stop', CB_STOP_GUIDE_FILE), ('zone_crossing', CB_CROSSING_GUIDE_FILE)):
        record = dict(
            format='eql-copied-source-guide-v1',
            client_data_pins=DATA_PINS,
            guide=cb_guide.record(),
            guide_sha256=cb_guide_pin,
            prior_sha256=cb_prior_pin,
            checked_plan_sha256=cb_plan_pin,
            arrival_mode=mode,
            input_authorized=False,
            real_client_accepted=False,
        )
        staged.append(dict(
            **_write_pinned(root / filename, encoded(record)),
            arrival_mode=mode,
            guide_sha256=cb_guide_pin,
            provenance_sha256=cb_guide.provenance_sha256,
            goal=cb_guide.goal,
        ))

    cb_sections_record = dict(
        format='eql-offline-goblin-sections-audit-v1',
        prior_sha256=cb_prior_pin,
        checked_plan_sha256=cb_plan_pin,
        source_candidate=True,
        current_character_observation=False,
        input_authorized=False,
        real_client_accepted=False,
        runtime_continuation_enabled=False,
        result=cb_data['walk_sections'],
    )
    staged.append(dict(
        **_write_pinned(root / CB_SECTIONS_FILE, encoded(cb_sections_record)),
        section_count=len(cb_sections.guides),
        section_manifest_sha256=cb_sections.record_sha256,
    ))

    line_record = crossing.policy.expected_zone_line.record()
    corridor_record = dict(
        format='eql-copied-source-crossing-corridor-v1',
        zone='gfaydark',
        destination_id='gfay-crushbone-crossing',
        destination=crossing.destination,
        destination_zone_id=crossing.destination_id,
        destination_zone='crushbone',
        provenance_sha256=cb_guide.provenance_sha256,
        start_xy=list(cb_guide.goal),
        transition_endpoint=carried['transition_endpoint'],
        cell_segments=[[c['start'], c['end']] for c in carried['cells']],
        expected_zone_line=line_record,
        expected_zone_line_sha256=crossing.policy.expected_zone_line.sha256,
        prior_sha256=cb_prior_pin,
        checked_plan_sha256=cb_plan_pin,
        destination_server_verified=False,
        spawn_coordinate_verified=False,
        input_authorized=False,
        real_client_accepted=False,
    )
    staged.append(dict(
        **_write_pinned(root / CB_CORRIDOR_FILE, encoded(corridor_record)),
        expected_zone_line_sha256=crossing.policy.expected_zone_line.sha256,
        cell_count=len(carried['cells']),
    ))

    for mode, filename in (('stop', FULL_CB_STOP_GUIDE_FILE), ('zone_crossing', FULL_CB_CROSSING_GUIDE_FILE)):
        record = dict(
            format='eql-copied-source-guide-v1',
            client_data_pins=DATA_PINS,
            guide=full_guide.record(),
            guide_sha256=full_guide_pin,
            prior_sha256=full_prior_pin,
            checked_plan_sha256=full_plan_pin,
            arrival_mode=mode,
            input_authorized=False,
            real_client_accepted=False,
        )
        staged.append(dict(
            **_write_pinned(root / filename, encoded(record)),
            arrival_mode=mode,
            guide_sha256=full_guide_pin,
            provenance_sha256=full_guide.provenance_sha256,
            goal=full_guide.goal,
        ))

    full_sections_record = dict(
        format='eql-offline-goblin-sections-audit-v1',
        prior_sha256=full_prior_pin,
        checked_plan_sha256=full_plan_pin,
        source_candidate=True,
        current_character_observation=False,
        input_authorized=False,
        real_client_accepted=False,
        runtime_continuation_enabled=False,
        result=full_data['walk_sections'],
    )
    staged.append(dict(
        **_write_pinned(root / FULL_CB_SECTIONS_FILE, encoded(full_sections_record)),
        section_count=len(full_sections.guides),
        section_manifest_sha256=full_sections.record_sha256,
    ))

    full_corridor_record = dict(
        format='eql-copied-source-crossing-corridor-v1',
        zone='gfaydark',
        destination_id='gfay-butcher-crushbone-crossing',
        destination=crossing.destination,
        destination_zone_id=crossing.destination_id,
        destination_zone='crushbone',
        provenance_sha256=full_guide.provenance_sha256,
        start_xy=list(full_guide.goal),
        transition_endpoint=full_carried['transition_endpoint'],
        cell_segments=[[c['start'], c['end']] for c in full_carried['cells']],
        expected_zone_line=line_record,
        expected_zone_line_sha256=crossing.policy.expected_zone_line.sha256,
        prior_sha256=full_prior_pin,
        checked_plan_sha256=full_plan_pin,
        destination_server_verified=False,
        spawn_coordinate_verified=False,
        input_authorized=False,
        real_client_accepted=False,
    )
    staged.append(dict(
        **_write_pinned(root / FULL_CB_CORRIDOR_FILE, encoded(full_corridor_record)),
        expected_zone_line_sha256=crossing.policy.expected_zone_line.sha256,
        cell_count=len(full_carried['cells']),
    ))
    return dict(directory=str(root), files=staged)


if __name__ == '__main__':
    os.umask(0o077)
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--orc-prior-name', default='gfay-butcher-exit-orc-camps-carbon-0.42.91-run4.json')
    p.add_argument('--orc-prior-pin', default='a184b01cda3d43b4b9f987255bf407cf145f90e6baad50603883654eafdaaa98')
    p.add_argument('--orc-plan-name', default='gfay-butcher-exit-orc-camps-carbon-0.42.91-run4.plan.json')
    p.add_argument('--orc-plan-pin', default='995adbb5eeaea76fbdd68580e245fbc8c09c7a32da2fa5459fbbb9257e3b5f5a')
    p.add_argument('--cb-prior-name', default='gfay-orc-crushbone-preline-carbon-0.42.91.json')
    p.add_argument('--cb-prior-pin', default='9b5ae572a596371838f3c745a283fcbff48a0fffc025ba9f1b9eea9115a7f53e')
    p.add_argument('--cb-plan-name', default='gfay-orc-crushbone-preline-carbon-0.42.91.plan.json')
    p.add_argument('--cb-plan-pin', default='d0d04e27af7d36fbf077d93640e6c3530395fa55f4545ecf0049fee67eb023fd')
    p.add_argument('--full-prior-name', default='gfay-butcher-crushbone-preline-carbon-0.42.91.json')
    p.add_argument('--full-prior-pin', default='0ca8004cbcd09420a9f18b105ac39e7ea9791554d3ce8c113dddcbd9bb27f42e')
    p.add_argument('--full-plan-name', default='gfay-butcher-crushbone-preline-carbon-0.42.91.plan.json')
    p.add_argument('--full-plan-pin', default='45a0254325b61c2d830015a2cf202e0457b126a0b45813427273f7f1431df6b7')
    args = p.parse_args()
    print(json.dumps(stage_gfay_routes(
        Path.home() / '.local/share/eql-automation',
        orc_prior_name=args.orc_prior_name,
        orc_prior_pin=args.orc_prior_pin,
        orc_plan_name=args.orc_plan_name,
        orc_plan_pin=args.orc_plan_pin,
        cb_prior_name=args.cb_prior_name,
        cb_prior_pin=args.cb_prior_pin,
        cb_plan_name=args.cb_plan_name,
        cb_plan_pin=args.cb_plan_pin,
        full_prior_name=args.full_prior_name,
        full_prior_pin=args.full_prior_pin,
        full_plan_name=args.full_plan_name,
        full_plan_pin=args.full_plan_pin,
    ), indent=2))
