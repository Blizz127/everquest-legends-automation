"""Pinned same-zone destinations; a guide never authorizes a zone crossing."""
from hashlib import sha256
import json
from pathlib import Path
from types import MappingProxyType

from . import crushbone_source_guide as crushbone
from .native_region_policy import encoded
from .owner_route_assets import checked_bytes
from .source_itinerary import SourceItineraryGuide

SourceGuideDestination = crushbone.SourceGuideDestination
DESTINATIONS = MappingProxyType({**crushbone.DESTINATIONS,
    'newbie-hills': SourceGuideDestination('newbie-hills', 'Newbie Hills',
        'butcher-newbie-source-guide-v1.json',
        '5de5e6f7394e00792f8e3ab579578c2f54c8cfb0d0d5e6386e127167da3de212',
        (-650.,2700.), '36b7d71b078ced64374e5ba2981cc2b751dc7f211155f422934f57ca0e5f0b4a', zone='butcher'),
    'newbie-hills-stop': SourceGuideDestination('newbie-hills-stop', 'Newbie Hills movement test',
        'butcher-newbie-stop-source-guide-v1.json',
        '38a2f367aa2e515a249656e45012230101b3d8b8ba2bcca2794f596e21cb9dbd',
        (-650.,2700.), '36b7d71b078ced64374e5ba2981cc2b751dc7f211155f422934f57ca0e5f0b4a', 'stop', 'butcher'),
    'goblin-camp': SourceGuideDestination('goblin-camp', 'Goblin Camp',
        'butcher-goblin-source-guide-v1.json',
        '1f80591a0a4835a7e7276d1d1b17e08fe801ed614634237afeb9bbb2da3f4aa8',
        (-2069.,-298.), 'cbf65baf94b8ce069e457dfe47aa220303fd69baa3a0a1be7915e1be61d753f2', zone='butcher'),
    'goblin-camp-stop': SourceGuideDestination('goblin-camp-stop', 'Goblin Camp movement test',
        'butcher-goblin-stop-source-guide-v1.json',
        '7d34ae25fca117206172b262fbc6f0f0f559331002611518e36c20381d547d1f',
        (-2069.,-298.), 'cbf65baf94b8ce069e457dfe47aa220303fd69baa3a0a1be7915e1be61d753f2', 'stop', 'butcher')})


def destination_spec(identifier):
    if type(identifier) is not str or identifier not in DESTINATIONS:
        raise ValueError('Unknown or unpackaged source destination')
    return DESTINATIONS[identifier]


def source_data_name(identifier):
    if destination_spec(identifier).zone == 'butcher':
        from .butcher_assets import DATA_NAME
    else:
        from .crushbone_assets import DATA_NAME
    return DATA_NAME


def load_source_guide(root, destination_id='slave-mines'):
    spec = destination_spec(destination_id)
    if spec.zone == 'crushbone':
        return crushbone.load_crushbone_source_guide(root, destination_id)
    from .butcher_assets import DATA_PINS, WLD_PIN, STATIC_PIN
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Missing private Butcherblock guide directory')
    data = json.loads(checked_bytes(root/spec.filename, spec.file_sha256))
    guide = SourceItineraryGuide.from_record(data['guide'])
    if (data['format'] != 'eql-copied-source-guide-v1' or data['client_data_pins'] != DATA_PINS
            or data['guide_sha256'] != sha256(encoded(guide.record())).hexdigest()
            or guide.zone != spec.zone or guide.wld_sha256 != WLD_PIN
            or guide.static_inventory_sha256 != STATIC_PIN or guide.goal != spec.goal
            or guide.provenance_sha256 != spec.provenance_sha256
            or guide.radius != 1.2 or guide.body_height != 6.
            or data['arrival_mode'] != spec.arrival_mode
            or data['input_authorized'] is not False or data['real_client_accepted'] is not False):
        raise ValueError('Private Butcherblock guide identity or provenance changed')
    return guide
