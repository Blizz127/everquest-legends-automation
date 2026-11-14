"""Expected crossing -> release -> fresh destination positions, on one lease.

The caller transfers its exclusive log lease before the final checked crossing
move. This class never creates a sender, steers, chooses a zone line, or reuses
the source route's heading/height/floor chain. Its only output operation is a
location request AFTER the expected entry and an explicit ready observation.
"""
from dataclasses import asdict
from datetime import datetime
import time

from .ground_binding import finite
from .motion_collection import CommandReceipt
from .owner_zone_tracker import ZoneReaderLease
from .stopped_location_pair import StoppedLocationPair


class ZoneArrivalHandoff:
    def __init__(self, lease, destination, *, release_controls, ready_for_location,
                 check_current, clock=time.monotonic, local_wall_clock=datetime.now,
                 maximum_seconds=90.):
        if (not isinstance(lease, ZoneReaderLease)
                or not all(callable(f) for f in (release_controls, ready_for_location,
                                                check_current, clock, local_wall_clock))
                or not finite(maximum_seconds) or not 0 < maximum_seconds <= 120):
            raise ValueError('Bounded arrival requires an exclusive lease and explicit callbacks')
        self.lease, self.reader = lease, lease.reader
        self.owner = lease.check()
        r = self.reader
        if (destination not in r.zone_ids or r.zone_id is None or r.tail.identity is None
                or r.zone_display_name == destination or r.tail.partial):
            raise ValueError('Distinct exact destination and complete current source zone required')
        self.destination, self.destination_id = destination, r.zone_ids[destination]
        self.source = (r.zone_id, r.zone_display_name)
        self.release_controls, self.ready_for_location = release_controls, ready_for_location
        self.check_current, self.clock, self.wall = check_current, clock, local_wall_clock
        self.started = self.last_at = clock()
        if not finite(self.started):
            raise ValueError('Finite arrival clock required')
        self.deadline = self.started+maximum_seconds
        self.log_binding = (r.tail.identity, r.tail.epoch)
        self.cursor = self._cursor()
        self.phase, self.reason = 'await_loading', ''
        self.loading = self.entry = self.release = self.collector = None
        self.events = []
        self._check()

    def _cursor(self):
        r = self.reader
        return (r.tail.position, r.zone_generation, r.log_line_seq, r.latest)

    def _check(self):
        if self.phase == 'stopped':
            raise ValueError(self.reason)
        self.check_current()
        owner = self.lease.check()
        now = self.clock()
        if (self.phase == 'stopped' or owner != self.owner or self.lease.reader is not self.reader
                or not finite(now) or not self.last_at <= now <= self.deadline
                or (self.reader.tail.identity, self.reader.tail.epoch) != self.log_binding):
            raise ValueError('Arrival cancelled, log/process binding changed or deadline expired')
        self.last_at = now
        return now

    def _release(self):
        began = self.clock()
        receipt = self.release_controls()
        now = self.clock()
        if (not isinstance(receipt, CommandReceipt)
                or not all(finite(v) for v in (began, receipt.started_at, receipt.completed_at, now))
                or not began <= receipt.started_at <= receipt.completed_at <= now):
            raise ValueError('Arrival release callback did not return its current completed receipt')
        self.release = receipt

    def cancel(self, reason):
        if self.phase == 'stopped':
            return
        self.phase, self.reason = 'stopped', str(reason)
        if self.collector is not None:
            self.collector.cancel(reason)
        self.reader.latest = None
        try:
            self._release()
        except Exception as error:
            self.reason += '; release failed: '+str(error)
            raise

    def _destination_current(self):
        self._check()
        if ((self.reader.zone_id, self.reader.zone_display_name, self.reader.zone_generation)
                != (self.destination_id, self.destination, self.entry.zone_generation)):
            raise ValueError('Destination zone changed during arrival positions')

    def tick(self):
        try:
            now = self._check()
            if self.phase == 'complete':
                self._destination_current()
                return None
            if self.collector is not None:
                action = self.collector.tick()
                self._destination_current()
                if self.collector.phase == 'complete':
                    self.phase = 'complete'
                return action
            if self._cursor() != self.cursor:
                raise ValueError('Arrival lease was consumed by another operation')
            fixes = self.reader.poll(now=now)
            boundaries, cursor = self.reader.boundaries, self._cursor()
            now = self._check()
            if self._cursor() != cursor:
                raise ValueError('Arrival lease changed during current-context callbacks')
            self.cursor = cursor
            # A reentrant empty poll can reset reader.boundaries without moving
            # its cursor. Keep our owned result so LOADING always releases.
            for event in boundaries:
                row = asdict(event)
                if event.log_local_time is not None:
                    row['log_local_time'] = event.log_local_time.isoformat()
                self.events.append(row)
                wall = self.wall()
                if (not isinstance(wall, datetime) or wall.tzinfo is not None
                        or event.log_local_time is None
                        or abs((wall-event.log_local_time).total_seconds()) > 2):
                    raise ValueError('Arrival event timestamp is missing or stale')
                if event.kind == 'loading' and self.phase == 'await_loading':
                    self.loading, self.phase = event, 'loading'
                    self._release()
                    self._check()  # Release callbacks may cancel reentrantly.
                elif (event.kind == 'entered' and self.phase == 'loading'
                      and (event.zone_id, event.zone_name) == (self.destination_id, self.destination)
                      and self.loading.log_local_time <= event.log_local_time):
                    self.entry, self.phase = event, 'await_ready'
                    self.reader.latest = None
                else:
                    raise ValueError('Unexpected zone, position or logging boundary during crossing')
            if fixes or self.reader.tail.partial:
                raise ValueError('Unsolicited position or incomplete log during crossing')
            self.cursor = self._cursor()
            if self.phase == 'await_ready':
                self._destination_current()
                ready = self.ready_for_location()
                now = self._check()
                if ready is True and now >= self.release.completed_at+.12:
                    self._destination_current()
                    self.collector = StoppedLocationPair(self.lease,
                        released_at=max(self.release.completed_at,self.entry.received_monotonic),
                        check_current=self._destination_current, clock=self.clock,
                        local_wall_clock=self.wall)
                    self.phase = 'locating'
                    return self.collector.tick()
            return None
        except BaseException as error:
            self.cancel(str(error))
            raise

    def command_sent(self, request, receipt):
        try:
            self._destination_current()
            if self.phase != 'locating' or self.collector is None:
                raise ValueError('No destination location request is pending')
            self.collector.command_sent(request, receipt)
            self._destination_current()
        except BaseException as error:
            self.cancel(str(error))
            raise

    def snapshot(self):
        return dict(outcome=self.phase, reason=self.reason, source_zone=self.source,
            destination=(self.destination_id,self.destination), log_binding=self.log_binding,
            events=list(self.events), release=None if self.release is None else asdict(self.release),
            positions=None if self.collector is None else self.collector.snapshot(),
            source_navigation_state_reused=False, spawn_coordinate_verified=False,
            crossing_movement_authorized=False, real_client_accepted=False)
