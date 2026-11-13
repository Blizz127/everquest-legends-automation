import json
from pathlib import Path

from PIL import Image
import pytest

from tools.analyze_owner_hp_capture import HP_CROP, HP_KEY, read_capture
from tools.capture_owner_ui import file_sha


def make_capture(tmp_path: Path, *, height: int = 17) -> tuple[Path, Path]:
    root = tmp_path / "private"
    folder = root / "owner-observation"
    folder.mkdir(parents=True)
    image = folder / HP_CROP
    Image.new("RGB", (330, height), (150, 0, 0)).save(image)
    metadata = {
        "format": "eql-owner-ui-observation-v1",
        "game_input_sent": False,
        "saved_layout_is_live_verified": False,
        "capture_started_utc": "2026-11-13T23:00:00+00:00",
        "capture_ended_utc": "2026-11-13T23:00:01+00:00",
        "window_size": [2560, 1600],
        "crops": {HP_KEY: {"file": HP_CROP,
                          "box": [1966, 693, 2296, 693 + height],
                          "sha256": file_sha(image)}},
    }
    (folder / "metadata.json").write_text(json.dumps(metadata))
    return root, folder


def test_exact_private_hp_crop_is_read_but_not_accepted_as_live_hp(tmp_path):
    root, folder = make_capture(tmp_path)
    metadata, image, metadata_hash = read_capture(folder, root=root)
    assert image == folder / HP_CROP
    assert metadata["saved_layout_is_live_verified"] is False
    assert metadata_hash == file_sha(folder / "metadata.json")


def test_crop_hash_or_inner_gauge_height_change_refuses(tmp_path):
    root, folder = make_capture(tmp_path)
    Image.new("RGB", (330, 17), (0, 0, 150)).save(folder / HP_CROP)
    with pytest.raises(ValueError, match="hash changed"):
        read_capture(folder, root=root)
    root2, folder2 = make_capture(tmp_path / "second", height=51)
    with pytest.raises(ValueError, match="inner-gauge"):
        read_capture(folder2, root=root2)


def test_symlink_or_metadata_path_traversal_refuses(tmp_path):
    root, folder = make_capture(tmp_path)
    shortcut = root / "shortcut"
    shortcut.symlink_to(folder, target_is_directory=True)
    with pytest.raises(ValueError, match="private observation"):
        read_capture(shortcut, root=root)
    metadata_file = folder / "metadata.json"
    metadata = json.loads(metadata_file.read_text())
    metadata["crops"][HP_KEY]["file"] = "../other.png"
    metadata_file.write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match="exact HP crop"):
        read_capture(folder, root=root)
