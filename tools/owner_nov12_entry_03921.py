#!/usr/bin/env python3
"""Owner-started supervised destination travel; no client launch or automatic job."""
from hashlib import sha256
import json
from pathlib import Path
import sys

# The builder replaces this with the hash of the exact packaged source list.
MANIFEST_SHA256 = '@MANIFEST_SHA256@'


def verify_snapshot(directory):
    manifest = directory/'SOURCE_HASHES.json'
    raw = manifest.read_bytes()
    if manifest.is_symlink() or sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise ValueError('Route preview source manifest changed; refusing input')
    pins = json.loads(raw)
    for name, expected in pins.items():
        relative = Path(name)
        path = directory/relative
        if (relative.is_absolute() or '..' in relative.parts or path.is_symlink()
                or sha256(path.read_bytes()).hexdigest() != expected):
            raise ValueError('Route preview source mismatch: '+name)


def main():
    if '--measure-navigation' not in sys.argv[1:]:
        print('Use ./launch.sh --measure-navigation for this finite route test. '
              'Use preview 0.39.13 for assist.', file=sys.stderr)
        return 2
    try:
        verify_snapshot(Path(__file__).resolve().parent)
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 2
    import rotation_engine
    from eql_automation.owner_route_assets import load_owner_planner
    from eql_automation.owner_destination_assets import load_owner_destination
    from eql_automation.owner_crossing_assets import load_owner_crossing
    from eql_automation.owner_route_trial import make_owner_route_trial_engine
    from eql_automation.owner_source_assets import load_owner_source_destination
    from eql_automation.map_zone_observer import observe_owner_map_zone
    rotation_engine.Engine = make_owner_route_trial_engine(
        rotation_engine.Engine, planner_loader=load_owner_planner, destination_loader=load_owner_destination,
        crossing_loader=load_owner_crossing, source_loader=load_owner_source_destination,
        zone_observer=observe_owner_map_zone)
    from eql_rotation import main as helper_main
    helper_main()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
