"""Rank source combat sprites against a saved owner crop; no live state claim.

Sizing comes from the client's decal and saved scale, not the containing button
height. Nearest/bilinear resizing and straight-alpha compositing over arbitrary
8-bit backgrounds are explicit diagnostic hypotheses, not verified client
rendering behavior. A low residual, even zero, never establishes scene safety.
"""
from hashlib import sha256
from io import BytesIO
from array import array
from functools import lru_cache
import json
import math
from pathlib import Path

from .combat_ui_atlas import CombatUiAtlas, _pinned


CONTROL = 'PlayerWindow__PW_CombatStateAnim'
MAX_COMPARISONS = 6_000_000
_BATCH_PLACEMENTS = 16
_CHANNEL_SCALE = [value*510 for value in range(256)]


@lru_cache(maxsize=128)
def _compile_template(frame, width, height, filter_name):
    """Cache immutable integer bounds; key includes the actual source bytes."""
    from PIL import Image
    filter_value={'nearest':Image.Resampling.NEAREST,'bilinear':Image.Resampling.BILINEAR}[filter_name]
    pixels=frame.image().resize((width,height),filter_value).tobytes()
    lower,upper=array('i'),array('i')
    if lower.itemsize!=4:raise RuntimeError('Pillow integer matching requires 32-bit native integers')
    mass=opaque=constrained=0
    for offset in range(0,len(pixels),4):
        r,g,b,a=pixels[offset:offset+4]
        mass+=a;opaque+=a==255;constrained+=3*(a>0)
        for value in (r,g,b):
            # The doubled original residual includes half an 8-bit unit of
            # rounding slack. Values fit signed 32 bits, including alpha=0.
            lower.append(2*value*a-255)
            upper.append(2*(value*a+255*(255-a))+255)
    return lower.tobytes(),upper.tobytes(),mass,opaque,constrained


@lru_cache(maxsize=1)
def _numpy_backend():
    # The retained gauge reader already uses NumPy on the owner machine.
    # Offline installations with Pillow alone retain the exact fallback.
    try:
        import numpy
    except ModuleNotFoundError as error:
        if error.name != 'numpy':raise
        return None
    return numpy


def _score_positions_numpy(observed, width, height, lower, upper):
    """Same native-int channel residuals; bounded batches and int64 sums."""
    import numpy as np
    source=np.asarray(observed,dtype=np.int32)
    lo=np.frombuffer(lower,dtype='=i4').reshape(height,3*width)
    hi=np.frombuffer(upper,dtype='=i4').reshape(height,3*width)
    positions=[(x,y) for y in range(observed.height-height+1)
               for x in range(observed.width//3-width+1)]
    for begin in range(0,len(positions),_BATCH_PLACEMENTS):
        batch=positions[begin:begin+_BATCH_PLACEMENTS]
        packed=np.empty((len(batch),height,3*width),dtype=np.int32)
        for index,(x,y) in enumerate(batch):
            packed[index]=source[y:y+height,3*x:3*(x+width)]
        # Every channel fits int32, but a 128x128 template sum can exceed it.
        residual=np.maximum(lo-packed,packed-hi)
        np.maximum(residual,0,out=residual)
        totals=residual.sum(axis=(1,2),dtype=np.int64)
        pixels=residual.reshape(len(batch),-1)
        pixels.flags.writeable=False
        for index,(x,y) in enumerate(batch):
            yield x,y,int(totals[index]),pixels[index]


def _score_positions(observed, width, height, lower, upper):
    scorer=_score_positions_pillow if _numpy_backend() is None else _score_positions_numpy
    yield from scorer(observed,width,height,lower,upper)


def _incompatible_count(pixels):
    np=_numpy_backend()
    return sum(value>0 for value in pixels) if np is None else int(np.count_nonzero(pixels))


def _score_positions_pillow(observed, width, height, lower, upper):
    """Yield exact integer residuals in original y/x order, in bounded batches.

    RGB channels occupy adjacent columns of one I-mode image. ImageStat's
    quantized I-mode histograms cannot sum these values exactly, so totals
    use the native 32-bit output buffer instead.
    """
    from PIL import Image,ImageMath
    positions=[(x,y) for y in range(observed.height-height+1)
               for x in range(observed.width//3-width+1)]
    channel_count=width*height*3
    for begin in range(0,len(positions),_BATCH_PLACEMENTS):
        batch=positions[begin:begin+_BATCH_PLACEMENTS]
        packed=Image.new('I',(3*width,height*len(batch)))
        for index,(x,y) in enumerate(batch):
            packed.paste(observed.crop((3*x,y,3*(x+width),y+height)),(0,index*height))
        lo=Image.frombytes('I',packed.size,lower*len(batch))
        hi=Image.frombytes('I',packed.size,upper*len(batch))
        residual=ImageMath.lambda_eval(
            lambda v:v['max'](v['max'](v['lo']-v['pixels'],v['pixels']-v['hi']),0),
            lo=lo,hi=hi,pixels=packed)
        values=memoryview(residual.tobytes()).cast('i')
        for index,(x,y) in enumerate(batch):
            pixels=values[index*channel_count:(index+1)*channel_count]
            yield x,y,sum(pixels),pixels


def decal_sizes(atlas: CombatUiAtlas, scale: float):
    if (isinstance(scale,bool) or not isinstance(scale,(int,float))
            or not math.isfinite(scale) or not .25 <= scale <= 4):
        raise ValueError('Unsupported saved UI scale')
    widgets=[w for w in atlas.widget_definitions if w['item']=='PW_CombatStateAnim']
    if len(widgets)!=1 or widgets[0]['decal_size'] is None:
        raise ValueError('Client combat decal dimensions are missing')
    width,height=widgets[0]['decal_size']
    # Independent floor/ceil sizes allow rounding at different screen origins.
    # They are hypotheses only; the containing widget may be taller than this.
    return tuple(sorted({(w,h) for w in (math.floor(width*scale),math.ceil(width*scale))
        for h in (math.floor(height*scale),math.ceil(height*scale)) if 1<=w<=128 and 1<=h<=128}))


def rank_combat_sprites(image, atlas: CombatUiAtlas, *, saved_scale: float):
    """Return one representative best box per animation and its tie count.

    For each channel, unknown background B is allowed in [0,255]:
    C lies in [alpha*T, alpha*T+(1-alpha)*255]. Residual is distance outside
    that interval, with half an 8-bit unit for output rounding, normalized by
    alpha mass. Transparent pixels cannot distinguish sprites. No threshold or
    accepted state is returned, and background consistency is not established.
    """
    from PIL import Image
    if image.mode!='RGB' or not 1<=image.width<=128 or not 1<=image.height<=128:
        raise ValueError('Expected a bounded RGB combat control crop')
    sizes=decal_sizes(atlas,saved_scale)
    frames=[f for f in atlas.frames if f.animation.startswith('A_PWCS')]
    if not frames:raise ValueError('No source combat sprites')
    operations=sum((image.width-w+1)*(image.height-h+1)*w*h
        for w,h in sizes if w<=image.width and h<=image.height)*len(frames)*2
    if operations>MAX_COMPARISONS:raise ValueError('Diagnostic search exceeds comparison budget')
    observed=Image.frombytes('L',(image.width*3,image.height),image.tobytes()).point(_CHANNEL_SCALE,'I')
    best={};ties={}
    for frame in frames:
        for width,height in sizes:
            if width>image.width or height>image.height:continue
            for filter_name in ('nearest','bilinear'):
                lower,upper,mass,opaque,constrained=_compile_template(frame,width,height,filter_name)
                if not mass:continue
                for x,y,residual,pixels in _score_positions(observed,width,height,lower,upper):
                    score=residual/(6*mass)
                    prior=best.get(frame.animation)
                    if prior is None or score<prior['mean_interval_residual']:
                        best[frame.animation]=dict(animation=frame.animation,frame_index=frame.index,
                            source_rgba_sha256=frame.rgba_sha256,filter_hypothesis=filter_name,
                            crop_box=[x,y,x+width,y+height],alpha_mass_pixels=mass/255,
                            opaque_pixels=opaque,constrained_channels=constrained,
                            incompatible_channels=_incompatible_count(pixels),mean_interval_residual=score)
                        ties[frame.animation]=1
                    elif score==prior['mean_interval_residual']:
                        ties[frame.animation]+=1
    ranking=sorted(best.values(),key=lambda c:(c['mean_interval_residual'],c['animation']))
    for candidate in ranking:candidate['equal_best_hypotheses']=ties[candidate['animation']]
    return dict(ranked_candidates=ranking,declared_decal_size_hypotheses=[list(s) for s in sizes],
        comparison_pixel_budget_used=operations,
        ranking_gap=(ranking[1]['mean_interval_residual']-ranking[0]['mean_interval_residual']
                     if len(ranking)>1 else None),
        diagnostic_model='straight_alpha_8bit_unknown_background_half_unit_rounding',
        selected_state=None,input_authorized=False,g2_safety_flags_provided=False,
        active_skin_verified=False,scaling_compositing_verified=False,live_state_verified=False)


def analyze_saved_combat_crop(metadata_path: Path, *, metadata_sha256: str,
                              atlas: CombatUiAtlas):
    """Read only the pinned metadata and its exact control PNG, not a display."""
    from PIL import Image
    metadata_path=Path(metadata_path)
    data=_pinned(metadata_path,metadata_sha256,1024*1024)
    metadata=json.loads(data)
    if (not isinstance(metadata,dict) or metadata.get('format')!='eql-owner-ui-observation-v1'
            or metadata.get('game_input_sent') is not False
            or metadata.get('saved_layout_is_live_verified') is not False
            or metadata.get('ui_skin_from_saved_ini')!=atlas.saved_skin):
        raise ValueError('Unsupported capture or different saved UI skin')
    sources=metadata.get('source_sha256_postcapture')
    if not isinstance(sources,dict):raise ValueError('Capture has no UI source provenance')
    atlas_xml={name:digest for name,digest in atlas.source_sha256 if name.lower().endswith('.xml')}
    for name,digest in atlas_xml.items():
        matching=[v for path,v in sources.items() if Path(path).name==name]
        if matching!=[digest]:raise ValueError('Captured client UI XML does not match the atlas')
    window=metadata.get('window_size')
    if (not isinstance(window,list) or len(window)!=2
            or any(type(v) is not int or not 1<=v<=7680 for v in window)):
        raise ValueError('Invalid captured window dimensions')
    if not isinstance(metadata.get('crops'),dict):raise ValueError('Missing crop inventory')
    crop=metadata['crops'].get(CONTROL)
    if (not isinstance(crop,dict) or crop.get('file')!=CONTROL+'.png'
            or not isinstance(crop.get('box'),list) or len(crop['box'])!=4
            or any(type(v) is not int for v in crop['box'])):
        raise ValueError('Missing exact combat control crop')
    x0,y0,x1,y1=crop['box']
    if not (0<=x0<x1<=window[0] and 0<=y0<y1<=window[1]
            and x1-x0<=128 and y1-y0<=128):
        raise ValueError('Combat control crop is outside bounded captured coordinates')
    pixels=_pinned(metadata_path.parent/crop['file'],crop['sha256'],5*1024*1024)
    with Image.open(BytesIO(pixels)) as source:
        if source.format!='PNG' or source.mode!='RGB' or source.size!=(x1-x0,y1-y0):
            raise ValueError('Combat control PNG does not match metadata dimensions/mode')
        image=source.copy()
    parent_verified=False
    parent=metadata['crops'].get('PlayerWindow')
    if parent is not None:
        if (not isinstance(parent,dict) or parent.get('file')!='PlayerWindow.png'
                or not isinstance(parent.get('box'),list) or len(parent['box'])!=4
                or any(type(v) is not int for v in parent['box'])):
            raise ValueError('Invalid player window crop')
        px0,py0,px1,py1=parent['box']
        if not (0<=px0<=x0<x1<=px1<=window[0] and 0<=py0<=y0<y1<=py1<=window[1]):
            raise ValueError('Combat crop is outside its saved player window')
        parent_data=_pinned(metadata_path.parent/parent['file'],parent['sha256'],8*1024*1024)
        with Image.open(BytesIO(parent_data)) as source:
            if (source.format!='PNG' or source.mode!='RGB' or source.size!=(px1-px0,py1-py0)
                    or source.width*source.height>2_000_000):
                raise ValueError('Player window PNG does not match its bounded metadata')
            if source.crop((x0-px0,y0-py0,x1-px0,y1-py0)).tobytes()!=image.tobytes():
                raise ValueError('Combat crop differs from the same captured player window')
        parent_verified=True
    result=rank_combat_sprites(image,atlas,saved_scale=metadata.get('ui_scale_from_saved_ini'))
    result.update(format='eql-owner-combat-crop-ranking-v1',capture_metadata_sha256=sha256(data).hexdigest(),
        capture_crop_sha256=sha256(pixels).hexdigest(),atlas_manifest_sha256=atlas.manifest_sha256,
        capture_control_box=crop['box'],saved_scale=metadata['ui_scale_from_saved_ini'],
        child_pixels_match_saved_parent=parent_verified,
        captured_xml_matches_copied_atlas=True,
        captured_texture_identity_verified=False,
        captured_frame_sha256_not_revalidated=metadata.get('frame_rgb_sha256'),
        source_timestamps_unverified={key:metadata.get(key) for key in
            ('capture_started_utc','capture_ended_utc')},
        native_melee_off_verified=False,no_incoming_attack_verified=False,
        standing_icon_can_also_be_null_player_fallback=True)
    return result
