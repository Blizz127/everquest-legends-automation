from dataclasses import replace
from fractions import Fraction as F
from hashlib import sha256

import pytest

from eql_automation.native_region_policy import encoded
from eql_automation.route_geometry import RouteMotionBounds
from eql_automation.source_stair_coverage import SourceStairContactIndex,covers_closed


def test_degenerate_covering_shapes_are_bounded_not_half_plane_intersections():
    origin=(F(0),F(0));one=(F(1),F(0));two=(F(2),F(0))
    assert covers_closed((origin,),((origin,),))
    assert not covers_closed((one,),((origin,),))
    assert covers_closed((one,),((origin,two),))
    assert not covers_closed(((F(3),F(0)),),((origin,two),))
    assert not covers_closed(((F(-1),F(0)),),((origin,two),))
    assert covers_closed((origin,two),((origin,one),(one,two)))
    assert not covers_closed((origin,two),((origin,one),(two,)))
    assert not covers_closed((origin,two),(((F(1),F(-1)),(F(1),F(1))),))
from eql_automation.source_stair_plan import SourceStairPlan,plan_stair_flight
from test_source_stair_plan import setup


BOUNDS=RouteMotionBounds('stair','motion',.01,.02,.05,2.,.01,.01,2.,.01,1.2,6.)


@pytest.fixture
def index():
    plan,_=plan_stair_flight(*setup(),radius=1.4,body_radius=1.2,
        vertical_model='bounded_source_contacts',check_context=lambda:None)
    return SourceStairContactIndex(plan)


@pytest.mark.parametrize('point,height',[((-2.,0.),0.),((-.1,0.),1.),((0.,0.),1.),
                                       ((1.,0.),1.),((2.,0.),2.),((3.,0.),2.),((5.9,0.),3.)])
def test_complete_forward_pulse_covers_grounded_and_ambiguous_stair_positions(index,point,height):
    proof=index.cover_pulse(point,90.,'forward',BOUNDS,height_interval=(height-.1,height+.1)).record()
    assert proof['full_motion_coverage_checked'] and proof['conditional_contact_semantics']
    assert proof['motion_bounds']['maximum_actual_hold']==.05
    assert proof['coupled_enclosures'] and proof['reachable_by_start']
    assert not proof['input_authorized'] and not proof['real_client_accepted']
    assert not proof['client_step_capability_verified'] and not proof['source_execution_wired']


def test_multiple_adjacent_step_states_are_retained_instead_of_waiting_for_unique_support(index):
    proof=index.cover_pulse((1.,0.),90.,'forward',BOUNDS,height_interval=(.9,1.1)).record()
    assert {c['state'] for c in proof['compatible']}=={1,4,5}
    assert {r['state'] for r in proof['reachable_by_start']}=={1,4,5}
    assert all(set(r['reachable'])=={1,4,5} for r in proof['reachable_by_start'])


def test_overlapping_transitions_do_not_require_center_on_the_middle_tread():
    args=list(setup());terrain=args[4]
    def narrowed(x):return {2.:.5,4.:1.}.get(x,x)
    terrain.sources=tuple(replace(s,vertices_wld=tuple((y,narrowed(x),z) for y,x,z in s.vertices_wld))
                          for s in terrain.sources)
    terrain.source_faces_for_footprint=lambda _:terrain.sources
    plan,_=plan_stair_flight(*args,radius=1.4,body_radius=1.2,
        vertical_model='bounded_source_contacts',check_context=lambda:None)
    idx=SourceStairContactIndex(plan)
    proof=idx.cover_pulse((-.6,0.),90.,'forward',BOUNDS,height_interval=(.4,.6)).record()
    assert [r['state'] for r in proof['reachable_by_start']]==[4]
    assert 5 in proof['reachable_by_start'][0]['reachable']
    assert 1 not in proof['reachable_by_start'][0]['reachable']


@pytest.mark.parametrize('kind',['left','right'])
def test_pivots_include_declared_displacement(index,kind):
    assert index.cover_pulse((1.,0.),90.,kind,BOUNDS,height_interval=(.9,1.1)).record()['full_motion_coverage_checked']
    with pytest.raises(ValueError,match='center motion leaves'):
        index.cover_pulse((1.,0.),90.,kind,replace(BOUNDS,pivot_displacement_upper_bound=.3),
            height_interval=(.9,1.1))


def test_wrong_height_lateral_escape_and_full_hold_overshoot_are_refused(index):
    with pytest.raises(ValueError,match='No compatible'):
        index.cover_pulse((1.,0.),90.,'forward',BOUNDS,height_interval=(8.,9.))
    with pytest.raises(ValueError,match='center motion leaves'):
        index.cover_pulse((1.,.15),0.,'forward',BOUNDS,height_interval=(.9,1.1))
    with pytest.raises(ValueError,match='center motion leaves'):
        index.cover_pulse((5.9,0.),90.,'forward',replace(BOUNDS,forward_speed_upper_bound=20.),
            height_interval=(2.9,3.1))


def test_lift_cache_cannot_be_relabelled_as_grounded_movement():
    plan,_=plan_stair_flight(*setup(),radius=1.4,check_context=lambda:None)
    with pytest.raises(ValueError,match='distinct bounded contact model'):SourceStairContactIndex(plan)


def test_xy_coverage_does_not_substitute_for_coupled_height_region_coverage(index):
    record=index.plan.record()
    # Deliberately invalid geometry fixture: its XY shapes still cover the
    # pulse, but none of its native-region bands includes grounded base Z=1.
    for cell in record['flight']['phases']:cell['region_band_exact'][0]='5'
    payload=encoded(record)
    altered=SourceStairContactIndex(SourceStairPlan(payload,sha256(payload).hexdigest()))
    with pytest.raises(ValueError,match='coupled stair'):
        altered.cover_pulse((1.,0.),90.,'forward',BOUNDS,height_interval=(.9,1.1))


def test_mutated_cached_cell_is_not_accepted(index):
    object.__setattr__(index.cells[0],'height',(F(-100),F(100)))
    with pytest.raises(ValueError,match='index changed'):
        index.cover_pulse((-2.,0.),90.,'forward',BOUNDS,height_interval=(-.1,.1))


def test_closed_coverage_preserves_zero_area_wall_contacts_and_gaps():
    rect=lambda x0,x1:((F(x0),F(-1)),(F(x1),F(-1)),(F(x1),F(1)),(F(x0),F(1)))
    segment=((F(0),F(0)),(F(2),F(0)))
    assert covers_closed(segment,(rect(0,1),rect(1,2)))
    assert not covers_closed(segment,(rect(0,1),rect(F(10000001,10000000),2)))
    assert covers_closed(((F(1),F(0)),),(rect(0,1),))
    assert not covers_closed(((F(2),F(0)),),(rect(0,1),))
