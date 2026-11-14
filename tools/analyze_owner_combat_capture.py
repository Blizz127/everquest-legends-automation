#!/usr/bin/env python3
"""Compare a saved private combat crop with client sprites; no display or input."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from eql_automation.combat_ui_atlas import load_combat_ui_atlas
from eql_automation.combat_ui_match import analyze_saved_combat_crop


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--metadata-sha256',required=True)
    parser.add_argument('--atlas-manifest',type=Path,required=True)
    parser.add_argument('--atlas-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    store=(Path.home()/'.local/share/eql-automation').resolve()
    protected=(Path.home()/'Games/everquest-legends').resolve()
    if (store.is_relative_to(protected) or any(not p.resolve().is_relative_to(store)
            for p in (args.metadata,args.atlas_manifest,args.output))
            or args.output.exists() or args.output.is_symlink()):
        parser.error('Use copied private inputs and a new private output file')
    atlas=load_combat_ui_atlas(args.atlas_manifest,expected_sha256=args.atlas_sha256)
    result=analyze_saved_combat_crop(args.metadata,metadata_sha256=args.metadata_sha256,atlas=atlas)
    args.output.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    with args.output.open('x') as output:json.dump(result,output,indent=2);output.write('\n')
    args.output.chmod(0o600)
    print(json.dumps(dict(output=str(args.output),candidates=len(result['ranked_candidates']),
                         live_state_verified=False,input_authorized=False)))


if __name__=='__main__':main()
