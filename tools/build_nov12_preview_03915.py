#!/usr/bin/env python3
"""Build a distinct source-only owner route trial from retained preview 0.39.12."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from build_nov12_preview import RUNTIME_FILES, sha256
from owner_nov12_entry_03912 import verify_snapshot, EXPECTED as BASE_EXPECTED

PROJECT = Path(__file__).resolve().parents[1]
PATCH = PROJECT/'patches/nov12-7e3cd28-local-route-trial.patch'


def build(source, output, *, version='0.39.15', entry_path=None, extra_patches=(), change=None):
    if output.exists() or output.is_symlink():
        raise ValueError('Refusing to replace an owner preview')
    if source.is_symlink() or not source.is_dir():
        raise ValueError('Retained preview must be a direct directory')
    if output.resolve().is_relative_to((Path.home()/'Games/everquest-legends').resolve()):
        raise ValueError('Preview must remain outside the protected game prefix')
    verify_snapshot(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='eql-preview-03915-', dir=output.parent) as temporary:
        work = Path(temporary)/'snapshot'; work.mkdir()
        names = set(RUNTIME_FILES)|set(BASE_EXPECTED)|{'launch.sh', 'BUILD_INFO.json'}
        names.update(str(path.relative_to(source)) for path in (source/'eqnav').glob('*.py'))
        for name in sorted(names):
            path = source/name
            if path.is_symlink() or not path.is_file():
                raise ValueError('Missing direct source file: '+name)
            (work/name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, work/name)
        # The route stack spans the current package. Pin every packaged file,
        # including the legacy runtime, rather than silently mixing versions.
        for path in sorted((PROJECT/'eql_automation').glob('*.py')):
            if path.is_symlink():
                raise ValueError('Package source must be a direct file')
            shutil.copy2(path, work/'eql_automation'/path.name)
        patches=(PATCH,*extra_patches)
        for patch in patches:
            subprocess.run(['patch', '--batch', '--forward', '-p1', '-i', str(patch)],
                           cwd=work, check=True, capture_output=True)
        shutil.copy2(PROJECT/'HOWTO.md', work/'HOWTO.md')
        pins = {str(p.relative_to(work)): sha256(p) for p in sorted(work.rglob('*'))
                if p.is_file() and p.name != 'BUILD_INFO.json'}
        raw = (json.dumps(pins, indent=2, sort_keys=True)+'\n').encode()
        (work/'SOURCE_HASHES.json').write_bytes(raw)
        manifest_hash = sha256(work/'SOURCE_HASHES.json')
        entry = (entry_path or PROJECT/'tools/owner_nov12_entry_03915.py').read_text()
        assert entry.count('@MANIFEST_SHA256@') == 1
        (work/'owner_nov12_entry.py').write_text(entry.replace('@MANIFEST_SHA256@', manifest_hash))
        info = work/'BUILD_INFO.json'; record = json.loads(info.read_text())
        record.update(version=version, preview_hashes=pins, source_manifest_sha256=manifest_hash,
            entry_sha256=sha256(work/'owner_nov12_entry.py'),
            patch_sha256=[*record['patch_sha256'], *(sha256(patch) for patch in patches)],
            change=change or 'Separate owner-started same-session motion and short GFay route trial',
            mode='measurement only; explicit bounded movement action; combat and leveling disabled',
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
