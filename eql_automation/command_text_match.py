"""Bounded fixed-command pixel comparisons; never a chat-focus classifier.

Renderings must come from an explicit caller-supplied, pinned source. This
module has no default font or renderer: saved font style 3 does not establish
the running client's glyphs. The constant-background model is a diagnostic
hypothesis. Even an exact pixel match proves neither delivery nor ownership.
"""
from dataclasses import dataclass
from hashlib import sha256
import math

from PIL import Image, ImageChops

from .chat_ui_frame import ChatInputFrame
from .command_submission import CommandSubmissionSnapshot, LOCATION_COMMAND, LOCATION_EVENTS


PREFIXES = tuple(LOCATION_COMMAND[:n] for n in range(1,len(LOCATION_COMMAND)+1))


@dataclass(frozen=True)
class PrefixRendering:
    prefix: str
    variant: str
    width: int
    height: int
    rgba: bytes
    # None is a fully specified hypothesis. Zero means the source sampler
    # cannot determine that pixel, never transparent or background.
    known_pixels: bytes | None = None


@dataclass(frozen=True,init=False)
class CommandTextMatcher:
    """Prepare explicit immutable renderings; observe only inside a frame pass.

    Origins and tolerance are declared hypotheses, shared by all prefixes.
    No translation/font search is added implicitly. Render the caret as an
    explicit variant if needed; no suffix pixels are ignored as 'probably a
    caret'. All nine prefixes are required to compare missing/extra letters.
    """
    renderings: tuple[PrefixRendering,...]
    origins: tuple[tuple[int,int],...]
    tolerance: int
    source_sha256: str

    def __init__(self,renderings,*,source_sha256,origins,pixel_tolerance):
        renderings=tuple(renderings);origins=tuple(origins)
        if (not 9<=len(renderings)<=32 or any(not isinstance(t,PrefixRendering) for t in renderings)
                or {t.prefix for t in renderings}!=set(PREFIXES)
                or len({(t.prefix,t.variant) for t in renderings})!=len(renderings)):
            raise ValueError('Nine fixed prefixes with unique bounded rendering variants required')
        if (not isinstance(source_sha256,str) or len(source_sha256)!=64
                or any(c not in '0123456789abcdef' for c in source_sha256)):
            raise ValueError('Pinned rendering provenance SHA256 required')
        if (not 1<=len(origins)<=25 or any(not isinstance(p,tuple) or len(p)!=2
                or any(type(v) is not int or v<0 for v in p) for p in origins)
                or len(set(origins))!=len(origins)):
            raise ValueError('One to 25 unique explicit pixel origins required')
        if type(pixel_tolerance) is not int or not 0<=pixel_tolerance<=255:
            raise ValueError('Explicit pixel tolerance must be an integer byte')
        for t in renderings:
            if (not isinstance(t.variant,str) or not t.variant or len(t.variant)>80
                    or type(t.width) is not int or type(t.height) is not int
                    or not 1<=t.width<=2048 or not 1<=t.height<=64
                    or type(t.rgba) is not bytes or len(t.rgba)!=t.width*t.height*4):
                raise ValueError('Bounded immutable RGBA rendering required')
            if (t.known_pixels is not None and (type(t.known_pixels) is not bytes
                    or len(t.known_pixels)!=t.width*t.height
                    or any(v not in (0,255) for v in t.known_pixels))):
                raise ValueError('Known-pixel mask must contain one immutable 0/255 byte per pixel')
            image=Image.frombytes('RGBA',(t.width,t.height),t.rgba)
            support=image.getchannel('A').point([0]+[255]*255)
            if support.getbbox() is None:raise ValueError('Empty glyph rendering')
        if sum(t.width*t.height*3 for t in renderings)*len(origins)>6_000_000:
            raise ValueError('Command rendering comparison budget exceeded')
        object.__setattr__(self,'renderings',renderings)
        object.__setattr__(self,'origins',origins)
        object.__setattr__(self,'tolerance',pixel_tolerance)
        object.__setattr__(self,'source_sha256',source_sha256)

    def __call__(self,chat_frame,submission,*,phase,capture_started_at):
        base=dict(format='eql-command-text-candidates-v1',status='unavailable',
            rendering_source_sha256=self.source_sha256,focus='unknown',draft_ownership='unknown',
            client_delivery_verified=False,font_rendering_live_verified=False,
            background_model_live_verified=False,text_recognized=False,input_authorized=False)
        if not isinstance(submission,CommandSubmissionSnapshot):
            return dict(base,reason='missing_command_snapshot')
        base.update(operation_id=submission.operation_id,submission_revision=submission.revision,
                    submitted_prefix=submission.submitted_prefix)
        if phase!='command_key':return dict(base,reason='not_a_drafting_phase')
        count=submission.submitted_key_count
        if (submission.uncertain or submission.enter_submitted or type(count) is not int
                or not 1<=count<=len(LOCATION_COMMAND) or submission.command!=LOCATION_COMMAND
                or submission.submitted_prefix!=LOCATION_COMMAND[:count]
                or len(submission.writes)!=count*4
                or any(not w.complete or w.event!=LOCATION_EVENTS[i] for i,w in enumerate(submission.writes))
                or any(a.finished_at>b.started_at for a,b in zip(submission.writes,submission.writes[1:]))):
            return dict(base,reason='incomplete_or_uncertain_command_snapshot')
        if (type(capture_started_at) not in (int,float) or not math.isfinite(capture_started_at)
                or capture_started_at<submission.writes[-1].finished_at):
            return dict(base,reason='frame_predates_submitted_prefix')
        if not isinstance(chat_frame,ChatInputFrame):
            return dict(base,reason='missing_chat_frame')
        crop=chat_frame.images.get('client')
        if (not isinstance(crop,Image.Image) or crop.mode!='RGB'
                or not 1<=crop.width<=2048 or not 1<=crop.height<=64):
            return dict(base,reason='unsupported_chat_crop')
        # Refuse the whole bank if any candidate clips. Dropping a competing
        # prefix would make the shorter expected text spuriously look best.
        if any(x+t.width>crop.width or y+t.height>crop.height
               for t in self.renderings for x,y in self.origins):
            return dict(base,reason='rendering_bank_clips_chat_crop')
        rgb=crop.tobytes();crop_digest=sha256(rgb).hexdigest()
        # Every model, including blank, is compared on the SAME intersection.
        # A candidate cannot improve its score by hiding its own extra glyphs.
        shared=Image.new('L',crop.size,255)
        for t in self.renderings:
            if t.known_pixels is None:continue
            known=Image.frombytes('L',(t.width,t.height),t.known_pixels)
            for x,y in self.origins:
                box=(x,y,x+t.width,y+t.height)
                shared.paste(ImageChops.darker(shared.crop(box),known),box)
        known_count=shared.histogram()[255]
        if not known_count:return dict(base,reason='no_shared_known_pixels')
        unknown_count=crop.width*crop.height-known_count
        shared_mask=shared if unknown_count else None
        background=tuple(_median(channel.histogram(shared_mask)) for channel in crop.split())
        difference=ImageChops.difference(crop,Image.new('RGB',crop.size,background))
        whole=_stats(difference,self.tolerance,shared_mask)
        right_errors,right_counts=_right_suffixes(difference,self.tolerance,shared_mask)
        rows=[]
        for t in self.renderings:
            rgba=Image.frombytes('RGBA',(t.width,t.height),t.rgba)
            support=rgba.getchannel('A').point([0]+[255]*255)
            digest=sha256(t.rgba).hexdigest()
            for x,y in self.origins:
                box=(x,y,x+t.width,y+t.height)
                observed=crop.crop(box)
                predicted=Image.new('RGB',rgba.size,background)
                predicted.paste(rgba,mask=rgba.getchannel('A'))
                delta=ImageChops.difference(observed,predicted)
                mask=shared.crop(box) if shared_mask is not None else None
                old=_stats(difference.crop(box),self.tolerance,mask)
                patch=_stats(delta,self.tolerance,mask)
                glyph=_stats(delta,self.tolerance,support if mask is None else ImageChops.darker(support,mask))
                squared=whole[0]-old[0]+patch[0]
                mismatches=whole[1]-old[1]+patch[1]
                right=(right_errors[x+t.width],right_counts[x+t.width])
                rows.append(dict(prefix=t.prefix,variant=t.variant,origin=(x,y),rgba_sha256=digest,
                    squared_error=squared,mean_squared_error=squared/(3*known_count),
                    mismatching_pixels=mismatches,outside_glyph_squared_error=squared-glyph[0],
                    outside_glyph_mismatching_pixels=mismatches-glyph[1],
                    right_of_rendering_squared_error=right[0],right_of_rendering_mismatching_pixels=right[1],
                    shared_known_pixels_match=mismatches==0,
                    declared_pixel_model_match=unknown_count==0 and mismatches==0))
        # Blank is a competing pixel model only; it never establishes closure.
        rows.append(dict(prefix='',variant='constant_background',origin=None,rgba_sha256=None,
            squared_error=whole[0],mean_squared_error=whole[0]/(3*known_count),
            mismatching_pixels=whole[1],outside_glyph_squared_error=whole[0],
            outside_glyph_mismatching_pixels=whole[1],right_of_rendering_squared_error=whole[0],
            right_of_rendering_mismatching_pixels=whole[1],shared_known_pixels_match=whole[1]==0,
            declared_pixel_model_match=unknown_count==0 and whole[1]==0))
        rows.sort(key=lambda row:row['squared_error'])
        expected=next(row for row in rows if row['prefix']==submission.submitted_prefix)
        alternate=next(row for row in rows if row['prefix']!=submission.submitted_prefix)
        matching_expected=sum(row['declared_pixel_model_match'] and row['prefix']==submission.submitted_prefix
                              for row in rows)
        if sha256(crop.tobytes()).hexdigest()!=crop_digest:
            raise ValueError('Chat pixels changed during text comparison')
        return dict(base,status='pixel_candidates_only',reason=None,frame_rgb_sha256=chat_frame.frame_rgb_sha256,
            crop_rgb_sha256=crop_digest,crop_size=crop.size,capture_started_at=capture_started_at,
            background_model='shared_per_channel_median_constant_rgb',background_rgb=background,
            pixel_tolerance=self.tolerance,ranked_candidates=rows,expected_candidate=expected,
            shared_known_pixel_count=known_count,unknown_pixel_count=unknown_count,
            complete_field_compared=unknown_count==0,
            shared_known_mask_sha256=sha256(shared.tobytes()).hexdigest(),
            prefix_unique_on_shared_known_pixels=(any(row['shared_known_pixels_match']
                and row['prefix']==submission.submitted_prefix for row in rows)
                and not any(row['shared_known_pixels_match']
                and row['prefix']!=submission.submitted_prefix for row in rows)),
            best_alternate_candidate=alternate,matching_expected_candidates=matching_expected,
            expected_error_margin=alternate['squared_error']-expected['squared_error'],
            exact_prefix_unique_under_declared_model=(matching_expected>0
                and not any(row['declared_pixel_model_match'] and row['prefix']!=submission.submitted_prefix for row in rows)))


def _median(histogram):
    threshold=(sum(histogram)+1)//2
    cumulative=0
    for value,count in enumerate(histogram):
        cumulative+=count
        if cumulative>=threshold:return value
    raise ValueError('Empty background histogram')


def _stats(difference,tolerance,mask=None):
    if not difference.width or not difference.height:return (0,0)
    histogram=difference.histogram(mask=mask)
    squared=sum((index%256)**2*count for index,count in enumerate(histogram))
    red,green,blue=difference.split()
    maximum=ImageChops.lighter(ImageChops.lighter(red,green),blue).histogram(mask=mask)
    return squared,sum(maximum[tolerance+1:])


def _right_suffixes(difference,tolerance,mask=None):
    """One whole-field pass, never a whole tail scan per hypothesis."""
    errors=[0]*(difference.width+1);counts=[0]*(difference.width+1)
    values=iter(difference.tobytes())
    known=None if mask is None else mask.tobytes()
    for index,(red,green,blue) in enumerate(zip(values,values,values)):
        if known is not None and not known[index]:continue
        x=index%difference.width
        errors[x]+=red*red+green*green+blue*blue
        counts[x]+=max(red,green,blue)>tolerance
    for x in range(difference.width-1,-1,-1):
        errors[x]+=errors[x+1];counts[x]+=counts[x+1]
    return errors,counts
