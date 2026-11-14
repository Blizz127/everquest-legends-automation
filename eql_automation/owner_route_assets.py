"""Pinned copied GFay geometry for the finite owner-run route experiment.

Client assets stay in the private data store. The live installation is only
read to check that its source archives/catalog still match the copied data.
No old route, location, heading or height result is loaded here.
"""
from hashlib import sha256
from pathlib import Path

from .bsp_detail_view import BspDetailMeshView
from .bsp_volume import BspVolumeView
from .current_route_start import CurrentStartPlanner
from .ground_sweep_view import GroundSweepView
from .location_log import unique_zone_ids_from_text
from .pfs_archive import PFSArchive
from .portal_precision_view import PortalPrecisionView
from .route_precision import RoutePrecisionPolicy
from .static_source_view import StaticSourceView
from .wld_inventory import WLDInventory

DATA_NAME = 'gfay-trial-20261114-current'
TILE_DATA_NAME = 'gfay-destination-20261114-tiles'
TILE_MANIFEST_PIN = 'ac9591eb63e1394363ad37d7d0ca6609a1ebe11fd8786bedb5b165b833e2eb82'
DATA_PINS = {
    'gfaydark.npz': '5f8e16c5bcd2221ba273f681750ca480349780524d23609c059a3e817df6abd9',
    'gfaydark.s3d': 'ea95f51a2d4645410223d24cc7da9eb0e7095310c6e9f8756e8c51d67df13d9f',
    'gfaydark_obj.s3d': '3439c59e9c6c1623e85b29694d6a6161b924b0a9ece39751b0234ab5c6f71892',
    'ZoneNames.txt': '0a5c0ff78c452a1895af2ac3014254d29aee996a36a2d4e907e717e2180c422d',
}
TRANSFORM_PIN = 'bffd21c5767b111f9516180377838d180bf31e3af8e2bc427258c987d6609a60'
WLD_PIN = '3f9a479ea46a3fb8f826ccfb608d0f69a5876e1cab5fa38ea86712e8fdabe138'
STATIC_PIN = 'dc489aff256243b2a84ad3979c2222d5011bbdc2865afa78534d0d43df99dcd4'
BSP_PIN = '43958a80b7a7c2d7d8768658ba6a909a78030b2ec77b000406815dad5c5c5a9b'
OBJECTS_PIN = 'b15dbe0df01eb2276e70a783ae067f65f5abb4ec18649481f6c1d867c89913e6'
LIBRARY_PIN = '4e0eef9ccb436c8abc2859aeed6d8e333918f3b814a92bcb2bb5ad1248830735'


def checked_bytes(path, expected):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 16*1024*1024:
        raise ValueError('Missing or unsupported route data file: '+str(path))
    data = path.read_bytes()
    if sha256(data).hexdigest() != expected:
        raise ValueError('Route data hash mismatch: '+str(path))
    return data


def load_gfay_planner(root, *, tile_rounding=False):
    """Load complete views, checking both before and after path-based parsers."""
    from eqnav import zonegeom
    root = Path(root)
    if type(tile_rounding) is not bool:
        raise ValueError('Tile rounding must be explicitly selected')
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Missing private GFay trial data: '+str(root))
    def verify():
        for name, pin in DATA_PINS.items():
            checked_bytes(root/name, pin)
        checked_bytes(Path(zonegeom.__file__), TRANSFORM_PIN)
        if tile_rounding:
            checked_bytes(root/'gfaydark.json', TILE_MANIFEST_PIN)
    verify()
    catalog = checked_bytes(root/'ZoneNames.txt', DATA_PINS['ZoneNames.txt'])
    unique, _ = unique_zone_ids_from_text(catalog.decode('latin-1'))
    names = [name for name, zone_id in unique.items() if zone_id == 54]
    if len(names) != 1:
        raise ValueError('Copied client catalog has no unique GFay identity')
    archive = PFSArchive(root/'gfaydark.s3d')
    terrain = WLDInventory(archive.read_member('gfaydark.wld'))
    objects = WLDInventory(archive.read_member('objects.wld'))
    object_archive = PFSArchive(root/'gfaydark_obj.s3d')
    library = WLDInventory(object_archive.read_member('gfaydark_obj.wld'))
    if (archive.sha256 != DATA_PINS['gfaydark.s3d']
            or object_archive.sha256 != DATA_PINS['gfaydark_obj.s3d']
            or terrain.sha256 != WLD_PIN or objects.sha256 != OBJECTS_PIN
            or library.sha256 != LIBRARY_PIN):
        raise ValueError('Loaded source archives or WLDs differ from pinned data')
    static = StaticSourceView.from_wld(objects, (library,),
        terrain_fragment_max=max(f.index for f in terrain.fragments),
        transform=zonegeom.place_vertices, transform_sha256=TRANSFORM_PIN)
    mesh_path = root/'gfaydark.npz'
    mesh = BspDetailMeshView.load(mesh_path, zone='gfaydark')
    ground = GroundSweepView.load(mesh_path, zone='gfaydark')
    source = PortalPrecisionView(ground, mesh_path, root/'gfaydark.s3d', zone='gfaydark',
                                 tile_rounding=tile_rounding)
    precision = RoutePrecisionPolicy(source.tile_grid, allow_overlap=True) if tile_rounding else None
    bsp = BspVolumeView.from_wld(terrain)
    if bsp.inventory_sha256 != BSP_PIN:
        raise ValueError('Loaded BSP differs from pinned inventory')
    planner = CurrentStartPlanner(mesh=mesh, ground=ground, source=source,
        static=static, bsp=bsp, zone_short_name='gfaydark',
        expected_zone_id=54, expected_zone_name=names[0],
        mesh_sha256=DATA_PINS['gfaydark.npz'], source_archive_sha256=DATA_PINS['gfaydark.s3d'],
        source_wld_sha256=WLD_PIN, static_inventory_sha256=STATIC_PIN, precision_policy=precision)
    verify()
    return planner


def load_owner_planner(engine, *, tile_rounding=False):
    tracker = engine.live_zone_tracker
    if tracker is None or tracker.reader.zone_id != 54:
        raise ValueError('This finite trial currently supports Greater Faydark only')
    game = Path(engine.settings.game_dir)
    for name in ('gfaydark.s3d', 'gfaydark_obj.s3d', 'ZoneNames.txt'):
        path = game/'Resources'/name if name == 'ZoneNames.txt' else game/name
        checked_bytes(path, DATA_PINS[name])
    engine.emit('Loading copied GFay terrain and objects; no movement yet.')
    name = TILE_DATA_NAME if tile_rounding else DATA_NAME
    planner = load_gfay_planner(Path.home()/'.local/share/eql-automation/owner-route-data'/name,
                               tile_rounding=tile_rounding)
    tracker.check_binding()
    unique, _ = unique_zone_ids_from_text(checked_bytes(
        game/'Resources/ZoneNames.txt', DATA_PINS['ZoneNames.txt']).decode('latin-1'))
    if tracker.reader.zone_ids != unique or tracker.reader.zone_display_name != planner.zone_name:
        raise ValueError('Current log zone differs from the copied client catalog')
    return planner
