"""Shared source execution, without trial or camp admission assumptions."""
from dataclasses import asdict

from .motion_collection import LocationRequest
from .source_transfer import SourceTransferController
from .source_walk_driver import SourceStepBoundary,SourceStairBoundary,SourceContactBoundary,SourceWalkFinished
from .source_stair_preflight import SourceStairPreflight
from .source_stair_controller import SourceStairController
from .source_contact_preflight import SourceContactPreflight
from .source_contact_controller import SourceContactController
from .stopped_location_pair import StoppedLocationPair


class SourceExecutionLoop:
    """Adapters supply owner scope, busy state, and exact sender operations."""
    @property
    def active(self):
        return self.transfer if self.transfer is not None else self.ledger

    def cancel(self, reason):
        with self.ledger.lock:
            self.phase, self.reason = 'stopped', str(reason)
            self.completed_arrival = None
            if self.collector is not None:
                self.collector.cancel(reason)
            if self.transfer is not None:
                self.transfer.cancel(reason)
            if self.stair_preflight is not None:self.stair_preflight.cancel(reason)
            if self.contact_preflight is not None:self.contact_preflight.cancel(reason)
            self.ledger.cancel(reason)

    @property
    def pending_preflight(self):
        return self.contact_preflight if self.contact_preflight is not None else self.stair_preflight

    def _contact_boundary_snapshot(self):
        d,b=self.driver,self.contact_boundary
        if b is None:return None
        return (id(d),id(d.plan),d.plan.payload,d.index,id(d._boundary),id(b),tuple(vars(b).items()),
            id(d.targets),id(d._contacts),d._contacts is d._contact_hints,
            tuple(vars(d._contacts[b.cell_index]).items()),
            tuple(tuple(vars(d.targets[i]).items()) for i in (*b.approach_cell_indices,b.cell_index)),
            None if d._stair_connector is None else tuple(vars(d._stair_connector).items()))

    def check_contact_boundary(self):
        if self._contact_driver_state is not None and self._contact_boundary_snapshot()!=self._contact_driver_state:
            raise ValueError('Contact itinerary boundary changed during execution')

    def _begin_contact(self,boundary):
        hint=self.driver.contact_hint(boundary)
        with self.ledger.lock:
            self.check_current()
            self.contact_boundary=boundary
            self._contact_driver_state=self._contact_boundary_snapshot()
            self.contact_preflight=SourceContactPreflight(self.ledger,policy=self.policy,hint=hint,
                released_at=self.last_movement_release)
        pre=self.contact_preflight
        pre.prepare()
        collector=StoppedLocationPair(self.lease,released_at=self.last_movement_release,
            check_current=self.check_current,clock=self.clock,local_wall_clock=self.wall)
        with self.ledger.lock:
            self.check_current();pre.check();self.check_contact_boundary()
            if self.contact_preflight is not pre or self.contact_boundary is not boundary:
                collector.cancel('Contact preflight handoff changed')
                raise ValueError('Contact preflight handoff changed')
            self.collector=collector;self.observations=[];self.phase='contact_start'

    def _collect_contact_start(self):
        pre,collector=self.contact_preflight,self.collector
        pre.check();self.check_contact_boundary();action=collector.tick()
        fixes=tuple(raw for raw in (collector.first,collector.second) if raw is not None)
        if len(fixes)!=len(self.observations):
            if len(fixes)!=len(self.observations)+1:raise ValueError('Skipped contact start reply')
            self.observations.append(pre.observe_reply(fixes[-1]))
        if isinstance(action,LocationRequest):collector.command_sent(action,self._request_location(action))
        if collector.phase!='complete':return
        with self.ledger.lock:
            self.check_current();pre.check();self.check_contact_boundary()
            if self.contact_preflight is not pre or self.collector is not collector or self.phase!='contact_start':
                raise ValueError('Contact start collection changed')
            start=pre.bind_start(*self.observations)
            self.transfer=SourceContactController.from_preflight(pre,start)
            self.check_contact_boundary()
            if self.contact_preflight is not pre or self.collector is not collector or self.phase!='contact_start':
                raise ValueError('Contact ownership changed while constructing its controller')
            self.pairs.append(collector.snapshot())
            self.events.append(dict(kind='source_contact_start',cache_sha256=pre.cache.sha256,
                raw_seq=start.second.raw_fix.log_line_seq,real_client_accepted=False))
            self.contact_preflight=self.collector=None;self.observations=[];self.phase='ready'

    def _begin_stair(self,boundary):
        hint=self.driver.stair_hint(boundary)
        with self.ledger.lock:
            self.check_current()
            self.stair_boundary=boundary
            self.stair_preflight=SourceStairPreflight(self.ledger,policy=self.policy,hint=hint,
                released_at=self.last_movement_release)
        pre=self.stair_preflight
        pre.prepare()  # Geometry does not hold the stop lock or send input.
        collector=StoppedLocationPair(self.lease,released_at=self.last_movement_release,
            check_current=self.check_current,clock=self.clock,local_wall_clock=self.wall)
        with self.ledger.lock:
            self.check_current();pre.check()
            if self.stair_preflight is not pre or self.stair_boundary is not boundary:
                collector.cancel('Stair preflight handoff changed')
                raise ValueError('Stair preflight handoff changed')
            self.collector=collector;self.observations=[];self.phase='stair_start'

    def _collect_stair_start(self):
        pre,collector=self.stair_preflight,self.collector
        pre.check();action=collector.tick()
        fixes=tuple(raw for raw in (collector.first,collector.second) if raw is not None)
        if len(fixes)!=len(self.observations):
            if len(fixes)!=len(self.observations)+1:raise ValueError('Skipped stair start reply')
            self.observations.append(pre.observe_reply(fixes[-1]))
        if isinstance(action,LocationRequest):
            collector.command_sent(action,self._request_location(action))
        if collector.phase!='complete':return
        with self.ledger.lock:
            self.check_current();pre.check()
            if self.stair_preflight is not pre or self.collector is not collector or self.phase!='stair_start':
                raise ValueError('Stair start collection changed')
            start=pre.bind_start(*self.observations)
            controller=SourceStairController.from_preflight(pre,start)
            self.transfer=controller  # Constructor has already bound the same policy.
            self.pairs.append(collector.snapshot())
            self.events.append(dict(kind='source_stair_start',cache_sha256=pre.cache.sha256,
                raw_seq=start.second.raw_fix.log_line_seq,real_client_accepted=False))
            self.stair_preflight=self.collector=None;self.observations=[];self.phase='ready'

    def _new_pair(self):
        # Settling retains the same release/deadline; it never buys another
        # movement or renews the transfer's ten-second observation window.
        active, seal, previous = self.active, self.seal, self.collector
        collector = StoppedLocationPair(self.lease,
            released_at=seal.receipt.up_completed_at, check_current=self.check_current,
            clock=self.clock, local_wall_clock=self.wall)
        with self.ledger.lock:
            self.check_current()
            active._check_seal(seal)
            if (self.phase == 'stopped' or self.active is not active
                    or self.seal is not seal or self.collector is not previous):
                collector.cancel('Source pair creation cancelled')
                raise ValueError('Source pair creation cancelled')
            self.collector = collector
            self.observations = []
            self.phase = 'settling' if active.phase == 'settling' else 'positions'

    def _collect(self):
        collector, active, seal = self.collector, self.active, self.seal
        active._check_seal(seal)
        action = collector.tick()
        fixes = tuple(raw for raw in (collector.first, collector.second) if raw is not None)
        if len(fixes) != len(self.observations):
            if len(fixes) != len(self.observations)+1:
                raise ValueError('Source route skipped an owned position reply')
            self.observations.append(active.observe_reply(seal, fixes[-1]))
        if isinstance(action, LocationRequest):
            collector.command_sent(action, self._request_location(action))
        if collector.phase != 'complete':
            return
        outcome = active.acknowledge_stopped(seal, *self.observations)
        self.pairs.append(collector.snapshot())
        kind = outcome.kind if self.transfer is not None else 'walk'
        self.events.append(dict(kind='source_acknowledgment', outcome=kind,
            **(dict(contact_coverage_sha256=outcome.window_sha256) if type(active) is SourceContactController
               else dict(floor_proof_sha256=outcome.floor_proof_sha256)),
            raw_seq=self.observations[-1].raw_fix.log_line_seq,
            real_client_accepted=False))
        if kind == 'settling':
            self._new_pair()
            return
        if type(active) is SourceContactController and kind=='arrived':
            self.check_contact_boundary();active.validate_arrival(outcome.arrival)
            self.check_contact_boundary()
            if (self.active is not active or self.collector is not collector or self.seal is not seal
                    or self.phase not in ('positions','settling') or active.arrival is not outcome.arrival):
                raise ValueError('Contact completion changed during final observation')
            self.completed_arrival=outcome.arrival
            self.collector=self.seal=None;self.observations=[];self.phase='complete'
            return
        if kind in ('approach', 'landed'):
            if type(self.transfer) is SourceStairController:
                self.driver.finish_stair(self.stair_boundary,self.transfer,outcome)
                self.stair_boundary=None
            self.policy.finish_transfer(self.transfer)
            self.transfer = None
        self.collector = self.seal = None
        self.observations = []
        self.phase = 'ready'

    def tick(self):
        if self.phase == 'complete':
            return
        self.check_current()
        if self._work_busy():
            return  # Nested pumps check scope without consuming the reader.
        self._set_work_busy(True)
        try:
            self.active._check()
            if self.collector is not None:
                if self.phase=='stair_start':self._collect_stair_start()
                elif self.phase=='contact_start':self._collect_contact_start()
                else:self._collect()
                return
            action = self.transfer.next_command() if self.transfer is not None else self.driver.next_action()
            if type(action) is SourceContactBoundary:
                self._begin_contact(action)
                return
            if type(action) is SourceStairBoundary:
                self._begin_stair(action)
                return
            if type(action) is SourceStepBoundary:
                self.transfer = SourceTransferController(self.driver, action)
                self.policy.bind_transfer(self.transfer)
                action = self.transfer.next_command()
            elif isinstance(action, SourceWalkFinished):
                self.completed_arrival = action
                self.phase = 'complete'
                return

            self.seal = self._send_movement(action)
            self.last_movement_release=self.seal.receipt.up_completed_at
            self.events.append(dict(kind='source_pulse', cell_index=action.cell_index,
                movement=action.kind, receipt=asdict(self.seal.receipt),
                geometry_sha256=self.seal.ticket.geometry.sha256, real_client_accepted=False))
            self._new_pair()
        except BaseException as error:
            self.cancel(str(error))
            raise
        finally:
            self._set_work_busy(False)

    def snapshot(self):
        contact_complete=self.phase=='complete' and type(self.transfer) is SourceContactController
        contact_steps=self.transfer.local_steps if contact_complete else 0
        return dict(phase=self.phase, reason=self.reason, itinerary_sha256=self.driver.plan.sha256,
            cell_index=self.driver.index, completed_movements=self.ledger.steps+contact_steps,
            transfer_phase=None if self.transfer is None else self.transfer.phase,
            partial_movements=0 if self.transfer is None or contact_complete else self.transfer.local_steps,
            stair_preflight_phase=None if self.stair_preflight is None else self.stair_preflight.phase,
            contact_preflight_phase=None if self.contact_preflight is None else self.contact_preflight.phase,
            incomplete_pair=None if self.collector is None else self.collector.snapshot(),
            stopped_pairs=list(self.pairs), executor_events=list(self.events), policy=self.policy.snapshot(),
            ordinary_route_driver_used=False, real_client_accepted=False)
