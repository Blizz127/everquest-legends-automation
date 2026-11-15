import json
import os
import struct

import pytest

from eql_automation.camp_progress_status import CampProgressStatus
from test_owner_camp_runtime import client,h,acquire


def test_camp_trace_and_terminal_status_follow_actual_accepted_kill(h,tmp_path):
    e=h.engine;e._camp_progress_status=CampProgressStatus(tmp_path/'status')
    acquire(h)
    h.append('You gain experience! (0.7%)');h.append('You have slain orc fixture!')
    h.tick();h.now+=2.1;h.tick()
    progress=e.camp_last_result['progress']
    assert progress['matching_kills']==1 and progress['xp_award_events']==1
    assert progress['state']=='stopped' and progress['arrival_destination'] is None
    assert progress['client_reported_level'] is None and progress['xp_units_per_hour'] is None
    assert any(event=='camp_progress' and values['xp_award_events']==1 for event,values in h.traces)
    saved=json.loads((tmp_path/'status/camp-progress.json').read_text())
    assert saved['state']=='stopped' and saved['matching_kills']==1 and not e.sender.held


def test_death_is_recorded_before_stop_and_later_same_batch_award_is_ignored(h):
    acquire(h)
    h.append('You have been slain by a snake!');h.append('You gain experience! (9%)')
    h.tick()
    p=h.engine.camp_last_result['progress']
    assert p['observed_deaths']==1 and p['xp_award_events']==0 and p['state']=='stopped'


def test_replaced_log_invalidates_rates_without_replaying_history(h):
    acquire(h);e=h.engine
    h.append('You gain experience! (1%)');h.tick()
    h.path.rename(h.path.with_suffix('.old'));h.path.touch()
    h.append('You gain experience! (99%)');h.tick()
    p=e.camp_last_result['progress']
    assert p['xp_award_events']==1 and not p['continuous'] and p['logged_award_percent_per_hour'] is None


def test_startup_drain_excludes_events_accumulated_during_gauge_read(h):
    e=h.engine;old=e.gate.read_gauges
    def gauge(*args):
        h.append('You gain experience! (9%)')
        return old(*args)
    e.gate.read_gauges=gauge
    assert e.start_stationary_camp();h.tick()
    assert e.camp_session.progress.award_events==0
    assert e.camp_session.progress.last_sequence>=1


def test_zone_change_during_startup_drain_cannot_adopt_wrong_candidates(h):
    e=h.engine;old=e.gate.read_gauges
    def gauge(*args):
        h.append('You have entered The Greater Faydark.')
        return old(*args)
    e.gate.read_gauges=gauge
    assert not e.start_stationary_camp()
    assert e.camp_session is None and not h.commands


def test_status_write_occurs_after_f9_releases_held_keys(h,tmp_path):
    e=h.engine;writer=CampProgressStatus(tmp_path/'status');seen=[]
    class CheckingWriter:
        def write(self,snapshot):
            assert not e.sender.held and not e.sender.unfinished
            seen.append(snapshot['state']);return writer.write(snapshot)
    e._camp_progress_status=CheckingWriter()
    acquire(h);e.stop_action('F9')
    assert seen[-1]=='stopped' and e.camp_session is None


@pytest.mark.parametrize('command',('/target orc_fixture','/consider','/cast 3'))
def test_f9_mid_command_releases_before_status_io(h,tmp_path,command):
    e=h.engine;writer=CampProgressStatus(tmp_path/'status');seen=[]
    class CheckingWriter:
        def write(self,snapshot):
            assert not e.sender.held
            seen.append(snapshot['state']);return writer.write(snapshot)
    e._camp_progress_status=CheckingWriter()
    def on_write(kind,key,value):
        os.write(h.write_fd,struct.pack('iii',kind,key,value))
        if value==1 and h.commands and h.commands[-1]==command:
            e.stop_action('F9 during typing')
    e.sender.ui.write=on_write
    assert e.start_stationary_camp()
    if command=='/cast 3':
        h.tick();h.append('Orc fixture scowls at you, ready to attack -- looks like quite a gamble. (Lvl: 5)')
    with pytest.raises(InterruptedError):h.tick()
    assert seen[-1]=='stopped' and not e.sender.held and e.camp_session is None
    saved=json.loads((tmp_path/'status/camp-progress.json').read_text())
    assert saved['state']=='stopped' and saved['finish_reason']=='F9 during typing'


def test_progress_trace_cancellation_cannot_continue_to_target_input(h):
    e=h.engine;old=e.trace
    def trace(event,**values):
        old(event,**values)
        if event=='camp_progress':e.stop_action('F9')
    e.trace=trace
    assert e.start_stationary_camp();h.tick()
    assert e.camp_session is None and not h.commands and not e.sender.held


@pytest.mark.parametrize('h',[{'repeat':True}],indirect=True)
def test_level_observation_remains_separate_from_configured_start(h):
    acquire(h);e=h.engine
    h.append('You have gained a level! Welcome to level 8!');h.tick()
    assert e.camp_session.progress.configured_level==7
    assert e.camp_session.progress.reported_level==8
