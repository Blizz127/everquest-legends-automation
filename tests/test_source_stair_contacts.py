from dataclasses import replace
from fractions import Fraction as F

import pytest

from eql_automation.source_stair_contacts import audit_stair_contacts
from eql_automation.source_stair_plan import plan_stair_flight
from test_source_stair_plan import setup
from test_source_step import face,rectangle


def run(*,descending=False,sources=None,static_sources=(),**options):
    prefix,start,end,groups,terrain,static,bsp,policy=setup(descending=descending)
    return audit_stair_contacts(terrain.sources if sources is None else sources,static_sources,groups,
        start=start,end=end,radius=1.4,body_radius=1.2,body_height=6.,
        source_wld_sha256=terrain.wld_sha256,static_inventory_sha256=static.inventory_sha256,
        bsp=bsp,region_policy=policy,**options)


@pytest.mark.parametrize('descending',[False,True])
def test_grounded_treads_and_overlapping_step_intervals_remain_explicit(descending):
    record=run(descending=descending)
    assert record['candidate'],record['reason']
    assert len(record['states'])==7
    assert len([s for s in record['states'] if s['kind']=='ground'])==4
    assert len([s for s in record['states'] if s['kind']=='transition'])==3
    assert all(p['terrain_static_clear'] and p['native']['complete'] for p in record['phases'])
    assert all(F(p['base_interval_exact'][1])-F(p['base_interval_exact'][0])<=4 for p in record['phases'])
    assert any(p['base_interval_exact']==['0','2'] for p in record['phases'])
    assert not any(record[k] for k in ('contact_semantics_verified','client_step_capability_verified',
        'real_client_accepted','input_authorized','executable_itinerary','floor_lineage_adopted'))


def test_full_contact_plan_links_only_planned_final_landing():
    args=setup();prefix=args[0];old=prefix.previous
    plan,branch=plan_stair_flight(*args,radius=1.4,body_radius=1.2,
        vertical_model='bounded_source_contacts',check_context=lambda:None)
    record=plan.record()
    assert record['vertical_model']=='bounded_source_contacts'
    assert record['flight']['candidate']
    assert len(record['complete_phase_queries'])==record['flight']['phase_count']
    assert prefix.previous is old and branch.previous.previous_sha256==old.proof_sha256
    assert branch.previous.reason=='conditional_stair_contact_landing_only'
    assert not record['input_authorized'] and not record['executable_itinerary']


def test_riser_id_does_not_exempt_a_wall_extending_above_its_adjacent_tread():
    sources=setup()[4].sources
    changed=tuple(replace(s,vertices_wld=tuple((x,y,4. if z==1. else z) for x,y,z in s.vertices_wld))
                  if s.face in (20,21) else s for s in sources)
    result=run(sources=changed)
    assert result['topology']['topology_candidate']
    assert not result['candidate'] and result['reason']=='noncontact_source_intersects_stair_body'
    assert result['phases'][-1]['obstruction']['source_id'] in ((1,20),(1,21))


@pytest.mark.parametrize('kind',['ceiling','vertical_static','flagged_riser','unlisted_wall'])
def test_other_geometry_never_inherits_tread_or_riser_contact_exception(kind):
    sources=setup()[4].sources;static=()
    if kind=='ceiling':sources=(*sources,*rectangle(-5.,9.,6.1,100))
    elif kind=='vertical_static':static=(face(((1.,-5.,0.),(1.,5.,0.),(1.,0.,10.)),200,99),)
    elif kind=='flagged_riser':sources=tuple(replace(s,flag=4) if s.face==20 else s for s in sources)
    else:sources=(*sources,face(((1.,-5.,0.),(1.,5.,0.),(1.,0.,10.)),200))
    result=run(sources=sources,static_sources=static)
    assert not result['candidate'] and result['reason']=='noncontact_source_intersects_stair_body'


def test_span_and_center_error_cannot_be_shrunk_to_make_geometry_pass():
    result=run(max_lift=1.)
    assert not result['candidate'] and result['reason']=='contact_cell_vertical_span_exceeded'
    args=setup()
    result=audit_stair_contacts(args[4].sources,(),args[3],start=args[1],end=args[2],
        radius=1.2,body_radius=1.2,body_height=6.,source_wld_sha256=args[4].wld_sha256,
        static_inventory_sha256=args[5].inventory_sha256,bsp=args[6],region_policy=args[7])
    assert not result['candidate'] and result['reason']=='checked_radius_leaves_no_center_corridor'


def test_context_stop_is_propagated():
    def stop():raise RuntimeError('F9')
    with pytest.raises(RuntimeError,match='F9'):run(check_context=stop)
