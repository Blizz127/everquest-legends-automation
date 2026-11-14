"""Owner-run /location plus UI diagnostic. Sends no game commands or input.

The owner types /location and closes chat. The result remains unbound to a
zone or navigation frame and cannot authorize movement. No chat crop is saved.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from math import isfinite
from pathlib import Path
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eql_automation.unbound_location_log import UnboundLocationReader
from tools.capture_owner_ui import (
    DEFAULT_GAME, DEFAULT_OUTPUT, DEFAULT_PREVIEW, capture, checked_preview, file_sha,
)


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


def collect(*, label, timeout, settle, preview, game, character, server, output,
            gate_factory=None, capture_fn=capture, clock=time.monotonic, sleep=time.sleep):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", label):
        raise ValueError("Invalid observation label")
    if not all(re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value)
               for value in (character, server)):
        raise ValueError("Invalid character/server identifier")
    if not 1 <= timeout <= 120 or not 0 <= settle <= 5:
        raise ValueError("Wait must be 1–120 seconds and settle 0–5 seconds")
    if not output.resolve().is_relative_to(DEFAULT_OUTPUT.resolve()):
        raise ValueError("Output must stay in the private G2 UI observation store")
    if gate_factory is None:
        checked_preview(preview)
        sys.path.insert(0, str(preview))
        from rotation_engine import WindowGate
        gate_factory = WindowGate
    gate = gate_factory()
    try:
        expected, _ = identity(gate)
        log = game / "Logs" / f"eqlog_{character}_{server}.txt"
        reader = UnboundLocationReader(log, expected_character=character,
                                       expected_server=server)
        started = clock()
        print("Stand still with the map on Current Zone. In EverQuest, type /location once, "
              "press Enter, then close chat and leave the game focused. No input is sent by this tool.",
              flush=True)
        fix = None
        while clock() - started < timeout:
            before_focus = require_identity(gate, expected)
            observations = reader.poll(now=clock())
            after_focus = require_identity(gate, expected)
            if observations:
                if len(observations) != 1 or not (before_focus and after_focus):
                    raise ValueError("A single new location with sampled game focus is required")
                fix = observations[0]
                break
            sleep(.1)
        if fix is None:
            raise ValueError("No fresh /location arrived before the observation timeout")
        dest = capture_fn(label=label, delay=settle, preview=preview, game=game,
                          character=character, server=server, output=output,
                          include_chat=False)
        # A transition/reset after the selected line invalidates the pair, even
        # if the UI capture itself completed. Raw crops are never a movement permit.
        require_identity(gate, expected, focused=True)
        if reader.poll(now=clock()):
            raise ValueError("Another location arrived during capture; pair is ambiguous")
        require_identity(gate, expected, focused=True)
        checked_at = clock()
        metadata_path = dest / "metadata.json"
        metadata = json.loads(metadata_path.read_text())
        validate_pair(fix, expected, metadata, checked_at)
        raw = asdict(fix)
        raw["log_local_time"] = fix.log_local_time.isoformat()
        record = {
            "format": "eql-unbound-location-ui-v1",
            "location": raw,
            "expected_character": character, "expected_server": server,
            "character_identity_verified": False,
            "source_log_identity": list(reader.tail.identity),
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
        with (dest / "unbound-location.json").open("x") as target:
            target.write(json.dumps(record, indent=2, sort_keys=True) + "\n")
        print(f"Unbound location/UI diagnostic saved: {dest}. Movement remains disabled.", flush=True)
        return dest
    finally:
        gate.display.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="current-zone-location")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--settle", type=float, default=2)
    parser.add_argument("--character", default="Legira")
    parser.add_argument("--server", default="freeport")
    parser.add_argument("--preview-dir", type=Path, default=DEFAULT_PREVIEW)
    parser.add_argument("--game-dir", type=Path, default=DEFAULT_GAME)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        collect(label=args.label, timeout=args.timeout, settle=args.settle,
                preview=args.preview_dir, game=args.game_dir, character=args.character,
                server=args.server, output=args.output_dir)
    except (OSError, RuntimeError, ValueError) as error:
        parser.exit(1, f"Location/UI observation refused: {error}\n")


if __name__ == "__main__":
    main()
