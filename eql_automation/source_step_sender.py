"""One source-only pulse on the retained sender; return a provisional seal."""
import os

from .fixed_route_follower import RouteHalt
from .route_step_sender import _fd_identity
from .source_motion import SourceReceiptLedger
from .source_transfer import SourceTransferController
from .source_stair_controller import SourceStairController
from .source_contact_controller import SourceContactController
from .supervised_source import SupervisedSourcePolicy
from .uinput_watchdog import PulseSelection, selected_key_pulse_receipt


def run_checked_source_step(sender,ledger,*,policy,kind,requested_seconds,
                            command_state_clear,pump):
    if (type(ledger) not in (SourceReceiptLedger,SourceTransferController,SourceStairController,SourceContactController) or type(policy) is not SupervisedSourcePolicy
            or policy.ledger is not ledger or not callable(command_state_clear) or not callable(pump)):
        raise ValueError('Exact source ledger, supervised policy and current sender providers required')
    operation=object();owned=False;pinned_fd=None;key=None;released=False
    ticket=authorization=None
    ui=identity=original_fd=reference=None

    def binding():
        # Pending validation below already checks the complete ledger after
        # descriptor callbacks. Do not repeat that ancestry scan here.
        if ticket is None:ledger._check()
        if (sender._eql_route_operation is not operation or sender.ui is not ui
                or ui.fileno()!=original_fd or _fd_identity(original_fd)!=identity
                or ledger.reference is not reference):
            raise RouteHalt('Source sender, descriptor or reference changed')
        if ticket is not None:ledger.check_pending(ticket)

    def check_sender():
        binding();sender.check()
        if (sender.unfinished is not False or sender.dismissed is not False
                or command_state_clear() is not True
                or sender.held-({key} if key is not None and not released else set())):
            raise RouteHalt('Source movement needs exclusive keys and clear command state')
        binding()

    def scene():
        check_sender();value=policy.observe();binding();policy.validate_scene(value)
        return value

    def select():
        nonlocal ticket,authorization,key
        observed=scene()
        ticket=ledger.stage(geometry,requested_seconds=requested_seconds)
        authorization=policy.authorize(ticket,observed)
        # The watchdog unconditionally calls should_stop under this same lock
        # after selection and before GO. That pass re-observes the scene and
        # rechecks sender/ticket/authorization after all provider callbacks.
        # Do not spend the 50ms permit on an identical extra sender pass here.
        if sender.held:
            raise RouteHalt('Source sender acquired a key during authorization')
        if authorization.expires_at>ticket.proposed_at+.05:
            raise RouteHalt('Source DOWN deadline changed')
        key=ticket.movement_key;sender.held.add(key)
        return PulseSelection(key,ticket.requested_seconds,authorization.expires_at)

    def should_stop():
        try:
            with ledger.lock:
                observed=scene()
                if authorization is not None:
                    if policy.still_authorized(authorization,observed) is not True:
                        raise RouteHalt('Source movement permission revoked')
                    check_sender()
                return False
        except Exception as error:
            ledger.cancel(str(error));return True

    try:
        with ledger.lock:
            if getattr(sender,'_eql_route_operation',None) is not None:
                raise RouteHalt('Another sender operation is active')
            sender._eql_route_operation=operation;owned=True
            ui=sender.ui;original_fd=ui.fileno();identity=_fd_identity(original_fd)
            reference=ledger.reference
            if (sender.held or ledger.phase!='ready'
                    or (sender.codes.KEY_UP,sender.codes.KEY_LEFT,sender.codes.KEY_RIGHT)!=(103,105,106)):
                raise RouteHalt('Source sender is not idle or key bindings differ')
            scene()
        geometry=ledger.prepare(kind)  # No keys; OFF may acquire the shared lock.
        with ledger.lock:
            scene();pinned_fd=os.dup(original_fd)
        try:
            receipt=selected_key_pulse_receipt(pinned_fd,select,pump=pump,
                should_stop=should_stop,go_lock=ledger.lock)
        finally:
            with ledger.lock:
                if key is not None:
                    if sender.ui is not ui or ui.fileno()!=original_fd or _fd_identity(original_fd)!=identity:
                        raise RouteHalt('Source input device changed; sender release unavailable')
                    sender.release(key)
                    if key in sender.held:raise RouteHalt('Source sender did not acknowledge UP')
                    released=True
        os.close(pinned_fd);pinned_fd=None
        with ledger.lock:
            if receipt is None or ticket is None or authorization is None or should_stop() or sender.held:
                raise RouteHalt('No uncancelled source release receipt')
            return ledger.seal_release(ticket,receipt)
    except BaseException as error:
        ledger.cancel(str(error));raise
    finally:
        try:
            if pinned_fd is not None:os.close(pinned_fd)
        finally:
            if owned:
                with ledger.lock:
                    if getattr(sender,'_eql_route_operation',None) is operation:
                        sender._eql_route_operation=None
