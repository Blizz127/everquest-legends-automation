#!/usr/bin/env python3
"""Compare copied Crushbone initial-floor policies with synthetic log samples.

Coordinates and dimensions are explicit hypotheses, never current game state.
No connection to the client, input device or account is made.
"""
import argparse
from datetime import datetime, timedelta
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile

STORE = Path.home()/'.local/share/eql-automation'
sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(STORE/'owner-assist/0.39.4')]

from eql_automation.crushbone_assets import DATA_NAME, load_crushbone_assets
from eql_automation.location_log import LocationLogReader
from eql_automation.observed_height import measure_current_height, height_record
from eql_automation.route_geometry import RouteMotionBounds


def run(args):
    rows = []
    root = STORE/'owner-route-data'/DATA_NAME
    for enabled in (False, True):
        planner = load_crushbone_assets(root, native_planning=enabled).planner
        now = 100.
        wall = lambda: datetime(2026,11,14,12)+timedelta(seconds=now-100.)
        with tempfile.TemporaryDirectory(prefix='eql-synthetic-start-') as temp:
            log = Path(temp)/'eqlog_OfflineProbe_synthetic.txt'; log.touch()
            reader = LocationLogReader(log, root/'ZoneNames.txt',
                expected_character='OfflineProbe', expected_server='synthetic')
            def append(body):
                with log.open('a') as out:
                    out.write(wall().strftime('[%a %b %d %H:%M:%S %Y] ')+body+'\n')
                return reader.poll(now=now)
            def position():
                return append(f'Your Location is {args.y:.2f}, {args.x:.2f}, {args.printed_z:.2f}')[0]
            append('You have entered '+planner.zone_name+'.')
            first = position(); now += .5; second = position()
            owner = ('offline', 'synthetic-probe')
            bounds = RouteMotionBounds('synthetic-hypotheses','synthetic-motion',.01,.05,.1,
                30.,.02,.01,1.,.01,args.body_radius,args.body_height)
            row = dict(native_planning=enabled, conditional_plan=False, stopped_height=False)
            try:
                plan = planner.plan(reader,first,second,heading=args.heading,
                    motion_record_id='synthetic-motion',bounds=bounds,length=.75,half_width=.3,
                    vertical_window=3.,maximum_source_z_difference=2.,owner_binding=owner,
                    binding_reader=lambda:owner,released_at=99.8,record_id='synthetic-start',
                    clock=lambda:now,local_wall_clock=wall,allow_overhead_boundary=True)
                row.update(conditional_plan=True, plan_sha256=sha256(plan.plan_bytes).hexdigest(),
                    geometry=json.loads(plan.evidence_bytes))
                release = now; now += .2; first = position(); now += .5; second = position()
                height = measure_current_height(plan.observer,reader,first,second,route=plan.route,
                    segment_index=0,owner_binding=owner,binding_reader=lambda:owner,
                    clock=lambda:now,local_wall_clock=wall,record_id='synthetic-height',
                    released_at=release,floor_plan=plan)
                row.update(stopped_height=True, height=height_record(height))
            except ValueError as error:
                row['refusal'] = str(error)
            rows.append(row)
    return dict(format='eql-copied-crushbone-native-planning-comparison-v1',
        synthetic_reader=True, synthetic_clock=True, coordinates_are_current=False,
        supplied_package_xy=[args.x,args.y], synthetic_printed_z=args.printed_z,
        supplied_heading=args.heading, body_radius_hypothesis=args.body_radius,
        body_height_hypothesis=args.body_height, rows=rows, game_input_sent=False,
        route_accepted=False, real_client_accepted=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('x', 'y', 'printed-z', 'heading', 'body-radius', 'body-height'):
        parser.add_argument('--'+name, required=True, type=float)
    print(json.dumps(run(parser.parse_args()), indent=2, allow_nan=False))
