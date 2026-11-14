"""Discard inactive/settings-era gauge readings in the existing assist helper.

This fixes cache lifetime only. The inherited reader still needs a correctly
calibrated, current game frame; invalidation does not establish that binding.
"""
from __future__ import annotations

from .owner_nov12_recovery import make_owner_nov12_engine as recovery_engine


def make_owner_nov12_engine(base_engine: type) -> type:
    class FreshGaugeOwnerEngine(recovery_engine(base_engine)):
        def _invalidate_gauges(self):
            self.hp = self.mana = None
            # The inherited loop samples before combat_tick. Make that sample
            # due even when its idle loop recently advanced last_gauge.
            self.last_gauge = float("-inf")

        def stop_action(self, reason, *, keep_autopilot=False):
            # Invalidate before cleanup: a release exception cannot preserve
            # stale healing/mana decisions for the next owner start request.
            self._invalidate_gauges()
            return super().stop_action(reason, keep_autopilot=keep_autopilot)

        def handle_job(self, name, value):
            if name == "settings" or name == "arm" and not self.active:
                self._invalidate_gauges()
            # Explicit F10 is independent of automatic HP decisions.
            return super().handle_job(name, value)

    FreshGaugeOwnerEngine.__name__ = "FreshGaugeOwnerEngine"
    return FreshGaugeOwnerEngine
