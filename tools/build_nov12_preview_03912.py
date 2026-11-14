#!/usr/bin/env python3
"""Build a separate owner-run supervised finite motion test from preview 0.39.11."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from build_nov12_preview import RUNTIME_FILES, sha256
from owner_nov12_entry_03911 import verify_snapshot, EXPECTED as BASE_EXPECTED
from owner_nov12_entry_03912 import EXPECTED

PROJECT = Path(__file__).resolve().parents[1]
PATCH = PROJECT/'patches/nov12-7e3cd28-supervised-motion.patch'
UPDATED = ('owner_supervised_motion.py', 'supervised_motion.py', 'owner_motion_adapter.py', 'motion_collection.py', 'motion_calibration.py', 'motion_executors.py', 'command_submission.py', 'scene_log_veto.py')


def build(source, output):
    if output.exists() or output.is_symlink():
        raise ValueError('Refusing to replace an owner preview')
    if source.is_symlink() or not source.is_dir():
        raise ValueError('Retained preview must be a direct directory')
    if output.resolve().is_relative_to((Path.home()/'Games/everquest-legends').resolve()):
        raise ValueError('Preview must remain outside the protected game prefix')
    verify_snapshot(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='eql-preview-03912-', dir=output.parent) as temporary:
        work = Path(temporary)/'snapshot'; work.mkdir()
        names = set(RUNTIME_FILES)|set(BASE_EXPECTED)|{'launch.sh', 'BUILD_INFO.json', 'eql_automation/__init__.py'}
        names.update(str(path.relative_to(source)) for path in (source/'eqnav').glob('*.py'))
        for name in sorted(names):
            path = source/name
            if path.is_symlink() or not path.is_file():
                raise ValueError('Missing direct source file: '+name)
            (work/name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, work/name)
        for name in UPDATED:
            shutil.copy2(PROJECT/'eql_automation'/name, work/'eql_automation'/name)
        subprocess.run(['patch', '--batch', '--forward', '-p1', '-i', str(PATCH)],
                       cwd=work, check=True, capture_output=True)
        for name, expected in EXPECTED.items():
            if sha256(work/name) != expected:
                raise ValueError('0.39.12 source hash mismatch: '+name)
        shutil.copy2(PROJECT/'tools/owner_nov12_entry_03912.py', work/'owner_nov12_entry.py')
        info = work/'BUILD_INFO.json'; record = json.loads(info.read_text())
        record.update(version='0.39.12', preview_hashes=EXPECTED,
            patch_sha256=[*record['patch_sha256'], sha256(PATCH)],
            change='Owner-supervised finite relative movement measurement; no route activation',
            real_position_acceptance=False, real_route_acceptance=False)
        info.write_text(json.dumps(record, indent=2)+'\n')
        work.rename(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.source, args.output)
    print(args.output)
