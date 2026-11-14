import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_owner_navigation_preflight import Base, forbidden
from eql_automation.owner_position_adapter import make_owner_nov12_engine, POSITION_JOB


class PositionBase(Base):
    def chat_input_opened(self):
        self.stop_action('Stopped because chat input opened. Press F8 after closing chat.')


def setup(tmp_path, **options):
    game = tmp_path/'game'; (game/'Logs').mkdir(parents=True)
    log = game/'Logs/eqlog_Test_freeport.txt'
    log.write_text('[Sat Nov 14 03:00:00 2026] Your Location is 99, 99, 99\n')
    output = tmp_path/'private'
    now = [100.]; captures = []; hook = [lambda: None]
    def capture(**kwargs):
        captures.append(kwargs)
        assert kwargs['gate'] is e.gate and e.sender is None
        kwargs['still_current'](); hook[0](); kwargs['still_current']()
        dest = output/str(len(captures)); dest.mkdir(parents=True)
        metadata = dict(game_session=e.gate.session.copy(), focused_window_id=e.gate.window.id,
            capture_started_monotonic=now[0], capture_ended_monotonic=now[0],
            game_input_sent=False, chat_crop_included=False, crops={})
        (dest/'metadata.json').write_text(json.dumps(metadata))
        return dest
    e = make_owner_nov12_engine(PositionBase,capture_fn=capture,clock=lambda:now[0],
                               output=output,private_root=output,**options)()
    e.settings.game_dir = str(game)
    def queue():
        e.post(POSITION_JOB); e.handle_job(*e.jobs.get_nowait())
    def append(body='Your Location is 1, 2, 3'):
        with log.open('a') as f: f.write('[Sat Nov 14 03:00:01 2026] '+body+'\n')
    def tick(delta=.025):
        now[0] += delta; e.autopilot_tick(now[0])
    return e,now,captures,hook,output,log,queue,append,tick


def last_result(e):
    return [v for name,v in e.traces if name=='position_observation_result'][-1]


def test_manual_chat_keeps_rotation_stopped_and_collects_on_separate_ticks(tmp_path):
    e,now,captures,hook,output,log,queue,append,tick=setup(tmp_path)
    queue(); tick(); assert not captures
    initial=e.cancel_generation
    for code in (53,28):
        e.keys.add(code); e.chat_input_opened(); tick(); e.keys.clear()
        assert e.position_observation is not None and e.cancelled and not e.active
    assert e.cancel_generation==initial+2
    append();tick();assert e.position_observation['session'].phase=='settling'
    tick(1.);assert not captures
    tick(1.);assert len(captures)==1 and e.position_observation is None
    r=last_result(e);assert r['outcome']=='saved' and not r['game_input_sent'] and not r['movement_authorized']
    data=json.loads((Path(r['output_path'])/'unbound-location.json').read_text())
    assert data['location']['raw_coordinates']==[1,2,3]
    assert not data['location']['zone_binding_verified'] and not data['character_identity_verified']
    assert not data['live_route_accepted'] and e.sender is None


@pytest.mark.parametrize('action',['f9','f11','settings_post','settings_job','level','window','process','exit','fake_chat_reason'])
def test_stop_and_binding_changes_cancel_collection(tmp_path,action):
    e,now,captures,hook,output,log,queue,append,tick=setup(tmp_path);queue();append();tick()
    if action=='f9':e.stop_action('F9')
    elif action=='f11':e.stop_autopilot('F11')
    elif action=='settings_post':e.post('settings',e.settings)
    elif action=='settings_job':e.handle_job('settings',e.settings)
    elif action=='level':e.settings.level+=1
    elif action=='window':e.gate.window.id+=1
    elif action=='process':e.gate.session['start_ticks']='101'
    elif action=='exit':e.stopping=True
    elif action=='fake_chat_reason':e.stop_action('Stopped because chat input opened. Press F8 after closing chat.')
    tick(2)
    assert e.position_observation is None and not captures
    assert last_result(e)['outcome'] in ('cancelled','refused')


@pytest.mark.parametrize('change',['extra','transition','reset','unfocused','timeout','backward'])
def test_bad_log_or_capture_state_refuses_without_using_old_position(tmp_path,change):
    e,now,captures,hook,output,log,queue,append,tick=setup(tmp_path);queue()
    if change=='timeout':tick(61)
    elif change=='backward':tick(-1)
    else:
        append();tick()
        if change=='extra':append()
        elif change=='transition':append('LOADING, PLEASE WAIT...')
        elif change=='reset':log.write_text('')
        elif change=='unfocused':e.gate.focus=False
        tick(2)
    assert not captures and e.position_observation is None
    assert last_result(e)['outcome']=='refused'


@pytest.mark.parametrize('action',['post','f9','process','exception'])
def test_revocation_during_capture_never_saves_a_pair(tmp_path,action):
    e,now,captures,hook,output,log,queue,append,tick=setup(tmp_path);queue();append();tick()
    def change():
        if action=='post':e.post('settings',e.settings)
        elif action=='f9':e.stop_action('F9')
        elif action=='process':e.gate.session['start_ticks']='101'
        else:raise OSError('fixture capture failed')
    hook[0]=change;tick(2)
    assert not list(output.glob('*/unbound-location.json')) and e.position_observation is None
    assert last_result(e)['outcome'] in ('cancelled','refused')


def test_stale_queued_request_and_assist_refuse_before_reading(tmp_path):
    e,now,captures,hook,output,log,queue,append,tick=setup(tmp_path)
    e.post(POSITION_JOB);request=e.jobs.get_nowait();e.stop_action('F9');e.handle_job(*request)
    assert e.position_observation is None
    e.measurement_only=False;queue();assert e.position_observation is None
    e.measurement_only=True;e.sender=SimpleNamespace(held=set(),unfinished=False);queue()
    assert e.position_observation is None and not captures


def test_preflight_and_position_collection_do_not_run_together(tmp_path):
    e,now,captures,hook,output,log,queue,append,tick=setup(tmp_path)
    e.post('nav_preflight_later');e.handle_job(*e.jobs.get_nowait())
    assert e.navigation_preflight is not None
    queue();assert e.navigation_preflight is None and e.position_observation is not None
    e.post('nav_preflight_later');e.handle_job(*e.jobs.get_nowait())
    assert e.position_observation is None and e.navigation_preflight is not None
    e.stop_action('F9'); assert not captures


def test_exit_cancels_without_closing_shared_gate(tmp_path):
    e,now,captures,hook,output,log,queue,append,tick=setup(tmp_path);queue()
    e.gate.close=forbidden
    e.run();assert e.position_observation is None and not captures


@pytest.mark.parametrize('action',['success','failure','f9','settings','process'])
def test_post_capture_analysis_is_one_input_free_step_and_keeps_raw_pair(tmp_path,action):
    calls=[]
    def analyze(dest,**kwargs):
        assert e.sender is None and e.pointer is None
        assert (dest/'unbound-location.json').is_file()
        before=(dest/'unbound-location.json').read_bytes()
        kwargs['still_current']();calls.append(dest)
        if action=='failure':raise ValueError('unsupported source fixture')
        if action=='f9':e.stop_action('F9')
        if action=='settings':e.post('settings',e.settings)
        if action=='process':e.gate.session['start_ticks']='changed'
        kwargs['still_current']()
        assert (dest/'unbound-location.json').read_bytes()==before
        report=dest/'combat-analysis.json';report.write_text('{}');return report
    e,now,captures,hook,output,log,queue,append,tick=setup(tmp_path,analysis_fn=analyze)
    queue();append();tick();tick(2)
    assert len(calls)==1 and len(captures)==1 and e.sender is None
    assert (output/'1/unbound-location.json').is_file()
    analyses=[values for name,values in e.traces if name=='position_analysis_result']
    assert len(analyses)==1 and not analyses[0]['game_input_sent'] and not analyses[0]['movement_authorized']
    assert analyses[0]['outcome']==('saved' if action=='success' else 'unavailable' if action=='failure' else 'cancelled')
    assert last_result(e)['outcome']==('saved' if action in ('success','failure') else 'cancelled' if action=='f9' else 'refused')


def test_immediate_crop_writer_borrows_gate_and_discards_cancelled_capture(tmp_path):
    from eql_automation.owner_ui_observation import capture_focused_ui
    from test_owner_navigation_preflight import Gate
    class Frame:
        width=height=100
        size=(100,100)
        def tobytes(self):return b'synthetic-frame'
        def crop(self,box):return self
        def save(self,path):path.write_bytes(b'synthetic-crop')
    class Layout:
        sources={};skin='fixture';ui_scale=1
        def window(self,name):
            assert name!='MainChat'
            return SimpleNamespace(x=1,y=1,w=10,h=10)
        def control(self,*args):return SimpleNamespace(x=1,y=1,w=5,h=5)
    gate=Gate();gate.close=forbidden;gate.display=SimpleNamespace(close=forbidden)
    gate.capture=lambda:Frame()
    root=tmp_path/'private';state={'cancelled':False}
    def valid():
        if state['cancelled']:raise ValueError('cancelled')
    kwargs=dict(label='test',gate=gate,layout_loader=lambda *a,**k:Layout(),
                game=tmp_path/'game',character='Test',server='freeport',output=root,
                private_root=root,still_current=valid)
    dest=capture_focused_ui(**kwargs)
    metadata=json.loads((dest/'metadata.json').read_text())
    assert not metadata['chat_crop_included'] and 'MainChat' not in metadata['crops']
    assert not metadata['saved_layout_is_live_verified']
    assert all(value=='unknown' for value in metadata['g2_safety_flags'].values())
    before=set(root.iterdir())
    def cancelled_capture():state['cancelled']=True;return Frame()
    gate.capture=cancelled_capture
    with pytest.raises(ValueError,match='cancelled'):capture_focused_ui(**kwargs)
    assert set(root.iterdir())==before
