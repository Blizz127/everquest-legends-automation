"""Pinned source geometry for one owner-supervised GFay to Crushbone crossing.

Native region identity is source evidence. It does not prove server destination,
arrival coordinates or actual traversal; arrival must be observed independently.
"""
from dataclasses import dataclass
import json
from pathlib import Path
from uuid import uuid4

from .current_route_start import encoded
from .owner_destination_assets import DestinationRouteAssets
from .owner_route_assets import (DATA_PINS, TILE_DATA_NAME, TILE_MANIFEST_PIN,
                                 WLD_PIN, checked_bytes, load_owner_planner)
from .pfs_archive import PFSArchive
from .wld_inventory import WLDInventory
from .zone_line import ExpectedZoneLine


@dataclass(frozen=True)
class CrossingDestinationAssets(DestinationRouteAssets):
    expected_zone_line: ExpectedZoneLine
    destination: str

    def check(self):
        super().check()
        line=self.expected_zone_line;p=self.planner
        if (type(line) is not ExpectedZoneLine or line.zone!=p.zone
                or (line.mesh_sha256,line.archive_sha256,line.wld_sha256,
                    line.bsp_inventory_sha256)!=(p.pins[0],p.pins[1],p.pins[2],p.bsp.inventory_sha256)
                or not isinstance(self.destination,str) or not self.destination):
            raise ValueError('Crossing source line and exact destination must match its planner')


def load_owner_crossing(engine):
    from eqnav.mesh import NavMesh
    planner=load_owner_planner(engine,tile_rounding=True)
    root=Path.home()/'.local/share/eql-automation/owner-route-data'/TILE_DATA_NAME
    manifest=checked_bytes(root/'gfaydark.json',TILE_MANIFEST_PIN)
    navigation=NavMesh.load(root/'gfaydark.npz',expected_sha256=DATA_PINS['gfaydark.npz'])
    wld=WLDInventory(PFSArchive(root/'gfaydark.s3d').read_member('gfaydark.wld'))
    if wld.sha256!=WLD_PIN:raise ValueError('Copied source terrain changed')
    line=ExpectedZoneLine.from_sources(crossing_id='owner-gfay-crushbone-'+uuid4().hex,
        wld=wld,bsp=planner.bsp,mesh=navigation,manifest_bytes=manifest,area_id=4)
    rows=[row for row in json.loads(manifest)['extra']['zone_lines'] if row['area']==4]
    names=[name for name,ident in engine.live_zone_tracker.reader.zone_ids.items() if ident==58]
    if (line.polygon_ids!=(19256,) or line.region_ids!=(2884,)
            or line.raw_label!='DRNTP00255000004_ZONE' or len(rows)!=1
            or rows[0]['raw']!=line.raw_label or len(names)!=1):
        raise ValueError('Pinned source crossing or unique destination catalog entry changed')
    goal=tuple(rows[0]['point'][:2])
    evidence=encoded(dict(kind='copied_native_source_zone_line',zone='gfaydark',
        expected_zone_line=line.record(),package_xy=goal,destination=names[0],
        destination_server_verified=False,spawn_coordinate_verified=False,
        current_character_position=False))
    return CrossingDestinationAssets(planner,navigation,goal,'Travel into Crushbone',
                                     evidence,line,names[0])
