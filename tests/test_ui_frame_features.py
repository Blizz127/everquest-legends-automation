from dataclasses import replace
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from PIL import Image
import pytest

from test_combat_ui_match import atlas, render
from eql_automation.combat_ui_match import analyze_saved_combat_crop
from eql_automation.owner_ui_observation import capture_focused_ui, sample_focused_ui
from eql_automation.ui_frame_features import analyze_ui_frame, read_focused_ui_features


@pytest.fixture(scope='module')
def gauge_reader():
    pytest.importorskip('numpy')
    path=Path.home()/'.local/share/eql-automation/owner-assist/0.39.10/rotation_core.py'
    if not path.exists():pytest.skip('Retained rotation core unavailable')
    assert sha256(path.read_bytes()).hexdigest()=='9f05379c407f7c9042b38dc7f39c72c0b603bc24d6e754330746f805211a3113'
    spec=importlib.util.spec_from_file_location('retained_frame_gauges',path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module.bar_fraction


@pytest.fixture
def h(tmp_path,gauge_reader):
    h=SimpleNamespace(now=100.,captures=0,focus=True,window=42,process=10,closed=False)
    h.game=tmp_path/'game';h.game.mkdir()
    h.xml=h.game/'player.xml';h.xml.write_text('synthetic source')
    h.a=replace(atlas(),source_sha256=(('player.xml',sha256(h.xml.read_bytes()).hexdigest()),))
    h.frame=Image.new('RGB',(800,600))
    h.frame.paste((200,0,0),(20,30,70,40));h.frame.paste((0,0,200),(20,45,120,55))
    h.frame.paste(render(h.a),(20,65))
    h.rects={'PlayerWindow':(10,20,140,90),'Player_HP':(20,30,120,40),
             'Player_Mana':(20,45,120,55),'PW_CombatStateAnim':(20,65,26,73)}
    def rect(name):
        box=h.rects.get(name)
        return None if box is None else SimpleNamespace(x=box[0],y=box[1],w=box[2]-box[0],h=box[3]-box[1])
    h.layout=SimpleNamespace(sources={'PW_CombatStateAnim':h.xml},skin='fixture',ui_scale=1,
        window=rect,control=lambda window,control:rect(control))
    h.load_hook=lambda:None
    def layout(*a,**kw):h.load_hook();return h.layout
    def capture():h.captures+=1;return h.frame.copy()
    h.gate=SimpleNamespace(windows=lambda:[SimpleNamespace(id=h.window)],
        focused_window=lambda:SimpleNamespace(id=h.window) if h.focus else None,
        game_session=lambda:{'pid':h.process,'start_ticks':'100'},capture=capture,
        close=lambda:pytest.fail('Borrowed gate closed'),
        refresh_grabs=lambda:pytest.fail('Read-only sampler grabbed input'))
    h.args=dict(gate=h.gate,layout_loader=layout,game=h.game,character='Test',server='private',clock=lambda:h.now)
    h.reader=gauge_reader
    h.read=lambda **kw:read_focused_ui_features(**h.args,atlas=h.a,gauge_reader=h.reader,**kw)
    return h


def test_single_frame_uses_actual_retained_gauges_and_no_file_round_trip(h,monkeypatch):
    monkeypatch.setattr(Image.Image,'save',lambda *a,**k:pytest.fail('Feature reader wrote an image'))
    result=h.read()
    assert h.captures==1 and result['gauges']['hp']['fraction_candidate']==.5
    assert result['gauges']['mana']['fraction_candidate']==1
    assert result['combat']['ranked_candidates'][0]['animation']=='A_PWCSStanding'
    assert result['chat_state']==result['target_state']=='unknown'
    assert result['selected_combat_state'] is None and not result['player_presence_verified']
    assert not any(result[key] for key in ('game_input_sent','input_authorized','automatic_healing_allowed','g2_safety_flags_provided'))
    assert sorted(p.name for p in h.game.iterdir())==['player.xml']


def test_saved_capture_and_memory_reader_rank_identical_pixels(h,tmp_path):
    result=h.read()
    root=tmp_path/'private'
    path=capture_focused_ui(**h.args,label='test',output=root,private_root=root)
    saved=analyze_saved_combat_crop(path/'metadata.json',
        metadata_sha256=sha256((path/'metadata.json').read_bytes()).hexdigest(),atlas=h.a)
    assert saved['ranked_candidates']==result['combat']['ranked_candidates']
    meta=json.loads((path/'metadata.json').read_text())
    assert meta['frame_rgb_sha256']==result['frame_rgb_sha256'] and 'MainChat' not in meta['crops']
    assert saved['child_pixels_match_saved_parent'] is True


def test_empty_or_too_small_gauges_remain_unknown(h):
    h.frame.paste((0,0,0),h.rects['Player_HP'])
    h.rects['Player_Mana']=(20,45,120,48)
    result=h.read()
    assert result['gauges']['hp']['fraction_candidate'] is None
    assert result['gauges']['mana']['fraction_candidate'] is None
    assert result['target_state']=='unknown' and not result['player_presence_verified']


@pytest.mark.parametrize('box',[None,(799,590,820,620)])
def test_missing_or_offscreen_combat_is_unknown_without_losing_gauges(h,box):
    h.rects['PW_CombatStateAnim']=box
    result=h.read()
    assert result['combat'] is None and result['gauges']['hp']['fraction_candidate']==.5


@pytest.mark.parametrize('change',['pixels','xml','skin'])
def test_changed_sample_binding_refuses(h,change):
    sample=sample_focused_ui(**h.args)
    if change=='pixels':sample.image.putpixel((0,0),(2,3,4))
    elif change=='xml':h.a=replace(h.a,source_sha256=(('player.xml','e'*64),))
    else:h.a=replace(h.a,saved_skin='different')
    with pytest.raises(ValueError):analyze_ui_frame(sample,atlas=h.a,gauge_reader=h.reader,clock=lambda:h.now)


@pytest.mark.parametrize('change',['focus','window','process','source','cancel'])
def test_changed_state_during_feature_reading_does_not_return_result(h,change):
    original=h.reader
    def read(image,channel):
        if change=='focus':h.focus=False
        elif change=='window':h.window+=1
        elif change=='process':h.process+=1
        elif change=='source':h.xml.write_text('changed')
        else:raise RuntimeError('owner cancellation')
        return original(image,channel)
    h.reader=read
    with pytest.raises(RuntimeError):h.read()


def test_sampling_budget_includes_layout_and_preserves_capture_age(h):
    h.load_hook=lambda:setattr(h,'now',h.now+.2)
    result=h.read()
    assert result['total_seconds']==pytest.approx(.2)
    assert result['frame_age_seconds']==pytest.approx(.2)
    assert not result['within_100ms_sample_budget']
    assert result['sample_started_at']==100. and result['capture_started_at']==100.


def test_focus_loss_during_layout_refuses_before_feature_reader(h):
    h.load_hook=lambda:setattr(h,'focus',False)
    h.reader=lambda *a:pytest.fail('Features read after lost focus')
    with pytest.raises(RuntimeError,match='layout'):h.read()


def test_mutating_frame_inside_gauge_reader_is_detected(h):
    sample=sample_focused_ui(**h.args)
    def mutate(image,channel):sample.image.putpixel((0,0),(3,4,5));return .5
    with pytest.raises(ValueError,match='changed'):analyze_ui_frame(sample,atlas=h.a,gauge_reader=mutate,clock=lambda:h.now)
