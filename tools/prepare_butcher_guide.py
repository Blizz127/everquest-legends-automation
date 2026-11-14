#!/usr/bin/env python3
"""Stage XY-only Newbie Hills guide records from the pinned offline rebuild."""
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


def prepare(store):
    root = Path(store)/'owner-route-data'/DATA_NAME
    prior = Path(store)/'nav-candidates/butcher-newbie-startup-0.42.75-initial.json'
    pin = '7efee54527957065583e45298b6a42961150045948a7c822859ce320b7a5c6ea'
    data = json.loads(checked_bytes(prior, pin))
    guide = SourceItineraryGuide.from_record(data['guide'])
    if (not data['completed'] or not data['source_candidate'] or not data['synthetic_game_log']
            or data['game_input_sent'] or data['real_client_accepted']
            or data['client_data_pins'] != DATA_PINS or guide.zone != 'butcher'
            or guide.wld_sha256 != WLD_PIN or guide.static_inventory_sha256 != STATIC_PIN
            or guide.goal != (-650., 2700.) or guide.radius != 1.2 or guide.body_height != 6.):
        raise ValueError('Pinned Butcher startup result differs')
    for name, expected in DATA_PINS.items(): checked_bytes(root/name, expected)
    result = []
    for mode, name in (('camp', 'butcher-newbie-source-guide-v1.json'),
                       ('stop', 'butcher-newbie-stop-source-guide-v1.json')):
        record = dict(format='eql-copied-source-guide-v1', client_data_pins=DATA_PINS,
            guide=guide.record(), guide_sha256=sha256(encoded(guide.record())).hexdigest(),
            prior_sha256=pin, arrival_mode=mode, input_authorized=False, real_client_accepted=False)
        blob = encoded(record); path = root/name
        if path.exists() or path.is_symlink(): checked_bytes(path, sha256(blob).hexdigest())
        else:
            with path.open('xb') as stream: stream.write(blob)
        result.append(dict(path=str(path), sha256=sha256(blob).hexdigest()))
    return result


if __name__ == '__main__':
    os.umask(0o077)
    print(json.dumps(prepare(Path.home()/'.local/share/eql-automation')))
