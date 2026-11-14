"""Finite camp-probe execution with one reader and no default movement policy.

This adapter is not installed in owner controls. Its caller supplies current
movement admission and owns the camp-to-runtime handoff. No old motion estimate
or quiet log is used to manufacture unattended clearance.
"""
from dataclasses import asdict
import threading

from .camp_probe_preparation import CampProbePreparation
from .camp_probe_sender import CampProbeInputPolicy,send_camp_probe
from .camp_probe_transaction import CampProbeTransaction
from .camp_stopped_height import measure_camp_stopped_height
from .ground_binding import finite
from .location_hotkey import OwnerLocationHotkey,send_location_hotkey
from .location_hotkey import HOTKEY_CODES
from .motion_calibration import PROBES,Probe
from .motion_collection import CommandReceipt,LocationRequest
from .native_region_policy import encoded
from .stopped_location_pair import StoppedLocationPair


class CampProbeRuntime:
    def __init__(self,preparation,*,sender,hotkey,owner_input,stop_lock,
                 movement_policy_factory,check_current,command_state_clear,pump,
                 probes=PROBES,maximum_seconds=120.):
        if (type(preparation) is not CampProbePreparation or preparation.phase!='new'
                or type(hotkey) is not OwnerLocationHotkey
                or not isinstance(stop_lock,type(threading.RLock()))
                or not all(callable(v) for v in (movement_policy_factory,check_current,
                    command_state_clear,pump,getattr(owner_input,'sample',None)))
                or type(probes) is not tuple or not 1<=len(probes)<=7
                or not finite(maximum_seconds) or not 0<maximum_seconds<=300):
            raise ValueError('Fresh preparation, explicit policy and finite retained runtime required')
        b=preparation.bounds
        if (any(type(p) is not Probe or p.key not in ('forward','left','right')
                or p.key_code!={'forward':103,'left':105,'right':106}[p.key]
                or not finite(p.seconds) or not b.minimum_requested_hold<=p.seconds<=b.maximum_requested_hold
                for p in probes) or probes[0].key!=preparation.kind):
            raise ValueError('Probe sequence differs from its prepared kind or explicit hold bounds')
        self.root=self.preparation=preparation;self.sender=sender;self.hotkey=hotkey
        self.owner_input=owner_input;self.lock=stop_lock
        self.policy_factory=movement_policy_factory;self.current=check_current
        self.command_clear=command_state_clear;self.pump=pump
        self.probes=probes;self._probes_bytes=encoded([asdict(p) for p in probes])
        self.maximum_seconds=maximum_seconds
        self.clock=preparation.clock;self.wall=preparation.wall;self.lease=preparation.lease
        self._context=(preparation,sender,hotkey,owner_input,stop_lock,movement_policy_factory,
            check_current,command_state_clear,pump,probes,self.clock,self.wall,self.lease,maximum_seconds)
        self.phase='prepare';self.reason='';self.busy=False;self.closed=False
        self.started=self.last_at=self.clock()
        self.collector=None;self.collection_kind=None;self.baseline=None;self.released_at=None
        self.index=0;self.transaction=None;self.start=None;self.policy=None;self.sent=None
        self.reference=None;self.results=[];self.transactions=[];self.collections=[];self.events=[]
        self.input_kind=self.input_request=None
        self._check();preparation.check(fresh=preparation.height)

    def _check(self):
        if self.phase=='stopped' or self.closed:raise ValueError(self.reason or 'Camp probe runtime ended')
        self.current();self.root.check();self.lease.check();self.hotkey.check()
        now=self.clock()
        actual=(self.root,self.sender,self.hotkey,self.owner_input,self.lock,self.policy_factory,
            self.current,self.command_clear,self.pump,self.probes,self.clock,self.wall,self.lease,self.maximum_seconds)
        if (self.phase=='stopped' or self.closed
                or any(a is not b for a,b in zip(self._context,actual))
                or encoded([asdict(p) for p in self.probes])!=self._probes_bytes
                or not finite(now) or not self.started<=self.last_at<=now<=self.started+self.maximum_seconds):
            raise ValueError('Camp probe runtime context changed or budget expired')
        self.last_at=now
        return now

    def cancel(self,reason):
        with self.lock:
            if self.phase=='stopped':return
            self.phase='stopped';self.reason=str(reason)
            if self.collector is not None:self.collector.cancel(reason)
            for tx in self.transactions:tx.cancel(reason)
            self.preparation.cancel(reason)
            # Keep navigation busy through any DOWN/UP cleanup. release() owns
            # the later lease release, which clears the reader's latest reply.
            self.lease.active=False

    def release(self):
        """Caller cleanup after completion/stop and actual sender release."""
        with self.lock:
            if self.closed:return
            if (self.phase not in ('complete','stopped') or self.busy or self.sender.held
                    or getattr(self.sender,'_eql_route_operation',None) is not None):
                raise ValueError('Camp probe runtime still owns pending input or work')
            self.lease.release();self.closed=True

    def _begin_pair(self,kind,*,released_at):
        self._check()
        self.baseline=self.lease.reader.log_line_seq;self.released_at=released_at
        self.collection_kind=kind
        self.collector=StoppedLocationPair(self.lease,released_at=released_at,
            check_current=self._check,clock=self.clock,local_wall_clock=self.wall)
        self.phase='collect_'+kind

    def _send_location(self,collector,request):
        def current():
            self._check();collector.check()
            if self.collector is not collector or collector.phase!='requesting' or collector.pending is not request:
                raise ValueError('Camp probe position request changed')
        self.input_kind='location';self.input_request=request
        try:
            receipt=send_location_hotkey(self.sender,binding=self.hotkey,owner_input=self.owner_input,
                lock=self.lock,clock=self.clock,expires_at=request.expires_at,ensure_current=current,
                cancel=self.cancel,pump=self.pump,record_event=self.events.append)
        finally:self.input_kind=self.input_request=None
        collector.command_sent(request,CommandReceipt(receipt.pulse.down_started_at,receipt.released_at))

    def current_input_key(self):
        """Exact pending driver key for engine admission; no movement permission."""
        if not self.busy or self.closed:return None
        if (self.input_kind=='location' and self.phase.startswith('collect_')
                and self.collector is not None and self.collector.phase=='requesting'
                and self.input_request is self.collector.pending):
            return HOTKEY_CODES[self.hotkey.key_name]
        if (self.input_kind=='movement' and self.phase=='pulse'
                and self.input_request is self.transaction and self.transaction is not None
                and self.transaction.phase in ('new','proposed','await_pair')):
            return self.probes[self.index].key_code
        return None

    def _collected(self):
        collector=self.collector
        request=collector.tick()
        if isinstance(request,LocationRequest):self._send_location(collector,request)
        if collector.phase!='complete':return None
        first,second=collector.first,collector.second
        self.collections.append(dict(kind=self.collection_kind,index=self.index,evidence=collector.snapshot()))
        # The completed collector has its own eight-second lifetime. Detach it
        # before geometry work, which must not renew or recheck that lifetime.
        self.collector=None
        return first,second

    def tick(self):
        if self.closed or self.phase in ('complete','stopped'):return
        if self.busy:
            try:self._check()
            except Exception as error:self.cancel(str(error));raise
            return
        self.busy=True
        try:
            self._check()
            if self.phase=='prepare':
                self.preparation.prepare(maximum_seconds=min(30.,self.started+self.maximum_seconds-self.clock()))
                self._begin_pair('start',released_at=self._check())
            elif self.phase.startswith('collect_'):
                kind=self.collection_kind;pair=self._collected()
                if pair is None:return
                self._check();first,second=pair
                if kind=='start':
                    self.start=self.preparation.observe_start(first,second,
                        minimum_log_seq=self.baseline,released_at=self.released_at)
                    self.transaction=CampProbeTransaction(self.preparation,stop_lock=self.lock)
                    self.transactions.append(self.transaction)
                    self.policy=self.policy_factory(self.transaction)
                    if (not isinstance(self.policy,CampProbeInputPolicy)
                            or self.policy.transaction is not self.transaction):
                        raise ValueError('No explicit movement policy for this probe')
                    self._check();self.phase='pulse'
                elif kind=='endpoint':
                    self.phase='endpoint_geometry'
                    self.transaction.prepare_endpoint(self.sent.seal,first,second,
                        maximum_seconds=min(30.,self.started+self.maximum_seconds-self.clock()))
                    self._begin_pair('confirm',released_at=self._check())
                elif kind=='confirm':
                    result=self.transaction.confirm_endpoint(first,second,minimum_log_seq=self.baseline)
                    self.reference=self.transaction.retain_endpoint(result)
                    self._check();self.results.append(result);self.index+=1
                    if self.index==len(self.probes):self.phase='complete'
                    else:self._begin_pair('planning',released_at=self._check())
                elif kind=='planning':
                    root=self.root
                    height=measure_camp_stopped_height(self.reference,self.lease.reader,first,second,
                        minimum_log_seq=self.baseline,released_at=self.released_at,
                        owner_binding=root.owner_binding,binding_reader=root.binding_reader,
                        clock=self.clock,local_wall_clock=self.wall)
                    self.preparation=CampProbePreparation(self.reference,height,self.lease,
                        probe_kind=self.probes[self.index].key,bounds=root.bounds,bounds_basis=root.bounds_basis,
                        owner_binding=root.owner_binding,binding_reader=root.binding_reader,
                        clock=self.clock,local_wall_clock=self.wall)
                    self._check();self.phase='prepare'
                else:raise ValueError('Unknown camp probe collection stage')
            elif self.phase=='pulse':
                self.input_kind='movement';self.input_request=self.transaction
                try:
                    self.sent=send_camp_probe(self.sender,self.transaction,self.start,policy=self.policy,
                        requested_seconds=self.probes[self.index].seconds,
                        command_state_clear=self.command_clear,pump=self.pump,record_event=self.events.append)
                finally:self.input_kind=self.input_request=None
                self._check()
                self._begin_pair('endpoint',released_at=self.sent.final_release_at)
            else:raise ValueError('Unknown camp probe runtime phase')
        except BaseException as error:
            self.cancel(str(error));raise
        finally:self.busy=False

    def snapshot(self):
        return dict(phase=self.phase,reason=self.reason,busy=self.busy,closed=self.closed,
            completed_probes=len(self.results),proposed_probes=[asdict(p) for p in self.probes],
            result_sha256=[r.sha256 for r in self.results],collections=list(self.collections),
            sender_events=list(self.events),
            current_floor_sha256=None if self.reference is None else self.reference.sha256,
            input_policy_required=True,independent_scene_verified=False,motion_bounds_verified=False,
            current_heading_verified=False,real_client_accepted=False)
