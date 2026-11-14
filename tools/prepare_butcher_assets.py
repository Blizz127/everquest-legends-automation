#!/usr/bin/env python3
"""Assemble pinned retained Butcherblock inputs in the private data store.

No download, client/prefix access or game input. Existing data is only verified;
new copies are installed by renaming a private temporary directory.
"""
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eql_automation.butcher_assets import DATA_NAME, DATA_PINS
from eql_automation.owner_route_assets import checked_bytes


def prepare(store):
    store = Path(store)
    target = store/'owner-route-data'/DATA_NAME
    sources = {
        'butcher.npz': store/'navmesh/nov12-7e3cd28-store/butcher.npz',
        'butcher.json': store/'navmesh/nov12-7e3cd28-store/butcher.json',
        'butcher.s3d': store/'client-data/retail-full/assets/butcher.s3d',
        'butcher_obj.s3d': store/'client-data/retail-full/assets/butcher_obj.s3d',
        'butcher_2_obj.s3d': store/'client-data/retail-full/assets/butcher_2_obj.s3d',
        'ZoneNames.txt': store/'client-data/zone-catalog-20261114T1123Z/ZoneNames.txt',
        'butcher_3.txt': store/'client-data/retail-full/maps/Solo_Leveling/butcher_3.txt',
        'butcher.map-alignment.json': store/'nav-candidates/butcher.map-alignment.json',
    }
    if store.is_symlink() or target.is_symlink() or target.parent.is_symlink():
        raise ValueError('Private data roots must not be symlinks')
    if not target.exists():
        data = {name: checked_bytes(path, DATA_PINS[name]) for name, path in sources.items()}
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.butcher-', dir=target.parent) as temporary:
            staging = Path(temporary)/'data'
            staging.mkdir(mode=0o700)
            for name, blob in data.items():
                with (staging/name).open('xb') as output:
                    output.write(blob)
            if target.exists() or target.is_symlink():
                raise ValueError('Private Butcherblock destination appeared during staging')
            staging.rename(target)
    for name, pin in DATA_PINS.items():
        checked_bytes(target/name, pin)
    return dict(data_root=str(target), pins=dict(DATA_PINS), client_install_modified=False)


if __name__ == '__main__':
    os.umask(0o077)
    print(json.dumps(prepare(Path.home()/'.local/share/eql-automation'), indent=2))
