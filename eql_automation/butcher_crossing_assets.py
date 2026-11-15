"""Pinned Butcherblock -> GFay source descriptor; no runtime/input adapter."""
from dataclasses import dataclass
import json
from pathlib import Path

from .butcher_assets import DATA_PINS, WLD_PIN, ButcherblockAssets
from .location_log import unique_zone_ids_from_text
from .native_crossing_policy import NativeCrossingRegionPolicy
from .owner_route_assets import checked_bytes
from .pfs_archive import PFSArchive
from .wld_inventory import WLDInventory
from .zone_line import ExpectedZoneLine


@dataclass(frozen=True)
class ButcherCrossingAssets:
    policy: NativeCrossingRegionPolicy
    goal_xy: tuple
    destination: str
    destination_id: int

    def record(self):
        return dict(format='eql-butcher-gfay-source-descriptor-v1', policy=self.policy.record(),
            goal_xy=self.goal_xy, goal_origin='retained_region_center_XY_proposal_only',
            goal_floor_verified=False, region_center_z_used=False,
            destination=self.destination, destination_id=self.destination_id,
            destination_origin='retained_map_hint_and_client_catalog',
            destination_server_verified=False, spawn_coordinate_verified=False,
            runtime_ready=False, input_authorized=False, real_client_accepted=False)


def load_butcher_crossing(root, assets):
    """Share the already loaded native terrain/static views without changing them."""
    from eqnav.mesh import NavMesh
    if type(assets) is not ButcherblockAssets or assets.planner.region_policy is None:
        raise ValueError('Loaded native Butcherblock source views required')
    root = Path(root)
    manifest_bytes = checked_bytes(root/'butcher.json', DATA_PINS['butcher.json'])
    catalog = checked_bytes(root/'ZoneNames.txt', DATA_PINS['ZoneNames.txt'])
    checked_bytes(root/'butcher.npz', DATA_PINS['butcher.npz'])
    checked_bytes(root/'butcher.s3d', DATA_PINS['butcher.s3d'])
    navigation = NavMesh.load(root/'butcher.npz', expected_sha256=DATA_PINS['butcher.npz'])
    wld = WLDInventory(PFSArchive(root/'butcher.s3d').read_member('butcher.wld'))
    if wld.sha256 != WLD_PIN:
        raise ValueError('Copied Butcherblock terrain changed')
    p = assets.planner
    line = ExpectedZoneLine.from_sources(crossing_id='butcher-gfay-source-v1',
        wld=wld, bsp=p.bsp, mesh=navigation, manifest_bytes=manifest_bytes, area_id=2)
    rows = [r for r in json.loads(manifest_bytes)['extra']['zone_lines'] if r['area']==2]
    names, _ = unique_zone_ids_from_text(catalog.decode('latin-1'))
    destinations = [name for name, ident in names.items() if ident==54]
    if (line.region_ids != (3077, 3083)
            or line.polygon_ids != (375, 376, 377, 389, 390, 391, 392)
            or line.raw_label != 'DRNTP00255000001_ZONE' or len(rows) != 1
            or rows[0]['to_zone'] != 'gfaydark' or len(destinations) != 1):
        raise ValueError('Exact Butcherblock transition or destination hint changed')
    policy = NativeCrossingRegionPolicy(p.region_policy, line)
    policy.check_context(p.source, p.static, p.bsp)
    for name in ('butcher.json', 'butcher.npz', 'butcher.s3d', 'ZoneNames.txt'):
        checked_bytes(root/name, DATA_PINS[name])
    return ButcherCrossingAssets(policy, tuple(rows[0]['point'][:2]), destinations[0], 54)
