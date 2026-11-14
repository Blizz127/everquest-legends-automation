"""Read an isolated GDI probe and reproduce the copied alpha4 glyph model.

This imports no display/Wine/input library and never starts a process. Selected
font bytes and LOGFONTA must match explicit pins. Probe glyphs are an isolated
renderer hypothesis, not observations of the running client. Final texture
sampling, scale compensation, language mapping and overrides are not applied.
"""
from dataclasses import dataclass
from hashlib import sha256
import struct

from PIL import Image

from .command_text_match import PrefixRendering, PREFIXES

GLYPHS = tuple(map(ord,'/locatin|'))  # Unique input characters, in probe order.
RASTER_RUNTIME_SHA256 = '4f5f18ee9821b3e15ff25980dda7def1b2cfcdfd72a5d359ac02d0b546163168'


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
            isolated_renderer=True,final_texture_sampling_applied=False,
            scale_compensation_applied=False,live_font_binding_verified=False,
            live_raster_equivalence_verified=False,input_authorized=False)

    def prefix_renderings(self,*,include_caret=True):
        """Compose independently rasterized glyphs at their GDI advances.

        The raw alpha4 texture model is retained at its probe size. No guessed
        interpolation or live DPI/font selection is introduced here.
        """
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
    if take(8)!=b'EQLGDI1\0':raise ValueError('Unknown GDI probe format')
    version,width,height,count,font_size=struct.unpack('<5I',take(20))
    if version!=1 or not 1<=width<=128 or not 1<=height<=64 or count!=len(GLYPHS) or not 1<=font_size<=32*1024*1024:
        raise ValueError('Unsupported probe dimensions or font size')
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
    return GdiFontProbe(expected_sha256,font_sha256,descriptor_sha256,width,height,descriptor,metrics,face,tuple(glyphs))
