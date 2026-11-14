"""Same-device release watchdog for the existing owner-run G0 check only.

This adds no movement mode: assist refuses hold(), and measurement permits
only its existing single 0.15-second forward stop check. G2 remains unwired.
"""
from __future__ import annotations

import threading
import time

from .owner_nov12_recovery import make_owner_nov12_engine as restricted_engine
from .uinput_watchdog import PulseError, timed_key_pulse


def make_owner_nov12_engine(base_engine: type) -> type:
    class WatchdogOwnerEngine(restricted_engine(base_engine)):
        def __init__(self, *args, **kwargs):
            # Reentrant: sender.check() reads F9 and can call stop_action()
            # while before_down is already inside the same stop/GO lock.
            self.g0_stop_lock = threading.RLock()
            super().__init__(*args, **kwargs)

        def stop_action(self, reason, *, keep_autopilot=False):
            with self.g0_stop_lock:
                return super().stop_action(reason, keep_autopilot=keep_autopilot)

        def stop_autopilot(self, reason):
            with self.g0_stop_lock:
                return super().stop_autopilot(reason)

        def hold(self, key, seconds, *, jump_at=None, should_stop=None):
            pilot = self.autopilot
            if (not self.measurement_only or self.active or self.preparing
                    or pilot is None or pilot.mode != "stop_check" or not pilot.running
                    or key != "forward" or type(seconds) is not float or seconds != 0.15
                    or jump_at is not None):
                raise InterruptedError("Only the supervised G0 forward pulse is available")
            generation = self.cancel_generation
            sender = self.ensure_sender()
            if sender.unfinished or self.command_recovery_pending or sender.held:
                raise InterruptedError("G0 requires closed helper chat and released keys")
            forward = sender.codes.KEY_UP

            def stopped():
                try:
                    sender.check()  # Includes focus, owner keys and F9 processing.
                    return (self.stopping or self.cancelled or self.active or self.preparing
                            or self.cancel_generation != generation
                            or self.autopilot is not pilot or not pilot.running
                            or sender.unfinished or self.command_recovery_pending
                            or (should_stop is not None and should_stop()))
                except Exception:
                    return True

            def before_down():
                self.pump()
                if stopped():
                    raise InterruptedError("G0 cancelled before key down")
                sender.held.add(forward)
                return time.monotonic() + 0.05

            self.trace("g0_watchdog_start", requested=seconds, generation=generation,
                       key="forward", same_device=True)
            try:
                held = timed_key_pulse(sender.ui.fileno(), forward, seconds,
                                       before_down=before_down, pump=self.pump,
                                       should_stop=stopped, go_lock=self.g0_stop_lock)
                if not 0 < held <= 0.20:
                    raise PulseError("G0 exceeded its 0.20-second reported hold limit")
                if stopped():
                    raise InterruptedError("G0 stopped after release; result is not accepted")
                self.trace("hold", key=key, requested=seconds, held=round(held, 6),
                           release="same_device_watchdog")
                return held
            except BaseException as error:
                self.stopped_mid_command = self.cancel_generation != generation
                self.trace("g0_watchdog_failed", reason=str(error),
                           generation=self.cancel_generation)
                if isinstance(error, PulseError):
                    raise InterruptedError(str(error)) from error
                raise
            finally:
                # The child exits before timed_key_pulse returns/raises. A
                # failed release keeps KeySender's held record for cleanup.
                if forward in sender.held:
                    sender.release(forward)

    WatchdogOwnerEngine.__name__ = "WatchdogOwnerEngine"
    return WatchdogOwnerEngine
