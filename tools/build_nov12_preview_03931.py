#!/usr/bin/env python3
"""Build explicit supervised next-camp travel after an observed level-up."""
import argparse
from pathlib import Path

from build_nov12_preview_03926 import build


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    build(args.source,args.output,version='0.39.31',
        extra_patches=('nov12-7e3cd28-camp-continuation.patch',),
        entry_name='owner_nov12_entry_03931.py',
        change='Existing assist/travel/camp with an explicit supervised next-camp option; reconsider current log level after preparation, measure fresh movement and travel only to a packaged map-compatible destination; stop before new-camp selection')
    print(args.output)
