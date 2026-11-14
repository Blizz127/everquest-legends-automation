#!/usr/bin/env python3
"""Build supervised Crushbone local movement and retain GFay crossing."""
import argparse
from pathlib import Path

from build_nov12_preview_03915 import build, PROJECT


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.source, args.output, version='0.39.21',
        entry_path=PROJECT/'tools/owner_nov12_entry_03921.py',
        extra_patches=(PROJECT/'patches/nov12-7e3cd28-destination-travel.patch',
                       PROJECT/'patches/nov12-7e3cd28-map-zone-startup.patch',
                       PROJECT/'patches/nov12-7e3cd28-crossing-travel.patch',
                       PROJECT/'patches/nov12-7e3cd28-crushbone-local-trial.patch',
                       PROJECT/'patches/nov12-7e3cd28-source-travel.patch'),
        change='Owner-started source travel toward Slave Mines with observed step landings; no combat or leveling')
    print(args.output)
