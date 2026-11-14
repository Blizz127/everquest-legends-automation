"""Pinned Butcherblock terrain, placements, BSP and copied camp annotations.

Nothing here sends input or accepts a route. Map level ranges are annotations;
actual mobs, suitability, current location and live movement remain unverified.
"""
from dataclasses import dataclass
import json
from pathlib import Path

from .bsp_detail_view import BspDetailMeshView
from .bsp_volume import BspVolumeView
from .camp_annotations import read_camp_annotations
from .client_region_classification import ClientBspClassificationView
from .current_route_start import CurrentStartPlanner
from .ground_sweep_view import GroundSweepView
from .location_log import unique_zone_ids_from_text
from .native_region_policy import NativeZeroRegionTrialPolicy
from .owner_route_assets import checked_bytes, TRANSFORM_PIN
from .pfs_archive import PFSArchive
from .portal_precision_view import PortalPrecisionView
from .static_source_view import StaticSourceView
from .wld_inventory import WLDInventory

DATA_NAME = 'butcher-camps-20261114'
DATA_PINS = {
    'butcher.npz': '4e450cdbca7ab6cc44a7973eca11929d7b920db49f6c51ad00a6337b5ee58bde',
    'butcher.json': '64f3b3d8673a61424268172b3b9c6989921c77e49d5b0f4d55fa034f2d8ef792',
    'butcher.s3d': 'af504e71d3f3497b5eef037d86475ba96985b261d96f6469915e058e05308839',
    'butcher_obj.s3d': 'ad4c886395c9af7f3de17be1c1a24785e295f892097b8e5785eec670a089c047',
    'butcher_2_obj.s3d': 'cb5cabede79b53f9b884c15712ec07225f5ca81e1093be36f7d3d12b8ea03ece',
    'ZoneNames.txt': '0a5c0ff78c452a1895af2ac3014254d29aee996a36a2d4e907e717e2180c422d',
    'butcher_3.txt': '96b4c8c3efd7d8209fa4820008b4db4e766195cfa7544ea39aca7b3e5341bf1d',
    'butcher.map-alignment.json': 'f96642d193df59984c158167c67d8213f8acb11bbfab1e5f23dd1e3a5d1c25ba',
}
WLD_PIN = 'd4c8db248f4b7d23fe714ff3dceedaf0c83696b178327efcf88d6091e35c722c'
OBJECTS_PIN = '605bc3b571a8779e62f09481c860b227024b0a97bd5877f4932517335682707b'
LIBRARY_PINS = ('06d6757279a3803a5c2b908b7f8bbce3c414bc802bd8271cb8558ac85acccc00',
                '36598801bbe072e6ac72c6b4e368a14eeecebb478da35f9a004e7352705f54df')
STATIC_PIN = '3d4f552ef2449335db63349f08e8d55f39f16b28224aa0f8a8a79f4897e92867'
BSP_PIN = 'ec67696e3d8e771792e85506b79727fdd245a2a168dca698fb156930d521ce55'
CLASSIFICATION_PIN = '094d40fc3169ab46ac4d75b29762e1d9d44b934e107a64bb263cff31e8c96d15'


@dataclass(frozen=True)
class ButcherblockAssets:
    planner: CurrentStartPlanner
    annotations: tuple
    classification: ClientBspClassificationView


def load_butcher_assets(root, *, native_planning=False):
    """Load full private copied views, verifying pins before and after parsing."""
    from eqnav import zonegeom
    if type(native_planning) is not bool:
        raise ValueError('Native planning opt-in must be explicit')
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Missing private Butcherblock data: '+str(root))

    def verify():
        for name, pin in DATA_PINS.items():
            checked_bytes(root/name, pin)
        checked_bytes(Path(zonegeom.__file__), TRANSFORM_PIN)
    verify()
    catalog = checked_bytes(root/'ZoneNames.txt', DATA_PINS['ZoneNames.txt'])
    unique, _ = unique_zone_ids_from_text(catalog.decode('latin-1'))
    names = [name for name, zone_id in unique.items() if zone_id == 68]
    if len(names) != 1:
        raise ValueError('Copied client catalog has no unique Butcherblock identity')
    alignment = json.loads(checked_bytes(root/'butcher.map-alignment.json',
                                         DATA_PINS['butcher.map-alignment.json']))
    if (alignment['zone'] != 'butcher'
            or alignment['best_map_to_wld_xy_transform'] != '-y,-x'
            or alignment['archive_sha256'] != DATA_PINS['butcher.s3d']
            or alignment['wld_sha256'] != WLD_PIN
            or alignment['frame_supported_by_rounded_vertex_matches'] is not True):
        raise ValueError('Copied Butcherblock map frame has no matching source alignment')
    annotations = read_camp_annotations(checked_bytes(root/'butcher_3.txt',
                                                       DATA_PINS['butcher_3.txt']))
    archive = PFSArchive(root/'butcher.s3d')
    object_archives = tuple(PFSArchive(root/(name+'.s3d')) for name in ('butcher_obj', 'butcher_2_obj'))
    terrain = WLDInventory(archive.read_member('butcher.wld'))
    placements = WLDInventory(archive.read_member('objects.wld'))
    libraries = tuple(WLDInventory(a.read_member(name+'.wld'))
                      for a,name in zip(object_archives, ('butcher_obj', 'butcher_2_obj')))
    if (archive.sha256 != DATA_PINS['butcher.s3d']
            or tuple(a.sha256 for a in object_archives) != tuple(DATA_PINS[n+'.s3d'] for n in ('butcher_obj', 'butcher_2_obj'))
            or (terrain.sha256, placements.sha256) != (WLD_PIN, OBJECTS_PIN)
            or tuple(w.sha256 for w in libraries) != LIBRARY_PINS):
        raise ValueError('Loaded Butcherblock source differs from pinned WLDs')
    static = StaticSourceView.from_wld(placements, libraries,
        terrain_fragment_max=max(f.index for f in terrain.fragments),
        transform=zonegeom.place_vertices, transform_sha256=TRANSFORM_PIN)
    mesh_path = root/'butcher.npz'
    mesh = BspDetailMeshView.load(mesh_path, zone='butcher')
    ground = GroundSweepView.load(mesh_path, zone='butcher')
    source = PortalPrecisionView(ground, mesh_path, root/'butcher.s3d', zone='butcher')
    bsp = BspVolumeView.from_wld(terrain)
    classification = ClientBspClassificationView.from_wld(terrain)
    if static.inventory_sha256 != STATIC_PIN or bsp.inventory_sha256 != BSP_PIN:
        raise ValueError('Loaded Butcherblock static/BSP inventory changed')
    if classification.inventory_sha256 != CLASSIFICATION_PIN:
        raise ValueError('Loaded native Butcherblock classification inventory changed')
    source.sources = tuple(source.sources)
    for array in (ground.triangles, ground.polys, ground.areas, ground.components,
                  ground.minimum, ground.maximum, source.source_minimum, source.source_maximum):
        array.flags.writeable = False
    planner = CurrentStartPlanner(mesh=mesh, ground=ground, source=source,
        static=static, bsp=bsp, zone_short_name='butcher', expected_zone_id=68,
        expected_zone_name=names[0], mesh_sha256=DATA_PINS['butcher.npz'],
        source_archive_sha256=DATA_PINS['butcher.s3d'], source_wld_sha256=WLD_PIN,
        static_inventory_sha256=STATIC_PIN,
        region_policy=(NativeZeroRegionTrialPolicy(DATA_PINS['butcher.npz'],
            DATA_PINS['butcher.s3d'], WLD_PIN, STATIC_PIN, BSP_PIN, CLASSIFICATION_PIN,
            classification, zone='butcher') if native_planning else None))
    verify()
    return ButcherblockAssets(planner, annotations, classification)
