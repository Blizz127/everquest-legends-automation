"""One camp probe through the retained descriptor and an explicit input policy.

There is no permissive policy implementation here. The caller must supply
current movement admission independently of geometry and historical receipts.
The watchdog records descriptor writes, not acceptance by the game client.
"""
from abc import ABC,abstractmethod
from dataclasses import asdict,dataclass
import os

from .camp_probe_transaction import CampProbeTransaction,CampProbeTicket
from .ground_binding import finite
from .route_step_sender import _fd_identity
from .uinput_watchdog import _EVENT,PulseSelection,selected_key_pulse_receipt


@dataclass(frozen=True)
class CampProbeAuthorization:
    ticket: CampProbeTicket
    issued_at: float
    expires_at: float
    policy_record_id: str


class CampProbeInputPolicy(ABC):
    """Required current-input admission provider; subclasses own its evidence.

    check/still_authorized must return exactly True or refuse. The sender does
    not interpret either as independent scene or motion-bound verification.
    """
    def __init__(self,transaction):
        if type(transaction) is not CampProbeTransaction:
            raise ValueError('Exact camp probe transaction required')
        self.transaction=transaction

    @abstractmethod
    def check(self):raise NotImplementedError

    @abstractmethod
    def authorize(self,ticket):raise NotImplementedError

    @abstractmethod
    def still_authorized(self,authorization):raise NotImplementedError


@dataclass(frozen=True)
class SentCampProbe:
    seal: object
    final_release_at: float


def send_camp_probe(sender,transaction,start,*,policy,requested_seconds,
                    command_state_clear,pump,record_event):
    """Select only after READY, release the pinned fd, then seal actual timing."""
    if (type(transaction) is not CampProbeTransaction
            or not isinstance(policy,CampProbeInputPolicy) or policy.transaction is not transaction
            or not all(callable(f) for f in (command_state_clear,pump,record_event))):
        raise ValueError('Exact transaction and explicit current movement policy required')
    tx=transaction;clock=tx.preparation.clock
    operation=object();owned=False;fd=None;key=None;receipt=None;released_at=None
    ticket=authorization=None;authorization_state=None
    ui=original_fd=identity=None;error_text=None;cleanup_error=None

    def binding():
        tx._check()
        if (sender._eql_route_operation is not operation or sender.ui is not ui
                or ui.fileno()!=original_fd or _fd_identity(original_fd)!=identity
                or policy.transaction is not tx):
            raise ValueError('Camp probe sender, descriptor or policy changed')

    def check():
        binding();sender.check();binding()
        if (sender.unfinished is not False or sender.dismissed is not False
                or sender.held-({key} if key is not None else set())
                or command_state_clear() is not True or policy.check() is not True):
            raise ValueError('Camp probe requires exclusive idle input and current policy')
        binding()
        if authorization is not None:
            if (authorization_values(authorization)!=authorization_state
                    or policy.still_authorized(authorization) is not True):
                raise ValueError('Camp probe input admission revoked')
            binding()

    def stop():
        try:
            with tx.lock:check()
            return False
        except Exception as error:
            tx.cancel(str(error));return True

    def select():
        nonlocal ticket,authorization,authorization_state,key
        check()
        key={'forward':103,'left':105,'right':106}[tx.preparation.kind]
        ticket=tx.stage(start,movement_key=key,requested_seconds=requested_seconds)
        authorization=policy.authorize(ticket)
        now=tx._check()
        if (type(authorization) is not CampProbeAuthorization or authorization.ticket is not ticket
                or not all(finite(v) for v in (authorization.issued_at,authorization.expires_at))
                or not ticket.proposed_at<=authorization.issued_at<=now<=authorization.expires_at
                or authorization.expires_at>min(start.expires_at,ticket.proposed_at+.05)
                or not isinstance(authorization.policy_record_id,str) or not authorization.policy_record_id):
            raise ValueError('Camp probe needs exact bounded current input admission')
        # Avoid recursive asdict of the ticket's complete floor/reader ancestry.
        authorization_state=authorization_values(authorization)
        check();sender.held.add(key)
        return PulseSelection(key,requested_seconds,authorization.expires_at)

    def authorization_values(value):
        return (id(value),id(value.ticket),value.issued_at,value.expires_at,value.policy_record_id)

    try:
        with tx.lock:
            if sender.held or getattr(sender,'_eql_route_operation',None) is not None:
                raise ValueError('Camp probe needs the idle retained sender')
            ui=sender.ui;original_fd=ui.fileno();identity=_fd_identity(original_fd)
            if (sender.codes.KEY_UP,sender.codes.KEY_LEFT,sender.codes.KEY_RIGHT)!=(103,105,106):
                raise ValueError('Camp probe movement key bindings differ')
            sender._eql_route_operation=operation;owned=True
            check();tx.preparation.check_start(start);fd=os.dup(original_fd)
        try:
            receipt=selected_key_pulse_receipt(fd,select,pump=pump,should_stop=stop,go_lock=tx.lock)
        except BaseException as error:
            receipt=getattr(error,'receipt',None)
            raise
        finally:
            with tx.lock:
                if key is not None and fd is not None:
                    try:
                        for event in ((1,key,0),(0,0,0)):
                            if os.write(fd,_EVENT.pack(0,0,*event))!=_EVENT.size:
                                raise OSError('Incomplete camp probe release')
                        released_at=clock()
                        if (sender.ui is ui and ui.fileno()==original_fd
                                and _fd_identity(original_fd)==identity):sender.held.discard(key)
                    except BaseException as error:
                        cleanup_error=error;tx.cancel('Camp probe release failed: '+str(error));raise
        with tx.lock:
            check()
            if receipt is None or ticket is None or sender.held or released_at is None:
                raise ValueError('Camp probe has no completed sender release')
            seal=tx.seal_release(ticket,receipt)
            return SentCampProbe(seal,released_at)
    except BaseException as error:
        error_text=type(error).__name__+': '+str(error);tx.cancel(str(error));raise
    finally:
        try:
            if fd is not None:os.close(fd)
        finally:
            if owned and getattr(sender,'_eql_route_operation',None) is operation:
                sender._eql_route_operation=None
            record_event(dict(kind='camp_probe_pulse',
                movement_key=key,requested_seconds=requested_seconds,
                receipt=None if receipt is None else asdict(receipt),final_release_at=released_at,
                policy_record_id=getattr(authorization,'policy_record_id',None),
                error=error_text,cleanup_error=None if cleanup_error is None else str(cleanup_error),
                client_effect_verified=False,real_client_accepted=False))
