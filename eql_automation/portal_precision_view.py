"""Complete copied-mesh/source lookup for local offline precision retries."""
from __future__ import annotations

from pathlib import Path
import numpy as np

from .ground_sweep import GroundFace
from .material_audit import mesh_face_materials
from .mesh_geometry import read_meshes
from .pfs_archive import PFSArchive
from .portal_precision import PortalLink, PrecisionCheck, SourceFace, collect_seams, retry_precision_gap
from .wld_inventory import WLDInventory


class PortalPrecisionView:
    def __init__(self, ground_view, mesh_path: Path, archive_path: Path, *, zone):
        self.ground = ground_view
        with np.load(mesh_path,allow_pickle=False) as data:
            a = np.asarray(data['link_a'],dtype=np.int64).reshape(-1)
            b = np.asarray(data['link_b'],dtype=np.int64).reshape(-1)
            edges = np.asarray(data['link_pts'],dtype=np.float64).reshape(-1,2,3)
        count = len(ground_view.areas)
        if (not 1 <= len(a) <= 1000000 or len(a) != len(b) or len(a) != len(edges)
                or min(a.min(),b.min()) < 0 or max(a.max(),b.max()) >= count or not np.isfinite(edges).all()):
            raise ValueError('Invalid copied precision portal arrays')
        links = (PortalLink(int(x),int(y),tuple(tuple(float(n) for n in p) for p in edge))
                 for x,y,edge in zip(a,b,edges))
        self.seams = collect_seams(links,ground_view.areas,ground_view.components)
        self.by_polygon = {}
        for index,seam in enumerate(self.seams):
            for poly in (seam.source,seam.target):
                self.by_polygon.setdefault(poly,set()).add(index)
        archive = PFSArchive(archive_path)
        wld = WLDInventory(archive.read_member(zone+'.wld'))
        self.archive_sha256, self.wld_sha256 = archive.sha256,wld.sha256
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

    def retry(self,original,footprint,detail_ids,*,reference,component,vertical_window,
              maximum_source_z_difference):
        if original.candidate or original.reason != 'uncovered_ground_area':
            return PrecisionCheck(False,'original_failure_is_not_a_coverage_gap')
        polygons = tuple(int(self.ground.polys[i]) for i in detail_ids)
        present = set(polygons)
        possible = set().union(*(self.by_polygon.get(poly,set()) for poly in present))
        seams = tuple(self.seams[i] for i in sorted(possible)
                      if self.seams[i].source in present and self.seams[i].target in present)
        if not 1 <= len(seams) <= 8:
            return PrecisionCheck(False,'no_bounded_reciprocal_seam_set')
        # Include all source XY boxes in the expanded margin, at every height.
        left,right = np.min(footprint,axis=0)-.002,np.max(footprint,axis=0)+.002
        local = np.flatnonzero((self.source_minimum[:,0] <= right[0]) & (self.source_maximum[:,0] >= left[0])
                              & (self.source_minimum[:,1] <= right[1]) & (self.source_maximum[:,1] >= left[1]))
        if len(local) > 128:
            return PrecisionCheck(False,'source_projection_candidate_budget_exceeded')
        sources = tuple(self.sources[i] for i in local)
        faces = tuple(GroundFace(tuple(tuple(float(v) for v in p) for p in self.ground.triangles[i]),
                                int(self.ground.areas[poly]),int(self.ground.components[poly]))
                      for i,poly in zip(detail_ids,polygons))
        return retry_precision_gap(original,footprint,faces,polygons,seams,sources,
            reference=reference,component=component,vertical_window=vertical_window,
            maximum_source_z_difference=maximum_source_z_difference)
