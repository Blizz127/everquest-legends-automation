"""Retained Engine tick integration; copied code, fixture logs and pipe input."""
from dataclasses import replace
from datetime import datetime, timedelta
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import pytest

from eql_automation.location_log import LocationLogReader
from eql_automation.motion_collection import (CommandReceipt, MotionExperimentDriver,
    MotionExperimentSession, ReleasedPulse, CollectionStopped)
from eql_automation.owner_motion_adapter import make_motion_collection_engine
from eql_automation.owner_position_adapter import make_owner_nov12_engine
from eql_automation.uinput_watchdog import PulseReceipt, PulseSelection, selected_key_pulse_receipt, _EVENT

HELPER = Path.home()/'.local/share/eql-automation/owner-assist/0.39.10'
PINS = {'rotation_engine.py':'48c6dd7cf6676284d8aafc1221a66ad71f1861cca82f6c9af56446504599848b',
        'rotation_core.py':'9f05379c407f7c9042b38dc7f39c72c0b603bc24d6e754330746f805211a3113',
        'autopilot.py':'24fb6f091025c09a968b4eb20e303db32f2158eebe38a67fb6ba54d6f393184f',
        'navigation.py':'69dbc6472447942cc30dbe592a6e1cf02998c0a0b8811a8bb59672655dc4049e'}


@pytest.fixture(scope='module')
def retained():
    pytest.importorskip('numpy')
    if not HELPER.exists(): pytest.skip('Requires retained owner helper')
    for name, pin in PINS.items(): assert sha256((HELPER/name).read_bytes()).hexdigest()==pin
    sys.path.insert(0,str(HELPER))
    import rotation_engine, rotation_core, navigation
    return rotation_engine.Engine, rotation_core.Settings, navigation


def setup(tmp_path, retained, *, real=False):
    Engine, Settings, legacy = retained
    h = SimpleNamespace(now=100., point=(0.,0.,0.), heading=350., speed=30., latency=.03,
        real=real, pulses=[], commands=[], traces=[], notices=[], mode='measurement', window=42)
    h.clock = time.monotonic if real else lambda:h.now
    began = h.clock()
    wall = datetime.now() if real else datetime(2026,11,14,6,0)
    h.wall = lambda:wall+timedelta(seconds=h.clock()-began)
    game=tmp_path/'game';(game/'Logs').mkdir(parents=True)
    h.log = game/'Logs/eqlog_Probe_private.txt'; h.log.touch()
    zones = tmp_path/'ZoneNames.txt'; zones.write_text('1^Fixture Zone^0^0\n')
    def append(body):
        with h.log.open('a') as f: f.write(h.wall().strftime('[%a %b %d %H:%M:%S %Y] ')+body+'\n')
    h.append=append
    reader=LocationLogReader(h.log,zones,expected_character='Probe',expected_server='private')
    append('You have entered Fixture Zone.');reader.poll(now=h.clock())
    base = make_owner_nov12_engine(Engine,clock=h.clock)
    e = make_motion_collection_engine(base,output_root=tmp_path/'saved')(Settings(game_dir=str(game),character='Probe',server='private'),
        lambda *_:None,lambda *_:None,measurement_only=True)
    e.selector.close()
    e.trace=lambda event,**values:h.traces.append((event,values))
    e.emit=lambda text=None:h.notices.append(text)
    def forbidden(*a,**kw): raise AssertionError('Unexpected real sender/capture/legacy movement')
    e.send=e.hold=e.ensure_sender=e.ensure_pointer=forbidden
    h.engine=e
    session=MotionExperimentSession(reader,zone_id=1,zone_display_name='Fixture Zone',zone_short_name='fixture',
        generation=e.cancel_generation,generation_reader=lambda:e.cancel_generation,mode_reader=lambda:h.mode,
        binding_reader=lambda:(h.window,e.settings.character,e.settings.server,e.settings.level),
        record_id='synthetic-engine-ticks',horizontal_error=.01,legacy=legacy,clock=h.clock,local_wall_clock=h.wall,
        stop_lock=e.g0_stop_lock)
    h.session=session
    h.command_hook=h.release_hook=lambda:None
    def location(request):
        start=h.clock();h.commands.append(request)
        append('Your Location is '+', '.join(f'{v:.2f}' for v in h.point))
        h.command_hook()
        # A reply during Enter handling must not be consumed before the
        # callback can report its command completion.
        e.autopilot_tick(h.clock())
        return CommandReceipt(start,h.clock())
    def pulse(request):
        probe=request.probe;h.pulses.append(request)
        if real:
            def select():
                session._check()  # Scene/geometry are explicitly synthetic.
                return PulseSelection(probe.key_code,probe.seconds,request.expires_at)
            receipt=selected_key_pulse_receipt(h.fd,select,go_lock=session.lock,
                pump=lambda:e.autopilot_tick(h.clock()))
        else:
            start=h.clock()
            receipt=PulseReceipt(probe.key_code,probe.seconds,start,start+.0002,
                start+.0002+probe.seconds,start+.0004+probe.seconds,'elapsed')
            h.now=receipt.up_completed_at
            e.autopilot_tick(h.clock())
        held=((receipt.up_started_at-receipt.down_completed_at)+receipt.maximum_held_seconds)/2
        if probe.key=='forward':
            rad=math.radians(h.heading)
            h.point=(h.point[0]+math.cos(rad)*h.speed*held,h.point[1]+math.sin(rad)*h.speed*held,0.)
        else:
            h.heading=(h.heading+(-1 if probe.key=='right' else 1)*170*max(0.,held-h.latency))%360
        h.release_hook()
        return ReleasedPulse(receipt,h.clock())
    h.location=location;h.pulse=pulse
    h.driver=MotionExperimentDriver(session,request_location=location,run_pulse=pulse)
    e.attach_motion_collection(h.driver)
    def tick():
        if real:time.sleep(.01)
        else:h.now+=.025
        e.autopilot_tick(h.clock())
    h.tick=tick
    def run(limit=1600):
        for _ in range(limit):
            if e.motion_collection_driver is None:break
            tick()
        assert e.motion_collection_driver is None, (session.phase,len(session.pairs),h.clock())
        return session.snapshot()
    h.run=run
    return h


def test_actual_engine_tick_collects_exact_finite_experiment(tmp_path,retained):
    h=setup(tmp_path,retained);record=h.run()
    assert record['outcome']=='complete' and len(record['pairs'])==8
    assert len(record['command_requests'])==16 and len(record['receipts'])==7
    assert len(record['raw_fixes'])==16 and len(record['final_releases'])==7
    assert [r['index'] for r in record['release_attempts']]==list(range(7))
    estimate=record['estimate']
    assert estimate['conditional_intervals']['turn_rate'][0] <=170<=estimate['conditional_intervals']['turn_rate'][1]
    assert not record['input_authorized'] and not record['request_correlation_verified']
    assert not record['real_client_accepted'] and h.engine.sender is None
    h.tick();assert len(h.pulses)==7
    assert len([x for x in h.traces if x[0]=='motion_collection_result'])==1
    assert h.engine.last_motion_collection_path.is_file()
    assert json.loads(h.engine.last_motion_collection_path.read_text())['outcome']=='complete'


@pytest.mark.parametrize('change',['F9','F11','post','settings','process','assist','off','exit','recording','recovery'])
def test_cancel_mid_collection_never_requests_another_operation(tmp_path,retained,change):
    h=setup(tmp_path,retained)
    while not h.pulses:h.tick()
    pulses,commands=len(h.pulses),len(h.commands)
    if change=='F9':h.engine.stop_action('F9')
    elif change=='F11':h.engine.stop_autopilot('F11')
    elif change=='post':h.engine.post('settings',object())
    elif change=='settings':h.engine.settings.level+=1
    elif change=='process':h.window+=1
    elif change in ('assist','off'):h.mode=change
    elif change=='recording':h.engine.recorder=object()
    elif change=='recovery':h.engine.command_recovery_pending=True
    else:h.engine.stopping=True
    record=h.run()
    assert record['outcome']=='stopped' and record['estimate'] is None
    assert len(h.pulses)==pulses and len(h.commands)==commands


def test_cancellation_after_final_up_preserves_attempted_receipt(tmp_path,retained):
    h=setup(tmp_path,retained)
    h.release_hook=lambda:h.engine.stop_action('F9 after UP')
    record=h.run()
    assert record['outcome']=='stopped' and not record['receipts']
    assert len(record['release_attempts'])==1
    assert record['release_attempts'][0]['reported']['receipt']['completion']=='elapsed'
    result=[v for event,v in h.traces if event=='motion_collection_result'][-1]
    assert result['record']['release_attempts']==record['release_attempts']


@pytest.mark.parametrize('change',['batched','zone','partial','malformed','rotation','consumed'])
def test_invalid_log_stream_stops_before_first_pulse(tmp_path,retained,change):
    h=setup(tmp_path,retained)
    def hook():
        if change=='batched':h.append('Your Location is 0.00, 0.00, 0.00')
        elif change=='zone':h.append('LOADING, PLEASE WAIT...')
        elif change=='partial':
            with h.log.open('a') as f:f.write('incomplete')
        elif change=='malformed':h.append('Your Location is broken')
        elif change=='rotation':
            h.log.rename(h.log.with_suffix('.old'));h.log.touch()
        else:h.session.reader.poll(now=h.clock())
    h.command_hook=hook
    record=h.run()
    assert record['outcome']=='stopped' and not h.pulses


@pytest.mark.parametrize('change',['blocked_forward','ambiguous_short_turn','speed_change','pivot_translation'])
def test_inconclusive_intermediate_motion_stops_without_finishing_sequence(tmp_path,retained,change):
    h=setup(tmp_path,retained)
    if change=='blocked_forward':h.speed=0.
    elif change=='ambiguous_short_turn':h.latency=.08
    elif change=='speed_change':h.release_hook=lambda:setattr(h,'speed',40.)
    else:
        def move():
            if h.pulses[-1].probe.key!='forward':h.point=(h.point[0]+1,h.point[1],h.point[2])
        h.release_hook=move
    record=h.run()
    assert record['outcome']=='stopped'
    assert len(h.pulses)<=3 and len(record['receipts'])==len(h.pulses)


def test_missing_request_reply_expires_without_retry(tmp_path,retained):
    h=setup(tmp_path,retained)
    h.driver.request_location=lambda a:CommandReceipt(h.clock(),h.clock())
    record=h.run()
    assert record['outcome']=='stopped' and 'expired' in record['reason']
    assert len(record['command_requests'])==1 and not h.pulses


def test_historical_zone_does_not_bootstrap_a_session(tmp_path,retained):
    h=setup(tmp_path,retained)
    second=LocationLogReader(h.log,tmp_path/'ZoneNames.txt',expected_character='Probe',expected_server='private')
    with pytest.raises(CollectionStopped,match='Fresh zone/log'):
        MotionExperimentSession(second,zone_id=1,zone_display_name='Fixture Zone',zone_short_name='fixture',
            generation=0,generation_reader=lambda:0,mode_reader=lambda:'measurement',binding_reader=lambda:('x',),
            record_id='no-history',horizontal_error=.01,legacy=retained[2],clock=h.clock,local_wall_clock=h.wall)


@pytest.mark.parametrize('pending',['position_observation','navigation_preflight','jobs'])
def test_composed_helper_refuses_competing_diagnostic_or_pending_job(tmp_path,retained,pending):
    h=setup(tmp_path,retained)
    h.engine.motion_collection_driver=None
    if pending=='jobs':h.engine.post('settings',object())
    else:setattr(h.engine,pending,object())
    with pytest.raises(ValueError):h.engine.attach_motion_collection(h.driver)
    assert not h.pulses and not h.commands


def test_optional_trace_and_failed_save_do_not_lose_partial_evidence(tmp_path,retained):
    h=setup(tmp_path,retained)
    h.engine.trace=lambda *a,**kw:None
    (tmp_path/'saved').write_text('block output directory')
    h.release_hook=lambda:h.engine.stop_action('F9 after UP')
    h.run()
    record=h.engine.last_motion_collection_result
    assert record['outcome']=='stopped' and len(record['release_attempts'])==1
    assert h.engine.last_motion_collection_path is None
    assert 'retained in memory' in h.notices[-1]


def test_real_watchdog_pipe_through_actual_engine_ticks(tmp_path,retained):
    h=setup(tmp_path,retained,real=True)
    rd,h.fd=os.pipe()
    try:record=h.run()
    finally:os.close(h.fd)
    raw=os.read(rd,65536);os.close(rd)
    events=[(kind,key,value) for _,_,kind,key,value in _EVENT.iter_unpack(raw)]
    (tmp_path/'engine-motion-evidence.json').write_text(json.dumps(dict(
        kind='retained-engine-and-real-watchdog-pipe-with-synthetic-positions',
        client_input_sent=False, events=events, record=record,
        retained_source_pins=PINS),indent=2)+'\n')
    count=len(h.pulses)
    assert len(events)==6*count and 1<=count<=7
    assert len([e for e in events if e[0]==1 and e[2]==1])==count
    assert len([e for e in events if e[0]==1 and e[2]==0])==2*count
    if record['outcome']=='complete':
        assert count==7 and len(record['receipts'])==7
    else:
        # Linux scheduling can overrun a child deadline. That is a failed
        # collection, not permission to widen the production hold limit or
        # fabricate a successful calibration. Verify the measured cause and
        # no next pulse after that rejection.
        assert record['outcome']=='stopped' and record['estimate'] is None
        assert 'timing overrun' in record['reason']
        last=record['release_attempts'][-1]['reported']['receipt']
        assert (last['up_completed_at']-last['down_started_at']>.2
                or record['last_checked_monotonic']-last['up_completed_at']>.3)
        assert count==len(record['receipts'])+1
    assert not record['real_client_accepted'] and h.engine.sender is None
