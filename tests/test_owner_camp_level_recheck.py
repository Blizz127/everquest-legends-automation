"""Fresh level events reconsider an optional plan without enabling movement."""
from dataclasses import replace

import pytest

from test_owner_camp_position import camp,finish
from test_camp_floor_checkpoint import checkpoint
from test_source_motion import f
from test_route_floor_commit import legacy
from test_motion_collection import retained
from test_owner_journey_runtime import h


def ding(h,level):
    e=h.engine
    with h.log.open('a') as out:
        out.write(e.camp_wall().strftime('[%a %b %d %H:%M:%S %Y] ')+
            f'You have gained a level! Welcome to level {level}!\n')
    e.read_log()
    assert e.camp_session is not None,'\n'.join(h.notices)
    assert e.camp_session.level==e.settings.level==level


def first_check(h):
    h.calls=[]
    h.engine._test_camp_probe_provider=lambda p:h.calls.append(p.level_advance)
    h.recovered();finish(h)
    assert h.engine.journey is not None,'\n'.join(h.notices)
    assert h.engine.journey.height_check_done,'\n'.join(h.notices)


@pytest.mark.parametrize('h',['level_provider'],indirect=True)
def test_new_observed_level_rechecks_once_after_spell_preparation(camp):
    h=camp;e=h.engine;first_check(h)
    assert h.calls==[None]
    ding(h,8);session=e.camp_session;advance=session.last_level_advance
    assert session.preparation_due
    before=list(h.events);h.recovered(kills=2);h.drain()
    assert e.camp_position is None and h.events==before and h.calls==[None]
    # Simulate completion of the existing preparation worker; its own retained
    # integration case covers memorizing, then recovery in the same sender.
    session.preparation_due=False
    h.recovered(kills=2);assert e.camp_position.level_advance is advance
    finish(h)
    assert h.calls==[None,advance] and e.journey.last_considered_level_advance is advance
    before=list(h.events);h.recovered(kills=3);h.drain()
    assert e.camp_position is None and h.events==before
    ding(h,8);session.preparation_due=False;h.recovered(kills=4);h.drain()
    assert e.camp_position is None and h.events==before and len(h.calls)==2
    assert not h.commands and not e.sender.held
    assert all(kind!=1 or key==62 for kind,key,value in h.events)


def test_default_camp_does_not_repeat_height_collection_after_level_up(camp):
    h=camp;e=h.engine;first_check(h);before=list(h.events)
    ding(h,8);e.camp_session.preparation_due=False
    h.recovered(kills=2);h.drain()
    assert e.camp_position is None and h.events==before and not h.calls
    assert e.camp_session.phase=='select'


@pytest.mark.parametrize('h',['level_provider'],indirect=True)
@pytest.mark.parametrize('change',('F9','F8','marker','settings'))
def test_second_position_scope_preserves_cancel_and_level_identity(camp,change):
    h=camp;e=h.engine;h.calls=[]
    e._test_camp_probe_provider=lambda p:h.calls.append(p.level_advance)
    # The successful first collection is exercised above. These cases start
    # from that state and cancel the second collection before it sends input.
    e.journey.height_check_done=True
    ding(h,8)
    e.camp_session.preparation_due=False;h.recovered(kills=2)
    p=e.camp_position;assert p is not None
    before=list(h.events)
    if change=='F9':e.stop_action('F9 during level reconsideration')
    elif change=='F8':e.handle_job('arm',e.cancel_generation)
    elif change=='marker':e.camp_session.last_level_advance=replace(p.level_advance)
    else:e.settings.level=9
    finish(h)
    assert not h.calls and h.events==before and e.camp_session is None
    assert e.journey is None and not e.sender.held and e.live_zone_tracker.lease is None
    assert h.scope_journey.last_considered_level_advance is None
    if change=='F8':assert e._journey_assist is not None
