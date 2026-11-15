"""Pinned copied Goblin route partition; each actual arrival is checked afresh."""
from hashlib import sha256
import json
from pathlib import Path

from .owner_source_assets import SourceDestinationAssets
from .source_section_manifest import parse_walking_sections


SECTION_FILE='butcher-goblin-sections-v1.json'
SECTION_SHA256='65c97d4cd1a4cefd0213877a602cc1276cd3e64d36a156b2a424859bd651d04c'


def load_owner_walking_sections(engine,destination):
    if type(destination) is not SourceDestinationAssets:
        raise ValueError('Actual source destination required for walking sections')
    if destination.destination_id not in ('goblin-camp','goblin-camp-stop'):return None
    destination.check()
    path=Path.home()/'.local/share/eql-automation/owner-route-data/butcher-camps-20261114'/SECTION_FILE
    if path.is_symlink() or not path.is_file() or path.stat().st_size>2_000_000:
        raise ValueError('Pinned Goblin walking-section file unavailable')
    raw=path.read_bytes()
    if sha256(raw).hexdigest()!=SECTION_SHA256:raise ValueError('Goblin walking-section file changed')
    record=json.loads(raw)
    if (record['format']!='eql-offline-goblin-sections-audit-v1' or not record['source_candidate']
            or record['current_character_observation'] or record['input_authorized']
            or record['real_client_accepted'] or record['runtime_continuation_enabled']):
        raise ValueError('Copied section proposals cannot claim live input authority')
    result=parse_walking_sections(destination.guide,record['result'])
    destination.check()
    return result
