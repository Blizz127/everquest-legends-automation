"""Rank source combat sprites against a saved owner crop; no live state claim.

Sizing comes from the client's decal and saved scale, not the containing button
height. Nearest/bilinear resizing and straight-alpha compositing over arbitrary
8-bit backgrounds are explicit diagnostic hypotheses, not verified client
rendering behavior. A low residual, even zero, never establishes scene safety.
"""
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path

from .combat_ui_atlas import CombatUiAtlas, _pinned


CONTROL = 'PlayerWindow__PW_CombatStateAnim'
MAX_COMPARISONS = 6_000_000


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
    observed=[image.getpixel((x,y)) for y in range(image.height) for x in range(image.width)]
    best={};ties={}
    for frame in frames:
        for width,height in sizes:
            if width>image.width or height>image.height:continue
            for filter_name,filter_value in (('nearest',Image.Resampling.NEAREST),
                                              ('bilinear',Image.Resampling.BILINEAR)):
                template=frame.image().resize((width,height),filter_value)
                pixels=[template.getpixel((x,y)) for y in range(height) for x in range(width)]
                mass=sum(p[3] for p in pixels)
                if not mass:continue
                bounds=[(i%width,i//width,tuple((v*a,v*a+255*(255-a)) for v in (r,g,b)))
                        for i,(r,g,b,a) in enumerate(pixels) if a]
                opaque=sum(p[3]==255 for p in pixels)
                for y in range(image.height-height+1):
                    for x in range(image.width-width+1):
                        residual=violations=0
                        for dx,dy,channels in bounds:
                            sample=observed[(y+dy)*image.width+x+dx]
                            for value,(lo,hi) in zip(sample,channels):
                                outside=max(lo-value*255,value*255-hi,0)
                                residual+=max(2*outside-255,0)
                                violations+=outside*2>255
                        score=residual/(6*mass)
                        candidate=dict(animation=frame.animation,frame_index=frame.index,
                            source_rgba_sha256=frame.rgba_sha256,filter_hypothesis=filter_name,
                            crop_box=[x,y,x+width,y+height],alpha_mass_pixels=mass/255,
                            opaque_pixels=opaque,constrained_channels=len(bounds)*3,
                            incompatible_channels=violations,mean_interval_residual=score)
                        prior=best.get(frame.animation)
                        if prior is None or score<prior['mean_interval_residual']:
                            best[frame.animation]=candidate;ties[frame.animation]=1
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
