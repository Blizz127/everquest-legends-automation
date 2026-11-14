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
WINDOWS = ("PlayerWindow", "TargetWindow", "MainChat", "MapViewWnd")
CONTROLS = (
    ("PlayerWindow", "Player_HP"),
    ("PlayerWindow", "Player_Mana"),
    ("PlayerWindow", "PW_CombatStateAnim"),
    ("TargetWindow", "Target_HP"),
    ("TargetWindow", "Target_Class"),
    ("TargetWindow", "Target_Level"),
    ("MapViewWnd", "MRA_ZoneLabel"),
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
            character: str, server: str, output: Path, include_chat: bool = True) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", label):
        raise ValueError("Label must contain only letters, numbers, _ or -")
    if not 0 <= delay <= 15:
        raise ValueError("Delay must be between 0 and 15 seconds")
    if not all(re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value)
               for value in (character, server)):
        raise ValueError("Character/server must contain only letters, numbers, _ or -")
    private_root = DEFAULT_OUTPUT.resolve()
    protected_prefix = (Path.home() / "Games/everquest-legends").resolve()
    if (private_root.is_relative_to(protected_prefix) or
            not output.resolve().is_relative_to(private_root)):
        raise ValueError("Output must stay in the private G2 UI observation store")
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
        capture_started_utc = datetime.now(timezone.utc).isoformat()
        capture_started_monotonic = time.monotonic()
        image = gate.capture()
        capture_ended_monotonic = time.monotonic()
        capture_ended_utc = datetime.now(timezone.utc).isoformat()
        final_focus = gate.focused_window()
        if (final_focus is None or final_focus.id != focused.id or
                gate.game_session() != session):
            raise RuntimeError("Game focus or process changed during capture")
    finally:
        gate.display.close()

    layout = UiLayout.load(game, character, server,
                           width=image.width, height=image.height)
    crops = {}
    for name in WINDOWS:
        if name == "MainChat" and not include_chat:
            continue
        crops[name] = box_of(layout.window(name), image)
    for window, control in CONTROLS:
        crops[f"{window}__{control}"] = box_of(layout.control(window, control), image)
    if crops["PlayerWindow__Player_HP"] is None:
        raise RuntimeError("Current client files did not resolve the player HP rectangle")
    if not any(crops.get(name) is not None for name in WINDOWS):
        raise RuntimeError("Current client files did not resolve an on-screen window")

    ini_exact = game / f"UI_{character}_{server}.ini"
    ui_ini = [ini_exact] if ini_exact.is_file() else sorted(game.glob(f"UI_{character}_{server}_*.ini"))
    source_paths = {game / "eqclient.ini", *layout.sources.values(), *ui_ini}
    sources = {str(path): file_sha(path) for path in source_paths if path.is_file()}

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
    if sources != {str(path): file_sha(path) for path in source_paths if path.is_file()}:
        raise RuntimeError("Client UI files changed while writing the observation")
    metadata = {
        "format": "eql-owner-ui-observation-v1",
        "capture_started_utc": capture_started_utc,
        "capture_ended_utc": capture_ended_utc,
        "capture_started_monotonic": capture_started_monotonic,
        "capture_ended_monotonic": capture_ended_monotonic,
        "capture_duration_monotonic_seconds": capture_ended_monotonic - capture_started_monotonic,
        "metadata_written_at_utc": datetime.now(timezone.utc).isoformat(),
        "owner_label_unverified": label,
        "game_input_sent": False,
        "chat_crop_included": include_chat,
        "g2_safety_flags": {name: "unknown" for name in
                            ("chat_clear", "target_absent", "combat_clear",
                             "native_melee_off", "no_incoming_attack")},
        "game_session": session,
        "focused_window_id": focused.id,
        "window_size": list(image.size),
        "frame_rgb_sha256": sha256(image.tobytes()).hexdigest(),
        "ui_skin_from_saved_ini": layout.skin,
        "ui_scale_from_saved_ini": layout.ui_scale,
        "source_sha256_postcapture": sources,
        "saved_layout_is_live_verified": False,
        # The map can browse other zones. A captured label alone is not a
        # current-zone observation, even if it matches a historical log line.
        "map_label_is_current_zone_verified": False,
        "map_label_requires_current_zone_selection": True,
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
