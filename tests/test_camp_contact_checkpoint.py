"""Retained contact history with synthetic client feedback; no game input."""
from dataclasses import replace
import json

import pytest

from eql_automation.camp_contact_checkpoint import CampContactCheckpoint
from eql_automation.camp_contact_observation import observe_camp_contact
from eql_automation.camp_motion_continuity import CampInputContinuity
from eql_automation.camp_probe_floor import CAMP_FLOOR_TYPES
from eql_automation.camp_stopped_height import measure_camp_stopped_height
from test_source_motion import f,legacy
from test_source_contact_controller import begin,traverse
from test_camp_motion_continuity import monitor_fixture

pytestmark=pytest.mark.parametrize('f',['contact_preflight'],indirect=True)


@pytest.fixture
def contact_checkpoint(f):
    c,_=begin(f);result,_=traverse(f,c)
    f.contact=c;f.checkpoint=CampContactCheckpoint(c,result.arrival)
    return f


def pair(f,*,y=3.6,z=2.79,second_z=None):
    baseline=f.reader.log_line_seq;released=f.now
    f.now+=.2;first=f.position(y=y,z=z)
    f.now+=.5;second=f.position(y=y,z=z if second_z is None else second_z)
    return first,second,dict(minimum_log_seq=baseline,released_at=released,
        owner_binding=('contact-camp',1),binding_reader=lambda:('contact-camp',1),
        clock=f.clock,local_wall_clock=f.wall)


def test_contact_checkpoint_keeps_actual_arrival_after_controller_retirement(contact_checkpoint,monkeypatch):
    f=contact_checkpoint;c=f.checkpoint;cal=c._calibration
    arrival=f.contact.arrival;original=f.ledger._state()
    assert c._reference is arrival.second and c._index is not f.contact.index
    assert c._reference.package_xyz[1]==3.6 and f.ledger.pose.y==2.
    assert not hasattr(c,'fork') and type(c) not in CAMP_FLOOR_TYPES
    historical=cal.valid_until_monotonic
    f.contact.cancel('released for camp');f.mode='off';f.generation+=1;f.reader.latest=None
    f.now=historical+100.
    monkeypatch.setattr(f.observer,'check',lambda:pytest.fail('Retired observer rearmed'))
    c.check();basis=json.loads(c.motion_basis());data=c.snapshot(include_evidence=True)
    assert c._calibration is cal and cal.valid_until_monotonic==historical
    assert f.ledger._state()==original
    assert basis['format']=='eql-camp-contact-arrival-motion-v1'
    assert basis['arrival_position']==list(arrival.second.package_xyz)
    assert basis['contact_checkpoint_sha256']==c.sha256 and not basis['movement_authorized']
    assert data['historical_contact_only'] and not data['ordinary_floor_available']
    assert not data['current_height_verified']


@pytest.mark.parametrize('fault',['arrival','first_raw','second_height','calibration','calibration_raw',
    'index','bounds','motion','source','static','policy','model','reader','epoch','partial','domain','payload'])
def test_changed_contact_history_is_discarded(contact_checkpoint,fault,tmp_path):
    f=contact_checkpoint;c=f.checkpoint
    if fault=='arrival':object.__setattr__(c._arrival,'payload',b'{}')
    elif fault=='first_raw':object.__setattr__(c._arrival.first.raw_fix,'log_epoch',99)
    elif fault=='second_height':object.__setattr__(c._reference,'height_interval',(0,1))
    elif fault=='calibration':object.__setattr__(c._calibration,'raw_z_minus_source_z',2.59)
    elif fault=='calibration_raw':object.__setattr__(c._calibration.evidence.first.raw_fix,'log_epoch',99)
    elif fault=='index':object.__setattr__(c._index.sheets[0],'height',0)
    elif fault=='bounds':object.__setattr__(c._bounds,'body_radius',.3)
    elif fault=='motion':object.__setattr__(c._motion,'run_speed',c._motion.run_speed+1)
    elif fault=='source':c._terrain.sources=tuple(list(c._terrain.sources))
    elif fault=='static':c._static.inventory_sha256='f'*64
    elif fault=='policy':c._classifier.inventory_sha256='f'*64
    elif fault=='model':(tmp_path/'EQGraphics.dll').write_bytes(b'changed')
    elif fault=='reader':c._reader=object()
    elif fault=='epoch':f.reader.tail.epoch+=1
    elif fault=='partial':f.reader.tail.partial='unfinished'
    elif fault=='domain':c._center_domain=tuple(list(c._center_domain))
    else:c._payload=b'{}'
    with pytest.raises(ValueError):c.check()
    assert not c.valid and c._index is None and c._reference is None
    with pytest.raises(ValueError):c.motion_basis()


@pytest.mark.parametrize('fault',['clone','expired','cancel','focus','input','final_callback'])
def test_capture_requires_live_exact_arrival_through_final_callback(f,fault,monkeypatch):
    c,_=begin(f);result,_=traverse(f,c);arrival=result.arrival
    if fault=='clone':arrival=replace(arrival)
    elif fault=='expired':f.now+=.51
    elif fault=='cancel':c.cancel('F9')
    elif fault=='focus':f.focus=False
    elif fault=='input':f.active=True
    else:
        from eql_automation.installed_region_model import InstalledRegionModel
        original=InstalledRegionModel.check_policy
        def revoke(model,policy):
            original(model,policy);f.generation+=1
        monkeypatch.setattr(InstalledRegionModel,'check_policy',revoke)
    with pytest.raises((ValueError,RuntimeError)):CampContactCheckpoint(c,arrival)


@pytest.mark.parametrize('stop',['F8','F9','physical_input'])
def test_input_continuity_owns_contact_checkpoint(contact_checkpoint,stop):
    c=contact_checkpoint.checkpoint;m,_,device,_=monitor_fixture()
    m=CampInputContinuity(m.observer,topology=m.topology,basis=c.motion_basis(),
        binding=m.binding,clock=m.clock,floor=c)
    m.check(m.binding)
    if stop=='physical_input':
        device.pending=[(1,106,1),(1,106,0)]
        with pytest.raises(ValueError):m.check(m.binding)
    else:m.close(stop)
    assert not m.valid and not c.valid and c._index is None


@pytest.mark.parametrize('expired',[False,True])
def test_new_stopped_contact_pair_never_snaps_or_refits_offset(contact_checkpoint,expired):
    f=contact_checkpoint;c=f.checkpoint;cal=c._calibration;deadline=cal.valid_until_monotonic
    f.contact.cancel('camp');f.mode='off';f.generation+=1
    if expired:f.now=deadline+1
    a,b,options=pair(f);result=observe_camp_contact(c,f.reader,a,b,**options)
    record=json.loads(result.payload)
    assert result.first.raw_fix is a and result.second.raw_fix is b
    assert result.second.package_xyz[2]==b.raw_coordinates[2]-2.5
    assert result.second.package_xyz[2]!=.2
    assert [v[0] for v in result.second.compatible_states]==['sheet_top']
    assert record['original_raw_z_minus_source_z']==2.5
    assert record['original_calibration_valid_until']==deadline
    assert record['original_calibration_current'] is not expired
    assert record['historical_correspondence_only'] and not record['old_calibration_renewed']
    assert not record['current_height_verified'] and not record['movement_calibration_available']
    assert cal.valid_until_monotonic==deadline and c._calibration is cal
    with pytest.raises(ValueError):measure_camp_stopped_height(c,f.reader,a,b,**options)


@pytest.mark.parametrize('fault',['far_corridor','unsupported','disjoint','moving','baseline','duplicate',
    'stale','early_release','zone','binding','discarded','backwards','mutated_raw','late_cancel'])
def test_invalid_contact_observation_cannot_resume_camp(contact_checkpoint,fault):
    f=contact_checkpoint;c=f.checkpoint
    a,b,options=pair(f,y=2.4 if fault=='far_corridor' else 3.6,
        z=2.7 if fault in ('far_corridor','disjoint') else 2.79,
        second_z=2.79 if fault=='disjoint' else 2.9 if fault=='unsupported' else None)
    if fault=='moving':a=replace(a,raw_coordinates=(3.,4.,2.79))
    elif fault=='baseline':options['minimum_log_seq']=c._reference.raw_fix.log_line_seq-1
    elif fault=='duplicate':a=b
    elif fault=='stale':f.now+=.51
    elif fault=='early_release':options['released_at']=a.received_monotonic
    elif fault=='zone':a=replace(a,zone_id=54)
    elif fault=='binding':options['binding_reader']=lambda:('wrong',1)
    elif fault=='discarded':c.invalidate('F9')
    elif fault in ('backwards','mutated_raw','late_cancel'):
        calls=[]
        def clock():
            calls.append(1)
            if len(calls)==4:
                if fault=='backwards':f.now-=.01
                elif fault=='mutated_raw':object.__setattr__(a,'raw_coordinates',(3.6,4.,100.))
                else:c.invalidate('F9 in final callback')
            return f.now
        options['clock']=clock
    with pytest.raises(ValueError):observe_camp_contact(c,f.reader,a,b,**options)


def test_initial_source_callback_cannot_replace_the_observed_raw_values(contact_checkpoint,monkeypatch):
    from eql_automation.installed_region_model import InstalledRegionModel
    f=contact_checkpoint;a,b,options=pair(f)
    original=InstalledRegionModel.check_policy;calls=[]
    def mutate(model,policy):
        original(model,policy);calls.append(1)
        if len(calls)==1:object.__setattr__(a,'raw_coordinates',(3.6,4.,2.8))
    monkeypatch.setattr(InstalledRegionModel,'check_policy',mutate)
    with pytest.raises(ValueError):observe_camp_contact(f.checkpoint,f.reader,a,b,**options)
