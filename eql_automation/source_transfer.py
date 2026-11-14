"""Receipt-bound supervised step progression with a provisional cursor.

The ordinary floor stays leased and unchanged until a complete observed cap
can be published. Partial steps never impersonate ordinary grounded fixes.
"""
from collections import deque
from copy import deepcopy
from dataclasses import dataclass,field
from fractions import Fraction
from hashlib import sha256
import math

from .fixed_route_follower import RouteHalt
from .ground_binding import finite
from .ground_sweep import motion_footprint,area,clip,hull
from .native_region_policy import encoded
from .route_floor_commit import _chain_snapshot
from .source_detour import swept_square
from .source_floor_chain import inside,rational
from .source_motion import SourceReceiptLedger,SourceMotionGeometry,SourceMotionTicket,SourceMotionSeal
from .source_observer import SourceStoppedFix
from .source_step_approach import plan_source_step_approach,source_step_supports,covered_by_union
from .uinput_watchdog import PulseReceipt


@dataclass(frozen=True)
class SourceTransitionFix:
    raw_fix: object
    package_xyz: tuple
    supports: tuple
    height_matches_unique_support: bool
    window_sha256: str
    observed_at: float
    observed_grounded: bool = field(default=False,init=False)
    input_authorized: bool = field(default=False,init=False)
    real_client_accepted: bool = field(default=False,init=False)


@dataclass(frozen=True)
class SourceTransferWindow:
    plan: object
    geometry: SourceMotionGeometry
    branches: tuple
    branch_snapshots: tuple
    step_index: int
    center_footprint: tuple
    branch_origins: tuple
    state: tuple


@dataclass(frozen=True)
class SourceTransferOutcome:
    kind: str
    reference: object
    window_sha256: str
    floor_proof_sha256: str | None = None
    real_client_accepted: bool = field(default=False,init=False)


class SourceTransferController:
    """Own one ordinary ledger temporarily, through the same input transport."""
    def __init__(self,driver,boundary):
        from .source_walk_driver import SourceWalkDriver,SourceStepBoundary
        if type(driver) is not SourceWalkDriver or type(boundary) is not SourceStepBoundary:
            raise ValueError('Exact source driver and issued step boundary required')
        l=driver.ledger
        if type(l) is not SourceReceiptLedger:raise ValueError('Ordinary source ledger required')
        self.ordinary,self.driver,self.boundary=l,driver,boundary
        self.observer,self.bounds,self.model,self.motion,self.legacy=l.observer,l.bounds,l.model,l.motion,l.legacy
        self.lock,self.clock=l.lock,l.clock
        self.phase,self.reason='ready',''
        self._prepared=self._pending=self._sealed=None;self._busy=None
        self._issued=deque(maxlen=2);self.local_steps=0
        self._lease=object()
        with self.lock:
            try:
                l._check();l.validate_reference()
                if (l.phase!='ready' or l._busy is not None or boundary is not driver._boundary
                        or driver._steps is not driver._step_hints or driver.targets is not driver._targets
                        or boundary.reference is not l.reference or boundary.start!=l.reference.package_xyz
                        or boundary.floor_proof_sha256!=l.chain.previous.proof_sha256):
                    raise RouteHalt('No current source step available for transfer')
                self.hint=driver._steps[boundary.cell_index]
                self._hint_state=tuple(vars(self.hint).items())
                self._driver_index=driver.index
                self._ordinary_state=l._state()
                self.chain=l.chain;self.reference=l.reference
                self.pose=deepcopy(l.pose);self.pose.motion=self.motion
                self.serial=l.serial
                self.started=self.clock()
                driver._active_step=boundary.cell_index
                l.phase='transfer';l._busy=self._lease
                self._check()
            except BaseException as error:self.cancel(str(error));raise

    @property
    def steps(self):return self.ordinary.steps+self.local_steps

    def cancel(self,reason='Source transfer cancelled'):
        with self.lock:
            if self.phase=='stopped':return
            self.phase,self.reason='stopped',str(reason)
            self._prepared=self._pending=self._sealed=None;self._busy=None
            if self.ordinary.phase=='transfer' and self.ordinary._busy is self._lease:
                self.ordinary.cancel(reason)

    def _check(self):
        if self.phase=='stopped':raise RouteHalt(self.reason)
        l=self.ordinary;now=l._check()
        if (l.phase!='transfer' or l._busy is not self._lease or l._state()!=self._ordinary_state
                or self.chain is not l.chain or self.observer is not l.observer or self.bounds is not l.bounds
                or self.model is not l.model or self.motion is not l.motion or self.clock is not l.clock
                or self.driver.ledger is not l or self.driver.index!=self._driver_index
                or self.driver._boundary is not self.boundary
                or self.driver._active_step!=self.boundary.cell_index
                or self.driver._steps is not self.driver._step_hints
                or self.driver._steps.get(self.boundary.cell_index) is not self.hint
                or tuple(vars(self.hint).items())!=self._hint_state
                or self.pose.motion is not self.motion or self.pose._sign_votes
                or self.pose.sign_conflict or self.pose.turn_dead
                or not self.started<=now<=self.started+60. or self.local_steps>=32):
            raise RouteHalt('Source transfer ownership, floor, motion or bounded session changed')
        return now

    def _state(self):
        return (id(self.reference),id(self.pose),deepcopy(vars(self.pose)),self.serial,self.local_steps,
            self.ordinary._state())

    @staticmethod
    def _fix_state(fix):
        return (id(fix.raw_fix),tuple(vars(fix.raw_fix).items()),tuple(vars(fix).items()))

    @staticmethod
    def _window_check(window):
        if tuple(_chain_snapshot(c) for c in window.branches)!=window.branch_snapshots:
            raise RouteHalt('Conditional source transition branches changed')
        if window.plan.conditional_branches is not window.branches:
            raise RouteHalt('Conditional source transition branch tuple changed')

    def validate_reference(self):
        now=self._check()
        if type(self.reference) is SourceStoppedFix:
            return self.observer.validate(self.reference,self.chain,maximum_age=.5)
        return self._validate_fix(self.reference,maximum_age=.5)

    def _validate_fix(self,fix,*,maximum_age=2.5):
        now=self._check();issued=next((v for v in self._issued if v[0] is fix),None)
        if (type(fix) is not SourceTransitionFix or issued is None
                or issued[2]!=self._fix_state(fix)
                or not 0<=now-fix.raw_fix.received_monotonic<=maximum_age):
            raise RouteHalt('Need an unchanged fresh issued transition observation')
        self._window_check(issued[1])
        return now

    def prepare(self,kind):
        try:
            with self.lock:
                self._check();self.validate_reference();self.model.check_policy(self.observer.policy)
                if self.phase!='ready' or self._busy is not None or kind not in ('forward','left','right'):
                    raise RouteHalt('Source transfer is not ready for a new movement')
                state=self._state();b=self.bounds;cursor=self.reference.package_xyz[:2]
                reach=b.forward_speed_upper_bound*b.maximum_actual_hold if kind=='forward' else 0.
                extra=0. if kind=='forward' else b.pivot_displacement_upper_bound
                footprint=motion_footprint(cursor,self.pose.heading,reach,position_error=b.position_error,
                    heading_error_degrees=b.heading_error_degrees,post_release_drift=b.post_release_drift,
                    extra_radius=b.body_radius+extra)
                centers=motion_footprint(cursor,self.pose.heading,reach,position_error=b.position_error,
                    heading_error_degrees=b.heading_error_degrees,post_release_drift=b.post_release_drift,
                    extra_radius=extra)
                radius=(b.body_radius+extra+b.position_error+b.post_release_drift
                    +2*reach*math.sin(math.radians(b.heading_error_degrees)/2))/math.cos(math.pi/16)
                angle=math.radians(self.pose.heading)
                end=(cursor[0]+reach*math.sin(angle),cursor[1]+reach*math.cos(angle))
                self.phase='preparing'
            def current():
                with self.lock:
                    self._check();self.model.check_policy(self.observer.policy)
                    if self.phase!='preparing' or self._state()!=state:
                        raise RouteHalt('Source transfer preparation cancelled')
            plan=plan_source_step_approach(self.chain,self.ordinary.reference.package_xyz[:2],self.hint,
                self.ordinary.terrain,self.ordinary.static,self.ordinary.bsp,self.observer.policy,
                footprint=footprint,nominal_end=end,body_radius=b.body_radius,checked_radius=radius,
                check_context=current,clock=self.clock)
            branches=plan.checked_branches();data=plan.record()
            step=next(i for i,c in enumerate(data['cells']) if c['kind']=='step')
            payload=encoded(dict(kind=kind,plan_sha256=plan.sha256,footprint=footprint,center_footprint=centers,
                parent_proof_sha256=self.chain.previous.proof_sha256,input_authorized=False))
            geometry=SourceMotionGeometry(kind,footprint,payload,sha256(payload).hexdigest())
            with self.lock:
                current();self.validate_reference()
                if self.phase!='preparing' or self._state()!=state:
                    raise RouteHalt('Source transfer preparation changed before publication')
                self._prepared=SourceTransferWindow(plan,geometry,branches,plan.branch_snapshots,step,centers,
                    tuple(tuple(c['end']) for c in data['cells']),state)
                self.phase='prepared'
                return geometry
        except BaseException as error:self.cancel(str(error));raise

    def stage(self,geometry,*,requested_seconds):
        with self.lock:
            try:
                now=self.validate_reference();window=self._prepared
                if (self.phase!='prepared' or window is None or window.geometry is not geometry
                        or self._state()!=window.state or not finite(requested_seconds)
                        or not self.bounds.minimum_requested_hold<=requested_seconds<=self.bounds.maximum_requested_hold):
                    raise RouteHalt('No exact prepared source transfer movement')
                self._window_check(window);geometry.record();self.serial+=1
                ticket=SourceMotionTicket(self.reference,geometry,self.serial,now,requested_seconds,
                    self.bounds.maximum_actual_hold,{'forward':103,'left':105,'right':106}[geometry.kind])
                self._pending=(ticket,window,self._state());self._prepared=None;self.phase='proposed'
                self.check_pending(ticket);return ticket
            except BaseException as error:self.cancel(str(error));raise

    def check_pending(self,ticket):
        with self.lock:
            self._check()
            if (self.phase!='proposed' or self._pending is None or self._pending[0] is not ticket
                    or self._pending[2]!=self._state() or self._busy is not None):
                raise RouteHalt('Source transfer ticket changed')
            self._window_check(self._pending[1]);ticket.geometry.record()

    def seal_release(self,ticket,receipt):
        with self.lock:
            try:
                self.check_pending(ticket);pending=self._pending;now=self.clock()
                if type(receipt) is not PulseReceipt:raise RouteHalt('Actual transfer pulse receipt required')
                stamps=(receipt.down_started_at,receipt.down_completed_at,receipt.up_started_at,receipt.up_completed_at)
                if (receipt.completion!='elapsed' or receipt.key_code!=ticket.movement_key
                        or receipt.requested_seconds!=ticket.requested_seconds
                        or not all(finite(v) for v in stamps)
                        or not ticket.proposed_at<=stamps[0]<=stamps[1]<=stamps[2]<=stamps[3]<=now
                        or stamps[0]-ticket.proposed_at>.05 or now-stamps[3]>.3
                        or not 0<receipt.maximum_held_seconds<=ticket.maximum_actual_hold):
                    raise RouteHalt('Source transfer receipt timing/control mismatch')
                self.model.check_policy(self.observer.policy);finished=self._check()
                if (self.phase!='proposed' or self._pending is not pending or self._state()!=pending[2]
                        or not now<=finished<=stamps[3]+.3):
                    raise RouteHalt('Source transfer receipt expired or cancelled')
                self._window_check(pending[1])
                seal=SourceMotionSeal(ticket,receipt,finished,stamps[3]+10.)
                self._sealed=seal;self.phase='await_stopped';return seal
            except BaseException as error:self.cancel(str(error));raise

    def _check_seal(self,seal):
        now=self._check();self.model.check_policy(self.observer.policy)
        if (self.phase not in ('await_stopped','settling') or self._sealed is not seal
                or self._pending is None or self._pending[0] is not seal.ticket
                or self._state()!=self._pending[2] or not seal.sealed_at<=now<=seal.expires_at):
            raise RouteHalt('Source transfer receipt missing, changed or expired')
        self._window_check(self._pending[1]);return self._pending[1]

    def observe_reply(self,seal,raw):
        with self.lock:
            try:
                window=self._check_seal(seal);o=self.observer;now=o.check()
                o.validate_raw(raw,now)
                if (o.reader.latest is not raw or o.reader.log_line_seq!=raw.log_line_seq
                        or raw.log_line_seq<=o.last_seq or not 0<=now-raw.received_monotonic<=.5):
                    raise RouteHalt('Need one fresh unreplayed transition reply')
                point=(raw.raw_coordinates[1],raw.raw_coordinates[0])
                if not inside(rational((point,))[0],rational(window.center_footprint)):
                    raise RouteHalt('Observed center left the full motion bounds')
                supports=source_step_supports(window.plan,point,self.ordinary.terrain,self.ordinary.static,
                    check_context=lambda:self._check_seal(seal))
                if not supports:raise RouteHalt('No source support in the checked transition')
                height=raw.raw_coordinates[2]-o.calibration.raw_z_minus_source_z
                e=window.plan.record()['cells'][window.step_index]['transfer']['evidence']
                low=min(float(Fraction(v)) for v in e['riser']['lower_heights'])
                high=float(Fraction(e['transfer_height_exact']))
                tolerance=o.calibration.residual_limit
                if not min(low,*(float(Fraction(s.height_exact)) for s in supports))-tolerance<=height<=high+tolerance:
                    raise RouteHalt('Transition height lies outside its checked model')
                matches=len(supports)==1 and abs(height-float(Fraction(supports[0].height_exact)))<=tolerance
                fix=SourceTransitionFix(raw,(*point,height),supports,matches,window.plan.sha256,now)
                self._check_seal(seal);finished=o.check()
                if (self.phase not in ('await_stopped','settling') or self._sealed is not seal
                        or self._pending is None or self._pending[1] is not window or self._busy is not None
                        or self._pending[2]!=self._state()
                        or self.ordinary.phase!='transfer' or self.ordinary._busy is not self._lease
                        or o.reader.latest is not raw or o.reader.log_line_seq!=raw.log_line_seq
                        or not 0<=finished-raw.received_monotonic<=.5):
                    raise RouteHalt('Transition reply changed or expired during observation')
                o.last_seq=raw.log_line_seq
                self._issued.append((fix,window,self._fix_state(fix)));return fix
            except BaseException as error:self.cancel(str(error));raise

    def _pair(self,seal,first,second):
        self._validate_fix(first);now=self._validate_fix(second,maximum_age=.5)
        a,b=first.raw_fix,second.raw_fix
        if (first.window_sha256!=second.window_sha256
                or seal.receipt.up_completed_at+.12>a.received_monotonic
                or a.log_line_seq<=seal.ticket.reference.raw_fix.log_line_seq
                or b.log_line_seq!=a.log_line_seq+1
                or not .4-1e-9<=b.received_monotonic-a.received_monotonic<=2.5
                or math.dist(first.package_xyz[:2],second.package_xyz[:2])>.25
                or abs(first.package_xyz[2]-second.package_xyz[2])>.25
                or self.observer.reader.latest is not b):
            raise RouteHalt('Need a fresh stationary transition pair after release')
        return now

    def _straddles(self,window,point):
        data=window.plan.record();cell=data['cells'][window.step_index];e=cell['transfer']['evidence']
        cap=swept_square(point,point,self.bounds.body_radius)
        if not covered_by_union(cap,tuple(c['footprint'] for c in data['cells'])):return False
        sources=self.ordinary.terrain.source_faces_for_footprint(tuple(tuple(p) for p in cell['footprint']))
        inventory={(s.fragment,s.face):s for s in sources};polygon=rational(cap)
        def overlaps(name):
            return any(area(clip(polygon,hull((Fraction(x),Fraction(y)) for y,x,z in inventory[tuple(k)].vertices_wld)))>0
                for k in e[name]['selected_ids'])
        return overlaps('lower_endpoint') and overlaps('landing_endpoint')

    def _cap(self,branch,origin,point):
        """Continue a saved lineage to the actual point before checking its cap."""
        try:
            return self.ordinary._geometry(branch,'observed_transition_cap',
                swept_square(point,point,self.bounds.body_radius))
        except ValueError as error:
            if not str(error).startswith('Source motion terrain: '):raise
        continued,_=self.ordinary._geometry(branch,'observed_transition_continuation',
            swept_square(origin,point,self.bounds.body_radius))
        return self.ordinary._geometry(continued,'observed_transition_cap',
            swept_square(point,point,self.bounds.body_radius))

    def acknowledge_stopped(self,seal,first,second):
        try:
            with self.lock:
                window=self._check_seal(seal);self._pair(seal,first,second)
                if self._busy is not None:raise RouteHalt('Source transfer acknowledgment already active')
                if not first.height_matches_unique_support or not second.height_matches_unique_support:
                    self.phase='settling'
                    return SourceTransferOutcome('settling',second,window.plan.sha256)
                state=self._state();busy=object();self._busy=busy
                point=second.package_xyz[:2];height=float(Fraction(second.supports[0].height_exact))
                pose=deepcopy(self.pose);pose.motion=self.motion
            candidates=[]
            for index,branch in enumerate(window.branches):
                try:
                    cap,geometry=self._cap(branch,window.branch_origins[index],point)
                    first_point=first.package_xyz[:2]
                    first_cap=(cap if first_point==point else
                        self._cap(branch,window.branch_origins[index],first_point)[0])
                except ValueError as error:
                    if str(error).startswith('Source motion terrain: '):continue
                    raise
                if (abs(cap.floor_at(point)[0]-height)<=1e-9
                        and abs(first_cap.floor_at(first_point)[0]-float(Fraction(first.supports[0].height_exact)))<=1e-9):
                    candidates.append((index>=window.step_index,cap,geometry))
            if candidates:
                if len({after for after,_,_ in candidates})!=1:
                    raise RouteHalt('Observed cap belongs to ambiguous transition lineages')
                after,cap,geometry=candidates[-1]
            elif not self._straddles(window,point):
                raise RouteHalt('Observed transition lacks a complete cap or a checked riser overlap')
            with self.lock:
                self._check_seal(seal);self._pair(seal,first,second)
                if self._busy is not busy or self._state()!=state:
                    raise RouteHalt('Source transfer acknowledgment cancelled')
                r=seal.receipt;kind=seal.ticket.geometry.kind
                pose.predict(r.maximum_held_seconds,self.legacy.Controls(forward=kind=='forward',turn=None if kind=='forward' else kind))
                pose.predict(second.raw_fix.received_monotonic-r.up_completed_at,self.legacy.STOP)
                correction=pose.correct(*second.package_xyz,age=0.)
                if correction.get('jumped') or pose._sign_votes or pose.sign_conflict or pose.turn_dead or pose.blocked_fixes>=2:
                    raise RouteHalt('Observed step movement contradicts its measured controls')
                if candidates:
                    reference,cap_state=self.observer._sample(second.raw_fix,cap,second.observed_at)
                else:reference=second
                self._check_seal(seal);now=self._validate_fix(second,maximum_age=.5)
                if self._busy is not busy or self._state()!=state or self._sealed is not seal:
                    raise RouteHalt('Source transfer changed before publication')
                self.local_steps+=1
                if candidates:
                    l=self.ordinary
                    self.observer._issued.append((reference,cap,cap_state,self.observer._observation_snapshot(reference)))
                    l.chain,l.pose,l.reference=cap,pose,reference
                    l.steps+=self.local_steps;l.serial=self.serial;l.phase='ready';l._busy=None
                    if after:
                        self.driver.index=self.boundary.cell_index+1;self.driver._active_step=None
                        # An early stair landing can hand off this step before
                        # its ordinary connector finishes. The checked actual
                        # step landing supersedes that earlier approach.
                        self.driver._stair_connector=None
                    self.driver._boundary=None
                    self.phase='landed' if after else 'approach'
                else:
                    self.reference,self.pose=reference,pose;self.phase='ready'
                self._busy=None;self._sealed=self._pending=None
                return SourceTransferOutcome(self.phase if candidates else 'in_transfer',reference,
                    window.plan.sha256,cap.previous.proof_sha256 if candidates else None)
        except BaseException as error:self.cancel(str(error));raise

    def next_command(self):
        from .source_walk_driver import SourceWalkCommand
        with self.lock:
            self._check()
            if self.phase!='ready':raise RouteHalt('Step movement must await stopped acknowledgment')
            self.validate_reference()
            point=self.reference.package_xyz[:2];target=self.boundary.end[:2]
            distance=math.dist(point,target)
            if distance<=.25:
                direction=tuple((self.hint.end[k]-self.hint.start[k])/math.dist(self.hint.start,self.hint.end) for k in (0,1))
                target=tuple(target[k]+.25*direction[k] for k in (0,1));distance=math.dist(point,target)
            error=self.legacy.wrap180(self.legacy.bearing(*point,*target)-self.pose.heading)
            low,high=self.bounds.minimum_requested_hold,self.bounds.maximum_requested_hold
            if abs(error)>1.:
                if high<=self.motion.turn_latency:raise RouteHalt('Step turn cannot overcome measured latency')
                kind='right' if error*self.motion.right_sign>0 else 'left'
                seconds=min(high,max(low,self.motion.turn_latency+abs(error)/self.motion.turn_rate))
            else:
                kind='forward';speed=self.pose.speed
                if not finite(speed) or speed<=0:raise RouteHalt('No measured step forward speed')
                count=max(1,math.ceil(distance/(speed*high)));seconds=distance/speed/count
                if seconds<low:
                    if count!=1 or low*speed-distance>.25:raise RouteHalt('Minimum step pulse overshoots target')
                    seconds=low
            return SourceWalkCommand(kind,seconds,self.boundary.cell_index,target,self.reference)
