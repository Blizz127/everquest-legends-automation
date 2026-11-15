"""Pinned owner-log search names; historical evidence never grants combat.

Selection/kill pairs are kept separate from prior NPC/consider/kill history.
Only the owner-supervised camp loader uses this fallback, after both qualified
sources. Its existing fresh consideration and cancellation checks still apply.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat

from .location_log import parse_client_log_line, is_logging_boundary
from .camp_session import NpcCandidate, _TARGET, _PROTECTED, _MISS
from .camp_recovery import EXE_PIN
from .camp_candidate_history import SOURCE_SERVER, MAX_HISTORY_BYTES

SOURCE_PIN = 'bd09c3cd11bee073e1550e4f8516644754f4e30630e7115cbdb767212753963c'
SEARCH_NAME = 'owner-npc-search-suggestions-20261115-v1.json'
SEARCH_PIN = '6aaa75110d27a4b9fd5f9de1589ea8bd95c1f5f5e2934869fa8dfd64ffb7f368'
MAX_SOURCE_BYTES = 4 * 1024 * 1024
MAX_PAIR_SECONDS = 150
EVIDENCE_KIND = 'npc_selection_owner_kill'

_OWN_KILL = re.compile(r'You have slain (.+)!\Z')
_ENTERED = re.compile(r'You have entered (.+)\.\Z')
_CONTINUITY_BREAKS = ('LOADING, PLEASE WAIT', 'You have been slain',
                      'You died', 'You die.', 'You die!', 'Returning to ')


def extract_search_suggestions(raw: bytes, zone_name: str, *, valid_name, excluded=()):
    """Extract search names from complete records of one immutable snapshot.

    Matching is exact after case folding (the client varies capitalization),
    never substring, prefix, fuzzy, or /consider-derived. Source line numbers
    are 1-based raw newline records. Malformed records lose zone continuity.
    """
    if not isinstance(raw, bytes) or len(raw) > MAX_SOURCE_BYTES:
        raise ValueError('Expected bounded immutable source bytes')
    if not isinstance(zone_name, str) or not zone_name:
        raise ValueError('An exact zone display name is required')
    denied = {name.casefold() for name in excluded}
    chunks = raw.split(b'\n')
    trailing = chunks.pop()  # Never parse even a valid-looking partial record.
    audit = dict(complete_lines=len(chunks), trailing_bytes_ignored=len(trailing),
                 malformed_records=0, backward_timestamps=0, rejected_stale_pairs=0,
                 mismatched_owner_kills=0, excluded_selections=0)
    zone = None
    zone_entry_line = None
    selected = None
    last_stamp = None
    records = {}
    for line_number, raw_line in enumerate(chunks, 1):
        try:
            parsed = parse_client_log_line(raw_line.decode('utf-8', errors='strict'))
        except UnicodeDecodeError:
            parsed = None
        if parsed is None:
            zone = selected = zone_entry_line = last_stamp = None
            audit['malformed_records'] += 1
            continue
        stamp, body = parsed
        if last_stamp is not None and stamp < last_stamp:
            zone = selected = zone_entry_line = None
            last_stamp = stamp
            audit['backward_timestamps'] += 1
            continue
        last_stamp = stamp
        if is_logging_boundary(body) or body.startswith(_CONTINUITY_BREAKS):
            zone = selected = zone_entry_line = None
            continue
        entered = _ENTERED.fullmatch(body)
        if entered:
            zone, zone_entry_line, selected = entered[1], line_number, None
            continue
        if zone != zone_name:
            continue
        target = _TARGET.fullmatch(body)
        if target:
            selected = None  # PC/Pet/other NPC replaces the previous receipt.
            name = target[2].strip()
            if target[1] == 'NPC':
                if valid_name(name) and name.casefold() not in denied and not _PROTECTED.search(name):
                    selected = (name, stamp, line_number, zone_entry_line)
                else:
                    audit['excluded_selections'] += 1
            continue
        if body in _MISS:
            selected = None
            continue
        killed = _OWN_KILL.fullmatch(body)
        if not killed:
            continue
        receipt, selected = selected, None  # One selection proves at most one pair.
        if receipt is None:
            continue
        name, selected_at, selection_line, entered_line = receipt
        if killed[1].casefold() != name.casefold():
            audit['mismatched_owner_kills'] += 1
            continue
        elapsed = (stamp - selected_at).total_seconds()
        if not 0 <= elapsed <= MAX_PAIR_SECONDS:
            audit['rejected_stale_pairs'] += 1
            continue
        row = records.setdefault(name.casefold(), dict(
            name=name, levels=[], pairs=[],
            evidence_kind='npc_selection_owner_kill',
            prior_consideration_claimed=False, current_target_authorized=False,
            selection_kill_pairs=[]))
        row['selection_kill_pairs'].append(dict(
            zone_entry_line=entered_line, selection_line=selection_line,
            kill_line=line_number, selection_kind='NPC',
            selection_time=selected_at.isoformat(), kill_time=stamp.isoformat(),
            elapsed_seconds=int(elapsed)))
    return dict(source_log_sha256=sha256(raw).hexdigest(), source_bytes=len(raw),
                client_timestamp_timezone='unverified_local',
                max_pair_seconds=MAX_PAIR_SECONDS,
                current_target_authorized=False, prior_consideration_claimed=False,
                candidates=[records[key] for key in sorted(records)], audit=audit)


def read_pinned_regular_file(path: Path, expected: str, limit=MAX_SOURCE_BYTES):
    """Read one immutable bounded snapshot, rejecting symlinks and changed data."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise ValueError('Pinned source must be a regular file')
        raw = source.read(limit + 1)
    if len(raw) > limit or sha256(raw).hexdigest() != expected:
        raise ValueError('Pinned source changed or exceeded its limit')
    return raw


def build_owner_search_history(path, client):
    """Reproduce the retained owner snapshot, preserving only search evidence."""
    raw = read_pinned_regular_file(Path(path), SOURCE_PIN)
    guide = client.default_guide()
    excluded = [t.name for c in guide.camps for t in c.targets if t.avoid]
    result = extract_search_suggestions(raw, guide.zone_long('butcher'),
        valid_name=client.valid_target_name, excluded=excluded)
    result.update(format='eql-owner-npc-search-suggestions-v1',
        server=SOURCE_SERVER, client_sha256=EXE_PIN, zone='butcher',
        zone_long=guide.zone_long('butcher'),
        origin='retained_owner_log_ordered_selection_kill',
        qualification='search_suggestion_only_not_prior_considered')
    payload = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
    if len(payload) > MAX_HISTORY_BYTES:
        raise ValueError('Owner search history exceeds its limit')
    return payload


def load_owner_search_candidates(server, zone, *, client, excluded=(), store=None):
    """Optional exact-zone fallback; never seeds a current target or its level."""
    if server != SOURCE_SERVER or zone != 'butcher':
        return ()
    store = Path.home()/'.local/share/eql-automation' if store is None else Path(store)
    try:
        raw = read_pinned_regular_file(store/'owner-route-data'/SEARCH_NAME,
                                      SEARCH_PIN, MAX_HISTORY_BYTES)
    except FileNotFoundError:
        return ()
    record = json.loads(raw)
    if (record['format'] != 'eql-owner-npc-search-suggestions-v1' or
            record['server'] != server or record['zone'] != zone or
            record['zone_long'] != client.default_guide().zone_long(zone) or
            record['client_sha256'] != EXE_PIN or record['source_log_sha256'] != SOURCE_PIN or
            record['current_target_authorized'] is not False or
            record['prior_consideration_claimed'] is not False):
        raise ValueError('Owner search history provenance mismatch')
    denied = {name.casefold() for name in excluded}
    result = []
    for row in record['candidates']:
        if (row['levels'] != [] or row['pairs'] != [] or
                row['evidence_kind'] != EVIDENCE_KIND or
                row['current_target_authorized'] is not False or
                row['prior_consideration_claimed'] is not False):
            raise ValueError('Owner search evidence was misclassified')
        name = row['name']
        if (not client.valid_target_name(name) or name.casefold() in denied or
                _PROTECTED.search(name)):
            continue
        provenance = tuple((p['zone_entry_line'], p['selection_line'], p['kill_line'])
                           for p in row['selection_kill_pairs'])
        if not provenance or any(not all(type(n) is int for n in p)
                                 or not 0 < p[0] < p[1] < p[2] for p in provenance):
            raise ValueError('Owner search evidence has no ordered selection/kill pair')
        result.append(NpcCandidate(name, (), SOURCE_PIN, (),
            'retained_owner_selection_kill', SEARCH_PIN, EVIDENCE_KIND, provenance))
    return tuple(result)
