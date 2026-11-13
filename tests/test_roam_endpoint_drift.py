import pytest

from tools.inspect_copied_roam_ring import endpoint_drifts, endpoints_match_ring


def test_same_xy_on_another_floor_is_not_a_local_roam_candidate():
    start = (1.0, 2.0, 3.0)
    goal = (11.0, 2.0, 3.0)
    good = endpoint_drifts((start, goal), start, goal)
    wrong_floor = endpoint_drifts((start, (11.0, 2.0, 10.0)), start, goal)
    assert endpoints_match_ring(good)
    assert wrong_floor["goal_xy_drift"] == 0.0
    assert wrong_floor["goal_z_drift"] == 7.0
    assert not endpoints_match_ring(wrong_floor)


def test_invalid_endpoint_fails_closed():
    with pytest.raises(ValueError, match="finite XYZ"):
        endpoint_drifts(((1.0, 2.0, 3.0), (float("nan"), 2.0, 3.0)),
                        (1.0, 2.0, 3.0), (2.0, 2.0, 3.0))
