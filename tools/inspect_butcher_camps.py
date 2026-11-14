#!/usr/bin/env python3
"""Check copied Butcherblock camp footprints and one retained short spoke.

This offline recipe checks terrain lineage, both static libraries and body
region metadata. It neither creates an executable itinerary nor changes the
Crushbone-only runtime policy. Map/old mesh heights never select a floor.
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

PROJECT = Path(__file__).resolve().parents[1]
STORE = Path.home()/'.local/share/eql-automation'
sys.path[:0] = [str(PROJECT), str(STORE/'owner-assist/0.39.4')]

from eql_automation.bsp_floor_guard import check_source_body_bsp
from eql_automation.bsp_volume import BspVolumeView
from eql_automation.camp_annotations import read_camp_annotations
from eql_automation.client_region_classification import ClientBspClassificationView
from eql_automation.ground_sweep_view import GroundSweepView
from eql_automation.native_body_regions import classify_source_body_regions
from eql_automation.native_region_policy import encoded
from eql_automation.owner_route_assets import checked_bytes, TRANSFORM_PIN
from eql_automation.pfs_archive import PFSArchive
from eql_automation.portal_precision_view import PortalPrecisionView
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import SourceFloorChain
from eql_automation.static_floor_guard import check_source_static_floor
from eql_automation.static_source_view import StaticSourceView
from eql_automation.wld_inventory import WLDInventory

PINS = {
    'client-data/retail-full/assets/butcher.s3d': 'af504e71d3f3497b5eef037d86475ba96985b261d96f6469915e058e05308839',
    'client-data/retail-full/assets/butcher_obj.s3d': 'ad4c886395c9af7f3de17be1c1a24785e295f892097b8e5785eec670a089c047',
    'client-data/retail-full/assets/butcher_2_obj.s3d': 'cb5cabede79b53f9b884c15712ec07225f5ca81e1093be36f7d3d12b8ea03ece',
    'client-data/retail-full/maps/Solo_Leveling/butcher_3.txt': '96b4c8c3efd7d8209fa4820008b4db4e766195cfa7544ea39aca7b3e5341bf1d',
    'navmesh/nov12-7e3cd28-store/butcher.npz': '4e450cdbca7ab6cc44a7973eca11929d7b920db49f6c51ad00a6337b5ee58bde',
    'navmesh/nov12-7e3cd28-store/butcher.json': '64f3b3d8673a61424268172b3b9c6989921c77e49d5b0f4d55fa034f2d8ef792',
    'nav-candidates/butcher.map-alignment.json': 'f96642d193df59984c158167c67d8213f8acb11bbfab1e5f23dd1e3a5d1c25ba',
    'nav-candidates/butcher-kaladim-roam-ring-bsp-wldframe-pinned-0.41.40.json': '48d05c38ae76666d54739e3b7674e623d55297b88fa1ec89d65979c7d338d066',
}


def run(output):
    from eqnav import zonegeom
    began = time.monotonic()
    code = {str(p.relative_to(PROJECT)): sha256(p.read_bytes()).hexdigest()
            for p in (Path(__file__), *sorted((PROJECT/'eql_automation').glob('*.py')))}
    def verify():
        for path, pin in PINS.items():
            checked_bytes(STORE/path, pin)
        for path, pin in code.items():
            checked_bytes(PROJECT/path, pin)
        checked_bytes(Path(zonegeom.__file__), TRANSFORM_PIN)
    verify()
    record = dict(format='eql-offline-butcher-camp-source-v1', data_sha256=PINS,
        code_sha256=code, transform_sha256=TRANSFORM_PIN, completed=False,
        route_accepted=False, executable_itinerary=False, game_input_sent=False,
        input_authorized=False, real_client_accepted=False,
        current_character_observation=False, label_z_used_for_floor_selection=False,
        mesh_z_used_for_floor_selection=False, body_radius=1.2, body_height=6.)
    try:
        asset = STORE/'client-data/retail-full/assets'
        archive = PFSArchive(asset/'butcher.s3d')
        terrain = WLDInventory(archive.read_member('butcher.wld'))
        objects = WLDInventory(archive.read_member('objects.wld'))
        libraries = tuple(WLDInventory(PFSArchive(asset/(n+'.s3d')).read_member(n+'.wld'))
                          for n in ('butcher_obj', 'butcher_2_obj'))
        alignment = json.loads((STORE/'nav-candidates/butcher.map-alignment.json').read_bytes())
        if (alignment['archive_sha256'] != archive.sha256
                or alignment['wld_sha256'] != terrain.sha256
                or alignment['best_map_to_wld_xy_transform'] != '-y,-x'
                or alignment['frame_supported_by_rounded_vertex_matches'] is not True):
            raise ValueError('Copied map frame lacks matching source alignment')
        static = StaticSourceView.from_wld(objects, libraries,
            terrain_fragment_max=max(f.index for f in terrain.fragments),
            transform=zonegeom.place_vertices, transform_sha256=TRANSFORM_PIN)
        mesh = STORE/'navmesh/nov12-7e3cd28-store/butcher.npz'
        ground = GroundSweepView.load(mesh, zone='butcher')
        source = PortalPrecisionView(ground, mesh, asset/'butcher.s3d', zone='butcher')
        bsp = BspVolumeView.from_wld(terrain)
        classifier = ClientBspClassificationView.from_wld(terrain)
        record.update(source_wld_sha256=terrain.sha256, objects_wld_sha256=objects.sha256,
            library_wld_sha256=[w.sha256 for w in libraries],
            static_inventory_sha256=static.inventory_sha256,
            bsp_inventory_sha256=bsp.inventory_sha256,
            classification_inventory_sha256=classifier.inventory_sha256,
            source_faces=len(source.sources), static_faces=len(static.sources),
            placements=len(static.identities), excluded_placements=static.excluded)
        print(json.dumps(dict(stage='loaded', source_faces=len(source.sources),
            static_faces=len(static.sources), placements=len(static.identities))), flush=True)

        def seed(point):
            proposal = source.propose_unique_diffuse_floor(point, body_height=6.)
            evidence = dict(kind='offline_point_hypothesis', proposal=asdict(proposal),
                            current_character_observation=False)
            chain = SourceFloorChain(inventory_sha256=terrain.sha256,
                seed_evidence_sha256=sha256(encoded(evidence)).hexdigest(),
                seed_ids=proposal.selected_ids, body_height=6.)
            return chain, evidence

        def cell(chain, start, end):
            footprint = swept_square(start, end, 1.2)
            local = source.source_faces_for_footprint(footprint)
            # The first cap creates the checked prefix. Forking is supported
            # only after that cap has been accepted by SourceFloorChain.
            branch = chain if chain.previous is None else chain.fork()
            floor = branch.advance(footprint, local)
            row = dict(start=start, end=end, footprint=footprint, terrain=asdict(floor),
                       terrain_static_passed=False, route_accepted=False)
            if floor.candidate:
                placed = check_source_static_floor(floor, footprint, local, static)
                row['static'] = asdict(placed)
                if placed.candidate:
                    row.update(terrain_static_passed=True,
                        start_floor_height=branch.floor_at(start)[0],
                        end_floor_height=branch.floor_at(end)[0],
                        bsp=asdict(check_source_body_bsp(floor, footprint, local, bsp, clip_branches=True)),
                        native=asdict(classify_source_body_regions(floor, footprint, local,
                            static, classifier, source_wld_sha256=terrain.sha256)))
            return row, branch

        annotations = read_camp_annotations((STORE/'client-data/retail-full/maps/Solo_Leveling/butcher_3.txt').read_bytes())
        record['annotations'] = []
        for annotation in annotations:
            point = tuple(-v for v in annotation.map_xyz[:2])
            row = dict(annotation=asdict(annotation), package_xy=point,
                       level_suitability_verified=False, usable_destination=False)
            try:
                row['source_intersections'] = [asdict(h) for h in source.source_hits_at(point)]
                chain, row['seed'] = seed(point)
                row['cap'], _ = cell(chain, point, point)
            except ValueError as error:
                row['refusal'] = str(error)
            record['annotations'].append(row)
        prior_path = STORE/'nav-candidates/butcher-kaladim-roam-ring-bsp-wldframe-pinned-0.41.40.json'
        prior = json.loads(prior_path.read_bytes())
        anchor = prior['copied_anchor_yxz']
        end = next(r['location_yxz'] for r in prior['roam_points'] if r['returned_index'] == 2)
        start, goal = (anchor[1], anchor[0]), (end[1], end[0])
        if sum(row['package_xy'] == start for row in record['annotations']) != 1:
            raise ValueError('Retained spoke start does not match one exact copied map annotation')
        chain, evidence = seed(start)
        spoke = dict(start=start, goal=goal, prior_sha256=PINS[str(prior_path.relative_to(STORE))],
                     prior_heights_used=False, seed=evidence, cells=[], completed=False,
                     route_accepted=False, executable_itinerary=False)
        record['spoke'] = spoke
        count = math.ceil(math.dist(start, goal)/2.)
        points = [start]+[tuple(start[k]+(goal[k]-start[k])*i/count for k in range(2))
                          for i in range(1, count)]+[goal]
        for a, b in [(start, start), *zip(points, points[1:])]:
            row, chain = cell(chain, a, b)
            spoke['cells'].append(row)
            if not row['terrain_static_passed']:
                break
        spoke['completed'] = len(spoke['cells']) == count+1 and all(r['terrain_static_passed'] for r in spoke['cells'])
    except (ValueError, TimeoutError) as error:
        record['refusal'] = str(error)
    signal.setitimer(signal.ITIMER_REAL, 0)
    verify()
    record.update(completed=True, seconds=time.monotonic()-began)
    with output.open('x') as stream:
        json.dump(record, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps(dict(output=str(output), sha256=sha256(output.read_bytes()).hexdigest(),
        seconds=record['seconds'], refusal=record.get('refusal'),
        annotations=len(record.get('annotations', [])),
        spoke_source_complete=record.get('spoke', {}).get('completed', False))), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if (args.output.exists() or args.output.is_symlink()
            or args.output.parent.resolve() != (STORE/'nav-candidates').resolve()):
        parser.error('Use a new output directly in the private nav-candidates store')
    os.umask(0o077); os.nice(19)
    def expired(*_):
        raise TimeoutError('Offline Butcher camp CPU/wall budget exhausted')
    signal.signal(signal.SIGALRM, expired); signal.signal(signal.SIGXCPU, expired)
    resource.setrlimit(resource.RLIMIT_CPU, (60, 65))
    signal.setitimer(signal.ITIMER_REAL, 240)
    run(args.output)
