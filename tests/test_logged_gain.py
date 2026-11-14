from pathlib import Path

import pytest

from eql_automation.telemetry import ClientLogReader,RunState,render_status


def award(state,text='2.574',now=60):
    state.observe_log(f'[synthetic] You gain experience! ({text}%)',now=now)


def test_new_awards_and_empty_polls_use_the_full_receipt_window(tmp_path: Path):
    p=tmp_path/'character.log';p.write_text('[old] You gain experience! (50.000%)\n')
    s=RunState(level=7);r=ClientLogReader(p,s,now=0)
    with p.open('a') as f:
        f.write('[new] You gain experience! (0.119%)\n[new] You gain experience! (2.574%)\n')
    r.poll(now=60)
    assert s.log_gain_events==2 and s.log_gain_micropoints==2693000
    assert s.client_reported_gain_percent_per_hour==pytest.approx(161.58)
    r.poll(now=120)
    assert s.client_reported_gain_percent_per_hour==pytest.approx(80.79)
    assert s.xp is None and s.xp_per_hour is None and s.level_progress_fraction is None
    assert 'Client-reported gross XP gain: 80.790 percentage points/hour' in render_status(s)


def test_only_exact_award_templates_are_counted():
    s=RunState(level=7);s.advance_log_clock(0)
    for text in ('Someone says, You gain experience! (5%)','You gain experience! (-1%)',
                 'You gain experience! (nan%)','You gain experience! (1e2%)',
                 'You gain experience! (2.1%) extra','You gain experience!',
                 'You gain experience! (0.1234567%)'):
        s.observe_log('[test] '+text,now=60)
    assert s.log_gain_events==0 and s.client_reported_gain_percent_per_hour==0
    s.observe_log('[test] You gain experience (with a bonus)! (1.000%)',now=60)
    s.observe_log('[test] You gain experience (with a penalty)! (0.125%)',now=60)
    assert s.log_gain_events==2 and s.client_reported_gain_percent_per_hour==67.5


@pytest.mark.parametrize('event',('You have gained a level! Welcome to level 8!',
    'You LOST a level! You are now level 6!','You LOST 2 levels! You are now level 5!',
    'You have been slain by a test mob!','You have entered The Greater Faydark.',
    'LOADING, PLEASE WAIT...'))
def test_level_death_and_zone_events_reset_even_without_a_death_counter(event):
    s=RunState(level=7,deaths=None);s.advance_log_clock(0);award(s)
    s.observe_log('[test] '+event,now=120)
    assert s.log_gain_events==0 and s.client_reported_gain_percent_per_hour is None
    s.advance_log_clock(180)
    assert s.client_reported_gain_percent_per_hour==0
    assert s.deaths is None


def test_unknown_level_direct_changes_and_clock_regression_do_not_mix_windows():
    s=RunState();award(s)
    assert s.client_reported_gain_percent_per_hour is None and s.log_gain_events==0
    s.level=7;s.advance_log_clock(100);award(s,now=160)
    for field,value in (('level',8),('camp','another'),('zone','another')):
        setattr(s,field,value)
        assert s.client_reported_gain_percent_per_hour is None
        s.advance_log_clock(200)
        assert s.log_gain_events==0
        award(s,now=260)
    s.advance_log_clock(10)
    assert s.log_gain_events==0 and s.client_reported_gain_percent_per_hour is None
    with pytest.raises(ValueError):s.advance_log_clock(float('nan'))
    assert s.log_gain_started_at is None


def test_raw_xp_drop_and_log_replacement_discard_reported_gain(tmp_path: Path):
    p=tmp_path/'character.log';p.write_text('')
    s=RunState(level=7);r=ClientLogReader(p,s,now=0)
    s.observe_xp(100,now=0);award(s)
    s.observe_xp(90,now=120)
    assert s.client_reported_gain_percent_per_hour is None
    r.poll(now=180)
    with p.open('a') as f:f.write('[new] You gain experience! (1%)\n')
    r.poll(now=240)
    assert s.log_gain_events==1
    replacement=tmp_path/'replacement';replacement.write_text('[old] You gain experience! (99%)\n')
    replacement.replace(p);r.poll(now=300)
    assert s.level is None and s.log_gain_events==0 and s.client_reported_gain_percent_per_hour is None


def test_missing_log_has_no_rate_window_and_backlog_is_not_replayed(tmp_path: Path):
    p=tmp_path/'missing.log';s=RunState(level=7);r=ClientLogReader(p,s,now=0)
    r.poll(now=60)
    assert s.client_reported_gain_percent_per_hour is None
    p.write_text('[old] You gain experience! (99%)\n');r.poll(now=120)
    assert s.level is None and s.log_gain_events==0
    s.level=7;r.poll(now=180)
    with p.open('a') as f:f.write('[old] You gain experience! (99%)\n'*20000)
    r.poll(now=240)
    assert s.level is None and s.log_gain_events==0


def test_unknown_loss_level_clears_previous_progress():
    s=RunState(level=7)
    s.observe_level_progress(level=7,fraction=.5,normal_xp_allocation_verified=True,now=0)
    s.observe_log('[test] You LOST a level! You are now level 0!',now=60)
    assert s.level is None and s.level_progress_fraction is None
    assert s.client_reported_gain_percent_per_hour is None


@pytest.mark.parametrize('bad_time',(float('nan'),float('inf'),True,'60'))
def test_invalid_poll_clock_cannot_consume_fresh_awards(tmp_path,bad_time):
    p=tmp_path/'character.log';p.write_text('')
    s=RunState(level=7);r=ClientLogReader(p,s,now=0)
    with p.open('a') as f:f.write('[new] You gain experience! (2.574%)\n')
    with pytest.raises(ValueError):r.poll(now=bad_time)
    assert s.log_gain_events==0 and s.client_reported_gain_percent_per_hour is None
    assert len(r.poll(now=60))==1
    assert s.log_gain_events==1 and s.log_gain_micropoints==2574000
