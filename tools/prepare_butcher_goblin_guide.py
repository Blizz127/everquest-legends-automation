#!/usr/bin/env python3
"""Stage the checked Goblin approach as XY hints for fresh runtime rebuilding."""
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from eql_automation.butcher_assets import DATA_NAME, DATA_PINS, WLD_PIN, STATIC_PIN
from eql_automation.native_region_policy import encoded
from eql_automation.owner_route_assets import checked_bytes
from eql_automation.source_itinerary import SourceItineraryGuide

PRIOR_NAME = 'butcher-newbie-goblin-transit-20261115-final-source-alienware.json'
PRIOR_PIN = '3c396a3944c4aba7ad05def3c939d45d74c24f87ccd7409a2d048cb4c85be22e'


def prepare(store):
    root = Path(store)/'owner-route-data'/DATA_NAME
    data = json.loads(checked_bytes(Path(store)/'nav-candidates'/PRIOR_NAME, PRIOR_PIN))
    guide = SourceItineraryGuide.from_record(data['guide'])
    plan = json.loads(checked_bytes(Path(store)/'nav-candidates'/Path(data['checked_plan']['file']).name,
                                   data['checked_plan']['sha256']))
    guide_pin = sha256(encoded(guide.record())).hexdigest()
    if (data['completed'] is not True or data['source_candidate'] is not True
            or data['synthetic_start'] is not True or data['game_input_sent'] is not False
            or data['real_client_accepted'] is not False or data['data_sha256'] != DATA_PINS
            or guide.zone != 'butcher' or guide.wld_sha256 != WLD_PIN
            or guide.static_inventory_sha256 != STATIC_PIN or guide.radius != 1.2
            or guide.body_height != 6. or guide.goal != (-2069., -298.)
            or guide.operations[0].start != (-650., 2700.)
            or plan['guide_sha256'] != guide_pin or plan['geometry_candidate'] is not True
            or plan['input_authorized'] is not False or plan['game_input_sent'] is not False):
        raise ValueError('Pinned Goblin guide and complete geometry evidence differ')
    for name, expected in DATA_PINS.items(): checked_bytes(root/name, expected)
    result = []
    for mode, name in (('camp', 'butcher-goblin-source-guide-v1.json'),
                       ('stop', 'butcher-goblin-stop-source-guide-v1.json')):
        record = dict(format='eql-copied-source-guide-v1', client_data_pins=DATA_PINS,
            guide=guide.record(), guide_sha256=guide_pin, prior_sha256=PRIOR_PIN,
            checked_plan_sha256=data['checked_plan']['sha256'], arrival_mode=mode,
            input_authorized=False, real_client_accepted=False)
        blob = encoded(record); path = root/name
        if path.exists() or path.is_symlink(): checked_bytes(path, sha256(blob).hexdigest())
        else:
            with path.open('xb') as stream: stream.write(blob)
        result.append(dict(path=str(path), sha256=sha256(blob).hexdigest(),
                           provenance_sha256=guide.provenance_sha256))
    return result


if __name__ == '__main__':
    os.umask(0o077)
    print(json.dumps(prepare(Path.home()/'.local/share/eql-automation')))
