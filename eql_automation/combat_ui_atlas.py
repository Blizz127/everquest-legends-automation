"""Extract combat/attack visual templates from pinned owner client assets.

This reads the client's animation definitions and texture pixels. It does not
classify a live frame, infer an active skin, prove widget placement, or grant
any G2/route safety flag. Runtime state selection and compositing remain to be
measured against real captures; absence of a blinking indicator is not OFF.
"""
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET


PREFIXES = ('A_PWCS', 'A_AttackIndicator')


@dataclass(frozen=True)
class AnimationFrame:
    animation: str
    index: int
    texture: str
    box: tuple[int, int, int, int]
    cycle: bool | None
    duration_ms: int | None
    hotspot: tuple[int, int] | None
    rgba_sha256: str
    rgba: bytes = field(repr=False)

    def image(self):
        from PIL import Image
        x0,y0,x1,y1 = self.box
        return Image.frombytes('RGBA', (x1-x0,y1-y0), self.rgba)

    def record(self):
        result=asdict(self)
        del result['rgba']
        return result


@dataclass(frozen=True)
class CombatUiAtlas:
    manifest_sha256: str
    saved_skin: str
    source_sha256: tuple[tuple[str,str], ...]
    frames: tuple[AnimationFrame, ...]
    widget_definitions: tuple[dict, ...]

    def record(self):
        return dict(format='eql-client-combat-atlas-v1',
            manifest_sha256=self.manifest_sha256, saved_skin=self.saved_skin,
            source_sha256=dict(self.source_sha256),
            frames=[f.record() for f in self.frames],
            widget_definitions=list(self.widget_definitions),
            live_state_verified=False, active_skin_verified=False,
            input_authorized=False, g2_safety_flags_provided=False,
            runtime_state_to_animation_verified=False,
            scaling_compositing_verified=False)


def _pinned(path, digest, limit):
    if (not isinstance(digest,str) or re.fullmatch('[0-9a-f]{64}',digest) is None
            or path.is_symlink() or not path.is_file() or path.stat().st_size>limit):
        raise ValueError('Missing, unbounded or unpinned client asset')
    data=path.read_bytes()
    if len(data)>limit or sha256(data).hexdigest()!=digest:
        raise ValueError('Client asset hash changed')
    return data


def _name(value):
    if not isinstance(value,str) or re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',value) is None or value in ('.','..'):
        raise ValueError('Asset reference must be one ordinary filename')
    return value


def _integer(element, path, *, minimum=0, optional=False):
    value=element.findtext(path)
    if value is None and optional:return None
    if value is None or re.fullmatch(r'[0-9]+',value.strip()) is None:
        raise ValueError('Missing or invalid animation integer: '+path)
    result=int(value.strip())
    if not minimum<=result<=65536:raise ValueError('Animation integer out of bounds: '+path)
    return result


def _boolean(element, path):
    value=element.findtext(path)
    if value is None:return None  # No invented client default.
    if value.strip() not in ('true','false'):raise ValueError('Unknown client boolean: '+path)
    return value.strip()=='true'


def load_combat_ui_atlas(manifest_path: Path, *, expected_sha256: str) -> CombatUiAtlas:
    """Read copied XML and textures; every input byte is hash pinned first."""
    from PIL import Image
    manifest_path=Path(manifest_path)
    manifest_bytes=_pinned(manifest_path,expected_sha256,256*1024)
    manifest=json.loads(manifest_bytes)
    if (manifest.get('format')!='eql-client-ui-assets-v1'
            or manifest.get('active_skin_verified') is not False
            or not isinstance(manifest.get('saved_skin'),str) or not manifest['saved_skin']):
        raise ValueError('Unsupported copied client asset manifest')
    xml_name=_name(manifest['xml'])
    textures=manifest['textures'];files=manifest['files']
    if (not isinstance(textures,list) or not 1<=len(textures)<=16
            or len(set(textures))!=len(textures) or xml_name in textures
            or not isinstance(files,dict) or set(files)!={xml_name,*textures}):
        raise ValueError('Incomplete or ambiguous asset inventory')
    pinned={}
    for name,item in files.items():
        _name(name)
        data=_pinned(manifest_path.parent/name,item['sha256'],5*1024*1024)
        if type(item.get('bytes')) is not int or len(data)!=item['bytes']:
            raise ValueError('Client asset size changed')
        pinned[name]=data
    xml=pinned[xml_name]
    if b'<!DOCTYPE' in xml or b'<!ENTITY' in xml:raise ValueError('External XML definitions are unsupported')
    root=ET.fromstring(xml)
    images={}
    for name in textures:
        with Image.open(BytesIO(pinned[name])) as image:
            if not (0<image.width<=4096 and 0<image.height<=4096):
                raise ValueError('Texture dimensions exceed bounded atlas size')
            images[name]=image.convert('RGBA')
    frames=[];seen=set()
    for animation in root.findall('Ui2DAnimation'):
        name=animation.get('item','')
        if not name.startswith(PREFIXES):continue
        _name(name)
        if name in seen:raise ValueError('Duplicate animation definition')
        seen.add(name)
        definitions=animation.findall('Frames')
        if not 1<=len(definitions)<=64:raise ValueError('Animation frame count is missing or unbounded')
        for index,frame in enumerate(definitions):
            texture=_name(frame.findtext('Texture'))
            if texture not in images:raise ValueError('Animation references an unpinned texture')
            image=images[texture]
            x,y=(_integer(frame,'Location/'+axis) for axis in ('X','Y'))
            w,h=(_integer(frame,'Size/'+axis,minimum=1) for axis in ('CX','CY'))
            if x+w>image.width or y+h>image.height:raise ValueError('Animation frame exceeds texture')
            hotspot=(tuple(_integer(frame,'Hotspot/'+axis) for axis in ('X','Y'))
                     if frame.find('Hotspot') is not None else None)
            box=(x,y,x+w,y+h);rgba=image.crop(box).tobytes()
            frames.append(AnimationFrame(name,index,texture,box,_boolean(animation,'Cycle'),
                _integer(frame,'Duration',minimum=1,optional=True),hotspot,sha256(rgba).hexdigest(),rgba))
    if not frames or not any(f.animation.startswith('A_PWCS') for f in frames):
        raise ValueError('Client XML contains no combat-state templates')
    widgets=[]
    for element in root:
        item=element.get('item','')
        if item!='PW_CombatStateAnim' and not (element.tag=='StaticAnimation' and item.startswith('A_AttackIndicatorAnim')):
            continue
        if any(w['item']==item for w in widgets):raise ValueError('Duplicate widget definition')
        # Keep literal links and absent fields; do not guess runtime defaults.
        widgets.append(dict(item=item,type=element.tag,screen_id=element.findtext('ScreenID'),
            animation=element.findtext('Animation'),auto_draw=_boolean(element,'AutoDraw'),
            auto_stretch=_boolean(element,'AutoStretch'),
            button_draw_template_present=element.find('ButtonDrawTemplate') is not None,
            decal_size=(tuple(_integer(element,'DecalSize/'+axis,minimum=1) for axis in ('CX','CY'))
                        if element.find('DecalSize') is not None else None)))
    return CombatUiAtlas(expected_sha256,manifest['saved_skin'],
        tuple(sorted((name,item['sha256']) for name,item in files.items())),tuple(frames),tuple(widgets))
