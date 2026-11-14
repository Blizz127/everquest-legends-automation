#!/usr/bin/env python3
"""Compare native-style point results at saved exact BSP refusal witnesses.

Vertices and their centroid are finite diagnostic samples. They cannot certify
a volume, erase a missing region or establish the live actor's query position.
"""
from collections import Counter
from dataclasses import asdict
from fractions import Fraction
from hashlib import sha256
import argparse
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from eql_automation.bsp_probe import BspPointLookup
from eql_automation.client_bsp_probe import ClientBspTreeView, ENGINE_SHA256
from eql_automation.pfs_archive import PFSArchive
from eql_automation.wld_inventory import WLDInventory

STORE = Path.home()/'.local/share/eql-automation'
PARENT = STORE/'nav-candidates/crushbone-clipped-bsp-all-phases-0.42.2.json'
ARCHIVE = STORE/'client-data/retail-full/assets/crushbone.s3d'
DLL = STORE/'client-data/font-runtime-20261114T0706Z/EQGraphics.dll'
PINS = {
    PARENT: '23e220cf97d72d75c2db39171222941453ecfb1b80ab8903750b1251c082a224',
    ARCHIVE: 'a2591482aac0a478caec1d79bf662a3f0f93d4ef2dc423be8f7591fe6d45e36f',
    DLL: ENGINE_SHA256,
}


def run(output):
    pins = dict(PINS)
    for p in (Path(__file__), PROJECT/'eql_automation/client_bsp_probe.py',
              PROJECT/'eql_automation/bsp_probe.py', PROJECT/'eql_automation/region_audit.py',
              PROJECT/'eql_automation/wld_inventory.py', PROJECT/'eql_automation/pfs_archive.py'):
        pins[p] = sha256(p.read_bytes()).hexdigest()

    def verify():
        for path, expected in pins.items():
            if path.is_symlink() or sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError('Changed copied input: '+str(path))

    verify()
    parent = json.loads(PARENT.read_text())
    wld = WLDInventory(PFSArchive(ARCHIVE).read_member('crushbone.wld'))
    if wld.sha256 != parent['source_wld_sha256']:
        raise ValueError('Different source WLD')
    native = ClientBspTreeView.from_wld(wld)
    conservative = BspPointLookup(wld)
    rows, centroid_counts, vertex_counts = [], Counter(), Counter()
    for cell_index, cell in enumerate(parent['cells']):
        if cell['clipped']['candidate']:
            continue
        # The retained audit contains the first refused piece; this is not an
        # enumeration of all unknown subvolumes in the original footprint.
        piece = next(p for p in cell['clipped']['pieces']
                     if not p['traversal']['candidate'])
        traversal = piece['traversal']
        if traversal['reason'] != 'missing_bsp_child':
            raise ValueError('Unexpected refusal; do not reinterpret it')
        vertices = tuple(tuple(Fraction(v) for v in p)
                         for p in traversal['refused_vertices_exact'])
        centroid = tuple(sum(p[k] for p in vertices)/len(vertices) for k in range(3))
        point = tuple(float(v) for v in centroid)
        result = native.probe_tree(*point)
        centroid_counts[result.reason] += 1
        vertex_results = []
        for vertex in vertices:
            probe = native.probe_tree(*(float(v) for v in vertex))
            vertex_counts[probe.reason] += 1
            vertex_results.append(dict(native_return=probe.native_return,
                                       region_id=probe.region_id, reason=probe.reason))
        rows.append(dict(cell=cell_index, selected_id=piece['selected_id'],
            centroid_exact=[str(v) for v in centroid],
            native_centroid=asdict(result),
            legacy_centroid=asdict(conservative.probe(*point)),
            copied_candidate_labels=sorted(conservative.labels_by_region.get(result.region_id, ())),
            vertex_results=vertex_results))
    verify()
    record = dict(format='eql-crushbone-native-point-diagnostic-v1',
        source_wld_sha256=wld.sha256, pins={str(p):v for p,v in pins.items()},
        scope='vertices and centroid of each first-reported ordinary-cell null volume',
        centroid_results=dict(centroid_counts), vertex_results=dict(vertex_counts),
        cell_count=len(rows), rows=rows, bounds_checked=False, live_mxcsr_verified=False,
        upstream_actor_position_verified=False, unknowns_reclassified=False,
        exhaustive_volume_classification=False, route_accepted=False,
        real_client_accepted=False, game_input_sent=False)
    with output.open('x') as stream:
        stream.write(json.dumps(record, indent=2)+'\n')
    return dict(path=str(output), sha256=sha256(output.read_bytes()).hexdigest(),
                cells=len(rows), centroid_results=dict(centroid_counts),
                vertex_results=dict(vertex_counts), route_accepted=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=STORE/
        'nav-candidates/crushbone-client-bsp-points-0.42.3.json')
    args = parser.parse_args()
    print(json.dumps(run(args.output), indent=2))
