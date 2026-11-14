"""Final checked pulse followed by exclusive loading/arrival observation.

The source floor fork is NEVER committed, even if the pulse fully elapses.
Destination positions start a new planner; no source heading/height carries.
This controller creates no device, starts no owner job, and sends no location
command itself. Its caller executes returned requests through checked input.
"""
from dataclasses import asdict,dataclass
from datetime import datetime

from .fixed_route_follower import finite
from .route_floor_commit import _chain_snapshot
from .route_geometry import RouteGeometryPreparer
from .uinput_watchdog import PulseReceipt
from .zone_arrival import ZoneArrivalHandoff
from .zone_line import ExpectedZoneLine


@dataclass(frozen=True)
class CrossingPulseResult:
    receipt: PulseReceipt
    expected_zone_line_sha256: str
    destination: str
    loading_observed: bool
    source_floor_committed: bool = False
    real_client_accepted: bool = False


class CrossingPulseHandoff:
    def __init__(self,geometry,lease,destination,*,release_controls,ready_for_location,
                 check_current,local_wall_clock=datetime.now,maximum_seconds=90.):
        if (type(geometry) is not RouteGeometryPreparer
                or not isinstance(geometry.expected_zone_line,ExpectedZoneLine)):
            raise ValueError('Crossing requires the exact complete geometry preparer')
        self.geometry,self.ledger=geometry,geometry.ledger
        self.line=geometry.expected_zone_line
        self.runner,self.clock=self.ledger.runner,self.ledger.clock
        self.chain_state=_chain_snapshot(self.ledger.chain)
        self.mode,self.generation=self.runner.mode_reader(),self.runner.generation
        self.route=self.runner.route
        self.phase,self.reason='prepared',''
        self.ticket=self.receipt=None
        self.policy=None
        self.finished_at=None
        self.check_current=check_current
        if (self.mode!='measurement' or self.runner.phase!='ready'
                or (lease.reader.zone_id,lease.reader.zone_display_name,
                    lease.reader.tail.epoch,lease.reader.zone_generation)!=self.runner.binding
                or self.line.zone!=self.route.zone):
            raise ValueError('Crossing requires a current stopped source route and exclusive source lease')
        self.arrival=ZoneArrivalHandoff(lease,destination,release_controls=release_controls,
            ready_for_location=lambda:self.phase=='await_arrival' and ready_for_location(),
            check_current=self._current,clock=self.clock,local_wall_clock=local_wall_clock,
            maximum_seconds=maximum_seconds,cancel_generation=self.generation)

    def _current(self):
        self.check_current()
        mode=self.runner.mode_reader()
        generation=self.runner.generation_reader()
        policy=self.policy
        if policy is not None and (
                policy._cancelled is not None or policy.declaration is not policy._declaration
                or policy.geometry is not self.geometry or policy.ledger is not self.ledger
                or policy.bounds is not self.geometry.bounds or policy.log_veto is not self.arrival.veto):
            raise ValueError('Crossing policy cancelled or changed')
        if (self.phase=='stopped' or self.geometry.ledger is not self.ledger
                or self.geometry.expected_zone_line is not self.line
                or self.runner.route is not self.route
                or mode!=self.mode or generation!=self.generation
                or _chain_snapshot(self.ledger.chain)!=self.chain_state):
            raise ValueError('Crossing cancelled or source/mode/floor binding changed')

    def start(self,policy):
        with self.ledger.lock:
            self._start(policy)

    def _start(self,policy):
        from .supervised_crossing import SupervisedCrossingPolicy
        self._current()
        if (self.phase!='prepared' or type(policy) is not SupervisedCrossingPolicy
                or policy.geometry is not self.geometry or policy.log_veto is not self.arrival.veto
                or policy.declaration.destination!=self.arrival.destination):
            raise ValueError('Exact prepared crossing and arrival policy required')
        self.policy=policy
        self._current()
        self.phase='pulsing'

    def selected(self,ticket):
        self._current()
        if self.phase!='pulsing' or self.ticket is not None:
            raise ValueError('Crossing pulse selection is one-use')
        self.ledger.check_pending(ticket)
        self.ticket=ticket

    def poll_loading(self):
        self._current()
        if self.phase!='pulsing':raise ValueError('No crossing pulse is active')
        action=self.arrival.tick()
        if action is not None:raise ValueError('Location request before crossing release')
        self._current()
        return self.arrival.loading is not None

    def released(self,receipt):
        with self.ledger.lock:
            return self._released(receipt)

    def _released(self,receipt):
        self._current()
        if self.phase!='pulsing' or self.ticket is None or not isinstance(receipt,PulseReceipt):
            raise ValueError('Actual selected crossing pulse receipt required')
        p=self.ticket.preparation
        self.poll_loading()
        now=self.clock()
        stamps=(receipt.down_started_at,receipt.down_completed_at,receipt.up_started_at,receipt.up_completed_at)
        if (receipt.key_code!=103 or receipt.requested_seconds!=p.requested_seconds
                or receipt.completion not in ('elapsed','interrupted')
                or not all(finite(t) for t in stamps)
                or not 0<receipt.maximum_held_seconds<=p.maximum_actual_hold
                or not self.ticket.staged_at<=stamps[0]<=stamps[1]<=stamps[2]<=stamps[3]<=now
                or receipt.down_started_at>p.proposal.at+.05
                or now-receipt.up_completed_at>.3
                or (receipt.completion=='interrupted' and self.arrival.loading is None)):
            raise ValueError('Crossing receipt differs, exceeds bounds or lacks expected loading')
        finished=self.clock()
        self._current()  # Clock and scope callbacks can synchronously cancel.
        if self.phase!='pulsing' or not finite(finished) or not now<=finished<=receipt.up_completed_at+.3:
            raise ValueError('Crossing changed or expired during release completion')
        self.receipt=receipt;self.finished_at=finished
        self.phase='await_arrival'
        return CrossingPulseResult(receipt,self.line.sha256,self.arrival.destination,
                                   self.arrival.loading is not None)

    def tick(self):
        try:
            self._current()
            if self.phase not in ('await_arrival','complete'):
                raise ValueError('Crossing release is required before arrival work')
            action=self.arrival.tick()
            self._current()
            if ((self.arrival.phase=='await_loading' and self.clock()>self.finished_at+2.5)
                    or (self.arrival.loading is not None
                        and self.arrival.loading.received_monotonic>self.finished_at+2.5)):
                raise ValueError('No loading observed after the final crossing pulse')
            if self.arrival.phase=='complete':
                with self.ledger.lock:
                    self._current()
                    self.phase='complete'
            return action
        except BaseException as error:
            self.cancel(str(error));raise

    def command_sent(self,request,receipt):
        try:
            self._current()
            if self.phase!='await_arrival':raise ValueError('Arrival is not collecting positions')
            self.arrival.command_sent(request,receipt);self._current()
        except BaseException as error:
            self.cancel(str(error));raise

    def cancel(self,reason):
        with self.ledger.lock:
            if self.phase=='stopped':return
            self.phase,self.reason='stopped',str(reason)
            self.ledger.cancel(str(reason))
            self.arrival.cancel(str(reason))

    def snapshot(self):
        return dict(outcome=self.phase,reason=self.reason,expected_zone_line=self.line.record(),
            receipt=None if self.receipt is None else asdict(self.receipt),
            arrival=self.arrival.snapshot(),source_floor_committed=False,
            source_navigation_state_reused=False,real_client_accepted=False)
