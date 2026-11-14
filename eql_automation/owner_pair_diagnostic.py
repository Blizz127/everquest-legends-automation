"""Read a saved owner position/UI pair without opening a display or input.

Hash links and overlapping saved pixels are independently checkable. Recorded
focus, process identity, stillness and current zone are not re-established by
reading a bundle. Raw coordinates never become a WLD navigation position here.
"""
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import re

from PIL import Image

from .combat_ui_atlas import _pinned
from .fixed_route_follower import FixedRoute
from .location_log import unique_zone_ids_from_text
from .owner_ui_observation import DEFAULT_OUTPUT, WINDOWS, CONTROLS
from .position_observation import validate_capture_record
from .unbound_location_log import UnboundLocationObservation


PARENTS = {window+'__'+control:window for window,control in CONTROLS}
ALLOWED_CROPS = frozenset(WINDOWS).difference({'MainChat'}).union(PARENTS)
PAIR_FALSE = ('game_input_sent','live_route_accepted','character_identity_verified',
              'owner_held_still_verified','log_flush_delay_verified','continuous_focus_verified')
LOCATION_FALSE = ('zone_binding_verified','coordinates_aligned_to_wld',
                  'request_correlation_verified','input_authorized')


def _finite(value):
    try:return type(value) in (int,float) and math.isfinite(value)
    except OverflowError:return False


def _digest(value):
    return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None


def _object(raw):
    result=json.loads(raw)
    if not isinstance(result,dict):raise ValueError('Expected a JSON object')
    return result


@dataclass(frozen=True)
class SavedCrop:
    name: str
    box: tuple[int,int,int,int]
    png_sha256: str
    rgb: bytes
    parent_pixels_match: bool | None

    def record(self):
        return dict(box=self.box,png_sha256=self.png_sha256,
                    rgb_sha256=sha256(self.rgb).hexdigest(),
                    parent=PARENTS.get(self.name),
                    child_pixels_match_saved_parent=self.parent_pixels_match)


@dataclass(frozen=True)
class SavedOwnerPair:
    directory: Path
    pair_bytes: bytes
    metadata_bytes: bytes
    location: UnboundLocationObservation
    crops: tuple[SavedCrop,...]
    pins: tuple[tuple[Path,str,int],...]

    @property
    def pair_sha256(self):return sha256(self.pair_bytes).hexdigest()

    @property
    def metadata_sha256(self):return sha256(self.metadata_bytes).hexdigest()

    def recheck(self):
        for path,pin,limit in self.pins:_pinned(path,pin,limit)


def load_saved_owner_pair(directory, *, expected_pair_sha256, private_root=DEFAULT_OUTPUT):
    directory,root=Path(directory).expanduser(),Path(private_root).expanduser().resolve()
    protected=(Path.home()/'Games/everquest-legends').resolve()
    if (directory.is_symlink() or not directory.is_dir() or directory.resolve()==root
            or not directory.resolve().is_relative_to(root) or root.is_relative_to(protected)):
        raise ValueError('Expected a private observation directory outside the game prefix')
    directory=directory.resolve();pins=[]
    def read(name,pin,limit):
        path=directory/name;data=_pinned(path,pin,limit);pins.append((path,pin,limit));return data
    pair_bytes=read('unbound-location.json',expected_pair_sha256,256*1024)
    pair=_object(pair_bytes)
    if pair.get('format')!='eql-unbound-location-ui-v1' or any(pair.get(k) is not False for k in PAIR_FALSE):
        raise ValueError('Unsupported or promoted unbound owner pair')
    for key in ('expected_character','expected_server'):
        if not isinstance(pair.get(key),str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}',pair[key]):
            raise ValueError('Missing expected character/server labels')
    identity=pair.get('source_log_identity')
    if (not isinstance(identity,list) or len(identity)!=2
            or any(type(n) is not int or n<0 for n in identity)):
        raise ValueError('Missing recorded source log identity')
    raw=pair.get('location')
    if not isinstance(raw,dict) or any(raw.get(k) is not False for k in LOCATION_FALSE):
        raise ValueError('Unbound location flags changed')
    coords=raw.get('raw_coordinates')
    if not isinstance(coords,list) or len(coords)!=3 or not all(_finite(n) for n in coords):
        raise ValueError('Invalid raw location coordinates')
    if any(type(raw.get(k)) is not int or raw[k]<1 for k in ('log_epoch','log_line_seq')):
        raise ValueError('Invalid recorded log epoch/sequence')
    if not isinstance(raw.get('log_local_time'),str) or len(raw['log_local_time'])>64:
        raise ValueError('Invalid local log timestamp')
    stamp=datetime.fromisoformat(raw['log_local_time'])
    if stamp.tzinfo is not None:raise ValueError('Client log timestamp must remain local and timezone-free')
    fix=UnboundLocationObservation(tuple(coords),stamp,raw.get('received_monotonic'),raw['log_epoch'],raw['log_line_seq'])
    started=pair.get('observation_started_monotonic')
    if not _finite(started) or not _finite(fix.received_monotonic) or not 0<=started<=fix.received_monotonic:
        raise ValueError('Invalid recorded observation start/receipt order')
    metadata_bytes=read('metadata.json',pair.get('ui_metadata_sha256'),1024*1024)
    metadata=_object(metadata_bytes)
    if (metadata.get('format')!='eql-owner-ui-observation-v1'
            or metadata.get('saved_layout_is_live_verified') is not False
            or metadata.get('map_label_is_current_zone_verified') is not False
            or not isinstance(metadata.get('crops'),dict)):
        raise ValueError('Unsupported capture metadata or promoted live layout/zone')
    if not all(_finite(n) for n in (metadata.get('capture_started_monotonic'),
            metadata.get('capture_ended_monotonic'),pair.get('post_capture_checked_monotonic'))):
        raise ValueError('Invalid recorded capture timestamps')
    validate_capture_record(fix,metadata,pair.get('post_capture_checked_monotonic'))
    session=metadata.get('game_session')
    if (not isinstance(session,dict) or type(session.get('pid')) is not int or session['pid']<=0
            or not isinstance(session.get('start_ticks'),str) or not re.fullmatch('[0-9]{1,32}',session['start_ticks'])
            or type(metadata.get('focused_window_id')) is not int or metadata['focused_window_id']<=0):
        raise ValueError('Invalid recorded process/window identifiers')
    window=metadata.get('window_size');inventory=metadata.get('crops');missing=metadata.get('missing_or_offscreen_crops')
    if (not isinstance(window,list) or len(window)!=2
            or any(type(n) is not int or not 1<=n<=7680 for n in window)
            or not isinstance(inventory,dict) or not inventory or not set(inventory)<=ALLOWED_CROPS
            or not isinstance(missing,list) or any(not isinstance(k,str) for k in missing)
            or len(set(missing))!=len(missing) or set(missing)!=ALLOWED_CROPS-set(inventory)):
        raise ValueError('Incomplete or invalid crop inventory/window bounds')
    if not _digest(metadata.get('frame_rgb_sha256')):
        raise ValueError('Missing recorded full-frame digest')
    sources=metadata.get('source_sha256_postcapture')
    if (not isinstance(sources,dict) or len(sources)>1024
            or any(not isinstance(k,str) or len(k)>4096 or not _digest(v) for k,v in sources.items())):
        raise ValueError('Invalid recorded UI source manifest')
    images={};records={};total_pixels=0
    for name,row in inventory.items():
        if not isinstance(row,dict) or row.get('file')!=name+'.png':
            raise ValueError('Unexpected crop filename')
        box=row.get('box')
        if not isinstance(box,list) or len(box)!=4 or any(type(n) is not int for n in box):
            raise ValueError('Invalid crop box')
        x0,y0,x1,y1=box
        pixels=(x1-x0)*(y1-y0);total_pixels+=pixels
        if not (0<=x0<x1<=window[0] and 0<=y0<y1<=window[1]) or pixels>8_000_000 or total_pixels>12_000_000:
            raise ValueError('Crop exceeds captured bounds or decoded-pixel budget')
        data=read(row['file'],row.get('sha256'),32*1024*1024)
        with Image.open(BytesIO(data)) as image:
            if image.format!='PNG' or image.mode!='RGB' or image.size!=(x1-x0,y1-y0):
                raise ValueError('Crop PNG differs from recorded dimensions or RGB mode')
            images[name]=image.copy()
        records[name]=(tuple(box),row['sha256'])
    crops=[]
    for name,image in images.items():
        box,pin=records[name];parent=PARENTS.get(name);matches=None
        if parent in images:
            px0,py0,px1,py1=records[parent][0];x0,y0,x1,y1=box
            if not (px0<=x0<x1<=px1 and py0<=y0<y1<=py1):
                raise ValueError('Control crop lies outside its saved parent')
            if images[parent].crop((x0-px0,y0-py0,x1-px0,y1-py0)).tobytes()!=image.tobytes():
                raise ValueError('Control pixels differ from the saved parent window')
            matches=True
        crops.append(SavedCrop(name,box,pin,image.tobytes(),matches))
    result=SavedOwnerPair(directory,pair_bytes,metadata_bytes,fix,tuple(crops),tuple(pins))
    result.recheck()
    return result


def diagnose_saved_owner_pair(saved, *, zone_names=None, zone_names_sha256=None,
                              map_label_text=None, route_path=None, route_sha256=None,
                              mesh_path=None, mesh_sha256=None):
    """Report checked saved bytes and an optional pinned offline route only.

    map_label_text is an explicit caller hypothesis tied to the saved label
    crop. Catalog membership proves neither Current Zone selection nor a
    short-name/WLD binding. No position-to-route query uses these raw numbers.
    """
    if not isinstance(saved,SavedOwnerPair):raise ValueError('Validated saved owner pair required')
    saved.recheck();pair=_object(saved.pair_bytes);metadata=_object(saved.metadata_bytes)
    crop_records={c.name:c.record() for c in saved.crops};extra=[]
    label=crop_records.get('MapViewWnd__MRA_ZoneLabel')
    zone=dict(label_crop=label,text_hypothesis=map_label_text,text_recognition_performed=False,
              catalog_zone_id=None,catalog_lookup='not_requested',current_zone_verified=False,
              asset_short_name_binding_verified=False)
    if (zone_names is None)!=(zone_names_sha256 is None):raise ValueError('Zone catalog path and hash are required together')
    if map_label_text is not None and (not isinstance(map_label_text,str) or not 1<=len(map_label_text)<=256 or label is None or zone_names is None):
        raise ValueError('A label hypothesis requires a saved label crop and pinned zone catalog')
    if zone_names is not None:
        path=Path(zone_names);raw=_pinned(path,zone_names_sha256,1024*1024);extra.append((path,zone_names_sha256,1024*1024))
        ids,ambiguous=unique_zone_ids_from_text(raw.decode('latin-1'))
        zone.update(catalog_sha256=zone_names_sha256,unique_display_names=len(ids),ambiguous_display_names=len(ambiguous))
        if map_label_text is not None:
            zone['catalog_lookup']='ambiguous' if map_label_text in ambiguous else 'unique' if map_label_text in ids else 'not_in_client_catalog'
            zone['catalog_zone_id']=ids.get(map_label_text)
    route_args=(route_path,route_sha256,mesh_path,mesh_sha256)
    if any(v is not None for v in route_args) and not all(v is not None for v in route_args):
        raise ValueError('Route and mesh paths/hashes are required together')
    route=None
    if route_path is not None:
        path,mesh=Path(route_path),Path(mesh_path)
        raw_plan=_pinned(path,route_sha256,10*1024*1024);_pinned(mesh,mesh_sha256,128*1024*1024)
        input_pins=_object(raw_plan).get('pins')
        if (not isinstance(input_pins,dict) or len(input_pins)>1024
                or any(not isinstance(k,str) or len(k)>4096 or not _digest(v) for k,v in input_pins.items())):
            raise ValueError('Invalid route input pins')
        extra.extend(((path,route_sha256,10*1024*1024),(mesh,mesh_sha256,128*1024*1024)))
        plan=FixedRoute.load(path,expected_sha256=route_sha256,mesh_sha256=mesh_sha256)
        if (not 1<=len(plan.segments)<=10000 or not _finite(plan.half_width) or plan.half_width<=0
                or not isinstance(plan.zone,str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}',plan.zone)):
            raise ValueError('Invalid fixed route bounds or zone label')
        mesh_keys=[key for key in input_pins if Path(key).name==plan.zone+'.npz']
        if len(mesh_keys)!=1 or input_pins[mesh_keys[0]]!=mesh_sha256:
            raise ValueError('Supplied file does not match the route zone mesh role')
        route=dict(artifact_sha256=plan.artifact_sha256,mesh_sha256=plan.mesh_sha256,
            mesh_source_pin_key=mesh_keys[0],mesh_local_path=str(mesh),
            zone_asset=plan.zone,segment_count=len(plan.segments),half_width=plan.half_width,
            frame='helper_package_WLD_Y_X_Z',planned_start=plan.segments[0].start,
            planned_end=plan.segments[-1].end,horizontal_length=sum(s.length for s in plan.segments),
            mesh_file_hash_checked=True,mesh_geometry_recomputed=False,offline_only=True,
            current_start_query='unavailable_unbound_raw_coordinates',route_accepted=False)
    result=dict(format='eql-saved-owner-position-diagnostic-v1',pair_sha256=saved.pair_sha256,
        metadata_sha256=saved.metadata_sha256,expected_character_label=pair['expected_character'],
        expected_server_label=pair['expected_server'],raw_location=pair['location'],
        recorded_process=metadata['game_session'],recorded_window_id=metadata['focused_window_id'],
        recorded_source_log_identity=pair['source_log_identity'],recorded_timing_consistent=True,
        recorded_capture_times={k:metadata.get(k) for k in ('capture_started_utc','capture_ended_utc')},
        recorded_process_identity_independently_verified=False,current_identity_verified=False,
        recorded_full_frame_sha256=metadata['frame_rgb_sha256'],full_frame_hash_revalidated=False,
        source_manifest=metadata['source_sha256_postcapture'],source_files_revalidated=False,
        saved_byte_integrity_verified=True,crops=crop_records,
        missing_or_offscreen_crops=metadata['missing_or_offscreen_crops'],map_zone=zone,route=route,
        scene_states={k:'unknown' for k in ('chat','target','combat','native_melee','incoming_attack')},
        missing_route_bindings=['current_zone','zone_to_asset','raw_coordinates_to_wld',
                                'standing_ground_height','motion_and_travel_envelope'],
        live_position_verified=False,live_route_accepted=False,f11_enabled=False,
        live_game_capture_performed=False,saved_pixels_analyzed=True,
        game_input_sent=False,input_authorized=False)
    saved.recheck()
    for path,pin,limit in extra:_pinned(path,pin,limit)
    return result
