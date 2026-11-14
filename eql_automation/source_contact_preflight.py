"""Build a thin-sheet corridor and refresh its exact stopped departure.

This retains the original terrain, calibration and aggregate scope. No sender
is enabled, and neither a proposed rug height nor a future floor is adopted.
"""
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
import math

from .fixed_route_follower import RouteHalt
from .ground_binding import finite
from .native_region_policy import encoded
from .observed_height import height_record,height_snapshot
from .source_motion import SourceReceiptLedger
from .source_contact_plan import plan_source_contact,SourceContactIndex
from .source_contact_envelope import declare_contact_hypothesis
from .source_itinerary import SourceWalkHint
from .supervised_source import SupervisedSourcePolicy


from .source_contact_hint import SourceContactHint


@dataclass(frozen=True)
class SourceContactRegionCache:
    payload: bytes
    sha256: str

    def record(self):
        if type(self.payload) is not bytes or sha256(self.payload).hexdigest()!=self.sha256:
            raise ValueError('Contact preflight cache seal changed')
        record=json.loads(self.payload)
        if encoded(record)!=self.payload:
            raise ValueError('Contact preflight cache encoding changed')
        return record


@dataclass(frozen=True)
class SourceContactStart:
    first: object
    second: object
    cache_sha256: str
    issued_at: float
    expires_at: float
    input_authorized: bool = field(default=False,init=False)
    real_client_accepted: bool = field(default=False,init=False)


class SourceContactPreflight:
    def __init__(self,ledger,*,policy,hint,released_at):
        if (type(ledger) is not SourceReceiptLedger or type(policy) is not SupervisedSourcePolicy
                or policy.ledger is not ledger or type(hint) is not SourceContactHint
                or not finite(released_at)):
            raise ValueError('Current ordinary source ledger, policy, hint and last UP time required')
        hint.validate()
        self.ledger,self.policy,self.hint=ledger,policy,hint
        self.lock=ledger.lock
        self.phase,self.reason='new',''
        self.cache=self.start=None
        self.contact_index=self._index_state=None
        self._cache_state=self._start_state=None
        self._prepared_state=None
        self._replies=[]
        self._reply_states=[]
        self._lease=object()
        self._released_at=released_at
        self._objects=(ledger,policy,hint,self.lock)
        self._hint=encoded(asdict(hint))
        with self.lock:
            ledger._check();ledger.validate_reference()
            if (ledger.phase!='ready' or ledger._busy is not None
                    or hint.start!=ledger.reference.package_xyz[:2]
                    or hint.radius<ledger.bounds.body_radius
                    or released_at+.12>ledger.reference.raw_fix.received_monotonic):
                raise RouteHalt('Contact preflight requires an idle matching stopped departure')
            self._chain=ledger.chain
            self._state=ledger._state()
            self._reference=ledger.reference
            self._old_fix=ledger.observer._observation_snapshot(self._reference)
            self._height=height_snapshot(ledger.observer.calibration)
            self._scope=self._scope_state()
            b=ledger.bounds
            reach=b.forward_speed_upper_bound*b.maximum_actual_hold
            padding=b.body_radius+b.position_error+b.post_release_drift
            self._radius=max(hint.radius,
                (padding+2*reach*math.sin(math.radians(b.heading_error_degrees)/2))/math.cos(math.pi/16),
                (padding+b.pivot_displacement_upper_bound)/math.cos(math.pi/16))
            self._runout=reach
            self._parameters=(released_at,self._radius,self._runout)
            ledger.phase,ledger._busy='contact_preflight',self._lease
            try:self.check()
            except BaseException as error:self.cancel(error);raise

    def _scope_state(self):
        p=self.policy
        return (id(p.declaration),asdict(p.declaration),p.started,p.origin,p.reserved_hold,
                p.window,p.topology,tuple(id(v) for v in p._context))

    def _assert_context(self):
        l=self.ledger
        if (self.phase in ('cancelled','consumed')
                or any(a is not b for a,b in zip(self._objects,(l,self.policy,self.hint,self.lock)))
                or l.phase!='contact_preflight' or l._busy is not self._lease
                or self.policy.ledger is not l or l.chain is not self._chain
                or l._state()!=self._state or l.reference is not self._reference
                or l.observer._observation_snapshot(self._reference)!=self._old_fix
                or height_snapshot(l.observer.calibration)!=self._height
                or self._scope_state()!=self._scope or encoded(asdict(self.hint))!=self._hint
                or (self._released_at,self._radius,self._runout)!=self._parameters):
            raise RouteHalt('Contact preflight lease, departure or scope changed')
        if self._prepared_state is not None and (self.prepared_at,self.minimum_seq)!=self._prepared_state:
            raise RouteHalt('Contact preflight collection boundary changed')
        if self._cache_state is not None:
            if ((id(self.cache),self.cache.payload,self.cache.sha256)!=self._cache_state):
                raise RouteHalt('Contact preflight cache changed')
        if self.contact_index is not self._index_state:
            raise RouteHalt('Contact preflight contact index changed')
        if self.contact_index is not None:self.contact_index.check()

    def check(self):
        """No old-fix age check: geometry may outlive it, original scope may not."""
        with self.lock:
            self._assert_context()
            self.ledger._check()
            observation=self.policy.observe_preflight(self._lease)
            self._assert_context()
            return observation

    def cancel(self,reason='Contact preflight cancelled'):
        with self.lock:
            # A consumed ancestor must never stop its successor controller.
            if self.phase in ('cancelled','consumed'):return
            self.phase,self.reason='cancelled',str(reason)
            if self.ledger.phase=='contact_preflight' and self.ledger._busy is self._lease:
                self.ledger.cancel(str(reason))

    def prepare(self):
        try:
            with self.lock:
                self.check()
                if self.phase!='new':raise RouteHalt('Contact preflight can only build once')
                self.phase='building'
            l,h=self.ledger,self.hint
            hypothesis=declare_contact_hypothesis(l.static,h.face_ids,max_rise=h.max_rise)
            operations=tuple(SourceWalkHint(a,b) for a,b in zip(h.waypoints,h.waypoints[1:]))
            # Planning uses a private fork. Its future terrain is not a floor
            # observation and never replaces the original departure chain.
            plan=plan_source_contact(self._chain,operations,h.end,l.terrain,l.static,l.bsp,
                l.observer.policy,hypothesis,body_radius=l.bounds.body_radius,
                checked_radius=self._radius,forward_runout=self._runout,check_context=self.check,
                clock=l.clock)
            index=SourceContactIndex(plan)
            payload=encoded(dict(format='eql-source-contact-preflight-v1',hint=asdict(h),
                checked_radius=self._radius,target_end=h.end,forward_runout=self._runout,
                motion_bounds=asdict(l.bounds),motion=dict(vars(l.motion)),heading=l.pose.heading,
                departure=self._reference.package_xyz,
                raw_departure=self._reference.raw_fix.raw_coordinates,
                original_observed_at=self._reference.observed_at,
                original_calibration=height_record(l.observer.calibration),
                original_scope=asdict(self.policy.declaration),scope_started=self.policy.started,
                original_steps=l.steps,original_serial=l.serial,
                contact_plan=plan.record(),contact_plan_sha256=plan.sha256,
                requires_new_matching_pair=True,old_calibration_renewed=False,
                full_motion_coverage_checked=False,source_execution_wired=False,
                input_authorized=False,real_client_accepted=False))
            cache=SourceContactRegionCache(payload,sha256(payload).hexdigest())
            cache.record()
            with self.lock:
                idle=self.check()
                if self.phase!='building':raise RouteHalt('Contact preflight build was cancelled')
                self.prepared_at=idle.finished_at
                self.minimum_seq=l.observer.reader.log_line_seq
                self._prepared_state=(self.prepared_at,self.minimum_seq)
                self.cache=cache
                self.contact_index=self._index_state=index
                self._cache_state=(id(cache),cache.payload,cache.sha256)
                self.phase='prepared'
                return cache
        except BaseException as error:self.cancel(error);raise

    def observe_reply(self,raw):
        try:
            with self.lock:
                self.check()
                if (self.phase!='prepared' or len(self._replies)>=2
                        or raw.log_line_seq<=self.minimum_seq
                        or raw.received_monotonic<self.prepared_at):
                    raise RouteHalt('New stopped replies must follow the completed contact preflight')
                fix=self.ledger.observer.observe(raw,checked_chain=self._chain)
                if (fix.package_xyz!=self._reference.package_xyz
                        or fix.raw_fix.raw_coordinates!=self._reference.raw_fix.raw_coordinates):
                    raise RouteHalt('Contact departure changed after planning; replan required')
                self.check()
                self._replies.append(fix)
                self._reply_states.append(self.ledger.observer._observation_snapshot(fix))
                return fix
        except BaseException as error:self.cancel(error);raise

    def _pair(self,first,second):
        if (len(self._replies)!=2 or first is not self._replies[0]
                or second is not self._replies[1]):
            raise RouteHalt('Exact issued post-preflight stopped pair required')
        now=self.ledger._pair(first,second,self._chain,self._released_at,self.minimum_seq)
        for fix in (first,second):
            if (fix.package_xyz!=self._reference.package_xyz
                    or fix.raw_fix.raw_coordinates!=self._reference.raw_fix.raw_coordinates
                    or fix.raw_fix.received_monotonic<self.prepared_at):
                raise RouteHalt('Contact departure changed after planning')
        return now

    def _pair_at(self,first,second,now):
        """Final pure checks after the last physical observation/provider call."""
        observer=self.ledger.observer
        if (len(self._replies)!=2 or first is not self._replies[0] or second is not self._replies[1]
                or len(self._reply_states)!=2
                or [observer._observation_snapshot(v) for v in (first,second)]!=self._reply_states
                or not first.raw_fix.received_monotonic<=now<=first.raw_fix.received_monotonic+2.5
                or not second.raw_fix.received_monotonic<=now<=second.raw_fix.received_monotonic+.5
                or observer.reader.latest is not second.raw_fix
                or observer.reader.log_line_seq!=second.raw_fix.log_line_seq):
            raise RouteHalt('Contact start pair changed or expired during final observation')

    @staticmethod
    def _start_snapshot(start):
        return (id(start),id(start.first),id(start.second),start.cache_sha256,
                start.issued_at,start.expires_at,start.input_authorized,start.real_client_accepted)

    def bind_start(self,first,second):
        try:
            with self.lock:
                self.check()
                if self.phase!='prepared':raise RouteHalt('Prepared contact cache required')
                self._pair(first,second)
                idle=self.check()
                issued=idle.finished_at
                self._pair_at(first,second,issued)
                start=SourceContactStart(first,second,self.cache.sha256,issued,
                    second.raw_fix.received_monotonic+.5)
                self.start=start
                self._start_state=self._start_snapshot(start)
                self.phase='ready'
                return start
        except BaseException as error:self.cancel(error);raise

    def consume_start(self,start):
        """Refresh only the reference once; acquire a successor in the same lock.

        A future controller must be constructed by the caller under this same
        outer RLock. This function returns conditional geometry, not permission.
        """
        try:
            with self.lock:
                self.check()
                if (self.phase!='ready' or type(start) is not SourceContactStart or start is not self.start
                        or self._start_snapshot(start)!=self._start_state):
                    raise RouteHalt('Exact unconsumed contact start required')
                self._pair(start.first,start.second)
                idle=self.check()
                now=idle.finished_at
                if start is not self.start or self._start_snapshot(start)!=self._start_state:
                    raise RouteHalt('Contact start changed during final observation')
                self._pair_at(start.first,start.second,now)
                if not start.issued_at<=now<=start.expires_at:
                    raise RouteHalt('Contact start expired')
                self.ledger.reference=start.second
                self.ledger.phase,self.ledger._busy='ready',None
                self.phase='consumed'
                return self.cache
        except BaseException as error:self.cancel(error);raise
