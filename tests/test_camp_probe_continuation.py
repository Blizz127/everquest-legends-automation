"""Chained source-floor probes; synthetic receipts/positions, no game input."""
from dataclasses import replace
import json
import threading

import pytest

from eql_automation.camp_probe_floor import CampProbeFloorReference
from eql_automation.camp_probe_preparation import CampProbePreparation
from eql_automation.camp_probe_transaction import CampProbeTransaction
from eql_automation.camp_stopped_height import measure_camp_stopped_height
from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.uinput_watchdog import PulseReceipt
from test_camp_probe_transaction import prepared,pair,staged
from test_camp_probe_preparation import probe
from test_camp_floor_checkpoint import checkpoint
from test_source_motion import f
from test_route_floor_commit import legacy


def confirmed(f):
    tx,_,_,_=prepared(f);a,b,baseline=pair(f)
    result=tx.confirm_endpoint(a,b,minimum_log_seq=baseline)
    return tx,result


def new_height(f,reference):
    released=f.now
    x,y,_=reference._result.package_xyz
    a,b,baseline=pair(f,x=x,y=y)
    return measure_camp_stopped_height(reference,f.reader,a,b,
        minimum_log_seq=baseline,released_at=released,owner_binding=f.camp_binding,
        binding_reader=f.probe.binding_reader,clock=f.clock,local_wall_clock=f.wall)


def next_preparation(f,reference,*,kind='right'):
    height=new_height(f,reference);old=f.probe
    p=CampProbePreparation(reference,height,f.lease,probe_kind=kind,
        bounds=old.bounds,bounds_basis=old.bounds_basis,owner_binding=f.camp_binding,
        binding_reader=old.binding_reader,clock=f.clock,local_wall_clock=f.wall)
    return p


def finish_probe(f,p,lock,*,x):
    p.prepare();released=f.now
    a,b,baseline=pair(f,x=p.height.package_xyz[0],y=p.height.package_xyz[1])
    start=p.observe_start(a,b,minimum_log_seq=baseline,released_at=released)
    tx=CampProbeTransaction(p,stop_lock=lock)
    key={'forward':103,'left':105,'right':106}[p.kind]
    ticket=tx.stage(start,movement_key=key,requested_seconds=.02)
    at=ticket.proposed_at;f.now=at+.026
    seal=tx.seal_release(ticket,PulseReceipt(key,.02,at+.001,at+.002,at+.024,at+.025,'elapsed'))
    a,b,_=pair(f,x=x);tx.prepare_endpoint(seal,a,b)
    a,b,baseline=pair(f,x=x)
    return tx,tx.confirm_endpoint(a,b,minimum_log_seq=baseline)


def test_seven_probe_continuation_preserves_arrival_and_all_observation_ages(probe):
    f=probe;original=_chain_snapshot(f.checkpoint._chain)
    calibration=f.checkpoint._calibration;expiry=calibration.valid_until_monotonic
    tx,result=confirmed(f);first_tx=tx
    results=[result];references=[];heights=[];lock=tx.lock
    sequence=(('right',4.5),('forward',5.),('right',5.),
              ('forward',5.5),('left',5.5),('forward',6.))
    for kind,x in sequence:
        reference=tx.retain_endpoint(result);references.append(reference)
        assert reference is not f.checkpoint
        p=next_preparation(f,reference,kind=kind);heights.append(p.height)
        assert p.height.first.log_line_seq>result.second.log_line_seq
        assert p.height.expires_at==p.height.second.received_monotonic+.5
        tx,result=finish_probe(f,p,lock,x=x);results.append(result)
    assert len(results)==7 and result.package_xyz==(6.,2.,.2)
    assert len({r.sha256 for r in results})==7
    assert _chain_snapshot(f.checkpoint._chain)==original
    assert f.checkpoint._calibration is calibration and calibration.valid_until_monotonic==expiry
    assert f.now>results[0].expires_at
    for reference in references:
        reference.check()
        data=reference.snapshot(include_evidence=True)
        assert data['historical_floor_only'] and not data['input_authorized']
        assert data['evidence']['arrival_expires_at']==reference._result.expires_at
        assert not data['evidence']['old_calibration_renewed']
    assert f.drain_events()==()
    # An ancestor stop invalidates the entire sequence, including its last fork.
    first_tx.cancel('F9 after seven probes')
    with pytest.raises(ValueError):tx.fork_reached(result)
    assert f.checkpoint.valid and _chain_snapshot(f.checkpoint._chain)==original


def test_result_pair_cannot_be_relabelled_as_new_height(probe):
    f=probe;tx,result=confirmed(f);reference=tx.retain_endpoint(result)
    with pytest.raises(ValueError,match='baseline|new consecutive'):
        measure_camp_stopped_height(reference,f.reader,result.first,result.second,
            minimum_log_seq=result.second.log_line_seq,released_at=tx.seal.receipt.up_completed_at,
            owner_binding=f.camp_binding,binding_reader=f.probe.binding_reader,
            clock=f.clock,local_wall_clock=f.wall)
    assert reference.valid and reference._result.expires_at==result.expires_at


@pytest.mark.parametrize('fault',('stale','latest','different_result','duplicate','unconfirmed'))
def test_reference_transfer_requires_exact_fresh_unused_confirmation(probe,fault):
    f=probe;tx,result=confirmed(f)
    if fault=='stale':f.now=result.expires_at+.01
    elif fault=='latest':f.position(x=4.5)
    elif fault=='different_result':result=replace(result)
    elif fault=='duplicate':tx.retain_endpoint(result)
    else:tx.phase='await_pair'
    with pytest.raises(ValueError):tx.retain_endpoint(result)
    assert tx.phase=='stopped' and f.checkpoint.valid


@pytest.mark.parametrize('fault',('floor','result','parent','binding','lease','payload'))
def test_changed_reference_or_ancestry_prevents_next_preparation(probe,fault):
    f=probe;tx,result=confirmed(f);reference=tx.retain_endpoint(result)
    if fault=='floor':reference._chain.seed_evidence_sha256='f'*64
    elif fault=='result':object.__setattr__(result,'package_xyz',(9.,9.,9.))
    elif fault=='parent':f.checkpoint.invalidate('original camp discarded')
    elif fault=='binding':f.camp_binding=('another camp',2)
    elif fault=='lease':f.lease.release()
    else:reference._payload=b'{}'
    with pytest.raises(ValueError):next_preparation(f,reference)
    assert not reference.valid


@pytest.mark.parametrize('phase',('retaining','continued'))
def test_stop_during_transfer_cannot_return_a_live_reference(probe,phase):
    f=probe;tx,result=confirmed(f)
    def stop():
        if tx.phase==phase:tx.cancel('F9 during transfer')
    f.binding_hook=stop
    with pytest.raises(ValueError):tx.retain_endpoint(result)
    assert tx.phase=='stopped'
    assert tx._continuation is None or not tx._continuation.valid


def test_reference_fork_and_history_do_not_expose_owned_branch(probe):
    f=probe;tx,result=confirmed(f);reference=tx.retain_endpoint(result)
    fork=reference.fork();fork.seed_evidence_sha256='f'*64
    snapshot=reference.snapshot(include_evidence=True)
    snapshot['evidence']['arrival_position']=[9.,9.,9.]
    reference.check()
    assert reference.fork().seed_evidence_sha256!='f'*64
    assert json.loads(reference._payload)['arrival_position']==[4.5,2.,.2]


def test_next_transaction_cannot_replace_shared_stop_lock(probe):
    f=probe;tx,result=confirmed(f);reference=tx.retain_endpoint(result)
    p=next_preparation(f,reference)
    with pytest.raises(ValueError,match='original stop lock'):
        CampProbeTransaction(p,stop_lock=threading.RLock())


def test_reference_cannot_be_constructed_from_an_unconfirmed_transaction(probe):
    f=probe;tx,ticket=staged(f)
    with pytest.raises(ValueError):CampProbeFloorReference(tx,ticket)
