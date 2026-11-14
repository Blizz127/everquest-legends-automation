from hashlib import sha256
import json

from PIL import Image
import pytest

from eql_automation.combat_ui_atlas import load_combat_ui_atlas


def fixture(tmp_path,*,xml=None):
    # Fabricated pixels only; real client textures remain outside git.
    image=Image.new('RGBA',(4,2))
    image.putdata([(255,0,0,255)]*4+[(0,200,0,128)]*4)
    image.save(tmp_path/'fixture.tga')
    frame='''<Frames><Texture>fixture.tga</Texture><Location><X>0</X><Y>1</Y></Location>
      <Size><CX>2</CX><CY>1</CY></Size><Duration>1000</Duration></Frames>'''
    if xml is None:
        xml=f'''<XML><Ui2DAnimation item="A_PWCSStanding"><Cycle>true</Cycle>{frame}</Ui2DAnimation>
        <StaticAnimation item="A_AttackIndicatorAnimTop"><Animation>A_PWCSStanding</Animation>
        <AutoDraw>false</AutoDraw></StaticAnimation>
        <Button item="PW_CombatStateAnim"><DecalSize><CX>13</CX><CY>13</CY></DecalSize></Button></XML>'''
    (tmp_path/'player.xml').write_text(xml)
    def save():
        files={name:dict(sha256=sha256((tmp_path/name).read_bytes()).hexdigest(),bytes=(tmp_path/name).stat().st_size)
               for name in ('player.xml','fixture.tga')}
        manifest=dict(format='eql-client-ui-assets-v1',xml='player.xml',textures=['fixture.tga'],
            saved_skin='synthetic',active_skin_verified=False,files=files)
        path=tmp_path/'manifest.json';path.write_text(json.dumps(manifest))
        return path,sha256(path.read_bytes()).hexdigest()
    return save,frame


def test_exact_source_pixels_alpha_and_unknown_runtime_fields(tmp_path):
    save,_=fixture(tmp_path);path,pin=save()
    atlas=load_combat_ui_atlas(path,expected_sha256=pin)
    frame,=atlas.frames
    assert frame.box==(0,1,2,2) and frame.cycle is True and frame.duration_ms==1000
    assert frame.rgba==bytes([0,200,0,128])*2
    assert frame.rgba_sha256==sha256(frame.rgba).hexdigest()
    assert [frame.image().getpixel((x,0)) for x in range(2)]==[(0,200,0,128)]*2
    record=atlas.record()
    assert all(record[k] is False for k in ('live_state_verified','active_skin_verified',
        'input_authorized','g2_safety_flags_provided','runtime_state_to_animation_verified','scaling_compositing_verified'))
    assert 'rgba' not in record['frames'][0]
    attack,combat=record['widget_definitions']
    assert attack['auto_draw'] is False and attack['animation']=='A_PWCSStanding'
    assert combat['animation'] is None and combat['auto_draw'] is None
    assert combat['button_draw_template_present'] is False and combat['decal_size']==(13,13)


@pytest.mark.parametrize('kind',['texture','xml','manifest','symlink'])
def test_changed_or_indirect_input_cannot_produce_templates(tmp_path,kind):
    save,_=fixture(tmp_path);path,pin=save()
    if kind=='manifest':path.write_text(path.read_text()+' ')
    elif kind=='symlink':
        original=tmp_path/'fixture.tga';original.rename(tmp_path/'elsewhere.tga');original.symlink_to('elsewhere.tga')
    else:
        target=tmp_path/('fixture.tga' if kind=='texture' else 'player.xml')
        with target.open('ab') as output:output.write(b'changed')
    with pytest.raises(ValueError):load_combat_ui_atlas(path,expected_sha256=pin)


@pytest.mark.parametrize('kind',['bounds','missing_texture','duplicate','boolean','no_combat','entity','unsafe_name'])
def test_unsupported_xml_is_not_guessed(tmp_path,kind):
    save,frame=fixture(tmp_path)
    animation=f'<Ui2DAnimation item="A_PWCSStanding"><Cycle>true</Cycle>{frame}</Ui2DAnimation>'
    xml='<XML>'+animation+'</XML>'
    if kind=='bounds':xml=xml.replace('<CX>2</CX>','<CX>5</CX>')
    elif kind=='missing_texture':xml=xml.replace('fixture.tga','absent.tga')
    elif kind=='duplicate':xml='<XML>'+animation+animation+'</XML>'
    elif kind=='boolean':xml=xml.replace('<Cycle>true</Cycle>','<Cycle>True</Cycle>')
    elif kind=='no_combat':xml=xml.replace('A_PWCSStanding','Unrelated')
    elif kind=='entity':xml='<!DOCTYPE XML [<!ENTITY item "text">]>'+xml
    elif kind=='unsafe_name':xml=xml.replace('fixture.tga','../fixture.tga')
    (tmp_path/'player.xml').write_text(xml)
    path,pin=save()
    with pytest.raises(ValueError):load_combat_ui_atlas(path,expected_sha256=pin)


def test_multiple_source_frames_keep_order_and_do_not_invent_optional_values(tmp_path):
    save,frame=fixture(tmp_path)
    xml='<XML><Ui2DAnimation item="A_PWCSTimer">'+frame.replace('<Duration>1000</Duration>','')+frame+'</Ui2DAnimation></XML>'
    (tmp_path/'player.xml').write_text(xml);path,pin=save()
    atlas=load_combat_ui_atlas(path,expected_sha256=pin)
    assert [f.index for f in atlas.frames]==[0,1]
    assert atlas.frames[0].duration_ms is None and atlas.frames[0].cycle is None
    assert atlas.frames[1].duration_ms==1000
