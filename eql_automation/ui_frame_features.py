"""Read gauge candidates and combat sprites from one ephemeral client frame.

This is the concrete pixel-reading stage, not the complete scene classifier.
It does not infer chat focus, player presence or target absence from empty
pixels, and source-proposed rectangles still require live alignment checks.
"""
from hashlib import sha256
import math
from pathlib import Path
import time

from .combat_ui_match import (CONTROL, rank_combat_sprites, decal_sizes,
                              _numpy_backend, _compile_template, _score_positions)
from .combat_ui_atlas import CombatUiAtlas
from .owner_ui_observation import UiFrameSample, sample_focused_ui
from .chat_ui_frame import chat_regions_from_sample
from .chat_ui_layout import ChatLayoutUnavailable


class PreparedUiFrameReader:
    """Initialize numerical work before an observation scope begins.

    Construction reads no display or input device. It compiles source sprite
    bounds and exercises one synthetic numerical batch, discarding its result.
    Every invocation still captures a new frame and reports its actual timing.
    Preparation is neither a previous scene nor a latency/authorization claim.
    """
    def __init__(self, *, gate, layout_loader, game, character, server, atlas,
                 gauge_reader, saved_scale, chat_runtime_sha256=None, command_text_matcher=None,
                 still_current=lambda:None, clock=time.monotonic):
        if (not isinstance(atlas,CombatUiAtlas) or not callable(layout_loader)
                or not callable(gauge_reader) or not callable(clock) or not callable(still_current)):
            raise ValueError('Source atlas, layout and gauge readers required')
        began=clock()
        if type(began) not in (int,float) or not math.isfinite(began):
            raise ValueError('Invalid preparation clock')
        self.atlas,self.scale,self.clock=atlas,saved_scale,clock
        self.sizes=decal_sizes(atlas,saved_scale)
        frames=[f for f in atlas.frames if f.animation.startswith('A_PWCS')]
        if not frames or not self.sizes:raise ValueError('Source combat templates unavailable')
        np=_numpy_backend()
        count=0
        for frame in frames:
            for width,height in self.sizes:
                for resize in ('nearest','bilinear'):
                    _compile_template(frame,width,height,resize)
                    count+=1
        from PIL import Image
        width,height=self.sizes[0]
        lo,hi,*_=_compile_template(frames[0],width,height,'nearest')
        # Trigger the chosen backend's lazy setup without a game frame.
        for _ in _score_positions(Image.new('I',(3*width,height)),width,height,lo,hi):pass
        finished=clock()
        if type(finished) not in (int,float) or not math.isfinite(finished) or finished<began:
            raise ValueError('Invalid preparation clock')
        self.preparation=dict(started_at=began,finished_at=finished,seconds=finished-began,
            backend='pillow' if np is None else 'numpy',compiled_templates=count,
            atlas_manifest_sha256=atlas.manifest_sha256,saved_scale=saved_scale,
            game_capture_used=False,game_input_sent=False,contains_scene_observation=False,
            input_authorized=False,observation_latency_guaranteed=False)
        def bound_layout(*args,**kwargs):
            layout=layout_loader(*args,**kwargs)
            if layout.skin!=atlas.saved_skin or layout.ui_scale!=saved_scale:
                raise ValueError('Saved skin/scale changed after reader preparation')
            return layout
        self.arguments=dict(gate=gate,layout_loader=bound_layout,game=game,character=character,
            server=server,atlas=atlas,gauge_reader=gauge_reader,chat_runtime_sha256=chat_runtime_sha256,
            command_text_matcher=command_text_matcher,still_current=still_current,clock=clock)

    def __call__(self, *, command_submission=None, command_phase=None):
        if decal_sizes(self.atlas,self.scale)!=self.sizes:
            raise ValueError('Template dimensions changed after reader preparation')
        result=read_focused_ui_features(**self.arguments,command_submission=command_submission,
                                       command_phase=command_phase)
        if result['sample_started_at']<self.preparation['finished_at']:
            raise ValueError('Frame observation predates reader preparation')
        result['reader_preparation']=dict(self.preparation)
        return result


def _crop(sample, name):
    box=sample.boxes.get(name)
    if (not isinstance(box,tuple) or len(box)!=4 or any(type(v) is not int for v in box)
            or not 0<=box[0]<box[2]<=sample.image.width
            or not 0<=box[1]<box[3]<=sample.image.height):
        return None
    return sample.image.crop(box)


def analyze_ui_frame(sample, *, atlas, gauge_reader, chat_runtime_sha256=None,
                     command_text_matcher=None, command_submission=None, command_phase=None, still_current=lambda:None,
                     clock=time.monotonic):
    """Use the retained gauge reader and source sprites, without PNG round trips.

    `gauge_reader` is the caller's existing rotation_core.bar_fraction. The
    returned candidates do not write Engine.hp/mana or change input state.
    Timings include the entire sample interval, not just the matching loop.
    """
    if (not isinstance(sample,UiFrameSample) or not isinstance(atlas,CombatUiAtlas)
            or not callable(gauge_reader) or sample.image.mode!='RGB'
            or sample.metadata['ui_skin_from_saved_ini']!=atlas.saved_skin):
        raise ValueError('Bound RGB sample, source atlas and existing gauge reader required')
    still_current()
    began=clock()
    first=sample.metadata['sample_started_monotonic']
    captured=sample.metadata['capture_started_monotonic']
    sampled=sample.metadata['sample_finished_monotonic']
    if (not all(type(v) in (int,float) and math.isfinite(v) for v in (first,captured,sampled,began))
            or not first<=captured<=sampled<=began):
        raise ValueError('Invalid frame observation interval')
    if sha256(sample.image.tobytes()).hexdigest()!=sample.metadata['frame_rgb_sha256']:
        raise ValueError('Frame pixels changed after sampling')
    # Same XML provenance check as the saved-crop analyzer. This still does
    # not prove which textures the running process actually rendered.
    xml={name:digest for name,digest in atlas.source_sha256 if name.lower().endswith('.xml')}
    if not xml:raise ValueError('Atlas lacks source XML provenance')
    for name,digest in xml.items():
        if [v for p,v in sample.sources.items() if Path(p).name==name]!=[digest]:
            raise ValueError('Frame source XML does not match the atlas')
    gauges={}
    for role,control,channel in (('hp','Player_HP','red'),('mana','Player_Mana','blue')):
        still_current()
        name='PlayerWindow__'+control
        image=_crop(sample,name)
        value=None;reason='missing_inner_gauge'
        if image is not None and image.width>=20 and 5<=image.height<=24:
            value=gauge_reader(image,channel)
            if value is not None and (type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=1):
                raise ValueError('Gauge reader returned an invalid fraction')
            reason='colored_band_candidate' if value is not None else 'band_unrecognized'
        gauges[role]=dict(fraction_candidate=value,reason=reason,box=sample.boxes.get(name))
    still_current()
    combat=_crop(sample,CONTROL)
    ranking=(None if combat is None else rank_combat_sprites(combat,atlas,
        saved_scale=sample.metadata['ui_scale_from_saved_ini']))
    chat_input=dict(status='not_requested',focus='unknown',draft='unknown')
    if chat_runtime_sha256 is not None:
        still_current()
        try:
            chat_frame=chat_regions_from_sample(sample,copied_binary_sha256=chat_runtime_sha256)
            chat_input=chat_frame.summary()
            if command_text_matcher is not None:
                from .command_text_match import CommandTextMatcher
                if not isinstance(command_text_matcher,CommandTextMatcher):
                    raise ValueError('Prepared fixed-prefix pixel matcher required')
                chat_input['command_text']=command_text_matcher(chat_frame,command_submission,
                    phase=command_phase,capture_started_at=captured)
        except ChatLayoutUnavailable as error:
            chat_input=dict(status='unavailable',reason=str(error),focus='unknown',draft='unknown')
    sample.check_sources()
    still_current()
    if sha256(sample.image.tobytes()).hexdigest()!=sample.metadata['frame_rgb_sha256']:
        raise ValueError('Frame changed during feature reading')
    finished=clock()
    if type(finished) not in (int,float) or not math.isfinite(finished) or finished<began:
        raise ValueError('Invalid feature observation clock')
    return dict(format='eql-ui-frame-features-v1',gauges=gauges,combat=ranking,chat_input=chat_input,
        frame_rgb_sha256=sample.metadata['frame_rgb_sha256'],window_size=sample.metadata['window_size'],
        game_session=sample.metadata['game_session'],focused_window_id=sample.metadata['focused_window_id'],
        atlas_manifest_sha256=atlas.manifest_sha256,source_sha256_postcapture=dict(sample.sources),
        crop_boxes=dict(sample.boxes),saved_skin=atlas.saved_skin,
        layout_preparation=sample.metadata.get('layout_preparation'),
        sample_started_at=first,capture_started_at=captured,sample_finished_at=sampled,
        feature_started_at=began,feature_finished_at=finished,
        capture_seconds=sample.metadata['capture_duration_monotonic_seconds'],
        sampling_seconds=sampled-first,feature_seconds=finished-began,total_seconds=finished-first,
        frame_age_seconds=finished-captured,within_100ms_sample_budget=finished-first<=.1,
        budget_excludes_owner_input_and_log_scans=True,
        saved_layout_live_verified=False,active_texture_identity_verified=False,
        player_presence_verified=False,chat_state='unknown',target_state='unknown',
        selected_combat_state=None,game_input_sent=False,input_authorized=False,
        automatic_healing_allowed=False,g2_safety_flags_provided=False)


def read_focused_ui_features(*, gate, layout_loader, game, character, server,
                             atlas, gauge_reader, chat_runtime_sha256=None,
                             command_text_matcher=None,command_submission=None,command_phase=None,
                             still_current=lambda:None,clock=time.monotonic):
    """Borrow an existing gate for one read-only sample and feature pass.

    The caller must invoke this only within its owner-started observation. It
    performs no input, file writes, gate creation/close, grabs or retries.
    """
    sample=sample_focused_ui(gate=gate,layout_loader=layout_loader,game=game,
        character=character,server=server,include_chat=False,still_current=still_current,clock=clock)
    result=analyze_ui_frame(sample,atlas=atlas,gauge_reader=gauge_reader,
        chat_runtime_sha256=chat_runtime_sha256,command_text_matcher=command_text_matcher,
        command_submission=command_submission,command_phase=command_phase,
        still_current=still_current,clock=clock)
    still_current()
    focused=gate.focused_window()
    if (focused is None or focused.id!=result['focused_window_id']
            or gate.game_session()!=result['game_session']):
        raise RuntimeError('Game focus/process changed during feature reading')
    finished=clock()
    if type(finished) not in (int,float) or not math.isfinite(finished) or finished<result['feature_finished_at']:
        raise ValueError('Invalid final observation clock')
    result.update(reader_finished_at=finished,total_seconds=finished-result['sample_started_at'],
        frame_age_seconds=finished-result['capture_started_at'],
        within_100ms_sample_budget=finished-result['sample_started_at']<=.1)
    return result
