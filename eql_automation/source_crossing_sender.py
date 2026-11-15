"""One checked source-crossing pulse on the retained sender.

Supports early interruption when ZoneArrivalHandoff observes LOADING after a
checked transition-touching footprint. Never commits a floor on release.
"""
import os

from .fixed_route_follower import RouteHalt
from .route_step_sender import _fd_identity
from .source_crossing_corridor import SourceCrossingCorridor
from .supervised_source_crossing import SupervisedSourceCrossingPolicy
from .uinput_watchdog import PulseInterrupted, PulseSelection, selected_key_pulse_receipt


def run_checked_source_crossing_step(sender, corridor, *, policy, kind,
                                     requested_seconds, command_state_clear, pump):
    if (type(corridor) is not SourceCrossingCorridor
            or type(policy) is not SupervisedSourceCrossingPolicy
            or policy.corridor is not corridor
            or not callable(command_state_clear)
            or not callable(pump)):
        raise ValueError('Exact source crossing corridor, supervised policy and sender providers required')
    operation = object()
    owned = False
    pinned_fd = None
    key = None
    released = False
    ticket = authorization = None
    ui = identity = original_fd = reference = None

    def binding(*, validate_corridor=True):
        if validate_corridor and ticket is None:
            corridor._current()
        if (getattr(sender, '_eql_route_operation', None) is not operation
                or sender.ui is not ui
                or ui.fileno() != original_fd
                or _fd_identity(original_fd) != identity
                or corridor.reference is not reference):
            raise RouteHalt('Source crossing sender, descriptor or reference changed')
        if validate_corridor and ticket is not None:
            corridor.check_pending(ticket)

    def check_sender(*, validate_corridor=True):
        binding(validate_corridor=False)
        sender.check()
        if (sender.unfinished is not False or sender.dismissed is not False
                or command_state_clear() is not True
                or sender.held - ({key} if key is not None and not released else set())):
            raise RouteHalt('Source crossing movement needs exclusive keys and clear command state')
        binding(validate_corridor=validate_corridor)

    def scene(*, validate=True):
        check_sender(validate_corridor=False)
        value = policy.observe(validate_reference=False)
        binding(validate_corridor=False)
        if validate:
            policy.validate_scene(value)
        return value

    def select():
        nonlocal ticket, authorization, key
        observed = scene()
        ticket = corridor.stage(geometry, requested_seconds=requested_seconds)
        authorization = policy.authorize(ticket, observed)
        if sender.held:
            raise RouteHalt('Source crossing sender acquired a key during authorization')
        if authorization.expires_at > ticket.proposed_at + .05:
            raise RouteHalt('Source crossing DOWN deadline changed')
        key = ticket.movement_key
        sender.held.add(key)
        return PulseSelection(key, ticket.requested_seconds, authorization.expires_at)

    def should_stop():
        try:
            with corridor.lock:
                if ticket is not None:
                    binding(validate_corridor=False)
                    if corridor.poll_loading():
                        return True
                observed = scene(validate=authorization is None)
                if authorization is not None:
                    if policy.still_authorized(authorization, observed) is not True:
                        raise RouteHalt('Source crossing movement permission revoked')
                    check_sender()
                return False
        except Exception as error:
            corridor.cancel(str(error))
            return True

    try:
        with corridor.lock:
            if getattr(sender, '_eql_route_operation', None) is not None:
                raise RouteHalt('Another sender operation is active')
            sender._eql_route_operation = operation
            owned = True
            ui = sender.ui
            original_fd = ui.fileno()
            identity = _fd_identity(original_fd)
            reference = corridor.reference
            if (sender.held or corridor.phase != 'ready'
                    or (sender.codes.KEY_UP, sender.codes.KEY_LEFT, sender.codes.KEY_RIGHT) != (103, 105, 106)):
                raise RouteHalt('Source crossing sender is not idle or key bindings differ')
            scene()
        geometry = corridor.prepare(kind, policy=policy)
        with corridor.lock:
            scene()
            pinned_fd = os.dup(original_fd)
        try:
            try:
                receipt = selected_key_pulse_receipt(
                    pinned_fd, select, pump=pump,
                    should_stop=should_stop, go_lock=corridor.lock,
                )
            except PulseInterrupted as error:
                if corridor.arrival.loading is None or corridor.arrival.phase == 'stopped':
                    raise
                receipt = error.receipt
        finally:
            with corridor.lock:
                if key is not None:
                    if (sender.ui is not ui or ui.fileno() != original_fd
                            or _fd_identity(original_fd) != identity):
                        raise RouteHalt('Source crossing input device changed; sender release unavailable')
                    sender.release(key)
                    if key in sender.held:
                        raise RouteHalt('Source crossing sender did not acknowledge UP')
                    released = True
        os.close(pinned_fd)
        pinned_fd = None
        with corridor.lock:
            if receipt is None or ticket is None or authorization is None or sender.held:
                reason = ': ' + corridor.reason if corridor.reason else ''
                raise RouteHalt('No uncancelled source crossing release receipt' + reason)
            if corridor.arrival.loading is None and should_stop():
                if corridor.arrival.loading is None or corridor.arrival.phase == 'stopped':
                    reason = ': ' + corridor.reason if corridor.reason else ''
                    raise RouteHalt('Source crossing cancelled before release completion' + reason)
            return corridor.released(receipt)
    except BaseException as error:
        corridor.cancel(str(error))
        raise
    finally:
        try:
            if pinned_fd is not None:
                os.close(pinned_fd)
        finally:
            if owned:
                with corridor.lock:
                    if getattr(sender, '_eql_route_operation', None) is operation:
                        sender._eql_route_operation = None
