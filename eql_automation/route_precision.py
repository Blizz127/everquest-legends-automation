"""Explicit numerical tile policy for receipt-bound route geometry.

The pinned model explains copied mesh seams only. Every accepted footprint
still needs continuous source support, static collision and BSP checks.
"""
from dataclasses import asdict, dataclass

from .tile_rounding import TileGrid


@dataclass(frozen=True)
class RoutePrecisionPolicy:
    grid: TileGrid
    allow_overlap: bool = False

    def __post_init__(self):
        if not isinstance(self.grid, TileGrid) or type(self.allow_overlap) is not bool:
            raise ValueError('An exact tile grid and explicit overlap policy are required')

    def record(self):
        return dict(format='eql-route-tile-policy-v1', **asdict(self),
                    numerical_model_only=True, real_client_accepted=False)


def precision_binding(source, policy, *, zone, mesh_sha256, archive_sha256):
    """Pin immutable model/seam objects; no implicit tile-mode activation."""
    grid = getattr(source, 'tile_grid', None)
    seams = source.seams
    if not isinstance(seams, tuple):
        raise ValueError('Route precision seams must be immutable')
    if policy is None:
        if grid is not None:
            raise ValueError('A tile-mode source requires an explicit route precision policy')
    elif (not isinstance(policy, RoutePrecisionPolicy) or grid is not policy.grid
            or (grid.zone, grid.mesh_sha256, grid.source_archive_sha256)
                != (zone, mesh_sha256, archive_sha256)):
        raise ValueError('Route precision grid differs from pinned zone/mesh/archive')
    return (id(policy), policy, id(grid), grid, id(seams), seams)


def validate_precision_seams(source, policy):
    """Check the complete retained immutable inventory once at construction."""
    if policy is None and any(s.tile_boundary is not None for s in source.seams):
        raise ValueError('Tile seams require an explicit route precision policy')
    if policy is not None and any(s.tile_boundary is None
            or s.tile_boundary.grid is not policy.grid for s in source.seams):
        raise ValueError('Route seam inventory differs from the selected tile grid')
