#!/usr/bin/env python3
"""Bounded copied-data topology audit of an explicitly chosen stair sequence."""
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
import argparse
import json
import os
import resource
import signal
import sys
import time

PROJECT = Path(__file__).resolve().parents[1]
STORE = Path.home()/'.local/share/eql-automation'
sys.path[:0] = [str(PROJECT), str(STORE/'owner-assist/0.39.4')]

from eql_automation.crushbone_assets import DATA_NAME, DATA_PINS, load_crushbone_assets
from eql_automation.ground_sweep import area, clip
from eql_automation.native_region_policy import encoded
from eql_automation.owner_route_assets import checked_bytes
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import rational
from eql_automation.source_floor_components import SourceFloorComponents
from eql_automation.source_step import expanded
from tools.source_stair_topology import audit_stair_topology


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prior', type=Path, required=True)
    parser.add_argument('--prior-sha256', required=True)
    parser.add_argument('--first-step', type=int, required=True)
    parser.add_argument('--last-step', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if (args.output.exists() or args.output.is_symlink()
            or args.output.parent.resolve() != (STORE/'nav-candidates').resolve()
            or not 0 <= args.first_step < args.last_step < 32):
        parser.error('New private output and explicit bounded step range required')
    os.umask(0o077); os.nice(19)
    resource.setrlimit(resource.RLIMIT_CPU, (20, 25))
    began = time.monotonic()
    def timeout(*_):
        raise TimeoutError('Offline staircase topology budget exhausted')
    signal.signal(signal.SIGALRM, timeout); signal.signal(signal.SIGXCPU, timeout)
    signal.alarm(90)
    pins = {str(p.relative_to(PROJECT)):sha256(p.read_bytes()).hexdigest()
            for p in (Path(__file__).resolve(), PROJECT/'tools/source_stair_topology.py',
                      *sorted((PROJECT/'eql_automation').glob('*.py')))}
    record = dict(format='eql-offline-stair-topology-v1', data_sha256=DATA_PINS,
        code_sha256=pins, prior_sha256=args.prior_sha256,
        first_step=args.first_step, last_step=args.last_step,
        completed=False, input_authorized=False, real_client_accepted=False,
        executable_itinerary=False, game_input_sent=False)
    try:
        prior = json.loads(checked_bytes(args.prior, args.prior_sha256))
        if prior['data_sha256'] != DATA_PINS:
            raise ValueError('Prior uses different copied client data')
        steps = [edge for edge in prior['proposal']['edges'] if edge['step']]
        chosen = steps[args.first_step:args.last_step+1]
        if len(chosen) != args.last_step-args.first_step+1:
            raise ValueError('Unknown proposed stair sequence')
        assets = load_crushbone_assets(STORE/'owner-route-data'/DATA_NAME, native_planning=True)
        source = assets.planner.source
        graph = SourceFloorComponents(tuple(source.sources), inventory_sha256=source.wld_sha256)
        components = [graph.components[tuple(chosen[0]['origin'])]]
        for edge in chosen:
            if graph.components[tuple(edge['origin'])] != components[-1]:
                raise ValueError('Proposed stairs skip a source component')
            components.append(graph.components[tuple(edge['destination'])])
        start = tuple(chosen[0]['step']['start']); end = tuple(chosen[-1]['step']['end'])
        radius = float(prior['guide']['radius'])
        boundary = expanded(swept_square(start, end, radius))
        low = tuple(min(p[k] for p in boundary) for k in range(2))
        high = tuple(max(p[k] for p in boundary) for k in range(2))
        # Explicit all-height inventory from the already loaded client source.
        # This is a separate bounded topology analysis, never a runtime query.
        local = tuple(s for s, minimum, maximum in zip(source.sources, source.source_minimum,
                      source.source_maximum) if all(minimum[k] <= high[k] and maximum[k] >= low[k]
                                                   for k in range(2)))
        groups = tuple(tuple(key for key, (polygon, _, _) in graph.faces.items()
                             if graph.components[key] == component
                             and area(clip(boundary, rational(polygon))) > 0)
                       for component in components)
        record.update(start=start, end=end, radius=radius, source_count=len(local),
            components=components, group_counts=[len(group) for group in groups])
        result = audit_stair_topology(local, groups, start=start, end=end, radius=radius)
        record.update(topology=result, topology_sha256=sha256(encoded(result)).hexdigest(),
                      source_faces=[asdict(s) for s in local])
    except (ValueError, TimeoutError) as error:
        record['refusal'] = str(error)
    signal.alarm(0)
    for name, pin in pins.items():
        checked_bytes(PROJECT/name, pin)
    for name, pin in DATA_PINS.items():
        checked_bytes(STORE/'owner-route-data'/DATA_NAME/name, pin)
    checked_bytes(args.prior, args.prior_sha256)
    record.update(completed=True, seconds=time.monotonic()-began)
    with args.output.open('xb') as stream:
        stream.write(encoded(record))
    print(json.dumps(dict(output=str(args.output), sha256=sha256(args.output.read_bytes()).hexdigest(),
        reason=record.get('refusal', record.get('topology', {}).get('reason')),
        treads=len(record.get('topology', {}).get('treads', [])),
        risers=len(record.get('topology', {}).get('risers', [])),
        seconds=record['seconds'])), flush=True)


if __name__ == '__main__':
    main()
