"""Load the private copied route guide without development recipe dependencies."""
from hashlib import sha256
import json
from pathlib import Path

from .crushbone_assets import DATA_PINS,WLD_PIN,STATIC_PIN
from .native_region_policy import encoded
from .owner_route_assets import checked_bytes
from .source_itinerary import SourceItineraryGuide

GUIDE_NAME='crushbone-source-guide-v1.json'
GUIDE_PIN='88aecac52585363add569d3f66ed9ba19921725e81e3a1626e96c50cfdc847e7'


def load_crushbone_source_guide(root):
    root=Path(root)
    if root.is_symlink() or not root.is_dir():raise ValueError('Missing private Crushbone guide directory')
    data=json.loads(checked_bytes(root/GUIDE_NAME,GUIDE_PIN))
    guide=SourceItineraryGuide.from_record(data['guide'])
    if (data['format']!='eql-copied-source-guide-v1' or data['client_data_pins']!=DATA_PINS
            or data['guide_sha256']!=sha256(encoded(guide.record())).hexdigest()
            or guide.wld_sha256!=WLD_PIN or guide.static_inventory_sha256!=STATIC_PIN
            or data['input_authorized'] is not False or data['real_client_accepted'] is not False):
        raise ValueError('Private source guide identity or provenance changed')
    return guide
