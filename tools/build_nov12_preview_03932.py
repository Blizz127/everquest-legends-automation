#!/usr/bin/env python3
"""Build the existing travel/camp helper with bounded hotbutton input settling."""
import argparse
from pathlib import Path

from build_nov12_preview_03926 import build


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.source, args.output, version='0.39.32',
        extra_patches=('nov12-7e3cd28-camp-continuation.patch',),
        entry_name='owner_nov12_entry_03931.py',
        change='Existing assist/travel/camp; location-hotbutton setup waits for still controls within its original deadline, distinguishes monitoring failures and records aggregate input observations; F8/F9 and send/reply checks retained')
    print(args.output)
