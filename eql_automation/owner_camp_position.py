"""Collect one fresh post-recovery position pair on the reached camp floor.

This uses the existing sender, owner-tested location hotbutton and exclusive
reader. It sends no movement, target, chat or combat command. A successful
record remains evidence; later relocation must acquire fresh observations.
"""
import json
import time
from types import SimpleNamespace

from .camp_stopped_height import measure_camp_stopped_height
from .ground_binding import finite
from .location_hotkey import HOTKEY_CODES, OwnerLocationHotkey, send_location_hotkey
from .motion_collection import CommandReceipt, LocationRequest
from .owner_navigation_preflight import settings_identity, window_identity
from .stopped_location_pair import StoppedLocationPair


def make_camp_position_engine(base_engine,*,clock=time.monotonic):
    class CampPositionEngine(base_engine):
        def __init__(self,*args,**kwargs):
            self.camp_position=None
            self.camp_position_last_result=None
            super().__init__(*args,**kwargs)

        def _navigation_busy(self):
            return self.camp_position is not None or super()._navigation_busy()

        def _camp_location_lease(self):
            p=self.camp_position
            if (p is not None and not p.cancelled and self.journey is p.journey
                    and self.camp_session is p.camp and self.live_zone_tracker is p.tracker
                    and p.lease.active and p.tracker.lease is p.lease):
                return p.lease
            return None

        def _camp_position_current(self,p):
            if self.camp_position is not p or p.cancelled:
                raise ValueError('Camp position collection ended')
            p.lease.check();p.hotkey.check()
            current=self._camp_current()
            window=window_identity(self.gate,require_focus=True)
            now=clock()
            if (not current or self.camp_position is not p or p.cancelled
                    or self.journey is not p.journey or p.journey.phase!='camp'
                    or self.camp_session is not p.camp or p.camp.phase!='position_check'
                    or not p.camp.running or self.cancelled or self.stopping
                    or self.cancel_generation!=p.generation or settings_identity(self.settings)!=p.settings
                    or self.live_zone_tracker is not p.tracker or p.tracker.reader is not p.reader
                    or p.tracker.lease is not p.lease or not p.lease.active
                    or self.sender is not p.sender or self.sender.ui is not p.ui or self.gate is not p.gate
                    or window!=p.window or self.active or self.target_ready or self.preparing
                    or self._camp_command is not None or self.sender.unfinished or self.sender.dismissed
                    or self.sender.held-({HOTKEY_CODES[p.hotkey.key_name]} if p.sending else set())
                    or not self.jobs.empty() or p.journey.arrival_floor is not p.floor or not p.floor.valid
                    or p.journey.location_binding is not p.hotkey or p.journey.camp_motion is not p.monitor
                    or not p.monitor.valid or p.monitor.closed
                    or p.camp.recovery is not p.recovery or p.recovery.phase!='recovered'
                    or p.recovery.last_stand_completed_at!=p.released_at
                    or not finite(now) or not p.started<=now<=p.started+8
                    or now<max(self.command_pause_until,self.rotation.busy_until)):
                raise ValueError('Camp position owner, recovery or input scope changed')
            return p.owner_binding

        def _camp_location_input_permitted(self):
            p=self.camp_position
            if (p is None or not p.busy or not p.sending or p.request is None
                    or p.collector is None or p.collector.phase!='requesting'
                    or p.collector.pending is not p.request):return False
            try:
                self._camp_position_current(p)
                return (self.camp_position is p and not p.cancelled and p.sending
                    and p.collector.phase=='requesting' and p.collector.pending is p.request)
            except (OSError,ValueError,RuntimeError):return False

        def _camp_recovery_complete(self,camp,now):
            j=self.journey
            if j is None or j.phase!='camp' or j.height_check_done or camp.kills==0:
                return super()._camp_recovery_complete(camp,now)
            lease=None
            try:
                if (not self._camp_current() or self.camp_session is not camp
                        or self.camp_position is not None or self.journey is not j
                        or camp.phase!='recovery' or camp.recovery.phase!='recovered'
                        or j.arrival_floor is None or j.camp_motion is None
                        or not isinstance(j.location_binding,OwnerLocationHotkey)
                        or not finite(camp.recovery.last_stand_completed_at)
                        or self.sender.held or self.sender.unfinished
                        or getattr(self.sender,'_eql_route_operation',None) is not None):
                    raise ValueError('Reached camp, completed recovery and idle sender required')
                j.location_binding.check()
                tracker=self.live_zone_tracker
                lease=tracker.acquire()
                p=SimpleNamespace(journey=j,camp=camp,tracker=tracker,reader=tracker.reader,
                    lease=lease,baseline=tracker.reader.log_line_seq,floor=j.arrival_floor,
                    monitor=j.camp_motion,hotkey=j.location_binding,sender=self.sender,ui=self.sender.ui,
                    gate=self.gate,window=window_identity(self.gate,require_focus=True),
                    generation=self.cancel_generation,settings=settings_identity(self.settings),
                    recovery=camp.recovery,released_at=camp.recovery.last_stand_completed_at,
                    started=clock(),busy=False,sending=False,releasing=False,cancelled=False,reason='',
                    collector=None,request=None,result=None,events=[])
                p.owner_binding=('camp-position',id(j),id(camp),id(p.sender),id(p.ui),
                    id(tracker),id(p.reader),p.generation,p.settings,p.window)
                self.camp_position=p;camp.phase='position_check'
                p.collector=StoppedLocationPair(lease,released_at=p.released_at,
                    check_current=lambda:self._camp_position_current(p),clock=clock,
                    local_wall_clock=self.camp_wall)
                self._camp_position_current(p)
                self.trace('camp_position_started',minimum_log_seq=p.baseline,
                    floor_checkpoint_sha256=p.floor.sha256,stand_command_completed_at=p.released_at,
                    posture_observed=None,movement_sent=False)
                self.emit('Checking stopped position after recovery · F9 stops')
            except (OSError,ValueError,RuntimeError) as error:
                if self.journey is j and self.camp_session is camp:
                    self.stop_action('Camp position collection stopped: '+str(error))
                if lease is not None and self.camp_position is None:lease.release()

        def _stop_camp_position(self,p,reason):
            # F8 already cancelled the camp and queued assist after release.
            # Cleanup failures must not turn that same cancellation into a new
            # stop generation which silently loses the owner's F8 request.
            if not p.cancelled:self.stop_action('Camp position collection stopped: '+str(reason))

        def _camp_position_hotkey(self,p,request):
            collector=p.collector
            def current():
                self._camp_position_current(p);collector.check()
                if (not p.busy or not p.sending or p.collector is not collector
                        or p.request is not request or collector.pending is not request
                        or collector.phase!='requesting'):
                    raise ValueError('Camp location request changed')
            def pump():
                self.pump();self.autopilot_tick(clock())
            p.request=request;p.sending=True
            try:
                receipt=send_location_hotkey(p.sender,binding=p.hotkey,owner_input=p.monitor.observer,
                    lock=self.g0_stop_lock,clock=clock,expires_at=request.expires_at,
                    ensure_current=current,cancel=lambda reason:self._stop_camp_position(p,reason),
                    pump=pump,record_event=p.events.append)
                return CommandReceipt(receipt.pulse.down_started_at,receipt.released_at)
            finally:
                p.sending=False;p.request=None

        def _release_camp_position(self,p):
            if p.releasing:return
            p.releasing=True
            try:p.lease.release()
            finally:
                if self.camp_position is p:self.camp_position=None
                p.releasing=False
            if p.cancelled:
                self.camp_position_last_result=dict(outcome='stopped',reason=p.reason,
                    collection=None if p.collector is None else p.collector.snapshot(),
                    location_events=list(p.events),movement_sent=False,real_client_accepted=False)
                self.trace('camp_position_stopped',**self.camp_position_last_result)

        def _camp_position_tick(self,p):
            if p.busy:
                self._camp_position_current(p)
                if p.collector is not None:p.collector.check()
                return
            p.busy=True
            complete=False
            try:
                self._camp_position_current(p)
                request=p.collector.tick()
                if isinstance(request,LocationRequest):
                    p.collector.command_sent(request,self._camp_position_hotkey(p,request))
                if p.collector.phase=='complete':
                    p.result=measure_camp_stopped_height(p.floor,p.reader,p.collector.first,p.collector.second,
                        minimum_log_seq=p.baseline,released_at=p.released_at,owner_binding=p.owner_binding,
                        binding_reader=lambda:self._camp_position_current(p),clock=clock,
                        local_wall_clock=self.camp_wall)
                    self._camp_position_current(p)
                    complete=True
            except (OSError,ValueError,RuntimeError) as error:
                self._stop_camp_position(p,error)
            finally:
                p.busy=False
                if p.cancelled:self._release_camp_position(p)
            if not complete or p.cancelled:return
            record=dict(outcome='complete',collection=p.collector.snapshot(),
                height=json.loads(p.result.payload),height_sha256=p.result.sha256,
                location_events=p.events,movement_sent=False,real_client_accepted=False)
            self._release_camp_position(p)
            if (self.journey is not p.journey or self.camp_session is not p.camp
                    or not self._camp_current() or p.cancelled):return
            p.journey.height_check_done=True
            self.camp_position_last_result=record
            p.camp.record('stopped_height_checked',height_sha256=p.result.sha256)
            self.trace('camp_position_complete',**record)
            # Base hook rechecks the camp after trace callbacks before resuming.
            super()._camp_recovery_complete(p.camp,clock())

        def stop_action(self,reason,*,keep_autopilot=False):
            p=self.camp_position
            if p is not None:
                p.cancelled=True;p.reason=str(reason)
                if p.collector is not None:p.collector.cancel(reason)
                p.lease.active=False
                if not p.busy:self._release_camp_position(p)
            return super().stop_action(reason,keep_autopilot=keep_autopilot)

        def autopilot_tick(self,now):
            p=self.camp_position
            if p is not None:
                try:self._camp_position_tick(p)
                except (OSError,ValueError,RuntimeError) as error:
                    self._stop_camp_position(p,error)
                return
            return super().autopilot_tick(now)

        def autopilot_payload(self):
            result=super().autopilot_payload()
            if self.camp_position is not None:
                result['phase']='Checking stopped position after recovery'
                collector=self.camp_position.collector
                result['camp_position_phase']='starting' if collector is None else collector.phase
            result['camp_position_last_result']=self.camp_position_last_result
            return result

    return CampPositionEngine
