from dataclasses import replace

import pytest

from eql_automation.current_source_itinerary import plan_current_source_itinerary
from eql_automation.source_section_manifest import parse_walking_sections
from eql_automation.source_walk_sections import plan_walk_sections
from eql_automation.source_itinerary import SourceWalkHint
from test_current_source_itinerary import fixture,run


@pytest.mark.parametrize('later',(False,True))
def test_section_rejoin_retains_the_one_actual_start_floor_and_full_destination(tmp_path,monkeypatch,later):
    f=fixture(tmp_path)
    f.guide=replace(f.guide,goal=(4.,3.75),operations=(SourceWalkHint((4.,2.),(4.,3.)),SourceWalkHint((4.,3.),(4.,3.75))))
    initial=run(f).initial
    bounds=replace(f.options['bounds'],maximum_requested_hold=.15,maximum_actual_hold=.2,
        forward_speed_upper_bound=.2,pivot_displacement_upper_bound=.001,post_release_drift=.001)
    record=plan_walk_sections(initial.floor_chain,f.guide,f.planner,bounds=bounds,
        maximum_length=1.1,minimum_length=.5,candidate_spacing=.1,check_context=lambda:None)
    sections=parse_walking_sections(f.guide,record)
    if later:
        for field in ('a','b'):
            f.now+=.5;f.append('Your Location is 2.7, 4.0, 2.7')
            setattr(f,field,f.reader.poll(now=f.now)[0])
        f.options['released_at']=f.a.received_monotonic-.2
    captured=[];original=f.planner.plan
    def capture(*a,**kw):
        value=original(*a,**kw);captured.append(value);return value
    monkeypatch.setattr(f.planner,'plan',capture)
    result=plan_current_source_itinerary(f.planner,f.reader,f.a,f.b,guide=f.guide,sections=sections,
        **{k:v for k,v in f.options.items() if k!='length'})
    assert captured==[result.initial]
    assert result.section_index==(1 if later else 0)
    assert result.full_itinerary.record()['goal']==[4.,3.75]
    assert result.itinerary.record()['goal']==list(sections.guides[result.section_index].goal)
    assert result.itinerary.record()['initial_proof_sha256']==result.initial.floor_chain.previous.proof_sha256
    assert result.itinerary.record()['initial_chain_index']==result.initial.floor_chain.index==1
    assert result.sections is sections and not result.input_authorized
