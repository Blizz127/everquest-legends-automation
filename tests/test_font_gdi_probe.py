"""Synthetic binary fixtures; no game assets, Wine or native process required."""
from hashlib import sha256
import struct

import pytest

from eql_automation.font_gdi_probe import read_gdi_probe,GLYPHS


def fixture():
    descriptor=struct.pack('<5l8B32s',4,0,0,0,100,0,0,0,1,0,0,0,0,b'Fixture\0')
    font=b'explicit synthetic font data'
    metrics=(4,3,1,0,0,3,4,100,0,96,96)
    data=b'EQLGDI1\0'+struct.pack('<5I',1,4,4,9,len(font))+descriptor+struct.pack('<11i',*metrics)+b'Fixture\0'.ljust(128,b'\0')+font
    # Blue controls coverage; red/green/reserved bytes must not substitute.
    bitmap=bytes((31,255,255,255,16,0,0,0,255,0,0,0,0,255,255,255))+bytes(48)
    for code in GLYPHS:data+=struct.pack('<3i',code,3,4)+bitmap
    return data,dict(font_sha256=sha256(font).hexdigest(),descriptor_sha256=sha256(descriptor).hexdigest())


def parse(data,pins):return read_gdi_probe(data,expected_sha256=sha256(data).hexdigest(),**pins)


def test_parse_preserves_selected_font_identity_and_keeps_live_binding_false():
    data,pins=fixture();p=parse(data,pins);s=p.summary()
    assert p.selected_face=='Fixture' and (p.width,p.height)==(4,4)
    assert s['selected_font_sha256']==pins['font_sha256']
    assert s['requested_height']==4 and s['charset']==1 and s['quality']==0
    assert not any(s[name] for name in ('input_authorized','live_font_binding_verified',
        'live_raster_equivalence_verified','final_texture_sampling_applied','scale_compensation_applied'))


def test_alpha4_uses_blue_and_prefixes_use_individual_advances():
    data,pins=fixture();p=parse(data,pins);rows=p.prefix_renderings()
    assert len(rows)==18
    slash=rows[0]
    assert slash.prefix=='/' and slash.variant=='gdi-alpha4-no-caret'
    assert slash.rgba[3:16:4]==bytes((17,17,255,0))
    # Each glyph advances by 3; the final glyph keeps its full 4-pixel bitmap.
    assert rows[1].width==7 and rows[2].prefix=='/l' and rows[2].width==7
    assert rows[-2].width==28 and rows[-1].width==31
    assert len(p.prefix_renderings(include_caret=False))==9


@pytest.mark.parametrize('change',['probe-pin','font-pin','descriptor-pin','magic','version','width','height',
    'glyph-count','font-size','metric-dimension','face-encoding','empty-face','glyph-order','advance','extent',
    'truncated','trailing','empty-glyph'])
def test_bad_identity_or_incomplete_probe_refuses(change):
    data,pins=fixture();data=bytearray(data)
    if change=='probe-pin':
        with pytest.raises(ValueError,match='SHA256'):read_gdi_probe(bytes(data),expected_sha256='0'*64,**pins)
        return
    if change=='font-pin':pins['font_sha256']='0'*64
    elif change=='descriptor-pin':pins['descriptor_sha256']='0'*64
    elif change=='magic':data[0]=0
    elif change=='version':struct.pack_into('<I',data,8,2)
    elif change=='width':struct.pack_into('<I',data,12,129)
    elif change=='height':struct.pack_into('<I',data,16,65)
    elif change=='glyph-count':struct.pack_into('<I',data,20,8)
    elif change=='font-size':struct.pack_into('<I',data,24,33*1024*1024)
    elif change=='metric-dimension':struct.pack_into('<i',data,88,3)
    elif change=='face-encoding':data[132]=255
    elif change=='empty-face':data[132]=0
    elif change=='glyph-order':struct.pack_into('<i',data,260+len(b'explicit synthetic font data'),10)
    elif change=='advance':struct.pack_into('<i',data,264+len(b'explicit synthetic font data'),5)
    elif change=='extent':struct.pack_into('<i',data,268+len(b'explicit synthetic font data'),5)
    elif change=='truncated':data=data[:-1]
    elif change=='trailing':data+=b'unknown'
    else:
        start=272+len(b'explicit synthetic font data');data[start:start+64]=bytes(64)
    with pytest.raises(ValueError):parse(bytes(data),pins).prefix_renderings()
