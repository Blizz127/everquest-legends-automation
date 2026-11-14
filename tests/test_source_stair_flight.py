from fractions import Fraction as F
import pytest

from eql_automation.native_region_policy import NativeZeroRegionTrialPolicy
from tools.source_stair_flight import audit_stair_flight, stair_body_extent, stair_body_footprint
from eql_automation.source_step import expanded
from eql_automation.source_detour import swept_square
from eql_automation.source_floor_chain import inside
from test_source_stair_topology import fixture
from test_source_step import face, rectangle
from test_bsp_volume import view as bsp_view, leaf
from test_client_classification import view as native_view


def run(*, sources=None, groups=None, static=(), descending=False, bsp=None, native=None, **options):
    original, ids = fixture()
    sources = original if sources is None else sources
    groups = ids if groups is None else groups
    bsp = bsp or bsp_view((leaf(1),))
    native = native or native_view((leaf(1),), wld_pin='a'*64)
    policy = NativeZeroRegionTrialPolicy('e'*64,'c'*64,'a'*64,'d'*64,
        bsp.inventory_sha256,native.inventory_sha256,native)
    start,end = ((6.,0.),(-2.,0.)) if descending else ((-2.,0.),(6.,0.))
    return audit_stair_flight(sources,static,tuple(reversed(groups)) if descending else groups,
        start=start,end=end,radius=1.2,body_height=6.,source_wld_sha256='a'*64,
        static_inventory_sha256='d'*64,bsp=bsp,region_policy=policy,**options)


@pytest.mark.parametrize('descending', [False, True])
def test_narrow_flight_checks_every_phase_without_adopting_intermediate_floor(descending):
    result = run(descending=descending)
    assert result['candidate'], result['reason']
    assert result['phase_count'] == 9
    assert all(p['terrain_static_clear'] and p['native']['complete'] for p in result['phases'])
    assert max(F(p['local_lift_exact']) for p in result['phases']) == F('17/8')
    assert all(not p['grounded_support_ids'] for p in result['phases'][1:-1])
    assert not any(result[k] for k in ('input_authorized','real_client_accepted',
        'executable_itinerary','floor_lineage_adopted','client_step_capability_verified'))


def test_low_ceiling_and_static_side_wall_cannot_be_exempted_as_stair_geometry():
    source, groups = fixture()
    ceiling = rectangle(-5.,9.,6.1,100)
    result = run(sources=(*source,*ceiling),groups=groups)
    assert not result['candidate'] and result['reason'] == 'source_intersects_stair_phase_body'
    wall = face(((1.,-5.,0.),(1.,5.,0.),(1.,0.,10.)),200,fragment=99)
    result = run(static=(wall,))
    assert not result['candidate'] and result['phases'][-1]['obstruction']['static']


def test_local_lift_bound_applies_to_lowest_support_under_whole_footprint():
    result = run(max_lift=2.)
    assert result['reason'] == 'phase_local_lift_bound_exceeded'
    assert F(result['phases'][-1]['local_lift_exact']) == F('17/8')


def test_missing_riser_and_hole_do_not_gain_motion_from_body_clearance():
    for options in (dict(missing_riser=True),dict(gap=.0000001)):
        source,groups=fixture(**options)
        assert not run(sources=source,groups=groups)['candidate']


def test_bsp_hazard_and_nonzero_native_metadata_refuse_complete_volume():
    result=run(bsp=bsp_view((leaf(1),),{0:{'water'}}))
    assert result['reason'] == 'stair_phase_bsp_labelled_bsp_volume'
    result=run(native=native_view((leaf(2),),water_id=1,wld_pin='a'*64))
    assert result['reason'] == 'stair_phase_nonzero_or_unresolved_native_regions'


def test_horizontal_bound_and_cancellation_stop_without_partial_candidate():
    assert run(max_transfer_distance=1.)['reason'] == 'phase_horizontal_transfer_bound_exceeded'
    def stop():
        raise TimeoutError('cancelled')
    with pytest.raises(TimeoutError,match='cancelled'):
        run(check_context=stop)


def test_exact_query_corridor_contains_float_caps_and_all_intermediate_squares():
    start,end,radius = (-1.,21.698),(2.851,52.27075),1.2
    extent=stair_body_extent(start,end,radius)
    corridor=stair_body_footprint(start,end,radius)
    for point in (start,end):
        assert all(inside(p,corridor) for p in expanded(swept_square(point,point,radius)))
    for t in (F(1,7),F(3,7),F(6,7)):
        center=tuple(F(start[k])+t*(F(end[k])-F(start[k])) for k in (0,1))
        assert all(inside((center[0]+dx,center[1]+dy),corridor)
                   for dx in (-extent,extent) for dy in (-extent,extent))
