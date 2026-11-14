#!/usr/bin/env python3
"""Reduce the pinned owner log to private NPC-name evidence; sends no game input."""
import json
from hashlib import sha256
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
STORE = Path.home()/'.local/share/eql-automation'
HELPER = STORE/'owner-assist/0.39.13'
ENGINE_PIN = 'd6ec143920a6748364eb27fa6e279aaf45763b8345fe8e81d7c171648561927f'


def main():
    if sha256((HELPER/'rotation_engine.py').read_bytes()).hexdigest() != ENGINE_PIN:
        raise ValueError('Retained rotation engine changed')
    sys.path[:0] = [str(ROOT), str(HELPER)]
    import rotation_engine
    from eql_automation.camp_candidate_history import build_owner_history, HISTORY_NAME, HISTORY_PIN
    raw = build_owner_history(STORE/'owner-traces/eqlog-Legira-20261113.txt', rotation_engine)
    if sha256(raw).hexdigest() != HISTORY_PIN:
        raise ValueError('Derived owner history differs from the reviewed artifact')
    path = STORE/'owner-route-data'/HISTORY_NAME
    if path.exists() or path.is_symlink():
        if path.is_symlink() or path.read_bytes() != raw:
            raise ValueError('Refusing to replace different history')
    else:
        with path.open('xb') as output:
            output.write(raw)
        path.chmod(0o600)
    print(json.dumps(dict(path=str(path), sha256=sha256(raw).hexdigest(),
        zones={z['zone']:len(z['candidates']) for z in json.loads(raw)['zones']},
        game_input_sent=False)))


if __name__ == '__main__':
    main()
