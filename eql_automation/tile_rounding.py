"""Empirical, metadata-bound float32 tile-side model for offline diagnostics.

The retained baker's native source is unavailable. Exact agreement with this
model explains copied portal coordinates; it is not proof of native code,
client collision, source support or live movement permission.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from types import MappingProxyType
import math
import re
import struct


def f32(value):
    if not isinstance(value,(int,float)) or isinstance(value,bool):
        raise ValueError('Expected finite float32 value')
    try:
        result=struct.unpack('<f',struct.pack('<f',value))[0]
    except (OverflowError,struct.error):
        raise ValueError('Float32 overflow') from None
    if not math.isfinite(result):
        raise ValueError('Expected finite float32 value')
    return result


def digest(value):
    return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None


@dataclass(frozen=True)
class TileGrid:
    zone: str
    mesh_sha256: str
    manifest_sha256: str
    baker_sha256: str
    source_archive_sha256: str
    origin_xy: tuple[float,float]
    cell_size: float
    agent_radius: float
    tile_size: int
    tile_counts_xy: tuple[int,int]

    def __post_init__(self):
        if (not isinstance(self.zone,str) or not self.zone
                or not all(digest(v) for v in (self.mesh_sha256,self.manifest_sha256,
                    self.baker_sha256,self.source_archive_sha256))
                or not isinstance(self.origin_xy,tuple) or len(self.origin_xy)!=2
                or any(f32(v)!=v for v in self.origin_xy)
                or f32(self.cell_size)!=self.cell_size or not 0<self.cell_size<=100
                or f32(self.agent_radius)!=self.agent_radius or not 0<self.agent_radius<=100
                or type(self.tile_size) is not int or not 8<=self.tile_size<=2048
                or not isinstance(self.tile_counts_xy,tuple) or len(self.tile_counts_xy)!=2
                or any(type(n) is not int or not 1<=n<=512 for n in self.tile_counts_xy)
                or self.border_cells>=self.tile_size):
            raise ValueError('Invalid pinned tile grid')

    @property
    def border_cells(self):
        return math.ceil(f32(self.agent_radius/self.cell_size))+3

    def sides(self,axis,tile):
        if type(axis) is not int or axis not in (0,1) or type(tile) is not int or not 0<=tile<self.tile_counts_xy[axis]:
            raise ValueError('Tile index outside copied grid')
        world=f32(self.tile_size*self.cell_size)
        border=f32(self.border_cells*self.cell_size)
        base=f32(f32(self.origin_xy[axis]+f32(tile*world))-border)
        return f32(base+border),f32(base+f32((self.tile_size+self.border_cells)*self.cell_size))

    @cached_property
    def coordinate_pairs(self):
        pairs={}
        for axis in (0,1):
            for lower in range(self.tile_counts_xy[axis]-1):
                a,b=self.sides(axis,lower)[1],self.sides(axis,lower+1)[0]
                # The explicit diagnostic cap is unchanged by coordinate
                # magnitude; an exact predicted pair is still mandatory.
                if not 0<abs(a-b)<=.0005:
                    continue
                boundary=TileBoundary(self,axis,lower)
                for first,second in ((a,b),(b,a)):
                    pairs.setdefault((axis,first,second),[]).append(boundary)
        return MappingProxyType({key:tuple(value) for key,value in pairs.items()})

    def match(self,axis,first,second):
        matches=self.coordinate_pairs.get((axis,first,second),())
        return matches[0] if len(matches)==1 else None


@dataclass(frozen=True)
class TileBoundary:
    grid: TileGrid
    axis: int
    lower_tile: int

    def __post_init__(self):
        if (not isinstance(self.grid,TileGrid) or type(self.axis) is not int or self.axis not in (0,1)
                or type(self.lower_tile) is not int or not 0<=self.lower_tile<self.grid.tile_counts_xy[self.axis]-1):
            raise ValueError('Invalid adjacent tile pair')

    @property
    def lower_tile_maximum(self):
        return self.grid.sides(self.axis,self.lower_tile)[1]

    @property
    def upper_tile_minimum(self):
        return self.grid.sides(self.axis,self.lower_tile+1)[0]

    def matches(self,axis,first,second):
        a,b=self.lower_tile_maximum,self.upper_tile_minimum
        return axis==self.axis and 0<abs(a-b)<=.0005 and (first,second) in ((a,b),(b,a))


def grid_from_metadata(manifest,meta,*,manifest_sha256,mesh_sha256,zone):
    """Caller hashes the actual manifest/mesh bytes and supplies NPZ metadata."""
    if (manifest.get('format')!=1 or meta.get('format')!=1 or manifest.get('zone')!=zone
            or meta.get('zone')!=zone or manifest.get('mesh_sha256')!=mesh_sha256
            or any(manifest.get(k)!=meta.get(k) for k in ('params','sources','tiles'))
            or manifest.get('extra',{}).get('geometry',{}).get('bounds') !=
               meta.get('extra',{}).get('geometry',{}).get('bounds')):
        raise ValueError('Tile grid manifest/mesh identity mismatch')
    params=manifest['params']
    origin=manifest['extra']['geometry']['bounds'][0]
    # Recast (X,Z) is package (Y,X). Keep the count conversion explicit.
    return TileGrid(zone,mesh_sha256,manifest_sha256,meta['baker_sha256'],
        manifest['sources'][zone+'.s3d'],tuple(f32(v) for v in origin[:2]),
        f32(params['cell_size']),f32(params['agent_radius']),params['tile_size'],
        (manifest['tiles']['z'],manifest['tiles']['x']))
