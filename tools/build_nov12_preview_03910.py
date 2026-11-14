#!/usr/bin/env python3
"""Build a separate owner observation candidate with automatic icon analysis."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile

from build_nov12_preview import RUNTIME_FILES, sha256
from owner_nov12_entry_0399 import verify_snapshot, EXPECTED as BASE_EXPECTED
from owner_nov12_entry_03910 import EXPECTED

PROJECT=Path(__file__).resolve().parents[1]
UPDATED=('owner_position_adapter.py','owner_ui_observation.py','owner_combat_diagnostic.py',
         'combat_ui_atlas.py','combat_ui_match.py')


def build(source,output):
    if output.exists() or output.is_symlink():raise ValueError('Refusing to replace an owner preview')
    if source.is_symlink() or not source.is_dir():raise ValueError('Retained preview must be a direct directory')
    if output.resolve().is_relative_to((Path.home()/'Games/everquest-legends').resolve()):
        raise ValueError('Owner preview must remain outside the protected game prefix')
    verify_snapshot(source)
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='eql-preview-03910-',dir=output.parent) as temp:
        work=Path(temp)/'snapshot';work.mkdir()
        names=set(RUNTIME_FILES)|set(BASE_EXPECTED)|{'launch.sh','BUILD_INFO.json','eql_automation/__init__.py'}
        names.update(str(p.relative_to(source)) for p in (source/'eqnav').glob('*.py'))
        names.update(p.name for p in source.glob('owner_nov12_smoke*.py'))
        for name in sorted(names):
            path=source/name
            if path.is_symlink() or not path.is_file():raise ValueError('Missing direct source file: '+name)
            (work/name).parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(path,work/name)
        for name in UPDATED:shutil.copy2(PROJECT/'eql_automation'/name,work/'eql_automation'/name)
        for name,expected in EXPECTED.items():
            if sha256(work/name)!=expected:raise ValueError('0.39.10 source hash mismatch: '+name)
        shutil.copy2(PROJECT/'tools/owner_nov12_entry_03910.py',work/'owner_nov12_entry.py')
        (work/'owner_nov12_smoke.py').rename(work/'owner_nov12_smoke_position.py')
        shutil.copy2(PROJECT/'tools/owner_nov12_smoke_03910.py',work/'owner_nov12_smoke.py')
        info=work/'BUILD_INFO.json';record=json.loads(info.read_text())
        record.update(version='0.39.10',preview_hashes=EXPECTED,
            change='Automatic source-pinned combat-icon diagnostic after owner position capture',
            real_position_acceptance=False,game_input_added=False)
        info.write_text(json.dumps(record,indent=2)+'\n')
        work.rename(output)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();build(args.source,args.output);print(args.output)
