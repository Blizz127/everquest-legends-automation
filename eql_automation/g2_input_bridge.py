"""Isolated G2 pulse bridge for the November helper's existing uinput device.

This is not imported by the owner preview. A future measurement-only job must
provide fresh G2 scenes and serialize OFF with this caller. No route following,
targeting, combat or key other than the helper's existing forward key occurs.
"""
from __future__ import annotations

from collections.abc import Callable

from .g2_pulse_budget import G2PulseBudget, G2Scene, PULSE_SECONDS
from .uinput_watchdog import timed_key_pulse


def run_g2_forward(sender, budget: G2PulseBudget,
                   scene_provider: Callable[[], G2Scene],
                   pump: Callable[[], None], stop_lock) -> float:
    """Use one revocable permit for one bounded forward pulse.

    The child is armed before the permit is reserved, so process startup
    cannot make a previously checked scene stale. ``before_down`` rechecks
    the scene immediately before GO. The watchdog releases on timeout/STOP.
    The caller must follow this with new /location fixes and budget checks.
    """
    if not isinstance(budget, G2PulseBudget) or not callable(scene_provider) or not callable(pump):
        raise ValueError("G2 needs a budget, current-scene observer and input pump")
    if stop_lock is None:
        raise ValueError("G2 needs the owner's shared stop/GO lock")
    forward = sender.codes.KEY_UP
    fd = sender.ui.fileno()
    permit = None

    def before_down():
        nonlocal permit
        sender.check()
        permit = budget.reserve_forward(scene_provider())
        sender.check()
        current = scene_provider()
        budget.confirm_keydown(current, permit)
        sender.held.add(forward)
        return current.at + 0.05

    def should_stop():
        try:
            sender.check()
            if permit is None:
                return budget.stage != "ready"
            budget.still_authorized(scene_provider(), permit)
            return False
        except Exception:
            budget.cancel()
            return True

    try:
        held = timed_key_pulse(fd, forward, PULSE_SECONDS,
                               before_down=before_down,
                               pump=pump, should_stop=should_stop,
                               go_lock=stop_lock)
        budget.record_hold(scene_provider(), held)
        return held
    except BaseException:
        budget.cancel()
        raise
    finally:
        # The watchdog has exited before timed_key_pulse returns or raises.
        # KeySender.release() retains its held record until UP and SYN both
        # succeed, so a failed final release remains visible for cleanup.
        if forward in sender.held:
            try:
                sender.release(forward)
            except Exception:
                budget.cancel()
                raise
