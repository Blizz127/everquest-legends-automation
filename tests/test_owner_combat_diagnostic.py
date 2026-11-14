from hashlib import sha256
import json
from pathlib import Path

from PIL import Image
import pytest

from eql_automation.owner_combat_diagnostic import analyze_owner_observation
from eql_automation.combat_ui_match import CONTROL
from test_combat_ui_atlas import fixture


def observation(tmp_path):
    game=tmp_path/'game';ui=game/'uifiles/custom';ui.mkdir(parents=True)
    save,_=fixture(ui);manifest,pin=save()
    original={p.name:p.read_bytes() for p in ui.iterdir()}
    root=tmp_path/'private';dest=root/'observation';dest.mkdir(parents=True)
    Image.new('RGB',(13,26),(20,110,30)).save(dest/(CONTROL+'.png'))
    xml=ui/'player.xml';digest=sha256(xml.read_bytes()).hexdigest()
    metadata=dict(format='eql-owner-ui-observation-v1',game_input_sent=False,
        saved_layout_is_live_verified=False,ui_skin_from_saved_ini='custom',ui_scale_from_saved_ini=1,
        combat_widget_source=dict(file=str(xml),sha256=digest),source_sha256_postcapture={str(xml):digest},
        window_size=[800,600],crops={CONTROL:dict(file=CONTROL+'.png',box=[100,100,113,126],
        sha256=sha256((dest/(CONTROL+'.png')).read_bytes()).hexdigest())})
    def write_pair():
        (dest/'metadata.json').write_text(json.dumps(metadata))
        pair=dict(format='eql-unbound-location-ui-v1',game_input_sent=False,live_route_accepted=False,
                  ui_metadata_sha256=sha256((dest/'metadata.json').read_bytes()).hexdigest())
        (dest/'unbound-location.json').write_text(json.dumps(pair))
    write_pair()
    return game,root,dest,metadata,write_pair,original


def test_snapshot_uses_recorded_widget_xml_and_keeps_game_and_raw_capture_unchanged(tmp_path):
    game,root,dest,metadata,_,original=observation(tmp_path)
    raw={name:(dest/name).read_bytes() for name in ('metadata.json','unbound-location.json',CONTROL+'.png')}
    report=analyze_owner_observation(dest,game=game,private_root=root)
    result=json.loads(report.read_text())
    assert report==dest/'combat-analysis.json'
    assert result['automatic_after_owner_capture'] and result['selected_state'] is None
    assert result['captured_xml_matches_copied_atlas'] and not result['captured_texture_identity_verified']
    assert not result['game_input_sent'] and not result['input_authorized']
    assert {p.name:p.read_bytes() for p in (game/'uifiles/custom').iterdir()}==original
    assert all((dest/name).read_bytes()==data for name,data in raw.items())
    copied=json.loads((dest/'combat-diagnostic-assets/manifest.json').read_text())
    assert copied['xml']=='player.xml' and copied['snapshot_after_capture']
    assert not copied['texture_identity_at_capture_verified']


@pytest.mark.parametrize('change',['old_metadata','changed_xml','missing_texture','different_source','changed_metadata','existing_snapshot'])
def test_failed_analysis_preserves_saved_pair_without_install_mutation(tmp_path,change):
    game,root,dest,metadata,write_pair,_=observation(tmp_path)
    if change=='old_metadata':metadata.pop('combat_widget_source');write_pair()
    elif change=='changed_xml':
        with (game/'uifiles/custom/player.xml').open('a') as output:output.write(' ')
    elif change=='missing_texture':
        fallback=game/'uifiles/default';fallback.mkdir()
        (game/'uifiles/custom/fixture.tga').rename(fallback/'fixture.tga')
    elif change=='different_source':
        elsewhere=tmp_path/'outside.xml';elsewhere.write_bytes((game/'uifiles/custom/player.xml').read_bytes())
        metadata['combat_widget_source']['file']=str(elsewhere)
        metadata['source_sha256_postcapture']={str(elsewhere):metadata['combat_widget_source']['sha256']};write_pair()
    elif change=='changed_metadata':
        with (dest/'metadata.json').open('a') as output:output.write(' ')
    elif change=='existing_snapshot':(dest/'combat-diagnostic-assets').mkdir()
    raw={name:(dest/name).read_bytes() for name in ('metadata.json','unbound-location.json')}
    with pytest.raises((ValueError,FileExistsError)):
        analyze_owner_observation(dest,game=game,private_root=root)
    assert all((dest/name).read_bytes()==data for name,data in raw.items())
    assert not (dest/'combat-analysis.json').exists()


def test_late_cancellation_relabels_only_the_new_analysis(tmp_path):
    game,root,dest,*_=observation(tmp_path)
    pair=(dest/'unbound-location.json').read_bytes()
    def current():
        if (dest/'combat-analysis.json').exists():raise ValueError('cancelled')
    with pytest.raises(ValueError,match='cancelled'):
        analyze_owner_observation(dest,game=game,private_root=root,still_current=current)
    assert not (dest/'combat-analysis.json').exists()
    assert (dest/'cancelled-combat-analysis.json').is_file()
    assert (dest/'unbound-location.json').read_bytes()==pair


def test_output_inside_game_refuses_before_reading(tmp_path):
    game,root,dest,*_=observation(tmp_path)
    with pytest.raises(ValueError,match='outside the game'):
        analyze_owner_observation(dest,game=tmp_path,private_root=root)


def test_output_elsewhere_in_protected_prefix_also_refuses(tmp_path,monkeypatch):
    monkeypatch.setattr(Path,'home',classmethod(lambda cls:tmp_path))
    root=tmp_path/'Games/everquest-legends/diagnostics'
    dest=root/'observation';dest.mkdir(parents=True)
    with pytest.raises(ValueError,match='outside the game'):
        analyze_owner_observation(dest,game=tmp_path/'Games/everquest-legends/drive_c/game',private_root=root)
