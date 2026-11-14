from types import SimpleNamespace

import pytest

from eql_automation.bsp_clip import check_bsp_wedge
from eql_automation.bsp_volume import BspVolumeView
from eql_automation.client_bsp_probe import ClientBspTreeView, ENGINE_SHA256


def leaf(region):
    return (0., 0., 0., 0., region, 0, 0)


def view(nodes):
    return ClientBspTreeView(nodes, region_count=2, wld_sha256='a'*64)


def test_zero_and_signed_zero_take_positive_child_without_tolerance():
    tree = view(((1., 0., 0., 0., 0, 2, 3), leaf(1), leaf(2)))
    for x in (0., -0., 1e-7):
        result = tree.probe_tree(x, 0., 0.)
        assert result.region_id == 0 and result.node_path == (1, 2)
    assert tree.probe_tree(-1e-7, 0., 0.).region_id == 1


def test_missing_child_is_not_null_root_special_return_or_a_dry_region():
    missing = view(((1., 0., 0., 0., 0, 0, 2), leaf(1))).probe_tree(1., 0., 0.)
    assert missing.native_return == -1 and missing.region_id is None
    assert missing.reason == 'missing_child'
    empty = view(()).probe_tree(0., 0., 0.)
    assert empty.native_return == 1 and empty.region_id is None
    assert empty.reason == 'null_root_special_return'
    for result in (missing, empty):
        assert not any((result.bounds_checked, result.dry_verified,
                        result.collision_verified, result.real_client_accepted,
                        result.input_authorized))
        assert result.engine_sha256 == ENGINE_SHA256


def test_region_reference_precedes_children_even_if_child_would_cycle():
    tree = view(((1., 0., 0., 0., 2, 1, 1),))
    result = tree.probe_tree(-10., 0., 0.)
    assert result.native_return == 1 and result.region_id == 1
    assert result.plane_results == ()


def test_binary32_intermediate_roundings_differ_from_exact_plane_sum():
    tree = view(((1., 2.**25, -2.**25, 0., 0, 2, 3), leaf(1), leaf(2)))
    assert -1. + 2.**25 - 2.**25 < 0  # exact/double arithmetic chooses child 3
    result = tree.probe_tree(-1., 1., 1.)
    assert result.plane_results == (0.,) and result.region_id == 0
    assert 'live_MXCSR_unverified' in result.arithmetic


def test_model_refusals_do_not_invent_native_return_values():
    cycle = view(((1., 0., 0., 0., 0, 1, 0),))
    assert cycle.probe_tree(1., 0., 0.).reason == 'model_cycle_refusal'
    assert cycle.probe_tree(1., 0., 0.).native_return is None
    tree = view(((1., 0., 0., 0., 0, 2, 0), leaf(1)))
    assert tree.probe_tree(1., 0., 0., max_visits=1).reason == 'model_visit_budget'
    overflow = view(((3e38, 0., 0., 0., 0, 0, 0),)).probe_tree(3e38, 0., 0.)
    assert overflow.reason == 'unsupported_arithmetic' and overflow.native_return is None
    underflow = view(((1e-30, 0., 0., 0., 0, 0, 0),)).probe_tree(1e-30, 0., 0.)
    assert underflow.reason == 'unsupported_arithmetic'


@pytest.mark.parametrize('point', [(float('nan'), 0, 0), (1e40, 0, 0),
                                   (True, 0, 0), (1e-44, 0, 0)])
def test_unsupported_input_arithmetic_rejects(point):
    with pytest.raises(ValueError):
        view((leaf(1),)).probe_tree(*point)


def test_point_model_does_not_relax_closed_volume_or_use_a_height_tolerance():
    nodes = ((0., 0., 1., -.000006, 0, 2, 0), leaf(1))
    point = view(nodes).probe_tree(0., 0., 1.)
    assert point.region_id == 0 and not point.dry_verified
    volume = BspVolumeView(SimpleNamespace(nodes=nodes, labels_by_region={}),
                          region_count=2, wld_sha256='a'*64)
    box = ((-1., -1.), (1., -1.), (1., 1.), (-1., 1.))
    result = check_bsp_wedge(volume, box, (0, 0, 0), (0, 0, 3))
    assert not result.candidate and result.reason == 'missing_bsp_child'


@pytest.mark.parametrize('nodes', [((1., 0., 0., 0., 0, 2, 0),),
                                   (leaf(3),), ((float('inf'), 0., 0., 0., 0, 0, 0),)])
def test_malformed_copied_nodes_reject(nodes):
    with pytest.raises(ValueError):
        view(nodes)
