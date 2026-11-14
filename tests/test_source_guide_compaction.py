from dataclasses import replace
import math

import pytest

from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_guide_compaction import compact_source_guide
from eql_automation.source_itinerary import SourceWalkHint,SourceStepHint,plan_source_itinerary
from test_source_itinerary import fixture


def guide_for(points):
    guide=fixture()[1]
    return replace(guide,goal=points[-1],operations=tuple(SourceWalkHint(a,b) for a,b in zip(points,points[1:])))


def test_straight_hints_compact_preserving_exact_endpoints_and_cell_bound():
    points=tuple((float(x),0.) for x in range(21));original=guide_for(points)
    result=compact_source_guide(original)
    assert len(result.operations)==3
    assert result.operations[0].start==points[0] and result.operations[-1].end==points[-1]
    assert all(math.dist(op.start,op.end)<=8 for op in result.operations)
    assert len(original.operations)==20 and result.provenance_sha256!=original.provenance_sha256


def test_corners_and_backtracking_remain_explicit():
    points=((0.,0.),(1.,0.),(2.,0.),(2.,2.),(1.,2.),(0.,2.),(1.,2.))
    result=compact_source_guide(guide_for(points))
    assert [(op.start,op.end) for op in result.operations]==[
        ((0.,0.),(2.,0.)),((2.,0.),(2.,2.)),((2.,2.),(0.,2.)),((0.,2.),(1.,2.))]


def test_steps_survive_and_full_checker_rebuilds_from_unchanged_current_floor():
    prefix,guide,*assets=fixture();before=_chain_snapshot(prefix)
    original_steps=[op for op in guide.operations if type(op) is SourceStepHint]
    result=compact_source_guide(guide)
    assert [op for op in result.operations if type(op) is SourceStepHint]==original_steps
    plan=plan_source_itinerary(prefix,(-2.,0.),result,*assets,check_context=lambda:None).record()
    assert plan['goal']==list(guide.goal) and not plan['input_authorized']
    assert _chain_snapshot(prefix)==before


def test_stationary_hints_removed_without_losing_entire_stationary_guide():
    result=compact_source_guide(guide_for(((1.,1.),)*5))
    assert result.operations==(SourceWalkHint((1.,1.),(1.,1.)),)
    moving=compact_source_guide(guide_for(((0.,0.),(0.,0.),(1.,0.),(1.,0.),(2.,0.))))
    assert moving.operations==(SourceWalkHint((0.,0.),(2.,0.)),)


def test_long_existing_hint_is_split_with_exact_fractional_endpoint():
    start=(-4030.3333333333335,0.);end=(start[0]+74.,0.)
    result=compact_source_guide(guide_for((start,end)))
    assert result.operations[-1].end==end
    assert all(math.dist(op.start,op.end)<=8.000000001 for op in result.operations)


def test_rounding_gaps_are_not_silently_removed():
    guide=guide_for(((0.,0.),(1.,0.),(2.,0.)))
    guide=replace(guide,operations=(guide.operations[0],SourceWalkHint((1.+1e-8,0.),(2.,0.))))
    with pytest.raises(ValueError,match='contiguous'):compact_source_guide(guide)


def test_tiny_rounding_is_explicit_and_strict_option_preserves_shallow_turns():
    guide=guide_for(((0.,0.),(1.,1e-9),(2.,0.)))
    assert len(compact_source_guide(guide,tolerance=0.).operations)==2
    assert len(compact_source_guide(guide,tolerance=1e-8).operations)==1
    assert len(compact_source_guide(guide,tolerance=1e-10).operations)==2


def test_intermediate_rounding_cannot_accumulate_beyond_bound():
    points=((0.,0.),(1.,.8e-8),(2.,0.),(3.,-.8e-8))
    result=compact_source_guide(guide_for(points),tolerance=1e-8)
    assert len(result.operations)==2
