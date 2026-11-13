"""Owner-run, attack-free assist adapter for the pinned November helper.

The owner starts this only from an isolated source snapshot on Alienware.
It never starts F11, records F12 routes, selects targets, moves, or controls
native melee. The inherited chat and target-observation gaps still prevent
claiming this as fully verified strict ASSIST.
"""
from __future__ import annotations

import re


_PREP = re.compile(
    r"/(?:outputfile spellbook eql-rotation-spellbook\.txt|memspellslot [1-8] \d+)\Z")
_ROTATION = re.compile(
    r"/(?:cast [1-8]|doability (?:Bash|Smite)|alt activate 6001)\Z")
_ROUTE_JOBS = frozenset({
    "record_point", "record_start", "record_finish", "record_undo",
    "record_cancel", "route_delete", "route_reversible", "anchor_here",
})
_AUTOPILOT_JOBS = frozenset({
    "autopilot_start", "autopilot_later", "nav_calibrate",
    "nav_stop_check", "nav_calibrate_later", "nav_stop_check_later",
})


def make_owner_nov12_engine(base_engine: type) -> type:
    """Restrict the November engine to supervised, owner-targeted rotation."""

    class OwnerNov12Engine(base_engine):
        def send(self, command: str):
            if command in {"/attack on", "/attack off"}:
                return None  # The owner alone controls native melee.
            if not isinstance(command, str):
                raise ValueError("Rotation command must be text")
            permitted = (command == "/consider" or
                         bool(_PREP.fullmatch(command)) and self.preparing or
                         bool(_ROTATION.fullmatch(command)))
            if not permitted:
                raise ValueError("Command is outside this owner's rotation scope")
            if self.sender is not None and self.sender.unfinished:
                raise InterruptedError("Uncertain game chat draft; stop and clear it manually")
            return super().send(command)

        def flush_native_attack_off(self):
            # The helper never owns native melee in this preview. Avoid the
            # inherited blind chat Escape and unsupported/unconfirmed off job.
            self.native_attack_off_pending = False
            self.attack_started = False
            return True

        def handle_job(self, name, value):
            if name in _ROUTE_JOBS or name in _AUTOPILOT_JOBS:
                self.emit("Rotation only · F11 movement and F12 routes disabled in this preview")
                return None
            if name == "attack_off":
                return None  # F9 stops rotation; melee remains owner-controlled.
            return super().handle_job(name, value)

        def stop_action(self, reason, *, keep_autopilot=False):
            return super().stop_action(
                f"Rotation OFF · melee is manual · {reason}",
                keep_autopilot=False,
            )

        def recover_interrupted_command(self):
            if self.command_recovery_pending:
                self.stop_action("Uncertain chat draft; close it manually before F8")
                return False
            return super().recover_interrupted_command()

        def input_events(self):
            # Physical Enter/Escape do not prove a helper-owned draft cleared.
            uncertain = bool(self.sender and self.sender.unfinished)
            result = super().input_events()
            if uncertain and self.sender and not self.sender.unfinished:
                self.sender.unfinished = True
            return result

    OwnerNov12Engine.__name__ = "OwnerNov12Engine"
    return OwnerNov12Engine
