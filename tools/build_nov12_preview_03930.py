#!/usr/bin/env python3
"""Build automatic stopped-position collection after reached-camp recovery."""
import argparse
from pathlib import Path

from build_nov12_preview_03926 import build


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    build(args.source,args.output,version='0.39.30',
        change='Existing assist/travel/camp; after first reached-camp kill and recovery collect two fresh location replies on the retained floor, then resume the same camp; F8 waits for key cleanup and F9 cancels')
    print(args.output)
