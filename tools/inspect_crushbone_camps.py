#!/usr/bin/env python3
"""Print pinned copied camp/terrain evidence without contacting the client."""
import json
import argparse
from pathlib import Path
import sys

STORE = Path.home()/'.local/share/eql-automation'
sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(STORE/'owner-assist/0.39.4')]
from eql_automation.crushbone_assets import DATA_NAME, load_crushbone_assets


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--body-height', type=float, help='Explicit offline hypothesis for floor-seed proposals')
    args = parser.parse_args()
    if args.body_height is not None and not 0 < args.body_height <= 100:
        parser.error('Body-height hypothesis must be finite and between 0 and 100')
    assets = load_crushbone_assets(STORE/'owner-route-data'/DATA_NAME)
    print(json.dumps(assets.annotation_report(body_height=args.body_height), indent=2, allow_nan=False))
