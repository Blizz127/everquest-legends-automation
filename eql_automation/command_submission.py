"""Immutable records of a fixed command's pinned-descriptor submissions.

These are kernel write receipts, not client delivery, text or focus evidence.
The surrounding executor serializes mutations with its existing stop lock.
Failed writes latch uncertainty; later release retries never repair a prefix.
Other writers (including the original sender's F9 releases) are outside this
scope's journal; generation and independent input/focus checks remain required.
"""
from dataclasses import dataclass
import math


LOCATION_COMMAND = '/location'
LOCATION_KEYS = (53,38,24,46,30,20,23,24,49,28)
LOCATION_EVENTS = tuple(event for code in LOCATION_KEYS for event in
                        ((1,code,1),(0,0,0),(1,code,0),(0,0,0)))


@dataclass(frozen=True)
class CommandWriteAttempt:
    index: int
    event: tuple[int,int,int]
    started_at: float | None
    finished_at: float | None
    expected_bytes: int
    written_bytes: int | None
    outcome: str
    error: str | None = None

    @property
    def complete(self):
        return (self.outcome=='complete' and self.written_bytes==self.expected_bytes
                and all(type(value) in (int,float) and math.isfinite(value)
                        for value in (self.started_at,self.finished_at))
                and self.started_at<=self.finished_at)


@dataclass(frozen=True)
class CommandSubmissionSnapshot:
    operation_id: str
    revision: int
    command: str
    writes: tuple[CommandWriteAttempt,...]
    attempted_key_codes: tuple[int,...]
    submitted_prefix: str
    submitted_key_count: int
    enter_submitted: bool
    uncertain: bool
    next_key_code: int | None
    client_delivery_verified: bool = False
    client_focus_verified: bool = False


class CommandSubmissionJournal:
    def __init__(self, operation_id):
        if not isinstance(operation_id,str) or not operation_id:
            raise ValueError('A command operation identity is required')
        self.operation_id=operation_id
        self.revision=0
        self._writes=[]

    def begin(self,event,started_at,expected_bytes):
        attempt=CommandWriteAttempt(len(self._writes),tuple(event),started_at,None,
                                    expected_bytes,None,'pending')
        self._writes.append(attempt)
        self.revision+=1
        return attempt

    def finish(self,attempt,finished_at,*,written_bytes=None,outcome,error=None):
        if self._writes[attempt.index] is not attempt:
            raise RuntimeError('Command write attempt already completed')
        self._writes[attempt.index]=CommandWriteAttempt(attempt.index,attempt.event,
            attempt.started_at,finished_at,attempt.expected_bytes,written_bytes,outcome,error)
        self.revision+=1

    def snapshot(self):
        writes=tuple(self._writes)
        progress=0
        uncertain=False
        last_finished=None
        for write in writes:
            if (uncertain or progress>=len(LOCATION_EVENTS)
                    or write.event!=LOCATION_EVENTS[progress] or not write.complete
                    or (last_finished is not None and write.started_at<last_finished)):
                uncertain=True
            else:
                progress+=1
                last_finished=write.finished_at
        count=progress//4
        next_key=(LOCATION_KEYS[count] if not uncertain and progress%4==0
                  and count<len(LOCATION_KEYS) else None)
        return CommandSubmissionSnapshot(self.operation_id,self.revision,LOCATION_COMMAND,writes,
            tuple(write.event[1] for write in writes if write.event[0]==1 and write.event[2]==1),
            LOCATION_COMMAND[:min(count,len(LOCATION_COMMAND))],count,
            count==len(LOCATION_KEYS),uncertain,next_key)
