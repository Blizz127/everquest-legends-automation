"""Pinned copied Goblin route partition; each actual arrival is checked afresh."""
from hashlib import sha256
import json
from pathlib import Path

from .owner_source_assets import SourceDestinationAssets
from .source_section_manifest import parse_walking_sections


SECTION_FILE='butcher-goblin-sections-v1.json'
SECTION_SHA256='65c97d4cd1a4cefd0213877a602cc1276cd3e64d36a156b2a424859bd651d04c'
BUTCHER_GFAY_SECTION_FILE='butcher-goblin-gfay-preline-carbon-sections-v1.json'
BUTCHER_GFAY_SECTION_SHA256='1cf209163cc780eb7ce6ed3d018527272948d9e16bf5875faf7da66e2b41b548'
GFAY_ORC_SECTION_FILE='gfay-orc-camps-carbon-sections-v1.json'
GFAY_ORC_SECTION_SHA256='695ba9a7f0bcd75d0ab82a1b51eee72c966d5615f76a9f0d077be8d6a4f6ef51'
GFAY_CB_SECTION_FILE='gfay-crushbone-preline-carbon-sections-v1.json'
GFAY_CB_SECTION_SHA256='0274d588564420ccff2fdd420d43a23c9667f8a36c2d1ff56159dcb51af1effc'
GFAY_FULL_CB_SECTION_FILE='gfay-butcher-crushbone-preline-carbon-sections-v1.json'
GFAY_FULL_CB_SECTION_SHA256='5a7253238acc541c65de2479f5be751cb7ffd249a8e79d386a226976b37eee57'

_SECTION_SPECS={
    'goblin-camp':('butcher-camps-20261114',SECTION_FILE,SECTION_SHA256),
    'goblin-camp-stop':('butcher-camps-20261114',SECTION_FILE,SECTION_SHA256),
    'butcher-gfay-preline-stop':('butcher-gfay-carbon-20261115',BUTCHER_GFAY_SECTION_FILE,BUTCHER_GFAY_SECTION_SHA256),
    'butcher-gfay-crossing':('butcher-gfay-carbon-20261115',BUTCHER_GFAY_SECTION_FILE,BUTCHER_GFAY_SECTION_SHA256),
    'gfay-orc-camps':('gfay-camps-carbon-20261115',GFAY_ORC_SECTION_FILE,GFAY_ORC_SECTION_SHA256),
    'gfay-orc-camps-stop':('gfay-camps-carbon-20261115',GFAY_ORC_SECTION_FILE,GFAY_ORC_SECTION_SHA256),
    'gfay-crushbone-preline-stop':('gfay-camps-carbon-20261115',GFAY_CB_SECTION_FILE,GFAY_CB_SECTION_SHA256),
    'gfay-crushbone-crossing':('gfay-camps-carbon-20261115',GFAY_CB_SECTION_FILE,GFAY_CB_SECTION_SHA256),
    'gfay-butcher-crushbone-preline-stop':('gfay-camps-carbon-20261115',GFAY_FULL_CB_SECTION_FILE,GFAY_FULL_CB_SECTION_SHA256),
    'gfay-butcher-crushbone-crossing':('gfay-camps-carbon-20261115',GFAY_FULL_CB_SECTION_FILE,GFAY_FULL_CB_SECTION_SHA256),
}


def load_owner_walking_sections(engine,destination):
    if type(destination) is not SourceDestinationAssets:
        raise ValueError('Actual source destination required for walking sections')
    if destination.destination_id not in _SECTION_SPECS:return None
    destination.check()
    result=load_guide_walking_sections(destination.destination_id,destination.guide)
    destination.check()
    return result


def load_guide_walking_sections(destination_id,guide,*,root=None):
    """Load the same pinned partition for an actual selected camp guide."""
    if destination_id not in _SECTION_SPECS:return None
    data_name,filename,expected_sha256=_SECTION_SPECS[destination_id]
    directory=(Path.home()/'.local/share/eql-automation/owner-route-data'/data_name
               if root is None else Path(root))
    path=directory/filename
    if path.is_symlink() or not path.is_file() or path.stat().st_size>2_000_000:
        raise ValueError('Pinned Goblin walking-section file unavailable')
    raw=path.read_bytes()
    if sha256(raw).hexdigest()!=expected_sha256:raise ValueError('Goblin walking-section file changed')
    record=json.loads(raw)
    if (record['format']!='eql-offline-goblin-sections-audit-v1' or not record['source_candidate']
            or record['current_character_observation'] or record['input_authorized']
            or record['real_client_accepted'] or record['runtime_continuation_enabled']):
        raise ValueError('Copied section proposals cannot claim live input authority')
    return parse_walking_sections(guide,record['result'])
