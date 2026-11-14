"""Conditional source-glyph sampling with explicit unknown edge pixels.

This joins the copied per-glyph geometry to the prefix matcher. It models
axis-aligned pixel-center coverage, bilinear alpha sampling, white-texture
color modulation and source-alpha/inverse-source-alpha ADD compositing.
Those pipeline choices and projection offset are hypotheses, not live state.
Float64 reference interpolation/byte rounding is not claimed GPU-equivalent.

Only the probe's cx-by-cy glyph extent supplies known texels. Samples outside
it may depend on reused-DIB history or a neighboring atlas cell. They become
unknown output pixels, never a clamped edge or invented transparent texel.
"""
from dataclasses import dataclass
from hashlib import sha256
import json
import math

from .command_text_match import PrefixRendering
from .font_gdi_probe import GdiFontProbe
from .font_geometry import (CommandFontGeometry, command_font_geometry,
                            COPIED_RUNTIME_SHA256, RASTER_RUNTIME_SHA256)


@dataclass(frozen=True)
class SampledCommandFont:
    rendering: PrefixRendering
    pixel_box: tuple[int, int, int, int]
    geometry_sha256: str
    model_sha256: str
    pipeline_evidence_sha256: str
    sampled_pixel_count: int
    unknown_pixel_count: int

    def summary(self):
        r = self.rendering
        return dict(format='eql-sampled-command-font-v1', prefix=r.prefix, variant=r.variant,
            pixel_box=self.pixel_box, geometry_sha256=self.geometry_sha256,
            model_sha256=self.model_sha256, pipeline_evidence_sha256=self.pipeline_evidence_sha256,
            rgba_sha256=sha256(r.rgba).hexdigest(), known_mask_sha256=sha256(r.known_pixels).hexdigest(),
            sampled_pixel_count=self.sampled_pixel_count, unknown_pixel_count=self.unknown_pixel_count,
            model='pixel_center_bilinear_alpha4_tinted_white_source_alpha_ADD',
            arithmetic='float64_reference_interpolation_round_half_up_output_bytes',
            final_texture_sampling_applied=True, unknown_atlas_edges_masked=True,
            active_atlas_contents_verified=False, inherited_color_blend_verified=False,
            gpu_raster_equivalence_verified=False, live_font_binding_verified=False,
            live_raster_equivalence_verified=False, focus_observed=False,
            selection_observed=False, game_capture_used=False, game_input_sent=False,
            input_authorized=False)


def _alpha(probe, glyph, u, v):
    # Texture-coordinate edges map to texel centers at n+.5.
    sx, sy = u-.5, v-.5
    ix, iy = math.floor(sx), math.floor(sy)
    fx, fy = sx-ix, sy-iy
    total = 0.
    for x, wx in ((ix, 1-fx), (ix+1, fx)):
        for y, wy in ((iy, 1-fy), (iy+1, fy)):
            weight = wx*wy
            if weight == 0: continue
            if not 0 <= x < glyph.advance or not 0 <= y < glyph.extent_height:
                return None
            total += weight * ((glyph.bgra[(y*probe.width+x)*4] >> 4) / 15.)
    return total


def sample_command_font(probe, geometry, *, pixel_box, screen_offset,
                        text_rgb, text_alpha, pipeline_evidence_sha256):
    """Render one complete prefix/caret hypothesis, without field clipping.

    Supply the absolute final pixel box and projection offset explicitly. The
    retained candidate viewport/shader calculation suggests +.5,+.5, but this
    function does not select it or declare that pipeline active. The complete
    sampled result and mask can be consumed by CommandTextMatcher.
    """
    if (type(probe) is not GdiFontProbe or type(geometry) is not CommandFontGeometry
            or (geometry.probe_sha256, geometry.font_sha256, geometry.descriptor_sha256)
                != (probe.probe_sha256, probe.font_sha256, probe.descriptor_sha256)
            or not isinstance(pipeline_evidence_sha256,str) or len(pipeline_evidence_sha256)!=64
            or any(c not in '0123456789abcdef' for c in pipeline_evidence_sha256)):
        raise ValueError('Matching pinned probe, geometry and pipeline evidence required')
    if probe.dib_reset_mode != 'clear_each_glyph' and probe.background_mode != 2:
        raise ValueError('Reused transparent DIB has no history-independent glyph extent')
    expected = command_font_geometry(probe, geometry.prefix, base_height=geometry.base_height,
        ui_scale=geometry.ui_scale, client_box_ui=geometry.client_box_ui,
        focused=geometry.focused_hypothesis, caret_visible=geometry.caret_visible_hypothesis,
        eqgame_sha256=COPIED_RUNTIME_SHA256, graphics_sha256=RASTER_RUNTIME_SHA256)
    if geometry != expected: raise ValueError('Geometry differs from pinned per-glyph transform')
    if (type(pixel_box) is not tuple or len(pixel_box)!=4
            or any(type(v) is not int for v in pixel_box)
            or not 1 <= pixel_box[2]-pixel_box[0] <= 2048
            or not 1 <= pixel_box[3]-pixel_box[1] <= 64
            or type(screen_offset) is not tuple or len(screen_offset)!=2
            or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>2 for v in screen_offset)
            or type(text_rgb) is not tuple or len(text_rgb)!=3
            or any(type(v) is not int or not 0<=v<=255 for v in text_rgb)
            or type(text_alpha) is not int or not 1<=text_alpha<=255):
        raise ValueError('Explicit bounded pixel rectangle, projection offset and text tint required')
    left, top, right, bottom = pixel_box
    width, height = right-left, bottom-top
    alpha = [0.] * (width*height)
    known = bytearray([255]) * len(alpha)
    touched = set()
    glyphs = {g.code:g for g in probe.glyphs}
    for q in (*geometry.glyphs, *((geometry.caret,) if geometry.caret is not None else ())):
        glyph = glyphs[q.code]
        ql, qt, qr, qb = (q.quad[0]+screen_offset[0], q.quad[1]+screen_offset[1],
                          q.quad[2]+screen_offset[0], q.quad[3]+screen_offset[1])
        tl, tt, tr, tb = q.texture_rect
        if not ql < qr or not qt < qb or (tl,tt,tr,tb)!=(0,0,glyph.advance,glyph.extent_height):
            raise ValueError('Unsupported glyph rectangle or texture extent')
        xs, xe = math.ceil(ql-.5), math.ceil(qr-.5)
        ys, ye = math.ceil(qt-.5), math.ceil(qb-.5)
        if not left <= xs <= xe <= right or not top <= ys <= ye <= bottom:
            raise ValueError('Pixel rectangle clips a sampled glyph or caret')
        for y in range(ys,ye):
            v = tt+(y+.5-qt)/(qb-qt)*(tb-tt)
            for x in range(xs,xe):
                u = tl+(x+.5-ql)/(qr-ql)*(tr-tl)
                i = (y-top)*width+x-left
                touched.add(i)
                value = _alpha(probe,glyph,u,v)
                if value is None:
                    known[i] = 0
                    continue
                value *= text_alpha/255.
                # All layers share this explicit white-texture tint. Keeping
                # straight RGB=tint and composing alpha represents their RGB
                # source-over result before unknown framebuffer quantization.
                alpha[i] = value+alpha[i]*(1-value)
    rgba = bytearray(width*height*4)
    for i,value in enumerate(alpha):
        if known[i] and value>0:
            rgba[i*4:i*4+4] = bytes((*text_rgb,min(255,math.floor(value*255+.5))))
    geometry_sha = sha256(json.dumps(geometry.summary(),sort_keys=True).encode()).hexdigest()
    model = dict(geometry_sha256=geometry_sha,pixel_box=pixel_box,screen_offset=screen_offset,
        text_rgb=text_rgb,text_alpha=text_alpha,pipeline_evidence_sha256=pipeline_evidence_sha256,
        model='pixel_center_bilinear_alpha4_tinted_white_source_alpha_ADD',
        arithmetic='float64_reference_interpolation_round_half_up_output_bytes',
        known_extent='only_gdi_cx_cy_no_border_clamp')
    model_sha = sha256(json.dumps(model,sort_keys=True).encode()).hexdigest()
    rendering = PrefixRendering(geometry.prefix,'sampled-'+model_sha[:24],width,height,bytes(rgba),bytes(known))
    return SampledCommandFont(rendering,pixel_box,geometry_sha,model_sha,
        pipeline_evidence_sha256,len(touched),known.count(0))
