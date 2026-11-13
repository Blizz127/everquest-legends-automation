#!/usr/bin/env python3
"""Inspect one owner-created private HP crop without sending game input.

A red fraction is a diagnostic only. One screenshot cannot prove the owner is
at full HP, that the saved layout is active, or that automatic healing is safe.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from tools.capture_owner_ui import DEFAULT_GAME, DEFAULT_OUTPUT, DEFAULT_PREVIEW, file_sha  # noqa: E402

HP_CROP = "PlayerWindow__Player_HP.png"
HP_KEY = "PlayerWindow__Player_HP"
PREVIEW_HASHES = {
    "rotation_core.py": "9f05379c407f7c9042b38dc7f39c72c0b603bc24d6e754330746f805211a3113",
    "uilayout.py": "d79ec2ae32a31fa642f4b64952996c28d7905efc15fce1d816fc671e552b733a",
}


def private_file(path: Path, root: Path, *, max_bytes: int) -> Path:
    path = path.expanduser()
    resolved = path.resolve()
    if (path.is_symlink() or not resolved.is_relative_to(root.resolve()) or
            not resolved.is_file() or not 0 < resolved.stat().st_size <= max_bytes):
        raise ValueError("expected a bounded regular file in the private capture store")
    return resolved


def read_capture(capture_dir: Path, *, root: Path = DEFAULT_OUTPUT) -> tuple[dict, Path, str]:
    root = root.expanduser().resolve()
    capture_dir = capture_dir.expanduser()
    directory = capture_dir.resolve()
    if (capture_dir.is_symlink() or not directory.is_relative_to(root) or
            directory == root or not directory.is_dir()):
        raise ValueError("capture folder must be a private observation directory")
    metadata_path = private_file(directory / "metadata.json", directory, max_bytes=1024 * 1024)
    metadata_hash = file_sha(metadata_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if (not isinstance(metadata, dict) or
            metadata.get("format") != "eql-owner-ui-observation-v1" or
            metadata.get("game_input_sent") is not False or
            metadata.get("saved_layout_is_live_verified") is not False or
            not isinstance(metadata.get("crops"), dict) or
            not isinstance(metadata.get("window_size"), list) or
            len(metadata["window_size"]) != 2 or
            any(not isinstance(value, int) or isinstance(value, bool) or
                not 640 <= value <= 7680 for value in metadata["window_size"]) or
            not isinstance(metadata.get("capture_started_utc"), str) or
            not isinstance(metadata.get("capture_ended_utc"), str)):
        raise ValueError("capture metadata is incomplete or not read-only")
    crop = metadata["crops"].get(HP_KEY)
    if (not isinstance(crop, dict) or crop.get("file") != HP_CROP or
            not isinstance(crop.get("box"), list) or len(crop["box"]) != 4 or
            any(not isinstance(value, int) or isinstance(value, bool)
                for value in crop["box"]) or
            not isinstance(crop.get("sha256"), str) or len(crop["sha256"]) != 64):
        raise ValueError("capture lacks an exact HP crop and box")
    x0, y0, x1, y1 = crop["box"]
    width, height = metadata["window_size"]
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height and
            x1 - x0 >= 20 and 5 <= y1 - y0 <= 24):
        raise ValueError("HP crop is not a bounded inner-gauge candidate")
    image_path = private_file(directory / HP_CROP, directory, max_bytes=5 * 1024 * 1024)
    if file_sha(image_path) != crop["sha256"]:
        raise ValueError("HP crop hash changed since capture")
    return metadata, image_path, metadata_hash


def analyze(capture_dir: Path, *, game: Path = DEFAULT_GAME,
            preview: Path = DEFAULT_PREVIEW, character: str = "Legira",
            server: str = "freeport") -> dict:
    metadata, image_path, metadata_hash = read_capture(capture_dir)
    preview = preview.expanduser().resolve()
    if (not preview.is_relative_to((Path.home() / ".local/share/eql-automation/owner-assist").resolve()) or
            not preview.is_dir()):
        raise ValueError("reviewed owner preview is outside its private store")
    for name, expected in PREVIEW_HASHES.items():
        source = preview / name
        if not source.is_file() or source.is_symlink() or file_sha(source) != expected:
            raise ValueError(f"reviewed owner preview source changed: {name}")
    sys.path.insert(0, str(preview))
    import rotation_core
    import uilayout
    if (Path(rotation_core.__file__).resolve() != (preview / "rotation_core.py").resolve() or
            Path(uilayout.__file__).resolve() != (preview / "uilayout.py").resolve()):
        raise ValueError("imported HP reader differs from reviewed preview")
    width, height = metadata["window_size"]
    try:
        layout = uilayout.UiLayout.load(game, character, server,
                                        width=width, height=height)
    except uilayout.UiLayoutError as error:
        raise ValueError(f"saved client UI layout unavailable: {error}") from error
    rect = layout.control("PlayerWindow", "Player_HP")
    expected_box = None if rect is None else [rect.x, rect.y, rect.x + rect.w, rect.y + rect.h]
    saved_box = metadata["crops"][HP_KEY]["box"]
    if expected_box != saved_box:
        raise ValueError("current saved client layout no longer matches captured HP box")
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = 2_000_000
    with Image.open(image_path) as raw:
        if raw.format != "PNG":
            raise ValueError("HP crop is not a PNG image")
        image = raw.convert("RGB")
    if image.size != (saved_box[2] - saved_box[0], saved_box[3] - saved_box[1]):
        raise ValueError("HP crop dimensions disagree with captured box")
    fraction = rotation_core.bar_fraction(image, "red")
    if fraction is not None and (not isinstance(fraction, (int, float)) or
                                 not math.isfinite(fraction) or not 0 <= fraction <= 1):
        raise ValueError("reviewed HP reader returned an invalid fraction")
    if (file_sha(image_path.parent / "metadata.json") != metadata_hash or
            file_sha(image_path) != metadata["crops"][HP_KEY]["sha256"] or
            any(file_sha(preview / name) != expected
                for name, expected in PREVIEW_HASHES.items())):
        raise ValueError("HP crop or reader changed during analysis")
    return {
        "format": "eql-owner-hp-crop-analysis-v1",
        "capture_metadata_sha256": metadata_hash,
        "hp_crop_sha256": metadata["crops"][HP_KEY]["sha256"],
        "capture_started_utc": metadata["capture_started_utc"],
        "capture_ended_utc": metadata["capture_ended_utc"],
        "window_size": metadata["window_size"],
        "hp_box_from_saved_client_layout": saved_box,
        "hp_fraction_observed_unverified": fraction,
        "reason": "red_band_candidate_only" if fraction is not None else "red_band_unrecognized",
        "source_sha256_postcapture_not_revalidated": metadata.get("source_sha256_postcapture"),
        "full_frame_sha256_from_metadata_not_revalidated": metadata.get("frame_rgb_sha256"),
        "saved_layout_live_verified": False,
        "full_health_verified": False,
        "automatic_healing_allowed": False,
        "g2_scene_verified": False,
        "game_input_sent": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-dir", required=True, type=Path)
    parser.add_argument("--game-dir", type=Path, default=DEFAULT_GAME)
    parser.add_argument("--preview-dir", type=Path, default=DEFAULT_PREVIEW)
    parser.add_argument("--character", default="Legira")
    parser.add_argument("--server", default="freeport")
    args = parser.parse_args()
    try:
        print(json.dumps(analyze(args.capture_dir, game=args.game_dir,
                                 preview=args.preview_dir, character=args.character,
                                 server=args.server), sort_keys=True))
    except (OSError, ValueError, RuntimeError, ImportError, json.JSONDecodeError) as error:
        parser.exit(1, f"HP crop analysis refused: {error}\n")


if __name__ == "__main__":
    main()
