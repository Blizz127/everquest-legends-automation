#!/usr/bin/env python3
"""Check a retained pre-line XY proposal and its short GFay trigger approach.

This uses copied terrain/static/native data only. It does not connect Goblin
Camp, send input, accept a server destination or reuse a mesh/label Z as floor.
"""
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
import argparse
import json
import math
import os
import resource
import signal
import sys
import time

PROJECT=Path(__file__).resolve().parents[1]
STORE=Path.home()/'.local/share/eql-automation'
sys.path[:0]=[str(PROJECT),str(STORE/'owner-assist/0.39.4')]

from eql_automation.butcher_assets import DATA_NAME, DATA_PINS, load_butcher_assets
from eql_automation.butcher_crossing_assets import load_butcher_crossing
from eql_automation.native_crossing_policy import check_source_crossing_cell
from eql_automation.native_region_policy import encoded
from eql_automation.owner_route_assets import checked_bytes
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain

PRIOR_NAME='butcher-kaladim-to-gfay-complex-select-only-20261113T2248Z.json'
PRIOR_PIN='5c7babe22742d9d1c9ae4d293e2f0a9f52ace21bd8687702260f1cedbd70fad8'


def inspect(output, *, stop_at_transition=False):
    began=time.monotonic()
    pins={str(p.relative_to(PROJECT)):sha256(p.read_bytes()).hexdigest()
        for p in (Path(__file__),*sorted((PROJECT/'eql_automation').glob('*.py')))}
    record=dict(format='eql-offline-butcher-crossing-inspection-v1', code_sha256=pins,
        client_data_pins=DATA_PINS, prior_sha256=PRIOR_PIN, completed=False,
        geometry_candidate=False, synthetic_floor_seed=True,
        stop_at_transition=stop_at_transition,
        current_character_observation=False, goblin_connector_checked=False,
        label_z_used_for_floor_selection=False, mesh_z_used_for_floor_selection=False,
        destination_server_verified=False, game_input_sent=False,
        input_authorized=False, runtime_ready=False, real_client_accepted=False)
    try:
        root=STORE/'owner-route-data'/DATA_NAME
        assets=load_butcher_assets(root,native_planning=True); p=assets.planner
        crossing=load_butcher_crossing(root,assets)
        record['descriptor']=crossing.record()
        prior=json.loads(checked_bytes(STORE/'nav-candidates'/PRIOR_NAME,PRIOR_PIN))
        # The old path is used as an XY proposal, never a floor certificate.
        path=prior['unverified_points']
        start=tuple(float(v) for v in path[-1][:2]); goal=crossing.goal_xy
        record.update(start=start,goal=goal)
        record['source_intersections']=[dict(point=tuple(point[:2]),
            hits=[asdict(h) for h in p.source.source_hits_at(tuple(point[:2]))])
            for point in (*path[-5:], goal)]
        # Preserve the production point-proposal refusal. An isolated offline
        # experiment may nominate the sole Diffuse layer as a hypothesis, but
        # every Boundary face remains in the full occupancy query below. This
        # does not broaden the live current-start/height producer.
        try:
            proposal=asdict(p.source.propose_unique_diffuse_floor(start,body_height=6.))
        except ValueError as error:
            record['production_floor_proposal_refusal']=str(error)
            hits=p.source.source_hits_at(start)
            floors=tuple(h for h in hits if h.flag==0 and h.material_class=='Diffuse')
            if not floors or max(h.height for h in floors)-min(h.height for h in floors)>1e-7:
                raise ValueError('No single Diffuse layer for an offline hypothesis')
            proposal=dict(selected_ids=tuple((h.fragment,h.face) for h in floors),
                height=floors[0].height, all_intersections=[asdict(h) for h in hits],
                hypothesis_only=True, faces_excluded_from_collision=0)
        seed=dict(format='synthetic_source_floor_hypothesis', point=start,
            proposal=proposal, source_wld_sha256=p.source.wld_sha256,
            current_character_observation=False)
        record['seed']=seed
        chain=SourceFloorChain(inventory_sha256=p.source.wld_sha256,
            seed_evidence_sha256=sha256(encoded(seed)).hexdigest(),
            seed_ids=tuple(tuple(k) for k in proposal['selected_ids']),body_height=6.)
        cap=swept_square(start,start,1.2)
        first=chain.advance(cap,p.source.source_faces_for_footprint(cap))
        if not first.candidate:raise ValueError('Initial source cap: '+first.reason)
        count=max(1,math.ceil(math.dist(start,goal)/2.))
        points=[start]+[tuple(start[k]+(goal[k]-start[k])*i/count for k in (0,1))
                       for i in range(1,count)]+[goal]
        record['cells']=[]
        for a,b in ((start,start),*zip(points,points[1:])):
            chain,cell=check_source_crossing_cell(chain,a,b,radius=1.2,
                terrain=p.source,static=p.static,bsp=p.bsp,policy=crossing.policy)
            value=cell.record()
            record['cells'].append(dict(sha256=cell.sha256,**value))
            if (stop_at_transition and b!=start
                    and value['native']['possible_flags']==[0x80000000]):
                # This is an offline endpoint proposal inside the exact native
                # label, not a server arrival or permission to move through it.
                chain,cap=check_source_crossing_cell(chain,b,b,radius=1.2,
                    terrain=p.source,static=p.static,bsp=p.bsp,policy=crossing.policy)
                if cap.record()['native']['possible_flags']!=[0x80000000]:
                    raise ValueError('Final cap no longer lies wholly in the expected native label')
                record['cells'].append(dict(sha256=cap.sha256,**cap.record()))
                record.update(region_center_target=goal,goal=b,
                    endpoint_reason='first_complete_body_cell_and_cap_in_exact_native_label')
                break
        if stop_at_transition and 'endpoint_reason' not in record:
            raise ValueError('No complete body cell in the expected transition before the proposed endpoint')
        record['geometry_candidate']=True
        record['possible_transition_regions']=sorted({r for cell in record['cells']
            for r in cell['possible_transition_regions']})
    except (ValueError,TimeoutError) as error:
        record['refusal']=str(error)
    signal.setitimer(signal.ITIMER_REAL,0)
    for name,pin in pins.items():checked_bytes(PROJECT/name,pin)
    for name,pin in DATA_PINS.items():checked_bytes(STORE/'owner-route-data'/DATA_NAME/name,pin)
    checked_bytes(STORE/'nav-candidates'/PRIOR_NAME,PRIOR_PIN)
    record.update(completed=True,seconds=time.monotonic()-began)
    with output.open('x') as stream:
        json.dump(record,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(output=str(output),sha256=sha256(output.read_bytes()).hexdigest(),
        geometry_candidate=record['geometry_candidate'],refusal=record.get('refusal'),
        cells=len(record.get('cells',[])),seconds=record['seconds'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--stop-at-transition',action='store_true',
        help='End at the first completely checked body cell inside the expected native label')
    args=parser.parse_args()
    if (args.output.exists() or args.output.is_symlink()
            or args.output.parent.resolve()!=(STORE/'nav-candidates').resolve()):
        parser.error('Use a new private nav-candidates output')
    os.umask(0o077);os.nice(19)
    def expired(*_):raise TimeoutError('Offline crossing CPU/wall budget exhausted')
    signal.signal(signal.SIGALRM,expired);signal.signal(signal.SIGXCPU,expired)
    resource.setrlimit(resource.RLIMIT_CPU,(60,65));signal.setitimer(signal.ITIMER_REAL,240)
    inspect(args.output,stop_at_transition=args.stop_at_transition)
