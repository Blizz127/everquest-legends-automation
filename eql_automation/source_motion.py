"""Provisional source walking: release receipts never commit a future floor.

This ledger owns no input device. A typed sender/policy must supply receipt
provenance. Only a fresh stationary pair on the exact swept branch, followed
by a checked cap at the observed endpoint, can publish its floor and pose.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from hashlib import sha256
import math
import threading

from .fixed_route_follower import RouteHalt
from .ground_binding import finite
from .ground_sweep import motion_footprint
from .installed_region_model import InstalledRegionModel
from .native_region_policy import encoded
from .route_floor_commit import _chain_snapshot
from .route_geometry import RouteMotionBounds
from .source_detour import swept_square
from .source_probe_geometry import check_source_footprint
from .source_observer import SourceItineraryObserver
from .uinput_watchdog import PulseReceipt


@dataclass(frozen=True)
class SourceMotionGeometry:
    kind: str
    footprint: tuple
    payload: bytes
    sha256: str

    def record(self):
        import json
        if type(self.payload) is not bytes or sha256(self.payload).hexdigest()!=self.sha256:
            raise ValueError('Source motion evidence changed')
        value=json.loads(self.payload)
        if encoded(value)!=self.payload:raise ValueError('Source motion evidence is not canonical')
        return value


@dataclass(frozen=True)
class SourceMotionTicket:
    reference: object
    geometry: SourceMotionGeometry
    serial: int
    proposed_at: float
    requested_seconds: float
    maximum_actual_hold: float
    movement_key: int
    input_authorized: bool = field(default=False,init=False)


@dataclass(frozen=True)
class SourceMotionSeal:
    ticket: SourceMotionTicket
    receipt: PulseReceipt
    sealed_at: float
    expires_at: float
    real_client_accepted: bool = field(default=False,init=False)


@dataclass(frozen=True)
class SourceMotionAck:
    seal: SourceMotionSeal
    first: object
    second: object
    reference: object
    floor_proof_sha256: str
    floor_index: int
    geometry_sha256: str
    acknowledged_at: float
    real_client_accepted: bool = field(default=False,init=False)


class SourceReceiptLedger:
    def __init__(self, observer, *, terrain, static, bsp, bounds, installed_model,
                 legacy, motion, heading, stop_lock):
        from .camp_source_observer import CampSourceObserver
        if (type(observer) not in (SourceItineraryObserver,CampSourceObserver) or type(bounds) is not RouteMotionBounds
                or type(installed_model) is not InstalledRegionModel
                or not isinstance(stop_lock,type(threading.RLock()))
                or not isinstance(motion,legacy.Motion)
                or not finite(heading) or not 0<=heading<360
                or not all(finite(v) and v>0 for v in (motion.run_speed,motion.turn_rate))
                or not finite(motion.back_speed) or motion.back_speed!=0
                or not finite(motion.turn_latency) or not 0<=motion.turn_latency<=.2
                or type(motion.right_sign) is not int or motion.right_sign not in (-1,1)):
            raise ValueError('Source ledger needs current observations, measured motion and shared stop lock')
        if type(observer) is CampSourceObserver and (stop_lock is not observer.lock
                or static is not observer.preparation.checkpoint._static
                or bsp is not observer.preparation.checkpoint._bsp
                or installed_model is not observer.preparation.checkpoint._model):
            raise ValueError('Camp source ledger must retain its exact geometry and stop lock')
        self.observer,self.terrain,self.static,self.bsp=observer,terrain,static,bsp
        self.bounds,self.model,self.legacy,self.motion=bounds,installed_model,legacy,motion
        self.lock,self.clock=stop_lock,observer.clock
        self.chain=observer.initial_floor_chain
        self.pose=legacy.PoseEstimator(motion);self.pose.heading=heading;self.pose.sign_verified=True
        self.phase,self.reason='need_start',''
        self.reference=None;self.serial=self.steps=0
        self._prepared=self._pending=self._sealed=None;self._busy=None
        self._context_objects=(observer,terrain,static,bsp,bounds,installed_model,legacy,motion,self.clock,stop_lock)
        self._motion=deepcopy(vars(motion));self._bounds=asdict(bounds)
        self._source_storage=self._source_snapshot()
        self._check()

    def cancel(self,reason='Source movement cancelled'):
        with self.lock:
            if self.phase=='stopped':return
            self.phase,self.reason='stopped',str(reason)
            self._prepared=self._pending=self._sealed=None;self._busy=None

    def _source_snapshot(self):
        # Complete loaded inventories are frozen. Pin their storage and query
        # implementations so prepared evidence cannot outlive a replacement.
        values=[]
        for view,names,query in (
                (self.terrain,('sources','source_minimum','source_maximum'),'source_faces_for_footprint'),
                (self.static,('sources','minimum','maximum'),'faces_for_footprint')):
            values.append(getattr(view,query))
            for name in names:
                value=getattr(view,name,None)
                values.append((id(value),getattr(getattr(value,'flags',None),'writeable',None)))
        return tuple(values)

    def _check(self):
        if self.phase=='stopped':raise RouteHalt(self.reason)
        now=self.observer.check()
        p=self.observer.policy
        self.bounds.validate_values(calibration_record_id=self.observer.planning_bounds.calibration_record_id,
                                    maximum_step_seconds=.2)
        p.check_context(zone=p.zone,pins=(p.mesh_sha256,self.terrain.archive_sha256,
            self.terrain.wld_sha256,self.static.inventory_sha256),bsp=self.bsp)
        if (any(a is not b for a,b in zip(self._context_objects,
                (self.observer,self.terrain,self.static,self.bsp,self.bounds,self.model,
                 self.legacy,self.motion,self.clock,self.lock)))
                or self.observer.reader.zone_id != p.zone_id
                or self.observer.terrain is not self.terrain
                or self.bounds is not self.observer.planning_bounds
                or vars(self.motion)!=self._motion or vars(self.bounds)!=self._bounds
                or self._source_snapshot()!=self._source_storage
                or self.bounds.body_height!=self.chain.body_height
                or self.bounds.maximum_requested_hold>.1
                or self.pose.motion is not self.motion
                or not finite(self.pose.heading) or not 0<=self.pose.heading<360
                or self.pose._sign_votes or self.pose.sign_conflict or self.pose.turn_dead):
            raise RouteHalt('Source movement bindings or motion assumptions changed')
        _chain_snapshot(self.chain)
        return now

    def _state(self):
        return (_chain_snapshot(self.chain),id(self.reference),self.steps,self.serial,
                id(self.pose),deepcopy(vars(self.pose)))

    def validate_reference(self):
        return self.observer.validate(self.reference,self.chain,maximum_age=.5)

    def _pair(self,first,second,branch,released_at,minimum_seq):
        self.observer.validate(first,branch)
        now=self.observer.validate(second,branch,maximum_age=.5)
        a,b=first.raw_fix,second.raw_fix
        if (not finite(released_at) or released_at+.12>a.received_monotonic
                or a.log_line_seq<=minimum_seq or b.log_line_seq!=a.log_line_seq+1
                or not .4-1e-9<=b.received_monotonic-a.received_monotonic<=2.5
                or math.dist(first.package_xyz[:2],second.package_xyz[:2])>.25
                or abs(first.package_xyz[2]-second.package_xyz[2])>.25
                or abs(a.raw_coordinates[2]-b.raw_coordinates[2])>.25
                or self.observer.reader.latest is not b):
            raise RouteHalt('Source movement needs a fresh stationary pair after release')
        return now

    def start(self,first,second,*,released_at):
        with self.lock:
            try:
                self._check()
                if self.phase!='need_start':raise RouteHalt('Source movement already started')
                self._pair(first,second,self.chain,released_at,
                    self.observer.calibration.last_calibration_log_line_seq)
                start=self.observer.start_xy
                if any(math.dist(v.package_xyz[:2],start)>.25 for v in (first,second)):
                    raise RouteHalt('Source start moved away from the planned current position')
                self.pose.correct(*second.package_xyz,age=0.)
                self._check()
                if self.phase!='need_start':raise RouteHalt('Source startup cancelled')
                self.reference=second;self.phase='ready'
            except BaseException as error:self.cancel(str(error));raise

    def _geometry(self,chain,kind,footprint):
        checked=check_source_footprint(chain,footprint,terrain=self.terrain,static=self.static,
            bsp=self.bsp,region_policy=self.observer.policy)
        payload=encoded(dict(kind=kind,footprint=footprint,terrain=asdict(checked.terrain),static=asdict(checked.static),
            bsp=asdict(checked.bsp),native=asdict(checked.native),itinerary_sha256=self.observer.itinerary.sha256,
            policy=self.observer.policy.record(),input_authorized=False,real_client_accepted=False))
        return checked.branch,SourceMotionGeometry(kind,footprint,payload,sha256(payload).hexdigest())

    def prepare(self,kind):
        """Read-only maximum-hold geometry outside the OFF lock."""
        try:
            with self.lock:
                self._check()
                self.model.check_policy(self.observer.policy)
                if self.phase!='ready' or self._busy is not None or kind not in ('forward','left','right'):
                    raise RouteHalt('No idle source position/control for geometry')
                self.observer.validate(self.reference,self.chain,maximum_age=.5)
                state=self._state();b=self.bounds;chain=self.chain.fork()
                footprint=motion_footprint(self.reference.package_xyz[:2],self.pose.heading,
                    b.forward_speed_upper_bound*b.maximum_actual_hold if kind=='forward' else 0.,
                    position_error=b.position_error,heading_error_degrees=b.heading_error_degrees,
                    post_release_drift=b.post_release_drift,
                    extra_radius=b.body_radius+(0. if kind=='forward' else b.pivot_displacement_upper_bound))
                self.phase='preparing'
            fork,geometry=self._geometry(chain,kind,footprint)
            with self.lock:
                self._check();self.observer.validate(self.reference,self.chain,maximum_age=.5)
                self.model.check_policy(self.observer.policy)
                if self.phase!='preparing' or self._state()!=state:
                    raise RouteHalt('Source geometry cancelled or reference changed')
                self._prepared=(geometry,fork,_chain_snapshot(fork),state)
                self.phase='prepared'
                return geometry
        except BaseException as error:self.cancel(str(error));raise

    def stage(self,geometry,*,requested_seconds):
        """Create the proposal only after watchdog READY, without doing geometry."""
        with self.lock:
            try:
                self._check()
                self.observer.validate(self.reference,self.chain,maximum_age=.5)
                if (self.phase!='prepared' or self._prepared is None
                        or geometry is not self._prepared[0] or self._state()!=self._prepared[3]
                        or _chain_snapshot(self._prepared[1])!=self._prepared[2]
                        or not finite(requested_seconds)
                        or not self.bounds.minimum_requested_hold<=requested_seconds<=self.bounds.maximum_requested_hold):
                    raise RouteHalt('No exact prepared source movement')
                geometry.record()
                # Timestamp the actual proposal after its preflight, rather
                # than spending its 50ms DOWN window on work done before the
                # ticket exists. Fresh-scene/reference checks still apply.
                now=self._check()
                if (self.phase!='prepared' or self._prepared is None or geometry is not self._prepared[0]
                        or self._state()!=self._prepared[3]
                        or _chain_snapshot(self._prepared[1])!=self._prepared[2]):
                    raise RouteHalt('Source proposal cancelled during final check')
                self.serial+=1
                ticket=SourceMotionTicket(self.reference,geometry,self.serial,now,requested_seconds,
                    self.bounds.maximum_actual_hold,{'forward':103,'left':105,'right':106}[geometry.kind])
                self._pending=(ticket,self._prepared[1],self._prepared[2],self._state())
                self._prepared=None;self.phase='proposed'
                self.check_pending(ticket)
                return ticket
            except BaseException as error:self.cancel(str(error));raise

    def check_pending(self,ticket):
        with self.lock:
            self._check()
            if (self.phase!='proposed' or self._pending is None or self._pending[0] is not ticket
                    or self._state()!=self._pending[3]
                    or _chain_snapshot(self._pending[1])!=self._pending[2]
                    or self._busy is not None):
                raise RouteHalt('Source movement transaction changed')
            ticket.geometry.record()

    def seal_release(self,ticket,receipt):
        with self.lock:
            try:
                self.check_pending(ticket);pending=self._pending;now=self.clock()
                if type(receipt) is not PulseReceipt:raise RouteHalt('Actual source pulse receipt required')
                stamps=(receipt.down_started_at,receipt.down_completed_at,receipt.up_started_at,receipt.up_completed_at)
                if (receipt.completion!='elapsed' or receipt.key_code!=ticket.movement_key
                        or receipt.requested_seconds!=ticket.requested_seconds
                        or not all(finite(v) for v in stamps)
                        or not ticket.proposed_at<=stamps[0]<=stamps[1]<=stamps[2]<=stamps[3]<=now
                        or stamps[0]-ticket.proposed_at>.05 or now-stamps[3]>.3
                        or not 0<receipt.maximum_held_seconds<=ticket.maximum_actual_hold):
                    raise RouteHalt('Source receipt does not match the selected key/timing')
                self.check_pending(ticket);self.model.check_policy(self.observer.policy)
                finished=self.observer.check()
                if (self.phase!='proposed' or self._pending is not pending
                        or self._sealed is not None or self._busy is not None
                        or self._state()!=pending[3] or _chain_snapshot(pending[1])!=pending[2]
                        or not now<=finished<=stamps[3]+.3):
                    raise RouteHalt('Source receipt seal expired, changed or cancelled')
                seal=SourceMotionSeal(ticket,receipt,finished,stamps[3]+10.)
                self._sealed=seal;self.phase='await_stopped'
                return seal
            except BaseException as error:self.cancel(str(error));raise

    def _check_seal(self,seal):
        now=self._check()
        self.model.check_policy(self.observer.policy)
        if (self.phase!='await_stopped' or self._sealed is not seal or self._pending is None
                or self._pending[0] is not seal.ticket or self._state()!=self._pending[3]
                or _chain_snapshot(self._pending[1])!=self._pending[2]
                or not seal.sealed_at<=now<=seal.expires_at):
            raise RouteHalt('Source release is missing, changed or expired')
        return self._pending[1]

    def floor_for_observation(self,seal):
        with self.lock:
            try:return self._check_seal(seal)
            except BaseException as error:self.cancel(str(error));raise

    def observe_reply(self,seal,raw):
        """Consume a source reply and stop the transaction on observation failure."""
        with self.lock:
            try:
                branch=self._check_seal(seal)
                result=self.observer.observe(raw,checked_chain=branch)
                if self._check_seal(seal) is not branch:
                    raise RouteHalt('Source reply branch changed')
                return result
            except BaseException as error:self.cancel(str(error));raise

    def acknowledge_stopped(self,seal,first,second):
        try:
            with self.lock:
                branch=self._check_seal(seal)
                if self._busy is not None:raise RouteHalt('Another source acknowledgment is active')
                self._busy='acknowledge'
                self._pair(first,second,branch,seal.receipt.up_completed_at,self.reference.raw_fix.log_line_seq)
                state=self._state();pose=deepcopy(self.pose);pose.motion=self.motion
                point=second.package_xyz[:2]
            # Exact endpoint cap is checked outside the stop lock. It may add
            # a second floor-chain index; this is not an extra movement pulse.
            cap,geometry=self._geometry(branch,'observed_endpoint_cap',swept_square(point,point,self.bounds.body_radius))
            with self.lock:
                self._check_seal(seal)
                self._pair(first,second,branch,seal.receipt.up_completed_at,self.reference.raw_fix.log_line_seq)
                if self._busy!='acknowledge' or self._state()!=state:
                    raise RouteHalt('Source acknowledgment cancelled')
                receipt=seal.receipt;kind=seal.ticket.geometry.kind
                pose.predict(receipt.maximum_held_seconds,self.legacy.Controls(
                    forward=kind=='forward',turn=None if kind=='forward' else kind))
                pose.predict(second.raw_fix.received_monotonic-receipt.up_completed_at,self.legacy.STOP)
                report=pose.correct(*second.package_xyz,age=0.)
                if report.get('jumped') or pose._sign_votes or pose.sign_conflict or pose.turn_dead or pose.blocked_fixes>=2:
                    raise RouteHalt('Observed source movement contradicts measured motion')
                reference=self.observer.rebind_cap(second,branch,cap)
                self._check_seal(seal)
                now=self.observer.validate(reference,cap,maximum_age=.5)
                if self._busy!='acknowledge' or self._state()!=state or self._sealed is not seal:
                    raise RouteHalt('Source acknowledgment changed before publication')
                self.chain,self.pose,self.reference=cap,pose,reference
                self.steps+=1;self.phase='ready';self._busy=None;self._sealed=self._pending=None
                return SourceMotionAck(seal,first,second,reference,cap.previous.proof_sha256,
                    cap.index,geometry.sha256,now)
        except BaseException as error:self.cancel(str(error));raise
