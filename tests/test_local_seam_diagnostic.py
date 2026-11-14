"""Synthetic tests of the diagnostic patch's source/portal scope, no client data."""
from types import SimpleNamespace

from tools.replay_fixed_route import local_seam_diagnostic


def fixture():
    west, east = 1761.2440185546875, 1761.244140625
    middle = (west + east) / 2
    # Analytic flat rectangles, not copied client triangles.
    triangles = {
        0: ((west-2, -2., 0.), (west, -2., 0.), (west, 2., 0.)),
        1: ((west-2, -2., 0.), (west, 2., 0.), (west-2, 2., 0.)),
        2: ((east, -2., 0.), (east+2, -2., 0.), (east+2, 2., 0.)),
        3: ((east, -2., 0.), (east+2, 2., 0.), (east, 2., 0.)),
    }
    view = SimpleNamespace(triangles=triangles, polys={0:31668, 1:31668, 2:32479, 3:32479},
                           areas={31668:63, 32479:63}, components={31668:1, 32479:1})
    footprint = ((middle-.5, -.5), (middle+.5, -.5), (middle+.5, .5), (middle-.5, .5))
    evidence = {'source_overlaps': [{'vertices_wld': [[-10., middle-10, 0.],
                                                    [10., middle-10, 0.], [0., middle+10, 0.]]}]}
    return view, footprint, (middle-.25, 0., 0.), evidence


def test_local_patch_closes_only_reciprocal_seam_without_mutating_view():
    view, footprint, reference, evidence = fixture()
    before = repr(view.triangles)
    result = local_seam_diagnostic(view, footprint, reference, 1, 1., (0,1,2,3), evidence)
    assert result.candidate and not result.input_authorized and not result.real_client_accepted
    assert repr(view.triangles) == before


def test_source_triangle_must_contain_every_footprint_vertex():
    view, footprint, reference, evidence = fixture()
    middle = (footprint[0][0] + footprint[1][0]) / 2
    evidence['source_overlaps'][0]['vertices_wld'] = [[-.1,middle-.1,0], [.1,middle-.1,0], [0,middle+.1,0]]
    assert local_seam_diagnostic(view, footprint, reference, 1, 1., (0,1,2,3), evidence) is None


def test_patch_does_not_apply_when_one_reciprocal_polygon_is_absent():
    view, footprint, reference, evidence = fixture()
    assert local_seam_diagnostic(view, footprint, reference, 1, 1., (0,1), evidence) is None


def test_unrelated_ground_hole_still_refuses():
    view, footprint, reference, evidence = fixture()
    # Removing a supporting triangle leaves a large hole even after the
    # known reciprocal edge has been canonicalized.
    reference = (reference[0]+.5, reference[1], reference[2])
    result = local_seam_diagnostic(view, footprint, reference, 1, 1., (1,2,3), evidence)
    assert not result.candidate and result.reason == 'uncovered_ground_area'
