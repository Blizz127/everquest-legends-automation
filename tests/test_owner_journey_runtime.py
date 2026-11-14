"""Actual retained engine/source navigation and pipe sender; no device/game input."""
import time
from types import SimpleNamespace

import pytest

from eql_automation.camp_session import NpcCandidate
from eql_automation.navigation_phase import navigation_active
from eql_automation.owner_journey_runtime import make_owner_journey_engine
from eql_automation.owner_route_trial import SOURCE_JOB
from test_motion_collection import retained
import test_owner_route_trial as route_fixture
from test_owner_source_travel import configure, start as route_start
from test_owner_route_trial import finish


@pytest.fixture
def h(tmp_path, retained, monkeypatch):
    import rotation_engine as client
    import rotation_core
    factory = route_fixture.make_owner_route_trial_engine
    prep = SimpleNamespace(catalog=rotation_core.Catalog([
        rotation_core.Spell(200,'Minor Healing',1,255,100,0,100,5,0,1),
        rotation_core.Spell(14,'Strike',1,255,100,0,100,5,0,1)]),
        check=lambda:None,source_sha256={'fixture':'a'*64})
    candidate = NpcCandidate('orc fixture', (5,), 'a'*64, ((1,2),))
    def combined(base, **options):
        return make_owner_journey_engine(base, client=client, **options,
            camp_options=dict(candidates_loader=lambda e:(candidate,),
                posture_loader=lambda p:SimpleNamespace(check=lambda:None),
                preparation_catalog_loader=lambda p:prep))
    monkeypatch.setattr(route_fixture,'make_owner_route_trial_engine',combined)
    generator=route_fixture.h.__wrapped__(tmp_path,retained,monkeypatch)
    h=next(generator);e=h.engine
    e.measurement_only=False;e.settings.level=7
    del e.send;del e.read_log
    e.tail=e.make_tail();e.tail.poll();e.zone='crushbone'
    e.gate.read_gauges=lambda *a:(1.,1.)
    e.stop_keys_held=lambda:False
    e.prepared_state_path=tmp_path/'prepared.json'
    e.settings.save=lambda:None
    h.commands=[]
    command=e.sender.command
    def record(text):h.commands.append(text);return command(text)
    e.sender.command=record
    yield h
    e.stop_action('test cleanup');generator.close()


def start(h):
    h.engine.read_log()  # Drain the fixture entry before the explicit travel start.
    return route_start(h)


def test_real_source_arrival_releases_navigation_then_starts_same_sender_camp(h,monkeypatch):
    configure(h,monkeypatch);e=h.engine
    assert not navigation_active(e) and not e.measurement_only
    start(h);assert navigation_active(e)
    h.due_trial();record=finish(h,timeout=80.)
    assert record is not None and record['outcome']=='arrived','\n'.join(h.notices)
    assert record['continuation']['camp_started'],h.notices
    assert e.camp_session is not None and e.journey.phase=='camp'
    assert e.sender is h.sender and not e.sender.held and h.observer_closed
    assert e.live_zone_tracker.lease is None and not navigation_active(e)
    assert e.camp_session.preparation_due and not record['real_client_accepted']
    h.tick();assert e.camp_session.phase=='preparing'
    h.tick();assert h.commands==['/outputfile spellbook eql-rotation-spellbook.txt']
    e.stop_action('F9');before=list(h.commands);h.tick();assert h.commands==before


@pytest.mark.parametrize('stop',('movement','location'))
def test_f9_never_hands_off_and_late_f11_release_cannot_restart(h,monkeypatch,stop):
    configure(h,monkeypatch,stop=stop);e=h.engine
    start(h);h.due_trial();record=finish(h,timeout=80.)
    assert record['outcome']=='stopped' and e.camp_session is None
    # Native F11 release may be queued AFTER the observer already stopped DOWN.
    e.stop_autopilot('GUI Stop while F11 still held')
    e.autopilot_hotkey_released()
    assert e.jobs.empty()
    assert not e.camp_session and not h.commands and not navigation_active(e)
    assert not h.sender.held and e.live_zone_tracker.lease is None


@pytest.mark.parametrize('where',('lease_release','gauges','start_stop','observer_close'))
def test_late_f9_during_arrival_or_cleanup_never_arms_camp(h,monkeypatch,where):
    from eql_automation.owner_zone_tracker import ZoneReaderLease
    configure(h,monkeypatch);e=h.engine;fired=[]
    def stop():
        if not fired:fired.append(True);e.stop_action('F9 during handoff')
    if where=='lease_release':
        original=ZoneReaderLease.release
        def release(lease):
            result=original(lease)
            if e.journey is not None and e.journey.phase=='handoff':stop()
            return result
        monkeypatch.setattr(ZoneReaderLease,'release',release)
    elif where=='gauges':e.gate.read_gauges=lambda *a:(stop() or (1.,1.))
    elif where=='start_stop':
        emit=e.emit
        def notice(text=None):
            if text and 'Camp starting' in text:stop()
            return emit(text)
        e.emit=notice
    else:
        # Observer remains open until the handoff releases its ownership.
        original=e._capture_trial_continuation
        def capture(p):
            token=original(p)
            if token:
                close=p['observer'].close
                def end():close();stop()
                p['observer'].close=end
            return token
        e._capture_trial_continuation=capture
    start(h);h.due_trial();record=finish(h,timeout=80.)
    assert fired,(record,h.notices)
    assert e.camp_session is None and e.cancelled and not e.active
    assert not h.commands and not h.sender.held and e.live_zone_tracker.lease is None


def test_f8_during_navigation_arms_only_after_cleanup_and_f9_defeats_it(h,monkeypatch):
    configure(h,monkeypatch);e=h.engine
    start(h);assert e.supervised_motion is not None
    e.handle_job('arm',e.cancel_generation)
    assert e._journey_assist is not None and not e.active
    e.stop_action('F9 after F8')
    finish(h,timeout=5.)
    assert not e.active and e._journey_assist is None and not h.sender.held


def test_assist_does_not_admit_navigation_without_explicit_job(h):
    e=h.engine
    assert not e._route_idle() and not e._motion_idle() and not e._hotkey_idle()
    e.handle_job(SOURCE_JOB,{'generation':e.cancel_generation-1,'settings':()})
    assert e.journey is None and e.supervised_motion is None and not h.commands


def test_same_helper_runs_hotbutton_setup_without_enabling_assist_movement(h,monkeypatch):
    from test_route_step_sender import after_down
    from test_owner_location_hotkey_test import finish as finish_hotkey
    after_down(monkeypatch,h.append)
    h.start();assert navigation_active(h.engine)
    h.due();record=finish_hotkey(h)
    assert record['outcome']=='observed_location',h.notices
    assert not navigation_active(h.engine) and h.engine.cancelled and not h.sender.held
    assert not any(kind==1 and code in {103,105,106} and value==1 for kind,code,value in h.events)


def test_death_during_countdown_stops_without_camp_or_native_autopilot(h,monkeypatch):
    configure(h,monkeypatch);e=h.engine
    start(h);h.append('You have been slain by orc fixture!');e.read_log()
    finish(h,timeout=5.)
    assert not e.camp_session and not e.active and e.cancelled and not h.commands


def test_quit_during_navigation_requests_worker_exit_after_release(h,monkeypatch):
    configure(h,monkeypatch);e=h.engine
    start(h);e.handle_job('quit',None)
    finish(h,timeout=5.)
    assert e.stopping and not e.camp_session and not h.sender.held


def test_f8_after_release_enters_existing_assist_without_target_or_movement_input(h,monkeypatch):
    configure(h,monkeypatch);e=h.engine
    e.prepared=True;e.prepared_level=7
    start(h);e.handle_job('arm',e.cancel_generation)
    assert not e.active
    finish(h,timeout=5.)
    assert e.active and not navigation_active(e) and not h.commands and not h.sender.held


def test_packaged_native_f11_release_survives_gui_stop_and_keeps_deduplication(h,tmp_path,monkeypatch):
    import importlib.util
    import sys
    from hashlib import sha256
    from pathlib import Path
    packaged=Path.home()/'.local/share/eql-automation/owner-assist/0.39.25'
    native=packaged/'rotation_engine.py'
    assert sha256(native.read_bytes()).hexdigest()=='d4925d8250e69d6e631f64b4c7eea115b34473aef90d86c9838c045ad355309e'
    spec=importlib.util.spec_from_file_location('journey_native_test',native)
    module=importlib.util.module_from_spec(spec);monkeypatch.setitem(sys.modules,spec.name,module);spec.loader.exec_module(module)
    e=h.engine;code=h.sender.codes.KEY_F11
    monkeypatch.setitem(sys.modules,'evdev',SimpleNamespace(ecodes=h.sender.codes))
    events=[SimpleNamespace(type=1,code=code,value=value) for value in (1,0)]
    device=SimpleNamespace(read=lambda:list(events))
    e.selector=SimpleNamespace(select=lambda **kw:[(SimpleNamespace(fileobj=device),None)])
    e._journey_f11_release=True
    e.stop_autopilot('GUI stop during an outstanding F11 press')
    assert e._journey_f11_release
    module.Engine.input_events(e)
    assert not e._journey_f11_release and e.jobs.empty() and code not in e.keys
    generation=e.cancel_generation
    events[:]=[SimpleNamespace(type=1,code=code,value=0)]
    module.Engine.input_events(e)  # Duplicate release retains the native debounce.
    assert e.cancel_generation==generation and e.jobs.empty()
