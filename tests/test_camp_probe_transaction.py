"""Actual source-floor/reader contracts with synthetic receipts; no game input."""
from dataclasses import replace
from hashlib import sha256
import json
import math
import threading

import pytest

from eql_automation.camp_probe_transaction import CampProbeTransaction
from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.uinput_watchdog import PulseReceipt
from test_camp_probe_preparation import probe,start
from test_camp_floor_checkpoint import checkpoint
from test_source_motion import f
from test_route_floor_commit import legacy


def staged(f):
    f.probe.prepare();fresh=start(f)
    tx=CampProbeTransaction(f.probe,stop_lock=threading.RLock())
    ticket=tx.stage(fresh,movement_key=103,requested_seconds=.02)
    return tx,ticket


def receipt(f,ticket):
    at=ticket.proposed_at
    f.now=at+.026
    return PulseReceipt(103,.02,at+.001,at+.002,at+.024,at+.025,'elapsed')


def sealed(f):
    tx,ticket=staged(f)
    seal=tx.seal_release(ticket,receipt(f,ticket))
    return tx,seal


def pair(f,*,x=4.5,y=2.,z=2.7):
    baseline=f.reader.log_line_seq
    f.now+=.2;first=f.position(x=x,y=y,z=z)
    f.now+=.5;second=f.position(x=x,y=y,z=z)
    return first,second,baseline


def prepared(f):
    tx,seal=sealed(f);a,b,_=pair(f)
    tx.prepare_endpoint(seal,a,b)
    return tx,seal,a,b


def test_probe_confirms_moved_floor_without_rearming_old_calibration(probe):
    f=probe;original=_chain_snapshot(f.checkpoint._chain)
    old_expiry=f.checkpoint._calibration.valid_until_monotonic
    tx,seal,a,b=prepared(f)
    # The moved point really is outside the original stopped-arrival cap.
    with pytest.raises(ValueError):f.checkpoint._chain.floor_at((4.5,2.))
    first,second,baseline=pair(f)
    result=tx.confirm_endpoint(first,second,minimum_log_seq=baseline)
    record=json.loads(result.payload)
    assert result.package_xyz==(4.5,2.,.2) and result.raw_z_minus_source_z==2.5
    assert result.expires_at==second.received_monotonic+.5
    assert record['endpoint_geometry']['planning_observations'][1]['log_line_seq']==b.log_line_seq
    assert sha256(result.payload).hexdigest()==result.sha256
    assert not any(record[k] for k in ('input_authorized','current_motion_verified',
        'current_heading_verified','real_client_accepted','sender_origin_verified'))
    f.now+=10. # Returning historical floor evidence never refreshes the pair.
    fork=tx.fork_reached(result)
    assert fork.floor_at((4.5,2.))[0]==.2 and fork is not tx._endpoint
    assert result.expires_at<f.now
    assert _chain_snapshot(f.checkpoint._chain)==original
    assert f.checkpoint._calibration.valid_until_monotonic==old_expiry
    assert f.drain_events()==() and not seal.sender_origin_verified


def test_slow_endpoint_geometry_requires_fresh_confirmation(probe,monkeypatch):
    import eql_automation.camp_probe_transaction as mod
    f=probe;tx,seal=sealed(f);a,b,_=pair(f)
    actual=mod.check_source_footprint
    def slow(*args,**kw):
        checked=actual(*args,**kw);f.now+=1.;return checked
    monkeypatch.setattr(mod,'check_source_footprint',slow)
    tx.prepare_endpoint(seal,a,b)
    assert f.now>b.received_monotonic+.5 and tx.result is None
    first,second,baseline=pair(f)
    result=tx.confirm_endpoint(first,second,minimum_log_seq=baseline)
    assert result.expires_at==second.received_monotonic+.5
    assert result.expires_at!=b.received_monotonic+.5


@pytest.mark.parametrize('fault',('wrong_key','wrong_duration','interrupted','zero_hold',
    'short_hold','overhold','late_down','late_receipt','backwards','nonfinite','new_reply'))
def test_invalid_receipts_never_acquire_endpoint_evidence(probe,fault):
    f=probe;tx,ticket=staged(f);r=receipt(f,ticket)
    if fault=='wrong_key':r=replace(r,key_code=105)
    elif fault=='wrong_duration':r=replace(r,requested_seconds=.01)
    elif fault=='interrupted':r=replace(r,completion='interrupted')
    elif fault=='zero_hold':r=replace(r,up_started_at=r.down_completed_at)
    elif fault=='short_hold':r=replace(r,up_started_at=r.down_completed_at+.01)
    elif fault=='overhold':
        r=replace(r,up_started_at=r.down_started_at+.051,up_completed_at=r.down_started_at+.052)
        f.now=r.up_completed_at+.001
    elif fault=='late_down':
        r=replace(r,down_started_at=ticket.proposed_at+.06,down_completed_at=ticket.proposed_at+.061,
            up_started_at=ticket.proposed_at+.083,up_completed_at=ticket.proposed_at+.084)
        f.now=r.up_completed_at+.001
    elif fault=='late_receipt':f.now=r.up_completed_at+.31
    elif fault=='backwards':r=replace(r,down_completed_at=r.down_started_at-.001)
    elif fault=='nonfinite':r=replace(r,up_completed_at=math.nan)
    else:f.position()
    with pytest.raises(ValueError):tx.seal_release(ticket,r)
    assert tx.phase=='stopped' and tx.seal is None and f.checkpoint.valid


def test_key_kind_mismatch_is_rejected_before_start_is_consumed(probe):
    f=probe;f.probe.prepare();fresh=start(f)
    tx=CampProbeTransaction(f.probe,stop_lock=threading.RLock())
    with pytest.raises(ValueError):tx.stage(fresh,movement_key=105,requested_seconds=.02)
    assert tx.ticket is None


def test_start_cannot_be_used_by_second_transaction(probe):
    f=probe;tx,ticket=staged(f)
    other=CampProbeTransaction(f.probe,stop_lock=tx.lock)
    with pytest.raises(ValueError):other.stage(ticket.start,movement_key=103,requested_seconds=.02)
    with pytest.raises(ValueError):tx.seal_release(ticket,receipt(f,ticket))


@pytest.mark.parametrize('fault',('stale','early','moving','wrong_height','outside','old_pair','zone'))
def test_bad_post_release_pairs_are_discarded(probe,fault):
    f=probe;tx,seal=sealed(f)
    if fault=='old_pair':a,b=tx.ticket.start.height.first,tx.ticket.start.height.second
    else:
        a,b,_=pair(f,x=6. if fault=='outside' else 4.5,z=2.8 if fault=='wrong_height' else 2.7)
        if fault=='stale':f.now+=.51
        elif fault=='early':a=replace(a,received_monotonic=seal.receipt.up_completed_at+.01)
        elif fault=='moving':a=replace(a,raw_coordinates=(2.,4.,2.7))
        elif fault=='zone':a=replace(a,zone_id=54)
    with pytest.raises(ValueError):tx.prepare_endpoint(seal,a,b)
    assert tx.phase=='stopped' and tx.result is None


def test_whole_body_must_fit_prepared_envelope_even_when_center_fits(probe):
    f=probe;tx,seal=sealed(f);bounds=f.probe.bounds
    limit=tx._envelope.record()['maximum_center_travel']+bounds.position_error+bounds.post_release_drift
    # Center passes the radial check, but keeping another position-error body
    # margin around this point would extend outside the prepared polygon.
    # Aim at a polygon face normal, rather than the extra slack at a vertex.
    angle=math.pi/16
    a,b,_=pair(f,x=round(4.+limit*math.cos(angle),2),y=round(2.+limit*math.sin(angle),2))
    with pytest.raises(ValueError,match='Endpoint body'):tx.prepare_endpoint(seal,a,b)


@pytest.mark.parametrize('fault',('old_pair','changed_position','expired','late_geometry','new_reply'))
def test_confirmation_never_promotes_planning_pair(probe,fault):
    f=probe;tx,seal,a,b=prepared(f);baseline=b.log_line_seq
    if fault!='old_pair':a,b,baseline=pair(f,x=4.51 if fault=='changed_position' else 4.5)
    if fault=='expired':f.now+=.51
    elif fault=='late_geometry':f.now=tx._confirmation_deadline+.01
    elif fault=='new_reply':f.position(x=4.5)
    with pytest.raises(ValueError):tx.confirm_endpoint(a,b,minimum_log_seq=baseline)
    assert tx.phase=='stopped' and tx.result is None


@pytest.mark.parametrize('phase',('staging','checking_pair','confirming'))
def test_reentrant_stop_cannot_publish_next_phase(probe,phase):
    f=probe
    if phase=='staging':
        f.probe.prepare();fresh=start(f)
        tx=CampProbeTransaction(f.probe,stop_lock=threading.RLock())
        operation=lambda:tx.stage(fresh,movement_key=103,requested_seconds=.02)
    elif phase=='checking_pair':
        tx,seal=sealed(f);a,b,_=pair(f)
        operation=lambda:tx.prepare_endpoint(seal,a,b)
    else:
        tx,_,_,_=prepared(f);a,b,baseline=pair(f)
        operation=lambda:tx.confirm_endpoint(a,b,minimum_log_seq=baseline)
    def stop():
        if tx.phase==phase:tx.cancel('F9 in context callback')
    f.binding_hook=stop
    with pytest.raises(ValueError):operation()
    assert tx.phase=='stopped' and tx.result is None and f.checkpoint.valid


def test_geometry_releases_stop_lock_and_cancel_discards_candidate(probe,monkeypatch):
    import eql_automation.camp_probe_transaction as mod
    f=probe;tx,seal=sealed(f);a,b,_=pair(f);actual=mod.check_source_footprint
    def cancelled(*args,**kw):
        worker=threading.Thread(target=lambda:tx.cancel('F9 during endpoint work'))
        worker.start();worker.join(timeout=1.)
        assert not worker.is_alive(),'Geometry held the stop lock'
        return actual(*args,**kw)
    monkeypatch.setattr(mod,'check_source_footprint',cancelled)
    with pytest.raises(ValueError):tx.prepare_endpoint(seal,a,b)
    assert tx.phase=='stopped' and tx._endpoint is None and tx.seal is seal


@pytest.mark.parametrize('fault',('start','start_raw','receipt','removed_ticket','lease','binding','payload'))
def test_changed_owned_evidence_cannot_be_committed(probe,fault):
    f=probe;tx,seal,a,b=prepared(f)
    if fault=='start':object.__setattr__(tx.ticket.start,'expires_at',f.now+20.)
    elif fault=='start_raw':object.__setattr__(tx.ticket.start.height.first,'raw_coordinates',(9.,9.,9.))
    elif fault=='receipt':object.__setattr__(seal.receipt,'key_code',105)
    elif fault=='removed_ticket':tx.ticket=None
    elif fault=='lease':f.lease.release()
    elif fault=='binding':f.camp_binding=('other-camp',2)
    else:tx._endpoint_payload=b'{}'
    first,second,baseline=pair(f)
    with pytest.raises(ValueError):tx.confirm_endpoint(first,second,minimum_log_seq=baseline)
    assert tx.phase=='stopped' and tx.result is None


def test_mutated_result_cannot_supply_a_floor_fork(probe):
    f=probe;tx,_,_,_=prepared(f);a,b,baseline=pair(f)
    result=tx.confirm_endpoint(a,b,minimum_log_seq=baseline)
    object.__setattr__(result,'payload',b'{}')
    with pytest.raises(ValueError):tx.fork_reached(result)
    assert tx.phase=='stopped'
