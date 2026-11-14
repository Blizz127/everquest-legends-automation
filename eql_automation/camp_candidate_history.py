"""Names derived from pinned owner history, never live target permission.

Only a reduced private artifact is deployed; no chat or other-player log data.
Its server and client build remain fixed. Current character history wins.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import os
import stat

from .camp_recovery import EXE_PIN
from .camp_session import NpcCandidate, _PROTECTED, observed_candidates

HISTORY_NAME = 'owner-npc-candidates-20261113-v1.json'
HISTORY_PIN = '0d43373b543d09a41e43f76aa42bfee9e6d892dda898ea238a4cac2fe8d73676'
SOURCE_LOG_PIN = 'd622b3c12567f903d411860d3de1a0be28e4e8b38be7bbdc2bebfdd62c60f04e'
SOURCE_SERVER = 'freeport'
MAX_HISTORY_BYTES = 256 * 1024


def build_owner_history(path, client):
    """Reproduce only the already retained owner log, without copying raw lines."""
    path = Path(path)
    if path.is_symlink():
        raise ValueError('Retained owner log must be a direct file')
    with path.open('rb') as source:
        raw = source.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024 or sha256(raw).hexdigest() != SOURCE_LOG_PIN:
        raise ValueError('Retained owner log changed')
    guide = client.default_guide()
    excluded = [t.name for c in guide.camps for t in c.targets if t.avoid]
    zones = []
    for zone in ('gfaydark', 'crushbone', 'butcher'):
        rows = observed_candidates(path, guide.zone_long(zone),
            consider=client.consider_target, safe=client.safe_leveling_target, excluded=excluded)
        if any(c.source_sha256 != SOURCE_LOG_PIN for c in rows):
            raise ValueError('Retained owner log changed during extraction')
        zones.append(dict(zone=zone, zone_long=guide.zone_long(zone), candidates=[
            dict(name=c.name, levels=c.levels, pairs=c.pairs) for c in rows]))
    with path.open('rb') as source:
        if source.read(4 * 1024 * 1024 + 1) != raw:
            raise ValueError('Retained owner log changed during extraction')
    record = dict(format='eql-owner-npc-history-v1', server=SOURCE_SERVER,
        client_sha256=EXE_PIN, source_log_sha256=SOURCE_LOG_PIN, source_bytes=len(raw),
        current_target_authorized=False, zones=zones)
    result = (json.dumps(record, indent=2, sort_keys=True)+'\n').encode()
    if len(result) > MAX_HISTORY_BYTES:
        raise ValueError('Reduced owner history exceeds its limit')
    return result


def load_owner_candidates(server, zone, *, client, excluded=(), store=None):
    """Return immutable search suggestions for this exact server and zone.

    A missing optional artifact supplies no candidates. A changed one refuses;
    it must not silently replace current-character evidence or live checks.
    The camp's existing executable binding verifies the installed client.
    """
    if server != SOURCE_SERVER or zone not in {'gfaydark', 'crushbone', 'butcher'}:
        return ()
    store = Path.home()/'.local/share/eql-automation' if store is None else Path(store)
    path = store/'owner-route-data'/HISTORY_NAME
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise ValueError('Owner NPC history must be a regular file')
            raw = source.read(MAX_HISTORY_BYTES + 1)
    except FileNotFoundError:
        return ()
    if len(raw) > MAX_HISTORY_BYTES or sha256(raw).hexdigest() != HISTORY_PIN:
        raise ValueError('Owner NPC history changed')
    record = json.loads(raw)
    if (record['format'] != 'eql-owner-npc-history-v1' or record['server'] != server or
            record['client_sha256'] != EXE_PIN or record['source_log_sha256'] != SOURCE_LOG_PIN or
            record['current_target_authorized'] is not False):
        raise ValueError('Owner NPC history provenance mismatch')
    denied = {name.casefold() for name in excluded}
    rows = [entry for entry in record['zones'] if entry['zone'] == zone]
    if len(rows) != 1 or rows[0]['zone_long'] != client.default_guide().zone_long(zone):
        raise ValueError('Owner NPC history zone mismatch')
    return tuple(NpcCandidate(c['name'], tuple(c['levels']), SOURCE_LOG_PIN,
        tuple(tuple(p) for p in c['pairs']), 'retained_owner_history', HISTORY_PIN)
        for c in rows[0]['candidates'] if client.valid_target_name(c['name']) and
        c['name'].casefold() not in denied and not _PROTECTED.search(c['name']))
