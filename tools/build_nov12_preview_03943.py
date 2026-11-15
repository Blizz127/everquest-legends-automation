#!/usr/bin/env python3
"""Build retained assist with a separate supervised two-crossing itinerary."""
import argparse
from pathlib import Path

from build_nov12_preview_03926 import build


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    build(args.source,args.output,version='0.39.43',
        extra_patches=('nov12-7e3cd28-camp-continuation.patch',
            'nov12-7e3cd28-stair-landing-test.patch','nov12-7e3cd28-throne-contact-test.patch',
            'nov12-7e3cd28-butcher-newbie-test.patch','nov12-7e3cd28-butcher-goblin-test.patch',
            'nov12-7e3cd28-goblin-sections.patch','nov12-7e3cd28-camp-progress.patch',
            'nov12-7e3cd28-gfay-crossing-destinations.patch',
            'nov12-7e3cd28-zone-itinerary.patch'),
        entry_name='owner_nov12_entry_03943.py',
        change='Adds a separately selected Butcherblock-to-Greater-Faydark-to-Clan-Crushbone itinerary with fresh destination measurements and a fixed whole-trip budget; final arrival stops without camping; actual movement and leveling unverified')
    print(args.output)
