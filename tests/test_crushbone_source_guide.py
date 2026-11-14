from hashlib import sha256
from pathlib import Path

import pytest

from eql_automation.crushbone_assets import DATA_NAME
from eql_automation.crushbone_source_guide import load_crushbone_source_guide,GUIDE_NAME,GUIDE_PIN
from eql_automation.crushbone_source_guide import destination_spec
from eql_automation.source_itinerary import SourceStepHint


ROOT=Path.home()/'.local/share/eql-automation/owner-route-data'/DATA_NAME


def test_retained_private_guide_loads_without_recipe_files_or_client_actions():
    guide=load_crushbone_source_guide(ROOT)
    assert sha256((ROOT/GUIDE_NAME).read_bytes()).hexdigest()==GUIDE_PIN
    assert guide.goal==(426.,74.) and len(guide.operations)==1053
    assert sum(type(op) is SourceStepHint for op in guide.operations)==7


def test_changed_guide_bytes_refuse(tmp_path):
    (tmp_path/GUIDE_NAME).write_bytes((ROOT/GUIDE_NAME).read_bytes()+b' ')
    with pytest.raises(ValueError):load_crushbone_source_guide(tmp_path)


def test_symlink_guide_directory_refuses(tmp_path):
    link=tmp_path/'guide';link.symlink_to(ROOT,target_is_directory=True)
    with pytest.raises(ValueError):load_crushbone_source_guide(link)


def test_north_wall_guide_has_exact_pinned_goal_and_seven_explicit_steps():
    spec=destination_spec('north-wall');guide=load_crushbone_source_guide(ROOT,spec.identifier)
    assert guide.goal==(-95.,-78.) and len(guide.operations)==237
    assert sum(type(op) is SourceStepHint for op in guide.operations)==7
    assert sha256((ROOT/spec.filename).read_bytes()).hexdigest()==spec.file_sha256


def test_stair_landing_is_a_separate_finite_movement_destination():
    from eql_automation.source_stair_hint import SourceStairHint
    spec=destination_spec('throne-stair-landing');guide=load_crushbone_source_guide(ROOT,spec.identifier)
    assert spec.arrival_mode=='stop' and guide.goal==(2.851,52.27075)
    assert guide.operations[0].start==(-95.,-78.) and len(guide.operations)==11
    assert type(guide.operations[-1]) is SourceStairHint
    assert guide.operations[-1].vertical_model=='bounded_source_contacts'
    assert guide.operations[-1].end==guide.goal and guide.body_height==6. and guide.radius==1.2


@pytest.mark.parametrize('identifier',('unknown','../slave-mines',None,[]))
def test_unknown_destination_never_falls_back_to_default(identifier):
    with pytest.raises(ValueError,match='Unknown'):load_crushbone_source_guide(ROOT,identifier)


def test_missing_selected_guide_does_not_load_available_slave_guide(tmp_path):
    (tmp_path/GUIDE_NAME).write_bytes((ROOT/GUIDE_NAME).read_bytes())
    with pytest.raises((ValueError,OSError)):load_crushbone_source_guide(tmp_path,'north-wall')
