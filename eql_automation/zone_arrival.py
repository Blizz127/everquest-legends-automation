"""Expected crossing -> release -> fresh destination positions, on one lease.

The caller transfers its exclusive log lease before the final checked crossing
move. This class never creates a sender, steers, chooses a zone line, or reuses
the source route's heading/height/floor chain. Its only output operation is a
location request after expected entry/readiness, or an explicitly started
stopped source pair while the caller retains a provisional movement receipt.
"""
from dataclasses import asdict,dataclass
from datetime import datetime
import time

from .ground_binding import finite
from .motion_collection import CommandReceipt
from .owner_zone_tracker import ZoneReaderLease
from .scene_log_veto import ExpectedArrivalLogVeto
from .stopped_location_pair import StoppedLocationPair


class _SourceTransition(Exception):
    """Owned boundary processing retired a source collector before its check."""


@dataclass(frozen=True)
class SourcePairResult:
    first: object
    second: object
    observations: tuple
    record: dict
    input_authorized: bool = False
    real_client_accepted: bool = False


class ZoneArrivalHandoff:
    def __init__(self, lease, destination, *, release_controls, ready_for_location,
                 check_current, clock=time.monotonic, local_wall_clock=datetime.now,
                 maximum_seconds=90.,cancel_generation=0,maximum_source_seconds=None):
        if (not isinstance(lease, ZoneReaderLease)
                or not all(callable(f) for f in (release_controls, ready_for_location,
                                                check_current, clock, local_wall_clock))
                or not finite(maximum_seconds) or not 0 < maximum_seconds <= 120
                or (maximum_source_seconds is not None and
                    (not finite(maximum_source_seconds) or not 0<maximum_source_seconds<=1500))):
            raise ValueError('Bounded arrival requires an exclusive lease and explicit callbacks')
        self.lease, self.reader = lease, lease.reader
        self.owner = lease.check()
        r = self.reader
        if (destination not in r.zone_ids or r.zone_id is None or r.tail.identity is None
                or r.zone_display_name == destination or r.tail.partial):
            raise ValueError('Distinct exact destination and complete current source zone required')
        self.destination, self.destination_id = destination, r.zone_ids[destination]
        self.source = (r.zone_id, r.zone_display_name)
        self.source_generation = r.zone_generation
        self.release_controls, self.ready_for_location = release_controls, ready_for_location
        self.check_current, self.clock, self.wall = check_current, clock, local_wall_clock
        self.started = self.last_at = clock()
        if not finite(self.started):
            raise ValueError('Finite arrival clock required')
        self.deadline = self.started+maximum_seconds
        self.maximum_source_seconds=maximum_source_seconds
        self.maximum_arrival_seconds=maximum_seconds
        self.outer_deadline=self.deadline
        if maximum_source_seconds is not None:
            self.deadline=self.started+maximum_source_seconds
            self.outer_deadline=self.deadline+maximum_seconds
        self.log_binding = (r.tail.identity, r.tail.epoch)
        self.cursor = self._cursor()
        self.phase, self.reason = 'await_loading', ''
        self.loading = self.entry = self.release = self.collector = None
        self.source_collector = self.source_result = self.observe_source_fix = None
        self.source_observations = []
        self.source_collections = []
        self._source_working = False
        self.events = []
        self.veto=ExpectedArrivalLogVeto(r.tail.path,
            expected_character=r.expected_character,expected_server=r.expected_server,
            cancel_generation=cancel_generation,clock=clock,destination=destination)
        self.veto_binding=(self.veto.tail.identity,self.veto.tail.epoch)
        if (self.veto.tail.identity,self.veto.tail.position)!=(r.tail.identity,r.tail.position):
            raise ValueError('Arrival hazard observer must start at the same exact source cursor')
        self._check()

    def _cursor(self):
        r = self.reader
        return (r.tail.position, r.zone_generation, r.log_line_seq, r.latest)

    def _check(self):
        if self.phase == 'stopped':
            raise ValueError(self.reason)
        self.check_current()
        owner = self.lease.check()
        hazard=self.veto.poll()
        now = self.clock()
        if (self.phase == 'stopped' or owner != self.owner or self.lease.reader is not self.reader
                or not finite(now) or not self.last_at <= now <= self.deadline
                or (self.reader.tail.identity, self.reader.tail.epoch) != self.log_binding
                or (self.veto.tail.identity,self.veto.tail.epoch)!=self.veto_binding
                or not hazard.continuity_available or hazard.reason is not None):
            raise ValueError('Arrival cancelled, log/process binding changed, hazard or deadline expired'
                             +(':'+hazard.reason if hazard.reason else ''))
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
        self._retire_source(reason)
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

    def _source_current(self):
        self._check()
        r=self.reader
        if (self.phase!='await_loading' or self.loading is not None
                or (r.zone_id,r.zone_display_name,r.zone_generation)!=(*self.source,self.source_generation)):
            raise ValueError('Source zone changed during stopped positions')

    def _retire_source(self,reason):
        collector=self.source_collector
        self.source_collector=self.source_result=self.observe_source_fix=None
        self.source_observations=[]
        if collector is not None:
            collector.cancel(reason)
            self.source_collections.append(collector.snapshot())

    def start_source_pair(self,*,released_at,observe_fix):
        """Collect source replies after a sealed release; no movement is issued.

        The crossing controller must wait for its loading window, hold all
        controls released, and bind each reply to the exact provisional fork.
        ``observe_fix`` runs immediately after request/freshness validation.
        It must not consume the reader; it supplies no destination evidence.
        """
        token=object()
        try:
            if self._source_working:raise ValueError('Source collection setup reentered')
            self._source_working=token
            self._source_current()
            if (self.source_collector is not None or self.source_result is not None
                    or not callable(observe_fix) or self._cursor()!=self.cursor):
                raise ValueError('Exclusive source pair and current arrival cursor required')
            collector=StoppedLocationPair(self.lease,released_at=released_at,
                check_current=self._source_current,clock=self.clock,local_wall_clock=self.wall,
                poll_reader=self._poll_source)
            self._source_current()
            if (self._cursor()!=self.cursor or self._source_working is not token
                    or self.source_collector is not None or self.source_result is not None):
                raise ValueError('Source reader changed while starting positions')
            self.source_collector=collector;self.observe_source_fix=observe_fix
            self.source_observations=[]
        except BaseException as error:
            self.cancel(str(error));raise
        finally:
            if self._source_working is token:self._source_working=False

    def _poll_owned(self,now,*,allow_source=False):
        if self._cursor()!=self.cursor:
            raise ValueError('Arrival lease was consumed by another operation')
        fixes=self.reader.poll(now=now)
        boundaries,cursor=self.reader.boundaries,self._cursor()
        now=self._check()
        if self._cursor()!=cursor:
            raise ValueError('Arrival lease changed during current-context callbacks')
        self.cursor=cursor
        # Keep the complete owned batch even if a callback makes an empty poll.
        # LOADING and entry may share a batch; later invalid events still refuse.
        for event in boundaries:
            row=asdict(event)
            if event.log_local_time is not None:row['log_local_time']=event.log_local_time.isoformat()
            self.events.append(row);wall=self.wall()
            self._check()
            if self._cursor()!=cursor:
                raise ValueError('Arrival lease changed during boundary callbacks')
            if (not isinstance(wall,datetime) or wall.tzinfo is not None
                    or event.log_local_time is None
                    or abs((wall-event.log_local_time).total_seconds())>2):
                raise ValueError('Arrival event timestamp is missing or stale')
            if event.kind=='loading' and self.phase=='await_loading':
                self.loading,self.phase=event,'loading'
                if self.maximum_source_seconds is not None:
                    self.deadline=min(self.outer_deadline,
                        event.received_monotonic+self.maximum_arrival_seconds)
                self._retire_source('loading observed; source positions discarded')
                self._release();self._check()
                if self._cursor()!=cursor:
                    raise ValueError('Arrival lease changed during loading release')
            elif (event.kind=='entered' and self.phase=='loading'
                    and (event.zone_id,event.zone_name)==(self.destination_id,self.destination)
                    and self.loading.log_local_time<=event.log_local_time):
                self.entry,self.phase=event,'await_ready';self.reader.latest=None
                cursor=self._cursor()
            else:
                raise ValueError('Unexpected zone, position or logging boundary during crossing')
        if self.reader.tail.partial or (fixes and (not allow_source or self.phase!='await_loading')):
            raise ValueError('Unsolicited position or incomplete log during crossing')
        self.cursor=self._cursor()
        return fixes

    def _poll_source(self,*,now):
        fixes=self._poll_owned(now,allow_source=True)
        if self.loading is not None:
            raise _SourceTransition()
        self._source_current()
        return fixes

    def _tick_source(self):
        if self._source_working:raise ValueError('Source position collection reentered')
        self._source_working=True
        try:
            collector=self.source_collector
            try:action=collector.tick()
            except _SourceTransition:
                self._check()
                if self.loading is None or self.source_collector is not None:
                    raise ValueError('Source collection retired without an owned loading event')
                return None
            self._source_current()
            if self.source_collector is not collector:
                raise ValueError('Source collector changed during its tick')
            fixes=tuple(v for v in (collector.first,collector.second) if v is not None)
            if len(fixes)>len(self.source_observations):
                if len(fixes)!=len(self.source_observations)+1:
                    raise ValueError('Source observations skipped a validated reply')
                cursor=self._cursor()
                value=self.observe_source_fix(fixes[-1])
                self._source_current()
                if self._cursor()!=cursor or self.source_collector is not collector:
                    raise ValueError('Source observer consumed the reader or cancelled collection')
                self.source_observations.append(value)
            if collector.phase=='complete':
                record=collector.snapshot()
                self.source_result=SourcePairResult(collector.first,collector.second,
                    tuple(self.source_observations),record)
                self.source_collections.append(record)
                self.source_collector=self.observe_source_fix=None
                self.source_observations=[]
            return action
        finally:self._source_working=False

    def take_source_pair(self):
        """Recheck queued boundaries before handing out one completed pair.

        A loading event revokes the pair and returns None. The caller still
        resolves its sealed ledger under its stop lock and current owner scope.
        """
        try:
            if self.source_result is None:raise ValueError('No complete source pair available')
            if self._source_working:raise ValueError('Source result requested during collection')
            self._poll_owned(self._check())
            if self.loading is not None:return None
            self._source_current()
            result=self.source_result
            if result is None:raise ValueError('Source result invalidated during handoff')
            self.source_result=None
            return result
        except BaseException as error:
            self.cancel(str(error));raise

    def tick(self):
        try:
            if self._source_working:raise ValueError('Source collection callback reentered')
            now = self._check()
            if self.phase == 'complete':
                self._destination_current()
                return None
            if self.source_collector is not None:
                return self._tick_source()
            if self.collector is not None:
                action = self.collector.tick()
                self._destination_current()
                if self.collector.phase == 'complete':
                    self.phase = 'complete'
                return action
            self._poll_owned(now)
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
            if self.source_collector is not None:
                self._source_current()
                self.source_collector.command_sent(request,receipt)
                self._source_current()
                return
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
            deadline=self.deadline,outer_deadline=self.outer_deadline,
            destination=(self.destination_id,self.destination), log_binding=self.log_binding,
            events=list(self.events), release=None if self.release is None else asdict(self.release),
            positions=None if self.collector is None else self.collector.snapshot(),
            source_collections=list(self.source_collections),
            source_navigation_state_reused=False, spawn_coordinate_verified=False,
            crossing_movement_authorized=False, real_client_accepted=False)
