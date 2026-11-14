"""Receipt-driven thin-sheet traversal; ordinary terrain remains frozen.

Actual log replies retain the original height calibration and every compatible
local contact state. Final contact arrival is a distinct receipt, never an
ordinary floor or an authorization to start a camp.
"""
from collections import deque
from copy import deepcopy
from dataclasses import asdict,dataclass,field
from fractions import Fraction as F
from hashlib import sha256
import json
import math

from .fixed_route_follower import RouteHalt
from .ground_binding import finite
from .native_region_policy import encoded
from .observed_height import height_snapshot,height_record
from .source_contact_preflight import SourceContactPreflight
from .source_motion import SourceMotionGeometry
from .source_stair_controller import SourceStairController
from .source_stair_coverage import covers_closed
from .source_step import digest


@dataclass(frozen=True)
class SourceContactFix:
    raw_fix: object
    package_xyz: tuple
    height_interval: tuple
    compatible_states: tuple
    window_sha256: str
    observed_at: float
    observed_grounded: bool = field(default=False,init=False)
    input_authorized: bool = field(default=False,init=False)
    real_client_accepted: bool = field(default=False,init=False)


@dataclass(frozen=True)
class SourceContactWindow:
    geometry: SourceMotionGeometry
    coverage: object
    center_footprint: tuple
    state: tuple
    coverage_state: tuple
    geometry_state: tuple


@dataclass(frozen=True)
class SourceContactArrival:
    first: SourceContactFix
    second: SourceContactFix
    payload: bytes
    sha256: str
    issued_at: float
    expires_at: float
    input_authorized: bool = field(default=False,init=False)
    real_client_accepted: bool = field(default=False,init=False)

    def record(self):
        if type(self.payload) is not bytes or sha256(self.payload).hexdigest()!=self.sha256:
            raise ValueError('Contact arrival seal changed')
        record=json.loads(self.payload)
        if encoded(record)!=self.payload:raise ValueError('Contact arrival encoding changed')
        return record


@dataclass(frozen=True)
class SourceContactOutcome:
    kind: str
    reference: SourceContactFix
    window_sha256: str
    arrival: SourceContactArrival | None = None
    real_client_accepted: bool = field(default=False,init=False)


def common_contact_heights(first,second):
    # Intersect the unions, never their convex hull: space between an exact
    # terrain and sheet top is not a possible support away from sheet edges.
    return tuple(sorted({(max(a[2][0],b[2][0]),min(a[2][1],b[2][1]))
        for a in first.compatible_states for b in second.compatible_states
        if max(a[2][0],b[2][0])<=min(a[2][1],b[2][1])}))


def contact_fix_record(fix):
    return dict(xyz=fix.package_xyz,seq=fix.raw_fix.log_line_seq,observed_at=fix.observed_at,
        received_at=fix.raw_fix.received_monotonic,raw_coordinates=fix.raw_fix.raw_coordinates,
        observed_height_interval_exact=[str(v) for v in fix.height_interval],
        compatible=[dict(kind=kind,source_ids=ids,height_interval_exact=[str(v) for v in heights])
                    for kind,ids,heights in fix.compatible_states])


class SourceContactController(SourceStairController):
    """Reuse the retained ticket/UP transport with distinct contact feedback."""
    def __init__(self,preflight,start):
        if type(preflight) is not SourceContactPreflight:
            raise ValueError('Exact completed contact preflight required')
        l=preflight.ledger
        self.ordinary,self.policy=l,preflight.policy
        self.lock,self.clock=l.lock,l.clock
        self.phase,self.reason='ready',''
        self._prepared=self._pending=self._sealed=self._busy=None
        self._ticket_state=self._seal_state=None;self._staging=False
        self._issued=deque(maxlen=2);self.local_steps=0;self._no_progress=0
        self._lease=object();self._bound=False
        self.arrival=self._arrival_state=None;self.cursor=self._cursor=0
        consumed=False
        with self.lock:
            try:
                preflight.check()
                if preflight.contact_index is None:
                    raise RouteHalt('Grounded contact cache required for contact movement')
                self.cache,self.index,self.hint=preflight.cache,preflight.contact_index,preflight.hint
                self._cache_state=(id(self.cache),self.cache.payload,self.cache.sha256)
                self.targets=tuple(tuple(row['end']) for row in self.index.plan.record()['contact_walks']['accepted_envelopes'])
                self._targets=self.targets
                self._hint_state=encoded(asdict(self.hint))
                self._index=self.index
                self._height=height_snapshot(l.observer.calibration)
                self._distance_origin=self.policy.origin if self.policy.origin is not None else l.reference.package_xyz
                self._scope=(id(self.policy.declaration),asdict(self.policy.declaration),self.policy.started,
                    tuple(id(v) for v in self.policy._context[1:]),self.policy.window,self.policy.topology,self._distance_origin)
                preflight.consume_start(start);consumed=True
                self.observer,self.bounds,self.model,self.motion,self.legacy=l.observer,l.bounds,l.model,l.motion,l.legacy
                self.chain,self.reference=l.chain,l.reference
                self._reference_state=self._fix_state(self.reference)
                self.pose=deepcopy(l.pose);self.pose.motion=self.motion;self.serial=l.serial
                self._ordinary_state=l._state()
                self._original_fix=l.observer._observation_snapshot(l.reference)
                self.history_sha256=digest(dict(cache=self.cache.sha256,start_seq=start.second.raw_fix.log_line_seq))
                l.phase,l._busy='contact_transfer',self._lease
                self._check()
                self.policy.bind_transfer(self)
                self._bound=True
                self._check()
            except BaseException as error:
                self.cancel(str(error))
                if not consumed:preflight.cancel(str(error))
                elif l.phase=='ready':l.cancel(str(error))
                raise

    @classmethod
    def from_preflight(cls,preflight,start):return cls(preflight,start)

    def cancel(self,reason='Contact movement cancelled'):
        with self.lock:
            if self.phase=='stopped':return
            self.phase,self.reason='stopped',str(reason)
            self._prepared=self._pending=self._sealed=self._busy=None
            self.arrival=self._arrival_state=None
            if self.ordinary.phase=='contact_transfer' and self.ordinary._busy is self._lease:
                self.ordinary.cancel(reason)

    def _check(self):
        now=self.ordinary._check()
        self._assert_context(now)
        return now

    def _assert_context(self,now):
        """Pure binding check usable after the last physical/provider call."""
        if self.phase=='stopped':raise RouteHalt(self.reason)
        l,p=self.ordinary,self.policy
        scope=(id(p.declaration),asdict(p.declaration),p.started,
            tuple(id(v) for v in p._context[1:]),p.window,p.topology,self._distance_origin)
        if (l.phase!='contact_transfer' or l._busy is not self._lease or l._state()!=self._ordinary_state
                or l.observer._observation_snapshot(l.reference)!=self._original_fix
                or self.chain is not l.chain or self.observer is not l.observer or self.bounds is not l.bounds
                or self.model is not l.model or self.motion is not l.motion or self.legacy is not l.legacy
                or self.clock is not l.clock or self.lock is not l.lock
                or self.index is not self._index
                or (id(self.cache),self.cache.payload,self.cache.sha256)!=self._cache_state
                or self.targets is not self._targets or self.cursor!=self._cursor
                or self._fix_state(self.reference)!=self._reference_state
                or encoded(asdict(self.hint))!=self._hint_state
                or height_snapshot(self.observer.calibration)!=self._height or scope!=self._scope
                or p.ledger not in ((self,) if self._bound else (l,self))
                or p.origin is not None and p.origin!=self._distance_origin
                or not p.started<=now<=p.started+p.declaration.maximum_seconds
                or self.pose.motion is not self.motion or not finite(self.pose.heading)
                or not 0<=self.pose.heading<360 or self.pose._sign_votes
                or self.pose.sign_conflict or self.pose.turn_dead):
            raise RouteHalt('Contact lease, cache, original floor or scope changed')
        self.index.check()

    def _state(self):
        return (*super()._state(),self.cursor,id(self.targets),id(self.arrival))

    def _window_check(self,window):
        self.index.check()
        if (type(window) is not SourceContactWindow
                or (id(window.coverage),window.coverage.payload,window.coverage.sha256,
                    window.center_footprint)!=window.coverage_state
                or (id(window.geometry),tuple(vars(window.geometry).items()))!=window.geometry_state):
            raise RouteHalt('Contact pulse coverage changed')

    def _validate_fix(self,fix,*,maximum_age=2.5):
        now=self._check();entry=next((v for v in self._issued if v[0] is fix),None)
        if (type(fix) is not SourceContactFix or entry is None or entry[2]!=self._fix_state(fix)
                or not 0<=now-fix.raw_fix.received_monotonic<=maximum_age):
            raise RouteHalt('Need an unchanged fresh issued contact observation')
        self._window_check(entry[1]);return now

    def prepare(self,kind):
        try:
            with self.lock:
                self._check();self.validate_reference()
                if self.phase!='ready' or self._busy is not None:
                    raise RouteHalt('Contact movement must await stopped acknowledgment')
                state=self._state();reference=self.reference;self.phase='preparing'
            coverage=self.index.cover_pulse(reference.package_xyz[:2],self.pose.heading,kind,self.bounds,
                height_interval=self._height_interval(reference.raw_fix))
            record=coverage.record()
            footprint=tuple(tuple(p) for p in record['body_footprint'])
            centers=tuple(tuple(F(v) for v in p) for p in record['center_footprint_exact'])
            payload=encoded(dict(kind=kind,cache_sha256=self.cache.sha256,coverage_sha256=coverage.sha256,
                parent_proof_sha256=self.chain.previous.proof_sha256,footprint=footprint,
                receipt_history_sha256=self.history_sha256,input_authorized=False))
            geometry=SourceMotionGeometry(kind,footprint,payload,sha256(payload).hexdigest())
            with self.lock:
                self._check();self.validate_reference()
                if self.phase!='preparing' or self._state()!=state:
                    raise RouteHalt('Contact preparation cancelled or changed')
                self._prepared=SourceContactWindow(geometry,coverage,centers,state,
                    (id(coverage),coverage.payload,coverage.sha256,centers),
                    (id(geometry),tuple(vars(geometry).items())))
                self.phase='prepared';return geometry
        except BaseException as error:self.cancel(str(error));raise

    def observe_reply(self,seal,raw):
        try:
            with self.lock:
                window=self._check_seal(seal);o=self.observer;now=o.check();o.validate_raw(raw,now)
                if (o.reader.latest is not raw or o.reader.log_line_seq!=raw.log_line_seq
                        or raw.log_line_seq<=o.last_seq or not 0<=now-raw.received_monotonic<=.5):
                    raise RouteHalt('Need one fresh unreplayed contact reply')
                raw_state=(id(raw),tuple(vars(raw).items()))
                point=(raw.raw_coordinates[1],raw.raw_coordinates[0])
                self._within_scope(point)
                if not covers_closed((tuple(map(F,point)),),(window.center_footprint,)):
                    raise RouteHalt('Observed center left the full contact motion bounds')
                interval=self._height_interval(raw)
                compatible=tuple((v.kind,v.source_ids,v.height_interval)
                    for v in self.index.compatible(point,self.bounds,height_interval=interval))
                # Arrival may introduce a rug state absent at departure. All
                # local states fit the prechecked whole-motion vertical band;
                # the departure candidate list is not an arrival allowlist.
                if not compatible:raise RouteHalt('Observed contact height has no local support state')
                height=raw.raw_coordinates[2]-o.calibration.raw_z_minus_source_z
                fix=SourceContactFix(raw,(*point,height),interval,compatible,window.coverage.sha256,now)
                self._check_seal(seal);finished=o.check()
                self._assert_context(finished);self._window_check(window)
                if (self.phase not in ('await_stopped','settling') or self._sealed is not seal
                        or self._pending is None or self._pending[1] is not window or self._busy is not None
                        or self._pending[2]!=self._state() or o.reader.latest is not raw
                        or o.reader.log_line_seq!=raw.log_line_seq
                        or self.ordinary.phase!='contact_transfer' or self.ordinary._busy is not self._lease
                        or (id(raw),tuple(vars(raw).items()))!=raw_state
                        or self._ticket_snapshot(seal.ticket)!=self._ticket_state
                        or (id(seal),tuple(vars(seal).items()),tuple(vars(seal.receipt).items()))!=self._seal_state
                        or not 0<=finished-raw.received_monotonic<=.5):
                    raise RouteHalt('Contact reply changed or expired during observation')
                o.last_seq=raw.log_line_seq
                self._issued.append((fix,window,self._fix_state(fix)));return fix
        except BaseException as error:self.cancel(str(error));raise

    def _within_scope(self,point):
        if math.dist(self._distance_origin[:2],point)>self.policy.declaration.maximum_distance:
            raise RouteHalt('Contact position exceeds original displacement budget')

    def _pair_at(self,first,second,now):
        if (not 0<=now-first.raw_fix.received_monotonic<=2.5
                or not 0<=now-second.raw_fix.received_monotonic<=.5
                or self.observer.reader.latest is not second.raw_fix
                or self.observer.reader.log_line_seq!=second.raw_fix.log_line_seq
                or any(not any(e[0] is fix and e[2]==self._fix_state(fix) for e in self._issued)
                       for fix in (first,second))):
            raise RouteHalt('Contact pair changed or expired during final physical observation')
        for fix in (first,second):self._within_scope(fix.package_xyz[:2])

    @staticmethod
    def _arrival_snapshot(arrival):
        return (id(arrival),id(arrival.first),id(arrival.second),arrival.payload,arrival.sha256,
                arrival.issued_at,arrival.expires_at,arrival.input_authorized,arrival.real_client_accepted)

    def _check_arrival(self,arrival,now):
        self._assert_context(now)
        if (self.phase!='arrived' or type(arrival) is not SourceContactArrival or arrival is not self.arrival
                or self._arrival_snapshot(arrival)!=self._arrival_state
                or self.reference is not arrival.second or self._busy is not None
                or self._pending is not None or self._sealed is not None
                or not arrival.issued_at<=now<=arrival.expires_at):
            raise RouteHalt('Exact current contact arrival required')
        self._pair_at(arrival.first,arrival.second,now)

    def validate_arrival(self,arrival):
        try:
            with self.lock:
                now=self._check();self._check_arrival(arrival,now);state=self._state()
                self._validate_fix(arrival.first);self._validate_fix(arrival.second,maximum_age=.5)
                idle=self.policy.observe_contact_arrival(self,arrival)
                self._check_arrival(arrival,idle.finished_at)
                if self._state()!=state:raise RouteHalt('Contact arrival changed during final observation')
                return arrival
        except BaseException as error:self.cancel(str(error));raise

    def acknowledge_stopped(self,seal,first,second):
        try:
            with self.lock:
                window=self._check_seal(seal);self._pair(seal,first,second)
                if self._busy is not None:raise RouteHalt('Contact acknowledgment already active')
                state=self._state();busy=object();self._busy=busy
                common=common_contact_heights(first,second)
                pose=deepcopy(self.pose);pose.motion=self.motion
                history=digest(dict(previous=self.history_sha256,coverage=window.coverage.sha256,
                    receipt=asdict(seal.receipt),pair=[contact_fix_record(f) for f in (first,second)]))
                r=seal.receipt;kind=seal.ticket.geometry.kind
                pose.predict(r.maximum_held_seconds,self.legacy.Controls(forward=kind=='forward',
                    turn=None if kind=='forward' else kind))
                pose.predict(second.raw_fix.received_monotonic-r.up_completed_at,self.legacy.STOP)
                correction=pose.correct(*second.package_xyz,age=0.)
                stalled=(self._no_progress+1 if kind=='forward' and
                    math.dist(self.reference.package_xyz[:2],second.package_xyz[:2])<.01 else 0)
                if (correction.get('jumped') or pose._sign_votes or pose.sign_conflict or pose.turn_dead
                        or pose.blocked_fixes>=2 or stalled>=3):
                    raise RouteHalt('Observed contact movement contradicts measured controls')
                self._check_seal(seal);self._pair(seal,first,second)
                idle=self.policy.observe_transfer(self,seal);now=idle.finished_at
                self._assert_context(now)
                if (self._busy is not busy or self._state()!=state or self._sealed is not seal
                        or self.phase not in ('await_stopped','settling')
                        or self._ticket_snapshot(seal.ticket)!=self._ticket_state
                        or (id(seal),tuple(vars(seal).items()),tuple(vars(seal.receipt).items()))!=self._seal_state):
                    raise RouteHalt('Contact movement changed before publication')
                self._window_check(window)
                self._pair_at(first,second,now)
                if not common:
                    self._busy=None;self.phase='settling'
                    return SourceContactOutcome('settling',second,window.coverage.sha256)
                cursor=self.cursor
                # Consume only nominal waypoints actually reached by both
                # replies. A shortcut's removed input vertices are not targets.
                while cursor<len(self.targets) and all(math.dist(f.package_xyz[:2],self.targets[cursor])<=.25
                                                       for f in (first,second)):
                    cursor+=1
                if cursor<len(self.targets) and math.dist(second.package_xyz[:2],self.targets[cursor])<=.01:
                    # No further pulse can usefully approach this target yet.
                    # Keep the same UP/deadline for another actual stopped pair.
                    # If this pair already reached earlier close waypoints,
                    # retain that proven progress without counting the pulse twice.
                    if cursor!=self.cursor:
                        self.cursor=self._cursor=cursor;self.history_sha256=history
                        self._pending=(seal.ticket,window,self._state())
                    self._busy=None;self.phase='settling'
                    return SourceContactOutcome('settling',second,window.coverage.sha256)
                arrival=None
                if cursor==len(self.targets):
                    payload=encoded(dict(format='eql-source-contact-arrival-v1',cache_sha256=self.cache.sha256,
                        contact_plan_sha256=self.index.plan.sha256,receipt_history_sha256=history,
                        itinerary_sha256=self.observer.itinerary.sha256,
                        original_scope=asdict(self.policy.declaration),scope_started=self.policy.started,
                        original_distance_origin=self._distance_origin,completed_waypoints=cursor,
                        final_coverage_sha256=window.coverage.sha256,final_receipt=asdict(seal.receipt),
                        original_floor_proof_sha256=self.chain.previous.proof_sha256,
                        original_calibration=height_record(self.observer.calibration),
                        goal=self.hint.end,actual_pair=[contact_fix_record(f) for f in (first,second)],
                        common_height_intervals_exact=[[str(v) for v in pair] for pair in common],
                        original_floor_unchanged=True,ordinary_grounded=False,contact_semantics_verified=False,
                        input_authorized=False,real_client_accepted=False))
                    arrival=SourceContactArrival(first,second,payload,sha256(payload).hexdigest(),now,
                        min(first.raw_fix.received_monotonic+2.5,second.raw_fix.received_monotonic+.5))
                self.local_steps+=1;self.history_sha256=history;self._no_progress=stalled
                self.reference,self.pose=second,pose;self.cursor=self._cursor=cursor
                self._reference_state=self._fix_state(second)
                self.phase='arrived' if arrival else 'ready'
                self.arrival=arrival;self._arrival_state=self._arrival_snapshot(arrival) if arrival else None
                self._busy=None;self._sealed=self._pending=None
                return SourceContactOutcome('arrived' if arrival else 'in_contact',second,window.coverage.sha256,arrival)
        except BaseException as error:self.cancel(str(error));raise

    def next_command(self):
        from .source_walk_driver import SourceWalkCommand
        with self.lock:
            self._check()
            if self.phase!='ready':raise RouteHalt('Contact movement must await stopped acknowledgment')
            self.validate_reference();point=self.reference.package_xyz[:2];target=self.targets[self.cursor]
            distance=math.dist(point,target)
            if distance<=.01:raise RouteHalt('Contact target reached without an acknowledged stopped pair')
            error=self.legacy.wrap180(self.legacy.bearing(*point,*target)-self.pose.heading)
            low,high=self.bounds.minimum_requested_hold,self.bounds.maximum_requested_hold
            if abs(error)>1.:
                if high<=self.motion.turn_latency:raise RouteHalt('Contact turn cannot overcome measured latency')
                kind='right' if error*self.motion.right_sign>0 else 'left'
                seconds=min(high,max(low,self.motion.turn_latency+abs(error)/self.motion.turn_rate))
            else:
                kind='forward';speed=self.pose.speed
                if not finite(speed) or speed<=0:raise RouteHalt('No measured contact forward speed')
                count=max(1,math.ceil(distance/(speed*high)));seconds=distance/speed/count
                if seconds<low:
                    if count!=1 or low*speed-distance>.25:raise RouteHalt('Minimum contact pulse overshoots target')
                    seconds=low
            return SourceWalkCommand(kind,seconds,self.cursor,target,self.reference)
