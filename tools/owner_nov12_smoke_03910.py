#!/usr/bin/env python3
"""Actual helper event dispatch with synthetic keys/log/capture; no devices/input."""
from pathlib import Path
from hashlib import sha256
from PIL import Image
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import json


def main():
    from owner_nov12_entry import verify_snapshot
    verify_snapshot(Path(__file__).resolve().parent)
    from evdev import ecodes as codes
    from rotation_core import Settings
    from rotation_engine import Engine
    from eql_automation.owner_position_adapter import make_owner_nov12_engine,POSITION_JOB
    def forbidden(*a,**k):raise AssertionError('Observation attempted input/device/display access')
    now=[100.];events=[];captures=[];traces=[];notices=[]
    class Device:
        def read(self):
            current=events[:];events.clear();return current
    device=Device()
    selector=SimpleNamespace(select=lambda **k:[(SimpleNamespace(fileobj=device),None)] if events else [])
    window=SimpleNamespace(id=42)
    gate=SimpleNamespace(windows=lambda:[window],game_session=lambda:{'pid':10,'start_ticks':'100'},
        focused_window=lambda:window,focused=lambda:True,controls_ready=lambda:True,
        capture=forbidden,close=forbidden)
    with TemporaryDirectory(prefix='eql-position-smoke-') as temp:
        root=Path(temp);game=root/'game';(game/'Logs').mkdir(parents=True)
        log=game/'Logs/eqlog_Test_freeport.txt';log.write_text('')
        output=root/'private'
        ui=game/'uifiles/synthetic';ui.mkdir(parents=True)
        texture=ui/'synthetic.tga';Image.new('RGBA',(2,2),(20,200,30,255)).save(texture)
        xml=ui/'selected.xml'
        xml.write_text('<XML><Ui2DAnimation item="A_PWCSStanding"><Frames>'
            '<Texture>synthetic.tga</Texture><Location><X>0</X><Y>0</Y></Location>'
            '<Size><CX>2</CX><CY>2</CY></Size></Frames></Ui2DAnimation>'
            '<Button item="PW_CombatStateAnim"><DecalSize><CX>2</CX><CY>2</CY></DecalSize></Button></XML>')
        xml_sha=sha256(xml.read_bytes()).hexdigest()
        def capture(**kwargs):
            assert kwargs['gate'] is gate and e.sender is None
            kwargs['still_current']();captures.append(1)
            dest=output/str(len(captures));dest.mkdir(parents=True)
            meta=dict(game_session=gate.game_session(),focused_window_id=42,
                capture_started_monotonic=now[0],capture_ended_monotonic=now[0],
                game_input_sent=False,chat_crop_included=False,
                format='eql-owner-ui-observation-v1',saved_layout_is_live_verified=False,
                ui_skin_from_saved_ini='synthetic',ui_scale_from_saved_ini=1,
                combat_widget_source={'file':str(xml),'sha256':xml_sha},
                source_sha256_postcapture={str(xml):xml_sha},window_size=[800,600],crops={})
            name='PlayerWindow__PW_CombatStateAnim'
            image=Image.new('RGB',(4,6),(20,30,90))
            image.paste(Image.new('RGB',(2,2),(20,200,30)),(1,2));image.save(dest/(name+'.png'))
            meta['crops'][name]={'file':name+'.png','box':[10,10,14,16],
                'sha256':sha256((dest/(name+'.png')).read_bytes()).hexdigest()}
            (dest/'metadata.json').write_text(json.dumps(meta));return dest
        adapted=make_owner_nov12_engine(Engine,capture_fn=capture,clock=lambda:now[0],
                                       output=output,private_root=output)
        e=adapted(Settings(game_dir=str(game),character='Test',server='freeport'),
                  lambda *_:None,lambda *_:None,measurement_only=True)
        e.selector.close();e.selector=selector;e.gate=gate
        e.trace_path=None;e.trace=lambda name,**values:traces.append((name,values))
        e.emit=lambda text=None:notices.append(text)
        e.send=e.hold=e.ensure_sender=forbidden
        def queue():e.post(POSITION_JOB);e.handle_job(*e.jobs.get_nowait())
        def key(code):
            for value in (1,0):
                events.append(SimpleNamespace(type=codes.EV_KEY,code=code,value=value))
                e.input_events()
        queue();before=e.cancel_generation
        for code in (codes.KEY_SLASH,codes.KEY_L,codes.KEY_ENTER):
            key(code);assert e.position_observation is not None and e.sender is None
        assert e.cancel_generation==before+2 and e.cancelled and not e.active
        with log.open('a') as file:file.write('[Sat Nov 14 03:00:01 2026] Your Location is 1, 2, 3\n')
        e.autopilot_tick(now[0]);assert not captures
        now[0]+=2;e.autopilot_tick(now[0]);assert len(captures)==1
        record=json.loads((output/'1/unbound-location.json').read_text())
        assert record['location']['raw_coordinates']==[1,2,3] and not record['live_route_accepted']
        assert e.position_observation is None and e.sender is None
        analysis=json.loads((output/'1/combat-analysis.json').read_text())
        assert analysis['ranked_candidates'][0]['animation']=='A_PWCSStanding'
        assert analysis['automatic_after_owner_capture'] and not analysis['input_authorized']
        assert not analysis['captured_texture_identity_verified']
        assert sha256(xml.read_bytes()).hexdigest()==xml_sha
        # A missing synthetic texture must preserve a second raw pair.
        texture.rename(ui/'temporarily-unavailable.tga')
        queue()
        with log.open('a') as file:file.write('[Sat Nov 14 03:00:02 2026] Your Location is 1, 2, 3\n')
        e.autopilot_tick(now[0]);now[0]+=2;e.autopilot_tick(now[0])
        assert (output/'2/unbound-location.json').is_file() and not (output/'2/combat-analysis.json').exists()
        assert [v for n,v in traces if n=='position_analysis_result'][-1]['outcome']=='unavailable'
        queue();key(codes.KEY_F9);assert e.position_observation is None
        while not e.jobs.empty():e.handle_job(*e.jobs.get_nowait())
        queue();key(codes.KEY_F11);assert e.position_observation is None
        assert len(captures)==2 and all(not r['game_input_sent'] for n,r in traces if n=='position_observation_result')
    print('PASS: actual Engine saves a synthetic pair then one source-pinned icon analysis; missing texture preserves second pair; F9/F11 cancel; no devices, real capture, settings writes or game input')


if __name__=='__main__':main()
