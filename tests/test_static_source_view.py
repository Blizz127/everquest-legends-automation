import unittest
from dataclasses import replace
from struct import pack_into
from types import SimpleNamespace

try:
    import numpy as np
except ImportError:
    raise unittest.SkipTest('Copied-geometry tests require the private numpy environment')

from eql_automation.mesh_geometry import MeshGeometry,Triangle
from eql_automation.placement_audit import ObjectLocation
from eql_automation.static_source_view import StaticModel,StaticSourceView,validate_single_component_actors


def transform(relative,center,p,*,convention):
    assert convention=='model'
    assert np.array_equal(relative,((0.,0.,0.),(2.,0.,0.),(0.,2.,2.)))
    assert tuple(center)==(10.,20.,30.)
    return ((relative+center)*p.scale[1]+p.position).astype(np.float32)


def location(fragment,z=0.):
    return ObjectLocation(fragment,'model_ACTORDEF',0,0.,0.,z,0.,0.,0.,1.,1.,False)


class StaticSourceTests(unittest.TestCase):
    def build(self,locations,**options):
        mesh=MeshGeometry(4,'model_DMSPRITEDEF',0,(10.,20.,30.),1,
            ((0,0,0),(4,0,0),(0,4,4)),(Triangle(0x10,0,1,2),),0)
        defaults=dict(objects_sha256='a'*64,terrain_fragment_max=100,
                      transform=transform,transform_sha256='b'*64)
        defaults.update(options)
        return StaticSourceView(locations,{'model_ACTORDEF':StaticModel('c'*64,mesh,('TransparentMasked',))},**defaults)

    def test_repeated_instances_have_distinct_reproducible_ids_and_keep_all_heights(self):
        locations=(location(8,70.),location(7))
        a=self.build(locations);b=self.build(tuple(reversed(locations)))
        self.assertEqual(a.inventory_sha256,b.inventory_sha256)
        self.assertEqual([(s.fragment,s.face) for s in a.sources],[(101,0),(102,0)])
        self.assertEqual(a.identities[101]['placement_fragment'],7)
        hits=a.faces_for_footprint(((19.,9.),(23.,9.),(23.,13.),(19.,13.)))
        self.assertEqual(len(hits),2)
        self.assertEqual({s.vertices_wld[0][2] for s in hits},{30.,100.})
        self.assertTrue(all(s.flag==0x10 and s.material_class=='TransparentMasked' for s in hits))

    def test_center_added_exactly_once_and_inputs_preserve_rotation_order(self):
        def probe(relative,center,p,*,convention):
            self.assertEqual(p.rotation,(128.,64.,32.))
            self.assertEqual(p.scale,(0.,2.,3.))
            return transform(relative,center,p,convention=convention)
        p=replace(location(7),x=5.,y=6.,z=7.,rot_z=128.,rot_y=64.,rot_x=32.,scale_y=2.,scale_x=3.)
        view=self.build((p,),transform=probe)
        self.assertEqual(view.sources[0].vertices_wld[0],(25.,46.,67.))

    def test_parked_height_boundary_is_explicitly_recorded(self):
        view=self.build((location(7,-31768.),location(8,-31767.5)))
        self.assertEqual(len(view.sources),1)
        self.assertEqual(view.identities[101]['placement_fragment'],8)
        self.assertEqual(view.excluded[0]['fragment'],7)
        self.assertEqual(view.excluded[0]['z'],-31768.)

    def test_vertical_faces_and_query_margin_are_not_discarded(self):
        def vertical(relative,center,p,*,convention):
            return np.array(((10.,20.,0.),(10.,20.,20.),(10.,22.,20.)),dtype=np.float32)
        view=self.build((location(7),),transform=vertical)
        hits=view.faces_for_footprint(((20.5,10.001),(21.5,10.001),(21.5,11.),(20.5,11.)))
        self.assertEqual(len(hits),1)

    def test_face_budget_refuses_instead_of_truncating(self):
        view=self.build((location(7),location(8)))
        with self.assertRaises(ValueError):
            view.faces_for_footprint(((19.,9.),(23.,9.),(23.,13.),(19.,13.)),max_faces=1)
        with self.assertRaises(ValueError):self.build((location(7),location(8)),max_faces=1)

    def test_unknown_models_duplicate_placements_and_wrong_transform_dtype_refuse(self):
        with self.assertRaises(ValueError):self.build((replace(location(7),actor_name='unknown'),))
        with self.assertRaises(ValueError):self.build((location(7),location(7)))
        with self.assertRaises(ValueError):
            self.build((location(7),),transform=lambda *a,**k:np.zeros((3,3),dtype=np.float64))

    def test_all_parked_inventory_can_be_queried_without_inventing_geometry(self):
        view=self.build((location(7,-32768.),))
        self.assertEqual(view.sources,())
        self.assertEqual(view.faces_for_footprint(((0.,0.),(1.,0.),(0.,1.))),())

    def test_unparsed_extra_actor_components_are_never_silently_omitted(self):
        body=bytearray(40)
        for offset,value in ((0,128),(8,1),(12,1),(20,1)):pack_into('<I',body,offset,value)
        library=SimpleNamespace(fragments=(SimpleNamespace(type_code=0x14),),body=lambda _:body)
        validate_single_component_actors(library)
        pack_into('<I',body,12,2)
        with self.assertRaises(ValueError):validate_single_component_actors(library)
        pack_into('<I',body,12,1);body.extend(b'\0'*4)
        with self.assertRaises(ValueError):validate_single_component_actors(library)


if __name__=='__main__':unittest.main()
