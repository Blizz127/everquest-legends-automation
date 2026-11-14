"""Checked source pulses, provisional source pairs, and one expected arrival.

This controller owns no device. The explicit corridor sender executes pulses;
the owner executes only its returned location requests. All raw positions and
boundaries use the same arrival lease, never an ordinary route driver in parallel.
"""
from dataclasses import asdict
from datetime import datetime

from .fixed_route_follower import finite
from .ground_observer import RouteGroundObserver
from .provisional_floor_commit import ProvisionalRouteFloorCommit
from .route_floor_commit import _chain_snapshot
from .route_geometry import RouteGeometryPreparer
from .uinput_watchdog import PulseReceipt
from .zone_arrival import ZoneArrivalHandoff
from .zone_line import ExpectedZoneLine


class CrossingCorridorHandoff:
    def __init__(self,geometry,observer,reference,lease,destination,*,release_controls,
                 ready_for_location,check_current,maximum_source_seconds,
                 maximum_arrival_seconds=90.,local_wall_clock=datetime.now):
        if (type(geometry) is not RouteGeometryPreparer
                or type(geometry.ledger) is not ProvisionalRouteFloorCommit
                or type(geometry.expected_zone_line) is not ExpectedZoneLine
                or not isinstance(observer,RouteGroundObserver)
                or observer.geometry is not geometry.ledger.runner.geometry_evidence
                or observer.ground is not geometry.ground):
            raise ValueError('Exact provisional ledger, observed ground and crossing geometry required')
        self.geometry,self.ledger,self.observer=geometry,geometry.ledger,observer
        self.runner,self.clock=self.ledger.runner,self.ledger.clock
        self.line,self.route=geometry.expected_zone_line,self.runner.route
        self.reference=reference
        self.chain_state=_chain_snapshot(self.ledger.chain)
        self.mode,self.generation=self.runner.mode_reader(),self.runner.generation
        self.phase,self.reason='ready',''
        self.ticket=self.receipt=self.seal=self.policy=None
        self.touches_line=False;self.quiet_until=None;self.steps=[]
        self.check_current=check_current
        if (self.mode!='measurement' or self.runner.phase!='ready'
                or reference.mesh_projection.package_xyz!=(self.runner.pose.x,self.runner.pose.y,self.runner.pose.z)
                or (lease.reader.zone_id,lease.reader.zone_display_name,
                    lease.reader.tail.epoch,lease.reader.zone_generation)!=self.runner.binding):
            raise ValueError('Current stopped source, measurement mode and exact lease required')
        def release():
            receipt=release_controls()
            self.ledger.cancel('Source corridor released on loading or stop')
            if self.arrival.loading is not None and (self.ticket is None or not self.touches_line):
                raise ValueError('Loading was not preceded by a checked footprint at the expected line')
            return receipt
        self.arrival=ZoneArrivalHandoff(lease,destination,release_controls=release,
            ready_for_location=lambda:self.phase=='await_arrival' and ready_for_location(),
            check_current=self._current,clock=self.clock,local_wall_clock=local_wall_clock,
            maximum_seconds=maximum_arrival_seconds,maximum_source_seconds=maximum_source_seconds,
            cancel_generation=self.generation)

    def _current(self):
        self.check_current()
        mode=self.runner.mode_reader();generation=self.runner.generation_reader()
        self._bound_state(mode,generation)
        return mode,generation

    def _bound_state(self,mode,generation):
        """Recheck cancellation/bindings without invoking external callbacks."""
        p=self.policy
        if getattr(getattr(self,'arrival',None),'phase',None)=='stopped':
            raise ValueError('Corridor arrival failed or was cancelled')
        if p is not None and (p._cancelled is not None or p.arrival is not self.arrival
                or p.declaration is not p._declaration or p.geometry is not self.geometry
                or p.ledger is not self.ledger or p.bounds is not self.geometry.bounds):
            raise ValueError('Corridor policy cancelled or changed')
        if (self.phase=='stopped' or self.geometry.ledger is not self.ledger
                or self.geometry.expected_zone_line is not self.line
                or self.runner.route is not self.route or self.observer.geometry is not self.runner.geometry_evidence
                or mode!=self.mode or generation!=self.generation
                or _chain_snapshot(self.ledger.chain)!=self.chain_state):
            raise ValueError('Corridor owner, mode, route or source floor changed')

    def start(self,policy):
        from .supervised_corridor import SupervisedCrossingCorridorPolicy
        with self.ledger.lock:
            self._current()
            if (self.phase!='ready' or self.runner.phase!='ready'
                    or type(policy) is not SupervisedCrossingCorridorPolicy
                    or policy.geometry is not self.geometry or policy.arrival is not self.arrival
                    or (self.policy is not None and self.policy is not policy)
                    or self.seal is not None or self.arrival.source_collector is not None
                    or self.arrival.source_result is not None):
                raise ValueError('The same ready corridor policy is required for every pulse')
            self.policy=policy;self._current()
            self.ticket=self.receipt=None;self.touches_line=False
            self.phase='pulsing'

    def selected(self,ticket):
        self._current()
        if self.phase!='pulsing' or self.ticket is not None:
            raise ValueError('Corridor pulse selection is one-use')
        self.ledger.check_pending(ticket)
        record=self.geometry.record_for(ticket)
        if record.expected_zone_line is not self.line:
            raise ValueError('Selected footprint belongs to another zone line')
        self.ticket=ticket
        self.touches_line=any(self.line.allows_region(region,labels)
            for region,labels in record.bsp.traversal.labelled_regions)

    def poll_loading(self):
        self._current()
        if self.phase!='pulsing':raise ValueError('No source corridor pulse is active')
        action=self.arrival.tick()
        if action is not None:raise ValueError('Position command requested before source release')
        self._current()
        return self.arrival.loading is not None

    def seal_released(self,receipt):
        """Called by the checked sender after final UP and before its cleanup."""
        with self.ledger.lock:
            self._current()
            if self.phase!='pulsing' or self.ticket is None or self.arrival.loading is not None:
                raise ValueError('Only an elapsed source pulse can be sealed')
            seal=self.ledger.seal_release(self.ticket,receipt)
            self._current()
            if self.phase!='pulsing':raise ValueError('Corridor cancelled during receipt seal')
            self.seal=seal;self.phase='released'

    def released(self,receipt):
        with self.ledger.lock:
            self._current()
            if (self.phase not in ('pulsing','released') or self.ticket is None
                    or not isinstance(receipt,PulseReceipt)):
                raise ValueError('Actual selected corridor receipt required after cleanup')
            p=self.ticket.preparation
            stamps=(receipt.down_started_at,receipt.down_completed_at,receipt.up_started_at,receipt.up_completed_at)
            now=self.clock();self._current()
            if (receipt.key_code!=p.movement_key or receipt.requested_seconds!=p.requested_seconds
                    or receipt.completion not in ('elapsed','interrupted')
                    or not all(finite(v) for v in stamps)
                    or not self.ticket.staged_at<=stamps[0]<=stamps[1]<=stamps[2]<=stamps[3]<=now
                    or stamps[0]>p.proposal.at+.05 or now-stamps[3]>.3
                    or not 0<receipt.maximum_held_seconds<=p.maximum_actual_hold):
                raise ValueError('Corridor receipt differs or exceeded its original timing bounds')
            mode,generation=self._current()
            finished=self.clock()
            self._bound_state(mode,generation)
            if (not finite(finished) or not now<=finished<=stamps[3]+.3
                    or self.phase not in ('pulsing','released')):
                raise ValueError('Corridor receipt expired or cancelled during release completion')
            if self.arrival.loading is None:
                if self.seal is None or self.seal.receipt is not receipt or self.phase!='released':
                    raise ValueError('Elapsed corridor receipt was not sealed by the checked sender')
                self.phase='settling'
                self.quiet_until=receipt.up_completed_at+(2.5 if self.touches_line else .12)
            else:
                if not self.touches_line:raise ValueError('Uncorrelated source loading')
                self.phase='await_arrival';self.seal=None
            self.receipt=receipt
            return dict(receipt=asdict(receipt),outcome=self.phase,source_floor_committed=False,
                expected_zone_line_sha256=self.line.sha256,real_client_accepted=False)

    def _observe_source(self,raw):
        self._current()
        if self.phase!='source_positions' or self.seal is None:
            raise ValueError('No provisional source observation is active')
        fork=self.ledger.floor_for_observation(self.seal)
        value=self.observer.observe(raw,route=self.route,segment_index=self.runner.index,
            height_calibration=self.runner.height_calibration,
            motion_calibration_record_id=self.runner.calibration,now=self.clock(),
            floor_chain=fork,mode=self.mode)
        self._current()
        return value

    def tick(self):
        try:
            with self.ledger.lock:
                self._current()
                if self.phase not in ('ready','settling','source_positions','await_arrival','complete'):
                    raise ValueError('Corridor sender must finish cleanup before ticking')
                action=self.arrival.tick();self._current()
                if self.arrival.loading is not None:
                    self.seal=None
                    self.phase='complete' if self.arrival.phase=='complete' else 'await_arrival'
                    return action
                if self.phase=='settling' and self.clock()>=self.quiet_until:
                    self._current()
                    self.arrival.start_source_pair(released_at=self.receipt.up_completed_at,
                                                  observe_fix=self._observe_source)
                    self.phase='source_positions'
                    return self.arrival.tick()
                if self.phase=='source_positions' and self.arrival.source_result is not None:
                    pair=self.arrival.take_source_pair();self._current()
                    if pair is None:
                        self.seal=None;self.phase='await_arrival';return None
                    step=self.ledger.resolve_source(self.seal,*pair.observations)
                    self.chain_state=_chain_snapshot(self.ledger.chain)
                    self.reference=pair.observations[-1]
                    self.steps.append(dict(receipt=asdict(self.receipt),floor_proof_sha256=step.proof_sha256,
                                          positions=pair.record))
                    self.seal=None
                    if self.runner.phase!='ready':
                        raise ValueError('Source corridor ended without expected loading')
                    self.phase='ready';self._current()
                return action
        except BaseException as error:
            self.cancel(str(error));raise

    def command_sent(self,request,receipt):
        try:
            with self.ledger.lock:
                self._current()
                if self.phase not in ('source_positions','await_arrival'):
                    raise ValueError('Corridor has no active stopped-position command')
                self.arrival.command_sent(request,receipt);self._current()
        except BaseException as error:
            self.cancel(str(error));raise

    def cancel(self,reason):
        with self.ledger.lock:
            if self.phase=='stopped':return
            self.phase,self.reason='stopped',str(reason)
            self.ledger.cancel(reason);self.seal=None
            self.arrival.cancel(reason)

    def snapshot(self):
        return dict(outcome=self.phase,reason=self.reason,source_steps=list(self.steps),
            arrival=self.arrival.snapshot(),policy=None if self.policy is None else self.policy.snapshot(),
            source_floor_provisional=self.seal is not None,source_navigation_state_reused=False,
            owner_action_wired=False,real_client_accepted=False)
