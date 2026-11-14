#!/usr/bin/env python3
"""Build owner assist plus a bounded stationary camp from retained 0.39.13."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from build_nov12_preview import RUNTIME_FILES, sha256, PROJECT
from owner_nov12_entry_03913 import verify_snapshot


def build(source, output):
    if output.exists() or output.is_symlink():
        raise ValueError('Refusing to replace an owner preview')
    if source.is_symlink() or not source.is_dir():
        raise ValueError('Retained preview must be a direct directory')
    if output.resolve().is_relative_to((Path.home()/'Games/everquest-legends').resolve()):
        raise ValueError('Preview must remain outside the protected game prefix')
    verify_snapshot(source)
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='eql-preview-03925-',dir=output.parent) as temporary:
        work=Path(temporary)/'snapshot';work.mkdir()
        names=set(RUNTIME_FILES)|{'launch.sh','BUILD_INFO.json'}
        names.update(str(p.relative_to(source)) for p in (source/'eqnav').glob('*.py'))
        for name in sorted(names):
            path=source/name
            if path.is_symlink() or not path.is_file():
                raise ValueError('Missing direct source file: '+name)
            (work/name).parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(path,work/name)
        (work/'eql_automation').mkdir()
        for path in sorted((PROJECT/'eql_automation').glob('*.py')):
            if path.is_symlink():raise ValueError('Source file is a symlink')
            shutil.copy2(path,work/'eql_automation'/path.name)
        patch=PROJECT/'patches/nov12-7e3cd28-journey-camp.patch'
        subprocess.run(['patch','--batch','--forward','-p1','-i',str(patch)],cwd=work,check=True,capture_output=True)
        shutil.copy2(PROJECT/'HOWTO.md',work/'HOWTO.md')
        pins={str(p.relative_to(work)):sha256(p) for p in sorted(work.rglob('*'))
              if p.is_file() and p.name!='BUILD_INFO.json'}
        (work/'SOURCE_HASHES.json').write_text(json.dumps(pins,indent=2,sort_keys=True)+'\n')
        manifest=sha256(work/'SOURCE_HASHES.json')
        entry=(PROJECT/'tools/owner_nov12_entry_03925.py').read_text()
        assert entry.count('@MANIFEST_SHA256@')==1
        (work/'owner_nov12_entry.py').write_text(entry.replace('@MANIFEST_SHA256@',manifest))
        info=work/'BUILD_INFO.json';record=json.loads(info.read_text())
        record.update(version='0.39.25',source_manifest_sha256=manifest,
            entry_sha256=sha256(work/'owner_nov12_entry.py'),preview_hashes=pins,
            patch_sha256=[*record['patch_sha256'],sha256(patch)],
            change='Existing assist plus supervised Crushbone travel with fresh stopped arrival into repeated automatic-preparation camp',
            mode='F8 owner-targeted assist; explicit travel then camp button; F11 stationary camp/off; F9 OFF; no loot input',
            real_camp_acceptance=False,real_route_acceptance=False)
        info.write_text(json.dumps(record,indent=2)+'\n')
        work.rename(output)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();build(args.source,args.output);print(args.output)
