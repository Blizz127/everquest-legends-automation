"""One owner-supervised input/log scope across a retained camp probe sequence.

Supervision is an explicit continuation choice, not independent scene or motion
verification. The sender still checks exact transaction ancestry and owns the
descriptor, DOWN deadline and unconditional release. This module sends nothing
and never consumes the location reader or resets a log-veto baseline.
"""
from dataclasses import asdict,dataclass

from .camp_motion_continuity import CampInputContinuity
from .camp_probe_runtime import CampProbeRuntime
from .camp_probe_sender import CampProbeAuthorization,CampProbeInputPolicy
from .camp_probe_transaction import CampProbeTransaction,CampProbeTicket
from .flat_record import flat_record_state
from .g2_safety_provider import GameWindowIdentity,focused_game_identity
from .ground_binding import finite
from .owner_input_observer import OwnerInputObservation
from .scene_log_veto import SceneLogVeto


@dataclass(frozen=True)
class SupervisedCampProbeDeclaration:
    record_id: str
    bounds_record_id: str
    owner_supervised_continuation: bool
    maximum_total_hold: float


class SupervisedCampProbeScope:
    """Shared deadline, physical observer, hazard latch and reservation budget."""
    def __init__(self,runtime,*,declaration,monitor,gate,expected_window,log_veto,
                 check_current,started_at,expires_at):
        if (type(runtime) is not CampProbeRuntime
                or type(declaration) is not SupervisedCampProbeDeclaration
                or type(monitor) is not CampInputContinuity
                or type(expected_window) is not GameWindowIdentity
                or type(log_veto) is not SceneLogVeto or not callable(check_current)
                or not all(finite(v) for v in (started_at,expires_at))):
            raise ValueError('Exact retained camp scope and explicit supervision required')
        r=runtime;d=declaration;b=r.root.bounds
        if (r.index!=0 or r.phase!='collect_start' or r.transaction is None
                or not isinstance(d.record_id,str) or not d.record_id
                or d.bounds_record_id!=b.record_id or d.owner_supervised_continuation is not True
                or not finite(d.maximum_total_hold)
                or not 0<d.maximum_total_hold<=len(r.probes)*b.maximum_actual_hold
                or not started_at<=r.started<=expires_at<=r.started+r.maximum_seconds
                or monitor.observer is not r.owner_input
                or log_veto is not r.log_veto
                # CampInputContinuity retains the journey engine binding:
                # six live identities followed by the owner stop generation.
                or len(monitor.binding)<7 or type(monitor.binding[6]) is not int
                or log_veto.cancel_generation!=monitor.binding[6]
                or log_veto.tail.path!=r.lease.reader.tail.path
                or log_veto.clock is not r.clock):
            raise ValueError('Camp supervision differs from original scope, bounds or input observer')
        self.runtime,self.declaration,self.monitor,self.gate=r,d,monitor,gate
        self.window,self.log_veto,self.current=expected_window,log_veto,check_current
        self.started_at,self.expires_at=started_at,expires_at
        self.clock,self.lock=r.clock,r.lock
        self.root,self.lease,self.reader=r.root,r.lease,r.lease.reader
        self.owner_input,self.topology=monitor.observer,monitor.topology
        self.generation=log_veto.cancel_generation
        self._context=(r,d,monitor,gate,expected_window,log_veto,check_current,
            self.clock,self.lock,self.root,self.lease,self.reader,self.owner_input)
        self._times=(started_at,expires_at,r.started,r.maximum_seconds)
        self._declaration=flat_record_state(d)
        self._bounds=flat_record_state(b);self._basis=r.root.bounds_basis
        self._owner=r.root.owner_binding;self._generation=self.generation
        self._topology=self.topology;self._monitor_binding=monitor.binding
        self._veto_tail=log_veto.tail
        self._policies=[];self._reserved=0.
        self.valid=True;self.reason='';self.last_at=started_at
        self._check()

    @property
    def reserved_hold(self):return self._reserved

    def cancel(self,reason):
        if self.valid:self.reason=str(reason)
        self.valid=False

    def _check(self):
        try:
            if not self.valid:raise ValueError(self.reason)
            self.current();r=self.runtime;began=r._check_scope()
            window=focused_game_identity(self.gate)
            self.current();finished=r._check_scope()
            m=self.monitor;d=self.declaration
            if (not self.valid or any(a is not b for a,b in zip(self._context,
                    (r,d,m,self.gate,self.window,self.log_veto,self.current,self.clock,self.lock,
                     self.root,self.lease,self.reader,self.owner_input)))
                    or (self.started_at,self.expires_at,r.started,r.maximum_seconds)!=self._times
                    or flat_record_state(d)!=self._declaration
                    or r.root is not self.root or r.lock is not self.lock or r.clock is not self.clock
                    or r.lease is not self.lease or self.lease.reader is not self.reader
                    or not self.lease.active or self.lease._tracker.lease is not self.lease
                    or r.owner_input is not self.owner_input or m.observer is not self.owner_input
                    or m.topology!=self._topology or self.topology!=self._topology
                    or not m.valid or m.closed or m.binding is not self._monitor_binding
                    or self.root.bounds_basis is not self._basis or self.root.owner_binding is not self._owner
                    or flat_record_state(self.root.bounds)!=self._bounds
                    or self.log_veto.tail.path!=self.reader.tail.path
                    or self.log_veto is not r.log_veto or self.log_veto.tail is not self._veto_tail
                    or self.log_veto.clock is not self.clock
                    or self.log_veto.cancel_generation!=self._generation or self.generation!=self._generation
                    or window!=self.window or not self.last_at<=began<=finished<=self.expires_at):
                raise ValueError('Camp supervision owner, deadline or observation binding changed')
            m.check_binding(self._monitor_binding)
            self.last_at=finished
            return finished
        except Exception as error:
            self.cancel(error);raise ValueError(self.reason) from error

    def policy(self,transaction):
        """Bind the next exact transaction without resetting time or budgets."""
        with self.lock:
            try:
                self._check();r=self.runtime;i=len(self._policies)
                if (type(transaction) is not CampProbeTransaction or r.phase!='collect_start'
                        or r.index!=i or i>=len(r.probes) or r.transaction is not transaction
                        or len(r.transactions)!=i+1 or r.transactions[-1] is not transaction
                        or transaction.phase!='new' or transaction.lock is not self.lock
                        or transaction.preparation is not r.preparation
                        or transaction.preparation.bounds is not self.root.bounds
                        or any(p.transaction is not r.transactions[n]
                            or p.transaction.phase!='continued' or p._authorization is None
                            or p.transaction.seal.ticket is not p._authorization.ticket
                            for n,p in enumerate(self._policies))):
                    raise ValueError('Camp policy must follow the original completed probe sequence')
                result=SupervisedCampProbePolicy(transaction,scope=self,index=i)
                self._policies.append(result)
                return result
            except Exception as error:
                self.cancel(error);raise

    def snapshot(self):
        return dict(kind='owner_supervised_camp_probes',valid=self.valid,reason=self.reason,
            declaration=asdict(self.declaration),started_at=self.started_at,expires_at=self.expires_at,
            reserved_maximum_hold=self._reserved,bound_probes=len(self._policies),
            independent_scene_verified=False,motion_bounds_verified=False,real_client_accepted=False)


class SupervisedCampProbePolicy(CampProbeInputPolicy):
    """One transaction; only the owning shared scope can bind its sequence slot."""
    def __init__(self,transaction,*,scope,index):
        super().__init__(transaction)
        if type(scope) is not SupervisedCampProbeScope or type(index) is not int:
            raise ValueError('Shared camp probe scope and exact sequence index required')
        self.scope,self.index=scope,index;self._context=(transaction,scope,index)
        self._scene=self._authorization=self._authorization_state=None

    def _check(self):
        s=self.scope;now=s._check();r=s.runtime;t=self.transaction;i=self.index
        if (any(a is not b for a,b in zip(self._context,(t,s,i)))
                or len(s._policies)!=i+1 or s._policies[i] is not self
                or r.phase!='pulse' or r.index!=i or r.transaction is not t or r.policy is not self
                or len(r.transactions)!=i+1 or r.transactions[i] is not t
                or t.preparation is not r.preparation or t.lock is not s.lock
                or t.preparation.lease is not s.lease or t.preparation.bounds is not s.root.bounds
                or t.preparation.bounds_basis is not s._basis
                or t.preparation.kind!=r.probes[i].key or t.phase not in ('new','proposed')):
            raise ValueError('Camp probe policy is not the current sequence transaction')
        t._assert_context()
        return now

    def check(self):
        s=self.scope
        with s.lock:
            try:
                began=self._check()
                before=s.owner_input.sample();log=s.log_veto.poll();after=s.owner_input.sample()
                finished=self._check()
                if (not 0<=finished-began<=.1
                        or not all(type(v) is OwnerInputObservation and v.clear_at(finished)
                            and v.topology_generation==s.topology for v in (before,after))
                        or not log.continuity_available or log.reason is not None
                        or log.cancel_generation!=s.generation
                        or not began<=before.started_at<=before.finished_at<=log.started_at
                            <=log.finished_at<=after.started_at<=after.finished_at<=finished):
                    raise ValueError('Camp probe physical activity or log observation veto')
                self._scene=(began,finished)
                return True
            except Exception as error:
                s.cancel(error);raise

    def _ticket(self,ticket):
        s=self.scope;now=self._check();t=self.transaction;p=s.runtime.probes[self.index]
        if (type(ticket) is not CampProbeTicket or t.phase!='proposed' or t.ticket is not ticket
                or ticket.kind!=p.key or ticket.movement_key!=p.key_code or ticket.requested_seconds!=p.seconds
                or ticket.maximum_actual_hold!=s.root.bounds.maximum_actual_hold
                or self._scene is None or not self._scene[0]<=self._scene[1]<=now<=self._scene[0]+.1):
            raise ValueError('Camp probe ticket or latest observation changed')
        return now

    def authorize(self,ticket):
        s=self.scope
        with s.lock:
            try:
                now=self._ticket(ticket)
                if (self._authorization is not None
                        or s._reserved+ticket.maximum_actual_hold>s.declaration.maximum_total_hold):
                    raise ValueError('Camp probe duplicate authorization or hold budget exhausted')
                expires=min(ticket.start.expires_at,ticket.proposed_at+.05,s.expires_at)
                if not ticket.proposed_at<=now<=expires:raise ValueError('Camp probe DOWN deadline expired')
                self._authorization=CampProbeAuthorization(ticket,now,expires,s.declaration.record_id)
                a=self._authorization
                self._authorization_state=(id(a),id(ticket),a.issued_at,a.expires_at,a.policy_record_id)
                s._reserved+=ticket.maximum_actual_hold
                return a
            except Exception as error:
                s.cancel(error);raise

    def still_authorized(self,authorization):
        s=self.scope
        with s.lock:
            try:
                if type(authorization) is not CampProbeAuthorization:
                    raise ValueError('Exact camp authorization required')
                self._ticket(authorization.ticket);a=authorization
                if (a is not self._authorization or
                        (id(a),id(a.ticket),a.issued_at,a.expires_at,a.policy_record_id)!=self._authorization_state):
                    raise ValueError('Camp probe authorization changed')
                # The sender refreshes check() first. DOWN expiry is not an UP
                # deadline: keep observing throughout .15-second turn probes.
                return True
            except Exception as error:
                s.cancel(error);raise
