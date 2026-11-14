"""Receipt-bound grounded stair traversal on the retained supervised sender.

Contact behavior remains a client hypothesis. Each pulse needs full cached
coverage and the existing physical policy; only an actual complete landing
can change the ordinary floor. This module does not start an owner session.
"""
from collections import deque
from copy import deepcopy
from dataclasses import asdict,dataclass,field,replace
from fractions import Fraction as F
from hashlib import sha256
import math

from .fixed_route_follower import RouteHalt
from .ground_binding import finite
from .ground_sweep import hull,motion_footprint
from .native_region_policy import encoded
from .observed_height import height_snapshot
from .source_detour import swept_square
from .source_floor_chain import SourceFloorChain,positive_overlap
from .source_motion import SourceMotionGeometry
from .source_observer import SourceStoppedFix
from .source_stair_coverage import covers_closed
from .source_stair_preflight import SourceStairPreflight
from .source_step import digest,expanded,vertices
from .source_transfer import SourceTransferController,SourceTransferOutcome


@dataclass(frozen=True)
class SourceStairFix:
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
class SourceStairWindow:
    geometry: SourceMotionGeometry
    coverage: object
    center_footprint: tuple
    reachable: tuple
    state: tuple
    coverage_state: tuple
    geometry_state: tuple


class SourceStairController(SourceTransferController):
    """Reuse only ticket/UP-seal transport; stair observations stay distinct."""
    def __init__(self,preflight,start):
        if type(preflight) is not SourceStairPreflight:
            raise ValueError('Exact completed stair preflight required')
        l=preflight.ledger
        self.ordinary,self.policy=l,preflight.policy
        self.lock,self.clock=l.lock,l.clock
        self.phase,self.reason='ready',''
        self._prepared=self._pending=self._sealed=self._busy=None
        self._ticket_state=self._seal_state=None;self._staging=False
        self._issued=deque(maxlen=2);self.local_steps=0;self._no_progress=0
        self._lease=object();self._bound=False
        consumed=False
        with self.lock:
            try:
                preflight.check()
                if preflight.hint.vertical_model!='bounded_source_contacts' or preflight.contact_index is None:
                    raise RouteHalt('Grounded contact cache required for stair movement')
                self.cache,self.index,self.hint=preflight.cache,preflight.contact_index,preflight.hint
                self._cache_state=(id(self.cache),self.cache.payload,self.cache.sha256)
                self.tread_ids=self._treads=preflight.checked_tread_ids
                self._hint_state=encoded(asdict(self.hint))
                self._index=self.index
                self._height=height_snapshot(l.observer.calibration)
                self._scope=(id(self.policy.declaration),asdict(self.policy.declaration),self.policy.started,
                    tuple(id(v) for v in self.policy._context[1:]),self.policy.window,self.policy.topology)
                preflight.consume_start(start);consumed=True
                self.observer,self.bounds,self.model,self.motion,self.legacy=l.observer,l.bounds,l.model,l.motion,l.legacy
                self.chain,self.reference=l.chain,l.reference
                self.pose=deepcopy(l.pose);self.pose.motion=self.motion;self.serial=l.serial
                self._ordinary_state=l._state()
                self._original_fix=l.observer._observation_snapshot(l.reference)
                self.history_sha256=digest(dict(cache=self.cache.sha256,start_seq=start.second.raw_fix.log_line_seq))
                l.phase,l._busy='stair_transfer',self._lease
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

    def cancel(self,reason='Stair movement cancelled'):
        with self.lock:
            if self.phase=='stopped':return
            self.phase,self.reason='stopped',str(reason)
            self._prepared=self._pending=self._sealed=self._busy=None
            if self.ordinary.phase=='stair_transfer' and self.ordinary._busy is self._lease:
                self.ordinary.cancel(reason)

    def _check(self):
        if self.phase=='stopped':raise RouteHalt(self.reason)
        l,p=self.ordinary,self.policy;now=l._check()
        scope=(id(p.declaration),asdict(p.declaration),p.started,
            tuple(id(v) for v in p._context[1:]),p.window,p.topology)
        if (l.phase!='stair_transfer' or l._busy is not self._lease or l._state()!=self._ordinary_state
                or l.observer._observation_snapshot(l.reference)!=self._original_fix
                or self.chain is not l.chain or self.observer is not l.observer or self.bounds is not l.bounds
                or self.model is not l.model or self.motion is not l.motion or self.legacy is not l.legacy
                or self.clock is not l.clock or self.lock is not l.lock
                or self.index is not self._index
                or (id(self.cache),self.cache.payload,self.cache.sha256)!=self._cache_state
                or self.tread_ids!=self._treads
                or encoded(asdict(self.hint))!=self._hint_state
                or height_snapshot(self.observer.calibration)!=self._height or scope!=self._scope
                or p.ledger not in ((self,) if self._bound else (l,self))
                or not p.started<=now<=p.started+p.declaration.maximum_seconds
                or self.pose.motion is not self.motion or not finite(self.pose.heading)
                or not 0<=self.pose.heading<360 or self.pose._sign_votes
                or self.pose.sign_conflict or self.pose.turn_dead):
            raise RouteHalt('Stair lease, cache, original floor or scope changed')
        self.index.check()
        return now

    def _state(self):
        return (*super()._state(),self.history_sha256,self._no_progress)

    def _window_check(self,window):
        self.index.check()
        if (type(window) is not SourceStairWindow
                or (id(window.coverage),window.coverage.payload,window.coverage.sha256,
                    window.center_footprint,window.reachable)!=window.coverage_state
                or (id(window.geometry),tuple(vars(window.geometry).items()))!=window.geometry_state):
            raise RouteHalt('Stair pulse coverage changed')

    @staticmethod
    def _ticket_snapshot(ticket):return (id(ticket),tuple(vars(ticket).items()))

    def stage(self,geometry,*,requested_seconds):
        with self.lock:
            self._ticket_state=None;self._staging=True
            try:return super().stage(geometry,requested_seconds=requested_seconds)
            finally:self._staging=False

    def check_pending(self,ticket):
        super().check_pending(ticket)
        value=self._ticket_snapshot(ticket)
        if self._ticket_state is None and self._staging:self._ticket_state=value
        if self._ticket_state!=value:raise RouteHalt('Stair pulse ticket changed')

    def seal_release(self,ticket,receipt):
        with self.lock:
            seal=super().seal_release(ticket,receipt)
            self._seal_state=(id(seal),tuple(vars(seal).items()),tuple(vars(receipt).items()))
            return seal

    def _check_seal(self,seal):
        window=super()._check_seal(seal)
        if (self._ticket_snapshot(seal.ticket)!=self._ticket_state
                or (id(seal),tuple(vars(seal).items()),tuple(vars(seal.receipt).items()))!=self._seal_state):
            raise RouteHalt('Stair release receipt changed')
        return window

    def _validate_fix(self,fix,*,maximum_age=2.5):
        now=self._check();entry=next((v for v in self._issued if v[0] is fix),None)
        if (type(fix) is not SourceStairFix or entry is None or entry[2]!=self._fix_state(fix)
                or not 0<=now-fix.raw_fix.received_monotonic<=maximum_age):
            raise RouteHalt('Need an unchanged fresh issued stair observation')
        self._window_check(entry[1]);return now

    def _height_interval(self,raw):
        c=self.observer.calibration
        z=F(raw.raw_coordinates[2])-F(c.raw_z_minus_source_z);error=F(c.residual_limit)
        return z-error,z+error

    def _origin(self,point):
        b=self.bounds
        if b.position_error+b.post_release_drift:
            return tuple(tuple(map(F,p)) for p in motion_footprint(point,0.,0.,
                position_error=b.position_error,heading_error_degrees=0.,post_release_drift=b.post_release_drift))
        return (tuple(map(F,point)),)

    def prepare(self,kind):
        try:
            with self.lock:
                self._check();self.validate_reference()
                if self.phase!='ready' or self._busy is not None:
                    raise RouteHalt('Stair movement must await stopped acknowledgment')
                state=self._state();reference=self.reference;self.phase='preparing'
            coverage=self.index.cover_pulse(reference.package_xyz[:2],self.pose.heading,kind,self.bounds,
                height_interval=self._height_interval(reference.raw_fix))
            record=coverage.record()
            footprint=tuple(tuple(p) for p in record['body_footprint'])
            centers=tuple(tuple(F(v) for v in p) for p in record['center_footprint_exact'])
            reachable=tuple(sorted({i for row in record['reachable_by_start'] for i in row['reachable']}))
            payload=encoded(dict(kind=kind,cache_sha256=self.cache.sha256,coverage_sha256=coverage.sha256,
                parent_proof_sha256=self.chain.previous.proof_sha256,footprint=footprint,
                receipt_history_sha256=self.history_sha256,input_authorized=False))
            geometry=SourceMotionGeometry(kind,footprint,payload,sha256(payload).hexdigest())
            with self.lock:
                self._check();self.validate_reference()
                if self.phase!='preparing' or self._state()!=state:
                    raise RouteHalt('Stair preparation cancelled or changed')
                self._prepared=SourceStairWindow(geometry,coverage,centers,reachable,state,
                    (id(coverage),coverage.payload,coverage.sha256,centers,reachable),
                    (id(geometry),tuple(vars(geometry).items())))
                self.phase='prepared';return geometry
        except BaseException as error:self.cancel(str(error));raise

    def observe_reply(self,seal,raw):
        try:
            with self.lock:
                window=self._check_seal(seal);o=self.observer;now=o.check();o.validate_raw(raw,now)
                if (o.reader.latest is not raw or o.reader.log_line_seq!=raw.log_line_seq
                        or raw.log_line_seq<=o.last_seq or not 0<=now-raw.received_monotonic<=.5):
                    raise RouteHalt('Need one fresh unreplayed stair reply')
                point=(raw.raw_coordinates[1],raw.raw_coordinates[0])
                if not covers_closed((tuple(map(F,point)),),(window.center_footprint,)):
                    raise RouteHalt('Observed center left the full stair motion bounds')
                interval=self._height_interval(raw)
                compatible=tuple(v.state_index for v in self.index.compatible(self._origin(point),interval))
                if not compatible or not set(compatible)<=set(window.reachable):
                    raise RouteHalt('Observed stair height/state is outside receipt coverage')
                height=raw.raw_coordinates[2]-o.calibration.raw_z_minus_source_z
                fix=SourceStairFix(raw,(*point,height),interval,compatible,window.coverage.sha256,now)
                self._check_seal(seal);finished=o.check()
                if (self.phase not in ('await_stopped','settling') or self._sealed is not seal
                        or self._pending is None or self._pending[1] is not window or self._busy is not None
                        or self._pending[2]!=self._state() or o.reader.latest is not raw
                        or o.reader.log_line_seq!=raw.log_line_seq
                        or self.ordinary.phase!='stair_transfer' or self.ordinary._busy is not self._lease
                        or not 0<=finished-raw.received_monotonic<=.5):
                    raise RouteHalt('Stair reply changed or expired during observation')
                o.last_seq=raw.log_line_seq
                self._issued.append((fix,window,self._fix_state(fix)));return fix
        except BaseException as error:self.cancel(str(error));raise

    def _landing(self,first,second,history):
        final=len(self.hint.tread_ids)-1
        if any(fix.compatible_states!=(final,) for fix in (first,second)):return None
        radius=(self.bounds.body_radius+self.bounds.position_error+self.bounds.post_release_drift)/math.cos(math.pi/16)
        cap=swept_square(first.package_xyz[:2],second.package_xyz[:2],radius)
        boundary=expanded(cap);sources=self.ordinary.terrain.source_faces_for_footprint(cap)
        permitted=set(self.tread_ids[-1])
        seeds=tuple((s.fragment,s.face) for s in sources if (s.fragment,s.face) in permitted
                    and positive_overlap(boundary,hull(p[:2] for p in vertices(s))))
        if not seeds:raise RouteHalt('Actual stair landing has no final tread support')
        temporary=SourceFloorChain(inventory_sha256=self.chain.inventory_sha256,
            seed_evidence_sha256=self.cache.sha256,seed_ids=seeds,body_height=self.chain.body_height)
        floor=temporary.advance(cap,sources)
        if not floor.candidate:raise RouteHalt('Actual stair landing: '+floor.reason)
        checked,geometry=self.ordinary._geometry(temporary,'actual_stair_landing',cap)
        if not set(checked.previous.selected_ids)<=permitted:
            raise RouteHalt('Actual stair landing escaped the final tread lineage')
        floor=replace(checked.previous,index=self.chain.index,carried_ids=(),joins=(),
            previous_sha256=self.chain.previous.proof_sha256,proof_sha256='',
            reason='receipt_bound_conditional_stair_landing')
        proof=digest(dict(cache_sha256=self.cache.sha256,receipt_history_sha256=history,
            actual_pair=[dict(xyz=f.package_xyz,seq=f.raw_fix.log_line_seq,observed_at=f.observed_at)
                         for f in (first,second)],geometry_sha256=geometry.sha256,landing=asdict(floor)))
        branch=self.chain.fork();branch.previous=replace(floor,proof_sha256=proof)
        branch.index=self.chain.index+1;branch._expanded=checked._expanded;branch._selected=checked._selected.copy()
        # Validate both original replies on the same complete cap, without
        # replaying observation or renewing either timestamp.
        self.observer._sample(first.raw_fix,branch,first.observed_at)
        reference,snapshot=self.observer._sample(second.raw_fix,branch,second.observed_at)
        return branch,reference,snapshot

    def acknowledge_stopped(self,seal,first,second):
        try:
            with self.lock:
                window=self._check_seal(seal);self._pair(seal,first,second)
                if self._busy is not None:raise RouteHalt('Stair acknowledgment already active')
                state=self._state();busy=object();self._busy=busy
                pose=deepcopy(self.pose);pose.motion=self.motion
                history=digest(dict(previous=self.history_sha256,coverage=window.coverage.sha256,
                    receipt=asdict(seal.receipt),pair=[dict(xyz=f.package_xyz,
                        states=f.compatible_states,seq=f.raw_fix.log_line_seq) for f in (first,second)]))
            landing=self._landing(first,second,history)
            with self.lock:
                self._check_seal(seal);self._pair(seal,first,second)
                if self._busy is not busy or self._state()!=state:
                    raise RouteHalt('Stair acknowledgment cancelled')
                r=seal.receipt;kind=seal.ticket.geometry.kind
                pose.predict(r.maximum_held_seconds,self.legacy.Controls(forward=kind=='forward',
                    turn=None if kind=='forward' else kind))
                pose.predict(second.raw_fix.received_monotonic-r.up_completed_at,self.legacy.STOP)
                correction=pose.correct(*second.package_xyz,age=0.)
                stalled=(self._no_progress+1 if kind=='forward' and
                    math.dist(self.reference.package_xyz[:2],second.package_xyz[:2])<.01 else 0)
                if (correction.get('jumped') or pose._sign_votes or pose.sign_conflict or pose.turn_dead
                        or pose.blocked_fixes>=2 or stalled>=3):
                    raise RouteHalt('Observed stair movement contradicts measured controls')
                self._check_seal(seal);self._pair(seal,first,second)
                idle=self.policy.observe_transfer(self,seal)
                now=idle.finished_at
                if self._busy is not busy or self._state()!=state or self._sealed is not seal:
                    raise RouteHalt('Stair movement changed before publication')
                if (self.phase not in ('await_stopped','settling')
                        or not 0<=now-first.raw_fix.received_monotonic<=2.5
                        or not 0<=now-second.raw_fix.received_monotonic<=.5
                        or self.observer.reader.latest is not second.raw_fix
                        or self.observer.reader.log_line_seq!=second.raw_fix.log_line_seq
                        or any(not any(e[0] is fix and e[2]==self._fix_state(fix) for e in self._issued)
                               for fix in (first,second))):
                    raise RouteHalt('Stair pair changed or expired during final physical observation')
                if landing is None and math.dist(second.package_xyz[:2],self.hint.end)<=.01:
                    self._busy=None;self.phase='settling'
                    return SourceTransferOutcome('settling',second,window.coverage.sha256)
                self.local_steps+=1;self.history_sha256=history;self._no_progress=stalled
                if landing is not None:
                    branch,reference,snapshot=landing;l=self.ordinary
                    self.observer._issued.append((reference,branch,snapshot,self.observer._observation_snapshot(reference)))
                    l.chain,l.pose,l.reference=branch,pose,reference
                    l.steps+=self.local_steps;l.serial=self.serial;l.phase='ready';l._busy=None
                    self.phase='landed'
                else:
                    reference=second;self.reference,self.pose=reference,pose;self.phase='ready'
                self._busy=None;self._sealed=self._pending=None
                return SourceTransferOutcome('landed' if landing else 'in_transfer',reference,
                    window.coverage.sha256,branch.previous.proof_sha256 if landing else None)
        except BaseException as error:self.cancel(str(error));raise

    def next_command(self):
        from .source_walk_driver import SourceWalkCommand
        with self.lock:
            self._check()
            if self.phase!='ready':raise RouteHalt('Stair movement must await stopped acknowledgment')
            self.validate_reference();point=self.reference.package_xyz[:2];target=self.hint.end
            distance=math.dist(point,target)
            if distance<=.01:raise RouteHalt('Stair target reached without an observed complete landing')
            error=self.legacy.wrap180(self.legacy.bearing(*point,*target)-self.pose.heading)
            low,high=self.bounds.minimum_requested_hold,self.bounds.maximum_requested_hold
            if abs(error)>1.:
                if high<=self.motion.turn_latency:raise RouteHalt('Stair turn cannot overcome measured latency')
                kind='right' if error*self.motion.right_sign>0 else 'left'
                seconds=min(high,max(low,self.motion.turn_latency+abs(error)/self.motion.turn_rate))
            else:
                kind='forward';speed=self.pose.speed
                if not finite(speed) or speed<=0:raise RouteHalt('No measured stair forward speed')
                count=max(1,math.ceil(distance/(speed*high)));seconds=distance/speed/count
                if seconds<low:
                    if count!=1 or low*speed-distance>.25:raise RouteHalt('Minimum stair pulse overshoots target')
                    seconds=low
            return SourceWalkCommand(kind,seconds,0,target,self.reference)
