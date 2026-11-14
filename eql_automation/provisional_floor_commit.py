"""Keep a released source step provisional while a crossing may start loading.

The receipt is checked at release, under the ordinary 0.3-second freshness
limit. No pose/floor changes until two fresh source observations resolve it.
Loading, cancellation or any failed check discards the source transaction.
This class neither reads a log nor sends input; its owner must retain one
exclusive source/arrival reader and provide the unchanged source context.
"""
from dataclasses import dataclass,field

from .fixed_route_follower import finite
from .ground_binding import AlignedWldFix,validate_ground_binding
from .ground_sweep import hull
from .motion_collection import immutable_binding
from .route_floor_commit import (RouteFloorCommit,_binding_snapshot,
                                _chain_snapshot,_controller_snapshot)
from .source_floor_chain import inside,rational
from .uinput_watchdog import PulseReceipt


@dataclass(frozen=True)
class SealedFloorReceipt:
    ticket: object
    receipt: PulseReceipt
    sealed_at: float
    expires_at: float
    source_context: tuple
    input_authorized: bool = field(default=False,init=False)
    real_client_accepted: bool = field(default=False,init=False)


class ProvisionalRouteFloorCommit(RouteFloorCommit):
    """A one-use receipt and floor fork; ordinary immediate commit is disabled.

    ``context_reader`` must reject any lost owner/input scope or source lease,
    and return the pinned owner, reader/log, source-zone and expected-line
    identities. It must not consume the reader or send input. The caller must
    process loading BEFORE source-context checks and cancel this ledger then.
    A quiet log alone never resolves the source transaction.
    """
    def __init__(self,*args,context_reader,maximum_resolution_seconds=10.,**kwargs):
        self._sealed=None
        super().__init__(*args,**kwargs)
        if (not callable(context_reader) or not finite(maximum_resolution_seconds)
                or not 0<maximum_resolution_seconds<=10.):
            raise ValueError('Current source context and bounded resolution time required')
        self.context_reader=context_reader
        self._context_reader=context_reader
        self.source_context=context_reader()
        if not immutable_binding(self.source_context) or not isinstance(self.source_context,tuple):
            raise ValueError('Immutable source context required')
        self._resolution_seconds=maximum_resolution_seconds
        self._last_seal_at=None

    def _discard(self,reason):
        self._sealed=None
        super()._discard(reason)

    def commit(self,*args,**kwargs):
        with self.lock:
            self._failure(ValueError('Provisional steps require a sealed receipt and fresh source pair'))

    def check_pending(self,ticket):
        with self.lock:
            if self._sealed is not None:
                self._failure(ValueError('A sealed step cannot authorize another movement'))
            return super().check_pending(ticket)

    def _context(self):
        if self.context_reader is not self._context_reader:
            raise ValueError('Source context reader changed')
        if self.context_reader()!=self.source_context:
            raise ValueError('Source owner/reader/zone context changed')

    def seal_release(self,ticket,receipt):
        """Validate an elapsed DOWN/UP receipt now, keeping pose/floor unchanged."""
        with self.lock:
            try:
                if (self._busy is not None or self._sealed is not None
                        or self._pending is None or ticket is not self._pending[0]):
                    raise ValueError('Missing exclusive unsealed floor ticket')
                self._busy='seal';pending=self._pending
                _,fork,_,base,fork_state,controller=pending
                self._context();now=self.clock();r=self.runner;r._check(now)
                if (_chain_snapshot(self.chain)!=base or _chain_snapshot(fork)!=fork_state
                        or _controller_snapshot(r)!=controller):
                    raise ValueError('Staged floor/controller changed before seal')
                p=ticket.preparation
                if not isinstance(receipt,PulseReceipt):raise ValueError('Actual watchdog receipt required')
                stamps=(receipt.down_started_at,receipt.down_completed_at,
                        receipt.up_started_at,receipt.up_completed_at)
                if (receipt.key_code!=p.movement_key or receipt.requested_seconds!=p.requested_seconds
                        or receipt.completion!='elapsed' or not all(finite(v) for v in stamps)
                        or not ticket.staged_at<=stamps[0]<=stamps[1]<=stamps[2]<=stamps[3]<=now
                        or stamps[0]-p.proposal.at>.05 or now-stamps[3]>.3
                        or not 0<receipt.maximum_held_seconds<=p.maximum_actual_hold):
                    raise ValueError('Receipt does not match the checked key, timing or hold bound')
                self._context();r._check(self.clock())
                current=_controller_snapshot(r)
                if current!=controller:raise ValueError('Source controller changed during receipt seal')
                finished=self.clock()
                self._context();r._check(finished);current=_controller_snapshot(r)
                if (self._busy!='seal' or self._pending is not pending or self._sealed is not None
                        or not finite(finished) or not now<=finished<=stamps[3]+.3
                        or _chain_snapshot(self.chain)!=base or _chain_snapshot(fork)!=fork_state
                        or current!=controller):
                    raise ValueError('Source transaction cancelled or changed during receipt seal')
                seal=SealedFloorReceipt(ticket,receipt,finished,
                    stamps[3]+self._resolution_seconds,self.source_context)
                self._sealed=(seal,pending);self._last_seal_at=finished;self._busy=None
                return seal
            except BaseException as error:self._failure(error)

    def _check_seal(self,seal,*,operation=None,controller=True):
        if (self._sealed is None or seal is not self._sealed[0]
                or self._pending is not self._sealed[1] or self._busy!=operation):
            raise ValueError('Missing current one-use sealed transaction')
        pending=self._pending
        _,fork,_,base,fork_state,original=pending
        self._context();self.runner._check(self.clock())
        state=_controller_snapshot(self.runner) if controller else _binding_snapshot(self.runner)
        if state!=(original if controller else original[0]):
            raise ValueError('Source controller changed during sealed observation')
        now=self.clock()
        self._context();self.runner._check(now)
        state=_controller_snapshot(self.runner) if controller else _binding_snapshot(self.runner)
        if (self._sealed is None or seal is not self._sealed[0]
                or self._sealed[1] is not pending or self._pending is not pending
                or self._busy!=operation or seal.source_context!=self.source_context
                or not finite(now) or not self._last_seal_at<=now<=seal.expires_at
                or _chain_snapshot(self.chain)!=base or _chain_snapshot(fork)!=fork_state
                or state!=(original if controller else original[0])):
            raise ValueError('Sealed source transaction changed, cancelled or expired')
        self._last_seal_at=now
        return pending,now

    def floor_for_observation(self,seal):
        """Read the exact provisional fork for each newly received raw fix.

        This does not commit it. Observe each reply immediately; the ordinary
        ground observer's <=0.5-second age limit remains unchanged.
        """
        with self.lock:
            try:return self._check_seal(seal)[0][1]
            except BaseException as error:self._failure(error)

    def resolve_source(self,seal,first,second):
        """Publish only after fresh stopped positions on the same source floor."""
        with self.lock:
            try:
                pending,now=self._check_seal(seal)
                self._busy='resolve'
                ticket,fork,_,base,fork_state,controller=pending
                r=self.runner;p=ticket.preparation
                for aligned in (first,second):
                    if not isinstance(aligned,AlignedWldFix):raise ValueError('Fresh aligned source pair required')
                    check=validate_ground_binding(aligned,height_calibration=r.height_calibration,
                        geometry_evidence=r.geometry_evidence,mesh_sha256=r.route.mesh_sha256,
                        zone_short_name=r.route.zone,now=now,motion_calibration_record_id=r.calibration,
                        mode=r.mode_reader())
                    xy=aligned.mesh_projection.package_xyz[:2]
                    z,ids=fork.floor_at(xy)
                    if (not check.candidate or not inside(rational((xy,))[0],rational(hull(p.footprint)))
                            or z!=aligned.source_floor.ground_wld_xyz[2]
                            or ids!=aligned.source_floor.source_surface_ids):
                        raise ValueError('Source pair is not supported by the sealed floor/footprint')
                _,now=self._check_seal(seal,operation='resolve')
                receipt=seal.receipt
                expected_steps=r.steps+1
                r.record_release(p.proposal,started_at=receipt.down_started_at,
                                 released_at=receipt.up_completed_at)
                _,now=self._check_seal(seal,operation='resolve',controller=False)
                if (r.phase!='await_stopped' or r.pending is not None or r.steps!=expected_steps
                        or r.released_at!=receipt.up_completed_at or r.step_started_at!=receipt.down_started_at):
                    raise ValueError('Sealed release was cancelled or did not integrate')
                r.observe_stopped(first,second,released_at=receipt.up_completed_at,now=now)
                self._check_seal(seal,operation='resolve',controller=False)
                # All callbacks have finished. A swallowed stop cannot resurrect
                # a transaction merely because observe_stopped wrote ready.
                if (self._sealed is None or self._sealed[0] is not seal or self._pending is not pending
                        or self._busy!='resolve' or r.phase not in ('ready','arrived')
                        or r.pending is not None or r.steps!=expected_steps or r.released_at is not None
                        or r.step_started_at!=receipt.down_started_at
                        or r.last_seq!=second.raw_fix.log_line_seq
                        or r.last_fix_at!=second.raw_fix.received_monotonic
                        or (r.pose.x,r.pose.y,r.pose.z)!=second.mesh_projection.package_xyz
                        or _chain_snapshot(self.chain)!=base or _chain_snapshot(fork)!=fork_state):
                    raise ValueError('Source resolution cancelled or did not accept the exact fresh pair')
                self.chain=fork;self._pending=None;self._sealed=None;self._busy=None
                return fork.previous
            except BaseException as error:self._failure(error)
