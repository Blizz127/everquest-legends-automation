"""Owner destination from the installed client's pinned map label and navmesh.

This identifies an approach marker, not the actual zone trigger or a camp.
The map-to-source alignment is retained outside git with the copied data.
"""
from dataclasses import dataclass
import json
from pathlib import Path

from .current_route_start import CurrentStartPlanner, encoded
from .fixed_route_follower import finite
from .owner_route_assets import checked_bytes, load_owner_planner, DATA_PINS, TILE_DATA_NAME

DESTINATION_DATA_NAME = 'gfay-crushbone-approach-20261114'
MAP_PIN = '84a1e1a655a73ddb13a71a7afc121acfe73d8737554a3ac1a5ad78249d0db882'
ALIGNMENT_PIN = 'c3f9fb5ffdf8dc740d145c119b2c3522e22cb5f36617e575417176932620901f'


@dataclass(frozen=True)
class DestinationRouteAssets:
    planner: CurrentStartPlanner
    navigation_mesh: object
    goal_xy: tuple[float, float]
    target_name: str
    source_evidence: bytes

    def __post_init__(self):
        self.check()

    def check(self):
        if (not isinstance(self.planner, CurrentStartPlanner)
                or getattr(self.navigation_mesh, 'sha256', None) != self.planner.pins[0]
                or not callable(getattr(self.navigation_mesh, 'find_path', None))
                or not isinstance(self.goal_xy, tuple) or len(self.goal_xy) != 2
                or not all(finite(v) for v in self.goal_xy)
                or not isinstance(self.target_name, str) or not self.target_name
                or not isinstance(self.source_evidence, bytes) or not 0 < len(self.source_evidence) <= 65536):
            raise ValueError('Pinned mesh, exact goal and destination provenance required')
        self.planner._check_views()


def read_crushbone_approach(root):
    root = Path(root)
    labels = checked_bytes(root/'gfaydark_1.txt', MAP_PIN)
    alignment = json.loads(checked_bytes(root/'gfaydark.map-alignment.json', ALIGNMENT_PIN))
    if (alignment['zone'] != 'gfaydark'
            or alignment['best_map_to_wld_xy_transform'] != '-y,-x'
            or alignment['label_map_sha256'] != MAP_PIN
            or alignment['archive_sha256'] != DATA_PINS['gfaydark.s3d']
            or alignment['frame_supported_by_rounded_vertex_matches'] is not True):
        raise ValueError('Client map destination has no matching source alignment')
    found = []
    for number, line in enumerate(labels.decode('latin-1').splitlines(), 1):
        if not line.startswith('P '):
            continue
        fields = [v.strip() for v in line[2:].split(',')]
        if len(fields) == 8 and fields[-1] == 'to_Clan_Crushbone':
            found.append((number, tuple(map(float, fields[:3]))))
    if len(found) != 1 or not all(finite(v) for v in found[0][1]):
        raise ValueError('Client map must contain one finite Crushbone approach marker')
    number, xyz = found[0]
    # Map -> raw WLD is (-y,-x); helper package swaps raw WLD X/Y.
    xy = (-xyz[0], -xyz[1])
    evidence = encoded(dict(kind='copied_client_map_approach', zone='gfaydark',
        label='to_Clan_Crushbone', line=number, map_xyz=xyz, package_xy=xy,
        label_map_sha256=MAP_PIN, alignment_sha256=ALIGNMENT_PIN,
        source_archive_sha256=DATA_PINS['gfaydark.s3d'],
        zone_trigger_verified=False, current_character_position=False))
    return xy, evidence


def load_owner_destination(engine):
    from eqnav.mesh import NavMesh
    game_map = Path(engine.settings.game_dir)/'maps/gfaydark_1.txt'
    checked_bytes(game_map, MAP_PIN)
    planner = load_owner_planner(engine, tile_rounding=True)
    store = Path.home()/'.local/share/eql-automation'
    goal, evidence = read_crushbone_approach(store/'owner-route-data'/DESTINATION_DATA_NAME)
    mesh_path = store/'owner-route-data'/TILE_DATA_NAME/'gfaydark.npz'
    navigation = NavMesh.load(mesh_path, expected_sha256=DATA_PINS['gfaydark.npz'])
    checked_bytes(game_map, MAP_PIN)
    return DestinationRouteAssets(planner, navigation, goal, 'Crushbone approach', evidence)
