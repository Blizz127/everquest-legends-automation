"""Complete copied-mesh/source lookup for local offline precision retries."""
from __future__ import annotations

from pathlib import Path
from hashlib import sha256
import json
import numpy as np

from .ground_sweep import GroundFace
from .material_audit import mesh_face_materials
from .map_alignment import _triangle_height
from .mesh_geometry import read_meshes
from .pfs_archive import PFSArchive
from .portal_precision import PortalLink, PrecisionCheck, SourceFace, collect_seams, retry_precision_gap
from .wld_inventory import WLDInventory
from .tile_rounding import grid_from_metadata


class PortalPrecisionView:
    def __init__(self, ground_view, mesh_path: Path, archive_path: Path, *, zone, maximum_ulp_steps=1,
                 tile_rounding=False):
        self.ground = ground_view
        with np.load(mesh_path,allow_pickle=False) as data:
            a = np.asarray(data['link_a'],dtype=np.int64).reshape(-1)
            b = np.asarray(data['link_b'],dtype=np.int64).reshape(-1)
            edges = np.asarray(data['link_pts'],dtype=np.float64).reshape(-1,2,3)
            meta = json.loads(str(data['meta'])) if tile_rounding else None
            rings = np.asarray(data['poly_verts'],dtype=np.float64) if tile_rounding else None
            sizes = np.asarray(data['poly_nv'],dtype=np.int64) if tile_rounding else None
        count = len(ground_view.areas)
        if (not 1 <= len(a) <= 1000000 or len(a) != len(b) or len(a) != len(edges)
                or min(a.min(),b.min()) < 0 or max(a.max(),b.max()) >= count or not np.isfinite(edges).all()):
            raise ValueError('Invalid copied precision portal arrays')
        links = (PortalLink(int(x),int(y),tuple(tuple(float(n) for n in p) for p in edge))
                 for x,y,edge in zip(a,b,edges))
        if type(maximum_ulp_steps) is not int or maximum_ulp_steps not in (1,2):
            raise ValueError('Only explicit one- or two-ULP diagnostics are supported')
        self.tile_grid=None
        if tile_rounding:
            if tile_rounding is not True or maximum_ulp_steps!=1:
                raise ValueError('Use either the tile model or an explicit ULP classifier')
            manifest_path=mesh_path.with_suffix('.json')
            if mesh_path.is_symlink() or manifest_path.is_symlink():
                raise ValueError('Pinned tile inputs must be regular files')
            manifest_bytes=manifest_path.read_bytes()
            self.tile_grid=grid_from_metadata(json.loads(manifest_bytes),meta,
                manifest_sha256=sha256(manifest_bytes).hexdigest(),
                mesh_sha256=sha256(mesh_path.read_bytes()).hexdigest(),zone=zone)
        self.seams = collect_seams(links,ground_view.areas,ground_view.components,
                                  maximum_ulp_steps=maximum_ulp_steps,tile_grid=self.tile_grid)
        self.tile_orientation_refusals=0
        if self.tile_grid is not None:
            if (rings.ndim!=3 or rings.shape[0]!=count or rings.shape[2]!=3
                    or sizes.shape!=(count,) or np.any(sizes<3) or np.any(sizes>rings.shape[1])
                    or not np.isfinite(rings).all()):
                raise ValueError('Invalid copied polygon rings')
            accepted=[]
            for seam in self.seams:
                good=True
                for poly,coordinate in ((seam.source,seam.source_coordinate),(seam.target,seam.target_coordinate)):
                    side=-1 if coordinate==seam.tile_boundary.lower_tile_maximum else 1
                    offsets=(rings[poly,:sizes[poly],seam.axis]-coordinate)*side
                    if np.min(offsets)<0 or np.max(offsets)<=0:good=False
                if good:accepted.append(seam)
                else:self.tile_orientation_refusals+=1
            self.seams=tuple(accepted)
        self.by_polygon = {}
        for index,seam in enumerate(self.seams):
            for poly in (seam.source,seam.target):
                self.by_polygon.setdefault(poly,set()).add(index)
        archive = PFSArchive(archive_path)
        wld = WLDInventory(archive.read_member(zone+'.wld'))
        self.archive_sha256, self.wld_sha256 = archive.sha256,wld.sha256
        if self.tile_grid is not None and self.tile_grid.source_archive_sha256!=self.archive_sha256:
            raise ValueError('Source archive does not match tile manifest')
        fragments = {f.index:f for f in wld.fragments}
        self.sources = []
        for mesh in read_meshes(wld):
            materials = mesh_face_materials(wld,fragments[mesh.fragment_index])
            vertices = tuple(mesh.vertex(i) for i in range(len(mesh.raw_vertices)))
            for index,face in enumerate(mesh.triangles):
                self.sources.append(SourceFace(tuple(vertices[i] for i in (face.a,face.b,face.c)),
                    face.flag,materials[index].material_class,mesh.fragment_index,index))
        if not 1 <= len(self.sources) <= 1000000:
            raise ValueError('Copied source terrain exceeds diagnostic budget')
        # Convert only at this explicit boundary: helper X=raw WLD Y.
        coordinates = np.asarray([f.vertices_wld for f in self.sources],dtype=np.float64)[:,:,[1,0,2]]
        self.source_minimum,self.source_maximum = coordinates.min(axis=1),coordinates.max(axis=1)

    def source_floor_at(self, package_xy):
        """Sample all copied terrain layers at exact XY; never choose nearest Z.

        This is an offline terrain point observation, not a body/obstacle
        check. Shared source edges may have multiple faces at the same Z.
        """
        x,y = package_xy
        if not np.isfinite((x,y)).all():
            raise ValueError('Invalid source-floor point')
        local = np.flatnonzero((self.source_minimum[:,0] <= x) & (self.source_maximum[:,0] >= x)
                              & (self.source_minimum[:,1] <= y) & (self.source_maximum[:,1] >= y))
        if len(local)>128:
            raise ValueError('Source-floor candidate budget exceeded')
        hits = []
        for index in local:
            face = self.sources[index]
            height = _triangle_height(y,x,face.vertices_wld)
            if height is not None:
                if face.flag != 0 or face.material_class != 'Diffuse':
                    raise ValueError('Source floor has unsupported collision/material')
                hits.append((height, f'wld:{face.fragment}:face:{face.face}'))
        if not hits or max(h[0] for h in hits)-min(h[0] for h in hits)>1e-7:
            raise ValueError('Copied source floor missing or layered at exact XY')
        return hits[0][0], tuple(h[1] for h in hits)

    def source_faces_for_footprint(self,footprint):
        """All XY source candidates across every height, including margin."""
        left,right = np.min(footprint,axis=0)-.002,np.max(footprint,axis=0)+.002
        local = np.flatnonzero((self.source_minimum[:,0] <= right[0]) & (self.source_maximum[:,0] >= left[0])
                              & (self.source_minimum[:,1] <= right[1]) & (self.source_maximum[:,1] >= left[1]))
        if len(local)>128:
            raise ValueError('Source projection candidate budget exceeded')
        return tuple(self.sources[i] for i in local)

    def retry(self,original,footprint,detail_ids,*,reference,component,vertical_window,
              maximum_source_z_difference,allow_overlap=False):
        allowed = ('uncovered_ground_area','overlapping_ground_faces') if allow_overlap is True else ('uncovered_ground_area',)
        if original.candidate or original.reason not in allowed:
            return PrecisionCheck(False,'original_failure_is_not_a_coverage_gap')
        polygons = tuple(int(self.ground.polys[i]) for i in detail_ids)
        present = set(polygons)
        possible = set().union(*(self.by_polygon.get(poly,set()) for poly in present))
        seams = tuple(self.seams[i] for i in sorted(possible)
                      if self.seams[i].source in present and self.seams[i].target in present)
        if not 1 <= len(seams) <= 8:
            return PrecisionCheck(False,'no_bounded_reciprocal_seam_set')
        # Include all source XY boxes in the expanded margin, at every height.
        try:
            sources = self.source_faces_for_footprint(footprint)
        except ValueError:
            return PrecisionCheck(False,'source_projection_candidate_budget_exceeded')
        faces = tuple(GroundFace(tuple(tuple(float(v) for v in p) for p in self.ground.triangles[i]),
                                int(self.ground.areas[poly]),int(self.ground.components[poly]))
                      for i,poly in zip(detail_ids,polygons))
        return retry_precision_gap(original,footprint,faces,polygons,seams,sources,
            reference=reference,component=component,vertical_window=vertical_window,
            maximum_source_z_difference=maximum_source_z_difference,allow_overlap=allow_overlap)
