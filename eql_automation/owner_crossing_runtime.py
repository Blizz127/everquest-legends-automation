"""Owner-started corridor adapter; never runs an ordinary route driver beside it."""
from .crossing_corridor import CrossingCorridorHandoff
from .g2_safety_provider import GameWindowIdentity
from .location_hotkey import send_location_hotkey
from .motion_collection import CommandReceipt,LocationRequest
from .route_step_sender import RouteStepScene,run_checked_corridor_step,_fd_identity
from .supervised_corridor import SupervisedCorridorDeclaration,SupervisedCrossingCorridorPolicy
from .supervised_route import scope_limits


class OwnerCrossingRuntime:
    def __init__(self,engine,pending,geometry,reference,*,clock,local_wall_clock):
        self.engine,self.pending,self.clock=engine,pending,clock
        self.sender,self.lease,self.observer=pending['sender'],pending['lease'],pending['observer']
        self.reader=self.lease.reader
        self.ui=self.sender.ui;self.fd=self.ui.fileno();self.fd_identity=_fd_identity(self.fd)
        self.hotkey=pending['binding']
        self.events=[]
        self._current()
        destination=pending['continuation']['destination']
        seconds,steps,distance,hold=scope_limits('zone_crossing_corridor')
        self.corridor=CrossingCorridorHandoff(geometry,pending['plan'].observer,reference,self.lease,
            destination.destination,release_controls=self._release,
            ready_for_location=lambda:clock()>=engine.zone_loading_until and engine.gate.controls_ready(),
            check_current=self._current,maximum_source_seconds=seconds,maximum_arrival_seconds=90.,
            local_wall_clock=local_wall_clock)
        declaration=SupervisedCorridorDeclaration(destination.expected_zone_line.crossing_id,
            geometry.ledger.runner.route.artifact_sha256,geometry.ledger.runner.calibration,
            geometry.bounds.record_id,True,seconds,steps,distance,hold,
            expected_zone_line_sha256=destination.expected_zone_line.sha256,destination=destination.destination)
        self.policy=SupervisedCrossingCorridorPolicy(geometry,arrival=self.corridor.arrival,
            declaration=declaration,gate=engine.gate,owner_input=self.observer,
            log_veto=self.corridor.arrival.veto,expected_log_path=engine.log_path(),
            expected_window=GameWindowIdentity(*pending['window']),topology_generation=pending['topology'],
            check_current=self._current)

    def _current(self):
        e,p=self.engine,self.pending
        e._trial_common_current(p)
        if (p.get('corridor_runtime') not in (None,self) or e.route_session_driver is not None
                or p.get('driver') is not None or p['lease'] is not self.lease
                or self.lease.reader is not self.reader or p['observer'] is not self.observer
                or p['binding'] is not self.hotkey or e.sender is not self.sender
                or self.sender.ui is not self.ui or self.ui.fileno()!=self.fd
                or _fd_identity(self.fd)!=self.fd_identity):
            raise ValueError('Exclusive crossing owner, sender, reader or input observer changed')
        self.lease.check()

    def check_current(self):
        self._current()
        self.corridor.arrival._check()

    def _release(self):
        # Cleanup must remain possible after focus/owner cancellation, but must
        # never release a replacement descriptor or a second operation's keys.
        if (self.sender.ui is not self.ui or self.ui.fileno()!=self.fd
                or _fd_identity(self.fd)!=self.fd_identity):
            raise ValueError('Original crossing sender unavailable for release')
        began=self.clock()
        for key in tuple(self.sender.held):self.sender.release(key)
        return CommandReceipt(began,self.clock())

    def cancel(self,reason):
        self.corridor.cancel(reason)

    def _request_location(self,request):
        e,p,c=self.engine,self.pending,self.corridor
        a=c.arrival
        collector=a.source_collector if a.source_collector is not None else a.collector
        if not isinstance(request,LocationRequest) or collector is None:
            raise ValueError('Owned stopped-position request required')
        def current():
            self.check_current();collector.check()
            active=a.source_collector if a.source_collector is not None else a.collector
            if (active is not collector or collector.pending is not request
                    or collector.phase!='requesting' or not p['busy']
                    or self.clock()<e.zone_loading_until
                    or p.get('corridor_runtime') is not self):
                raise ValueError('Crossing position request changed or client is loading')
        def pump():
            e.pump();e.autopilot_tick(self.clock())
        receipt=send_location_hotkey(self.sender,binding=self.hotkey,owner_input=self.observer,
            lock=c.ledger.lock,clock=self.clock,expires_at=request.expires_at,ensure_current=current,
            cancel=lambda reason:e._cancel_trial(reason),pump=pump,record_event=self.events.append)
        return CommandReceipt(receipt.pulse.down_started_at,receipt.released_at)

    def tick(self):
        e,p,c=self.engine,self.pending,self.corridor
        self.check_current()
        if p['busy']:return  # Nested input pumps check scope without consuming the reader.
        p['busy']=True
        try:
            action=c.tick()
            if isinstance(action,LocationRequest):
                c.command_sent(action,self._request_location(action))
            elif c.phase=='ready':
                def scene():return RouteStepScene(c.reference,self.policy.observe(c.reference))
                def pump():
                    e.pump();e.autopilot_tick(self.clock())
                result=run_checked_corridor_step(self.sender,c,policy=self.policy,
                    scene_provider=scene,command_state_clear=lambda:e._route_idle() and not e.cancelled
                        and e.jobs.empty(),pump=pump)
                self.events.append(dict(kind='corridor_pulse',**result))
        except BaseException as error:
            self.cancel(str(error));raise
        finally:p['busy']=False

    def snapshot(self):
        return dict(self.corridor.snapshot(),owner_action_wired=True,executor_events=list(self.events),
                    ordinary_route_driver_used=False)
