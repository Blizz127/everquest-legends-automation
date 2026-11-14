"""Analytic test evidence only; no client data or live calibration."""
from datetime import datetime

from eql_automation.ground_binding import (
    AlignedWldFix, GroundGeometryEvidence, HeightCalibration,
    MeshProjection, SourceFloorObservation,
)
from eql_automation.location_log import RawLocationFix

MESH = 'a' * 64
ARCHIVE = 'c' * 64
WLD = 'd' * 64
PROOF = 'e' * 64
MOTION = 'synthetic-stopped-route-test'
HEIGHT = HeightCalibration('synthetic-source-height', 'gfaydark', 54,
    'Greater Faydark', 1, 1, ARCHIVE, WLD, 2.5, .05, 0, 0., 1e12,
    live_verified=True)
GEOMETRY = GroundGeometryEvidence('gfaydark', MESH, ARCHIVE, WLD, PROOF,
    1., ((1, 2),), geometry_verified=True)


def aligned(point=(0., 0., 0.), *, at=100., seq=1, polygon=1, component=2,
            source_z=None, height_calibration=HEIGHT, neighbors=()):
    point = tuple(point)
    # Deliberately variable bake offset, unrelated to character height.
    if source_z is None:
        source_z = point[2] - (.3 + .001 * point[1])
    source_point = (point[1], point[0], source_z)
    raw_point = (*source_point[:2], source_z + 2.5)
    raw = RawLocationFix(54, 'Greater Faydark', raw_point, datetime(2026, 11, 14),
                         at, 1, seq, 1)
    source = SourceFloorObservation(raw, source_point, ARCHIVE, WLD,
                                    ('synthetic-ground',), 1, True)
    projection = MeshProjection(raw, point, MESH, polygon, 63, component,
        ARCHIVE, WLD, source.source_surface_ids, PROOF, 1., neighbors, True, True)
    return AlignedWldFix(raw, source, projection, height_calibration,
                         'gfaydark', MOTION, True)
