#!/usr/bin/env python3
"""Check copied camp geometry with explicitly SYNTHETIC location observations.

No game input or live state. Output is private client-derived data. Command-line
motion/body numbers are hypotheses, not measurements or game constants.
"""
import argparse
from dataclasses import asdict
from datetime import datetime,timedelta
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import time

STORE=Path.home()/'.local/share/eql-automation'
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(STORE/'owner-assist/0.39.4')]
from eql_automation.crushbone_assets import DATA_NAME,DATA_PINS,load_crushbone_assets
from eql_automation.crushbone_source_guide import DESTINATIONS
from eql_automation.location_log import LocationLogReader
from eql_automation.owner_route_assets import checked_bytes
from eql_automation.route_geometry import RouteMotionBounds


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--speed-bound',type=float,required=True)
    parser.add_argument('--maximum-hold',type=float,required=True)
    parser.add_argument('--body-radius',type=float,required=True)
    parser.add_argument('--body-height',type=float,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    root=STORE/'nav-candidates';root.mkdir(parents=True,exist_ok=True)
    if args.output.parent.resolve()!=root.resolve() or args.output.exists() or args.output.is_symlink():
        parser.error('Use a new file directly under the private nav-candidates store')
    bounds=RouteMotionBounds('offline-probe-hypotheses','synthetic-no-calibration',
        .01,min(.05,args.maximum_hold),args.maximum_hold,args.speed_bound,.1,.05,180.,.1,
        args.body_radius,args.body_height)
    bounds.validate_values(calibration_record_id='synthetic-no-calibration',maximum_step_seconds=.2)
    assets=load_crushbone_assets(STORE/'owner-route-data'/DATA_NAME,native_planning=True)
    p=assets.planner;rows=[]
    for identifier,destination in DESTINATIONS.items():
        row=dict(destination_id=identifier,package_xy=destination.goal,accepted_geometry=False)
        began=time.monotonic()
        try:
            _,z=p._support(destination.goal)
            with tempfile.TemporaryDirectory(prefix='probe-fixture-',dir=root) as directory:
                directory=Path(directory);log=directory/'eqlog_ProbeFixture_private.txt';log.touch()
                reader=LocationLogReader(log,STORE/'owner-route-data'/DATA_NAME/'ZoneNames.txt',
                    expected_character='ProbeFixture',expected_server='private')
                wall=datetime.now();baseline=time.monotonic();synthetic=baseline
                def append(body):
                    with log.open('a') as out:
                        out.write((wall+timedelta(seconds=synthetic-baseline)).strftime('[%a %b %d %H:%M:%S %Y] ')+body+'\n')
                    return reader.poll(now=synthetic)
                append('You have entered '+p.zone_name+'.')
                x,y=destination.goal
                append(f'Your Location is {y}, {x}, {z}');first=reader.latest
                synthetic+=.5
                append(f'Your Location is {y}, {x}, {z}');second=reader.latest
                # Planning time advances from the synthetic final observation.
                planning=time.monotonic()
                clock=lambda:synthetic+time.monotonic()-planning
                local_wall=lambda:wall+timedelta(seconds=clock()-baseline)
                result=p.plan_probe_envelope(reader,first,second,probe_kind='forward',
                    motion_record_id='synthetic-no-calibration',bounds=bounds,
                    vertical_window=1.,maximum_source_z_difference=1.,
                    owner_binding=('synthetic-copied-camp-audit',),
                    binding_reader=lambda:('synthetic-copied-camp-audit',),
                    released_at=baseline-.2,record_id='offline-'+identifier,
                    clock=clock,local_wall_clock=local_wall,maximum_seconds=30.,
                    allow_overhead_boundary=True)
                row.update(accepted_geometry=True,evidence_sha256=result.evidence_sha256,
                    evidence=json.loads(result.evidence_bytes))
        except ValueError as error:row['refusal']=str(error)
        row['seconds']=time.monotonic()-began;rows.append(row)
    for name,pin in DATA_PINS.items():checked_bytes(STORE/'owner-route-data'/DATA_NAME/name,pin)
    project=Path(__file__).resolve().parents[1]
    code_pins={str(p.relative_to(project)):sha256(p.read_bytes()).hexdigest()
        for p in (Path(__file__).resolve(),*sorted((project/'eql_automation').glob('*.py')))}
    record=dict(format='eql-copied-camp-probe-audit-v1',synthetic_observations=True,
        code_sha256=code_pins,motion_body_hypotheses=asdict(bounds),
        current_character_position=False,source_data_pins=DATA_PINS,rows=rows,
        game_input_sent=False,movement_authorized=False,real_client_accepted=False)
    raw=(json.dumps(record,indent=2,allow_nan=False)+'\n').encode()
    with args.output.open('xb') as out:out.write(raw)
    args.output.chmod(0o600)
    print(json.dumps(dict(path=str(args.output),sha256=sha256(raw).hexdigest(),
        rows=[{k:v for k,v in row.items() if k not in {'evidence','package_xy'}} for row in rows])))


if __name__=='__main__':main()
