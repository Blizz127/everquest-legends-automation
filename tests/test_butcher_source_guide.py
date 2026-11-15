from pathlib import Path

import pytest

from eql_automation.butcher_assets import DATA_NAME
from eql_automation.source_destinations import destination_spec, load_source_guide
from eql_automation.source_itinerary import SourceWalkHint


ROOT = Path.home()/'.local/share/eql-automation/owner-route-data'/DATA_NAME


@pytest.mark.parametrize('identifier,mode', [('goblin-camp','camp'), ('goblin-camp-stop','stop')])
def test_checked_goblin_route_retains_same_zone_start_goal_and_ordinary_steps(identifier,mode):
    spec=destination_spec(identifier);guide=load_source_guide(ROOT,identifier)
    assert spec.zone==guide.zone=='butcher' and spec.arrival_mode==mode
    assert guide.operations[0].start==(-650.,2700.) and guide.goal==(-2069.,-298.)
    assert len(guide.operations)==1057 and all(type(op) is SourceWalkHint for op in guide.operations)
    assert guide.radius==1.2 and guide.body_height==6.


def test_goblin_selection_never_uses_an_available_newbie_guide(tmp_path):
    spec=destination_spec('newbie-hills')
    (tmp_path/spec.filename).write_bytes((ROOT/spec.filename).read_bytes())
    with pytest.raises((OSError,ValueError)):
        load_source_guide(tmp_path,'goblin-camp')
    goblin=destination_spec('goblin-camp')
    (tmp_path/goblin.filename).write_bytes((ROOT/goblin.filename).read_bytes()+b' ')
    with pytest.raises(ValueError):load_source_guide(tmp_path,'goblin-camp')
