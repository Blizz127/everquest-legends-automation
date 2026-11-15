"""Pinned Greater Faydark terrain, placements, BSP and copied camp annotations.

Nothing here sends input or accepts a route. Map level ranges are annotations;
actual mobs, suitability, current location and live movement remain unverified.
"""
from dataclasses import asdict, dataclass
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

DATA_NAME = 'gfay-camps-carbon-20261115'
DATA_PINS = {
    'gfaydark.npz': '5f8e16c5bcd2221ba273f681750ca480349780524d23609c059a3e817df6abd9',
    'gfaydark.json': 'ac9591eb63e1394363ad37d7d0ca6609a1ebe11fd8786bedb5b165b833e2eb82',
    'gfaydark.s3d': 'ea95f51a2d4645410223d24cc7da9eb0e7095310c6e9f8756e8c51d67df13d9f',
    'gfaydark_obj.s3d': '3439c59e9c6c1623e85b29694d6a6161b924b0a9ece39751b0234ab5c6f71892',
    'ZoneNames.txt': '0a5c0ff78c452a1895af2ac3014254d29aee996a36a2d4e907e717e2180c422d',
    'gfaydark_1.txt': '84a1e1a655a73ddb13a71a7afc121acfe73d8737554a3ac1a5ad78249d0db882',
    'gfaydark_3.txt': '473a65146ab6ac239a6ddfc08ffbb980abc692a85c10c2fbbd8c781b721457aa',
    'gfaydark.map-alignment.json': 'c3f9fb5ffdf8dc740d145c119b2c3522e22cb5f36617e575417176932620901f',
}
WLD_PIN = '3f9a479ea46a3fb8f826ccfb608d0f69a5876e1cab5fa38ea86712e8fdabe138'
OBJECTS_PIN = 'b15dbe0df01eb2276e70a783ae067f65f5abb4ec18649481f6c1d867c89913e6'
LIBRARY_PIN = '4e0eef9ccb436c8abc2859aeed6d8e333918f3b814a92bcb2bb5ad1248830735'
STATIC_PIN = 'dc489aff256243b2a84ad3979c2222d5011bbdc2865afa78534d0d43df99dcd4'
BSP_PIN = '43958a80b7a7c2d7d8768658ba6a909a78030b2ec77b000406815dad5c5c5a9b'
CLASSIFICATION_PIN = '738b5e6d1f9c8a2e712b6c4c543d0d5e4e79c964a7918b2abb1af012c1aef03a'


@dataclass(frozen=True)
class GreaterFaydarkAssets:
    planner: CurrentStartPlanner
    annotations: tuple
    classification: ClientBspClassificationView

    def annotation_report(self, *, body_height=None):
        """Inspect exact annotation XY, never turn label Z into a floor seed."""
        self.planner._check_views()
        rows = []
        for annotation in self.annotations:
            xy = (-annotation.map_xyz[0], -annotation.map_xyz[1])
            row = dict(annotation=asdict(annotation), package_xy=xy,
                       level_suitability_verified=False, usable_destination=False)
            try:
                polygon, height = self.planner._support(xy)
                row['mesh_support'] = dict(polygon=polygon, height=height,
                    component=int(self.planner.ground.components[polygon]))
            except ValueError as error:
                row['mesh_refusal'] = str(error)
            hits = self.planner.source.source_hits_at(xy)
            row['source_intersections'] = [asdict(hit) for hit in hits]
            row['diffuse_heights'] = sorted({hit.height for hit in hits
                if hit.flag == 0 and hit.material_class == 'Diffuse'})
            try:
                height, identities = self.planner.source.source_floor_at(xy)
                row['strict_source_support'] = dict(height=height, identities=identities)
            except ValueError as error:
                row['source_refusal'] = str(error)
            if body_height is not None:
                try:
                    row['floor_seed_proposal'] = asdict(self.planner.source.propose_unique_diffuse_floor(
                        xy, body_height=body_height))
                except ValueError as error:
                    row['floor_seed_refusal'] = str(error)
            rows.append(row)
        return dict(format='eql-gfay-annotations-v1', zone='gfaydark',
            zone_id=self.planner.zone_id, zone_name=self.planner.zone_name,
            pins=dict(DATA_PINS), source_wld_sha256=WLD_PIN,
            static_inventory_sha256=STATIC_PIN, bsp_inventory_sha256=BSP_PIN,
            map_to_package_xy='-x,-y', label_z_used_for_floor_selection=False,
            terrain_faces=len(self.planner.source.sources),
            static_faces=len(self.planner.static.sources),
            placements=len(self.planner.static.identities),
            rows=rows, current_character_position=False, game_input_sent=False,
            route_accepted=False, real_client_accepted=False)


def load_gfay_assets(root, *, native_planning=False):
    """Load full private copied views, verifying pins before and after parsing."""
    from eqnav import zonegeom
    if type(native_planning) is not bool:
        raise ValueError('Native planning opt-in must be explicit')
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Missing private Greater Faydark data: ' + str(root))

    def verify():
        for name, pin in DATA_PINS.items():
            checked_bytes(root / name, pin)
        checked_bytes(Path(zonegeom.__file__), TRANSFORM_PIN)
    verify()
    catalog = checked_bytes(root / 'ZoneNames.txt', DATA_PINS['ZoneNames.txt'])
    unique, _ = unique_zone_ids_from_text(catalog.decode('latin-1'))
    names = [name for name, zone_id in unique.items() if zone_id == 54]
    if len(names) != 1:
        raise ValueError('Copied client catalog has no unique Greater Faydark identity')
    alignment = json.loads(checked_bytes(root / 'gfaydark.map-alignment.json',
                                         DATA_PINS['gfaydark.map-alignment.json']))
    if (alignment['zone'] != 'gfaydark'
            or alignment['best_map_to_wld_xy_transform'] != '-y,-x'
            or alignment['archive_sha256'] != DATA_PINS['gfaydark.s3d']
            or alignment['wld_sha256'] != WLD_PIN
            or alignment['frame_supported_by_rounded_vertex_matches'] is not True):
        raise ValueError('Copied Greater Faydark map frame has no matching source alignment')
    annotations = read_camp_annotations(checked_bytes(root / 'gfaydark_3.txt',
                                                      DATA_PINS['gfaydark_3.txt']))
    archive = PFSArchive(root / 'gfaydark.s3d')
    object_archive = PFSArchive(root / 'gfaydark_obj.s3d')
    terrain = WLDInventory(archive.read_member('gfaydark.wld'))
    placements = WLDInventory(archive.read_member('objects.wld'))
    library = WLDInventory(object_archive.read_member('gfaydark_obj.wld'))
    if (archive.sha256 != DATA_PINS['gfaydark.s3d']
            or object_archive.sha256 != DATA_PINS['gfaydark_obj.s3d']
            or (terrain.sha256, placements.sha256, library.sha256) !=
               (WLD_PIN, OBJECTS_PIN, LIBRARY_PIN)):
        raise ValueError('Loaded Greater Faydark source differs from pinned WLDs')
    static = StaticSourceView.from_wld(placements, (library,),
        terrain_fragment_max=max(f.index for f in terrain.fragments),
        transform=zonegeom.place_vertices, transform_sha256=TRANSFORM_PIN)
    mesh_path = root / 'gfaydark.npz'
    mesh = BspDetailMeshView.load(mesh_path, zone='gfaydark')
    ground = GroundSweepView.load(mesh_path, zone='gfaydark')
    source = PortalPrecisionView(ground, mesh_path, root / 'gfaydark.s3d', zone='gfaydark')
    bsp = BspVolumeView.from_wld(terrain)
    classification = ClientBspClassificationView.from_wld(terrain)
    if static.inventory_sha256 != STATIC_PIN or bsp.inventory_sha256 != BSP_PIN:
        raise ValueError('Loaded Greater Faydark static/BSP inventory changed')
    if classification.inventory_sha256 != CLASSIFICATION_PIN:
        raise ValueError('Loaded native Greater Faydark classification inventory changed')
    source.sources = tuple(source.sources)
    for array in (ground.triangles, ground.polys, ground.areas, ground.components,
                  ground.minimum, ground.maximum, source.source_minimum, source.source_maximum):
        array.flags.writeable = False
    planner = CurrentStartPlanner(mesh=mesh, ground=ground, source=source,
        static=static, bsp=bsp, zone_short_name='gfaydark', expected_zone_id=54,
        expected_zone_name=names[0], mesh_sha256=DATA_PINS['gfaydark.npz'],
        source_archive_sha256=DATA_PINS['gfaydark.s3d'], source_wld_sha256=WLD_PIN,
        static_inventory_sha256=STATIC_PIN,
        region_policy=(NativeZeroRegionTrialPolicy(DATA_PINS['gfaydark.npz'],
            DATA_PINS['gfaydark.s3d'], WLD_PIN, STATIC_PIN, BSP_PIN, CLASSIFICATION_PIN,
            classification, zone='gfaydark') if native_planning else None))
    verify()
    return GreaterFaydarkAssets(planner, annotations, classification)
