from datetime import datetime,timedelta
from types import SimpleNamespace

import pytest

from eql_automation.camp_recovery import CampRecovery
from eql_automation.camp_session import StationaryCamp,NpcCandidate


def test_gauge_samples_predating_posture_settle_never_count():
    r=CampRecovery(0.,phase='stand_after_rest')
    r.submitted('/stand',1.)
    assert r.last_stand_completed_at==1. and r.posture_observed is None
    r.sample(1.6,1.1,1.,1.);r.sample(1.7,1.2,1.,1.)
    assert r.good_samples==0 and r.phase=='stand_settle'
    r.sample(1.8,1.6,1.,1.);r.sample(1.9,1.6,1.,1.)
    assert r.good_samples==1
    r.sample(2.,1.9,1.,1.);assert r.phase=='recovered'


def test_recovery_cannot_loop_without_progress_or_repeat_the_sit_toggle():
    r=CampRecovery(0.)
    r.submitted('/stand',0.);r.submitted('/sit on',.5)
    with pytest.raises(ValueError):r.submitted('/sit on',1.)
    r.sample(1.,1.,.7,.4)
    with pytest.raises(ValueError,match='timed out'):r.sample(92.,92.,.7,.4)


def test_duplicate_kill_from_previous_same_name_encounter_is_not_another_kill():
    c=StationaryCamp((NpcCandidate('orc fixture',(5,),'a'*64,()),),7,1,0.,'fixture',repeat=True)
    start=datetime(2026,11,14,17)
    def observe(body,seq,now):
        stamp=start+timedelta(seconds=int(now))
        raw=stamp.strftime('[%a %b %d %H:%M:%S %Y] ')+body
        c.observe(raw,seq,now,stamp,consider=lambda b:('orc fixture','scowls',5) if b=='con' else None,safe=lambda *a:True)
    c.next_candidate(0.);c.expect_reply(0,0.,start);observe('con',1,.1)
    observe('You have slain orc fixture!',2,.2);assert c.kills==1
    c.reset_round();c.next_candidate(.3);c.expect_reply(2,.3,start);observe('con',3,.4)
    observe('You have slain orc fixture!',4,.5)
    assert c.kills==1 and c.phase=='fight'


def test_backward_pending_level_is_rejected_in_same_batch():
    c=StationaryCamp((),7,1,0.,'fixture',repeat=True)
    stamp=datetime(2026,11,14,17)
    for seq,level in enumerate((8,7),1):
        raw=stamp.strftime('[%a %b %d %H:%M:%S %Y] ')+f'You have gained a level! Welcome to level {level}!'
        c.observe(raw,seq,0.,stamp,consider=lambda b:None,safe=lambda *a:True)
    assert not c.running and c.pending_level==8


def test_level_advance_marker_coalesces_increases_but_ignores_duplicates():
    c=StationaryCamp((),7,3,0.,'fixture',repeat=True)
    stamp=datetime(2026,11,14,17)
    def ding(level,seq):
        raw=stamp.strftime('[%a %b %d %H:%M:%S %Y] ')+f'You have gained a level! Welcome to level {level}!'
        c.observe(raw,seq,1.,stamp,consider=lambda b:None,safe=lambda *a:True)
    ding(8,1);first=c.last_level_advance
    assert (first.previous_level,first.level,first.camp_log_seq,first.generation)==(7,8,1,3)
    ding(8,2);assert c.last_level_advance is first
    ding(9,3);latest=c.last_level_advance
    assert latest is not first and (latest.previous_level,latest.level,latest.camp_log_seq)==(8,9,3)
    c.level=9;c.pending_level=None;c.level_source='client_log';c.reset_round()
    ding(9,4);assert c.last_level_advance is latest
    assert c.snapshot()['last_level_advance']['camp_log_seq']==3


@pytest.mark.parametrize('fault',('delayed','sequence','backwards'))
def test_invalid_level_message_never_replaces_the_last_advance(fault):
    c=StationaryCamp((),7,3,0.,'fixture',repeat=True)
    stamp=datetime(2026,11,14,17)
    def ding(level,seq,wall):
        raw=stamp.strftime('[%a %b %d %H:%M:%S %Y] ')+f'You have gained a level! Welcome to level {level}!'
        c.observe(raw,seq,1.,wall,consider=lambda b:None,safe=lambda *a:True)
    ding(8,2,stamp);first=c.last_level_advance
    ding(7 if fault=='backwards' else 9,2 if fault=='sequence' else 3,
        stamp+timedelta(seconds=10) if fault=='delayed' else stamp)
    assert not c.running and c.last_level_advance is first
