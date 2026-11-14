"""New stopped samples compared with a historical contact correspondence.

This is a stationary-camp diagnostic. It neither snaps to terrain nor refits
the original offset, and cannot become a source movement calibration. Expired
correspondence is explicitly historical even when new samples are compatible.
"""
from dataclasses import asdict,dataclass,field
from datetime import datetime
from fractions import Fraction as F
from hashlib import sha256
import math
import time

from .camp_contact_checkpoint import CampContactCheckpoint
from .flat_record import flat_record_state
from .ground_binding import finite,point
from .location_log import LocationLogReader,RawLocationFix
from .motion_collection import immutable_binding
from .native_region_policy import encoded
from .source_contact_controller import SourceContactFix,contact_fix_record,common_contact_heights
from .source_stair_coverage import covers_closed


@dataclass(frozen=True)
class CampContactObservation:
    checkpoint: CampContactCheckpoint
    first: SourceContactFix
    second: SourceContactFix
    observed_at: float
    expires_at: float
    payload: bytes
    sha256: str
    input_authorized: bool=field(default=False,init=False)
    real_client_accepted: bool=field(default=False,init=False)


def observe_camp_contact(checkpoint,reader,first,second,*,minimum_log_seq,released_at,
                         owner_binding,binding_reader,clock=time.monotonic,local_wall_clock=datetime.now):
    if (type(checkpoint) is not CampContactCheckpoint or type(reader) is not LocationLogReader
            or any(type(v) is not RawLocationFix for v in (first,second))
            or type(minimum_log_seq) is not int or minimum_log_seq<1
            or not finite(released_at) or released_at<0
            or type(owner_binding) is not tuple or not immutable_binding(owner_binding)
            or not all(callable(v) for v in (binding_reader,clock,local_wall_clock))):
        raise ValueError('Exact contact checkpoint and newly collected stopped pair required')
    raw_states=tuple(flat_record_state(v) for v in (first,second))
    checkpoint.check()
    if reader is not checkpoint._reader or minimum_log_seq<checkpoint._reference.raw_fix.log_line_seq:
        raise ValueError('Contact collection must follow its exact reader and arrival')
    expected=(reader.zone_id,reader.zone_display_name,reader.tail.epoch,reader.zone_generation)
    last=None
    def check():
        nonlocal last
        binding=binding_reader();wall=local_wall_clock()
        checkpoint.check();now=clock();checkpoint._assert_intact()
        if (binding!=owner_binding or reader is not checkpoint._reader
                or tuple(flat_record_state(v) for v in (first,second))!=raw_states
                or not finite(now) or last is not None and now<last
                or reader.latest is not second or reader.log_line_seq!=second.log_line_seq
                or (reader.zone_id,reader.zone_display_name,reader.tail.epoch,reader.zone_generation)!=expected
                or not isinstance(wall,datetime) or wall.tzinfo is not None
                or any(not finite(v.received_monotonic) or not isinstance(v.log_local_time,datetime)
                    or v.log_local_time.tzinfo is not None for v in (first,second))
                or not 0<=now-second.received_monotonic<=.5
                or any(abs((wall-v.log_local_time).total_seconds()-(now-v.received_monotonic))>2.
                       for v in (first,second))):
            raise ValueError('Contact observation changed, expired or lost its collection scope')
        last=now;return now,wall
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
    calibration=checkpoint._calibration;fixes=[]
    for raw in (first,second):
        xy=(raw.raw_coordinates[1],raw.raw_coordinates[0])
        if not covers_closed((tuple(map(F,xy)),),(checkpoint._center_domain,)):
            raise ValueError('Stopped position left the retained contact arrival domain')
        z=F(raw.raw_coordinates[2])-F(calibration.raw_z_minus_source_z)
        error=F(calibration.residual_limit);interval=(z-error,z+error)
        compatible=tuple((v.kind,v.source_ids,v.height_interval) for v in
            checkpoint._index.compatible(xy,checkpoint._bounds,height_interval=interval))
        if not compatible:raise ValueError('Stopped contact height has no compatible local support')
        now,_=check()
        fixes.append(SourceContactFix(raw,(*xy,raw.raw_coordinates[2]-calibration.raw_z_minus_source_z),
            interval,compatible,checkpoint._coverage.sha256,now))
    common=common_contact_heights(*fixes)
    if not common:raise ValueError('Stopped contact samples have disjoint possible heights')
    observed,wall=check()
    def raw_record(raw):
        result=asdict(raw);result['log_local_time']=raw.log_local_time.isoformat();return result
    payload=encoded(dict(format='eql-camp-contact-observation-v1',checkpoint_sha256=checkpoint.sha256,
        observations=[raw_record(v) for v in (first,second)],contacts=[contact_fix_record(v) for v in fixes],
        common_height_intervals_exact=[[str(v) for v in pair] for pair in common],
        minimum_log_seq=minimum_log_seq,released_at=released_at,owner_binding=owner_binding,
        original_raw_z_minus_source_z=calibration.raw_z_minus_source_z,
        original_residual_limit=calibration.residual_limit,
        original_calibration_valid_until=calibration.valid_until_monotonic,
        original_calibration_current=calibration.valid_from_monotonic<=observed<=calibration.valid_until_monotonic,
        observed_at=observed,expires_at=second.received_monotonic+.5,local_wall_time=wall.isoformat(),
        historical_correspondence_only=True,old_calibration_renewed=False,
        current_height_verified=False,movement_calibration_available=False,
        input_authorized=False,real_client_accepted=False))
    return CampContactObservation(checkpoint,*fixes,observed,second.received_monotonic+.5,
        payload,sha256(payload).hexdigest())
