"""Owner-run, read-only EQL UI observation for later G2 calibration.

This script never sends keys, clicks, commands or game input. A capture labels
what the owner says was on screen; it does not infer that a safety gate is clear.
Only crops are written, under the owner's private data directory.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
import time


PREVIEW_HASHES = {
    "rotation_engine.py": "d6ec143920a6748364eb27fa6e279aaf45763b8345fe8e81d7c171648561927f",
    "uilayout.py": "d79ec2ae32a31fa642f4b64952996c28d7905efc15fce1d816fc671e552b733a",
}
DEFAULT_PREVIEW = Path.home() / ".local/share/eql-automation/owner-assist/0.39.4"
DEFAULT_GAME = (Path.home() / "Games/everquest-legends/drive_c/users/Public/"
                "Daybreak Game Company/Installed Games/EverQuest Legends")
DEFAULT_OUTPUT = Path.home() / ".local/share/eql-automation/g2-ui-observations"
WINDOWS = ("PlayerWindow", "TargetWindow", "MainChat")
CONTROLS = (
    ("PlayerWindow", "Player_HP"),
    ("PlayerWindow", "Player_Mana"),
    ("PlayerWindow", "PW_CombatStateAnim"),
    ("TargetWindow", "Target_HP"),
    ("TargetWindow", "Target_Class"),
    ("TargetWindow", "Target_Level"),
)


def file_sha(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checked_preview(preview: Path) -> None:
    if not preview.is_dir() or preview.is_symlink():
        raise RuntimeError("Reviewed owner preview 0.39.4 is missing")
    for name, expected in PREVIEW_HASHES.items():
        path = preview / name
        if not path.is_file() or path.is_symlink() or file_sha(path) != expected:
            raise RuntimeError(f"Reviewed owner preview file changed: {name}")


def box_of(rect, image) -> tuple[int, int, int, int] | None:
    if rect is None or not all(isinstance(n, int) for n in
                               (rect.x, rect.y, rect.w, rect.h)):
        return None
    box = (rect.x, rect.y, rect.x + rect.w, rect.y + rect.h)
    if rect.w <= 0 or rect.h <= 0 or not (0 <= box[0] < box[2] <= image.width and
                                          0 <= box[1] < box[3] <= image.height):
        return None
    return box


def capture(*, label: str, delay: float, preview: Path, game: Path,
            character: str, server: str, output: Path) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", label):
        raise ValueError("Label must contain only letters, numbers, _ or -")
    if not 0 <= delay <= 15:
        raise ValueError("Delay must be between 0 and 15 seconds")
    checked_preview(preview)
    sys.path.insert(0, str(preview))
    from rotation_engine import WindowGate  # owner preview; no input object created
    from uilayout import UiLayout

    print(f"Focus EverQuest now; read-only capture in {delay:g} seconds.", flush=True)
    time.sleep(delay)
    gate = WindowGate()
    try:
        windows = gate.windows()
        focused = gate.focused_window()
        session = gate.game_session()
        if len(windows) != 1 or focused is None or focused.id != windows[0].id or session is None:
            raise RuntimeError("Exactly one focused EverQuest window and process are required")
        image = gate.capture()
        if (gate.focused_window() is None or gate.focused_window().id != focused.id or
                gate.game_session() != session):
            raise RuntimeError("Game focus or process changed during capture")
    finally:
        gate.display.close()

    layout = UiLayout.load(game, character, server,
                           width=image.width, height=image.height)
    crops = {}
    for name in WINDOWS:
        crops[name] = box_of(layout.window(name), image)
    for window, control in CONTROLS:
        crops[f"{window}__{control}"] = box_of(layout.control(window, control), image)
    if crops["PlayerWindow__Player_HP"] is None:
        raise RuntimeError("Current client files did not resolve the player HP rectangle")
    if not any(crops[name] is not None for name in WINDOWS):
        raise RuntimeError("Current client files did not resolve an on-screen window")

    os.umask(0o077)
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = output / f"{stamp}-{time.time_ns()}-{label}"
    dest.mkdir(mode=0o700)
    saved = {}
    for name, box in crops.items():
        if box is None:
            continue
        path = dest / f"{name}.png"
        image.crop(box).save(path)
        saved[name] = {"box": list(box), "file": path.name,
                       "sha256": file_sha(path)}
    sources = {str(path): file_sha(path)
               for path in (game / "eqclient.ini", *layout.sources.values())
               if path.is_file()}
    ui_ini = sorted(game.glob(f"UI_{character}_{server}*.ini"))
    if len(ui_ini) == 1:
        sources[str(ui_ini[0])] = file_sha(ui_ini[0])
    metadata = {
        "format": "eql-owner-ui-observation-v1",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "owner_label_unverified": label,
        "game_input_sent": False,
        "g2_safety_flags": {name: "unknown" for name in
                            ("chat_clear", "target_absent", "combat_clear",
                             "native_melee_off", "no_incoming_attack")},
        "game_session": session,
        "focused_window_id": focused.id,
        "window_size": list(image.size),
        "frame_rgb_sha256": sha256(image.tobytes()).hexdigest(),
        "ui_skin_from_saved_ini": layout.skin,
        "ui_scale_from_saved_ini": layout.ui_scale,
        "source_sha256": sources,
        "crops": saved,
        "missing_or_offscreen_crops": [name for name, box in crops.items() if box is None],
    }
    (dest / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(f"Read-only private UI observation: {dest}", flush=True)
    print("All G2 safety flags remain unknown until paired live states are reviewed.", flush=True)
    return dest


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
