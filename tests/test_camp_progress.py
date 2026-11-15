from datetime import datetime,timedelta
import json

import pytest

from eql_automation.camp_progress import CampProgress
from eql_automation.camp_progress_status import CampProgressStatus

START=datetime(2026,11,15,3,0)

def observe(p,body,seq,seconds):
    p.observe(START+timedelta(seconds=seconds),body,seq,100.+seconds)


def test_receipt_window_counts_identical_awards_and_quiet_time_without_inventing_xp():
    p=CampProgress(100.,7,last_sequence=4)
    observe(p,'You gain experience! (0.1%)',5,10)
    observe(p,'You gain experience! (0.1%)',6,10)
    p.advance(160.)
    s=p.snapshot()
    assert s['xp_award_events']==2 and s['logged_award_percent']==.2
    assert s['logged_award_percent_per_hour']==12.
    assert s['xp_award_events_per_hour']==120.
    assert s['client_reported_level'] is None and s['configured_level']==7
    assert s['current_xp'] is s['xp_units_per_hour'] is s['net_xp_progress'] is None
    assert '12.00%/h' in p.summary() and s['arrival_destination'] is None
    p.advance(220.);assert p.snapshot()['logged_award_percent_per_hour']==6.


def test_ding_closes_old_window_and_keeps_exact_line_order():
    p=CampProgress(100.,7)
    observe(p,'You gain experience! (1.25%)',1,10)
    observe(p,'You have gained a level! Welcome to level 8!',2,60)
    observe(p,'You gain experience (with a bonus)! (0.25%)',3,60)
    p.advance(220.)
    s=p.snapshot()
    assert s['client_reported_level']==s['award_window_level']==8
    assert s['xp_award_events']==2 and s['award_window_events']==1
    assert s['logged_award_percent_per_hour']==15.
    assert s['closed_award_windows']==[dict(ended_by_sequence=2,reported_level=None,
        seconds=60.,events=1,logged_award_percent=1.25,logged_award_percent_per_hour=75.)]


def test_death_and_level_loss_survive_finalization_and_clock_no_longer_dilutes_rate():
    p=CampProgress(100.,7)
    observe(p,'You gain experience! (1%)',1,20)
    observe(p,'You LOST a level! You are now level 6!',2,40)
    observe(p,'You have been slain by a snake!',3,60)
    p.finish(160.,'Death observed');before=p.snapshot()
    p.finish(300.,'later cleanup');p.advance(400.)
    observe(p,'You gain experience! (9%)',4,400)
    assert p.snapshot()==before
    assert before['observed_deaths']==1 and before['client_reported_level']==6
    assert before['xp_award_events']==1 and before['finish_reason']=='Death observed'


@pytest.mark.parametrize('problem',('replay','gap','backward_stamp','clock_backwards','nan','logging'))
def test_discontinuous_observation_cannot_publish_a_rate(problem):
    p=CampProgress(100.,7)
    observe(p,'You gain experience! (0.5%)',1,10)
    if problem=='replay':observe(p,'You gain experience! (0.5%)',1,11)
    elif problem=='gap':observe(p,'You gain experience! (0.5%)',3,11)
    elif problem=='backward_stamp':p.observe(START,'You gain experience! (0.5%)',2,111.)
    elif problem=='clock_backwards':p.advance(109.)
    elif problem=='nan':p.advance(float('nan'))
    else:observe(p,"Logging to 'changed' is now ON.",2,11)
    p.advance(160.)
    s=p.snapshot()
    assert not s['continuous'] and s['logged_award_percent_per_hour'] is None
    assert s['xp_award_events']==1 and s['xp_award_events_per_hour'] is None


def test_only_accepted_matching_kill_hook_counts_and_arrival_is_historical():
    p=CampProgress(100.,7)
    observe(p,'You have slain a bat!',1,10)
    assert p.snapshot()['matching_kills']==0
    p.matching_kill(0);assert p.snapshot()['matching_kills']==0
    p.matching_kill(1);assert p.snapshot()['matching_kills']==1
    p.matching_kill(1);assert p.snapshot()['matching_kills']==1
    p.bind_arrival(destination_id='goblin-camp',name='Goblin Camp',zone='butcher',
        itinerary_sha256='a'*64,stopped_log_seq=90)
    a=p.snapshot()['arrival_destination']
    assert a['name']=='Goblin Camp' and not a['current_position_verified']
    with pytest.raises(ValueError):
        p.bind_arrival(destination_id='wrong',name='wrong',zone='wrong',itinerary_sha256='b'*64,stopped_log_seq=91)


def test_status_is_timestamped_private_historical_evidence(tmp_path):
    p=CampProgress(100.,7);observe(p,'You gain experience! (1%)',1,30);p.finish(160.,'F9')
    writer=CampProgressStatus(tmp_path/'owner-status')
    assert writer.write(p.snapshot())
    record=json.loads((writer.directory/'camp-progress.json').read_text())
    assert record['state']=='stopped' and record['recorded_at'] and not record['current_process_verified']
    text=(writer.directory/'STATUS.md').read_text()
    assert 'Client-reported level: unknown' in text and 'XP units per hour: unknown' in text
    assert 'F9' in text and '60.000 percentage points/hour' in text
    assert (writer.directory/'STATUS.md').stat().st_mode & 0o777==0o600
    assert not list(writer.directory.glob('.*'))
    blocked=tmp_path/'blocked';blocked.write_text('preserve')
    assert not CampProgressStatus(blocked).write(p.snapshot()) and blocked.read_text()=='preserve'
