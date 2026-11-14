"""Copied static-instance faces for conditional, all-height occupancy queries.

The caller supplies and pins the retained bake's transform. This adapter does
not select supporting floors, discard collision/material flags, or authorize
input. Dynamic objects and actual client collision behavior remain unverified.
"""
from __future__ import annotations

from dataclasses import asdict,dataclass
from hashlib import sha256
import json
from struct import unpack_from
from types import SimpleNamespace

import numpy as np

from .ground_sweep import finite
from .material_audit import mesh_face_materials
from .mesh_geometry import read_meshes
from .model_links import combine_model_links
from .placement_audit import read_object_locations
from .portal_precision import SourceFace


@dataclass(frozen=True)
class StaticModel:
    library_sha256: str
    mesh: object
    material_classes: tuple[str,...]


def validate_single_component_actors(library):
    """Fixed-offset links are supported only for the observed single-mesh layout."""
    for fragment in library.fragments:
        if fragment.type_code!=0x14:continue
        body=library.body(fragment)
        if (len(body)!=40 or tuple(unpack_from('<I',body,offset)[0] for offset in (0,8,12,20))
                !=(128,1,1,1)):
            raise ValueError('Unsupported static actor layout; additional components cannot be omitted')


class StaticSourceView:
    """Immutable transformed faces; exact XY AABBs, with no Z culling."""

    def __init__(self,locations,models,*,objects_sha256,terrain_fragment_max,
                 transform,transform_sha256,max_faces=1_000_000):
        if (type(terrain_fragment_max) is not int or terrain_fragment_max<0
                or type(max_faces) is not int or not 1<=max_faces<=1_000_000
                or len(locations)>100_000):
            raise ValueError('Invalid static-source inventory budget')
        for digest in (objects_sha256,transform_sha256):
            if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
                raise ValueError('Static-source provenance needs SHA-256 identities')
        if len({p.fragment_index for p in locations})!=len(locations):
            raise ValueError('Duplicate placement fragment')
        self.sources=[];self.identities={};self.excluded=[]
        records=[]
        for p in locations:
            if not all(finite(v) for v in (p.x,p.y,p.z,p.rot_z,p.rot_y,p.rot_x,p.scale_y,p.scale_x)):
                raise ValueError('Nonfinite placement')
            # Match the retained baker's explicit parked-height band; record
            # every exclusion, rather than silently using a narrower sentinel.
            if p.z<=-31768.:
                self.excluded.append({'fragment':p.fragment_index,'actor':p.actor_name,
                                      'z':p.z,'reason':'retained_baker_parked_height_band'})
                continue
            if p.actor_name not in models:
                raise ValueError('Placement lacks an exact supported static model')
            model=models[p.actor_name]
            if p.scale_y<=0 or not isinstance(model,StaticModel):
                raise ValueError('Unsupported static model or placement scale')
            records.append((p,model))
        records.sort(key=lambda item:(item[0].fragment_index,item[1].library_sha256,item[1].mesh.fragment_index))
        for ordinal,(p,model) in enumerate(records):
            mesh=model.mesh
            if len(model.material_classes)!=len(mesh.triangles):
                raise ValueError('Every static face needs material provenance')
            if len(self.sources)+len(mesh.triangles)>max_faces:
                raise ValueError('Static-source face budget exceeded')
            fragment=terrain_fragment_max+1+ordinal
            identity={'objects_wld_sha256':objects_sha256,'placement_fragment':p.fragment_index,
                      'model_wld_sha256':model.library_sha256,'mesh_fragment':mesh.fragment_index,
                      'actor_name':p.actor_name,'transform_sha256':transform_sha256,
                      'transform_convention':'model','location':asdict(p)}
            self.identities[fragment]=identity
            relative=np.asarray(mesh.raw_vertices,dtype=np.float64)/(1<<mesh.scale)
            placement=SimpleNamespace(position=(p.x,p.y,p.z),rotation=(p.rot_z,p.rot_y,p.rot_x),
                                      scale=(0.,p.scale_y,p.scale_x))
            vertices=np.asarray(transform(relative,np.asarray(mesh.center,dtype=np.float64),
                                          placement,convention='model'))
            if (vertices.dtype!=np.float32 or vertices.shape!=(len(mesh.raw_vertices),3)
                    or not np.isfinite(vertices).all()):
                raise ValueError('Retained model transform must return finite float32 XYZ')
            for index,face in enumerate(mesh.triangles):
                points=tuple(tuple(float(v) for v in vertices[i]) for i in (face.a,face.b,face.c))
                self.sources.append(SourceFace(points,face.flag,model.material_classes[index],fragment,index))
        self.sources=tuple(self.sources)
        coordinates=np.asarray([s.vertices_wld for s in self.sources],dtype=np.float64).reshape(-1,3,3)
        # WLD XYZ -> helper YXZ only at this spatial-index boundary.
        package=coordinates[:,:,[1,0,2]]
        self.minimum=package.min(axis=1);self.maximum=package.max(axis=1)
        self.minimum.flags.writeable=False;self.maximum.flags.writeable=False
        provenance={'objects':objects_sha256,'transform':transform_sha256,
                    'identities':self.identities,'excluded':self.excluded,
                    'face_labels':[(s.fragment,s.face,s.flag,s.material_class) for s in self.sources]}
        digest=sha256(json.dumps(provenance,sort_keys=True,separators=(',',':')).encode())
        digest.update(coordinates.astype('<f8').tobytes())
        self.inventory_sha256=digest.hexdigest()

    @classmethod
    def from_wld(cls,objects,libraries,*,terrain_fragment_max,transform,transform_sha256):
        for library in libraries:validate_single_component_actors(library)
        links=combine_model_links(libraries)
        meshes={w.sha256:{m.fragment_index:m for m in read_meshes(w)} for w in libraries}
        fragments={w.sha256:{f.index:f for f in w.fragments} for w in libraries}
        models={}
        for actor,(library,link) in links.items():
            if not link.exact_expected_mesh_name:
                raise ValueError('Static actor mesh name does not match exactly')
            mesh=meshes[library.sha256][link.mesh_fragment_index]
            materials=mesh_face_materials(library,fragments[library.sha256][mesh.fragment_index])
            models[actor]=StaticModel(library.sha256,mesh,tuple(m.material_class for m in materials))
        return cls(read_object_locations(objects),models,objects_sha256=objects.sha256,
                   terrain_fragment_max=terrain_fragment_max,transform=transform,
                   transform_sha256=transform_sha256)

    def faces_for_footprint(self,footprint,*,max_faces=128):
        if (not isinstance(footprint,tuple) or not 3<=len(footprint)<=64
                or any(not isinstance(p,tuple) or len(p)!=2 or not all(finite(v) for v in p) for p in footprint)
                or type(max_faces) is not int or not 1<=max_faces<=128):
            raise ValueError('Invalid static-source query')
        low=np.min(footprint,axis=0)-.002;high=np.max(footprint,axis=0)+.002
        hits=np.flatnonzero((self.minimum[:,0]<=high[0])&(self.maximum[:,0]>=low[0])
                           &(self.minimum[:,1]<=high[1])&(self.maximum[:,1]>=low[1]))
        if len(hits)>max_faces:
            raise ValueError('Static-source query exceeds face budget; never truncated')
        return tuple(self.sources[int(i)] for i in hits)
