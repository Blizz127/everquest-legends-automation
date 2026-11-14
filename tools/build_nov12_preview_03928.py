#!/usr/bin/env python3
"""Build retained input continuity through the travel-to-camp handoff."""
import argparse
from pathlib import Path

from build_nov12_preview_03926 import build


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    build(args.source,args.output,version='0.39.28',
          change='Existing assist/travel/camp; preserve the same read-only input monitor through camp and retire it before assist; retain historical arrival motion for later relocation work')
    print(args.output)
