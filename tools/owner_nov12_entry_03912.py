#!/usr/bin/env python3
"""Pinned, owner-run entry for the isolated November assist preview.

Copy this file beside the three pinned November helper modules and the
``eql_automation.owner_nov12_adapter`` package. The owner launches it; this
entry never starts EverQuest or logs in on its own.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys


EXPECTED = {'eql_automation/combat_ui_atlas.py': 'da0e09c37fb5c5145e62ed67ac241435ba06725b8abadd90899b150f7dfab402',
 'eql_automation/combat_ui_match.py': '5f615bbdbf21a1d204883c854ab8d36c2070fab4f6ca6b1753630ae78f2712a8',
 'eql_automation/command_submission.py': 'cb87fe6a5a8b765c4619468a50cb9c1101ebe0f2e78e7bcadb65664a722d44bf',
 'eql_automation/hp_layout.py': '3866414c8e3dfff41744ff7ba39e4996ae1ac645e2712ecf79a1836dcca1481f',
 'eql_automation/input_contacts.py': '4521dde1d977bf6ea7cc912586fafd0ff73613fd9324f2314bc4bdb5a628a577',
 'eql_automation/location_hotkey.py': 'c201c621bf976080b8f463196f6cceb185e944ceacfb4b6674cfa1775678c499',
 'eql_automation/location_log.py': '1934976dd334efcbde14c1ee9dd7c2adf1d6ea3914fe234bb1ac6e0d687f067e',
 'eql_automation/motion_calibration.py': 'c00d2b138365094f2217adb6d1b360b5eeae8ca94e5170bfdbff6e450887b487',
 'eql_automation/motion_collection.py': '6df1c7aadec73e787b2925a585d00f2651da35275c42eb8722880b4eec118255',
 'eql_automation/motion_executors.py': '0c46491716c7c3c5e917354fc760b6ecdcb13836fdd313a9a63315bda715c907',
 'eql_automation/owner_combat_diagnostic.py': 'fafd2c2063f0105d82783bd9cc37723d9c42d25298c1181c88fea0963d1b634a',
 'eql_automation/owner_g0_watchdog.py': '9a905e4477494b944f8cad733b07907a9b7c35177890565f7f9c31c201d93b56',
 'eql_automation/owner_input_observer.py': '296171170fa9aee7b3b021e00f3fa29103bb822f8f2c0e854c4c28e5f405b4a6',
 'eql_automation/owner_location_hotkey_test.py': '8c3c9380a919eaa4937884ce7bb75d6ace8b33fcbc96aed471f026b0daea88c8',
 'eql_automation/owner_motion_adapter.py': '2bf8a93614f77eb4bb7e1c5b1dab34682055150ef3fb115822899219e7821e0f',
 'eql_automation/owner_navigation_preflight.py': '4cc33a96723b48973e8237418320ebcd1f6bce948c1b725630d29155f4cea9b0',
 'eql_automation/owner_nov12_adapter.py': '26a62fa0d1d30966dd19ad9ab578d2b81d38d48181c2d01de98a5839defcf49a',
 'eql_automation/owner_nov12_recovery.py': 'efdf13c8b63efc31154be0c889d7be85ea6f8736a340334a99c3486c9a1a5a34',
 'eql_automation/owner_position_adapter.py': 'fa10a945008e09dde1904ed5903fb9836fef501aa5c29b4ed2b1f29f31975461',
 'eql_automation/owner_supervised_motion.py': '8f2910ee062c94e23271859ca10e896ae19f3020410c739eeac6958fe593747e',
 'eql_automation/owner_ui_observation.py': '3da44541cc6dee7e55c87a32188512a8ce55681188c4859e5a5d3d5b3161e940',
 'eql_automation/position_observation.py': 'e1cd015858e19c2dd8116d4cb65bda40a3d20d32653da8d14133100502c3ec16',
 'eql_automation/scene_log_veto.py': '569ab693b4b7b040ee8984823951a4fede803eeeb4bf5ecea3e342ff80219773',
 'eql_automation/supervised_motion.py': 'c12482e73ac40c80247e2880d5f96baacd0515aef6f2c03584ed78edcaef136e',
 'eql_automation/uinput_watchdog.py': '3ccaf83ca95183ffe918f6fdc9a62a22e1b43c2bf9f5bacd0e0c265620fdef39',
 'eql_automation/unbound_location_log.py': 'e24021e4d1b1d326438f5510f7f47568f5323ed36e224a9b8fcce39fec906ec8',
 'eql_rotation.py': '163dba68206e6af309993bc3e24077688826d0df7c32b6996157510fef749621',
 'navigation.py': '69dbc6472447942cc30dbe592a6e1cf02998c0a0b8811a8bb59672655dc4049e',
 'rotation_core.py': '9f05379c407f7c9042b38dc7f39c72c0b603bc24d6e754330746f805211a3113',
 'rotation_engine.py': '48c6dd7cf6676284d8aafc1221a66ad71f1861cca82f6c9af56446504599848b',
 'uilayout.py': 'd79ec2ae32a31fa642f4b64952996c28d7905efc15fce1d816fc671e552b733a'}


def verify_snapshot(directory: Path) -> None:
    for name, expected in EXPECTED.items():
        path = directory / name
        try:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            raise RuntimeError(f"Owner preview missing {name}: {exc}") from exc
        if actual != expected:
            raise RuntimeError(f"Owner preview source mismatch: {name}; refusing input")


def main() -> int:
    directory = Path(__file__).resolve().parent
    try:
        verify_snapshot(directory)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 2
    # The isolated snapshot is on sys.path when this file is invoked directly.
    import rotation_engine
    from eql_automation.owner_supervised_motion import make_owner_nov12_engine
    rotation_engine.Engine = make_owner_nov12_engine(rotation_engine.Engine)
    from eql_rotation import main as helper_main
    helper_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
