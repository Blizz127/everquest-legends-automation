#!/usr/bin/env python3
"""Owner-started assist and stationary camp; never starts the game or logs in."""
from hashlib import sha256
import json
from pathlib import Path
import sys

MANIFEST_SHA256 = '@MANIFEST_SHA256@'


def verify_snapshot(directory):
    manifest=directory/'SOURCE_HASHES.json';raw=manifest.read_bytes()
    if manifest.is_symlink() or sha256(raw).hexdigest()!=MANIFEST_SHA256:
        raise ValueError('Owner source manifest changed; refusing input')
    for name,expected in json.loads(raw).items():
        relative=Path(name);path=directory/relative
        if relative.is_absolute() or '..' in relative.parts or path.is_symlink() or sha256(path.read_bytes()).hexdigest()!=expected:
            raise ValueError('Owner source mismatch: '+name)


def main():
    if '--measure-navigation' in sys.argv[1:]:
        print('Use 0.39.21 for movement; this preview is assist plus a stationary repeated camp.',file=sys.stderr)
        return 2
    try:verify_snapshot(Path(__file__).resolve().parent)
    except (OSError,ValueError) as error:
        print(error,file=sys.stderr);return 2
    import rotation_engine
    from eql_automation.owner_camp_runtime import make_owner_camp_engine
    rotation_engine.Engine=make_owner_camp_engine(rotation_engine.Engine,client=rotation_engine,repeat=True)
    from eql_rotation import main as helper_main
    helper_main();return 0


if __name__=='__main__':raise SystemExit(main())
