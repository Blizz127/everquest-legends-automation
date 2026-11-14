#!/usr/bin/env python3
"""Reconcile one pinned GFay replay footprint against copied source terrain.

This is a local geometry experiment. It never changes the source archive,
navmesh, route plan, client or input state. Its virtual seam correction applies
only to this footprint, not to a whole portal or a live route.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys
import time

PROJECT = Path(__file__).resolve().parents[1]
STORE = Path.home() / ".local/share/eql-automation"
ARCHIVE = STORE / "client-data/retail-full/assets/gfaydark.s3d"
REPLAY = STORE / "nav-candidates/gfay-full-ground-sweep-replay-0.41.51-v2.json"
SEAM = STORE / "nav-candidates/gfay-detail-seam-gap-0.41.51.json"
MESH = STORE / "navmesh/nov12-7e3cd28-store/gfaydark.npz"
PINS = {
    ARCHIVE: "ea95f51a2d4645410223d24cc7da9eb0e7095310c6e9f8756e8c51d67df13d9f",
    REPLAY: "77b97911957c32a6d1c0ef8a3b1fec365ce61934ed0755cfc61b71f96eeb0d8a",
    SEAM: "d938fc7956194d8bf20450fa02699c1c2ee90da03a150acbe439f480e8b25fa6",
    MESH: "5f8e16c5bcd2221ba273f681750ca480349780524d23609c059a3e817df6abd9",
    MESH.with_suffix('.json'): "ac9591eb63e1394363ad37d7d0ca6609a1ebe11fd8786bedb5b165b833e2eb82",
}


def run(output):
    began = time.monotonic()
    sys.path.insert(0, str(PROJECT))
    from eql_automation.ground_sweep import GroundFace, area, check_ground_coverage, clip, cross, hull
    from eql_automation.ground_sweep_view import GroundSweepView
    from eql_automation.map_alignment import _triangle_height
    from eql_automation.material_audit import mesh_face_materials
    from eql_automation.mesh_geometry import read_meshes
    from eql_automation.pfs_archive import PFSArchive
    from eql_automation.wld_inventory import WLDInventory
    pins = dict(PINS)
    for name in ('ground_sweep', 'ground_sweep_view', 'map_alignment', 'material_audit',
                 'mesh_geometry', 'pfs_archive', 'wld_inventory'):
        path = PROJECT / 'eql_automation' / (name + '.py')
        pins[path] = sha256(path.read_bytes()).hexdigest()
    pins[Path(__file__)] = sha256(Path(__file__).read_bytes()).hexdigest()
    def verify():
        if any(p.is_symlink() or sha256(p.read_bytes()).hexdigest() != h for p, h in pins.items()):
            raise ValueError('Pinned seam experiment input changed')
    verify()
    failure = json.loads(REPLAY.read_text())['sweep_failure']
    if failure['step'] != 18 or failure['result']['reason'] != 'uncovered_ground_area':
        raise ValueError('Unexpected diagnostic footprint')
    footprint = tuple(map(tuple, failure['footprint']))
    reference = tuple(failure['reference'])
    source_footprint = hull((p[1], p[0]) for p in footprint)
    source_reference = (reference[1], reference[0], reference[2])
    wld = WLDInventory(PFSArchive(ARCHIVE).read_member('gfaydark.wld'))
    meshes = read_meshes(wld)
    fragments = {f.index: f for f in wld.fragments}
    overlaps = []
    for mesh in meshes:
        vertices = tuple(mesh.vertex(i) for i in range(len(mesh.raw_vertices)))
        materials = None
        for index, face in enumerate(mesh.triangles):
            tri = tuple(vertices[i] for i in (face.a, face.b, face.c))
            xy = hull(p[:2] for p in tri)
            if len(xy) != 3 or area(clip(source_footprint, xy)) <= 1e-10:
                continue
            if materials is None:
                materials = mesh_face_materials(wld, fragments[mesh.fragment_index])
            material = materials[index]
            denominator = cross(*xy)
            barycentrics = tuple((cross(xy[1], xy[2], p) / denominator,
                                 cross(xy[2], xy[0], p) / denominator,
                                 cross(xy[0], xy[1], p) / denominator) for p in source_footprint)
            minimum = min(min(b) for b in barycentrics)
            heights = tuple(_triangle_height(*p, tri) for p in source_footprint)
            a, b, c = tri
            det = cross(a, b, c)
            dzdx = ((b[2]-a[2])*(c[1]-a[1]) - (c[2]-a[2])*(b[1]-a[1])) / det
            dzdy = ((b[0]-a[0])*(c[2]-a[2]) - (c[0]-a[0])*(b[2]-a[2])) / det
            source_z = _triangle_height(*source_reference[:2], tri)
            overlaps.append({'fragment': mesh.fragment_index, 'face': index, 'vertices_wld': tri,
                'flag': face.flag, 'material': material.material_name, 'material_class': material.material_class,
                'clipped_area': area(clip(source_footprint, xy)), 'minimum_vertex_barycentric': minimum,
                'strictly_contains_entire_convex_footprint': minimum > 0,
                'footprint_vertex_source_heights': heights, 'source_grade': math.hypot(dzdx, dzdy),
                'source_reference_z': source_z,
                'baked_minus_source_reference_z': None if source_z is None else reference[2] - source_z})
    supported = (len(overlaps) == 1 and overlaps[0]['strictly_contains_entire_convex_footprint']
                 and overlaps[0]['flag'] == 0 and overlaps[0]['material_class'] == 'Diffuse')
    view = GroundSweepView.load(MESH, zone='gfaydark')
    seam = json.loads(SEAM.read_text())
    west, east = seam['west_boundary_x'], seam['east_boundary_x']
    midpoint = (west + east) / 2
    component = int(view.components[31668])
    window = max(math.dist(reference[:2], p) for p in footprint) + .05
    before, local_ids = view.check(footprint, reference=reference, component=component, vertical_window=window)
    if before.reason != 'uncovered_ground_area' or list(local_ids) != failure['detail_ids']:
        raise ValueError('Original copied-detail failure did not reproduce')
    corrections, faces = [], []
    for detail_id in local_ids:
        polygon = int(view.polys[detail_id])
        vertices = []
        for vertex_index, vertex in enumerate(view.triangles[detail_id]):
            point = tuple(float(v) for v in vertex)
            if supported and ((polygon == 31668 and point[0] == west) or
                              (polygon == 32479 and point[0] == east)):
                corrected = (midpoint, point[1], point[2])
                corrections.append({'detail': detail_id, 'vertex': vertex_index,
                                    'before': point, 'after': corrected})
                point = corrected
            vertices.append(point)
        faces.append(GroundFace(tuple(vertices), int(view.areas[polygon]), int(view.components[polygon])))
    after = check_ground_coverage(footprint, tuple(faces), reference=reference,
                                  component=component, vertical_window=window)
    verify()
    record = {'format': 'eql-local-source-seam-experiment-v1', 'zone': 'gfaydark',
        'scope': 'single_failed_footprint_only', 'source_continuity_supported': supported,
        'source_meshes': len(meshes), 'source_faces': sum(len(m.triangles) for m in meshes),
        'source_wld_sha256': wld.sha256, 'source_overlaps': overlaps,
        'helper_to_source_frame': 'WLD_X=helper_Y,WLD_Y=helper_X,WLD_Z=helper_Z',
        'footprint_helper': footprint, 'reference_helper': reference,
        'original_ground_check': asdict(before), 'virtual_local_ground_check': asdict(after),
        'local_vertex_corrections': corrections, 'seam_width': east-west,
        'maximum_virtual_xy_shift': (east-west)/2, 'virtual_z_shift': 0.,
        'not_checked': ['actual_collision', 'walls_and_headroom', 'BSP_hazards', 'dynamic_obstacles',
                        'body_dimensions', 'live_alignment_and_motion', 'other_portal_footprints'],
        'game_input_sent': False, 'input_authorized': False, 'real_client_accepted': False,
        'source_or_mesh_modified': False, 'pins': {str(p): h for p, h in pins.items()},
        'seconds': time.monotonic()-began}
    with output.open('x') as out:
        json.dump(record, out, indent=2); out.write('\n')
    print(json.dumps({'artifact': str(output), 'sha256': sha256(output.read_bytes()).hexdigest(),
        'source_continuity_supported': supported, 'overlapping_source_faces': len(overlaps),
        'original': before.reason, 'virtual_local': after.reason, 'seconds': record['seconds']}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.expanduser()
    if (output.parent.resolve() != (STORE/'nav-candidates').resolve() or output.exists()
            or output.is_symlink() or output.suffix != '.json'):
        parser.error('Use a new private nav-candidates JSON')
    os.umask(0o077)
    os.nice(15)
    run(output)


if __name__ == '__main__':
    main()
