from fractions import Fraction
from types import SimpleNamespace

import pytest

from eql_automation.bsp_probe import BspPointLookup
from eql_automation.bsp_volume import BspVolumeView


SQUARE = ((-1., -1.), (1., -1.), (1., 1.), (-1., 1.))


def leaf(region): return (0., 0., 0., 0., region, 0, 0)


def view(nodes, labels=None, regions=2):
    return BspVolumeView(SimpleNamespace(nodes=nodes, labels_by_region=labels or {}),
                         region_count=regions, wld_sha256='a'*64)


def water_pocket():
    # Small interior box: -.2<x<.2, .2<y<.4, 1<z<2. All outside leaves share dry region 2.
    nodes = ((1., 0., 0., .2, 0, 2, 8), (-1., 0., 0., .2, 0, 3, 8),
             (0., 1., 0., -.2, 0, 4, 8), (0., -1., 0., .4, 0, 5, 8),
             (0., 0., 1., -1., 0, 6, 8), (0., 0., -1., 2., 0, 7, 8),
             leaf(1), leaf(2))
    return nodes, {0: {'water'}}


def test_complete_volume_detects_interior_water_missed_by_corners_and_centerline():
    nodes, labels = water_pocket()
    sampled = BspPointLookup.__new__(BspPointLookup)
    sampled.nodes = nodes; sampled.labels_by_region = labels
    assert all(not sampled.probe(x, y, z).labels for x, y in SQUARE for z in (0., 3.))
    assert all(not span.labels for span in sampled.trace_segment((-1., 0., 1.5), (1., 0., 1.5)))
    result = view(nodes, labels).check_prism(SQUARE, (0., 3.))
    assert not result.candidate and result.labelled_regions == ((0, ('water',)),)
    assert result.conservative_unclipped_traversal and not result.input_authorized


@pytest.mark.parametrize('label', ('water', 'lava', 'unknown', 'zoneline', 'slippery'))
def test_every_label_refuses_including_lateral_sliver(label):
    result = view(((1., 0., 0., -.9, 0, 2, 3), leaf(1), leaf(2)),
                  {0: {label}}).check_prism(SQUARE, (0., 8.))
    assert not result.candidate and result.reason == 'labelled_bsp_volume'


def test_upper_body_and_exact_plane_contact_visit_both_children():
    tree = view(((0., 0., 1., -7., 0, 2, 3), leaf(1), leaf(2)), {0: {'water'}})
    assert tree.check_prism(SQUARE, (0., 6.)).candidate
    assert not tree.check_prism(SQUARE, (0., 7.)).candidate
    assert not tree.check_prism(SQUARE, (0., 8.)).candidate


def test_exact_plane_arithmetic_does_not_lose_small_negative_offset():
    huge = 2**54
    xy = ((Fraction(huge), Fraction(-1)), (Fraction(huge)+Fraction(1,4), Fraction(-1)),
          (Fraction(huge)+Fraction(1,4), Fraction(-3,4)), (Fraction(huge), Fraction(-3,4)))
    # Rounding XY to floats would erase the negative planar contribution.
    assert (float(huge) - 1. - float(huge)) + .1 > 0
    result = view(((1., 1., 1., -float(huge), 0, 2, 3), leaf(1), leaf(2)),
                  {1: {'water'}}).check_prism(xy, (Fraction(1,10), Fraction(1,5)))
    assert not result.candidate and result.labelled_regions == ((1, ('water',)),)


@pytest.mark.parametrize('nodes,reason', [
    (((1., 0., 0., 0., 0, 0, 2), leaf(1)), 'missing_bsp_child'),
    ((leaf(0),), 'bsp_leaf_has_no_region'),
    (((1., 0., 0., 0., 0, 1, 2), leaf(1)), 'bsp_volume_cycle'),
])
def test_missing_data_and_cycle_refuse(nodes, reason):
    result = view(nodes).check_prism(SQUARE, (0., 1.))
    assert not result.candidate and result.reason == reason


def test_dag_shared_leaf_is_not_a_cycle_and_budgets_are_enforced():
    tree = view(((1., 0., 0., 0., 0, 2, 2), leaf(1)))
    assert tree.check_prism(SQUARE, (0., 1.)).candidate
    assert tree.check_prism(SQUARE, (0., 1.), max_visits=1).reason == 'bsp_volume_visit_budget_exceeded'
    assert tree.check_prism(SQUARE, (0., 1.), max_depth=1).reason == 'bsp_volume_depth_budget_exceeded'


@pytest.mark.parametrize('nodes', [((float('nan'), 0., 0., 0., 0, 1, 1),),
                                  ((1., 0., 0., 0., 0, 2, 0),), (leaf(3),)])
def test_malformed_inventories_refuse_before_query(nodes):
    with pytest.raises(ValueError): view(nodes)


def test_lookup_mutation_cannot_remove_a_snapshotted_label():
    lookup = SimpleNamespace(nodes=[leaf(1)], labels_by_region={0: {'water'}})
    tree = BspVolumeView(lookup, region_count=1, wld_sha256='a'*64)
    lookup.labels_by_region.clear(); lookup.nodes[0] = leaf(0)
    assert tree.check_prism(SQUARE, (0., 1.)).labelled_regions == ((0, ('water',)),)


@pytest.mark.parametrize('xy,z', [(SQUARE, (1., 1.)), (SQUARE, (0., float('inf'))),
                                (((0., 0.), (1., 0.), (2., 0.)), (0., 1.))])
def test_invalid_prism_refuses(xy, z):
    with pytest.raises(ValueError): view((leaf(1),)).check_prism(xy, z)


def test_sloped_body_wedge_does_not_invent_space_below_its_floor():
    # The supported floor is z=x. Below it is an actually missing BSP child.
    tree=view(((-1.,0.,1.,.001,0,2,0),leaf(1)))
    vertices=tuple((x,y,x+z) for x,y in SQUARE for z in (0.,6.))
    assert tree.check_prism(SQUARE,(-1.,7.)).reason=='missing_bsp_child'
    assert tree.check_convex_volume(vertices).candidate
    bad=tuple((x,y,z-.01) for x,y,z in vertices)
    assert tree.check_convex_volume(bad).reason=='missing_bsp_child'


def test_convex_volume_still_detects_small_interior_water_and_contacts():
    nodes,labels=water_pocket()
    vertices=tuple((x,y,z) for x,y in SQUARE for z in (0.,3.))
    assert not view(nodes,labels).check_convex_volume(vertices).candidate
    tree=view(((0.,0.,1.,-3.,0,2,3),leaf(1),leaf(2)),{0:{'water'}})
    assert not tree.check_convex_volume(vertices).candidate


@pytest.mark.parametrize('vertices',[(),((0.,0.,0.),)*4,
    ((0.,0.,0.),(1.,0.,0.),(0.,1.,0.),(1.,1.,0.)),
    ((0.,0.,0.),(1.,0.,0.),(0.,1.,0.),(0.,0.,float('nan')))])
def test_convex_body_requires_nonzero_finite_volume(vertices):
    with pytest.raises(ValueError):view((leaf(1),)).check_convex_volume(vertices)
