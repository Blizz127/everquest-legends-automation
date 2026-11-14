#!/usr/bin/env python3
"""Build the existing helper with a separate stair-landing movement test."""
import argparse
from pathlib import Path

from build_nov12_preview_03926 import build


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.source, args.output, version='0.39.33',
        extra_patches=('nov12-7e3cd28-camp-continuation.patch','nov12-7e3cd28-stair-landing-test.patch'),
        entry_name='owner_nov12_entry_03931.py',
        change='Existing assist and camp travel plus optional North Wall to Throne stair landing movement test; fresh stopped stair handoff, provisional feedback and actual landing; stop on arrival without camp; F8 assist and F9 cancellation retained')
    print(args.output)
