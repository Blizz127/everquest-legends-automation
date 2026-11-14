"""Real pair/crop producers with synthetic pixels; no window or game process."""
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

from PIL import Image, ImageDraw
import pytest

from eql_automation.owner_pair_diagnostic import load_saved_owner_pair,diagnose_saved_owner_pair
from eql_automation.owner_ui_observation import capture_focused_ui
from eql_automation.position_observation import save_pair
from eql_automation.unbound_location_log import UnboundLocationObservation


def fixture(tmp_path, *, capture_fn=capture_focused_ui, save_pair_fn=save_pair):
    root=tmp_path/'private';game=tmp_path/'fixture-game';game.mkdir(parents=True)
    (game/'eqclient.ini').write_text('[Defaults]\nUIScale=1\n')
    log=game/'fixture.log';log.write_text('synthetic log identity only')
    windows={'PlayerWindow':(10,10,110,80),'TargetWindow':(130,10,250,80),'MapViewWnd':(10,100,300,300)}
    controls={'Player_HP':(20,20,100,30),'Player_Mana':(20,32,100,42),
        'PW_CombatStateAnim':(90,50,103,63),'Target_HP':(140,20,240,30),
        'Target_Class':(140,40,170,55),'Target_Level':(180,40,210,55),
        'MRA_ZoneLabel':(20,110,150,125)}
    def rect(box):
        x0,y0,x1,y1=box;return SimpleNamespace(x=x0,y=y0,w=x1-x0,h=y1-y0)
    layout=SimpleNamespace(sources={},skin='fixture',ui_scale=1.25,
        window=lambda name:rect(windows[name]),control=lambda window,name:rect(controls[name]))
    image=Image.new('RGB',(320,320),(10,20,30));draw=ImageDraw.Draw(image)
    for i,box in enumerate(controls.values()):draw.rectangle(box,fill=(20+i*20,80,100))
    window=SimpleNamespace(id=42);session={'pid':123,'start_ticks':'456'}
    gate=SimpleNamespace(windows=lambda:[window],focused_window=lambda:window,
                         game_session=lambda:dict(session),capture=lambda:image.copy())
    now=[102.]
    def clock():now[0]+=.01;return now[0]
    dest=capture_fn(label='synthetic-position',gate=gate,layout_loader=lambda *a,**k:layout,
        game=game,character='Fixture',server='fixture',output=root,private_root=root,clock=clock)
    fix=UnboundLocationObservation((1.,2.,3.),datetime(2026,11,14,1,0),100.,1,1)
    meta=json.loads((dest/'metadata.json').read_text())
    save_pair_fn(fix=fix,expected={'game_session':session,'window_id':42},metadata=meta,dest=dest,
        checked_at=clock(),started=99.,log_identity=(log.stat().st_dev,log.stat().st_ino),
        character='Fixture',server='fixture')
    pair=json.loads((dest/'unbound-location.json').read_text())
    def rewrite():
        (dest/'metadata.json').write_text(json.dumps(meta))
        pair['ui_metadata_sha256']=sha256((dest/'metadata.json').read_bytes()).hexdigest()
        (dest/'unbound-location.json').write_text(json.dumps(pair))
    def load():
        return load_saved_owner_pair(dest,private_root=root,
            expected_pair_sha256=sha256((dest/'unbound-location.json').read_bytes()).hexdigest())
    catalog=tmp_path/'ZoneNames.txt'
    catalog.write_text('54^Fixture Zone^0^0\n1^Duplicate^0^0\n2^Duplicate^0^0\n')
    mesh=tmp_path/'fixturezone.npz';mesh.write_bytes(b'explicit synthetic mesh identity')
    mesh_pin=sha256(mesh.read_bytes()).hexdigest()
    plan=tmp_path/'route.json'
    plan.write_text(json.dumps(dict(format='eql-fixed-segment-plan-v1',frame='helper_package_WLD_Y_X_Z',
        offline_only=True,route_accepted=False,real_client_accepted=False,zone='fixturezone',half_width=1.2,
        pins={str(mesh):mesh_pin},segments=[
            dict(index=0,polygon=1,points=[[1,2,3],[1,12,3]]),
            dict(index=1,polygon=2,points=[[1,12,3],[1,22,3]])])))
    route_args=dict(route_path=plan,route_sha256=sha256(plan.read_bytes()).hexdigest(),
                    mesh_path=mesh,mesh_sha256=mesh_pin)
    zone_args=dict(zone_names=catalog,zone_names_sha256=sha256(catalog.read_bytes()).hexdigest())
    return SimpleNamespace(root=root,dest=dest,meta=meta,pair=pair,rewrite=rewrite,load=load,
                           catalog=catalog,route_args=route_args,zone_args=zone_args)


def test_producer_roundtrip_checks_saved_pixels_without_claiming_live_identity(tmp_path):
    f=fixture(tmp_path);before={p:p.read_bytes() for p in f.dest.iterdir()}
    saved=f.load();report=diagnose_saved_owner_pair(saved,**f.route_args,**f.zone_args,map_label_text='Fixture Zone')
    assert report['saved_byte_integrity_verified'] and report['recorded_timing_consistent']
    assert report['recorded_process']=={'pid':123,'start_ticks':'456'}
    assert not report['recorded_process_identity_independently_verified']
    assert not report['full_frame_hash_revalidated'] and not report['source_files_revalidated']
    assert report['map_zone']['catalog_zone_id']==54 and report['map_zone']['catalog_lookup']=='unique'
    assert not report['map_zone']['current_zone_verified']
    assert f.meta['map_label_expected_eqtype']==1020
    assert f.meta['map_label_requires_current_zone_selection'] is False
    assert not f.meta['map_label_runtime_refresh_verified']
    assert not f.meta['map_label_xml_to_runtime_binding_verified']
    assert report['route']['segment_count']==2 and report['route']['horizontal_length']==20
    assert report['route']['planned_start']==tuple(report['raw_location']['raw_coordinates'])
    assert report['route']['current_start_query']=='unavailable_unbound_raw_coordinates'
    assert not report['route']['route_accepted'] and not report['route']['mesh_geometry_recomputed']
    assert all(c['child_pixels_match_saved_parent'] is True for name,c in report['crops'].items() if '__' in name)
    assert set(report['scene_states'].values())=={'unknown'}
    assert all(report[k] is False for k in ('input_authorized','f11_enabled','game_input_sent',
        'live_game_capture_performed','live_position_verified','live_route_accepted'))
    assert all(p.read_bytes()==data for p,data in before.items())


@pytest.mark.parametrize('text,status,zone_id',[
    ('Fixture Zone','unique',54),('fixture zone','not_in_client_catalog',None),('Duplicate','ambiguous',None)])
def test_catalog_is_exact_lookup_not_ocr_or_zone_binding(tmp_path,text,status,zone_id):
    f=fixture(tmp_path);r=diagnose_saved_owner_pair(f.load(),**f.zone_args,map_label_text=text)
    assert r['map_zone']['catalog_lookup']==status and r['map_zone']['catalog_zone_id']==zone_id
    assert not r['map_zone']['text_recognition_performed'] and not r['map_zone']['asset_short_name_binding_verified']
    assert r['route'] is None


def test_missing_parent_preserves_unknown_relationship_and_scene(tmp_path):
    f=fixture(tmp_path);del f.meta['crops']['TargetWindow']
    f.meta['missing_or_offscreen_crops'].append('TargetWindow');f.rewrite()
    r=diagnose_saved_owner_pair(f.load())
    assert r['crops']['TargetWindow__Target_HP']['child_pixels_match_saved_parent'] is None
    assert r['scene_states']['target']=='unknown'


def test_missing_label_cannot_support_a_text_hypothesis(tmp_path):
    f=fixture(tmp_path);del f.meta['crops']['MapViewWnd__MRA_ZoneLabel']
    f.meta['missing_or_offscreen_crops'].append('MapViewWnd__MRA_ZoneLabel');f.rewrite()
    assert diagnose_saved_owner_pair(f.load())['map_zone']['label_crop'] is None
    with pytest.raises(ValueError,match='saved label crop'):
        diagnose_saved_owner_pair(f.load(),**f.zone_args,map_label_text='Fixture Zone')


@pytest.mark.parametrize('change',['pair-pin','metadata-pin','crop-pin','crop-symlink',
    'crop-filename','wrong-png-mode','wrong-png-size','wrong-parent-pixels','outside-parent',
    'window-bool','oversized-box','missing-inventory','chat-crop','promoted-zone'])
def test_corrupt_or_inconsistent_capture_refuses(tmp_path,change):
    f=fixture(tmp_path);key='PlayerWindow__Player_HP';path=f.dest/(key+'.png')
    if change=='pair-pin':
        with pytest.raises(ValueError):load_saved_owner_pair(f.dest,private_root=f.root,expected_pair_sha256='0'*64)
        return
    if change=='metadata-pin':(f.dest/'metadata.json').write_text('{}')
    elif change=='crop-pin':path.write_bytes(path.read_bytes()+b'changed')
    elif change=='crop-symlink':
        other=tmp_path/'other.png';path.rename(other);path.symlink_to(other)
    else:
        if change=='crop-filename':f.meta['crops'][key]['file']='../other.png'
        elif change in ('wrong-png-mode','wrong-png-size','wrong-parent-pixels'):
            size=(80,10) if change!='wrong-png-size' else (79,10)
            Image.new('RGBA' if change=='wrong-png-mode' else 'RGB',size,'white').save(path)
            f.meta['crops'][key]['sha256']=sha256(path.read_bytes()).hexdigest()
        elif change=='outside-parent':f.meta['crops'][key]['box']=[200,200,280,210]
        elif change=='window-bool':f.meta['window_size'][0]=True
        elif change=='oversized-box':
            f.meta['window_size']=[7680,7680];f.meta['crops'][key]['box']=[0,0,7680,7680]
        elif change=='missing-inventory':f.meta['missing_or_offscreen_crops']=['TargetWindow']
        elif change=='chat-crop':f.meta['chat_crop_included']=True
        elif change=='promoted-zone':f.meta['map_label_is_current_zone_verified']=True
        f.rewrite()
    with pytest.raises(ValueError):f.load()


@pytest.mark.parametrize('change',['promoted-location','promoted-pair','coords-nan','coords-bool',
    'coords-overflow','aware-log-time','receipt-before-start','capture-before-receipt','stale-receipt',
    'identity','epoch-bool','process-id','window-id','capture-overflow'])
def test_bad_raw_record_or_internal_timing_refuses_without_reproving_identity(tmp_path,change):
    f=fixture(tmp_path)
    if change=='promoted-location':f.pair['location']['coordinates_aligned_to_wld']=True
    elif change=='promoted-pair':f.pair['character_identity_verified']=True
    elif change.startswith('coords-'):
        f.pair['location']['raw_coordinates'][0]={'coords-nan':float('nan'),'coords-bool':True,'coords-overflow':10**400}[change]
    elif change=='aware-log-time':f.pair['location']['log_local_time']='2026-11-14T01:00:00+00:00'
    elif change=='receipt-before-start':f.pair['observation_started_monotonic']=101
    elif change=='capture-before-receipt':f.meta['capture_started_monotonic']=99
    elif change=='stale-receipt':f.pair['post_capture_checked_monotonic']=111
    elif change=='identity':f.pair['source_log_identity']=[1]
    elif change=='epoch-bool':f.pair['location']['log_epoch']=True
    elif change=='process-id':f.meta['game_session']['pid']=0
    elif change=='window-id':f.meta['focused_window_id']='42'
    elif change=='capture-overflow':f.meta['capture_ended_monotonic']=10**400
    f.rewrite()
    with pytest.raises(ValueError):f.load()


def test_changed_bundle_is_rechecked_and_route_mesh_pins_are_required(tmp_path):
    f=fixture(tmp_path);saved=f.load()
    with pytest.raises(ValueError,match='required together'):
        diagnose_saved_owner_pair(saved,route_path=f.route_args['route_path'])
    with pytest.raises(ValueError):
        diagnose_saved_owner_pair(saved,**{**f.route_args,'mesh_sha256':'0'*64})
    with (f.dest/'metadata.json').open('a') as stream:stream.write(' ')
    with pytest.raises(ValueError):diagnose_saved_owner_pair(saved)


def test_private_root_and_symlinked_bundle_are_rejected(tmp_path):
    f=fixture(tmp_path);pin=sha256((f.dest/'unbound-location.json').read_bytes()).hexdigest()
    with pytest.raises(ValueError):load_saved_owner_pair(f.dest,expected_pair_sha256=pin,private_root=tmp_path/'elsewhere')
    link=f.root/'linked';link.symlink_to(f.dest,target_is_directory=True)
    with pytest.raises(ValueError):load_saved_owner_pair(link,expected_pair_sha256=pin,private_root=f.root)


@pytest.mark.parametrize('duplicate',[False,True])
def test_route_cannot_substitute_another_pinned_input_for_its_zone_mesh(tmp_path,duplicate):
    f=fixture(tmp_path);plan_path=f.route_args['route_path'];data=json.loads(plan_path.read_text())
    if duplicate:
        data['pins']['/another/store/fixturezone.npz']=f.route_args['mesh_sha256']
        kwargs=dict(f.route_args)
    else:
        wrong=tmp_path/'other-input.txt';wrong.write_bytes(b'not the zone mesh')
        wrong_pin=sha256(wrong.read_bytes()).hexdigest();data['pins'][str(wrong)]=wrong_pin
        kwargs={**f.route_args,'mesh_path':wrong,'mesh_sha256':wrong_pin}
    plan_path.write_text(json.dumps(data));kwargs['route_sha256']=sha256(plan_path.read_bytes()).hexdigest()
    with pytest.raises(ValueError,match='mesh role'):diagnose_saved_owner_pair(f.load(),**kwargs)


def test_identical_mesh_can_be_explicitly_relocated_without_changing_source_pin(tmp_path):
    f=fixture(tmp_path);copy=tmp_path/'relocated-copy.bin'
    copy.write_bytes(f.route_args['mesh_path'].read_bytes())
    report=diagnose_saved_owner_pair(f.load(),**{**f.route_args,'mesh_path':copy})
    assert report['route']['mesh_local_path']==str(copy)
    assert report['route']['mesh_source_pin_key']==str(f.route_args['mesh_path'])
    assert report['route']['current_start_query']=='unavailable_unbound_raw_coordinates'
