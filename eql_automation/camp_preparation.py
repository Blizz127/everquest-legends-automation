"""Serialized spell preparation using the retained catalog and client log replies.

No silence-based success. Slots are attributed to the sole submitted command;
client log messages themselves contain spell names, not gem numbers.
"""
from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from .location_log import parse_client_log_line

EXPORT_COMMAND = '/outputfile spellbook eql-rotation-spellbook.txt'
EXPORT_REPLY = 'Outputfile Complete: eql-rotation-spellbook.txt'


def file_identity(path):
    try:
        s=path.stat()
        return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    except FileNotFoundError:
        return None


class PreparationCatalog:
    def __init__(self,game_dir,client):
        self.game_dir=Path(game_dir)
        self.paths=tuple(self.game_dir/name for name in ('spells_us.txt','spells_us_str.txt'))
        self.identities=tuple(file_identity(p) for p in self.paths)
        if self.identities[0] is None:raise ValueError('Installed spell catalog is missing')
        self.catalog=client.Catalog.load(self.game_dir)
        self.source_sha256={p.name:sha256(p.read_bytes()).hexdigest() if identity else None
                            for p,identity in zip(self.paths,self.identities)}
        self.check()

    def check(self):
        if tuple(file_identity(p) for p in self.paths)!=self.identities:
            raise ValueError('Installed spell data changed during camp')


@dataclass
class CampPreparation:
    level: int
    generation: int
    started: float
    export: Path
    source: object
    slots: dict
    phase: str='export'
    previous_export: tuple | None=None
    reply_after: int=0
    reply_wall: datetime | None=None
    deadline: float=0.
    wait_until: float=0.
    export_logged: bool=False
    export_sha256: str | None=None
    known: set=field(default_factory=set)
    profile: dict=field(default_factory=dict)
    gems: tuple=()
    index: int=0
    clear_slot: int=1
    began: int | None=None
    receipts: list=field(default_factory=list)
    clears_submitted: list=field(default_factory=list)
    clear_reply_after: int | None=None
    clear_reply_wall: datetime | None=None
    last_stamp: datetime | None=None

    def __post_init__(self):
        self.previous_export=file_identity(self.export)
        self.deadline=self.started+10.

    def command(self,now):
        if now<self.wait_until:return None
        if self.phase=='export':return EXPORT_COMMAND
        if self.phase=='clear':return f'/memspellslot {self.clear_slot} 0'
        if self.phase=='memorize':
            slot,spell=self.gems[self.index]
            return f'/memspellslot {slot} {spell.id}'
        return None

    def submitted(self,command,seq,now,wall):
        if command!=self.command(now):raise ValueError('Preparation command no longer matches the pending slot')
        self.reply_after=seq;self.reply_wall=wall
        if self.phase=='export':
            self.phase='await_export';self.deadline=now+10.
        elif self.phase=='clear':
            if self.clear_reply_after is None:self.clear_reply_after=seq;self.clear_reply_wall=wall
            self.clears_submitted.append(self.clear_slot);self.clear_slot+=1
            if self.clear_slot>8:self.phase='clear_settle';self.wait_until=now+1.
        else:
            self.phase='await_gem';self.began=None;self.deadline=now+60.

    def observe(self,raw,seq,now,client):
        parsed=parse_client_log_line(raw)
        if parsed is None:raise ValueError('Malformed preparation log record')
        stamp,body=parsed
        if self.last_stamp is not None and stamp<self.last_stamp:
            raise ValueError('Preparation log time moved backward')
        self.last_stamp=stamp
        event=client.MEMORIZE_EVENT.fullmatch(body)
        if client.MEM_FAILURE.match(body):raise ValueError('Client rejected preparation: '+body)
        if body!=EXPORT_REPLY and not event:return
        if event and event.lastgroup=='forget' and self.phase in {'clear','clear_settle'}:
            if (self.clear_reply_after is None or seq<=self.clear_reply_after or
                    stamp<self.clear_reply_wall.replace(microsecond=0)):
                raise ValueError('Spell changed before the first clear request')
            return  # Acknowledges a forgotten name, never proves an empty slot.
        if self.reply_wall is None or seq<=self.reply_after or stamp<self.reply_wall.replace(microsecond=0):
            raise ValueError('Preparation reply predates the submitted command')
        if body==EXPORT_REPLY:
            if self.phase!='await_export' or self.export_logged:raise ValueError('Unexpected spellbook export reply')
            self.export_logged=True;return
        kind=event.lastgroup;name=event.group(kind)
        if self.phase!='await_gem' or now>self.deadline:
            raise ValueError('Unrequested or late spell-gem change')
        slot,spell=self.gems[self.index]
        if name.casefold()!=spell.name.casefold():raise ValueError('Memorization named a different spell')
        if kind=='begin' and self.began is None:
            self.began=seq;return
        if kind!='finish' or self.began is None or seq<=self.began:
            raise ValueError('A fresh matching begin must precede the memorization finish')
        self.receipts.append(dict(slot=slot,spell_id=spell.id,spell_name=spell.name,
            submitted_after=self.reply_after,begin_seq=self.began,finish_seq=seq,
            slot_source='sole_outstanding_command',slot_named_in_log=False))
        self.index+=1
        if self.index==len(self.gems):self.phase='settle';self.wait_until=now+1.
        else:self.phase='memorize'

    def advance(self,now):
        self.source.check()
        if now-self.started>600:raise ValueError('Spell preparation exceeded ten minutes')
        if self.phase in {'await_export','await_gem'} and now>self.deadline:
            raise ValueError('No complete fresh '+('export' if self.phase=='await_export' else 'begin/finish')+' acknowledgment')
        if self.phase=='await_export' and self.export_logged:
            before=file_identity(self.export)
            if before is None or before==self.previous_export:return
            if not 0<before[2]<=1024*1024:raise ValueError('Spellbook export size is unsupported')
            raw=self.export.read_bytes()
            if file_identity(self.export)!=before:raise ValueError('Spellbook export changed while being read')
            self.known=self.source.catalog.parse_book(raw.decode('utf-8',errors='replace'))
            self.profile=self.source.catalog.profile(self.level,self.known)
            if 'quick_heal' not in self.profile or 'nuke' not in self.profile:
                raise ValueError('Fresh learned spellbook lacks a usable heal and damage spell')
            self.gems=tuple(sorted(((self.slots[role],spell) for role,spell in self.profile.items()),key=lambda pair:pair[0]))
            if (len({slot for slot,spell in self.gems})!=len(self.gems) or
                    len({spell.id for slot,spell in self.gems})!=len(self.gems) or
                    any(type(slot) is not int or not 1<=slot<=8 or type(spell.id) is not int or
                        spell.id<=0 or spell.id not in self.known for slot,spell in self.gems)):
                raise ValueError('Prepared spell profile has invalid or duplicate gem assignments')
            self.export_sha256=sha256(raw).hexdigest();self.phase='clear'
        elif self.phase=='clear_settle' and now>=self.wait_until:self.phase='memorize'
        elif self.phase=='settle' and now>=self.wait_until:self.phase='ready'

    def snapshot(self):
        return dict(level=self.level,phase=self.phase,export_sha256=self.export_sha256,
            catalog_sha256=self.source.source_sha256,clears_submitted=self.clears_submitted,
            clear_completion_verified=False,gem_receipts=self.receipts,
            silent_success_allowed=False,slot_named_in_log=False)
