"""Read an isolated GDI probe and reproduce the copied alpha4 glyph model.

This imports no display/Wine/input library and never starts a process. Selected
font bytes and LOGFONTA must match explicit pins. Probe glyphs are an isolated
renderer hypothesis, not observations of the running client. Version 2 records
actual mapping/background modes and DIB reset policy. Reused-DIB diagnostics
are sequence-dependent and cannot supply an independent glyph rendering bank.
Final texture sampling, scale compensation, language mapping and overrides
are not applied.
"""
from dataclasses import dataclass
from hashlib import sha256
import struct

from PIL import Image

from .command_text_match import PrefixRendering, PREFIXES

GLYPHS = tuple(map(ord,'/locatin|'))  # Unique input characters, in probe order.
RASTER_RUNTIME_SHA256 = '4f5f18ee9821b3e15ff25980dda7def1b2cfcdfd72a5d359ac02d0b546163168'
DIB_MODES = ('clear_each_glyph', 'zero_once_then_reuse', 'white_once_then_reuse')


@dataclass(frozen=True)
class GdiGlyph:
    code: int
    advance: int
    extent_height: int
    bgra: bytes


@dataclass(frozen=True)
class GdiFontProbe:
    probe_sha256: str
    font_sha256: str
    descriptor_sha256: str
    width: int
    height: int
    descriptor: bytes
    metrics: tuple[int,...]
    selected_face: str
    glyphs: tuple[GdiGlyph,...]
    format_version: int = 1
    dib_reset_mode: str = 'clear_each_glyph'
    mapping_mode: int | None = None  # Legacy probe did not record this.
    background_mode: int = 1  # Legacy helper explicitly set TRANSPARENT.

    def summary(self):
        height,width,escapement,orientation,weight=struct.unpack_from('<5i',self.descriptor)
        return dict(format='eql-isolated-gdi-font-v1',probe_sha256=self.probe_sha256,
            selected_font_sha256=self.font_sha256,descriptor_sha256=self.descriptor_sha256,
            selected_face=self.selected_face,bitmap_size=(self.width,self.height),
            requested_height=height,requested_width=width,weight=weight,
            charset=self.descriptor[23],quality=self.descriptor[26],
            metric_height=self.metrics[0],ascent=self.metrics[1],descent=self.metrics[2],
            glyphs=[dict(code=g.code,advance=g.advance,extent_height=g.extent_height,
                         bitmap_sha256=sha256(g.bgra).hexdigest()) for g in self.glyphs],
            alpha_model='low_blue_byte_shift_right_4_then_expand_to_8_bits',
            raster_runtime_sha256=RASTER_RUNTIME_SHA256,source_font_identity_verified=True,
            probe_format_version=self.format_version,dib_reset_mode=self.dib_reset_mode,
            mapping_mode=self.mapping_mode,background_mode=self.background_mode,
            glyphs_independent=self.dib_reset_mode=='clear_each_glyph',
            copied_client_dc_state_verified=False,
            isolated_renderer=True,final_texture_sampling_applied=False,
            scale_compensation_applied=False,live_font_binding_verified=False,
            live_raster_equivalence_verified=False,input_authorized=False)

    def prefix_renderings(self,*,include_caret=True):
        """Compose independently rasterized glyphs at their GDI advances.

        The raw alpha4 texture model is retained at its probe size. No guessed
        interpolation or live DPI/font selection is introduced here.
        """
        if self.dib_reset_mode!='clear_each_glyph':
            raise ValueError('Reused DIB glyphs are sequence-dependent; no independent rendering bank')
        glyphs={g.code:g for g in self.glyphs}
        layers={}
        for code,g in glyphs.items():
            blue=Image.frombytes('RGBA',(self.width,self.height),g.bgra,'raw','BGRA').getchannel('B')
            alpha=blue.point([(value>>4)*17 for value in range(256)])
            layer=Image.new('RGBA',(self.width,self.height),(255,255,255,0));layer.putalpha(alpha)
            if alpha.getbbox() is None:raise ValueError('Probe contains an empty required glyph')
            layers[code]=layer
        renderings=[]
        for prefix in PREFIXES:
            for caret in (False,True) if include_caret else (False,):
                text=prefix+('|' if caret else '')
                advance=sum(glyphs[ord(c)].advance for c in text[:-1])
                canvas=Image.new('RGBA',(advance+self.width,self.height))
                cursor=0
                for c in text:
                    canvas.alpha_composite(layers[ord(c)],(cursor,0))
                    cursor+=glyphs[ord(c)].advance
                renderings.append(PrefixRendering(prefix,'gdi-alpha4-'+('caret' if caret else 'no-caret'),
                                                  canvas.width,canvas.height,canvas.tobytes()))
        return tuple(renderings)


def read_gdi_probe(data,*,expected_sha256,font_sha256,descriptor_sha256):
    if type(data) is not bytes or len(data)>33*1024*1024:
        raise ValueError('Bounded immutable probe bytes required')
    if sha256(data).hexdigest()!=expected_sha256:
        raise ValueError('Probe SHA256 mismatch')
    cursor=0
    def take(size):
        nonlocal cursor
        if size<0 or cursor+size>len(data):raise ValueError('Truncated GDI probe')
        value=data[cursor:cursor+size];cursor+=size;return value
    magic=take(8)
    version,width,height,count,font_size=struct.unpack('<5I',take(20))
    if (magic,version) not in ((b'EQLGDI1\0',1),(b'EQLGDI2\0',2)):
        raise ValueError('Unknown GDI probe format/version')
    if not 1<=width<=128 or not 1<=height<=64 or count!=len(GLYPHS) or not 1<=font_size<=32*1024*1024:
        raise ValueError('Unsupported probe dimensions or font size')
    reset_mode,mapping_mode,background_mode=0,None,1
    if version==2:
        reset_mode,mapping_mode,background_mode=struct.unpack('<3I',take(12))
        if reset_mode>=len(DIB_MODES) or mapping_mode!=1 or background_mode not in (1,2):
            raise ValueError('Unsupported DIB reset policy or DC modes')
    descriptor=take(60)
    if sha256(descriptor).hexdigest()!=descriptor_sha256:
        raise ValueError('LOGFONTA hypothesis SHA256 mismatch')
    if not 1<=struct.unpack_from('<i',descriptor)[0]<=64:
        raise ValueError('Unsupported LOGFONTA height')
    metrics=struct.unpack('<11i',take(44))
    if metrics[0]!=height or metrics[6]!=width:
        raise ValueError('GDI bitmap and metric dimensions differ')
    try:face=take(128).split(b'\0',1)[0].decode('ascii')
    except UnicodeDecodeError:raise ValueError('Unsupported selected-font face encoding') from None
    if not face:raise ValueError('Selected-font face missing')
    if sha256(take(font_size)).hexdigest()!=font_sha256:
        raise ValueError('Selected font differs from supplied copied font')
    glyphs=[]
    for expected_code in GLYPHS:
        code,advance,extent_height=struct.unpack('<3i',take(12))
        if code!=expected_code or not 1<=advance<=width or not 1<=extent_height<=height:
            raise ValueError('Unexpected glyph order or metrics')
        glyphs.append(GdiGlyph(code,advance,extent_height,take(width*height*4)))
    if cursor!=len(data):raise ValueError('Trailing GDI probe bytes')
    return GdiFontProbe(expected_sha256,font_sha256,descriptor_sha256,width,height,descriptor,metrics,face,tuple(glyphs),
                        version,DIB_MODES[reset_mode],mapping_mode,background_mode)


def compare_dib_history(baseline, reused):
    """Compare alpha4 within/beyond glyph extents under the same explicit DC.

    Differences outside cx/cy still matter: the client copies the full cell
    and linear sampling can fetch neighboring texels. This comparison describes
    these two isolated sequences, never the history of the running game.
    """
    if (not isinstance(baseline,GdiFontProbe) or not isinstance(reused,GdiFontProbe)
            or baseline.format_version!=2 or reused.format_version!=2
            or baseline.dib_reset_mode!='clear_each_glyph'
            or reused.dib_reset_mode not in DIB_MODES[1:]):
        raise ValueError('Version-2 clear-each baseline and reused-DIB diagnostic required')
    identity=('font_sha256','descriptor_sha256','width','height','metrics',
              'selected_face','mapping_mode','background_mode')
    if any(getattr(baseline,k)!=getattr(reused,k) for k in identity):
        raise ValueError('Font, descriptor, metrics and DC state must match for a DIB history comparison')
    if (len(baseline.glyphs)!=len(reused.glyphs) or any(
            (a.code,a.advance,a.extent_height)!=(b.code,b.advance,b.extent_height)
            for a,b in zip(baseline.glyphs,reused.glyphs))):
        raise ValueError('Glyph sequence and extents must match')
    rows=[]
    for clean,carried in zip(baseline.glyphs,reused.glyphs):
        before,after=clean.bgra[::4],carried.bgra[::4]
        changed=[i for i,(a,b) in enumerate(zip(before,after)) if a>>4!=b>>4]
        inside=sum(i%baseline.width<clean.advance and i//baseline.width<clean.extent_height
                   for i in changed)
        rows.append(dict(code=clean.code,advance=clean.advance,extent_height=clean.extent_height,
            raw_blue_changed_pixels=sum(a!=b for a,b in zip(before,after)),
            alpha4_changed_pixels=len(changed),inside_extent_changed_pixels=inside,
            outside_extent_changed_pixels=len(changed)-inside,
            right_neighbor_column_changes=sum(i%baseline.width==clean.advance for i in changed)))
    return dict(format='eql-isolated-dib-history-v1',baseline_sha256=baseline.probe_sha256,
        reused_sha256=reused.probe_sha256,font_sha256=baseline.font_sha256,
        descriptor_sha256=baseline.descriptor_sha256,mapping_mode=baseline.mapping_mode,
        background_mode=baseline.background_mode,reused_dib_mode=reused.dib_reset_mode,
        glyphs=rows,game_capture_used=False,game_input_sent=False,
        live_dib_history_verified=False,input_authorized=False)
