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
def h(tmp_path, monkeypatch, client):
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
                              candidates_loader=lambda e:(candidate,))
    e = h.engine = E(rotation_core.Settings(game_dir=str(game), character='Probe', server='private', level=7),
                     lambda p:None, lambda *a:None)
    e.selector.close(); e.trace = lambda event, **values:h.traces.append((event,values))
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
