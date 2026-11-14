"""Synthetic glyphs only; these tests establish no actual font or chat state."""
from dataclasses import FrozenInstanceError,replace
from hashlib import sha256

from PIL import Image
import pytest

from eql_automation.chat_ui_frame import ChatInputFrame
from eql_automation.command_submission import CommandSubmissionJournal, LOCATION_EVENTS
from eql_automation.command_text_match import CommandTextMatcher, PrefixRendering, PREFIXES


def rendering(text,variant='no-caret'):
    image=Image.new('RGBA',(len(text)*5,7))
    for n,char in enumerate(text):
        bits=ord(char)
        for y in range(7):
            for x in range(3):
                if bits&(1<<((x+y)%7)):
                    image.putpixel((n*5+x,y),(255,255,255,255 if x%2 else 180))
    return PrefixRendering(text,variant,*image.size,image.tobytes())


def matcher(**kw):
    defaults=dict(source_sha256='a'*64,origins=((2,2),),pixel_tolerance=0)
    defaults.update(kw)
    return CommandTextMatcher(tuple(rendering(text) for text in PREFIXES),**defaults)


def snapshot(prefix):
    journal=CommandSubmissionJournal('synthetic-operation')
    for index,event in enumerate(LOCATION_EVENTS[:len(prefix)*4]):
        attempt=journal.begin(event,index*.01,24)
        journal.finish(attempt,index*.01+.001,written_bytes=24,outcome='complete')
    return journal.snapshot()


def frame(text,origin=(2,2),size=(90,15)):
    image=Image.new('RGB',size,(12,18,30))
    if text:
        t=rendering(text);layer=Image.frombytes('RGBA',(t.width,t.height),t.rgba)
        image.paste(layer,origin,layer.getchannel('A'))
    return ChatInputFrame({},dict(client=image),sha256(image.tobytes()).hexdigest())


def match(text,*,actual=None,prepared=None,**kwargs):
    return (prepared or matcher())(frame(text if actual is None else actual),snapshot(text),
                                   phase='command_key',capture_started_at=1.,**kwargs)


@pytest.mark.parametrize('prefix',PREFIXES)
def test_exact_prefix_is_only_a_pixel_model_match(prefix):
    result=match(prefix)
    assert result['status']=='pixel_candidates_only'
    assert result['expected_candidate']['squared_error']==0
    assert result['expected_candidate']['mismatching_pixels']==0
    assert result['ranked_candidates'][0]['prefix']==prefix
    assert result['exact_prefix_unique_under_declared_model']
    assert result['expected_error_margin']>0
    assert result['focus']==result['draft_ownership']=='unknown'
    assert not any(result[k] for k in ('input_authorized','client_delivery_verified',
        'text_recognized','font_rendering_live_verified','background_model_live_verified'))


@pytest.mark.parametrize('actual',['/location','/locx','/lo','/loc|',''])
def test_missing_extra_wrong_and_caret_text_are_not_ignored(actual):
    result=match('/loc',actual=actual)
    assert not result['expected_candidate']['declared_pixel_model_match']
    assert not result['exact_prefix_unique_under_declared_model']
    assert result['expected_candidate']['squared_error']>0
    if len(actual)>4:
        assert result['expected_candidate']['outside_glyph_mismatching_pixels']>0
        assert result['expected_candidate']['right_of_rendering_mismatching_pixels']>0


def test_unexplained_ink_inside_rendering_padding_is_counted():
    f=frame('/loc');f.images['client'].putpixel((6,3),(255,255,255))
    result=matcher()(f,snapshot('/loc'),phase='command_key',capture_started_at=1.)
    assert result['expected_candidate']['outside_glyph_mismatching_pixels']==1
    assert not result['exact_prefix_unique_under_declared_model']


def test_blank_field_never_proves_closed_chat():
    result=match('/loc',actual='')
    assert result['ranked_candidates'][0]['prefix']==''
    assert result['ranked_candidates'][0]['declared_pixel_model_match']
    assert result['focus']=='unknown' and not result['input_authorized']


def test_uniform_white_cannot_uniquely_identify_white_text():
    f=frame('');f.images['client'].paste((255,255,255),(0,0,90,15))
    result=matcher()(f,snapshot('/loc'),phase='command_key',capture_started_at=1.)
    assert result['expected_candidate']['declared_pixel_model_match']
    assert not result['exact_prefix_unique_under_declared_model']
    assert result['expected_error_margin']==0


@pytest.mark.parametrize('phase',['command_start','command_first_key','command_end','pulse_start',None])
def test_non_draft_phases_remain_unknown(phase):
    result=matcher()(frame('/loc'),snapshot('/loc'),phase=phase,capture_started_at=1.)
    assert result['status']=='unavailable' and result['reason']=='not_a_drafting_phase'


@pytest.mark.parametrize('change',['uncertain','partial','enter','wrong-prefix','reversed-clock','old-frame'])
def test_bad_submission_or_old_capture_is_not_compared(change):
    s=snapshot('/loc');at=1.
    if change=='uncertain':s=replace(s,uncertain=True)
    elif change=='partial':s=replace(s,writes=s.writes[:-1])
    elif change=='enter':s=replace(s,enter_submitted=True)
    elif change=='wrong-prefix':s=replace(s,submitted_prefix='/location')
    elif change=='reversed-clock':s=replace(s,writes=(replace(s.writes[0],finished_at=.05),)+s.writes[1:])
    else:at=0.
    result=matcher()(frame('/loc'),s,phase='command_key',capture_started_at=at)
    assert result['status']=='unavailable' and 'ranked_candidates' not in result


def test_all_competing_renderings_must_fit_even_if_expected_fits():
    result=matcher()(frame('/',size=(20,15)),snapshot('/'),phase='command_key',capture_started_at=1.)
    assert result['reason']=='rendering_bank_clips_chat_crop'


def test_explicit_origin_search_is_shared_and_bounded():
    p=matcher(origins=((2,2),(3,2)))
    result=p(frame('/loc',origin=(3,2)),snapshot('/loc'),phase='command_key',capture_started_at=1.)
    assert result['expected_candidate']['origin']==(3,2)
    assert result['expected_candidate']['squared_error']==0


def test_prepared_bank_and_rendering_bytes_are_immutable():
    p=matcher()
    with pytest.raises(FrozenInstanceError):p.tolerance=255
    with pytest.raises(FrozenInstanceError):p.renderings[0].rgba=b'changed'


def test_all_expected_variants_count_even_when_lowest_squared_error_exceeds_tolerance():
    def row(prefix,variant,values):
        pixels=b''.join(bytes((v,v,v,255 if v else 0)) for v in values)
        return PrefixRendering(prefix,variant,3,1,pixels)
    bank=[row(p,'other',(100,100,100)) for p in PREFIXES if p!='/loc']
    bank.extend([row('/loc','low-sse',(6,0,0)),row('/loc','within-tolerance',(8,3,3))])
    image=Image.new('RGB',(20,5));image.putpixel((0,0),(10,10,10))
    f=ChatInputFrame({},dict(client=image),sha256(image.tobytes()).hexdigest())
    p=CommandTextMatcher(bank,source_sha256='a'*64,origins=((0,0),),pixel_tolerance=3)
    result=p(f,snapshot('/loc'),phase='command_key',capture_started_at=1.)
    assert result['expected_candidate']['variant']=='low-sse'
    assert not result['expected_candidate']['declared_pixel_model_match']
    assert result['matching_expected_candidates']==1 and result['exact_prefix_unique_under_declared_model']


def test_optimized_residuals_match_independent_full_canvas_comparison():
    f=frame('/locx');p=matcher(pixel_tolerance=3)
    result=p(f,snapshot('/loc'),phase='command_key',capture_started_at=1.)
    observed=f.images['client']
    for row in result['ranked_candidates']:
        predicted=Image.new('RGB',observed.size,result['background_rgb'])
        support=Image.new('L',observed.size)
        if row['prefix']:
            t=rendering(row['prefix']);layer=Image.frombytes('RGBA',(t.width,t.height),t.rgba)
            predicted.paste(layer,row['origin'],layer.getchannel('A'))
            support.paste(layer.getchannel('A').point([0]+[255]*255),row['origin'])
        total=outside=count=outside_count=0
        for y in range(observed.height):
          for x in range(observed.width):
            o,e,s=observed.getpixel((x,y)),predicted.getpixel((x,y)),support.getpixel((x,y))
            differences=[abs(a-b) for a,b in zip(o,e)]
            error=sum(d*d for d in differences);mismatch=max(differences)>3
            total+=error;count+=mismatch
            if not s:outside+=error;outside_count+=mismatch
        assert (row['squared_error'],row['mismatching_pixels'],row['outside_glyph_squared_error'],
                row['outside_glyph_mismatching_pixels'])==(total,count,outside,outside_count)


@pytest.mark.parametrize('change',['missing-prefix','empty-alpha','mutable-bytes','duplicate','invalid-hash','too-many-origins','budget'])
def test_invalid_or_unbounded_template_bank_refuses(change):
    templates=[rendering(s) for s in PREFIXES]
    args=dict(source_sha256='a'*64,origins=((2,2),),pixel_tolerance=0)
    if change=='missing-prefix':templates.pop()
    elif change=='empty-alpha':templates[0]=replace(templates[0],rgba=bytes(len(templates[0].rgba)))
    elif change=='mutable-bytes':templates[0]=replace(templates[0],rgba=bytearray(templates[0].rgba))
    elif change=='duplicate':templates.append(templates[0])
    elif change=='invalid-hash':args['source_sha256']='not-a-source-pin'
    elif change=='too-many-origins':args['origins']=tuple((i,0) for i in range(26))
    else:
        args['origins']=tuple((i,0) for i in range(25))
        templates=[replace(t,width=2048,height=64,rgba=b'\xff'*2048*64*4) for t in templates]
    with pytest.raises(ValueError):CommandTextMatcher(templates,**args)


def test_unknown_pixels_are_shared_by_every_competitor_and_never_complete_match():
    templates=[rendering(p) for p in PREFIXES]
    mask=bytearray([255])*templates[0].width*templates[0].height
    mask[1]=0
    templates[0]=replace(templates[0],known_pixels=bytes(mask))
    prepared=CommandTextMatcher(templates,source_sha256='a'*64,origins=((2,2),),pixel_tolerance=0)
    image=frame('/loc');image.images['client'].putpixel((3,2),(255,0,255))
    result=prepared(image,snapshot('/loc'),phase='command_key',capture_started_at=1.)
    assert result['unknown_pixel_count']==1 and result['prefix_unique_on_shared_known_pixels']
    assert result['expected_candidate']['squared_error']==0
    assert not result['exact_prefix_unique_under_declared_model']
    assert not any(row['declared_pixel_model_match'] for row in result['ranked_candidates'])
    assert not result['complete_field_compared'] and not result['input_authorized']


def test_hiding_all_distinguishing_pixels_cannot_win_against_blank():
    templates=[replace(rendering(p),known_pixels=bytes(len(p)*5*7)) for p in PREFIXES]
    prepared=CommandTextMatcher(templates,source_sha256='a'*64,origins=((2,2),),pixel_tolerance=0)
    result=prepared(frame('/location'),snapshot('/location'),phase='command_key',capture_started_at=1.)
    assert not result['prefix_unique_on_shared_known_pixels']
    assert not result['exact_prefix_unique_under_declared_model']
    assert all(row['squared_error']==0 for row in result['ranked_candidates'])


@pytest.mark.parametrize('mask',[b'bad',bytearray(35),bytes([1])*35])
def test_invalid_unknown_mask_refuses(mask):
    templates=[rendering(p) for p in PREFIXES]
    templates[0]=replace(templates[0],known_pixels=mask)
    with pytest.raises(ValueError):CommandTextMatcher(templates,source_sha256='a'*64,origins=((2,2),),pixel_tolerance=0)
