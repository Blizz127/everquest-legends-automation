from datetime import datetime
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont
import pytest

from eql_automation import map_zone_observer as m
from eql_automation.unbound_location_log import UnboundLocationObservation


def fixture(tmp_path, monkeypatch):
    game = tmp_path/'game'; (game/'Resources').mkdir(parents=True)
    (game/'eqgame.exe').write_bytes(b'fixture executable, never executed')
    xml = game/'map.xml'; xml.write_text('fixture layout')
    monkeypatch.setattr(m, 'EXE_PIN', sha256((game/'eqgame.exe').read_bytes()).hexdigest())
    monkeypatch.setattr(m, 'XML_PIN', sha256(xml.read_bytes()).hexdigest())
    (game/'Resources/ZoneNames.txt').write_text('54^The Greater Faydark^0^0\n58^Clan Crushbone^0^0\n')
    boxes = {name:(20, 40+i*40, 360 if i==0 else 150, 70+i*40)
             for i,(name,_) in enumerate(m.CONTROL_TYPES)}
    frame = Image.new('RGB', (500, 260), 'white')
    texts = ('The Greater Faydark', '1780', '-1802', '11')
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 20)
    for name,text in zip(boxes,texts):
        x,y,_,_ = boxes[name]; ImageDraw.Draw(frame).text((x+4,y),text,font=font,fill='black')
    def rect(box):
        return None if box is None else SimpleNamespace(x=box[0],y=box[1],w=box[2]-box[0],h=box[3]-box[1])
    elements = {name:ET.fromstring(f'<Label><EQType>{kind}</EQType></Label>') for name,kind in m.CONTROL_TYPES}
    layout = SimpleNamespace(sources={name:xml for name in boxes},elements=elements,
        skin='fixture',ui_scale=1,window=lambda name:rect((10,10,450,220)) if name=='MapViewWnd' else None,
        control=lambda window,name:rect(boxes.get(name)))
    window=SimpleNamespace(id=42)
    gate = SimpleNamespace(windows=lambda:[window],focused_window=lambda:window,
        game_session=lambda:dict(pid=10,start_ticks='100'),capture=lambda:frame.copy())
    fix=UnboundLocationObservation((1780.12,-1802.22,10.5),datetime.now(),100.,1,1)
    h=SimpleNamespace(game=game,frame=frame,layout=layout,boxes=boxes,texts=texts,now=100.5)
    h.args=dict(gate=gate,layout_loader=lambda *a,**kw:layout,game=game,character='Probe',server='private',
        fix=fix,still_current=lambda:None,clock=lambda:h.now)
    def reader():
        it=iter(h.texts)
        return lambda image:dict(text=next(it),confidence=95.)
    h.reader=reader
    return h


def test_exact_zone_and_native_coordinate_order_without_replaying_position(tmp_path,monkeypatch):
    h=fixture(tmp_path,monkeypatch)
    obs=m.read_current_map_zone(**h.args,line_reader=h.reader())
    assert obs.zone_id==54 and obs.raw_coordinates==(1780.12,-1802.22,10.5)
    assert obs.displayed_coordinates==(1780.,-1802.,11.)
    assert obs.record()['map_coordinates_are_navigation_input'] is False
    assert not obs.record()['game_input_sent']


@pytest.mark.parametrize('change', ['unknown','fuzzy','duplicate','swapped','decimal','missing','expired','source','type','cancel'])
def test_unreadable_mismatched_or_changed_map_does_not_bind_zone(tmp_path,monkeypatch,change):
    h=fixture(tmp_path,monkeypatch)
    if change=='unknown':h.texts=('Unknown Zone',*h.texts[1:])
    elif change=='fuzzy':h.texts=('The Greater Faydar',*h.texts[1:])
    elif change=='duplicate':
        with (h.game/'Resources/ZoneNames.txt').open('a') as out:out.write('99^The Greater Faydark^0^0\n')
    elif change=='swapped':h.texts=(h.texts[0],'-1802','1780','11')
    elif change=='decimal':h.texts=(h.texts[0],'1780.0','-1802','11')
    elif change=='missing':h.boxes.pop('MRA_LocZCoords')
    elif change=='expired':h.now=103.
    elif change=='source':(h.game/'eqgame.exe').write_bytes(b'updated')
    elif change=='type':h.layout.elements['MRA_ZoneLabel'].find('EQType').text='1021'
    elif change=='cancel':
        def cancelled():raise ValueError('F9')
        h.args['still_current']=cancelled
    with pytest.raises((ValueError,RuntimeError)):
        m.read_current_map_zone(**h.args,line_reader=h.reader())


def test_actual_tesseract_reads_synthetic_map_footer(tmp_path,monkeypatch):
    if not (m.OCR_ROOT/'run').is_file():pytest.skip('Private Tesseract bundle absent')
    h=fixture(tmp_path,monkeypatch)
    obs=m.read_current_map_zone(**h.args,line_reader=m.TesseractLineReader())
    assert obs.zone_id==54 and obs.texts==h.texts


@pytest.mark.parametrize('text', ['','level\ttext\tconf\n5\tExample\tNaN\n'])
def test_empty_or_invalid_tsv_refuses(text):
    with pytest.raises((ValueError,KeyError)):m.read_tsv_line(text)
