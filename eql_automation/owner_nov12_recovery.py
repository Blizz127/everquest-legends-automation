"""Owner-confirmed local draft recovery for the isolated assist preview.

No input is sent by recovery. The owner closes game chat themselves, confirms
that fact while stopped, and must make a fresh F8/F6/F10 request afterwards.
"""
from __future__ import annotations

from .owner_nov12_adapter import make_owner_nov12_engine as restricted_engine


_START_JOBS = frozenset({"arm", "prepare", "prepare_later", "heal"})
_DRAFT_HELP = (
    "Assist OFF · close the game chat draft yourself, then use Chat recovery "
    "in the helper; F8 resumes only after that confirmation."
)


def make_owner_nov12_engine(base_engine: type) -> type:
    class RecoverableOwnerEngine(restricted_engine(base_engine)):
        def post(self, name, value=None):
            if name in _START_JOBS and value is None:
                value = self.cancel_generation
            return super().post(name, value)

        def handle_job(self, name, value):
            if name == "owner_chat_closed":
                return self.confirm_chat_closed(value)
            if name in _START_JOBS:
                # In particular, a queued GUI preparation must not survive F9.
                if type(value) is not int or value != self.cancel_generation:
                    return None
                if self.sender and self.sender.unfinished:
                    self.emit(_DRAFT_HELP)
                    return None
            return super().handle_job(name, value)

        def recover_interrupted_command(self):
            if self.command_recovery_pending:
                self.stop_action(_DRAFT_HELP)
                return False
            return super().recover_interrupted_command()

        def confirm_chat_closed(self, value):
            # A GUI confirmation from before another stop/focus/chat event is
            # stale. Never infer consent from Escape, Enter, or a timeout.
            if (not isinstance(value, dict) or value.get("chat_closed") is not True
                    or type(value.get("generation")) is not int
                    or value["generation"] != self.cancel_generation):
                self.emit("Chat recovery not applied: confirm again while assist is stopped.")
                return False
            if (self.active or self.preparing or self.stopping or self.measurement_only
                    or self.autopilot is not None or self.pointer is not None
                    or self.keys or self.sender and self.sender.held):
                self.emit("Chat recovery not applied: stop assist and release all keys first.")
                return False
            if self.sender is None or not self.sender.unfinished:
                self.emit("No interrupted helper draft is pending. Assist stays OFF.")
                return False

            # Only local bookkeeping changes here. No stop/release, sender or
            # game-window method is called; uncertain held keys refuse above.
            self.cancel_generation += 1
            self.cancelled = True
            self.deferred = None
            self.command_recovery_pending = False
            self.stopped_mid_command = False
            self.sender.unfinished = False
            self.sender.dismissed = False
            self.reset_target(False, forget=True, clear_seen=True, clear_role=True)
            self.native_attack_off_pending = False
            self.trace("owner_chat_closed", generation=self.cancel_generation,
                       owner_confirmed=True, game_input_sent=False, active=False)
            self.emit("Assist OFF · chat closure confirmed · focus the game and press F8 when ready.")
            return True

    RecoverableOwnerEngine.__name__ = "RecoverableOwnerEngine"
    return RecoverableOwnerEngine
