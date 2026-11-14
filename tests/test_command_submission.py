from dataclasses import FrozenInstanceError

import pytest

from eql_automation.command_submission import CommandSubmissionJournal,LOCATION_EVENTS


def write(journal,event,at,*,outcome='complete',written=24,finished=None):
    attempt=journal.begin(event,at,24)
    journal.finish(attempt,at+.001 if finished is None else finished,
                   outcome=outcome,written_bytes=written)


def test_prefix_advances_only_after_complete_key_cycle_and_snapshots_do_not_change():
    journal=CommandSubmissionJournal('fixture-operation')
    initial=journal.snapshot()
    snapshots=[]
    for index,event in enumerate(LOCATION_EVENTS):
        write(journal,event,float(index))
        snapshots.append(journal.snapshot())
    assert [s.submitted_prefix for s in snapshots[:4]]==['','','','/']
    assert snapshots[35].submitted_prefix=='/location' and not snapshots[35].enter_submitted
    assert snapshots[-1].enter_submitted and snapshots[-1].next_key_code is None
    assert snapshots[-1].submitted_key_count==10 and not snapshots[-1].uncertain
    assert initial.revision==0 and initial.writes==() and initial.submitted_prefix==''
    assert not snapshots[-1].client_delivery_verified and not snapshots[-1].client_focus_verified
    with pytest.raises(FrozenInstanceError):initial.revision=1


@pytest.mark.parametrize('failure',['short','exception','clock-backwards','unexpected'])
def test_failure_is_not_repaired_by_later_successful_release(failure):
    journal=CommandSubmissionJournal('fixture')
    write(journal,LOCATION_EVENTS[0],0.)
    if failure=='short':write(journal,LOCATION_EVENTS[1],1.,outcome='short',written=0)
    elif failure=='exception':write(journal,LOCATION_EVENTS[1],1.,outcome='exception',written=None)
    elif failure=='clock-backwards':write(journal,LOCATION_EVENTS[1],1.,finished=.5)
    else:write(journal,(1,28,1),1.)
    for index,event in enumerate(LOCATION_EVENTS[2:],2):write(journal,event,float(index))
    result=journal.snapshot()
    assert result.submitted_prefix=='' and result.uncertain and not result.enter_submitted
    assert result.next_key_code is None and result.attempted_key_codes[0]==53


def test_pending_attempt_is_retained_in_earlier_snapshot_after_completion():
    journal=CommandSubmissionJournal('fixture')
    attempt=journal.begin(LOCATION_EVENTS[0],1.,24)
    pending=journal.snapshot()
    journal.finish(attempt,1.01,written_bytes=24,outcome='complete')
    assert pending.writes[0].outcome=='pending' and pending.uncertain
    assert journal.snapshot().writes[0].outcome=='complete'
    assert journal.snapshot().next_key_code is None  # Still mid-cycle.


def test_inter_event_clock_reversal_prevents_prefix_completion():
    journal=CommandSubmissionJournal('fixture')
    write(journal,LOCATION_EVENTS[0],10.)
    for index,event in enumerate(LOCATION_EVENTS[1:4],1):write(journal,event,float(index))
    assert journal.snapshot().uncertain and journal.snapshot().submitted_prefix==''
