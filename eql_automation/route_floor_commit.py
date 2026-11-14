"""Commit a conditional floor fork only after its matching movement receipt.

This owns no input device and grants no input permit. The sender adapter must
establish the receipt's provenance, and an external live guard must prove that
the supplied footprint covers the proposed motion with measured bounds and
current scene/static/BSP/dynamic checks. Identity binding here does not prove
those facts or turn an offline FloorTrial into movement authority.
The separate owner-supervised measurement policy retains these as conditional
planning hypotheses; a committed receipt never upgrades their verification.
"""
from copy import copy,deepcopy
from dataclasses import asdict,dataclass,field
from hashlib import sha256
import json
import threading
import time

from .fixed_route_follower import FixedRouteFollower,RouteHalt,RouteProposal,finite
from .floor_replay import FloorTrial
from .ground_binding import AlignedWldFix,validate_ground_binding
from .ground_sweep import hull
from .portal_precision import SourceFace
from .source_floor_chain import SourceFloorChain,rational
from .uinput_watchdog import PulseReceipt


@dataclass(frozen=True)
class FloorStepPreparation:
    proposal: RouteProposal
    reference_fix: AlignedWldFix
    footprint: tuple
    sources: tuple[SourceFace,...]
    requested_seconds: float
    maximum_actual_hold: float
    movement_key: int
    motion_bounds_record_id: str
    geometry_sha256: str
    input_authorized: bool = field(default=False,init=False)


@dataclass(frozen=True)
class FloorCommitTicket:
    preparation: FloorStepPreparation
    staged_at: float
    input_authorized: bool = field(default=False,init=False)


def _chain_snapshot(chain):
    if (not isinstance(chain,SourceFloorChain) or chain.halted
            or chain.previous is None or not chain.previous.candidate
            or chain.index!=chain.previous.index+1):
        raise ValueError('No committed conditional source floor')
    return (id(chain),chain.inventory_sha256,chain.seed_evidence_sha256,chain.seed_ids,
        chain.body_height,chain.index,chain.halted,chain.previous,chain._expanded,
        tuple(sorted(chain._selected.items())))


def _binding_snapshot(runner):
    return (id(runner.route),runner.route,id(runner.height_calibration),runner.height_calibration,
        id(runner.geometry_evidence),runner.geometry_evidence,runner.calibration,runner.generation,
        runner.mode_reader(),runner.binding,
        runner.max_step_seconds,runner.max_steps,runner.radius,runner.height_tolerance,
        id(runner.generation_reader),id(runner.mode_reader),id(runner.motion),deepcopy(vars(runner.motion)))


def _controller_snapshot(runner):
    return (_binding_snapshot(runner),runner.index,runner.last_seq,runner.last_fix_at,
        runner.phase,id(runner.pending),runner.serial,runner.steps,runner.last_at,
        runner.component,runner.best_remaining,runner.no_progress_steps,runner.step_started_at,
        runner.released_at,id(runner.pose),deepcopy(vars(runner.pose)))


class RouteFloorCommit:
    """One staged update, serialized with the caller's same OFF/GO stop lock.

    ``check_geometry(preparation, chain_copy)`` must evaluate that exact request
    and return its proposed chain and FloorTrial. It receives a shallow fork;
    SourceFloorChain.advance replaces its state without changing the base.
    Staging and committing never reserve, send or release any key themselves.
    """
    def __init__(self,runner,chain,*,stop_lock,clock=time.monotonic):
        if (not isinstance(runner,FixedRouteFollower)
                or not isinstance(stop_lock,type(threading.RLock())) or not callable(clock)):
            raise ValueError('Need a route follower, shared reentrant stop lock and clock')
        _chain_snapshot(chain)
        if chain.inventory_sha256!=runner.geometry_evidence.source_wld_sha256:
            raise ValueError('Source floor inventory differs from route geometry')
        self.runner,self.chain,self.lock,self.clock=runner,chain,stop_lock,clock
        self._pending=None
        self._busy=None

    def cancel(self,reason='route floor transaction cancelled'):
        """Discard pending floor state and halt; the external sender releases."""
        with self.lock:
            self._discard(reason)

    def _discard(self,reason):
        self._pending=None
        self._busy=None
        try:self.runner.halt(reason)
        except RouteHalt:pass

    def _failure(self,error):
        self._discard('Route floor transaction: '+str(error))
        if isinstance(error,(KeyboardInterrupt,SystemExit)):raise error
        raise RouteHalt(self.runner.reason) from error

    def check_pending(self,ticket):
        """Recheck a staged request without consuming it or granting input."""
        with self.lock:
            try:
                self.runner._check(self.clock())
                if self._busy is not None or self._pending is None or ticket is not self._pending[0]:
                    raise ValueError('Missing current one-use floor ticket')
                _,fork,_,base,fork_state,controller=self._pending
                if (_chain_snapshot(self.chain)!=base or _chain_snapshot(fork)!=fork_state
                        or _controller_snapshot(self.runner)!=controller):
                    raise ValueError('Staged floor or route context changed')
            except BaseException as error:self._failure(error)

    def stage(self,proposal,*,reference_fix,footprint,sources,requested_seconds,
              maximum_actual_hold,movement_key,motion_bounds_record_id,check_geometry):
        with self.lock:
            try:
                if self._pending is not None or self._busy is not None:
                    raise ValueError('Another floor operation is pending')
                self._busy='stage'
                r=self.runner;now=self.clock();r._check(now)
                if (r.phase!='proposed' or proposal is not r.pending
                        or not isinstance(proposal,RouteProposal) or proposal.segment_index!=r.index
                        or not 0<=now-proposal.at<=.05 or not callable(check_geometry)):
                    raise ValueError('Missing fresh exclusive route proposal')
                expected=(103 if proposal.forward and proposal.turn is None else
                          {'left':105,'right':106}.get(proposal.turn) if not proposal.forward else None)
                if (type(movement_key) is not int or expected is None or movement_key!=expected
                        or not all(finite(v) for v in (requested_seconds,maximum_actual_hold))
                        or not 0<requested_seconds<=maximum_actual_hold<=r.max_step_seconds
                        or not isinstance(motion_bounds_record_id,str) or not motion_bounds_record_id):
                    raise ValueError('Invalid movement key or external hold-bound binding')
                if not isinstance(reference_fix,AlignedWldFix):raise ValueError('Missing current aligned fix')
                raw=reference_fix.raw_fix
                check=validate_ground_binding(reference_fix,height_calibration=r.height_calibration,
                    geometry_evidence=r.geometry_evidence,mesh_sha256=r.route.mesh_sha256,
                    zone_short_name=r.route.zone,now=now,motion_calibration_record_id=r.calibration,
                    mode=r.mode_reader())
                if (not check.candidate or raw.log_line_seq!=r.last_seq
                        or raw.received_monotonic!=r.last_fix_at
                        or (raw.zone_id,raw.zone_display_name,raw.log_epoch,raw.zone_generation)!=r.binding
                        or reference_fix.mesh_projection.package_xyz!=(r.pose.x,r.pose.y,r.pose.z)):
                    raise ValueError('Reference fix differs from stopped route observation')
                xy=reference_fix.mesh_projection.package_xyz[:2]
                source_z,source_ids=self.chain.floor_at(xy)
                if (source_z!=reference_fix.source_floor.ground_wld_xyz[2]
                        or source_ids!=reference_fix.source_floor.source_surface_ids):
                    raise ValueError('Reference fix differs from committed source floor')
                if (not isinstance(footprint,tuple) or not 3<=len(footprint)<=64
                        or any(not isinstance(p,tuple) or len(p)!=2 or not all(finite(v) for v in p) for p in footprint)
                        or len(hull(footprint))!=len(footprint)
                        or not isinstance(sources,tuple) or not 1<=len(sources)<=128
                        or any(not isinstance(s,SourceFace) for s in sources)):
                    raise ValueError('Missing bounded footprint or complete source tuple')
                from .source_floor_chain import inside
                if not inside(rational((xy,))[0],rational(hull(footprint))):
                    raise ValueError('Footprint excludes the current reference position')
                geometry=sha256(json.dumps({'footprint':footprint,'sources':[asdict(s) for s in sources]},
                    sort_keys=True,separators=(',',':')).encode()).hexdigest()
                prepared=FloorStepPreparation(proposal,reference_fix,footprint,sources,requested_seconds,
                    maximum_actual_hold,movement_key,motion_bounds_record_id,geometry)
                base=_chain_snapshot(self.chain);controller=_controller_snapshot(r)
                fork,trial=check_geometry(prepared,copy(self.chain))
                r._check(self.clock())
                if (self._busy!='stage' or _chain_snapshot(self.chain)!=base or _controller_snapshot(r)!=controller
                        or self.clock()-proposal.at>.05):
                    raise ValueError('Route context changed during geometry evaluation')
                if (fork is self.chain or not isinstance(fork,SourceFloorChain)
                        or not isinstance(trial,FloorTrial) or not trial.candidate
                        or not trial.coverage.candidate or trial.source_support is None or not trial.source_support.candidate
                        or trial.floor_step is None or not trial.floor_step.candidate
                        or trial.floor_step is not fork.previous or trial.floor_step.occupancy is None
                        or not trial.floor_step.occupancy.candidate or fork.index!=self.chain.index+1
                        or trial.floor_step.index!=self.chain.index
                        or trial.floor_step.previous_sha256!=self.chain.previous.proof_sha256
                        or trial.floor_step.geometry_sha256!=geometry
                        or (fork.inventory_sha256,fork.seed_evidence_sha256,fork.seed_ids,fork.body_height)!=
                           (self.chain.inventory_sha256,self.chain.seed_evidence_sha256,self.chain.seed_ids,self.chain.body_height)):
                    raise ValueError('Checked fork does not extend this exact floor request')
                expanded=rational(hull((x+dx,y+dy) for x,y in footprint
                    for dx in (-.002,.002) for dy in (-.002,.002)))
                if fork._expanded!=expanded or tuple(sorted(fork._selected))!=trial.floor_step.selected_ids:
                    raise ValueError('Checked fork footprint or selected faces differ')
                inventory={(s.fragment,s.face):s for s in sources}
                for key,(source,vertices,polygon) in fork._selected.items():
                    expected_vertices=tuple((y,x,z) for x,y,z in inventory[key].vertices_wld)
                    if (source!=inventory[key] or vertices!=expected_vertices
                            or polygon!=rational(hull(v[:2] for v in expected_vertices))):
                        raise ValueError('Checked fork selected geometry differs')
                staged_at=self.clock();r._check(staged_at)
                if (self._busy!='stage' or not 0<=staged_at-proposal.at<=.05 or _chain_snapshot(self.chain)!=base
                        or _controller_snapshot(r)!=controller):
                    raise ValueError('Geometry result became stale before ticket staging')
                ticket=FloorCommitTicket(prepared,staged_at)
                self._pending=(ticket,fork,trial,base,_chain_snapshot(fork),controller)
                self._busy=None
                return ticket
            except BaseException as error:self._failure(error)

    def commit(self,ticket,receipt):
        with self.lock:
            try:
                if self._busy is not None or self._pending is None or ticket is not self._pending[0]:
                    raise ValueError('Missing current one-use floor ticket')
                self._busy='commit'
                r=self.runner;now=self.clock();r._check(now)
                pending=self._pending
                _,fork,trial,base,fork_state,controller=pending
                if (_chain_snapshot(self.chain)!=base or _chain_snapshot(fork)!=fork_state
                        or _controller_snapshot(r)!=controller):
                    raise ValueError('Staged floor or route context changed before receipt')
                p=ticket.preparation;proposal=p.proposal
                if not isinstance(receipt,PulseReceipt):raise ValueError('Missing watchdog receipt')
                stamps=(receipt.down_started_at,receipt.down_completed_at,receipt.up_started_at,receipt.up_completed_at)
                if (receipt.key_code!=p.movement_key or receipt.requested_seconds!=p.requested_seconds
                        or receipt.completion!='elapsed' or not all(finite(v) for v in stamps)
                        or not ticket.staged_at<=stamps[0]<=stamps[1]<=stamps[2]<=stamps[3]<=now
                        or stamps[0]-proposal.at>.05 or now-stamps[3]>.3
                        or not 0<receipt.maximum_held_seconds<=p.maximum_actual_hold):
                    raise ValueError('Receipt does not match the checked key, timing or hold bound')
                expected_steps=r.steps+1
                r.record_release(proposal,started_at=stamps[0],released_at=stamps[3])
                r._check(self.clock())
                if (self._busy!='commit' or self._pending is not pending
                        or _binding_snapshot(r)!=controller[0]
                        or _chain_snapshot(self.chain)!=base or _chain_snapshot(fork)!=fork_state
                        or r.phase!='await_stopped' or r.pending is not None or r.steps!=expected_steps
                        or r.released_at!=stamps[3] or r.step_started_at!=stamps[0]):
                    raise ValueError('Receipt integration was cancelled or did not complete')
                self.chain=fork
                self._pending=None
                self._busy=None
                return self.chain.previous
            except BaseException as error:self._failure(error)
