"""Plan a finite source-checked trial at exact current printed XY.

No historical start, nearest-height selection, input or live clearance claim.
The result needs a NEW stopped pair for height/startup and a continuously
observed motion session before a supervised driver can consume it.
"""
from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
import json
import math
import re
import time

import numpy as np

from .bsp_floor_guard import check_bsp_floor
from .bsp_volume import BspVolumeView
from .fixed_route_follower import FixedRoute, FixedSegment
from .floor_replay import check_floor_trial
from .ground_binding import GroundGeometryEvidence, digest, finite, integer, point
from .ground_observer import RouteGroundObserver, exact_detail_support
from .ground_sweep import GroundFace, check_ground_coverage, hull, motion_footprint
from .location_log import LocationLogReader, RawLocationFix
from .motion_collection import immutable_binding
from .route_geometry import RouteMotionBounds
from .source_floor_chain import SourceFloorChain
from .source_occupancy import exact_floor_partition
from .static_floor_guard import check_static_floor


def encoded(record):
    return (json.dumps(record, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def raw_record(raw):
    result = asdict(raw)
    result['log_local_time'] = raw.log_local_time.isoformat()
    return result


@dataclass(frozen=True)
class CurrentStartPlan:
    route: FixedRoute
    observer: RouteGroundObserver
    floor_chain: SourceFloorChain
    planning_bounds: RouteMotionBounds
    plan_bytes: bytes
    evidence_bytes: bytes
    requires_fresh_start_pair: bool = True
    real_client_accepted: bool = False
    input_authorized: bool = False


class CurrentStartPlanner:
    """Use preloaded, pinned full-zone views; construction sends no input.

    Direct construction supports injected geometry fixtures. Production must
    load these views from the checked mesh/archive/static placement inventory,
    and resolve expected zone ID/name from the client's catalog. The caller
    retains current heading/input continuity; saved JSON cannot restore it.
    """
    def __init__(self, *, mesh, ground, source, static, bsp, zone_short_name,
                 expected_zone_id, expected_zone_name, mesh_sha256,
                 source_archive_sha256, source_wld_sha256,
                 static_inventory_sha256):
        pins = (mesh_sha256, source_archive_sha256, source_wld_sha256, static_inventory_sha256)
        if (not all(digest(v) for v in pins) or not isinstance(bsp, BspVolumeView)
                or not isinstance(zone_short_name, str) or not zone_short_name
                or not integer(expected_zone_id) or not isinstance(expected_zone_name, str)
                or not expected_zone_name):
            raise ValueError('Complete pinned views and catalog-resolved zone required')
        self.mesh, self.ground, self.source, self.static, self.bsp = mesh, ground, source, static, bsp
        self.zone, self.zone_id, self.zone_name = zone_short_name, expected_zone_id, expected_zone_name
        self.pins = pins
        self.bsp_pin = bsp.inventory_sha256
        self._views = (mesh, ground, source, static, bsp)
        self._check_views()

    def _check_views(self):
        mesh, archive, wld, static = self.pins
        if (any(a is not b for a, b in zip(self._views,
                    (self.mesh, self.ground, self.source, self.static, self.bsp)))
                or getattr(self.mesh, 'mesh_sha256', None) != mesh
                or self.ground.mesh_sha256 != mesh or self.source.mesh_sha256 != mesh
                or self.source.ground is not self.ground
                or self.source.archive_sha256 != archive or self.source.wld_sha256 != wld
                or self.static.inventory_sha256 != static or self.bsp.wld_sha256 != wld
                or self.bsp.inventory_sha256 != self.bsp_pin
                or len(self.mesh.area) != len(self.ground.areas)
                or len(self.ground.areas) != len(self.ground.components)):
            raise ValueError('Current-start geometry identities changed')

    def _support(self, xy):
        g = self.ground
        indices = np.flatnonzero((g.minimum[:, 0] <= xy[0]) & (g.maximum[:, 0] >= xy[0])
                               & (g.minimum[:, 1] <= xy[1]) & (g.maximum[:, 1] >= xy[1]))
        if len(indices) > 128:
            raise ValueError('Current-start support candidate budget exceeded')
        polygons = tuple(sorted(set(int(g.polys[i]) for i in indices)))
        if len(polygons) > 32:
            raise ValueError('Current-start polygon candidate budget exceeded')
        hits = []
        for poly in polygons:
            value = exact_detail_support(self.mesh, poly, xy)
            if value.status == 'ambiguous':
                raise ValueError('Current XY has ambiguous detail heights')
            if value.status == 'supported':
                hits.append((poly, value.height))
        if len(hits) != 1:
            raise ValueError('Current XY needs one uniquely supported polygon; no snapping or Z selection')
        poly, height = hits[0]
        if (int(self.mesh.area[poly]) != 63 or int(g.areas[poly]) != 63
                or int(g.components[poly]) < 0):
            raise ValueError('Current polygon is not dry connected ground')
        return poly, height

    def plan(self, reader, first, second, *, heading, motion_record_id, bounds,
             length, half_width, vertical_window, maximum_source_z_difference,
             owner_binding, binding_reader, released_at, record_id,
             clock=time.monotonic, local_wall_clock=datetime.now, maximum_seconds=10.):
        """Check a short capsule from the second exact stopped fix, not old data.

        Planning can outlast the input fix lifetime. This never retimestamps
        samples: a later height/startup stage must collect another stopped pair
        at the resulting start. The complete plan remains conditional geometry.
        """
        if (not isinstance(reader, LocationLogReader)
                or not all(isinstance(f, RawLocationFix) for f in (first, second))
                or not isinstance(bounds, RouteMotionBounds)
                or not all(finite(v) for v in (heading, length, half_width, vertical_window,
                    maximum_source_z_difference, released_at, maximum_seconds))
                or not 0 <= heading < 360 or not .5 < length <= 3
                or not .25 < half_width <= 2 or not 0 < vertical_window <= 3
                or not 0 < maximum_source_z_difference <= 3
                or released_at < 0 or not 0 < maximum_seconds <= 30
                or not isinstance(record_id, str) or not record_id
                or not immutable_binding(owner_binding) or not isinstance(owner_binding, tuple)
                or not all(callable(f) for f in (binding_reader, clock, local_wall_clock))):
            raise ValueError('Current stopped pair, bounded local trial and explicit hypotheses required')
        bounds.validate_values(calibration_record_id=motion_record_id, maximum_step_seconds=.2)
        began = clock()
        identity = reader.tail.identity
        expected = (self.zone_id, self.zone_name, second.log_epoch, second.zone_generation)
        last = began
        def check():
            nonlocal last
            owner = binding_reader()
            self._check_views()
            now = clock()
            if (owner != owner_binding or not finite(now) or not finite(began)
                    or not began <= last <= now <= began+maximum_seconds or identity is None
                    or reader.tail.identity != identity or reader.tail.partial
                    or reader.latest is not second or reader.log_line_seq != second.log_line_seq
                    or (reader.zone_id, reader.zone_display_name, reader.tail.epoch,
                        reader.zone_generation) != expected):
                raise ValueError('Current-start owner/log identity changed or planning budget expired')
            last = now
            return now
        initial = check()
        wall = local_wall_clock()
        if (not isinstance(wall, datetime) or wall.tzinfo is not None
                or not all(point(f.raw_coordinates) and finite(f.received_monotonic)
                    and isinstance(f.log_local_time, datetime) and f.log_local_time.tzinfo is None
                    and (f.zone_id, f.zone_display_name, f.log_epoch, f.zone_generation) == expected
                    for f in (first, second))
                or not integer(first.log_line_seq) or first.log_line_seq < 1
                or second.log_line_seq != first.log_line_seq+1
                or not released_at+.12 <= first.received_monotonic
                or not .4 <= second.received_monotonic-first.received_monotonic <= 2.5
                or not 0 <= initial-second.received_monotonic <= .5
                or math.dist(first.raw_coordinates[:2], second.raw_coordinates[:2]) > .25
                or abs(first.raw_coordinates[2]-second.raw_coordinates[2]) > .25
                or first.log_local_time > second.log_local_time
                or any(abs((wall-f.log_local_time).total_seconds()
                           -(initial-f.received_monotonic)) > 2 for f in (first, second))):
            raise ValueError('Two fresh consecutive stopped observations in the expected zone required')
        xy = (second.raw_coordinates[1], second.raw_coordinates[0])
        first_xy = (first.raw_coordinates[1], first.raw_coordinates[0])
        polygon, z = self._support(xy)
        if self._support(first_xy)[0] != polygon:
            raise ValueError('Stopped pair crosses a polygon boundary')
        angle = math.radians(heading)
        end_xy = (xy[0]+length*math.sin(angle), xy[1]+length*math.cos(angle))
        end_polygon, end_z = self._support(end_xy)
        if end_polygon != polygon:
            raise ValueError('First local trial must remain in its starting polygon')
        source_z, seed_names = self.source.source_floor_at(xy)
        seeds = []
        for name in seed_names:
            match = re.fullmatch(r'wld:(\d+):face:(\d+)', name)
            if match is None:
                raise ValueError('Unrecognized source-floor identity')
            seeds.append(tuple(map(int, match.groups())))
        if (not finite(source_z) or abs(source_z-z) > maximum_source_z_difference
                or not 1 <= len(seeds) <= 32 or len(set(seeds)) != len(seeds)):
            raise ValueError('Current source floor or complete seed inventory unavailable')
        footprint = motion_footprint(xy, heading, length, position_error=bounds.position_error,
            heading_error_degrees=bounds.heading_error_degrees,
            post_release_drift=bounds.post_release_drift,
            extra_radius=bounds.body_radius+half_width+bounds.pivot_displacement_upper_bound)
        reference = (*xy, z)
        component = int(self.ground.components[polygon])
        original, detail_ids = self.ground.check(footprint, reference=reference,
            component=component, vertical_window=vertical_window)
        # A large Recast polygon may contain hundreds of detail triangles.
        # Keep ALL intersecting XY boxes, but do not charge unrelated remote
        # triangles to the bounded local coverage query. Never truncate.
        selected_ids = tuple(i for i in detail_ids if int(self.ground.polys[i]) == polygon)
        selected_faces = tuple(GroundFace(tuple(tuple(float(n) for n in p) for p in t), 63,
            component) for t in self.ground.triangles[list(selected_ids)])
        selected = check_ground_coverage(footprint, selected_faces, reference=reference,
            component=component, vertical_window=vertical_window)
        if (not selected.candidate or not exact_floor_partition(footprint,
                tuple(hull(p[:2] for p in f.vertices) for f in selected_faces))):
            raise ValueError('Complete local capsule refused: '+
                (selected.reason if not selected.candidate else 'selected_polygon_exact_partition_failed'))
        check()
        seed_record = dict(format='eql-current-floor-seed-v1', record_id=record_id,
            pins=self.pins, bsp_inventory_sha256=self.bsp_pin, owner_binding=owner_binding,
            log_identity=identity, observations=[raw_record(first), raw_record(second)],
            motion_record_id=motion_record_id, heading=heading, source_z=source_z,
            selected_ids=seeds, planning_bounds=asdict(bounds), footprint=footprint,
            released_at=released_at, began=began)
        chain = SourceFloorChain(inventory_sha256=self.pins[2],
            seed_evidence_sha256=sha256(encoded(seed_record)).hexdigest(),
            seed_ids=tuple(seeds), body_height=bounds.body_height)
        chain, terrain = check_floor_trial(self.source, chain, original, footprint, detail_ids,
            reference=reference, component=component,
            vertical_window=vertical_window, maximum_source_z_difference=maximum_source_z_difference)
        if not terrain.candidate:
            raise ValueError('Current-start terrain refused: '+terrain.reason)
        sources = self.source.source_faces_for_footprint(footprint)
        static = check_static_floor(terrain, footprint, sources, self.static)
        if not static.candidate:
            raise ValueError('Current-start static geometry refused: '+static.reason)
        bsp = check_bsp_floor(terrain, footprint, sources, self.bsp)
        if not bsp.candidate:
            raise ValueError('Current-start BSP refused: '+bsp.reason)
        finished = check()
        evidence = encoded(dict(format='eql-current-start-geometry-v1', seed=seed_record,
            selected_polygon=polygon, selected_coverage=asdict(selected), exact_partition=True,
            terrain=asdict(terrain), static=asdict(static), bsp=asdict(bsp),
            maximum_source_baked_z_difference=maximum_source_z_difference,
            vertical_window=vertical_window, started=began, finished=finished,
            motion_bounds_verified=False, independent_scene_verified=False,
            requires_fresh_start_pair=True, real_client_accepted=False, input_authorized=False))
        proof = sha256(evidence).hexdigest()
        geometry = GroundGeometryEvidence(self.zone, *self.pins[:3], proof,
            maximum_source_z_difference, (), True)
        start, end = reference, (*end_xy, end_z)
        plan_bytes = encoded(dict(format='eql-fixed-segment-plan-v1', zone=self.zone,
            frame='helper_package_WLD_Y_X_Z', offline_only=True, route_accepted=False,
            real_client_accepted=False, pins=dict(mesh=self.pins[0], archive=self.pins[1],
                wld=self.pins[2], static=self.pins[3], bsp=self.bsp_pin, geometry=proof),
            half_width=half_width, segments=[dict(index=0, polygon=polygon, points=(start, end))],
            scope='current_position_supervised_trial', requires_fresh_start_pair=True))
        route = FixedRoute(self.zone, self.pins[0], sha256(plan_bytes).hexdigest(), half_width,
                           (FixedSegment(polygon, start, end),))
        observer = RouteGroundObserver(mesh=self.mesh, ground=self.ground, source=self.source,
            geometry_evidence=geometry, reciprocal_links=())
        return CurrentStartPlan(route, observer, chain, bounds, plan_bytes, evidence)
