"""Finite two-reply startup collection on an exclusively leased live reader.

The caller sends its already-tested location hotbutton and supplies the real
release receipt. This class never creates input or infers request IDs from
the client log. Reentrant input pumps must call check(), not consume the tail.
"""
from dataclasses import asdict
from datetime import datetime
import math
import time

from .ground_binding import finite, point
from .motion_collection import CommandReceipt, LocationRequest
from .owner_zone_tracker import ZoneReaderLease


class StoppedLocationPair:
    def __init__(self, lease, *, released_at, check_current, clock=time.monotonic,
                 local_wall_clock=datetime.now, poll_reader=None):
        if (not isinstance(lease, ZoneReaderLease) or not finite(released_at)
                or released_at < 0 or not all(callable(f) for f in
                    (check_current, clock, local_wall_clock))
                or (poll_reader is not None and not callable(poll_reader))):
            raise ValueError('Exclusive zone lease and current release required')
        self.lease, self.reader = lease, lease.reader
        self.check_current, self.clock, self.wall = check_current, clock, local_wall_clock
        # An enclosing arrival controller may own this same reader's poll,
        # handling loading boundaries before our source-zone postcheck. It
        # must return only that poll's actual fixes, or abort this collection.
        self.poll_reader = self.reader.poll if poll_reader is None else poll_reader
        self.owner = lease.check()
        self.started = self.last_at = clock()
        if not finite(self.started) or released_at > self.started:
            raise ValueError('Invalid startup release time')
        self.released_at = released_at
        self.zone = (self.reader.zone_id, self.reader.zone_display_name,
                     self.reader.tail.identity, self.reader.tail.epoch, self.reader.zone_generation)
        self.seq, self.latest = self.reader.log_line_seq, self.reader.latest
        self.first = self.second = self.pending = None
        self.phase, self.reason = 'need_location', ''
        self.due = max(self.started, released_at+.12)
        self.deadline = self.due+2.5
        self.requests, self.raw_fixes = [], []
        self.check()

    def cancel(self, reason):
        self.phase, self.reason, self.pending = 'stopped', str(reason), None

    def check(self):
        if self.phase == 'stopped':
            raise ValueError(self.reason)
        self.check_current()
        owner = self.lease.check()
        now = self.clock()
        r = self.reader
        if (self.phase == 'stopped' or owner != self.owner or not finite(now)
                or not self.last_at <= now <= self.started+8
                or self.lease.reader is not r
                or (r.zone_id, r.zone_display_name, r.tail.identity, r.tail.epoch,
                    r.zone_generation) != self.zone):
            self.cancel('Stopped-pair context changed or expired')
            raise ValueError(self.reason)
        self.last_at = now
        return now

    def tick(self):
        try:
            now = self.check()
            if self.phase == 'complete':
                return None
            if self.reader.latest is not self.latest or self.reader.log_line_seq != self.seq:
                raise ValueError('Startup reader was consumed elsewhere')
            fixes = self.poll_reader(now=now)
            now = self.check()
            if (self.reader.tail.partial or len(fixes)>1
                    or self.reader.log_line_seq != self.seq+len(fixes)
                    or (fixes and self.phase != 'await_location')
                    or (fixes and self.reader.latest is not fixes[-1])
                    or (not fixes and self.reader.latest is not self.latest)):
                raise ValueError('Startup received partial, invalid or unsolicited positions')
            if fixes:
                raw = fixes[0]
                request, receipt = self.pending
                wall = self.wall()
                if (not point(raw.raw_coordinates) or not isinstance(wall,datetime)
                        or wall.tzinfo is not None or raw.log_local_time.tzinfo is not None
                        or abs((wall-raw.log_local_time).total_seconds())>2
                        or not receipt.completed_at <= raw.received_monotonic <= now <= request.expires_at
                        or raw.received_monotonic < self.released_at+.12):
                    raise ValueError('Startup reply is stale or not after the bound release')
                self.seq, self.latest, self.pending = raw.log_line_seq, raw, None
                record=asdict(raw);record['log_local_time']=raw.log_local_time.isoformat()
                self.raw_fixes.append(record)
                if self.first is None:
                    self.first = raw
                    self.due, self.deadline = raw.received_monotonic+.4, raw.received_monotonic+2.5
                    self.phase = 'need_location'
                else:
                    if (not .4 <= raw.received_monotonic-self.first.received_monotonic <= 2.5
                            or raw.log_line_seq != self.first.log_line_seq+1
                            or math.dist(raw.raw_coordinates[:2],self.first.raw_coordinates[:2])>.25
                            or abs(raw.raw_coordinates[2]-self.first.raw_coordinates[2])>.25):
                        raise ValueError('Startup positions did not remain stopped')
                    self.second, self.phase = raw, 'complete'
            if self.phase != 'complete' and now > self.deadline:
                raise ValueError('Startup position reply timed out')
            if self.phase == 'need_location' and now >= self.due:
                self.pending = LocationRequest(len(self.requests),0,now,self.deadline)
                self.phase = 'requesting'
                return self.pending
            return None
        except BaseException as error:
            self.cancel(str(error))
            raise

    def command_sent(self, request, receipt):
        now = self.check()
        if (self.phase != 'requesting' or self.pending is not request
                or not isinstance(receipt, CommandReceipt)
                or not all(finite(v) for v in (receipt.started_at,receipt.completed_at))
                or not request.issued_at <= receipt.started_at <= receipt.completed_at <= now <= request.expires_at):
            self.cancel('Startup hotbutton receipt does not match its request')
            raise ValueError(self.reason)
        self.requests.append(dict(request=asdict(request),receipt=asdict(receipt)))
        self.pending, self.phase = (request,receipt), 'await_location'

    def snapshot(self):
        return dict(outcome=self.phase,reason=self.reason,zone_binding=self.zone,
            started=self.started,released_at=self.released_at,requests=list(self.requests),
            raw_fixes=list(self.raw_fixes),request_correlation_verified=False,
            input_authorized=False,real_client_accepted=False)
