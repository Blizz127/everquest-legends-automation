"""Owner-started Alienware preview using the reviewed October GUI and engine.

This entry never starts EverQuest Legends or logs in. It refuses an unknown
October helper source revision and applies the attack-free engine adapter
before that helper creates any input device or GUI worker.
"""
from __future__ import annotations

from hashlib import sha256
import importlib
from pathlib import Path
import sys

from .owner_live_adapter import make_owner_rotation_engine


LEGACY_SOURCE_HASHES = {
    "rotation_core.py": "bdd5203bbf87563039799f7dd228480a517fca8dd4550d53b6559506a56875fa",
    "rotation_engine.py": "8e32a72eb7f87dae9901f84841679fdb628c46fab7458de216bfdff9fe567683",
    "eql_rotation.py": "95b4251558ecd1a5c31d9e12f2d71c2a0492de1e3df52592745fa7e8fc517adc",
}


def verify_legacy_source(directory: Path) -> None:
    for name, expected in LEGACY_SOURCE_HASHES.items():
        path = directory / name
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"Reviewed October helper source is missing: {name}")
        if not 0 < path.stat().st_size <= 1024 * 1024:
            raise RuntimeError(f"October helper source size changed: {name}")
        with path.open("rb") as stream:
            digest = sha256(stream.read()).hexdigest()
        if digest != expected:
            raise RuntimeError(f"October helper source changed; review required: {name}")


def main() -> None:
    legacy_dir = Path.home() / "Projects" / "everquest-legends-rotation"
    verify_legacy_source(legacy_dir)
    sys.path.insert(0, str(legacy_dir))
    engine = importlib.import_module("rotation_engine")
    engine.Engine = make_owner_rotation_engine(engine.Engine)
    gui = importlib.import_module("eql_rotation")
    print("Owner-run rotation preview: autoattack stays manual; F6 prepares gems; "
          "F8 toggles rotation; F9 cancels. Target and movement stay yours.",
          flush=True)
    gui.main()


if __name__ == "__main__":
    main()
