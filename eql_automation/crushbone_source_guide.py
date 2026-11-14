"""Load the private copied route guide without development recipe dependencies."""
from hashlib import sha256
import json
from pathlib import Path
from dataclasses import dataclass
from types import MappingProxyType

from .crushbone_assets import DATA_PINS,WLD_PIN,STATIC_PIN
from .native_region_policy import encoded
from .owner_route_assets import checked_bytes
from .source_itinerary import SourceItineraryGuide

GUIDE_NAME='crushbone-source-guide-v1.json'
GUIDE_PIN='88aecac52585363add569d3f66ed9ba19921725e81e3a1626e96c50cfdc847e7'


@dataclass(frozen=True)
class SourceGuideDestination:
    identifier: str
    label: str
    filename: str
    file_sha256: str
    goal: tuple
    provenance_sha256: str


DESTINATIONS=MappingProxyType({
    'slave-mines':SourceGuideDestination('slave-mines','Slave Mines',GUIDE_NAME,GUIDE_PIN,(426.,74.),
        '339427229a54c400e1fc11a05dd96ae329cd43a03caad74af27955061450fe2c'),
    'north-wall':SourceGuideDestination('north-wall','North Wall and Castle',
        'crushbone-north-wall-source-guide-v1.json',
        '62f8f50797414ace566d7ec967a5ed61153b15ccdb11efeb4f2ea35f38f67d97',(-95.,-78.),
        '8704194aa161892c590ddfb7359d41a0d7d70fb777b3c369268964eb026c0bea')})


def destination_spec(identifier):
    if type(identifier) is not str or identifier not in DESTINATIONS:
        raise ValueError('Unknown or unpackaged Crushbone destination')
    return DESTINATIONS[identifier]


def load_crushbone_source_guide(root,destination_id='slave-mines'):
    spec=destination_spec(destination_id)
    root=Path(root)
    if root.is_symlink() or not root.is_dir():raise ValueError('Missing private Crushbone guide directory')
    data=json.loads(checked_bytes(root/spec.filename,spec.file_sha256))
    guide=SourceItineraryGuide.from_record(data['guide'])
    if (data['format']!='eql-copied-source-guide-v1' or data['client_data_pins']!=DATA_PINS
            or data['guide_sha256']!=sha256(encoded(guide.record())).hexdigest()
            or guide.wld_sha256!=WLD_PIN or guide.static_inventory_sha256!=STATIC_PIN
            or guide.goal!=spec.goal or guide.provenance_sha256!=spec.provenance_sha256
            or guide.radius!=1.2 or guide.body_height!=6.
            or data['input_authorized'] is not False or data['real_client_accepted'] is not False):
        raise ValueError('Private source guide identity or provenance changed')
    return guide
