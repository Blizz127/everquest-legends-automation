"""Join current window, input and independently calibrated UI observations.

This is the runtime safety-provider boundary for G2ReadOnlySceneObserver. It
does not classify pixels, infer safety from engine flags, or send game input.
The UI observer is still a required independently validated dependency.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import re
import time
from pathlib import Path

from .g2_scene_observer import G2ObservationUnavailable, G2SafetyObservation, MAX_SAFETY_AGE
from .owner_input_observer import OwnerInputObservation
from .scene_log_veto import SceneLogVeto


@dataclass(frozen=True)
class GameWindowIdentity:
    window_id: int
    pid: int
    start_ticks: int


@dataclass(frozen=True)
class G2UiObservation:
    """Result from the eventual calibrated UI classifier, not a claim it exists.

    Capture must occur within this provider invocation and identify its game
    process/window and approved calibration. All unknown states stay False.
    Transition/incoming-attack flags require the classifier's independent
    current UI/log evidence; one quiet still image alone is insufficient.
    """
    started_at: float
    finished_at: float
    window: GameWindowIdentity
    frame_sha256: str
    calibration_sha256: str
    chat_clear: bool = False
    target_absent: bool = False
    combat_clear: bool = False
    no_transition: bool = False
    no_incoming_attack: bool = False


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _positive_integer(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _identity_valid(window):
    return (isinstance(window, GameWindowIdentity)
            and all(_positive_integer(v) for v in (window.window_id, window.pid, window.start_ticks)))


def _sha(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def focused_game_identity(gate):
    """Use the retained helper WindowGate's read methods, never its grab API."""
    windows = gate.windows()
    focused = gate.focused_window()
    session = gate.game_session()
    if (len(windows) != 1 or focused is None or focused.id != windows[0].id
            or not isinstance(session, dict) or set(session) != {"pid", "start_ticks"}
            or not isinstance(session["start_ticks"], str)
            or re.fullmatch(r"[0-9]+", session["start_ticks"]) is None
            or gate.controls_ready() is not True):
        raise G2ObservationUnavailable("A single focused input-ready game session is required")
    window = GameWindowIdentity(focused.id, session["pid"], int(session["start_ticks"]))
    if not _identity_valid(window):
        raise G2ObservationUnavailable("Invalid focused game identity")
    return window


class G2SafetyProvider:
    """Bracket one new UI observation with complete independent input scans.

    Construct per owner-started measurement, bound to its window/process and
    cancel generation. A first-attach input observation is intentionally not
    clear; the engine must collect its input baseline before arming G2.
    The caller must bind expected_log_path to this window's owner-selected
    character/server. A filename is not proof of the active character. The log
    monitor persists for the whole scope, and supplements rather than replaces
    the independently validated UI classifier. Nothing here authorizes movement
    or bootstraps a zone from log history.
    """
    def __init__(self, *, gate, input_observer, ui_observer, log_veto, expected_log_path, expected_window,
                 calibration_sha256, cancel_generation, generation_reader,
                 mode_reader,
                 clock=time.monotonic):
        if (not _identity_valid(expected_window) or not _sha(calibration_sha256)
                or not isinstance(cancel_generation, int) or isinstance(cancel_generation, bool)
                or cancel_generation < 0 or not callable(generation_reader) or not callable(mode_reader)
                or not callable(ui_observer) or not callable(clock)
                or not callable(getattr(input_observer, "sample", None))
                or not isinstance(log_veto, SceneLogVeto)
                or not isinstance(expected_log_path, Path)
                or log_veto.tail.path != expected_log_path
                or log_veto.cancel_generation != cancel_generation):
            raise ValueError("G2 needs bound current input, UI calibration and cancellation")
        self.gate, self.input_observer, self.ui_observer = gate, input_observer, ui_observer
        self.window, self.calibration = expected_window, calibration_sha256
        self.generation, self.generation_reader = cancel_generation, generation_reader
        self.mode_reader = mode_reader
        self.clock = clock
        self.last_ui = None
        self.log_veto = log_veto
        self.log_path = expected_log_path
        self.last_log_veto = None

    def _check_log(self, began):
        if (self.log_veto.tail.path != self.log_path
                or self.log_veto.cancel_generation != self.generation):
            raise G2ObservationUnavailable("Client log source/generation changed")
        observation = self.log_veto.poll()
        self.last_log_veto = observation
        now = self.clock()
        if (observation.reason is not None or observation.continuity_available is not True
                or observation.cancel_generation != self.generation
                or not all(_finite(v) for v in (observation.started_at, observation.finished_at, now))
                or not began <= observation.started_at <= observation.finished_at <= now
                or now - began > MAX_SAFETY_AGE):
            raise G2ObservationUnavailable(
                f"Client log veto or unavailable continuity: {observation.reason or 'timing/binding'}")

    def _binding(self):
        generation = self.generation_reader()
        if (not isinstance(generation, int) or isinstance(generation, bool)
                or generation != self.generation
                or self.mode_reader() != "measurement"
                or focused_game_identity(self.gate) != self.window):
            raise G2ObservationUnavailable("G2 session or cancellation generation changed")

    def observe_ui(self, ui_observer):
        """Collect a new calibrated frame with input/log/focus bracketing.

        Chat semantics are deliberately left to the caller: a movement check
        requires closed chat, whereas a command key must verify its exact open
        draft. This returns evidence, never a movement or command permit.
        """
        self.last_ui = None
        self.last_log_veto = None
        if not callable(ui_observer):
            raise ValueError('A current independent UI observer is required')
        try:
            began = self.clock()
            if not _finite(began):
                raise G2ObservationUnavailable("Invalid safety observation clock")
            self._binding()
            self._check_log(began)
            self._binding()
            before = self.input_observer.sample()
            input_at = self.clock()
            if (not isinstance(before, OwnerInputObservation) or not _finite(input_at)
                    or before.started_at < began or not before.clear_at(input_at)):
                raise G2ObservationUnavailable("Owner input coverage is incomplete or active")
            visual = ui_observer(self.window)
            after = self.input_observer.sample()
            self._binding()
            self._check_log(began)
            self._binding()
            finished = self.clock()
            if (not _finite(finished) or not 0 <= finished - began <= MAX_SAFETY_AGE
                    or not isinstance(after, OwnerInputObservation)
                    or not after.clear_at(finished)
                    or after.topology_generation != before.topology_generation
                    or not before.clear_at(finished)):
                raise G2ObservationUnavailable("Owner input changed or safety scan expired")
            if (not isinstance(visual, G2UiObservation)
                    or not _finite(visual.started_at) or not _finite(visual.finished_at)
                    or not before.finished_at <= visual.started_at <= visual.finished_at <= after.started_at
                    or visual.window != self.window or not _sha(visual.frame_sha256)
                    or visual.calibration_sha256 != self.calibration
                    or not all(v is True for v in (visual.target_absent,
                                                   visual.combat_clear, visual.no_transition,
                                                   visual.no_incoming_attack))):
                raise G2ObservationUnavailable("Current independently calibrated UI evidence is missing")
            return began, visual
        except G2ObservationUnavailable:
            raise
        except Exception as error:
            raise G2ObservationUnavailable("Independent safety observation failed") from error

    def __call__(self):
        began, visual = self.observe_ui(self.ui_observer)
        if visual.chat_clear is not True:
            raise G2ObservationUnavailable('Current independently calibrated closed chat is missing')
        self.last_ui = visual
        # The oldest observation time is retained, never refreshed to now.
        return G2SafetyObservation(began, focused=True, owner_keys_clear=True,
                                   chat_clear=True, target_absent=True, combat_clear=True,
                                   no_transition=True, no_incoming_attack=True)
