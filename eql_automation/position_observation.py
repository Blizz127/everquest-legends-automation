"""Tick-driven, owner-requested position/UI diagnostics with no input authority."""
from dataclasses import asdict
import json
from math import isfinite
from pathlib import Path
import time

from .unbound_location_log import UnboundLocationReader
from .owner_ui_observation import DEFAULT_OUTPUT, file_sha, validate_request


def identity(gate):
    windows = gate.windows()
    session = gate.game_session()
    focus = gate.focused_window()
    if len(windows) != 1 or session is None:
        raise ValueError("Exactly one EverQuest window and process are required")
    return {"window_id": windows[0].id, "game_session": session}, (
        focus is not None and focus.id == windows[0].id)


def require_identity(gate, expected, *, focused=False):
    actual, has_focus = identity(gate)
    if actual != expected or (focused and not has_focus):
        raise ValueError("Game window, process or required focus changed")
    return has_focus


def validate_pair(fix, expected, metadata, checked_at):
    if (metadata.get("game_session") != expected["game_session"] or
            metadata.get("focused_window_id") != expected["window_id"]):
        raise ValueError("Captured window/process differs from the location observation")
    start = metadata.get("capture_started_monotonic")
    end = metadata.get("capture_ended_monotonic")
    if not all(isinstance(n, (float, int)) and not isinstance(n, bool) and isfinite(n)
               for n in (start, end, checked_at, fix.received_monotonic)):
        raise ValueError("Capture timing is missing or invalid")
    if not fix.received_monotonic <= start <= end <= checked_at:
        raise ValueError("Location/capture timing order changed")
    if checked_at - fix.received_monotonic > 10:
        raise ValueError("Location receipt is too old for this diagnostic pair")
    if (metadata.get("game_input_sent") is not False or
            metadata.get("chat_crop_included") is not False or
            "MainChat" in metadata.get("crops", {})):
        raise ValueError("Capture does not satisfy the input-free, no-chat-crop contract")


def save_pair(*, fix, expected, metadata, dest, checked_at, started, log_identity,
              character, server, still_current=lambda: None):
    validate_pair(fix, expected, metadata, checked_at)
    metadata_path = dest / "metadata.json"
    raw = asdict(fix)
    raw["log_local_time"] = fix.log_local_time.isoformat()
    record = {
        "format": "eql-unbound-location-ui-v1",
        "location": raw,
        "expected_character": character, "expected_server": server,
        "character_identity_verified": False,
        "source_log_identity": list(log_identity),
        "observation_started_monotonic": started,
        "post_capture_checked_monotonic": checked_at,
        "ui_metadata_sha256": file_sha(metadata_path),
        "game_input_sent": False,
        "owner_held_still_verified": False,
        "log_flush_delay_verified": False,
        "continuous_focus_verified": False,
        "live_route_accepted": False,
        "note": "Newly appended log bytes and sampled focus only; no zone, alignment or command correlation proof.",
    }
    still_current()
    pair_path = dest / "unbound-location.json"
    with pair_path.open("x") as target:
        target.write(json.dumps(record, indent=2, sort_keys=True) + "\n")
    pair_path.chmod(0o600)
    try:
        still_current()
    except Exception:
        pair_path.rename(dest / "cancelled-unbound-location.json")
        raise
    return pair_path


class StationaryPositionSession:
    """Borrow the engine's gate. The owner types /location; ticks never send it."""
    def __init__(self, *, gate, game, character, server, output, capture_fn,
                 still_current=lambda: None, clock=time.monotonic,
                 timeout=60., settle=2., private_root=DEFAULT_OUTPUT):
        self.label = "current-zone-location"
        validate_request(self.label, character, server, output, private_root)
        if not 1 <= timeout <= 120 or not 0 <= settle <= 5:
            raise ValueError("Invalid collection timing")
        self.gate, self.game = gate, Path(game)
        self.character, self.server, self.output = character, server, output
        self.capture_fn, self.still_current, self.clock = capture_fn, still_current, clock
        self.timeout, self.settle = timeout, settle
        self.started = self.last_at = clock()
        if not isfinite(self.started): raise ValueError("Invalid observation clock")
        self.fix = None
        self.phase = "waiting"
        still_current()
        self.expected, _ = identity(gate)
        self.reader = UnboundLocationReader(self.game / "Logs" / f"eqlog_{character}_{server}.txt",
            expected_character=character, expected_server=server)

    def cancel(self):
        self.phase = "cancelled"

    def check(self, *, focused=False):
        if self.phase not in ("waiting", "settling", "capturing"):
            raise ValueError("Position observation is no longer active")
        self.still_current()
        now = self.clock()
        if not isfinite(now) or now < self.last_at:
            raise ValueError("Observation clock moved backward or became invalid")
        self.last_at = now
        if self.fix is None and now - self.started >= self.timeout:
            raise ValueError("No fresh /location arrived before the observation timeout")
        if self.fix is not None and now - self.fix.received_monotonic > 10:
            raise ValueError("Location receipt is too old for this diagnostic pair")
        return require_identity(self.gate, self.expected, focused=focused)

    def tick(self):
        try:
            return self._tick()
        except Exception:
            self.phase = "refused"
            raise

    def _tick(self):
        before_focus = self.check()
        found = self.reader.poll(now=self.clock())
        after_focus = self.check()
        if self.phase == "waiting":
            if not found: return None
            if len(found) != 1 or not (before_focus and after_focus):
                raise ValueError("A single new location with sampled game focus is required")
            self.fix = found[0]
            self.due = self.clock() + self.settle
            self.phase = "settling"
            return None
        if found:
            raise ValueError("Another location arrived during collection; pair is ambiguous")
        if self.clock() < self.due: return None
        self.check(focused=True)
        self.phase = "capturing"
        dest = self.capture_fn(label=self.label, gate=self.gate, game=self.game,
            character=self.character, server=self.server, output=self.output,
            still_current=lambda: self.check(focused=True), clock=self.clock)
        self.check(focused=True)
        if self.reader.poll(now=self.clock()):
            raise ValueError("Another location arrived during capture; pair is ambiguous")
        self.check(focused=True)
        checked_at = self.clock()
        metadata = json.loads((dest / "metadata.json").read_text())
        save_pair(fix=self.fix, expected=self.expected, metadata=metadata, dest=dest,
            checked_at=checked_at, started=self.started, log_identity=self.reader.tail.identity,
            character=self.character, server=self.server,
            still_current=lambda: self.check(focused=True))
        self.phase = "done"
        return dest
