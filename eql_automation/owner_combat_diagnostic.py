"""Analyze an owner-requested saved observation using copied current UI assets.

Only the layout loader's recorded combat-widget source is used. Texture files
must be beside that XML; unresolved fallback is refused rather than guessed.
Source files are read only. All writes are private sidecars to the saved pair.
No display, input, game launch or live safety permission is provided here.
"""
from hashlib import sha256
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from .combat_ui_atlas import PREFIXES, _name, _pinned, load_combat_ui_atlas
from .combat_ui_match import analyze_saved_combat_crop
from .owner_ui_observation import DEFAULT_OUTPUT


def analyze_owner_observation(dest, *, game, private_root=DEFAULT_OUTPUT, still_current=lambda:None):
    dest,game,private_root=Path(dest),Path(game).resolve(),Path(private_root).resolve()
    protected=(Path.home()/'Games/everquest-legends').resolve()
    if (dest.is_symlink() or not dest.resolve().is_relative_to(private_root)
            or dest.resolve()==private_root or private_root.is_relative_to(game)
            or private_root.is_relative_to(protected)
            or not dest.is_dir()):
        raise ValueError('Observation analysis must remain outside the game in its private store')
    still_current()
    pair_path=dest/'unbound-location.json'
    if pair_path.is_symlink() or not pair_path.is_file() or pair_path.stat().st_size>256*1024:
        raise ValueError('Missing bounded owner location/UI pair')
    pair_bytes=pair_path.read_bytes()
    pair=json.loads(pair_bytes)
    if (pair.get('format')!='eql-unbound-location-ui-v1'
            or pair.get('game_input_sent') is not False or pair.get('live_route_accepted') is not False):
        raise ValueError('Unsupported owner observation pair')
    metadata_path=dest/'metadata.json'
    metadata_bytes=_pinned(metadata_path,pair.get('ui_metadata_sha256'),1024*1024)
    metadata=json.loads(metadata_bytes)
    source=metadata.get('combat_widget_source')
    if (not isinstance(source,dict) or set(source)!={'file','sha256'}
            or not isinstance(source['file'],str)
            or metadata.get('source_sha256_postcapture',{}).get(source['file'])!=source['sha256']):
        raise ValueError('Capture lacks the layout-selected combat XML provenance')
    xml_path=Path(source['file'])
    if not xml_path.resolve().is_relative_to(game/'uifiles'):
        raise ValueError('Combat XML is outside the selected game UI directory')
    xml=_pinned(xml_path,source['sha256'],5*1024*1024)
    if b'<!DOCTYPE' in xml or b'<!ENTITY' in xml:raise ValueError('External XML definitions unsupported')
    root=ET.fromstring(xml)
    if len([node for node in root if node.get('item')=='PW_CombatStateAnim'])!=1:
        raise ValueError('Selected XML does not uniquely define the combat widget')
    textures=sorted({_name(frame.findtext('Texture'))
        for animation in root.findall('Ui2DAnimation') if animation.get('item','').startswith(PREFIXES)
        for frame in animation.findall('Frames')})
    if not 1<=len(textures)<=16:raise ValueError('Missing or unbounded combat textures')
    xml_name=_name(xml_path.name)
    if xml_name in textures:raise ValueError('Texture and XML filenames conflict')
    sources={xml_name:(xml_path,xml)}
    for name in textures:
        still_current()
        path=xml_path.parent/name
        if (path.is_symlink() or not path.is_file() or path.stat().st_size>5*1024*1024
                or not path.resolve().is_relative_to(game/'uifiles')):
            raise ValueError('Texture beside selected XML is unavailable; fallback is unverified: '+name)
        data=path.read_bytes()
        if len(data)>5*1024*1024:raise ValueError('Texture grew beyond the snapshot bound')
        sources[name]=(path,data)
    files={name:dict(sha256=sha256(data).hexdigest(),bytes=len(data))
           for name,(_,data) in sources.items()}
    # Pin source bytes again before publishing the copied snapshot. This does
    # not prove that these textures were the ones rendered in the earlier frame.
    for name,(path,_) in sources.items():
        still_current();_pinned(path,files[name]['sha256'],5*1024*1024)
    if pair_path.read_bytes()!=pair_bytes:
        raise ValueError('Owner pair changed during source snapshot')
    _pinned(metadata_path,pair['ui_metadata_sha256'],1024*1024)
    snapshot=dest/'combat-diagnostic-assets'
    still_current();snapshot.mkdir(mode=0o700,exist_ok=False)
    for name,(_,data) in sources.items():
        still_current()
        path=snapshot/name
        with path.open('xb') as output:output.write(data)
        path.chmod(0o600)
    manifest=dict(format='eql-client-ui-assets-v1',xml=xml_name,textures=textures,files=files,
        saved_skin=metadata.get('ui_skin_from_saved_ini'),active_skin_verified=False,
        source_paths={name:str(path) for name,(path,_) in sources.items()},
        snapshot_after_capture=True,texture_identity_at_capture_verified=False)
    manifest_bytes=(json.dumps(manifest,indent=2)+'\n').encode()
    manifest_path=snapshot/'manifest.json'
    still_current()
    with manifest_path.open('xb') as output:output.write(manifest_bytes)
    manifest_path.chmod(0o600)
    atlas=load_combat_ui_atlas(manifest_path,expected_sha256=sha256(manifest_bytes).hexdigest())
    result=analyze_saved_combat_crop(metadata_path,metadata_sha256=pair['ui_metadata_sha256'],atlas=atlas)
    result.update(owner_pair_sha256=sha256(pair_bytes).hexdigest(),automatic_after_owner_capture=True,
                  game_input_sent=False)
    still_current()
    if pair_path.read_bytes()!=pair_bytes:raise ValueError('Owner pair changed during analysis')
    path=dest/'combat-analysis.json'
    with path.open('x') as output:json.dump(result,output,indent=2);output.write('\n')
    path.chmod(0o600)
    try:still_current()
    except Exception:
        path.rename(dest/'cancelled-combat-analysis.json')
        raise
    return path
