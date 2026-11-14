"""Actual retained Engine and KeySender; fake game feedback, OS-pipe key events."""
from datetime import datetime, timedelta
from hashlib import sha256
import os
import re
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

import pytest

from eql_automation.camp_session import NpcCandidate, observed_candidates
from eql_automation.owner_camp_runtime import make_owner_camp_engine, CAMP_JOB

HELPER = Path.home()/'.local/share/eql-automation/owner-assist/0.39.13'
PIN = 'd6ec143920a6748364eb27fa6e279aaf45763b8345fe8e81d7c171648561927f'


@pytest.fixture(scope='module')
def client():
    assert sha256((HELPER/'rotation_engine.py').read_bytes()).hexdigest() == PIN
    sys.path.insert(0, str(HELPER))
    import rotation_engine
    return rotation_engine


@pytest.fixture
def h(tmp_path, monkeypatch, client, request):
    import rotation_core
    # Only Linux key constants; never import/create an input device.
    header = Path('/usr/include/linux/input-event-codes.h')
    if header.exists():
        definitions = header.read_text()
        ecodes = SimpleNamespace(**{name:int(value,0) for name,value in
            re.findall(r'^#define\s+((?:KEY|EV)_[A-Z0-9_]+)\s+(0x[0-9a-fA-F]+|[0-9]+)\b', definitions, re.M)})
    else:
        from evdev import ecodes  # Constants only on the owner runtime.
    h = SimpleNamespace(now=100., commands=[], traces=[], notices=[], focus=True, cancel_hook=lambda:None)
    h.clock = lambda:h.now
    h.wall = lambda:datetime(2026,11,14,17,0)+timedelta(seconds=h.now-100.)
    game = tmp_path/'game'; (game/'Logs').mkdir(parents=True)
    h.path = game/'Logs/eqlog_Probe_private.txt'; h.path.touch()
    h.append = lambda body: h.path.open('a').write(h.wall().strftime('[%a %b %d %H:%M:%S %Y] ')+body+'\n')
    candidate = NpcCandidate('orc fixture', (5,), 'a'*64, ((1,2),))
    E = make_owner_camp_engine(client.Engine, client=client, clock=h.clock, wall=h.wall,
                              candidates_loader=lambda e:(candidate,),repeat=getattr(request,'param',False),
                              posture_loader=lambda p:SimpleNamespace(check=lambda:None))
    e = h.engine = E(rotation_core.Settings(game_dir=str(game), character='Probe', server='private', level=7),
                     lambda p:None, lambda *a:None)
    e.selector.close(); e.trace = lambda event, **values:h.traces.append((event,values))
    h.saved_levels=[];e.settings.save=lambda:h.saved_levels.append(e.settings.level)
    e.emit = lambda text=None:h.notices.append(text)
    e.gate = SimpleNamespace(controls_ready=lambda:h.focus, focused=lambda:h.focus,
                            read_gauges=lambda *a:(1.,1.))
    e.input_events = lambda:h.cancel_hook()
    e.blocked_keys = lambda:False
    e.stop_keys_held = lambda:False
    e.tail = e.make_tail(); e.tail.poll(); e.zone = 'fixture'
    e.prepared = True; e.prepared_level = 7
    spell = SimpleNamespace(busy_seconds=.2, recast_ms=200, duration_ticks=0, name='Fixture Bolt')
    e.profile={'nuke':spell}; e.rotation=rotation_core.Rotation(e.profile,7,damage_interval=4.)
    h.read_fd, h.write_fd = os.pipe(); os.set_blocking(h.read_fd,False)
    sender=client.KeySender.__new__(client.KeySender)
    sender.codes=ecodes; sender.gate=e.gate; sender.allowed=e.allowed
    sender.held=set();sender.unfinished=False;sender.dismissed=False
    sender.ui=SimpleNamespace(write=lambda kind,key,value:os.write(h.write_fd,struct.pack('iii',kind,key,value)), syn=lambda:None)
    original=sender.command
    def command(text):
        h.commands.append(text);original(text)
    sender.command=command; e.sender=sender
    # Real typing sequence and cancellation callbacks, deterministic time.
    monkeypatch.setattr(client.time,'sleep',lambda seconds:setattr(h,'now',h.now+seconds))
    monkeypatch.setattr(client.time,'monotonic',h.clock)
    def tick():
        e.pump();e.last_gauge=h.now
        e.combat_tick(h.now);e.autopilot_tick(h.now)
    h.tick=tick
    yield h
    sender.release_all();os.close(h.write_fd);os.close(h.read_fd)


def acquire(h):
    e=h.engine;assert e.start_stationary_camp(), h.notices
    h.tick()
    assert h.commands==['/target orc_fixture','/consider']
    assert not e.active
    h.append('Orc fixture scowls at you, ready to attack -- looks like quite a gamble. (Lvl: 5)')
    h.tick()
    assert e.camp_session.phase=='fight', (h.notices,h.traces)
    assert '/cast 3' in h.commands


def test_actual_engine_selects_casts_observes_kill_and_stops(h):
    acquire(h);e=h.engine
    h.append('You gain experience! (0.7%)');h.append('You have slain orc fixture!')
    h.tick();assert not e.active
    h.append('--You have looted a Fixture Item.--');h.now+=2.1;h.tick()
    assert e.camp_session is None and e.cancelled and not e.active
    assert e.camp_last_result['kills']==1 and e.camp_last_result['logged_xp_awards']==[.7]
    assert e.camp_last_result['loot_messages']==1 and not e.camp_last_result['loot_completion_verified']
    assert not e.sender.held
    data=os.read(h.read_fd,65536)
    events=list(struct.iter_unpack('iii',data));assert any(kind==1 and value==1 for kind,key,value in events)
    assert not any(key in e.sender.movement_codes() and value==1 for kind,key,value in events)
    before=list(h.commands);h.tick();assert h.commands==before


@pytest.mark.parametrize('command',('/target orc_fixture','/consider','/cast 3'))
def test_f9_during_actual_key_sequence_cancels_scope(h,command):
    e=h.engine
    def cancel():
        if h.commands and h.commands[-1]==command and e.sender.held:
            e.stop_action('F9');h.cancel_hook=lambda:None
    # check() runs between taps; trigger after at least one byte was emitted.
    def on_write(kind,key,value):
        os.write(h.write_fd,struct.pack('iii',kind,key,value))
        if value==1: cancel()
    e.sender.ui.write=on_write
    if command=='/cast 3':
        assert e.start_stationary_camp();h.tick()
        h.append('Orc fixture scowls at you, ready to attack -- looks like quite a gamble. (Lvl: 5)')
    else:
        assert e.start_stationary_camp()
    with pytest.raises(InterruptedError):h.tick()
    assert e.camp_session is None and not e.active and e.cancelled and not e.sender.held
    before=list(h.commands);h.tick();assert before==h.commands


@pytest.mark.parametrize('event',('replacement','other_target','retaliation','expired_reply','zone','focus','locked'))
def test_camp_never_reuses_old_target_permission(h,event):
    e=h.engine
    if event=='expired_reply':
        assert e.start_stationary_camp();h.tick();h.now+=7
        h.append('Orc fixture scowls at you, ready to attack -- looks like quite a gamble. (Lvl: 5)')
    else:
        acquire(h)
        if event=='replacement':
            replaced=h.path.with_suffix('.new');replaced.write_text('historical junk\n');replaced.replace(h.path)
        elif event=='other_target':h.append('Targeted (PC): Someone')
        elif event=='retaliation':h.append('Another orc hits YOU for 3 points of damage.')
        elif event=='zone':h.append('You have entered Another Zone.')
        elif event=='focus':h.focus=False
        elif event=='locked':h.append('Your attack failed because your target is Encounter Locked to someone else.')
    before=len(h.commands);h.tick()
    assert e.camp_session is None and not e.active and len(h.commands)==before


def test_f9_invalidates_queued_start_and_assist_stays_current_target(h):
    e=h.engine;e.post(CAMP_JOB);job=e.jobs.get_nowait();e.stop_action('F9')
    e.handle_job(*job);assert e.camp_session is None and not h.commands
    acquire(h);h.now+=2
    e.handle_job('arm',e.cancel_generation)
    assert e.camp_session is None and e.active
    with pytest.raises(ValueError):e.send('/target orc_fixture')


@pytest.mark.parametrize('point',('first_focus','log_drain','final_reset'))
def test_f9_during_startup_cannot_be_adopted(h,point):
    e=h.engine
    if point=='first_focus':
        def focus():
            e.gate.controls_ready=lambda:True;e.stop_action('F9');return True
        e.gate.controls_ready=focus
    elif point=='log_drain':
        original=e.read_log
        def read():
            original();e.stop_action('F9')
        e.read_log=read
    else:
        original=e.reset_target
        def reset(*args,**kw):
            original(*args,**kw);e.stop_action('F9')
        e.reset_target=reset
    assert not e.start_stationary_camp()
    assert e.camp_session is None and e.cancelled and not h.commands


def test_f9_in_last_provider_cannot_allow_another_key(h):
    e=h.engine;assert e.start_stationary_camp()
    e._camp_command='/consider'
    def focus():
        e.gate.controls_ready=lambda:True;e.stop_action('F9');return True
    e.gate.controls_ready=focus
    assert not e.allowed() and e.camp_session is None


@pytest.mark.parametrize('job',('stationary_camp_later','arm'))
def test_stop_callback_cannot_queue_new_generation(h,job):
    e=h.engine
    if job=='arm':acquire(h)
    def emit(text=None):
        e.emit=lambda *a:None;e.stop_action('F9')
    e.emit=emit
    e.handle_job(job,e.cancel_generation)
    assert not e.active and e.camp_session is None and e.deferred is None


def test_kill_during_target_refresh_still_finishes_one_kill(h):
    acquire(h);e=h.engine;h.now+=4.1;h.tick()
    assert e.camp_session.phase=='consider'
    h.append('You have slain orc fixture!');h.tick();h.now+=2.1;h.tick()
    assert e.camp_session is None and e.camp_last_result['kills']==1


@pytest.mark.parametrize('hp,mana',((.6,1.),(1.,.20)))
def test_camp_preserves_heal_priority_and_mana_reserve(h,hp,mana):
    acquire(h);e=h.engine;e.hp=hp;e.mana=mana
    h.now+=1.;e.last_gauge=h.now;e.rotation.last.clear()
    before=len(h.commands);e.combat_tick(h.now)
    assert len(h.commands)==before


def test_no_combat_progress_stops_without_navigation(h):
    acquire(h);e=h.engine;h.now+=31
    e.autopilot_tick(h.now)
    assert e.camp_session is None and '30 seconds' in e.camp_last_result['reason']


def test_losing_an_engaged_target_never_acquires_an_add(h):
    acquire(h);e=h.engine;h.now+=4.1;h.tick()
    h.append('Consider whom?');h.tick()
    assert e.camp_session is None and h.commands.count('/target orc_fixture')==1


def test_final_enter_release_stop_does_not_publish_a_command_result(h):
    e=h.engine;assert e.start_stationary_camp()
    def write(kind,key,value):
        os.write(h.write_fd,struct.pack('iii',kind,key,value))
        if key==e.sender.codes.KEY_ENTER and value==0:
            # Avoid recursion through cleanup of that same held Enter.
            e.sender.ui.write=lambda k,c,v:os.write(h.write_fd,struct.pack('iii',k,c,v))
            e.stop_action('F9 at final Enter release')
    e.sender.ui.write=write
    with pytest.raises(InterruptedError):h.tick()
    assert e.camp_session is None and not e.active and not e.sender.held
    assert h.commands==['/target orc_fixture']


def test_history_only_seeds_paired_npc_names_and_requires_kill(tmp_path,client):
    path=tmp_path/'log';stamp='[Sat Nov 14 17:00:00 2026] '
    rows=['You have entered Fixture.', 'Targeted (NPC): orc fixture',
          'Orc fixture scowls at you, ready to attack -- looks like quite a gamble. (Lvl: 5)',
          'You have slain orc fixture!', 'Targeted (NPC): an elven slave',
          'An elven slave scowls at you, ready to attack -- looks like quite a gamble. (Lvl: 2)',
          'You have slain an elven slave!', 'Targeted (PC): Someone']
    path.write_text('\n'.join(stamp+body for body in rows)+'\n')
    result=observed_candidates(path,'Fixture',consider=client.consider_target,safe=client.safe_leveling_target)
    assert len(result)==1 and result[0].name=='Orc fixture' and result[0].levels==(5,)
    assert observed_candidates(path,'Other',consider=client.consider_target,safe=client.safe_leveling_target)==()


def repeat_tick(h):
    h.tick()
    # Keep the actual pipe bounded while exercising a longer series of commands.
    try:data=os.read(h.read_fd,65536)
    except BlockingIOError:data=b''
    assert not any(kind==1 and key in h.engine.sender.movement_codes() and value==1
                   for kind,key,value in struct.iter_unpack('iii',data))


def kill_to_recovery(h):
    h.append('You gain experience (with a bonus)! (0.7%)')
    h.append('You have slain orc fixture!');repeat_tick(h)
    h.now+=2.1;repeat_tick(h)
    assert h.engine.camp_session.phase=='recovery',h.notices


def finish_full_recovery(h):
    # Start with the stand request. Two later captured samples must pass settling.
    repeat_tick(h)
    assert h.commands[-1]=='/stand'
    for _ in range(2):h.now+=.6;repeat_tick(h)
    assert h.engine.camp_session.phase=='select',h.notices
    repeat_tick(h)
    assert h.engine.camp_session.phase=='consider'
    assert h.commands[-2:]==['/target orc_fixture','/consider']


@pytest.mark.parametrize('h',[True],indirect=True)
def test_repeated_actual_engine_two_kills_and_same_sender(h):
    acquire(h);e=h.engine;camp=e.camp_session;sender=e.sender;generation=e.cancel_generation
    kill_to_recovery(h);finish_full_recovery(h)
    assert e.camp_session is camp and e.sender is sender and e.cancel_generation==generation
    assert not e.active and not e.target_ready
    h.append('Orc fixture scowls at you, ready to attack -- looks like quite a gamble. (Lvl: 5)')
    repeat_tick(h)
    assert camp.phase=='fight'
    h.append('You have slain orc fixture!');repeat_tick(h)
    assert camp.kills==2 and camp.round_number==2
    killed_at=camp.killed_at
    h.append('You have slain orc fixture!');repeat_tick(h)
    assert camp.kills==2 and camp.killed_at==killed_at
    e.stop_action('F9');before=list(h.commands);repeat_tick(h)
    assert h.commands==before and not e.sender.held


@pytest.mark.parametrize('h',[True],indirect=True)
def test_long_recovery_uses_one_sit_toggle_and_observed_resources(h):
    acquire(h);e=h.engine;e.hp=.7;e.mana=.4
    kill_to_recovery(h);repeat_tick(h)
    assert h.commands[-1]=='/stand'
    h.now+=.6;repeat_tick(h);assert h.commands[-1]=='/sit on'
    camp=e.camp_session;assert camp.rest_count==1
    h.now+=35;repeat_tick(h)
    assert camp.running and camp.recovery.phase=='recovering' and not e.active
    e.hp=1.;e.mana=1.
    for _ in range(2):h.now+=.6;repeat_tick(h)
    assert camp.recovery.phase=='stand_settle' and h.commands[-1]=='/stand'
    for _ in range(2):h.now+=.6;repeat_tick(h)
    assert camp.phase=='select' and h.commands.count('/sit on')==1
    assert camp.snapshot()['posture_observed'] is None


@pytest.mark.parametrize('h',[True],indirect=True)
@pytest.mark.parametrize('fault',('stale','missing','same_name_hit','inventory','executable'))
def test_recovery_faults_never_reacquire_or_stand_after_stop(h,fault):
    acquire(h);e=h.engine;e.hp=.7;e.mana=.4;kill_to_recovery(h)
    repeat_tick(h);h.now+=.6;repeat_tick(h)
    before=list(h.commands)
    if fault=='stale':
        h.now+=2.;e.autopilot_tick(h.now)
    elif fault=='missing':
        e.hp=None;repeat_tick(h)
    elif fault=='executable':
        def changed():raise ValueError('changed')
        e._camp_posture.check=changed;repeat_tick(h)
    else:
        h.append('Orc fixture hits YOU for 3 points of damage.' if fault=='same_name_hit'
                 else 'There was no room in your inventory for this item.')
        repeat_tick(h)
    assert e.camp_session is None and e.cancelled and not e.active
    repeat_tick(h);assert h.commands==before


@pytest.mark.parametrize('h',[True],indirect=True)
@pytest.mark.parametrize('phase',('stand_before_sit','sit_once','stand_after_rest'))
@pytest.mark.parametrize('at_release',(False,True))
def test_f9_during_each_recovery_command_leaves_no_continuation(h,phase,at_release):
    acquire(h);e=h.engine;e.hp=.7;e.mana=.4;kill_to_recovery(h)
    camp=e.camp_session;camp.recovery.phase=phase
    command=camp.recovery.command(h.now)
    def write(kind,key,value):
        os.write(h.write_fd,struct.pack('iii',kind,key,value))
        trigger=key==e.sender.codes.KEY_ENTER and value==0 if at_release else value==1
        if trigger:
            e.sender.ui.write=lambda k,c,v:os.write(h.write_fd,struct.pack('iii',k,c,v))
            e.stop_action('F9 in recovery')
    e.sender.ui.write=write
    repeat_tick(h)  # Recovery handles an interrupted command as a stopped session.
    assert h.commands[-1]==command and e.camp_session is None and not e.sender.held and e.cancelled
    assert not any(event=='camp_posture_requested' for event,values in h.traces)
    before=list(h.commands);repeat_tick(h);assert h.commands==before


@pytest.mark.parametrize('h',[True],indirect=True)
@pytest.mark.parametrize('order',('kill_first','level_first'))
@pytest.mark.parametrize('level',(8,20))
def test_level_up_and_kill_preserve_current_bar_and_stop_at_twenty(h,order,level):
    acquire(h);e=h.engine;rotation=e.rotation;profile=e.profile;camp=e.camp_session
    kill='You have slain orc fixture!';ding=f'You have gained a level! Welcome to level {level}!'
    for body in ((kill,ding) if order=='kill_first' else (ding,kill)):h.append(body)
    repeat_tick(h)
    assert camp.kills==1 and camp.phase=='loot_observation' and camp.level==level
    assert e.rotation is rotation and e.profile is profile and e.prepared_level is None
    assert camp.level_source=='client_log' and h.saved_levels==[level]
    h.now+=2.1;repeat_tick(h)
    if level==20:
        assert e.camp_session is None and 'Target level' in e.camp_last_result['reason']
        assert h.commands.count('/target orc_fixture')==1
    else:assert camp.phase=='recovery'


@pytest.mark.parametrize('h',[True],indirect=True)
def test_ding_during_outstanding_con_discard_then_recheck(h):
    acquire(h);e=h.engine;h.now+=4.1;repeat_tick(h)
    assert e.camp_session.phase=='consider'
    h.append('You have gained a level! Welcome to level 8!')
    h.append('Orc fixture scowls at you, ready to attack -- looks like quite a gamble. (Lvl: 5)')
    before=h.commands.count('/cast 3');repeat_tick(h)
    assert e.camp_session.phase=='consider' and not e.active
    assert h.commands.count('/cast 3')==before
    assert any(row['event']=='pre_level_consideration_discarded' for row in e.camp_session.evidence)
    h.append('Orc fixture scowls at you, ready to attack -- looks like quite a gamble. (Lvl: 5)')
    repeat_tick(h);assert e.camp_session.phase=='fight'


@pytest.mark.parametrize('h',[True],indirect=True)
def test_failed_candidate_sweeps_wait_and_stop_after_fifteen_minutes(h):
    e=h.engine;assert e.start_stationary_camp();repeat_tick(h)
    h.append('Consider whom?');repeat_tick(h)
    camp=e.camp_session;assert camp.phase=='waiting_respawn'
    before=list(h.commands);h.now+=29.;repeat_tick(h);assert h.commands==before
    h.now+=1.1;repeat_tick(h)
    assert h.commands.count('/target orc_fixture')==2
    h.append('Consider whom?');repeat_tick(h)
    camp.empty_since=h.now-901
    h.now+=31.;repeat_tick(h)
    h.append('Consider whom?');repeat_tick(h)
    assert e.camp_session is None and 'fifteen minutes' in e.camp_last_result['reason']


@pytest.mark.parametrize('h',[True],indirect=True)
def test_f9_during_last_recovery_permission_never_authorizes_a_key(h):
    acquire(h);e=h.engine;kill_to_recovery(h)
    camp=e.camp_session;e._camp_command='/stand'
    def proposal(now):
        e.stop_action('F9 in last recovery check');return '/stand'
    camp.recovery.command=proposal
    assert not e.allowed() and e.camp_session is None and e.cancelled
    e._camp_command=None
