"""Fresh printed/source height correspondence on an in-memory camp floor.

This consumes no reader cursor and sends no input. The owner controller must
own collection/request correlation and obtain both replies after acquiring its
new scope. Neither historical height evidence nor these records authorize input.
"""
from dataclasses import asdict,dataclass,field
from datetime import datetime
from hashlib import sha256
import math
import time

from .camp_floor_checkpoint import CampFloorCheckpoint
from .camp_probe_floor import CAMP_FLOOR_TYPES,CampProbeFloorReference,camp_floor_anchor
from .ground_binding import finite,point
from .location_log import LocationLogReader,RawLocationFix
from .motion_collection import immutable_binding
from .native_region_policy import encoded
from .route_floor_commit import _chain_snapshot


@dataclass(frozen=True)
class CampStoppedHeight:
    checkpoint: CampFloorCheckpoint | CampProbeFloorReference
    first: RawLocationFix
    second: RawLocationFix
    package_xyz: tuple
    raw_z_minus_source_z: float
    observed_at: float
    expires_at: float
    payload: bytes
    sha256: str
    input_authorized: bool=field(default=False,init=False)
    real_client_accepted: bool=field(default=False,init=False)


def measure_camp_stopped_height(checkpoint,reader,first,second,*,minimum_log_seq,
                                released_at,owner_binding,binding_reader,
                                clock=time.monotonic,local_wall_clock=datetime.now,
                                residual_limit=.05,maximum_offset_change=.05):
    """Validate new samples without constructing a route or rearming an observer."""
    if (type(checkpoint) not in CAMP_FLOOR_TYPES or type(reader) is not LocationLogReader
            or any(type(v) is not RawLocationFix for v in (first,second))
            or type(minimum_log_seq) is not int or minimum_log_seq<1
            or not all(finite(v) for v in (released_at,residual_limit,maximum_offset_change))
            or released_at<0 or not 0<residual_limit<=.25 or not 0<maximum_offset_change<=.25
            or type(owner_binding) is not tuple or not immutable_binding(owner_binding)
            or not all(callable(v) for v in (binding_reader,clock,local_wall_clock))):
        raise ValueError('Fresh camp pair, acquisition baseline and bounded correspondence required')
    checkpoint.check()
    if reader is not checkpoint._reader:
        raise ValueError('Camp height reader differs from the retained arrival')
    anchor,anchor_raw,anchor_position=camp_floor_anchor(checkpoint)
    if minimum_log_seq<anchor_raw.log_line_seq:
        raise ValueError('Acquisition baseline predates the arrival')
    branch=checkpoint.fork();state=_chain_snapshot(branch);last=None
    expected=(reader.zone_id,reader.zone_display_name,reader.tail.epoch,reader.zone_generation)
    def check():
        nonlocal last
        binding=binding_reader();wall=local_wall_clock()
        checkpoint.check();now=clock();checkpoint._assert_intact()
        if (binding!=owner_binding or reader is not checkpoint._reader
                or camp_floor_anchor(checkpoint)[0] is not anchor or _chain_snapshot(branch)!=state
                or not finite(now) or last is not None and now<last
                or reader.latest is not second or reader.log_line_seq!=second.log_line_seq
                or (reader.zone_id,reader.zone_display_name,reader.tail.epoch,reader.zone_generation)!=expected
                or not isinstance(wall,datetime) or wall.tzinfo is not None
                or any(not finite(v.received_monotonic) or not isinstance(v.log_local_time,datetime)
                    or v.log_local_time.tzinfo is not None for v in (first,second))
                or not 0<=now-second.received_monotonic<=.5
                or any(abs((wall-v.log_local_time).total_seconds()-(now-v.received_monotonic))>2.
                       for v in (first,second))):
            raise ValueError('Camp height scope changed or fresh observations expired')
        last=now
        return now,wall
    check()
    if (any(not point(v.raw_coordinates) or v.coordinates_aligned_to_wld is not False
            or (v.zone_id,v.zone_display_name,v.log_epoch,v.zone_generation)!=expected
            or type(v.log_line_seq) is not int for v in (first,second))
            or first.log_line_seq<=minimum_log_seq or second.log_line_seq!=first.log_line_seq+1
            or not released_at+.12<=first.received_monotonic
            or not .4<=second.received_monotonic-first.received_monotonic<=2.5
            or first.log_local_time>second.log_local_time
            or math.dist(first.raw_coordinates[:2],second.raw_coordinates[:2])>.25
            or abs(first.raw_coordinates[2]-second.raw_coordinates[2])>.25):
        raise ValueError('Two new consecutive stopped positions after release are required')
    samples=[]
    for raw in (first,second):
        xy=(raw.raw_coordinates[1],raw.raw_coordinates[0])
        z,identities=branch.floor_at(xy)
        samples.append(dict(package_xyz=(*xy,z),source_ids=identities,
                            offset=raw.raw_coordinates[2]-z))
        check()
    offsets=tuple(s['offset'] for s in samples);center=sum(offsets)/2
    anchor_offset=anchor_raw.raw_coordinates[2]-anchor_position[2]
    if (not finite(center) or center<=0 or not finite(anchor_offset) or anchor_offset<=0
            or any(abs(v-center)>residual_limit or abs(v-anchor_offset)>maximum_offset_change for v in offsets)):
        raise ValueError('Fresh heights disagree with the reached floor correspondence')
    observed,wall=check()
    def raw_record(raw):
        value=asdict(raw);value['log_local_time']=raw.log_local_time.isoformat();return value
    payload=encoded(dict(format='eql-camp-stopped-height-v1',checkpoint_sha256=checkpoint.sha256,
        source_floor_proof_sha256=branch.previous.proof_sha256,
        observations=(raw_record(first),raw_record(second)),samples=samples,
        minimum_log_seq=minimum_log_seq,released_at=released_at,owner_binding=owner_binding,
        anchor_offset=anchor_offset,raw_z_minus_source_z=center,residual_limit=residual_limit,
        maximum_offset_change=maximum_offset_change,observed_at=observed,
        expires_at=second.received_monotonic+.5,local_wall_time=wall.isoformat(),
        old_calibration_renewed=False,body_height_verified=False,heading_verified=False,
        input_authorized=False,real_client_accepted=False))
    return CampStoppedHeight(checkpoint,first,second,tuple(samples[1]['package_xyz']),center,
        observed,second.received_monotonic+.5,payload,sha256(payload).hexdigest())
