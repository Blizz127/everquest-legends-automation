#!/usr/bin/env python3
"""Print pinned copied camp/terrain evidence without contacting the client."""
import json
from pathlib import Path
import sys

STORE = Path.home()/'.local/share/eql-automation'
sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(STORE/'owner-assist/0.39.4')]
from eql_automation.crushbone_assets import DATA_NAME, load_crushbone_assets


if __name__ == '__main__':
    assets = load_crushbone_assets(STORE/'owner-route-data'/DATA_NAME)
    print(json.dumps(assets.annotation_report(), indent=2, allow_nan=False))
