"""Bounded stationary camp state, using observed NPC names as search candidates.

History supplies names, never a current target, encounter safety or current
character level. A successful session means one matching client kill message;
it does not establish loot completion or unattended leveling acceptance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
import math
from pathlib import Path
import re

from .location_log import parse_client_log_line, is_logging_boundary
from .prior_rotation_core import level_from_message
from .telemetry import LOOT_NO_ROOM, FOOD_DRINK_WARNINGS, LOG_GAIN

_TARGET = re.compile(r"Targeted \(([^)]+)\):\s*(.+)\Z")
_PROTECTED = re.compile(r"\b(?:slave|prisoner|captive|pet|merchant|banker|guard|trainer|vendor)\b", re.I)
_MISS = {"I don't see anyone by that name around here...", "Target not found nearby.", "Consider whom?"}


@dataclass(frozen=True)
class NpcCandidate:
    name: str
    levels: tuple[int, ...]
    source_sha256: str
    pairs: tuple[tuple[int, int], ...]


def observed_candidates(path: Path, zone_name: str, *, consider, safe, excluded=(), max_bytes=4*1024*1024):
    """Read a bounded suffix of the owner's log; require NPC/con pairs and kills.

    The first partial line and any interval without an exact entered-zone line
    are ignored. The hash covers the exact bounded bytes, not the whole file.
    """
    with path.open('rb') as source:
        source.seek(0, 2); end = source.tell(); offset = max(0, end-max_bytes)
        source.seek(offset); raw = source.read(max_bytes)
    lines = raw.decode('utf-8', errors='replace').splitlines()
    if offset:
        lines = lines[1:]
    pin = sha256(raw).hexdigest()
    denied = {name.casefold() for name in excluded}
    zone = None; selected = None; records = {}; killed = set()
    for number, line in enumerate(lines, 1):
        parsed = parse_client_log_line(line)
        if parsed is None:
            continue
        at, body = parsed
        if body.startswith('You have entered ') and body.endswith('.'):
            zone = body[len('You have entered '):-1]; selected = None
        if is_logging_boundary(body):
            zone = None; selected = None
        if zone != zone_name:
            continue
        target = _TARGET.fullmatch(body)
        if target:
            selected = (target[2].strip(), at, number) if target[1] == 'NPC' else None
        reply = consider(body)
        if reply and selected:
            name, reaction, level = reply
            if (name.casefold() == selected[0].casefold() and
                    0 <= (at-selected[1]).total_seconds() <= 10 and
                    type(level) is int and 1 <= level <= 50 and
                    name.casefold() not in denied and not _PROTECTED.search(name) and
                    safe(name, reaction, 'NPC', level, level)):
                row = records.setdefault(name.casefold(), [name, set(), []])
                row[1].add(level); row[2].append((selected[2], number))
        if body.startswith('You have slain '):
            killed.add(body[len('You have slain '):].rstrip('!.').casefold())
    return tuple(NpcCandidate(name, tuple(sorted(levels)), pin, tuple(pairs))
                 for key, (name, levels, pairs) in sorted(records.items()) if key in killed)


@dataclass
class StationaryCamp:
    candidates: tuple[NpcCandidate, ...]
    level: int
    generation: int
    started: float
    zone: str | None
    repeat: bool=False
    target_level: int=20
    phase: str = 'select'
    reason: str = ''
    state: str = 'running'
    index: int = 0
    requested: str | None = None
    reply_after: int = 0
    reply_started: float = 0.
    reply_wall: datetime | None = None
    grant_until: float = 0.
    killed_at: float | None = None
    kills: int = 0
    loot_messages: int = 0
    engaged_name: str | None = None
    last_progress: float | None = None
    encounter_started: float | None = None
    pending_level: int | None = None
    level_reply_pending: bool = False
    engaged_after: int = 0
    engaged_wall: datetime | None = None
    completed_kills: set = field(default_factory=set)
    level_source: str='owner_configuration'
    wait_until: float=0.
    empty_since: float | None=None
    recovery: object | None=None
    inventory_full: bool | None=None
    rest_count: int=0
    round_number: int=0
    xp_awards: list[float] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    camp = None
    paused = False

    @property
    def mode(self):
        return 'stationary_repeat' if self.repeat else 'stationary_one_kill'

    @property
    def session_seconds(self):
        return 14400 if self.repeat else 240

    @property
    def running(self):
        return self.state == 'running'

    def stop(self, reason):
        self.state = 'off'; self.reason = str(reason); self.grant_until = 0.

    def record(self, event, **values):
        self.evidence.append(dict(event=event, **values))

    def next_candidate(self,now=None):
        self.grant_until = 0.
        if self.index >= len(self.candidates):
            if self.repeat:
                if now is None:raise ValueError('Repeated candidate sweep requires a clock')
                self.empty_since=now if self.empty_since is None else self.empty_since
                if now-self.empty_since>900:
                    self.stop('No eligible target found for fifteen minutes; camp needs a new location')
                else:
                    self.phase='waiting_respawn';self.wait_until=now+30.
                return None
            self.stop('No observed candidate passed the current nearby-target check'); return None
        candidate = self.candidates[self.index]; self.index += 1
        self.requested = candidate.name
        self.engaged_name = None
        self.phase = 'target'
        return candidate.name

    def reset_round(self):
        self.index=0;self.requested=self.engaged_name=None
        self.reply_after=0;self.reply_started=0.;self.reply_wall=None
        self.level_reply_pending=False;self.engaged_after=0;self.engaged_wall=None
        self.grant_until=0.;self.killed_at=self.last_progress=self.encounter_started=None
        self.recovery=None;self.phase='select'

    def expect_reply(self, seq, now, wall):
        self.phase = 'consider'; self.reply_after = seq
        self.reply_started = now; self.reply_wall = wall
        self.grant_until = 0.

    def authorized(self, now):
        return self.running and self.phase == 'fight' and now < self.grant_until

    def observe(self, raw, seq, now, wall, *, consider, safe):
        if not self.running:
            return
        parsed = parse_client_log_line(raw)
        if parsed is None:
            self.stop('Malformed log line during camp'); return
        stamp, body = parsed
        if not -1 <= (wall-stamp).total_seconds() <= 3:
            self.stop('Delayed or future log line during camp'); return
        level=level_from_message(raw)
        if level is not None and self.repeat:
            if level<max(self.level,self.pending_level or 0) or level>50:
                self.stop('Unexpected level change');return
            self.pending_level=level;self.grant_until=0.
            if self.phase=='consider':self.level_reply_pending=True
            elif self.phase in {'fight','probe'}:self.phase='probe'
            self.record('level_observed',level=level,seq=seq)
            return
        if (is_logging_boundary(body) or body.startswith(('You have entered ', 'LOADING, PLEASE WAIT',
                'You have been slain', 'You died', 'You die.', 'You die!', 'You have gained ', 'You LOST ', 'Returning to '))):
            self.stop('Character, logging or zone boundary during camp'); return
        if body == 'Auto attack is on.':
            self.stop('Native melee became active; camp does not own its toggle'); return
        if body == 'Your attack failed because your target is Encounter Locked to someone else.':
            self.stop('Encounter belongs to someone else'); return
        if body in {'You cannot see your target.', 'Your target is out of range, get closer!',
                    'Your target is too far away, get closer!', 'You must be standing to cast a spell.'}:
            self.stop('Stationary target cannot be reached from the current posture/position'); return
        incoming = re.match(r"^([A-Za-z][A-Za-z '\-]{0,79}) (?:[a-z]+ YOU for \d+ points? of damage|tries to [a-z ]+ YOU, but )", body)
        engaged=self.phase in {'fight','probe','consider'} and self.engaged_name is not None and self.killed_at is None
        if incoming and (not engaged or incoming[1].casefold() != (self.requested or '').casefold()):
            self.stop('An additional attacker was observed'); return
        if body in LOOT_NO_ROOM or body.startswith('There was no room in your inventory') or body.startswith('Your inventory is full.'):
            self.inventory_full=True;self.stop('Loot did not fit; inventory service required');return
        if self.repeat and body in FOOD_DRINK_WARNINGS:
            self.stop('Food/drink warning; supplies require service');return
        if self.repeat and body=='That is not a valid command.':
            self.stop('Client rejected a camp command');return
        selected = _TARGET.fullmatch(body)
        if selected and (selected[1] != 'NPC' or selected[2].strip().casefold() != (self.requested or '').casefold()):
            self.stop('Another target was selected'); return
        if body in _MISS:
            if self.phase in {'target', 'consider'} and self.engaged_name is None:
                self.phase = 'select'; self.grant_until = 0.
            else:
                self.stop('Current target was lost')
            return
        reply = consider(body)
        if reply:
            if self.phase != 'consider' or seq <= self.reply_after:
                self.stop('Unrequested consideration reply'); return
            if now-self.reply_started > 6:
                self.stop('Consideration reply exceeded its deadline'); return
            if self.reply_wall is None or stamp < self.reply_wall.replace(microsecond=0):
                self.stop('Consideration reply predates the request'); return
            name, reaction, level = reply
            if self.level_reply_pending:
                self.level_reply_pending=False;self.phase='probe'
                self.record('pre_level_consideration_discarded',seq=seq)
                return
            allowed = (name.casefold() == (self.requested or '').casefold() and
                       type(level) is int and max(1, self.level-3) <= level <= self.level and
                       safe(name, reaction, 'Unknown', level, self.level))
            self.record('considered', name=name, level=level, accepted=allowed, seq=seq)
            if allowed:
                self.phase = 'fight'; self.grant_until = now+6.
                if self.engaged_name is None:
                    self.last_progress = now;self.encounter_started=now;self.round_number+=1
                    self.engaged_after=seq;self.engaged_wall=stamp
                    self.empty_since=None
                self.engaged_name = name
            else:
                if self.engaged_name is not None:
                    self.stop('Engaged target no longer passes consideration')
                else:
                    self.phase = 'select'; self.grant_until = 0.
            return
        damage = re.fullmatch(r'You hit (.+?) for \d+ points? of [a-z -]+ damage by .+\.', body)
        if damage and damage[1].casefold() == (self.engaged_name or '').casefold():
            self.last_progress = now
        slain_by = re.fullmatch(r'(.+?) has been slain by .+!', body)
        if slain_by and slain_by[1].casefold() == (self.engaged_name or '').casefold():
            self.stop('Another killer was reported for the engaged target'); return
        if body.startswith('You have slain ') and self.engaged_name is not None:
            name = body[len('You have slain '):].rstrip('!.')
            if name.casefold() == (self.requested or '').casefold():
                identity=(stamp,body.casefold())
                if identity in self.completed_kills or self.killed_at is not None:return
                if seq<=self.engaged_after or self.engaged_wall is None or stamp<self.engaged_wall:
                    self.stop('Kill predates the current engagement');return
                self.completed_kills.add(identity)
                self.kills += 1; self.phase = 'loot_observation'; self.killed_at = now
                self.grant_until = 0.; self.record('matching_kill', name=name, seq=seq,round=self.round_number)
            else:
                self.stop('Kill message did not match the camp target')
        if self.phase == 'loot_observation' and body.startswith('--You have looted '):
            self.loot_messages += 1
        award = LOG_GAIN.fullmatch(body)
        if award:
            value = float(award[1])
            if math.isfinite(value):
                self.xp_awards.append(value)

    # Retained engine protocol. Its legacy navigation programs are never started.
    def on_line(self, *args, **kwargs): pass
    def target_names(self): return frozenset({self.requested.casefold()}) if self.requested else frozenset()
    def accepts(self, name, level, now): return self.authorized(now) and name.casefold() == (self.requested or '').casefold()
    def vetoes(self, now): return True
    def holds_combat(self, now): return not self.authorized(now)
    def recovers_from_death(self): return False
    def expecting_zone(self, now): return False

    def snapshot(self):
        return dict(state=self.state, phase=self.phase, reason=self.reason, mode=self.mode,
            zone=self.zone, loc=None, camp=None, kills=self.kills, calibrated=False,
            inventory_full=self.inventory_full, con_window=[max(1, self.level-3), self.level],
            loot_messages=self.loot_messages, loot_completion_verified=False,
            logged_xp_awards=self.xp_awards, current_xp=None,level=self.level,level_source=self.level_source,
            target_level=self.target_level,rest_count=self.rest_count,round_number=self.round_number,
            posture_requested=getattr(self.recovery,'posture_requested',None),posture_observed=None,
            candidates=[dict(name=c.name, source_sha256=c.source_sha256, pairs=c.pairs) for c in self.candidates],
            evidence=self.evidence)
