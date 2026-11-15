#!/usr/bin/env python3
"""Reproduce the pinned, private Butcherblock search-name artifact. No game input."""
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
STORE=Path.home()/'.local/share/eql-automation'
HELPER=STORE/'owner-assist/0.39.13'
POLICY_PINS={
    'rotation_engine.py':'d6ec143920a6748364eb27fa6e279aaf45763b8345fe8e81d7c171648561927f',
    'rotation_core.py':'9f05379c407f7c9042b38dc7f39c72c0b603bc24d6e754330746f805211a3113',
    'leveling_guide.py':'9babe5213d4903f5c014f59bf38b1fa3c3167e22ecb6ff4af61e624cf342ca4c',
    'leveling_guide.json':'bfe936da1aec38b37a683af51f0ee4189cd86bcb4a1680deee613c4dfeba77b9',
}


def main():
    for name,pin in POLICY_PINS.items():
        path=HELPER/name
        if path.is_symlink() or sha256(path.read_bytes()).hexdigest()!=pin:
            raise ValueError('Retained name policy changed: '+name)
    sys.path[:0]=[str(ROOT),str(HELPER)]
    import rotation_engine
    from eql_automation.camp_search_history import build_owner_search_history,SEARCH_NAME,SEARCH_PIN
    raw=build_owner_search_history(STORE/'owner-traces/owner-log-20261115T0243Z.txt',rotation_engine)
    if sha256(raw).hexdigest()!=SEARCH_PIN:
        raise ValueError('Derived search names differ from the reviewed artifact')
    path=STORE/'owner-route-data'/SEARCH_NAME
    if path.exists() or path.is_symlink():
        if path.is_symlink() or path.read_bytes()!=raw:
            raise ValueError('Refusing to replace different search history')
    else:
        with path.open('xb') as output:output.write(raw)
        path.chmod(0o600)
    print(json.dumps(dict(path=str(path),sha256=SEARCH_PIN,
        candidates=len(json.loads(raw)['candidates']),game_input_sent=False)))


if __name__=='__main__':main()
