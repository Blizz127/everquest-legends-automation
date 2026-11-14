"""Fresh source-height observations on a retained in-memory camp checkpoint."""
from dataclasses import replace
from hashlib import sha256
import json

import pytest

from eql_automation.camp_stopped_height import measure_camp_stopped_height
from test_camp_floor_checkpoint import checkpoint
from test_source_motion import f
from test_route_floor_commit import legacy


def pair(f):
    baseline=f.reader.log_line_seq;released=f.now
    f.now+=.2;first=f.position()
    f.now+=.5;second=f.position()
    options=dict(minimum_log_seq=baseline,released_at=released,
        owner_binding=('camp-height',1),binding_reader=lambda:('camp-height',1),
        clock=f.clock,local_wall_clock=f.wall)
    return first,second,options


def test_new_pair_measures_same_floor_without_renewing_old_height(checkpoint):
    f=checkpoint;c=f.checkpoint;old=c._calibration
    f.mode='off';f.generation+=1;f.reader.latest=None
    f.now=old.valid_until_monotonic+10.
    first,second,options=pair(f)
    result=measure_camp_stopped_height(c,f.reader,first,second,**options)
    data=json.loads(result.payload)
    assert result.first is first and result.second is second
    assert result.package_xyz==(4.,2.,.2) and result.raw_z_minus_source_z==2.5
    assert result.expires_at==second.received_monotonic+.5
    assert result.observed_at>old.valid_until_monotonic and c._calibration is old
    assert not data['old_calibration_renewed'] and data['checkpoint_sha256']==c.sha256
    assert sha256(result.payload).hexdigest()==result.sha256
    assert not result.input_authorized and not result.real_client_accepted
    assert f.reader.latest is second and c.valid


@pytest.mark.parametrize('fault',('old_pair','baseline','duplicate','moving','above_floor','outside_cap',
    'offset','stale','early_release','wrong_zone','binding','discarded','backwards_time','late_cancel'))
def test_old_or_changed_observations_cannot_reuse_floor_correspondence(checkpoint,fault):
    f=checkpoint;c=f.checkpoint;first,second,options=pair(f)
    if fault=='old_pair':first,second=f.first.raw_fix,f.second.raw_fix
    elif fault=='baseline':options['minimum_log_seq']=c._reference.raw_fix.log_line_seq-1
    elif fault=='duplicate':first=second
    elif fault=='moving':first=replace(first,raw_coordinates=(3.,4.,2.7))
    elif fault in ('above_floor','offset'):
        height=20. if fault=='above_floor' else 2.8
        first=replace(first,raw_coordinates=(2.,4.,height))
        second=replace(second,raw_coordinates=(2.,4.,height));f.reader.latest=second
    elif fault=='outside_cap':
        first=replace(first,raw_coordinates=(2.,5.,2.7))
        second=replace(second,raw_coordinates=(2.,5.,2.7));f.reader.latest=second
    elif fault=='stale':f.now+=.51
    elif fault=='early_release':options['released_at']=first.received_monotonic
    elif fault=='wrong_zone':first=replace(first,zone_id=54)
    elif fault=='binding':options['binding_reader']=lambda:('changed',2)
    elif fault=='discarded':c.invalidate('F9')
    else:
        calls=[]
        def clock():
            calls.append(1)
            if len(calls)==4:
                if fault=='late_cancel':c.invalidate('F9 at final observation')
                else:f.now-=.01
            return f.now
        options['clock']=clock
    with pytest.raises(ValueError):measure_camp_stopped_height(c,f.reader,first,second,**options)
