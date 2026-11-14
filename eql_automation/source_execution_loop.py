"""Shared source execution, without trial or camp admission assumptions."""
from dataclasses import asdict

from .motion_collection import LocationRequest
from .source_transfer import SourceTransferController
from .source_walk_driver import SourceStepBoundary, SourceWalkFinished
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
            self.ledger.cancel(reason)

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
            floor_proof_sha256=outcome.floor_proof_sha256,
            raw_seq=self.observations[-1].raw_fix.log_line_seq,
            real_client_accepted=False))
        if kind == 'settling':
            self._new_pair()
            return
        if kind in ('approach', 'landed'):
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
                self._collect()
                return
            action = self.transfer.next_command() if self.transfer is not None else self.driver.next_action()
            if isinstance(action, SourceStepBoundary):
                self.transfer = SourceTransferController(self.driver, action)
                self.policy.bind_transfer(self.transfer)
                action = self.transfer.next_command()
            elif isinstance(action, SourceWalkFinished):
                self.completed_arrival = action
                self.phase = 'complete'
                return

            self.seal = self._send_movement(action)
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
        return dict(phase=self.phase, reason=self.reason, itinerary_sha256=self.driver.plan.sha256,
            cell_index=self.driver.index, completed_movements=self.ledger.steps,
            transfer_phase=None if self.transfer is None else self.transfer.phase,
            partial_movements=0 if self.transfer is None else self.transfer.local_steps,
            incomplete_pair=None if self.collector is None else self.collector.snapshot(),
            stopped_pairs=list(self.pairs), executor_events=list(self.events), policy=self.policy.snapshot(),
            ordinary_route_driver_used=False, real_client_accepted=False)
