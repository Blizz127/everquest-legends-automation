#!/usr/bin/env python3
"""Check the pinned Goblin approach through the owner's current-start producer.

Only copied geometry and a synthetic location log are read. No game interface
or input device is used. The result does not establish real-client acceptance.
"""
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path
import argparse
import json
import math
import os
import resource
import signal
import sys
import tempfile
import time

SOURCE_SCRIPT = Path(__file__).resolve()
PROJECT = SOURCE_SCRIPT.parents[1]
STORE = Path.home()/'.local/share/eql-automation'
sys.path[:0] = [str(PROJECT), str(STORE/'owner-assist/0.39.4')]

from eql_automation.butcher_assets import DATA_NAME, DATA_PINS, load_butcher_assets
from eql_automation.current_source_itinerary import plan_current_source_itinerary
from eql_automation.location_log import LocationLogReader
from eql_automation.native_region_policy import encoded
from eql_automation.owner_route_assets import checked_bytes
from eql_automation.route_geometry import RouteMotionBounds
from eql_automation.source_itinerary import SourceItineraryGuide

PRIOR = 'butcher-newbie-goblin-transit-20261115-final-source-alienware.json'
PRIOR_PIN = '3c396a3944c4aba7ad05def3c939d45d74c24f87ccd7409a2d048cb4c85be22e'


def run(output):
    began = time.monotonic()
    pins = {str(p.relative_to(PROJECT)): sha256(p.read_bytes()).hexdigest()
            for p in (SOURCE_SCRIPT, *sorted((PROJECT/'eql_automation').glob('*.py')))}
    root = STORE/'owner-route-data'/DATA_NAME
    prior = json.loads(checked_bytes(STORE/'nav-candidates'/PRIOR, PRIOR_PIN))
    guide = SourceItineraryGuide.from_record(prior['guide'])
    plan_name = Path(prior['checked_plan']['file']).name
    old_plan = json.loads(checked_bytes(STORE/'nav-candidates'/plan_name, prior['checked_plan']['sha256']))
    if (prior['completed'] is not True or prior['source_candidate'] is not True
            or prior['game_input_sent'] is not False or prior['real_client_accepted'] is not False
            or prior['data_sha256'] != DATA_PINS or guide.zone != 'butcher'
            or guide.goal != (-2069., -298.) or guide.operations[0].start != (-650., 2700.)
            or old_plan['guide_sha256'] != sha256(encoded(guide.record())).hexdigest()
            or old_plan['geometry_candidate'] is not True):
        raise ValueError('Pinned Goblin route differs from its complete checked plan')
    result = dict(format='eql-butcher-goblin-startup-check-v1', prior_sha256=PRIOR_PIN,
        guide=guide.record(), code_sha256=pins, client_data_pins=DATA_PINS,
        completed=False, source_candidate=False, synthetic_game_log=True,
        game_input_sent=False, current_character_observation=False, real_client_accepted=False)
    try:
        p = load_butcher_assets(root, native_planning=True).planner
        start = tuple(round(v, 2) for v in guide.operations[0].start)
        end = next(op.end for op in guide.operations if op.end != start)
        source_z = p.source.propose_unique_diffuse_floor(start, body_height=6.).height
        heading = math.degrees(math.atan2(end[0]-start[0], end[1]-start[1])) % 360
        bounds = RouteMotionBounds('offline-start-bounds', 'offline-motion',
            .01, .1, .2, 30., .4, .01, 2., .1, 1.2, 6.)
        now = 100.
        local_base = datetime(2026, 11, 15, 12)
        with tempfile.TemporaryDirectory(prefix='butcher-goblin-start-') as temporary:
            log = Path(temporary)/'eqlog_Probe_private.txt'; log.touch()
            reader = LocationLogReader(log, root/'ZoneNames.txt',
                expected_character='Probe', expected_server='private')
            def append(body):
                stamp = local_base+timedelta(seconds=now-100.)
                with log.open('a') as stream:
                    stream.write(stamp.strftime('[%a %b %d %H:%M:%S %Y] ')+body+'\n')
                return reader.poll(now=now)
            append('You have entered '+p.zone_name+'.')
            first, = append(f'Your Location is {start[1]:.2f}, {start[0]:.2f}, {source_z+2.5:.2f}')
            now += .5
            second, = append(f'Your Location is {start[1]:.2f}, {start[0]:.2f}, {source_z+2.5:.2f}')
            plan = plan_current_source_itinerary(p, reader, first, second, guide=guide,
                maximum_seconds=240., clock=lambda:now, heading=heading,
                motion_record_id='offline-motion', bounds=bounds, half_width=.3,
                vertical_window=3., maximum_source_z_difference=2.,
                owner_binding=('synthetic',), binding_reader=lambda:('synthetic',),
                released_at=99.8, record_id='butcher-goblin-offline-start',
                local_wall_clock=lambda:local_base+timedelta(seconds=now-100.),
                allow_overhead_boundary=True)
            result.update(initial=json.loads(plan.initial.evidence_bytes),
                plan=plan.itinerary.record(), plan_sha256=plan.itinerary.sha256,
                exact_detail_support=p._support(start), source_start_height=source_z,
                source_candidate=True)
    except (ValueError, TimeoutError) as error:
        result['refusal'] = str(error)
    signal.setitimer(signal.ITIMER_REAL, 0)
    for name, pin in pins.items(): checked_bytes(PROJECT/name, pin)
    for name, pin in DATA_PINS.items(): checked_bytes(root/name, pin)
    result.update(completed=True, seconds=time.monotonic()-began)
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps(dict(output=str(output), sha256=sha256(output.read_bytes()).hexdigest(),
        source_candidate=result['source_candidate'], refusal=result.get('refusal'),
        seconds=result['seconds'], cells=len(result.get('plan',{}).get('cells',[])))), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if (args.output.exists() or args.output.is_symlink()
            or args.output.parent.resolve() != (STORE/'nav-candidates').resolve()):
        parser.error('Use a new output directly in private nav-candidates')
    os.umask(0o077); os.nice(19)
    def expired(*_): raise TimeoutError('Offline Goblin startup CPU/wall budget exhausted')
    signal.signal(signal.SIGALRM, expired); signal.signal(signal.SIGXCPU, expired)
    resource.setrlimit(resource.RLIMIT_CPU, (120, 125))
    signal.setitimer(signal.ITIMER_REAL, 300)
    run(args.output)
