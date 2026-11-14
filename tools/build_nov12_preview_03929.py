#!/usr/bin/env python3
"""Build reached-floor retention through the travel-to-camp handoff."""
import argparse
from pathlib import Path

from build_nov12_preview_03926 import build


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    build(args.source,args.output,version='0.39.29',
        change='Existing assist/travel/camp; retain the exact reached source floor during camp, discard it on stop or assist, and validate fresh stopped-height evidence for later relocation')
    print(args.output)
