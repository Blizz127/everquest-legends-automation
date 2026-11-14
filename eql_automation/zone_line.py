"""Exact copied zone-line geometry for an explicit crossing, never dry ground.

This permits a footprint to overlap ONE named transition region. It grants no
input authority and does not establish the server's destination or spawn.
"""
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re

from .client_region_labels import ClientRegionMap, decode_client_region_label


def digest(value):
    return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None


@dataclass(frozen=True)
class ExpectedZoneLine:
    crossing_id: str
    zone: str
    mesh_sha256: str
    archive_sha256: str
    wld_sha256: str
    bsp_inventory_sha256: str
    manifest_sha256: str
    raw_label: str
    area_id: int
    polygon_ids: tuple[int,...]
    region_ids: tuple[int,...]

    def __post_init__(self):
        if (not isinstance(self.crossing_id,str) or not self.crossing_id
                or not isinstance(self.zone,str) or re.fullmatch('[a-z0-9]{1,32}',self.zone) is None
                or not all(digest(v) for v in (self.mesh_sha256,self.archive_sha256,self.wld_sha256,
                    self.bsp_inventory_sha256,self.manifest_sha256))
                or type(self.area_id) is not int or not 2<=self.area_id<63):
            raise ValueError('Exact crossing identity and copied geometry pins required')
        for ids in (self.polygon_ids,self.region_ids):
            if (not isinstance(ids,tuple) or not 1<=len(ids)<=128
                    or any(type(i) is not int or i<0 for i in ids) or tuple(sorted(set(ids)))!=ids):
                raise ValueError('Exact unique bounded zone-line IDs required')
        flags=decode_client_region_label(self.raw_label)
        if (flags.matched_prefix!='DR' or flags.flags!=0x80000000
                or flags.transition_write_kind!='copy_complete_label'
                or flags.transition_source!=self.raw_label):
            raise ValueError('Only the inspected pure DR transition-label form is supported')

    @classmethod
    def from_sources(cls, *, crossing_id, wld, bsp, mesh, manifest_bytes, area_id):
        from .bsp_volume import BspVolumeView
        if not isinstance(bsp,BspVolumeView) or not isinstance(manifest_bytes,bytes):
            raise ValueError('Copied BSP and exact manifest bytes required')
        manifest=json.loads(manifest_bytes)
        zone=manifest['zone'];pin=manifest['mesh_sha256']
        if (getattr(mesh,'sha256',None)!=pin or mesh.meta.get('zone')!=zone
                or wld.sha256!=bsp.wld_sha256):
            raise ValueError('Zone-line sources do not describe the same copied geometry')
        rows=[r for r in manifest['extra']['zone_lines'] if r['area']==area_id]
        if len(rows)!=1:
            raise ValueError('Expected zone-line area must have exactly one manifest record')
        label=rows[0]['raw']
        if manifest['areas'][str(area_id)].get('raw')!=label:
            raise ValueError('Manifest area and zone-line labels disagree')
        native=ClientRegionMap(wld)
        regions=tuple(i for i,record in enumerate(native.region_to_record)
                      if record>=0 and native.records[record][1]==label)
        polygons=tuple(i for i,area in enumerate(mesh.area) if int(area)==area_id)
        if len(polygons)!=manifest['area_polygons'][str(area_id)]:
            raise ValueError('Manifest zone-line polygon count changed')
        result=cls(crossing_id,zone,pin,manifest['sources'][zone+'.s3d'],wld.sha256,
            bsp.inventory_sha256,sha256(manifest_bytes).hexdigest(),label,area_id,polygons,regions)
        result.check_bsp(bsp)
        return result

    @property
    def sha256(self):
        return sha256(json.dumps(asdict(self),sort_keys=True,separators=(',',':')).encode()).hexdigest()

    def check_bsp(self, view):
        if (view.wld_sha256!=self.wld_sha256 or view.inventory_sha256!=self.bsp_inventory_sha256
                or any(i>=view.region_count or view.labels[i]!=('zoneline',) for i in self.region_ids)):
            raise ValueError('Expected zone line differs from the actual BSP inventory or labels')

    def check_geometry(self, *, zone, mesh_sha256, archive_sha256, wld_sha256, bsp):
        self.check_sources(zone=zone,mesh_sha256=mesh_sha256,
                           archive_sha256=archive_sha256,wld_sha256=wld_sha256)
        self.check_bsp(bsp)

    def check_sources(self, *, zone, mesh_sha256, archive_sha256, wld_sha256):
        if (zone,mesh_sha256,archive_sha256,wld_sha256)!=(
                self.zone,self.mesh_sha256,self.archive_sha256,self.wld_sha256):
            raise ValueError('Expected zone line belongs to another source geometry')

    def allows_face(self, polygon, area):
        return type(polygon) is int and polygon in self.polygon_ids and area==self.area_id

    def allows_region(self, region, labels):
        return region in self.region_ids and labels==('zoneline',)

    def record(self):
        return dict(asdict(self),sha256=self.sha256,destination_verified=False,
                    spawn_coordinate_verified=False,input_authorized=False,real_client_accepted=False)
