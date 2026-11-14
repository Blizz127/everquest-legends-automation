"""Pinned Crushbone terrain, placements, BSP and copied camp annotations.

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
from .owner_route_assets import checked_bytes, TRANSFORM_PIN
from .pfs_archive import PFSArchive
from .portal_precision_view import PortalPrecisionView
from .static_source_view import StaticSourceView
from .wld_inventory import WLDInventory

DATA_NAME = 'crushbone-camps-20261114'
DATA_PINS = {
    'crushbone.npz': 'ba544e96700b51777d81c522c3dd6eba27c4d4a1af387852bf70729086158e56',
    'crushbone.json': '3c5701958bead8a9919be4d86db36cef80e57ed32825a4a75543cdac0d121b37',
    'crushbone.s3d': 'a2591482aac0a478caec1d79bf662a3f0f93d4ef2dc423be8f7591fe6d45e36f',
    'crushbone_obj.s3d': 'd80521fdb69c53497d3070b4869dd33ecbdeafdca9ee5f6a3010a93e228f14a5',
    'ZoneNames.txt': '0a5c0ff78c452a1895af2ac3014254d29aee996a36a2d4e907e717e2180c422d',
    'crushbone_3.txt': '4b1c009838988b13507797afd1ccbce8ba23e1ca99adbafd1065956cfd71bda0',
    'crushbone.map-alignment.json': '2847766145022db7405acfebe5c0a4c5b1cb55845cbaf17a4d5011a8b7a8645d',
}
WLD_PIN = 'ce43cea4ea9a83cc0db0b25a666cfbe538543dcc451c34ee3bc984227ef1f9d1'
OBJECTS_PIN = 'fc7535a0c3ade7a4e3e76733d301acee697dddbf0d2db9ae41718009a29bb8c8'
LIBRARY_PIN = 'efe378db3c69b1f2d8b362bc3c32b997bf0d8cec9eac418f893c1ec897b3be95'
STATIC_PIN = 'b49d11674658e30a6df8914c4ba2002df6772f093b859647f05ad43c2842647a'
BSP_PIN = '048f1cef7ddc9adc4700498c7211ef0fa2717ccd81132843890422a7e69db45c'
CLASSIFICATION_PIN = '99197a077bfd709305eeececf77602f5ff3283006cad14da948d960c11b08b0a'


@dataclass(frozen=True)
class CrushboneAssets:
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
        return dict(format='eql-crushbone-annotations-v1', zone='crushbone',
            zone_id=self.planner.zone_id, zone_name=self.planner.zone_name,
            pins=dict(DATA_PINS), source_wld_sha256=WLD_PIN,
            static_inventory_sha256=STATIC_PIN, bsp_inventory_sha256=BSP_PIN,
            map_to_package_xy='-x,-y', label_z_used_for_floor_selection=False,
            terrain_faces=len(self.planner.source.sources),
            static_faces=len(self.planner.static.sources),
            placements=len(self.planner.static.identities),
            rows=rows, current_character_position=False, game_input_sent=False,
            route_accepted=False, real_client_accepted=False)


def load_crushbone_assets(root):
    """Load full private copied views, verifying pins before and after parsing."""
    from eqnav import zonegeom
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Missing private Crushbone data: '+str(root))

    def verify():
        for name, pin in DATA_PINS.items():
            checked_bytes(root/name, pin)
        checked_bytes(Path(zonegeom.__file__), TRANSFORM_PIN)
    verify()
    catalog = checked_bytes(root/'ZoneNames.txt', DATA_PINS['ZoneNames.txt'])
    unique, _ = unique_zone_ids_from_text(catalog.decode('latin-1'))
    names = [name for name, zone_id in unique.items() if zone_id == 58]
    if len(names) != 1:
        raise ValueError('Copied client catalog has no unique Crushbone identity')
    alignment = json.loads(checked_bytes(root/'crushbone.map-alignment.json',
                                         DATA_PINS['crushbone.map-alignment.json']))
    if (alignment['zone'] != 'crushbone'
            or alignment['best_map_to_wld_xy_transform'] != '-y,-x'
            or alignment['archive_sha256'] != DATA_PINS['crushbone.s3d']
            or alignment['wld_sha256'] != WLD_PIN
            or alignment['frame_supported_by_rounded_vertex_matches'] is not True):
        raise ValueError('Copied Crushbone map frame has no matching source alignment')
    annotations = read_camp_annotations(checked_bytes(root/'crushbone_3.txt',
                                                       DATA_PINS['crushbone_3.txt']))
    archive = PFSArchive(root/'crushbone.s3d')
    object_archive = PFSArchive(root/'crushbone_obj.s3d')
    terrain = WLDInventory(archive.read_member('crushbone.wld'))
    placements = WLDInventory(archive.read_member('objects.wld'))
    library = WLDInventory(object_archive.read_member('crushbone_obj.wld'))
    if (archive.sha256 != DATA_PINS['crushbone.s3d']
            or object_archive.sha256 != DATA_PINS['crushbone_obj.s3d']
            or (terrain.sha256, placements.sha256, library.sha256) !=
               (WLD_PIN, OBJECTS_PIN, LIBRARY_PIN)):
        raise ValueError('Loaded Crushbone source differs from pinned WLDs')
    static = StaticSourceView.from_wld(placements, (library,),
        terrain_fragment_max=max(f.index for f in terrain.fragments),
        transform=zonegeom.place_vertices, transform_sha256=TRANSFORM_PIN)
    mesh_path = root/'crushbone.npz'
    mesh = BspDetailMeshView.load(mesh_path, zone='crushbone')
    ground = GroundSweepView.load(mesh_path, zone='crushbone')
    source = PortalPrecisionView(ground, mesh_path, root/'crushbone.s3d', zone='crushbone')
    bsp = BspVolumeView.from_wld(terrain)
    classification = ClientBspClassificationView.from_wld(terrain)
    if static.inventory_sha256 != STATIC_PIN or bsp.inventory_sha256 != BSP_PIN:
        raise ValueError('Loaded Crushbone static/BSP inventory changed')
    if classification.inventory_sha256 != CLASSIFICATION_PIN:
        raise ValueError('Loaded native Crushbone classification inventory changed')
    source.sources = tuple(source.sources)
    for array in (ground.triangles, ground.polys, ground.areas, ground.components,
                  ground.minimum, ground.maximum, source.source_minimum, source.source_maximum):
        array.flags.writeable = False
    planner = CurrentStartPlanner(mesh=mesh, ground=ground, source=source,
        static=static, bsp=bsp, zone_short_name='crushbone', expected_zone_id=58,
        expected_zone_name=names[0], mesh_sha256=DATA_PINS['crushbone.npz'],
        source_archive_sha256=DATA_PINS['crushbone.s3d'], source_wld_sha256=WLD_PIN,
        static_inventory_sha256=STATIC_PIN)
    verify()
    return CrushboneAssets(planner, annotations, classification)
