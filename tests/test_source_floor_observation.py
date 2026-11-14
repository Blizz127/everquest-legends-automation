"""Exact-point source lookup, using analytic triangles and no game files."""
import unittest

import numpy as np

from eql_automation.portal_precision import SourceFace
from eql_automation.portal_precision_view import PortalPrecisionView


def view(*faces):
    result = object.__new__(PortalPrecisionView)
    result.sources = faces
    coordinates = np.asarray([f.vertices_wld for f in faces])[:, :, [1, 0, 2]]
    result.source_minimum = coordinates.min(axis=1)
    result.source_maximum = coordinates.max(axis=1)
    return result


def face(z=0., *, flag=0, material='Diffuse', index=1):
    return SourceFace(((0., 0., z), (1., 0., z+1.), (0., 1., z+2.)),
                       flag, material, 7, index)


class SourceFloorObservationTests(unittest.TestCase):
    def test_queries_source_frame_without_swapping_height(self):
        height, surfaces = view(face()).source_floor_at((.1, .2))
        self.assertAlmostEqual(height, .4)
        self.assertEqual(surfaces, ('wld:7:face:1',))

    def test_other_floor_cannot_be_removed_by_nearest_height(self):
        with self.assertRaisesRegex(ValueError, 'layered'):
            view(face(), face(100., index=2)).source_floor_at((.1, .2))

    def test_shared_source_edge_with_same_height_retains_both_faces(self):
        neighbor = SourceFace(((1., 0., 1.), (1., 1., 3.), (0., 1., 2.)),
                               0, 'Diffuse', 7, 2)
        height, surfaces = view(face(), neighbor).source_floor_at((.5, .5))
        self.assertEqual(height, 1.5)
        self.assertEqual(surfaces, ('wld:7:face:1', 'wld:7:face:2'))

    def test_missing_or_unsupported_source_refuses(self):
        with self.assertRaises(ValueError): view(face()).source_floor_at((.8, .8))
        with self.assertRaises(ValueError): view(face(flag=16)).source_floor_at((.1, .2))
        with self.assertRaises(ValueError): view(face(material='Water')).source_floor_at((.1, .2))
        with self.assertRaises(ValueError): view(face()).source_floor_at((float('nan'), .2))

    def test_candidate_budget_never_truncates_a_layer(self):
        with self.assertRaisesRegex(ValueError, 'budget'):
            view(*(face(index=i) for i in range(129))).source_floor_at((.1, .2))

    def test_footprint_query_keeps_all_heights_and_outer_margin(self):
        near=SourceFace(((1.001,0.,0.),(2.,0.,0.),(1.001,1.,0.)),0,'Diffuse',7,3)
        sources=view(face(),face(100.,index=2),near)
        # Input uses helper XY; the extra triangle is within the .002 margin
        # beyond raw X=1 even though it misses the unexpanded footprint.
        found=sources.source_faces_for_footprint(((.1,.1),(.8,.1),(.8,1.),(.1,1.)))
        self.assertEqual(tuple(f.face for f in found),(1,2,3))

    def test_footprint_candidate_budget_is_exhaustive(self):
        with self.assertRaisesRegex(ValueError,'budget'):
            view(*(face(index=i) for i in range(129))).source_faces_for_footprint(
                ((.1,.1),(.3,.1),(.3,.3),(.1,.3)))
