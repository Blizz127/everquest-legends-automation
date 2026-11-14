from tools.source_stair_topology import audit_stair_topology
from test_source_step import face, rectangle


def fixture(*, missing_riser=False, gap=0., overlap=False):
    sources = (*rectangle(-5., 0., 0., 0), *rectangle(gap, 2., 1., 2),
               *rectangle(2., 4., 2., 4), *rectangle(4., 9., 3., 6))
    for i, x in enumerate((0., 2., 4.)):
        if missing_riser and i == 1:
            continue
        sources += (face(((x,-5.,float(i)), (x,5.,float(i)), (x,5.,i+1.)), 20+2*i),
                    face(((x,-5.,float(i)), (x,5.,i+1.), (x,-5.,i+1.)), 21+2*i))
    groups = tuple(((1, 2*i), (1, 2*i+1)) for i in range(4))
    if overlap:
        sources += rectangle(0., 2., 1., 30)
        groups = (groups[0], (*groups[1], (1,30), (1,31)), *groups[2:])
    return sources, groups


def test_narrow_treads_keep_every_real_riser_without_claiming_body_clearance():
    result = audit_stair_topology(*fixture(), start=(-2.,0.), end=(6.,0.), radius=1.2)
    assert result['topology_candidate'] and len(result['risers']) == 3
    assert [t['height_exact'] for t in result['treads']] == ['0','1','2','3']
    assert not any(result[k] for k in ('full_body_clearance_checked', 'static_objects_checked',
        'bsp_regions_checked', 'executable_itinerary', 'floor_lineage_adopted',
        'client_step_capability_verified', 'input_authorized', 'real_client_accepted'))


def test_missing_riser_or_projected_gap_or_overlap_stays_refused():
    for options, reason in ((dict(missing_riser=True), 'complete_bounded_source_riser_not_found'),
            (dict(gap=.0000001), 'treads_do_not_exactly_partition_corridor'),
            (dict(overlap=True), 'treads_do_not_exactly_partition_corridor')):
        result = audit_stair_topology(*fixture(**options), start=(-2.,0.), end=(6.,0.), radius=1.2)
        assert not result['topology_candidate'] and result['reason'] == reason


def test_individual_rise_and_endpoint_support_remain_bounded():
    result = audit_stair_topology(*fixture(), start=(-2.,0.), end=(6.,0.), radius=1.2, max_rise=.5)
    assert not result['topology_candidate']
    result = audit_stair_topology(*fixture(), start=(-2.,0.), end=(5.1,0.), radius=1.2)
    assert result['reason'] == 'endpoint_not_wholly_supported_by_end_tread'


def test_reversed_run_keeps_lower_to_upper_riser_evidence():
    sources, groups = fixture()
    result = audit_stair_topology(sources, tuple(reversed(groups)),
                                start=(6.,0.), end=(-2.,0.), radius=1.2)
    assert result['topology_candidate'] and result['direction'] == 'down'
