#!/usr/bin/env python3
"""Build fresh-character candidate fallback using the retained owner helper."""
import argparse
from pathlib import Path

from build_nov12_preview_03926 import build


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    build(args.source,args.output,version='0.39.27',
          change='Existing assist/travel/camp; empty character history uses pinned owner NPC names on the same server; NPC-selection bookkeeping no longer blocks spell casting')
    print(args.output)
