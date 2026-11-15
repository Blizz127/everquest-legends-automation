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
        (-2069.,-298.), 'cbf65baf94b8ce069e457dfe47aa220303fd69baa3a0a1be7915e1be61d753f2', 'stop', 'butcher'),
    'butcher-gfay-preline-stop': SourceGuideDestination(
        'butcher-gfay-preline-stop', 'Greater Faydark zone-line approach test',
        'butcher-goblin-gfay-preline-stop-carbon-source-guide-v1.json',
        '610c572a9913a33fe4a13c96bb6e6ad7fcdb9332fd9c78e687028ff51810b9bf',
        (-3084.646484375, -1328.2936706542969),
        'ef9f03f53d49158d6d9681d5e00860f36aaeecfc0c9c5f05e949b51eddf76ddb', 'stop', 'butcher'),
    'butcher-gfay-crossing': SourceGuideDestination(
        'butcher-gfay-crossing', 'Travel into The Greater Faydark',
        'butcher-goblin-gfay-crossing-carbon-source-guide-v1.json',
        'c1c20af83d12fc6397edfc5aecae285b2ed68596ae6eea2d6d7e0fadea5eb5a3',
        (-3084.646484375, -1328.2936706542969),
        'ef9f03f53d49158d6d9681d5e00860f36aaeecfc0c9c5f05e949b51eddf76ddb', 'zone_crossing', 'butcher'),
    'gfay-orc-camps': SourceGuideDestination(
        'gfay-orc-camps', 'Orc Camps',
        'gfay-orc-camps-carbon-source-guide-v1.json',
        '9b5be822710177e29c917ee0a652e4496a286ddce85085105cfdf35f7acef645',
        (48., 1849.),
        'b9c43400ce387cc5c1aa9ef23bb48e6bf9a680d9433ea498667fbe404fc291d7', 'camp', 'gfaydark'),
    'gfay-orc-camps-stop': SourceGuideDestination(
        'gfay-orc-camps-stop', 'Orc Camps movement test',
        'gfay-orc-camps-stop-carbon-source-guide-v1.json',
        '6e3892020e1fbafa5981eaaea054f5a442adb4af97fa7cb3431a29fa6722a248',
        (48., 1849.),
        'b9c43400ce387cc5c1aa9ef23bb48e6bf9a680d9433ea498667fbe404fc291d7', 'stop', 'gfaydark'),
    'gfay-crushbone-preline-stop': SourceGuideDestination(
        'gfay-crushbone-preline-stop', 'Crushbone zone-line approach test',
        'gfay-crushbone-preline-stop-carbon-source-guide-v1.json',
        'b5e8be8788a070559f3bf2dfd01dc47db5b84dd9d7a38ef29a8bdc1d3c388526',
        (-52., 2597.),
        '61f31ed94d707102625f42836ed51e0d9954d295f0c6441cf44bbb9706daaa05', 'stop', 'gfaydark'),
    'gfay-crushbone-crossing': SourceGuideDestination(
        'gfay-crushbone-crossing', 'Travel into Clan Crushbone',
        'gfay-crushbone-crossing-carbon-source-guide-v1.json',
        'e8f8e48d57715e06c0e6ca10c392b05680f603fb034f1961ea9b823a7c588443',
        (-52., 2597.),
        '61f31ed94d707102625f42836ed51e0d9954d295f0c6441cf44bbb9706daaa05', 'zone_crossing', 'gfaydark'),
    'gfay-butcher-crushbone-preline-stop': SourceGuideDestination(
        'gfay-butcher-crushbone-preline-stop', 'Butcher exit to Crushbone approach test',
        'gfay-butcher-crushbone-preline-stop-carbon-source-guide-v1.json',
        '48156e0c05f03ef33bfe34c7690ed0d0d20f50517416c51cf2af10ffa8422413',
        (-52., 2597.),
        '1e2dfe7730bb61b37ef0fcc7bca6904dfc11311462af11df8d38a795a8e461e4', 'stop', 'gfaydark'),
    'gfay-butcher-crushbone-crossing': SourceGuideDestination(
        'gfay-butcher-crushbone-crossing', 'Butcher exit travel into Clan Crushbone',
        'gfay-butcher-crushbone-crossing-carbon-source-guide-v1.json',
        '5d4ffffdf2f253e95ac183995c411df2e8f4f51084976c8595a363e9ffea4b54',
        (-52., 2597.),
        '1e2dfe7730bb61b37ef0fcc7bca6904dfc11311462af11df8d38a795a8e461e4', 'zone_crossing', 'gfaydark')})

CARBON_BUTCHER_GFAY_DATA_NAME = 'butcher-gfay-carbon-20261115'
CARBON_GFAY_DATA_NAME = 'gfay-camps-carbon-20261115'


def destination_spec(identifier):
    if type(identifier) is not str or identifier not in DESTINATIONS:
        raise ValueError('Unknown or unpackaged source destination')
    return DESTINATIONS[identifier]


def source_data_name(identifier):
    spec = destination_spec(identifier)
    if spec.identifier in ('butcher-gfay-preline-stop', 'butcher-gfay-crossing'):
        return CARBON_BUTCHER_GFAY_DATA_NAME
    if spec.zone == 'gfaydark':
        return CARBON_GFAY_DATA_NAME
    if spec.zone == 'butcher':
        from .butcher_assets import DATA_NAME
    else:
        from .crushbone_assets import DATA_NAME
    return DATA_NAME


def load_source_guide(root, destination_id='slave-mines'):
    spec = destination_spec(destination_id)
    if spec.zone == 'crushbone':
        return crushbone.load_crushbone_source_guide(root, destination_id)
    if spec.zone == 'gfaydark':
        from .gfay_assets import DATA_PINS, WLD_PIN, STATIC_PIN
    else:
        from .butcher_assets import DATA_PINS, WLD_PIN, STATIC_PIN
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Missing private source guide directory')
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
        raise ValueError('Private source guide identity or provenance changed')
    return guide
