"""One checked route pulse on the existing sender, with transactional release.

Not installed in an owner helper. All providers are mandatory trusted
dependencies: in particular an offline FloorTrial is never an authorization.
The default external guard must cover the complete swept body, measured
hold/speed/drift bounds, static/BSP geometry and current dynamic hazards.
An explicit supervised measurement policy instead retains owner declarations
and conditional planning bounds, with their verification fields false. This
bridge checks bindings and revocation, not the truth of those measurements.

All users of this sender (including device close/replacement) must share the
ledger's stop lock and respect its exclusive operation marker. A duplicated
descriptor pins watchdog cleanup to the original open device even on failure.
No device is created; no chat, target, recovery or location command is sent.
"""
from dataclasses import dataclass
import os

from .fixed_route_follower import RouteHalt, finite
from .g2_pulse_budget import G2Scene
from .ground_binding import AlignedWldFix
from .route_floor_commit import FloorCommitTicket, RouteFloorCommit
from .uinput_watchdog import PulseReceipt, PulseSelection, PulseInterrupted, selected_key_pulse_receipt


@dataclass(frozen=True)
class RouteStepScene:
    # The provider must poll the independent log/scene observer and preserve
    # the exact accepted AlignedWldFix object (including its raw fix). This is
    # the stopped reference, never
    # a claim to have observed the character's current position while moving.
    reference_fix: AlignedWldFix
    scene: G2Scene


@dataclass(frozen=True)
class RouteStepAuthorization:
    ticket: FloorCommitTicket
    reference_fix: AlignedWldFix
    issued_at: float
    expires_at: float
    guard_record_id: str


@dataclass(frozen=True)
class RouteStepResult:
    receipt: PulseReceipt
    floor_proof_sha256: str
    guard_record_id: str
    # Device writes alone do not prove client consumption or route acceptance.
    real_client_accepted: bool = False
    authorization_scope: str = 'external_guard'


def _fd_identity(fd):
    info = os.fstat(fd)
    return info.st_dev, info.st_ino, info.st_rdev, info.st_mode


def run_checked_route_step(sender, ledger, *, scene_provider, prepare_step,
                           authorize_step, still_authorized,
                           command_state_clear, pump, supervised_policy=None):
    return _run_checked_step(sender,ledger,scene_provider=scene_provider,prepare_step=prepare_step,
        authorize_step=authorize_step,still_authorized=still_authorized,
        command_state_clear=command_state_clear,pump=pump,supervised_policy=supervised_policy)


def run_checked_crossing_step(sender, crossing, *, policy, scene_provider, command_state_clear, pump):
    """One final source pulse, release, then an independently checked arrival.

    The caller transfers the exclusive reader before calling, and must not run
    the ordinary RouteSessionDriver concurrently. No source floor/pose commit
    occurs, including when the pulse elapses before the loading log arrives.
    """
    from .crossing_pulse import CrossingPulseHandoff
    if type(crossing) is not CrossingPulseHandoff:
        raise ValueError('Explicit exclusive crossing handoff required')
    try:
        crossing.start(policy)
        try:
            receipt=_run_checked_step(sender,crossing.ledger,scene_provider=scene_provider,
                prepare_step=crossing.geometry,authorize_step=policy.authorize,
                still_authorized=policy.still_authorized,command_state_clear=command_state_clear,
                pump=pump,supervised_policy=policy,crossing=crossing)
        except PulseInterrupted as error:
            if crossing.arrival.loading is None or crossing.arrival.phase=='stopped':raise
            receipt=error.receipt
        if sender.held or getattr(sender,'_eql_route_operation',None) is not None:
            raise RouteHalt('Crossing sender has not finished exclusive release cleanup')
        return crossing.released(receipt)
    except BaseException as error:
        crossing.cancel(str(error));raise


def run_checked_corridor_step(sender,corridor,*,policy,scene_provider,command_state_clear,pump):
    """One pulse in the same aggregate corridor; elapsed receipts stay sealed."""
    from .crossing_corridor import CrossingCorridorHandoff
    if type(corridor) is not CrossingCorridorHandoff:
        raise ValueError('Explicit exclusive crossing corridor required')
    try:
        corridor.start(policy)
        try:
            receipt=_run_checked_step(sender,corridor.ledger,scene_provider=scene_provider,
                prepare_step=corridor.geometry,authorize_step=policy.authorize,
                still_authorized=policy.still_authorized,command_state_clear=command_state_clear,
                pump=pump,supervised_policy=policy,corridor=corridor)
        except PulseInterrupted as error:
            if corridor.arrival.loading is None or corridor.arrival.phase=='stopped':raise
            receipt=error.receipt
        if sender.held or getattr(sender,'_eql_route_operation',None) is not None:
            raise RouteHalt('Corridor sender has not finished exclusive release cleanup')
        return corridor.released(receipt)
    except BaseException as error:
        corridor.cancel(str(error));raise


def _run_checked_step(sender, ledger, *, scene_provider, prepare_step,
                      authorize_step, still_authorized, command_state_clear, pump,
                      supervised_policy=None,crossing=None,corridor=None):
    """Arm, observe, propose, check, send, release, then commit exactly once.

    ``prepare_step(proposal, scene)`` stages the complete geometry request on
    this ledger. Its optional ``precompute(scene)`` method runs while stopped,
    before arming the child or creating the fresh proposal. It must not mutate
    route/scene/input state or extend the reference lifetime.
    ``authorize_step(ticket, scene)`` supplies an independently
    verified RouteStepAuthorization for that exact request. Its guard must
    remain revocable through ``still_authorized(authorization, scene)``.
    ``command_state_clear()`` must read engine recovery/draft/job state, not
    merely sender.check(). All callbacks must avoid input and device mutation;
    pump may process OFF, which must cancel/increment the bound generation.

    An explicit SupervisedRoutePolicy may instead supply its separate typed,
    owner-declared measurement evidence. This does not claim independent UI or
    motion-bound verification. It retains geometry, timing, release and commit
    checks and cannot run in full-auto/assist. The default path is unchanged.

    Fresh scene checks can exhaust the 50 ms proposal deadline; that refuses
    movement rather than renewing timestamps. After success the follower still
    requires a new stopped-location pair. Assist/off always refuse movement.
    """
    if corridor is not None:
        if crossing is not None:raise ValueError('One exclusive transition controller required')
        crossing=corridor
    if (not isinstance(ledger, RouteFloorCommit) or not all(callable(f) for f in
            (scene_provider, prepare_step, authorize_step, still_authorized,
             command_state_clear, pump))):
        raise ValueError('A route ledger and all independent live providers are required')
    if supervised_policy is not None:
        from .supervised_route import SupervisedRoutePolicy
        policy_type=SupervisedRoutePolicy
        if corridor is not None:
            from .supervised_corridor import SupervisedCrossingCorridorPolicy
            policy_type=SupervisedCrossingCorridorPolicy
        elif crossing is not None:
            from .supervised_crossing import SupervisedCrossingPolicy
            policy_type=SupervisedCrossingPolicy
        if (type(supervised_policy) is not policy_type
                or supervised_policy.ledger is not ledger
                or prepare_step is not supervised_policy.geometry
                or authorize_step != supervised_policy.authorize
                or still_authorized != supervised_policy.still_authorized):
            raise ValueError('Supervised route must use its exact geometry and typed policy')
    elif crossing is not None:
        raise ValueError('Crossing requires its exact explicit supervised policy')
    operation = object()
    owned = False
    pinned_fd = None
    key = None
    ticket = authorization = reference = None
    ui = identity = original_fd = None
    initial_mode = None
    released = False
    r = ledger.runner

    def binding():
        r._check(ledger.clock())
        if (getattr(sender, '_eql_route_operation', None) is not operation
                or sender.ui is not ui or ui.fileno() != original_fd
                or _fd_identity(original_fd) != identity
                or r.mode_reader() != initial_mode):
            raise RouteHalt('Route sender/device/mode binding changed')
        if ticket is not None:
            ledger.check_pending(ticket)

    def check_sender():
        binding()
        sender.check()  # May synchronously process OFF using this same RLock.
        if (sender.unfinished is not False or sender.dismissed is not False
                or command_state_clear() is not True
                or sender.held - ({key} if key is not None and not released else set())):
            raise RouteHalt('Route requires closed chat, clear recovery and exclusive keys')
        binding()  # Recheck after every potentially reentrant callback.

    def checked_scene():
        if crossing is not None:
            binding()  # A changed descriptor must never receive arrival cleanup.
            if crossing.poll_loading():
                raise RouteHalt('Source movement ends on observed loading')
        check_sender()
        observed = scene_provider()
        binding()
        now = ledger.clock()
        if not isinstance(observed, RouteStepScene) or not isinstance(observed.reference_fix, AlignedWldFix):
            raise RouteHalt('No independent route scene/reference')
        aligned = observed.reference_fix
        raw, scene = aligned.raw_fix, observed.scene
        if (not isinstance(scene, G2Scene) or not finite(scene.at)
                or not 0 <= now-scene.at <= .1
                or not finite(raw.received_monotonic) or not 0 <= now-raw.received_monotonic <= .5
                or scene.zone != r.route.zone or scene.raw_location != raw.raw_coordinates
                or (scene.log_epoch, scene.fix_seq, scene.zone_generation) !=
                   (raw.log_epoch, raw.log_line_seq, raw.zone_generation)
                or (raw.zone_id, raw.zone_display_name, raw.log_epoch, raw.zone_generation) != r.binding
                or raw.log_line_seq != r.last_seq or raw.received_monotonic != r.last_fix_at
                or aligned.mesh_projection.package_xyz != (r.pose.x, r.pose.y, r.pose.z)
                or (reference is not None and aligned is not reference)):
            raise RouteHalt('Route scene is stale, unsafe or differs from the stopped reference')
        if supervised_policy is None:
            if type(scene) is not G2Scene or not all(v is True for v in
                    (scene.focused, scene.owner_keys_clear, scene.chat_clear, scene.target_absent,
                     scene.combat_clear, scene.no_transition, scene.no_incoming_attack)):
                raise RouteHalt('Independent route scene is missing or unsafe')
        else:
            supervised_policy.validate_scene(observed, ledger)
        return observed

    def select():
        nonlocal reference, ticket, authorization, key
        observed = checked_scene()
        reference = observed.reference_fix
        proposal = r.propose(ledger.clock())  # Child READY precedes this timestamp.
        ticket = prepare_step(proposal, observed)
        binding()
        if (not isinstance(ticket, FloorCommitTicket)
                or ticket.preparation.proposal is not proposal
                or ticket.preparation.reference_fix is not reference
                or ledger._pending is None or ledger._pending[0] is not ticket):
            raise RouteHalt('Guard did not stage this exact route step')
        authorization = authorize_step(ticket, observed)
        binding()
        now = ledger.clock()
        if (not isinstance(authorization, RouteStepAuthorization)
                or authorization.ticket is not ticket or authorization.reference_fix is not reference
                or not all(finite(t) for t in (authorization.issued_at, authorization.expires_at))
                or not ticket.staged_at <= authorization.issued_at <= now <= authorization.expires_at
                or authorization.expires_at > proposal.at+.05
                or not isinstance(authorization.guard_record_id, str) or not authorization.guard_record_id):
            raise RouteHalt('Missing fresh route-step authorization')
        if supervised_policy is None:
            if type(authorization) is not RouteStepAuthorization:
                raise RouteHalt('Default route requires independent authorization')
        else:
            supervised_policy.validate_authorization(authorization, observed)
        check_sender()
        if crossing is not None:crossing.selected(ticket)
        key = ticket.preparation.movement_key
        sender.held.add(key)  # Retain until final UP and SYN both succeed.
        return PulseSelection(key, ticket.preparation.requested_seconds, authorization.expires_at)

    def should_stop():
        try:
            with ledger.lock:
                if crossing is not None:
                    binding()
                    if crossing.poll_loading():return True
                observed = checked_scene()
                if authorization is not None:
                    if still_authorized(authorization, observed) is not True:
                        raise RouteHalt('Whole-motion authorization revoked')
                    check_sender()
                return False
        except Exception as error:
            ledger.cancel(str(error))
            return True

    try:
        with ledger.lock:
            if getattr(sender, '_eql_route_operation', None) is not None:
                raise RouteHalt('Another route sender operation is active')
            sender._eql_route_operation = operation
            owned = True
            ui = sender.ui
            original_fd = ui.fileno()
            identity = _fd_identity(original_fd)
            initial_mode = r.mode_reader()
            if (sender.held or r.phase != 'ready' or ledger._pending is not None
                    or ledger._busy is not None
                    or (sender.codes.KEY_UP, sender.codes.KEY_LEFT, sender.codes.KEY_RIGHT) != (103,105,106)):
                raise RouteHalt('Route sender is not idle or movement key bindings differ')
            check_sender()
            precompute = getattr(prepare_step, 'precompute', None)
            if precompute is not None:
                if not callable(precompute):
                    raise RouteHalt('Invalid route geometry precomputation')
                observed = checked_scene()
        if precompute is not None:
            # No keys or watchdog are armed. Let OFF acquire the stop lock
            # while the expensive read-only geometry checks run.
            precompute(observed)
        with ledger.lock:
            check_sender()
            if precompute is not None:
                fresh = checked_scene()
                if fresh.reference_fix is not observed.reference_fix or r.phase != 'ready':
                    raise RouteHalt('Stopped reference changed during geometry precomputation')
            pinned_fd = os.dup(original_fd)
        try:
            receipt = selected_key_pulse_receipt(pinned_fd, select, pump=pump,
                should_stop=should_stop, go_lock=ledger.lock)
        finally:
            # Watchdog teardown/its pinned-fd UP has finished. Never consult
            # focus or send Escape before cleanup. A replacement UI must not
            # receive this operation's release, nor clear its held marker.
            with ledger.lock:
                if key is not None:
                    if (sender.ui is not ui or ui.fileno() != original_fd
                            or _fd_identity(original_fd) != identity):
                        raise RouteHalt('Input device changed; final sender release unavailable')
                    sender.release(key)
                    if key in sender.held:
                        raise RouteHalt('Sender failed to acknowledge final release')
                    released = True
        os.close(pinned_fd)
        pinned_fd = None
        with ledger.lock:
            if receipt is None or ticket is None or authorization is None:
                raise RouteHalt('No completed checked route pulse')
            if should_stop():
                if crossing is not None and crossing.arrival.loading is not None:
                    raise PulseInterrupted('Loading observed after crossing release',receipt)
                raise RouteHalt('Route was cancelled before receipt commit')
            if sender.held:
                raise RouteHalt('Sender acquired a held key after final release')
            if corridor is not None:
                corridor.seal_released(receipt)
                return receipt
            if crossing is not None:
                ledger.cancel('Final crossing pulse released; source floor is not committed')
                return receipt
            floor = ledger.commit(ticket, receipt)
            return RouteStepResult(receipt, floor.proof_sha256, authorization.guard_record_id,
                authorization_scope='external_guard' if supervised_policy is None else
                                    'owner_supervised_conditional_trial')
    except BaseException:
        ledger.cancel('Checked route sender failed; no floor commit')
        raise
    finally:
        try:
            if pinned_fd is not None:
                os.close(pinned_fd)
        finally:
            if owned:
                with ledger.lock:
                    if getattr(sender, '_eql_route_operation', None) is operation:
                        sender._eql_route_operation = None
