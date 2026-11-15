#!/usr/bin/env python3
"""Owner-started assist and bounded source crossings; never logs into the game."""
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
        print('Use ./launch.sh without --measure-navigation; travel and camp share this helper.',file=sys.stderr)
        return 2
    try:verify_snapshot(Path(__file__).resolve().parent)
    except (OSError,ValueError) as error:
        print(error,file=sys.stderr);return 2
    import rotation_engine
    from eql_automation.owner_journey_runtime import make_owner_journey_engine
    from eql_automation.owner_camp_plan_provider import owner_camp_probe_plan
    from eql_automation.owner_route_assets import load_owner_planner
    from eql_automation.owner_source_assets import load_owner_source_destination
    from eql_automation.owner_section_assets import load_owner_walking_sections, load_guide_walking_sections
    from eql_automation.map_zone_observer import observe_owner_map_zone
    rotation_engine.Engine = make_owner_journey_engine(rotation_engine.Engine, client=rotation_engine,
        planner_loader=load_owner_planner, source_loader=load_owner_source_destination,
        zone_observer=observe_owner_map_zone,camp_probe_plan_provider=owner_camp_probe_plan,
        section_provider=load_owner_walking_sections,camp_section_provider=load_guide_walking_sections,
        camp_options=dict(progress_directory=Path.home()/'.local/share/eql-automation/owner-status'))
    from eql_rotation import main as helper_main
    helper_main();return 0


if __name__=='__main__':raise SystemExit(main())
