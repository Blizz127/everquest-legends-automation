#!/usr/bin/env python3
"""Build an isolated read-only preflight candidate from retained preview 0.39.7."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from build_nov12_preview import RUNTIME_FILES, sha256
from owner_nov12_entry_0397 import verify_snapshot, EXPECTED as BASE_EXPECTED
from owner_nov12_entry_0398 import EXPECTED

PROJECT = Path(__file__).resolve().parents[1]
PATCH = PROJECT/'patches/nov12-7e3cd28-navigation-preflight.patch'


def build(source, output):
    if output.exists() or output.is_symlink():
        raise ValueError('Refusing to replace an existing owner preview')
    if source.is_symlink() or not source.is_dir():
        raise ValueError('Retained preview must be a direct directory')
    verify_snapshot(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='eql-preview-0398-', dir=output.parent) as temp:
        work = Path(temp)/'snapshot'; work.mkdir()
        names = set(RUNTIME_FILES) | {'launch.sh', 'BUILD_INFO.json', 'eql_automation/__init__.py',
            'owner_nov12_smoke.py', 'owner_nov12_smoke_base.py', 'owner_nov12_smoke_recovery.py'}
        names.update(name for name in BASE_EXPECTED if name.startswith('eql_automation/'))
        names.update(str(p.relative_to(source)) for p in (source/'eqnav').glob('*.py'))
        for name in sorted(names):
            path=source/name
            if not path.is_file() or path.is_symlink():
                raise ValueError('Missing/direct-file requirement failed: '+name)
            (work/name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, work/name)
        for name in ('owner_navigation_preflight.py','owner_input_observer.py','input_contacts.py'):
            shutil.copy2(PROJECT/'eql_automation'/name, work/'eql_automation'/name)
        subprocess.run(['patch','--batch','--forward','-p1','-i',str(PATCH)],cwd=work,
                       check=True,capture_output=True,text=True)
        for name, expected in EXPECTED.items():
            if sha256(work/name) != expected:
                raise ValueError('0.39.8 source hash mismatch: '+name)
        shutil.copy2(PROJECT/'tools/owner_nov12_entry_0398.py',work/'owner_nov12_entry.py')
        (work/'owner_nov12_smoke.py').rename(work/'owner_nov12_smoke_watchdog.py')
        shutil.copy2(PROJECT/'tools/owner_nov12_smoke_0398.py',work/'owner_nov12_smoke.py')
        info_path=work/'BUILD_INFO.json';info=json.loads(info_path.read_text())
        info.update(version='0.39.8',preview_hashes=EXPECTED,
                    patch_sha256=[*info['patch_sha256'],sha256(PATCH)],
                    change='Measurement-only read-only preflight; no movement permit or G2/F11',
                    real_preflight_acceptance=False)
        info_path.write_text(json.dumps(info,indent=2)+'\n')
        work.rename(output)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();build(args.source,args.output);print(args.output)


if __name__=='__main__':main()
