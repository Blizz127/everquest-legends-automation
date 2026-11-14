#!/usr/bin/env python3
"""Check one saved stationary pair and optional offline route, without input.

The label text option is an explicit hypothesis for catalog lookup, not OCR
or evidence that Current Zone was selected. Results are JSON on stdout; this
tool never changes the bundle, starts the game, or enables movement.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from eql_automation.owner_pair_diagnostic import (
    DEFAULT_OUTPUT,load_saved_owner_pair,diagnose_saved_owner_pair,
)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture-dir',type=Path,required=True)
    parser.add_argument('--pair-sha256',required=True)
    parser.add_argument('--private-root',type=Path,default=DEFAULT_OUTPUT)
    parser.add_argument('--zone-names',type=Path)
    parser.add_argument('--zone-names-sha256')
    parser.add_argument('--map-label-text',help='Explicit unverified label-text hypothesis; no OCR')
    parser.add_argument('--route',type=Path)
    parser.add_argument('--route-sha256')
    parser.add_argument('--mesh',type=Path)
    parser.add_argument('--mesh-sha256')
    args=parser.parse_args()
    try:
        saved=load_saved_owner_pair(args.capture_dir,expected_pair_sha256=args.pair_sha256,
                                   private_root=args.private_root)
        report=diagnose_saved_owner_pair(saved,zone_names=args.zone_names,
            zone_names_sha256=args.zone_names_sha256,map_label_text=args.map_label_text,
            route_path=args.route,route_sha256=args.route_sha256,
            mesh_path=args.mesh,mesh_sha256=args.mesh_sha256)
    except (OSError,ValueError,KeyError,TypeError) as error:
        parser.exit(1,f'Saved position diagnostic refused: {error}\n')
    print(json.dumps(report,indent=2,allow_nan=False))


if __name__=='__main__':main()
