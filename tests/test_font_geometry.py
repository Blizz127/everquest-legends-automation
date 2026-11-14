"""Source-transform examples; all probe pixels/font bytes are synthetic."""
from hashlib import sha256
import struct

import pytest

from eql_automation.command_text_match import PREFIXES
from eql_automation.font_gdi_probe import GLYPHS, read_gdi_probe, RASTER_RUNTIME_SHA256
from eql_automation.font_geometry import command_font_geometry, COPIED_RUNTIME_SHA256


def probe(height=4):
    descriptor = struct.pack('<5l8B32s', height, 0, 0, 0, 100, 0, 0, 0, 1, 0, 0, 0, 0, b'Fixture\0')
    font = b'geometry fixture'
    data = (b'EQLGDI1\0' + struct.pack('<5I', 1, 4, 4, len(GLYPHS), len(font)) + descriptor
            + struct.pack('<11i', 4, 3, 1, 0, 0, 3, 4, 100, 0, 96, 96)
            + b'Fixture\0'.ljust(128, b'\0') + font)
    for code in GLYPHS:
        data += struct.pack('<3i', code, 3, 4) + bytes((255, 0, 0, 0))*16
    return read_gdi_probe(data, expected_sha256=sha256(data).hexdigest(),
        font_sha256=sha256(font).hexdigest(), descriptor_sha256=sha256(descriptor).hexdigest())


def model(prefix='/lo', **kwargs):
    defaults = dict(base_height=3, ui_scale=1.25, client_box_ui=(10, 20, 200, 36),
        focused=True, caret_visible=True, eqgame_sha256=COPIED_RUNTIME_SHA256,
        graphics_sha256=RASTER_RUNTIME_SHA256)
    p = kwargs.pop('probe', None) or probe()
    defaults.update(kwargs)
    return command_font_geometry(p, prefix, **defaults)


def test_fractional_quads_keep_integer_advances_and_per_glyph_texture_extents():
    m = model()
    assert m.requested_height == 4 and m.compensation == .9375
    assert [q.origin for q in m.glyphs] == [(12, 31), (15, 31), (18, 31)]
    assert m.glyphs[0].quad == (11.5, 30.5, 14.3125, 34.25)
    assert m.glyphs[0].texture_rect == (0, 0, 3, 4)  # NOT bitmap storage width 4.
    assert m.text_width_graphics == 9
    long = model('/location')
    assert long.text_width_graphics == 27  # ceil(total fractional width) would be 26.


def test_caret_rounds_in_ui_space_instead_of_concatenating_in_graphics_space():
    m = model()
    assert m.text_width_ui == 8
    assert m.caret_origin_ui == (18, 25)
    assert m.caret_origin_graphics == (22, 31)
    assert m.caret_origin_graphics[0] != m.text_origin_graphics[0]+m.text_width_graphics
    assert m.caret.quad == (21.5, 30.5, 24.3125, 34.25)


def test_height_uses_graphics_metric_then_ui_ceil_then_extra_one():
    m = model()
    assert m.graphics_line_height == 4 and m.font_height_ui == 5
    assert m.text_origin_ui == (10, 25)  # Truncated 11/2, not round(11/2).
    assert m.text_origin_graphics == (12, 31)  # Floor, not round(12.5, 31.25).


def test_negative_origin_uses_floor_not_truncation():
    m = model(client_box_ui=(-10, -20, 200, -4))
    assert m.text_origin_ui == (-10, -15)
    assert m.text_origin_graphics == (-13, -19)


def test_blink_does_not_change_fitting_width_or_text_origin():
    shown, hidden = model(), model(caret_visible=False)
    assert hidden.caret is None and hidden.caret_origin_ui is None
    assert hidden.glyphs == shown.glyphs
    assert hidden.focused_width_ui == shown.focused_width_ui
    assert not hidden.summary()['focus_observed']


def test_float32_product_rounds_before_ceil_and_probe_binding():
    # Python double product exceeds 4; native float32 rounds it exactly to 4.
    m = model(base_height=4, ui_scale=1+2**-25)
    assert m.ui_scale == 1 and m.requested_height == 4 and m.compensation == 1
    # This scale itself is exact float32, but its double-precision product
    # exceeds 4. The native multiply rounds to 4 before ceil chooses the font.
    m = model(base_height=3, ui_scale=1.3333333730697632)
    assert m.requested_height == 4 and m.compensation == 1


def test_metrics_are_not_logfont_requested_height():
    m = model(probe=probe(1), base_height=1, ui_scale=.5)
    assert m.compensation == .5 and m.graphics_line_height == 2
    assert [g.advance for g in m.glyphs] == [2, 2, 2]


@pytest.mark.parametrize('prefix', PREFIXES)
def test_complete_prefixes_preserve_provenance_and_never_grant_live_authority(prefix):
    p = probe(); m = model(prefix, probe=p); report = m.summary()
    assert len(m.glyphs) == len(prefix)
    assert report['probe_sha256'] == p.probe_sha256
    assert report['font_sha256'] == p.font_sha256
    assert report['descriptor_sha256'] == p.descriptor_sha256
    assert report['graphics_sha256'] == RASTER_RUNTIME_SHA256
    for key in ('final_gpu_projection_applied', 'final_texture_sampling_applied',
                'live_filter_verified', 'live_font_binding_verified',
                'live_raster_equivalence_verified', 'focus_observed',
                'game_capture_used', 'game_input_sent', 'input_authorized'):
        assert report[key] is False


@pytest.mark.parametrize('kwargs', [
    {'eqgame_sha256': '0'*64}, {'graphics_sha256': '0'*64},
    {'base_height': 0}, {'base_height': True}, {'ui_scale': float('nan')},
    {'ui_scale': float('inf')}, {'ui_scale': 0}, {'ui_scale': True},
    {'base_height': 15}, {'client_box_ui': [10, 20, 200, 36]},
    {'client_box_ui': (10., 20, 200, 36)}, {'client_box_ui': (10, 20, 10, 36)},
    {'client_box_ui': (10, 20, 20, 36)}, {'client_box_ui': (10, 20, 200, 21)},
    {'focused': False}, {'caret_visible': 1}, {'focused': None},
])
def test_unsupported_source_and_layout_hypotheses_refuse(kwargs):
    with pytest.raises(ValueError): model(**kwargs)


@pytest.mark.parametrize('prefix', ['', '/location extra', '/loc\n', '|'])
def test_not_a_fixed_prefix_refuses(prefix):
    with pytest.raises(ValueError): model(prefix)
