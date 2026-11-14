from hashlib import sha256
import json

from PIL import Image
import pytest

from eql_automation.combat_ui_atlas import AnimationFrame, CombatUiAtlas
from eql_automation.combat_ui_match import CONTROL, analyze_saved_combat_crop, decal_sizes, rank_combat_sprites


def atlas(*, duplicate=False, transparent=False):
    frames=[]
    for name,base in [('A_PWCSStanding',(210,20,15)),('A_PWCSInCombat',(20,180,30))]:
        if duplicate:base=(210,20,15)
        image=Image.new('RGBA',(4,4))
        for y in range(4):
            for x in range(4):
                image.putpixel((x,y),(*base,0 if transparent else (128 if x==0 else 255)))
        data=image.tobytes()
        frames.append(AnimationFrame(name,0,'fake.tga',(0,0,4,4),False,1000,None,
                                      sha256(data).hexdigest(),data))
    return CombatUiAtlas('a'*64,'fixture',(('player.xml','b'*64),),tuple(frames),
        (dict(item='PW_CombatStateAnim',decal_size=(4,4)),))


def render(a, *, scale=1, index=0, filter_value=Image.Resampling.NEAREST):
    # Fabricated sprite, alpha and background; no real client pixels in git.
    image=Image.new('RGBA',(int(4*scale)+2,int(4*scale)*2),(33,45,90,255))
    icon=a.frames[index].image().resize((int(4*scale),int(4*scale)),filter_value)
    image.alpha_composite(icon,(1,2))
    return image.convert('RGB')


def test_tall_control_uses_declared_decal_and_finds_its_offset():
    a=atlas();image=render(a)
    result=rank_combat_sprites(image,a,saved_scale=1)
    first,second=result['ranked_candidates']
    assert first['animation']=='A_PWCSStanding'
    assert first['crop_box']==[1,2,5,6] and first['mean_interval_residual']==0
    assert second['mean_interval_residual']>0 and result['ranking_gap']>0
    assert result['declared_decal_size_hypotheses']==[[4,4]]
    assert result['selected_state'] is None
    assert all(result[key] is False for key in ('input_authorized','g2_safety_flags_provided',
               'active_skin_verified','scaling_compositing_verified','live_state_verified'))


@pytest.mark.parametrize('filter_value',[Image.Resampling.NEAREST,Image.Resampling.BILINEAR])
def test_partial_alpha_over_unknown_background_and_scaled_candidate(filter_value):
    a=atlas();image=render(a,scale=1.25,filter_value=filter_value)
    result=rank_combat_sprites(image,a,saved_scale=1.25)
    best=result['ranked_candidates'][0]
    assert best['animation']=='A_PWCSStanding' and best['mean_interval_residual']==0
    assert best['alpha_mass_pixels']<25 and best['opaque_pixels']>0


def test_rounding_sizes_do_not_use_tall_widget_height():
    assert decal_sizes(atlas(),1.3)==((5,5),(5,6),(6,5),(6,6))


def test_identical_or_transparent_source_pixels_never_choose_state():
    a=atlas(duplicate=True)
    result=rank_combat_sprites(render(a),a,saved_scale=1)
    assert result['ranking_gap']==0 and result['selected_state'] is None
    assert len(result['ranked_candidates'])==2
    a=atlas(transparent=True)
    result=rank_combat_sprites(render(a),a,saved_scale=1)
    assert result['ranked_candidates']==[] and result['ranking_gap'] is None


@pytest.mark.parametrize('scale',[float('nan'),float('inf'),True,None,0,5])
def test_unknown_or_invalid_scale_refuses(scale):
    with pytest.raises(ValueError):rank_combat_sprites(render(atlas()),atlas(),saved_scale=scale)


def test_no_search_outside_crop_or_unbounded_work():
    assert rank_combat_sprites(Image.new('RGB',(2,2)),atlas(),saved_scale=1)['ranked_candidates']==[]
    with pytest.raises(ValueError,match='budget'):
        rank_combat_sprites(Image.new('RGB',(128,128)),atlas(),saved_scale=4)


def capture(tmp_path):
    a=atlas();image=render(a);image.save(tmp_path/(CONTROL+'.png'))
    parent=Image.new('RGB',(20,20));parent.paste(image,(2,3));parent.save(tmp_path/'PlayerWindow.png')
    def item(name,box):return dict(file=name+'.png',box=box,sha256=sha256((tmp_path/(name+'.png')).read_bytes()).hexdigest())
    metadata=dict(format='eql-owner-ui-observation-v1',game_input_sent=False,
        saved_layout_is_live_verified=False,ui_skin_from_saved_ini='fixture',ui_scale_from_saved_ini=1,
        source_sha256_postcapture={'/private/copied/player.xml':'b'*64},window_size=[800,600],
        crops={CONTROL:item(CONTROL,[12,13,18,21]),'PlayerWindow':item('PlayerWindow',[10,10,30,30])})
    def save():
        path=tmp_path/'metadata.json';path.write_text(json.dumps(metadata))
        return dict(metadata_path=path,metadata_sha256=sha256(path.read_bytes()).hexdigest(),atlas=a)
    return metadata,save


def test_pinned_saved_crop_consistent_with_parent_produces_only_diagnostics(tmp_path):
    _,save=capture(tmp_path)
    result=analyze_saved_combat_crop(**save())
    assert result['ranked_candidates'][0]['animation']=='A_PWCSStanding'
    assert result['child_pixels_match_saved_parent'] is True
    assert result['captured_xml_matches_copied_atlas'] is True
    assert result['captured_texture_identity_verified'] is False
    assert result['standing_icon_can_also_be_null_player_fallback'] is True
    assert not result['native_melee_off_verified'] and not result['no_incoming_attack_verified']


@pytest.mark.parametrize('change',['metadata','crop','parent','xml','skin','dimensions','outside','traversal','symlink'])
def test_changed_misbound_or_inconsistent_saved_inputs_refuse(tmp_path,change):
    metadata,save=capture(tmp_path);kwargs=save()
    if change=='metadata':kwargs['metadata_path'].write_text('{}')
    elif change in ('crop','parent'):
        name=CONTROL if change=='crop' else 'PlayerWindow'
        path=tmp_path/(name+'.png')
        with path.open('ab') as output:output.write(b'changed')
    elif change=='xml':metadata['source_sha256_postcapture']['/private/copied/player.xml']='c'*64
    elif change=='skin':metadata['ui_skin_from_saved_ini']='other'
    elif change=='dimensions':metadata['crops'][CONTROL]['box'][2]+=1
    elif change=='outside':metadata['crops'][CONTROL]['box']=[1,1,7,9]
    elif change=='traversal':metadata['crops'][CONTROL]['file']='../elsewhere.png'
    elif change=='symlink':
        path=tmp_path/(CONTROL+'.png');path.rename(tmp_path/'elsewhere.png');path.symlink_to('elsewhere.png')
    if change in ('xml','skin','dimensions','outside','traversal'):kwargs=save()
    with pytest.raises(ValueError):analyze_saved_combat_crop(**kwargs)


def test_parent_pixels_disagree_even_with_valid_individual_hashes(tmp_path):
    metadata,save=capture(tmp_path)
    Image.new('RGB',(20,20)).save(tmp_path/'PlayerWindow.png')
    metadata['crops']['PlayerWindow']['sha256']=sha256((tmp_path/'PlayerWindow.png').read_bytes()).hexdigest()
    with pytest.raises(ValueError,match='same captured'):
        analyze_saved_combat_crop(**save())
