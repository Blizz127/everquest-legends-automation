#!/usr/bin/env python3
"""Build the existing assist helper with zone-bound Butcherblock Newbie Hills and Goblin Camp destinations."""
import argparse
from pathlib import Path

from build_nov12_preview_03926 import build


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    build(args.source,args.output,version='0.39.36',
        extra_patches=('nov12-7e3cd28-camp-continuation.patch',
            'nov12-7e3cd28-stair-landing-test.patch','nov12-7e3cd28-throne-contact-test.patch','nov12-7e3cd28-butcher-newbie-test.patch',
            'nov12-7e3cd28-butcher-goblin-test.patch'),
        entry_name='owner_nov12_entry_03931.py',
        change='Existing rotation/assist plus zone-bound Butcherblock Newbie Hills to Goblin Camp travel/camp and movement-only options; preserved Crushbone guides; F8 assist/F9 stop; real travel and leveling unverified')
    print(args.output)
