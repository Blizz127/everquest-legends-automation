from copy import deepcopy
from dataclasses import replace

import pytest

from eql_automation.source_section_manifest import parse_walking_sections
from test_source_walk_sections import context,plan


def test_partition_selects_the_section_after_a_checked_current_start_join():
    prefix,guide,planner,bounds=context()
    record=plan(prefix,guide,planner,bounds)
    result=parse_walking_sections(guide,record)
    assert [result.section_for_entry(i) for i in (0,9,10,20,39)]==[0,0,1,2,3]
    assert result.guides[-1].goal==guide.goal
    record['sections'].clear()  # Mutable JSON input cannot change the parsed guides.
    result.check()
    with pytest.raises(ValueError):result.section_for_entry(40)


@pytest.mark.parametrize('fault',('gap','omitted_tail','foreign_guide','changed_goal','reserve','body','false_input'))
def test_partition_cannot_skip_operations_or_substitute_source_provenance(fault):
    prefix,guide,planner,bounds=context();record=deepcopy(plan(prefix,guide,planner,bounds))
    if fault=='gap':record['sections'][1]['first_operation']+=1
    elif fault=='omitted_tail':record['sections'].pop()
    elif fault=='foreign_guide':record['original_guide_sha256']='f'*64
    elif fault=='changed_goal':record['sections'][-1]['guide']['goal']=(0.,0.)
    elif fault=='reserve':record['sections'][0]['measurement_reserve']['current_position_verified']=True
    elif fault=='body':record['sections'][0]['guide']['radius']=.05
    else:record['sections'][0]['input_authorized']=True
    with pytest.raises(ValueError):parse_walking_sections(guide,record)


def test_parsed_guide_and_range_replacement_are_refused():
    prefix,guide,planner,bounds=context();result=parse_walking_sections(guide,plan(prefix,guide,planner,bounds))
    object.__setattr__(result,'ranges',((0,19),(20,39)))
    with pytest.raises(ValueError):result.check()


@pytest.mark.parametrize('fault',('start','end','extra','missing','field_order','body','operation_count'))
@pytest.mark.parametrize('original',(False,True))
def test_fast_integrity_comparison_rejects_each_nested_guide_mutation(fault,original):
    prefix,guide,planner,bounds=context();result=parse_walking_sections(guide,plan(prefix,guide,planner,bounds))
    selected=result.original if original else result.guides[-1]
    op=selected.operations[-1]
    if fault=='start':object.__setattr__(op,'start',(0.,0.))
    elif fault=='end':object.__setattr__(op,'end',(0.,0.))
    elif fault=='extra':object.__setattr__(op,'unvalidated',True)
    elif fault=='missing':object.__delattr__(op,'end')
    elif fault=='field_order':
        start=op.start;object.__delattr__(op,'start');object.__setattr__(op,'start',start)
    elif fault=='body':object.__setattr__(selected,'body_height',2.)
    else:object.__setattr__(selected,'operations',selected.operations[:-1])
    with pytest.raises(ValueError):result.check()
