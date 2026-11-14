from hashlib import sha256
from pathlib import Path

import pytest

from eql_automation.crushbone_assets import DATA_NAME
from eql_automation.crushbone_source_guide import load_crushbone_source_guide,GUIDE_NAME,GUIDE_PIN
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
