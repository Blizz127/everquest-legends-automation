"""Actual retained engine/source navigation and pipe sender; no device/game input."""
import time
from dataclasses import replace
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
def h(tmp_path, retained, monkeypatch, request):
    import rotation_engine as client
    import rotation_core
    factory = route_fixture.make_owner_route_trial_engine
    prep = SimpleNamespace(catalog=rotation_core.Catalog([
        rotation_core.Spell(200,'Minor Healing',1,255,100,0,100,5,0,1),
        rotation_core.Spell(14,'Strike',1,255,100,0,100,5,0,1)]),
        check=lambda:None,source_sha256={'fixture':'a'*64})
    candidate = NpcCandidate('orc fixture', (5,), 'a'*64, ((1,2),))
    import eql_automation.owner_camp_runtime as camp_runtime
    monkeypatch.setattr(camp_runtime,'observed_candidates',lambda *args,**kwargs:(candidate,))
    def combined(base, **options):
        return make_owner_journey_engine(base, client=client, **options,
            camp_probe_plan_provider=((lambda engine,p:engine._test_camp_probe_provider(p))
                if getattr(request,'param',None)=='level_provider' else None),
            camp_options=dict(
                posture_loader=lambda p:SimpleNamespace(check=lambda:None),
                preparation_catalog_loader=lambda p:prep))
    monkeypatch.setattr(route_fixture,'make_owner_route_trial_engine',combined)
    generator=route_fixture.h.__wrapped__(tmp_path,retained,monkeypatch)
    h=next(generator);e=h.engine
    h.camp_continuation_enabled=getattr(request,'param',None)=='level_provider'
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


def start(h,destination_id=None):
    h.engine.read_log()  # Drain the fixture entry before the explicit travel start.
    if destination_id is not None:
        e=h.engine;e.post(SOURCE_JOB,dict(open_flat_clear=True,destination_id=destination_id))
        return e.handle_job(*e.jobs.get_nowait())
    return route_start(h)


@pytest.mark.parametrize('destination_id', ('north-wall','newbie-hills'))
def test_real_source_arrival_releases_navigation_then_starts_same_sender_camp(h,monkeypatch,destination_id):
    from eql_automation.source_destinations import destination_spec
    zone=destination_spec(destination_id).zone
    assets=configure(h,monkeypatch,destination_id=destination_id);e=h.engine
    from eql_automation.source_observer import SourceItineraryObserver
    source_check=SourceItineraryObserver.check
    def no_observer_resume(observer):
        assert e.journey is None or e.journey.phase!='camp','Old movement observer was resumed'
        return source_check(observer)
    monkeypatch.setattr(SourceItineraryObserver,'check',no_observer_resume)
    import eql_automation.owner_camp_runtime as camp_runtime
    fallback=NpcCandidate('orc fixture',(5,),'a'*64,((1,2),),'retained_owner_history','b'*64)
    monkeypatch.setattr(camp_runtime,'observed_candidates',lambda *a,**k:())
    loads=[]
    def history(server,zone,**kwargs):
        loads.append((server,zone));return (fallback,)
    monkeypatch.setattr(camp_runtime,'load_owner_candidates',history)
    assert not navigation_active(e) and not e.measurement_only
    captured=[];capture=e._capture_trial_continuation
    def keep(p):
        token=capture(p)
        if token:captured.append(token)
        return token
    e._capture_trial_continuation=keep
    start(h,destination_id);assert navigation_active(e)
    h.due_trial();record=finish(h,timeout=80.)
    assert record is not None and record['outcome']=='arrived','\n'.join(h.notices)
    assert record['continuation']['camp_started'],h.notices
    assert record['destination']['destination_id']==record['continuation']['destination_id']==destination_id
    assert record['destination']['guide_sha256']==record['continuation']['destination']['guide_sha256']
    assert captured[0].destination is assets and captured[0].destination_id==destination_id
    assert e.journey_last_result['destination_id']==e.journey.destination_id==destination_id
    assert e.camp_session is not None and e.journey.phase=='camp'
    assert e.zone==e.camp_session.zone==zone
    assert loads==[(e.settings.server,zone)]
    assert e.camp_session.candidates==(fallback,)
    assert e.sender is h.sender and not e.sender.held and not h.observer_closed
    assert e.journey.camp_motion.observer is captured[0].pending['observer']
    assert e.journey.camp_motion.snapshot()['movement_authorized'] is False
    import json
    basis=json.loads(captured[0].motion_basis)
    assert basis['arrival_heading_estimate']==captured[0].runtime.ledger.pose.heading
    assert e.live_zone_tracker.lease is None and not navigation_active(e)
    checkpoint=captured[0].floor_checkpoint;ledger=captured[0].runtime.ledger
    assert e.journey.arrival_floor is checkpoint and e.journey.camp_motion.floor is checkpoint
    assert checkpoint._chain is not ledger.chain and checkpoint._reference is ledger.reference
    assert checkpoint._calibration is ledger.observer.calibration
    assert checkpoint._chain.previous.proof_sha256==ledger.chain.previous.proof_sha256
    assert e.live_zone_tracker.reader.latest is None
    checkpoint.check()
    assert e.camp_session.preparation_due and not record['real_client_accepted']
    h.tick();assert e.camp_session.phase=='preparing'
    h.tick();assert h.commands==['/outputfile spellbook eql-rotation-spellbook.txt']
    e.stop_action('F9');before=list(h.commands);h.tick();assert h.commands==before
    assert h.observer_closed
    assert not checkpoint.valid and checkpoint._chain is None


@pytest.mark.parametrize('destination_id', ('throne-stair-landing','newbie-hills-stop'))
def test_movement_destination_needs_no_npc_history_and_stops_without_camp(h,monkeypatch,destination_id):
    configure(h,monkeypatch,destination_id=destination_id);e=h.engine
    import eql_automation.owner_camp_runtime as camp_runtime
    def no_candidates(*args,**kwargs):raise AssertionError('Movement test must not load camp targets')
    monkeypatch.setattr(camp_runtime,'observed_candidates',no_candidates)
    monkeypatch.setattr(camp_runtime,'load_owner_candidates',no_candidates)
    start(h,destination_id);h.due_trial();record=finish(h,timeout=80.)
    assert record is not None and record['outcome']=='arrived',h.notices
    assert record['continuation']['phase']=='arrived' and not record['continuation']['camp_started']
    assert e.journey is None and e.camp_session is None and e.cancelled
    assert e.live_zone_tracker.lease is None and h.observer_closed and not h.sender.held
    assert not h.commands
    count=len(h.events);h.tick();h.drain();assert len(h.events)==count


def test_movement_destination_cannot_request_automatic_camp_continuation(h,monkeypatch):
    configure(h,monkeypatch,destination_id='throne-stair-landing');e=h.engine;e.read_log()
    e.post(SOURCE_JOB,dict(open_flat_clear=True,destination_id='throne-stair-landing',continue_camps=True))
    e.handle_job(*e.jobs.get_nowait())
    assert e.journey is None and e.route_trial is None and e.camp_session is None
    assert any('camp continuation is unavailable' in str(s) for s in h.notices)


def test_butcher_camp_without_observed_npc_history_sends_no_input(h,monkeypatch):
    import eql_automation.owner_camp_runtime as camp_runtime
    configure(h,monkeypatch,destination_id='newbie-hills')
    monkeypatch.setattr(camp_runtime,'observed_candidates',lambda *a,**k:())
    monkeypatch.setattr(camp_runtime,'load_owner_candidates',lambda *a,**k:())
    start(h,'newbie-hills');h.tick();h.drain()
    assert not h.events and not h.commands and not h.sender.held
    assert h.engine.supervised_motion is None
    assert h.engine.camp_session is None and h.engine.route_trial is None
    assert any('No observed NPC' in str(s) for s in h.notices)


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


@pytest.mark.parametrize('where',('lease_release','gauges','start_stop','monitor_transfer','floor_capture'))
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
    elif where=='floor_capture':
        import eql_automation.owner_journey_runtime as runtime
        factory=runtime.CampFloorCheckpoint;checkpoints=[]
        def capture(ledger):
            checkpoint=factory(ledger);checkpoints.append(checkpoint);stop();return checkpoint
        monkeypatch.setattr(runtime,'CampFloorCheckpoint',capture)
    else:
        # F9 wins even after the monitor changes ownership, before the commit.
        original=e._retain_camp_input
        def retain(token):
            original(token);stop()
        e._retain_camp_input=retain
    start(h);h.due_trial();record=finish(h,timeout=80.)
    assert fired,(record,h.notices)
    assert e.camp_session is None and e.cancelled and not e.active
    assert not h.commands and not h.sender.held and e.live_zone_tracker.lease is None
    if where=='floor_capture':assert not checkpoints[0].valid and checkpoints[0]._chain is None


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


@pytest.mark.parametrize('stop_after_f8', [False, True])
def test_f8_during_hotbutton_input_wait_releases_before_assist(h, stop_after_f8):
    e = h.engine
    e.prepared = True; e.prepared_level = 7
    h.start()
    h.sample_transform = lambda sample: replace(sample, activity=True)
    h.due()
    assert e.hotkey_test is not None and not e.hotkey_test['fired']
    e.handle_job('arm', e.cancel_generation)
    assert e._journey_assist is not None and not e.active
    if stop_after_f8:
        e.stop_action('F9 after F8 during input wait')
    h.sample_transform = lambda sample: sample
    h.tick(); h.drain()
    assert e.hotkey_test is None and h.observer_closed
    assert e._journey_assist is None and e.active is (not stop_after_f8)
    assert not h.events and not h.commands and not h.sender.held


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


def test_queued_destination_is_copied_before_gui_or_caller_changes(h,monkeypatch):
    assets=configure(h,monkeypatch,destination_id='north-wall');e=h.engine;e.read_log()
    declaration=dict(open_flat_clear=True,destination_id='north-wall')
    e.post(SOURCE_JOB,declaration);declaration['destination_id']='slave-mines'
    queued=e.jobs.get_nowait();epoch=queued[1]['epoch'];generation=queued[1]['generation']
    e.handle_job(*queued)
    assert e.journey.destination_id=='north-wall' and e.journey.destination_assets is assets
    assert e.supervised_motion['declaration']=={'open_flat_clear':True}
    assert e.supervised_motion['epoch']==epoch and e.cancel_generation==generation
    assert e.supervised_motion['continuation']['destination'] is assets and not h.events


@pytest.mark.parametrize('identifier',('unknown',None,[],7))
def test_invalid_destination_does_not_load_or_send_input(h,monkeypatch,identifier):
    configure(h,monkeypatch);e=h.engine;called=[]
    h.source_loading[0]=lambda:called.append(True)
    start(h,identifier) if identifier is not None else (
        e.read_log(),e.post(SOURCE_JOB,dict(open_flat_clear=True,destination_id=None)),
        e.handle_job(*e.jobs.get_nowait()))
    assert not called and e.journey is None and e.supervised_motion is None and e.route_trial is None
    assert not h.events and not h.commands


def test_known_destination_cannot_fall_back_to_another_guides_assets(h,monkeypatch):
    configure(h,monkeypatch);start(h,'north-wall')
    assert h.engine.journey is None and h.engine.supervised_motion is None and not h.events
    assert any('queued choice' in str(value) for value in h.notices)


@pytest.mark.parametrize('changed',('id','assets'))
def test_destination_change_after_arrival_capture_never_hands_off(h,monkeypatch,changed):
    from eql_automation.owner_zone_tracker import ZoneReaderLease
    assets=configure(h,monkeypatch,destination_id='north-wall');e=h.engine;fired=[]
    original=ZoneReaderLease.release
    def release(lease):
        result=original(lease)
        if e.journey is not None and e.journey.phase=='handoff' and not fired:
            fired.append(True)
            if changed=='id':e.journey.destination_id='slave-mines'
            else:
                # The actual token retains the completed route's original evidence.
                token=e._captured_for_test
                token.pending['continuation']['destination']=replace(assets,destination_id='slave-mines')
        return result
    capture=e._capture_trial_continuation
    def keep(p):
        token=capture(p);e._captured_for_test=token;return token
    e._capture_trial_continuation=keep;monkeypatch.setattr(ZoneReaderLease,'release',release)
    start(h,'north-wall');h.due_trial();record=finish(h,timeout=80.)
    assert fired and e.camp_session is None and e.journey is None
    assert record['destination']['destination_id']=='north-wall'
    assert not record['continuation'] and not h.commands and not h.sender.held
    assert e.live_zone_tracker.lease is None and e.journey_last_result['destination_id']=='north-wall'
