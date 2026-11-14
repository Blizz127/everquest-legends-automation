from fractions import Fraction as F

import pytest

from eql_automation.bsp_clip import check_bsp_wedge
from test_bsp_volume import SQUARE,leaf,view,water_pocket


def check(tree, *, low=(0,0,0), high=(0,0,3), **bounds):
    return check_bsp_wedge(tree,SQUARE,low,high,**bounds)


def test_ancestor_clipping_eliminates_only_unreachable_missing_branch():
    # The second split's missing x<-.5 branch cannot occur under root x>=0.
    tree = view(((1.,0.,0.,0.,0,2,3),(-1.,0.,0.,-.5,0,0,3),leaf(1)))
    assert tree.check_prism(SQUARE,(0.,3.)).reason=='missing_bsp_child'
    result = check(tree)
    assert result.candidate and result.region_ids==(0,)
    assert result.exact_closed_clipping and not result.conservative_unclipped_traversal
    assert not result.input_authorized and not result.real_client_accepted


def test_clipping_finds_water_inside_volume_without_corner_or_center_sample():
    nodes,labels = water_pocket()
    result = check(view(nodes,labels))
    assert not result.candidate and result.labelled_regions==((0,('water',)),)
    assert result.refused_node==7 and result.refused_vertices_exact
    for x,y,z in result.refused_vertices_exact:
        assert -F(.2)<=F(x)<=F(.2) and F(.2)<=F(y)<=F(.4) and 1<=F(z)<=2


@pytest.mark.parametrize('label',('water','lava','unknown','zoneline','slippery'))
def test_hazard_labels_are_never_removed_by_clipping(label):
    result = check(view(((1.,0.,0.,-.9,0,2,3),leaf(1),leaf(2)),{0:{label}}))
    assert not result.candidate and result.reason=='labelled_bsp_volume'


@pytest.mark.parametrize('offset',(0.,.000006))
def test_real_thin_unknown_layer_and_exact_floor_contact_still_refuse(offset):
    result = check(view(((0.,0.,1.,-offset,0,2,0),leaf(1))))
    assert result.reason=='missing_bsp_child'
    assert max(F(p[2]) for p in result.refused_vertices_exact)==F(offset)
    assert min(F(p[2]) for p in result.refused_vertices_exact)==0


def test_degenerate_point_contact_survives_successive_clips():
    # Reach x=0, then y=0, then z=0. The resulting point is labelled water.
    nodes = ((1.,0.,0.,0.,0,2,8),(-1.,0.,0.,0.,0,3,8),
             (0.,1.,0.,0.,0,4,8),(0.,-1.,0.,0.,0,5,8),
             (0.,0.,1.,0.,0,6,8),(0.,0.,-1.,0.,0,7,8),leaf(1),leaf(2))
    result = check(view(nodes,{0:{'water'}}))
    assert result.reason=='labelled_bsp_volume'
    assert result.refused_vertices_exact==( ('0','0','0'), )


def test_sloped_source_wedge_preserves_exact_support_without_bbox_underfill():
    tree = view(((-1.,0.,1.,.000015,0,2,0),leaf(1)))
    assert check(tree,low=(1,0,0),high=(1,0,6)).candidate
    assert check(tree,low=(1,0,-.01),high=(1,0,6)).reason=='missing_bsp_child'


def test_exact_coordinates_cannot_round_away_a_hazard():
    huge = 2**54
    xy = ((F(huge),F(-1)),(F(huge)+F(1,4),F(-1)),
          (F(huge)+F(1,4),F(-3,4)),(F(huge),F(-3,4)))
    tree = view(((1.,1.,1.,-float(huge),0,2,3),leaf(1),leaf(2)),{1:{'water'}})
    result = check_bsp_wedge(tree,xy,(0,0,F(1,10)),(0,0,F(1,5)))
    assert result.labelled_regions==((1,('water',)),)


def test_dag_cycle_and_resource_limits_are_not_silently_accepted():
    shared = view(((1.,0.,0.,0.,0,2,2),leaf(1)))
    assert check(shared).candidate
    assert check(shared,max_visits=1).reason=='bsp_volume_visit_budget_exceeded'
    assert check(shared,max_depth=1).reason=='bsp_volume_depth_budget_exceeded'
    assert check(shared,max_vertices=4).reason=='bsp_clipped_geometry_budget_exceeded'
    assert check(view(((1.,0.,0.,0.,0,1,2),leaf(1)))).reason=='bsp_volume_cycle'
    assert check(view((leaf(0),))).reason=='bsp_leaf_has_no_region'


@pytest.mark.parametrize('low,high',(((0,0,1),(0,0,1)),((2,0,0),(0,0,1)),
                                     ((0,0,float('nan')),(0,0,1))))
def test_invalid_wedge_does_not_create_a_traversal(low,high):
    with pytest.raises(ValueError):check(view((leaf(1),)),low=low,high=high)
