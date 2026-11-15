#!/usr/bin/env python3
"""Build retained assist with finite automatic sections for supervised Goblin travel."""
import argparse
from pathlib import Path

from build_nov12_preview_03926 import build


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    build(args.source,args.output,version='0.39.38',
        extra_patches=('nov12-7e3cd28-camp-continuation.patch',
            'nov12-7e3cd28-stair-landing-test.patch','nov12-7e3cd28-throne-contact-test.patch',
            'nov12-7e3cd28-butcher-newbie-test.patch','nov12-7e3cd28-butcher-goblin-test.patch',
            'nov12-7e3cd28-goblin-sections.patch'),
        entry_name='owner_nov12_entry_03938.py',
        change='Supervised Goblin travel automatically continues ordered sections after fresh stopped-position and motion checks, retaining one finite whole-trip budget; strict assist unchanged; real travel and leveling unverified')
    print(args.output)
