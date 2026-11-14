from dataclasses import replace

import pytest

from eql_automation.current_source_itinerary import plan_current_source_itinerary
from eql_automation.source_itinerary import SourceItineraryGuide, SourceWalkHint
from test_native_region_policy import setup


def fixture(tmp_path, zone='crushbone'):
    from eql_automation.source_zones import source_zone_id
    f=setup(tmp_path, zone=zone, native_zone=zone, zone_id=source_zone_id(zone));p=f.planner
    f.guide=SourceItineraryGuide(zone,p.pins[2],p.pins[3],'f'*64,
        f.options['bounds'].body_radius,6.,(4.,3.25),
        (SourceWalkHint((4.,2.),(4.,3.)),))
    return f


def run(f):
    return plan_current_source_itinerary(f.planner,f.reader,f.a,f.b,guide=f.guide,
        **{k:v for k,v in f.options.items() if k!='length'})


@pytest.mark.parametrize('zone', ('crushbone', 'butcher'))
def test_real_log_reader_pipeline_keeps_original_current_floor_and_exact_destination(tmp_path, zone):
    f=fixture(tmp_path, zone);result=run(f);data=result.itinerary.record()
    assert data['start']==[4.,2.] and data['goal']==[4.,3.25]
    assert result.initial.floor_chain.index==1
    assert data['initial_proof_sha256']==result.initial.floor_chain.previous.proof_sha256
    assert result.requires_fresh_start_pair and not result.source_execution_wired
    assert not result.input_authorized and not result.real_client_accepted


@pytest.mark.parametrize('change',('owner','log','zone','partial','body'))
def test_changed_session_and_body_do_not_produce_current_itinerary(tmp_path,change):
    f=fixture(tmp_path)
    if change=='body':f.guide=replace(f.guide,body_height=5.)
    else:
        query=f.planner.source.source_faces_for_footprint; calls=[]
        def changed(fp):
            result=query(fp);calls.append(1)
            if len(calls)>2:
                if change=='owner':f.owner=('other',)
                if change=='log':f.reader.tail.epoch+=1
                if change=='zone':f.reader.zone_generation+=1
                if change=='partial':f.reader.tail.partial=b'unfinished'
            return result
        f.planner.source.source_faces_for_footprint=changed
    with pytest.raises(ValueError):run(f)
