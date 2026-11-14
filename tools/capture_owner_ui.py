"""Owner-run, read-only EQL UI observation for later G2 calibration.

This script never sends keys, clicks, commands or game input. A capture labels
what the owner says was on screen; it does not infer that a safety gate is clear.
Only crops are written, under the owner's private data directory.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eql_automation.owner_ui_observation import (
    DEFAULT_OUTPUT, WINDOWS, CONTROLS, file_sha, box_of, validate_request,
    capture_focused_ui,
)

PREVIEW_HASHES = {
    "rotation_engine.py": "d6ec143920a6748364eb27fa6e279aaf45763b8345fe8e81d7c171648561927f",
    "uilayout.py": "d79ec2ae32a31fa642f4b64952996c28d7905efc15fce1d816fc671e552b733a",
}
DEFAULT_PREVIEW = Path.home() / ".local/share/eql-automation/owner-assist/0.39.4"
DEFAULT_GAME = (Path.home() / "Games/everquest-legends/drive_c/users/Public/"
                "Daybreak Game Company/Installed Games/EverQuest Legends")


def checked_preview(preview: Path) -> None:
    if not preview.is_dir() or preview.is_symlink():
        raise RuntimeError("Reviewed owner preview 0.39.4 is missing")
    for name, expected in PREVIEW_HASHES.items():
        path = preview / name
        if not path.is_file() or path.is_symlink() or file_sha(path) != expected:
            raise RuntimeError(f"Reviewed owner preview file changed: {name}")


def capture(*, label: str, delay: float, preview: Path, game: Path,
            character: str, server: str, output: Path, include_chat: bool = True) -> Path:
    validate_request(label, character, server, output, DEFAULT_OUTPUT)
    if not 0 <= delay <= 15:
        raise ValueError("Delay must be between 0 and 15 seconds")
    checked_preview(preview)
    sys.path.insert(0, str(preview))
    from rotation_engine import WindowGate
    from uilayout import UiLayout
    print(f"Focus EverQuest now; read-only capture in {delay:g} seconds.", flush=True)
    time.sleep(delay)
    gate = WindowGate()
    try:
        return capture_focused_ui(label=label, gate=gate, layout_loader=UiLayout.load,
            game=game, character=character, server=server, output=output,
            include_chat=include_chat, private_root=DEFAULT_OUTPUT)
    finally:
        gate.display.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True, help="owner-described visible state, e.g. idle")
    parser.add_argument("--delay", type=float, default=5.0,
                        help="seconds to switch focus to the game (0–15; default 5)")
    parser.add_argument("--character", default="Legira")
    parser.add_argument("--server", default="freeport")
    parser.add_argument("--preview-dir", type=Path, default=DEFAULT_PREVIEW)
    parser.add_argument("--game-dir", type=Path, default=DEFAULT_GAME)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        capture(label=args.label, delay=args.delay, preview=args.preview_dir,
                game=args.game_dir, character=args.character, server=args.server,
                output=args.output_dir)
    except (OSError, RuntimeError, ValueError) as error:
        parser.exit(1, f"UI observation refused: {error}\n")


if __name__ == "__main__":
    main()
