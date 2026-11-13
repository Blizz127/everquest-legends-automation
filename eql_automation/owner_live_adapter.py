"""Narrow owner-run adaptation of the October Paladin/Cleric helper.

This does not log in, launch the game, move, select targets, or send input by
itself. The owner explicitly starts the helper on Alienware. The adaptation
keeps autoattack manual and never auto-prepares on F8. The older chat sender
and target observation limitations still apply; this is not strict ASSIST.
"""
from __future__ import annotations

import re


_PREP_COMMAND = re.compile(
    r"/(?:outputfile spellbook eql-rotation-spellbook\.txt|memspellslot [1-8] \d+)\Z")
_ROTATION_COMMAND = re.compile(
    r"/(?:cast [1-8]|doability (?:Bash|Smite)|alt activate 6001)\Z")


def make_owner_rotation_engine(base_engine: type) -> type:
    """Return an attack-free engine subclass using the reviewed October base."""

    class OwnerRotationEngine(base_engine):
        def stop_action(self, reason):
            return super().stop_action(f"Rotation OFF · {reason}")

        def send(self, command: str):
            if command in {"/attack on", "/attack off"}:
                return  # The game autoattack state stays under the owner.
            if not isinstance(command, str):
                raise ValueError("Rotation command must be text")
            permitted = (_PREP_COMMAND.fullmatch(command) if self.preparing else
                         _ROTATION_COMMAND.fullmatch(command))
            if permitted is None:
                raise ValueError("Command is outside this owner's rotation-only input scope")
            return super().send(command)

        def handle_job(self, name, value):
            if name == "attack_off":
                return  # F8/F9 stop only this helper, never the game's attack.
            if name == "arm":
                if isinstance(value, int) and value != self.cancel_generation:
                    return
                if not self.prepared or self.prepared_level != self.settings.level:
                    self.emit("Press F6 out of combat to prepare gems explicitly, then F8 for rotation.")
                    return
            result = super().handle_job(name, value)
            if name == "arm" and self.active:
                self.emit("Rotation ON · autoattack manual · F8 stop · F9 cancel")
            return result

        def input_events(self):
            # The inherited code clears KeySender.unfinished on a physical
            # Escape/Enter even when it cannot prove the game chat draft is
            # closed. Preserve the uncertainty for the rest of this process.
            uncertain = bool(self.sender and self.sender.unfinished)
            result = super().input_events()
            if uncertain and self.sender and not self.sender.unfinished:
                self.sender.unfinished = True
            return result

    OwnerRotationEngine.__name__ = "OwnerRotationEngine"
    return OwnerRotationEngine
