"""Copied-client single-line font geometry, before GPU projection/rasterization.

This consumes an isolated, pinned GDI probe. It does not resize a whole text
bitmap: integer glyph advances and fractional quad sizes follow separate paths.
The caller supplies a logical client rectangle and caret state as hypotheses;
neither is discovered or accepted as live state here.
"""
from dataclasses import asdict, dataclass
import math
import struct

from .chat_ui_layout import COPIED_RUNTIME_SHA256
from .command_text_match import PREFIXES
from .font_gdi_probe import GdiFontProbe, RASTER_RUNTIME_SHA256


def _f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def _int(value, name, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{name} must be an integer in [{low}, {high}]')
    return value


@dataclass(frozen=True)
class GlyphGeometry:
    code: int
    advance: int
    origin: tuple[int, int]
    # Local texel coordinates, not atlas UVs; tmMaxCharWidth is only storage.
    texture_rect: tuple[int, int, int, int]
    quad: tuple[float, float, float, float]


@dataclass(frozen=True)
class CommandFontGeometry:
    prefix: str
    focused_hypothesis: bool
    caret_visible_hypothesis: bool
    client_box_ui: tuple[int, int, int, int]
    ui_scale: float
    base_height: int
    requested_height: int
    compensation: float
    graphics_line_height: int
    font_height_ui: int
    text_width_graphics: int
    text_width_ui: int
    focused_width_ui: int
    text_origin_ui: tuple[int, int]
    text_origin_graphics: tuple[int, int]
    caret_origin_ui: tuple[int, int] | None
    caret_origin_graphics: tuple[int, int] | None
    glyphs: tuple[GlyphGeometry, ...]
    caret: GlyphGeometry | None
    probe_sha256: str
    font_sha256: str
    descriptor_sha256: str

    def summary(self):
        return dict(format='eql-command-font-geometry-v1', **asdict(self),
            eqgame_sha256=COPIED_RUNTIME_SHA256,
            graphics_sha256=RASTER_RUNTIME_SHA256,
            geometry_scope='fitting_left_aligned_single_line_no_selection',
            quad_space='graphics_input_before_projection',
            texture_coordinates='local_source_texels_not_atlas_uv',
            source_default_filter='MIN_MAG_LINEAR_MIP_POINT',
            float_operations='IEEE754_binary32_at_inspected_operation_boundaries',
            clip_applied=False, final_gpu_projection_applied=False,
            final_texture_sampling_applied=False, live_filter_verified=False,
            live_font_binding_verified=False, live_raster_equivalence_verified=False,
            focus_observed=False, game_capture_used=False, game_input_sent=False,
            input_authorized=False)


def command_font_geometry(probe, prefix, *, base_height, ui_scale,
                          client_box_ui, focused, caret_visible,
                          eqgame_sha256, graphics_sha256):
    """Model the fitting left-aligned source path; reject unsupported layouts.

    Glyph widths: EQGraphics 197110; line height: 196a70; parser origins:
    197290; fractional quads: 1945d0. Text/caret calls use eqgame 624ed0,
    UI metric wrappers 5e3bc0/5e3e30 and scaled coordinates in 5e3a10.
    Explicit binary pins select these semantics, not a running-process binding.
    """
    if eqgame_sha256 != COPIED_RUNTIME_SHA256 or graphics_sha256 != RASTER_RUNTIME_SHA256:
        raise ValueError('Font geometry needs both inspected binary pins')
    if type(probe) is not GdiFontProbe:
        raise ValueError('Pinned GDI probe required')
    if prefix not in PREFIXES:
        raise ValueError('Only fixed /location prefixes are supported')
    if type(focused) is not bool or type(caret_visible) is not bool or (caret_visible and not focused):
        raise ValueError('Explicit consistent focus/caret hypotheses required')
    base_height = _int(base_height, 'base_height', 1, 64)
    if type(ui_scale) not in (int, float) or not math.isfinite(ui_scale) or not .5 <= ui_scale <= 4:
        raise ValueError('Finite bounded UI scale required')
    scale = _f32(ui_scale)
    product = _f32(base_height * scale)
    requested_height = math.ceil(product)
    if requested_height != struct.unpack_from('<i', probe.descriptor)[0]:
        raise ValueError('Probe LOGFONTA height differs from ceil(base_height * UI scale)')
    compensation = _f32(product / requested_height)
    if type(client_box_ui) is not tuple or len(client_box_ui) != 4:
        raise ValueError('Immutable logical client rectangle required')
    left, top, right, bottom = (_int(v, 'client edge', -16384, 16384) for v in client_box_ui)
    if not 6 <= right-left <= 2048 or not 1 <= bottom-top <= 64:
        raise ValueError('Unsupported client rectangle dimensions')
    glyphs = {g.code: g for g in probe.glyphs}

    def advance(code):
        return math.ceil(_f32(glyphs[code].advance * compensation))

    # The graphics parser accumulates integer advances, not fractional widths.
    width = sum(advance(ord(c)) for c in prefix)
    width_ui = math.ceil(_f32(width / scale))
    fitting_width = width + (advance(ord('|')) if focused else 0)
    fitting_width_ui = math.ceil(_f32(fitting_width / scale))
    line_height = math.ceil(_f32(probe.metrics[0] * compensation))
    font_height_ui = 1 + math.ceil(_f32(line_height / scale))
    if fitting_width_ui > right-left-5 or font_height_ui > bottom-top:
        raise ValueError('Overflow or clipping needs an unsupported layout path')
    # Integer division in the native centering path truncates toward zero.
    origin_ui = (left, top + math.trunc((bottom-top-font_height_ui) / 2))

    def project(origin):
        return tuple(math.floor(_f32(v * scale)) for v in origin)

    origin = project(origin_ui)

    def quad(code, at):
        glyph = glyphs[code]
        x, y = at
        qx, qy = _f32(x-.5), _f32(y-.5)
        w = _f32(glyph.advance * compensation)
        h = _f32(glyph.extent_height * compensation)
        return GlyphGeometry(code, advance(code), at,
            (0, 0, glyph.advance, glyph.extent_height),
            (qx, qy, _f32(qx+w), _f32(qy+h)))

    quads = []
    cursor = origin[0]
    for char in prefix:
        q = quad(ord(char), (cursor, origin[1]))
        quads.append(q)
        cursor += q.advance
    # Caret is a separate widget draw; its UI-space width rounds independently.
    caret_ui = (origin_ui[0]+width_ui, origin_ui[1]) if caret_visible else None
    caret_origin = project(caret_ui) if caret_ui is not None else None
    caret = quad(ord('|'), caret_origin) if caret_origin is not None else None
    return CommandFontGeometry(prefix, focused, caret_visible, client_box_ui,
        scale, base_height, requested_height, compensation, line_height,
        font_height_ui, width, width_ui, fitting_width_ui, origin_ui, origin,
        caret_ui, caret_origin, tuple(quads), caret,
        probe.probe_sha256, probe.font_sha256, probe.descriptor_sha256)
