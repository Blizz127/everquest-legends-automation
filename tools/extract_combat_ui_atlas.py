#!/usr/bin/env python3
"""Extract private, hash-pinned client templates; no live capture or input."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from eql_automation.combat_ui_atlas import load_combat_ui_atlas


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    store=(Path.home()/'.local/share/eql-automation').resolve()
    protected=(Path.home()/'Games/everquest-legends').resolve()
    if (store.is_relative_to(protected)
            or not args.manifest.resolve().is_relative_to(store)
            or not args.output.resolve().is_relative_to(store)
            or args.output.exists() or args.output.is_symlink()):
        parser.error('Use copied private inputs and a new private output directory')
    atlas=load_combat_ui_atlas(args.manifest,expected_sha256=args.sha256)
    args.output.mkdir(mode=0o700,parents=True,exist_ok=False)
    record=atlas.record()
    for item,frame in zip(record['frames'],atlas.frames):
        path=args.output/f'{frame.animation}-{frame.index}.png'
        frame.image().save(path);path.chmod(0o600)
        item.update(file=path.name,png_sha256=sha256(path.read_bytes()).hexdigest())
    path=args.output/'atlas.json'
    path.write_text(json.dumps(record,indent=2)+'\n');path.chmod(0o600)
    print(json.dumps(dict(output=str(path),sha256=sha256(path.read_bytes()).hexdigest(),
                         frames=len(atlas.frames),live_state_verified=False)))


if __name__=='__main__':main()
