"""Offline mode control and queued-action cancellation.

Hotkeys are simulated inputs to this layer. It has no keyboard grab, game
window overlay or command sender. A future live sender must recheck each
permit's cancellation event before every emitted key.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Lock, RLock
from typing import Callable

from .modes import Action, Mode, ModeController, Permit


HOTKEY_MODES = {"F7": Mode.FULL_AUTO, "F8": Mode.ASSIST, "F9": Mode.OFF}


@dataclass(frozen=True)
class ModeIndicator:
    mode: Mode
    generation: int
    text: str
    safety_latched: bool = False


@dataclass(frozen=True)
class DrainResult:
    ready: tuple[QueuedAction, ...]
    dropped: int


@dataclass(frozen=True)
class QueuedAction:
    """An intent and its original permit; recheck before each emitted key."""

    permit: Permit
    action: Action


class ControlPlane:
    def __init__(self, notify: Callable[[ModeIndicator], None] | None = None) -> None:
        self.controller = ModeController()
        self.notify = notify
        self._lock = Lock()
        self._transition_lock = RLock()
        self._queued: deque[QueuedAction] = deque()
        self._safety_latched = False
        self.indicator = ModeIndicator(Mode.OFF, 0, "MODE OFF · generation 0 · startup")
        if notify:
            notify(self.indicator)

    @property
    def safety_latched(self) -> bool:
        with self._transition_lock:
            return self._safety_latched

    def _indicator(self, permit: Permit, reason: str) -> ModeIndicator:
        indicator_text = f"MODE {permit.mode.value.upper()} · generation {permit.generation} · {reason}"
        self.indicator = ModeIndicator(permit.mode, permit.generation, indicator_text,
                                       self._safety_latched)
        return self.indicator

    def _publish(self, indicator: ModeIndicator) -> ModeIndicator:
        if self.notify:
            try:
                self.notify(indicator)
            except Exception as exc:
                # Active mode without its advertised indicator is unsafe.
                with self._transition_lock:
                    permit = self.controller.switch(Mode.OFF)
                    self._safety_latched = True
                    self._indicator(permit, "SAFETY STOP: mode indicator failed")
                raise RuntimeError("Mode indicator failed; safety stop latched OFF") from exc
        return indicator

    def switch(self, mode: Mode, *, reason: str = "command") -> ModeIndicator:
        mode = Mode(mode)
        with self._transition_lock:
            if self._safety_latched and mode != Mode.OFF:
                raise RuntimeError("Safety stop is latched; use 'reset safety' while OFF")
            indicator = self._indicator(self.controller.switch(mode), reason)
        return self._publish(indicator)

    def handle_command(self, command: str) -> ModeIndicator:
        normalized = " ".join(command.strip().casefold().split())
        if normalized in {"mode full", "mode assist", "mode off"}:
            return self.switch(Mode(normalized.split()[1]))
        if normalized == "stop":
            return self.switch(Mode.OFF)
        if normalized == "reset safety":
            with self._transition_lock:
                if self.controller.mode != Mode.OFF:
                    raise RuntimeError("Switch OFF before resetting a safety stop")
                self._safety_latched = False
                indicator = self._indicator(self.controller.permit(), "safety reset")
            return self._publish(indicator)
        if normalized == "status":
            with self._transition_lock:
                return self.indicator
        raise ValueError("Use mode full, mode assist, mode off, stop, reset safety, or status")

    def handle_hotkey(self, key: str) -> ModeIndicator:
        mode = HOTKEY_MODES.get(key.strip().upper())
        if mode is None:
            raise ValueError("Supported simulated keys are F7, F8 and F9")
        return self.switch(mode, reason=f"simulated {key.strip().upper()}")

    def emergency_stop(self, reason: str) -> ModeIndicator:
        if not reason.strip():
            raise ValueError("Safety stop needs a reason")
        # Cancel outstanding permits before touching the queued-action lock.
        with self._transition_lock:
            permit = self.controller.switch(Mode.OFF)
            self._safety_latched = True
            indicator = self._indicator(permit, f"SAFETY STOP: {reason.strip()}")
        return self._publish(indicator)

    def queue(self, action: Action) -> bool:
        permit = self.controller.permit()
        if not self.controller.allows(permit, action):
            return False
        with self._lock:
            self._queued.append(QueuedAction(permit, action))
        return True

    def allows(self, queued: QueuedAction) -> bool:
        """The final check a future sender must repeat before every key."""
        return self.controller.allows(queued.permit, queued.action)

    def drain(self) -> DrainResult:
        ready: list[QueuedAction] = []
        dropped = 0
        with self._lock:
            while self._queued:
                queued = self._queued.popleft()
                if self.allows(queued):
                    ready.append(queued)
                else:
                    dropped += 1
        return DrainResult(tuple(ready), dropped)
