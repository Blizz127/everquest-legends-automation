"""Reference sampling arithmetic and mask propagation; synthetic font only."""
from dataclasses import replace

import pytest

from eql_automation.font_raster import sample_command_font
from eql_automation.font_geometry import command_font_geometry, COPIED_RUNTIME_SHA256, RASTER_RUNTIME_SHA256
from test_font_geometry import probe, model


def sample(p=None,g=None,**changes):
    p = p or probe(); g = g or model(probe=p)
    args = dict(pixel_box=(0,20,160,40),screen_offset=(.5,.5),
                text_rgb=(255,255,255),text_alpha=255,pipeline_evidence_sha256='a'*64)
    args.update(changes)
    return sample_command_font(p,g,**args)


def pixel(result,x,y):
    i=(y-result.pixel_box[1])*result.rendering.width+x-result.pixel_box[0]
    return result.rendering.rgba[i*4:i*4+4],result.rendering.known_pixels[i]


def unscaled(p):
    return command_font_geometry(p,'/',base_height=4,ui_scale=1.,client_box_ui=(0,0,160,8),
        focused=False,caret_visible=False,eqgame_sha256=COPIED_RUNTIME_SHA256,
        graphics_sha256=RASTER_RUNTIME_SHA256)


def test_integer_pixel_centers_sample_exact_texels_without_border_invention():
    p=probe();g=unscaled(p);r=sample(p,g,pixel_box=(0,0,160,8))
    assert r.unknown_pixel_count==0 and r.sampled_pixel_count==12
    for y in range(1,5):
        for x in range(3):assert pixel(r,x,y)==(b'\xff'*4,255)
    assert pixel(r,3,1)==(bytes(4),255)


def test_bilinear_fraction_and_unknown_neighbor_do_not_clamp_to_glyph_edge():
    p=probe();raw=bytes(v for y in range(4) for x in range(4)
                      for v in ((255 if x in (1,3) else 0),0,0,0))
    p=replace(p,glyphs=tuple(replace(g,bgra=raw) for g in p.glyphs));g=unscaled(p)
    r=sample(p,g,pixel_box=(0,0,160,8),screen_offset=(.25,.5))
    assert pixel(r,0,1)==(bytes((255,255,255,64)),255)
    assert pixel(r,1,1)==(bytes((255,255,255,191)),255)
    # Probe storage column 3 exists and is white, but is outside cx=3.
    assert pixel(r,2,1)[1]==0 and r.unknown_pixel_count==4


def test_compensated_geometry_masks_last_column_and_bottom_row():
    p=probe();r=sample(p,model(probe=p,prefix='/'))
    assert r.unknown_pixel_count>0
    # glyph origin (12,31), fractional width2.8125/height3.75, caret separately.
    assert pixel(r,12,31)[1]==255
    assert pixel(r,14,31)[1]==0
    assert pixel(r,12,34)[1]==0
    assert pixel(r,11,31)==(bytes(4),255)


def test_caret_uses_separate_ui_rounding_and_does_not_shift_text():
    p=probe();shown=model(probe=p);hidden=model(probe=p,caret_visible=False)
    a,b=sample(p,shown),sample(p,hidden)
    assert shown.caret_origin_graphics==(22,31)
    assert pixel(a,22,31)[0][3]>0 and pixel(b,22,31)==(bytes(4),255)
    assert pixel(a,21,31)==pixel(b,21,31)==(bytes(4),255)
    assert a.rendering.rgba[:10]==b.rendering.rgba[:10]


def test_tint_and_alpha4_conversion_are_explicit():
    p=probe();p=replace(p,glyphs=tuple(replace(g,bgra=bytes((128,0,0,0))*16) for g in p.glyphs))
    r=sample(p,unscaled(p),pixel_box=(0,0,160,8),text_rgb=(20,40,60),text_alpha=255)
    assert pixel(r,0,1)==(bytes((20,40,60,136)),255)
    assert all(r.summary()[k] is False for k in ('input_authorized','focus_observed','selection_observed',
        'live_raster_equivalence_verified','active_atlas_contents_verified','inherited_color_blend_verified'))


@pytest.mark.parametrize('change',[{'pixel_box':(14,20,160,40)}, {'screen_offset':(3.,0.)},
    {'screen_offset':(float('nan'),0.)}, {'text_rgb':(True,0,0)}, {'text_alpha':0},
    {'pipeline_evidence_sha256':'unknown'}, {'pixel_box':(0,0,4096,64)}])
def test_unknown_unbounded_or_clipped_render_hypotheses_refuse(change):
    with pytest.raises(ValueError):sample(**change)


def test_changed_geometry_or_probe_and_transparent_reuse_refuse():
    p=probe();g=model(probe=p)
    with pytest.raises(ValueError):sample(p,replace(g,text_width_graphics=99))
    with pytest.raises(ValueError):sample(replace(p,probe_sha256='d'*64),g)
    p=replace(p,dib_reset_mode='zero_once_then_reuse')
    with pytest.raises(ValueError):sample(p,model(probe=p))
