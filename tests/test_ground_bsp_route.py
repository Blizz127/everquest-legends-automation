import pytest

from eql_automation.bsp_probe import BspSegmentSpan
from eql_automation.ground_bsp_route import audit_ground_bsp_route


class FlatMesh:
    def __init__(self):
        ring = ((0.0, 0.0, 2.0), (10.0, 0.0, 2.0),
                (10.0, 10.0, 2.0), (0.0, 10.0, 2.0))
        self.area = (63,)
        self.polys = (ring,)
        self._detail = ((ring[0], ring[1], ring[2]),
                        (ring[0], ring[2], ring[3]))
        self._detail_start = (0, 2)


class Lookup:
    def __init__(self, labels=(), region_id=1):
        self.labels = labels
        self.region_id = region_id
        self.calls = []

    def trace_segment(self, start, end):
        self.calls.append((start, end))
        return (BspSegmentSpan(0.0, 1.0, self.region_id,
                               self.labels, "sample"),)


POINTS = ((1.0, 5.0), (9.0, 5.0))


def test_clean_copied_bsp_is_only_an_offline_candidate():
    lookup = Lookup()
    result = audit_ground_bsp_route(FlatMesh(), lookup, (0,), POINTS)

    assert result.candidate and result.reason == "copied_static_bsp_candidate_only"
    assert result.bsp_spans == 2 and len(lookup.calls) == 2
    assert lookup.calls[0][0][2] == 2.0 and lookup.calls[1][0][2] == 3.0
    assert result.route_accepted is False and result.real_client_accepted is False


@pytest.mark.parametrize("labels,region,reason", [
    (("water",), 1, "labelled_bsp_interval"),
    ((), None, "unknown_bsp_interval"),
])
def test_label_or_unknown_interval_rejects_candidate(labels, region, reason):
    result = audit_ground_bsp_route(FlatMesh(), Lookup(labels, region),
                                    (0,), POINTS)
    assert not result.candidate and result.reason == reason
    assert not result.route_accepted


def test_missing_detail_height_and_non_ground_are_not_passes():
    mesh = FlatMesh()
    missing = audit_ground_bsp_route(mesh, Lookup(), (0,),
                                     ((1.0, 5.0), (30.0, 5.0)))
    assert not missing.candidate
    mesh.area = (5,)
    non_ground = audit_ground_bsp_route(mesh, Lookup(), (0,), POINTS)
    assert not non_ground.candidate


def test_bounded_inputs_and_span_budget():
    with pytest.raises(ValueError):
        audit_ground_bsp_route(FlatMesh(), Lookup(), (0,), ((1.0, 5.0),))
    with pytest.raises(ValueError):
        audit_ground_bsp_route(FlatMesh(), Lookup(), (0,),
                               ((1.0, 5.0), (float("nan"), 5.0)))
    limited = audit_ground_bsp_route(FlatMesh(), Lookup(), (0,), POINTS,
                                     max_total_spans=1)
    assert not limited.candidate and limited.reason == "bsp_span_budget_exceeded"
    with pytest.raises(ValueError):
        audit_ground_bsp_route(FlatMesh(), Lookup(), (0,),
                               ((1.0, 5.0), (1.0, 5.0)))


def test_missing_or_gapped_bsp_partition_fails_closed():
    class EmptyLookup:
        def trace_segment(self, start, end):
            return ()

    class GapLookup:
        def trace_segment(self, start, end):
            return (BspSegmentSpan(0.0, 0.4, 1, (), "sample"),
                    BspSegmentSpan(0.5, 1.0, 1, (), "sample"))

    for lookup in (EmptyLookup(), GapLookup()):
        result = audit_ground_bsp_route(FlatMesh(), lookup, (0,), POINTS)
        assert not result.candidate and result.reason == "unknown_bsp_interval"
        assert result.unknown[0]["reason"] == "invalid_bsp_partition"
