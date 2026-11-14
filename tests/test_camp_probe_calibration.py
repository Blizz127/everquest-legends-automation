"""Conditional fitting from synthetic per-leg observations and actual floor ledgers."""
from dataclasses import replace
import math
import threading
from types import SimpleNamespace

import pytest

from eql_automation.camp_probe_calibration import reduce_camp_probes
from eql_automation.camp_probe_preparation import CampProbePreparation
from eql_automation.camp_probe_runtime import CampProbeRuntime
from eql_automation.camp_probe_transaction import CampProbeTransaction
from eql_automation.camp_stopped_height import measure_camp_stopped_height
from eql_automation.location_hotkey import OwnerLocationHotkey
from eql_automation.motion_calibration import (CalibrationUnavailable, PROBES,
    StoppedPair, reduce_probe_legs)
from eql_automation.uinput_watchdog import PulseReceipt
from test_motion_calibration import experiment, legacy as fitter
from test_camp_probe_preparation import probe
from test_camp_probe_transaction import pair
from test_camp_floor_checkpoint import checkpoint
from test_source_motion import f
from test_route_floor_commit import legacy


def separated():
    pairs, receipts, heading = experiment()
    before, after, holds = [], [], []
    for i, receipt in enumerate(receipts):
        def shifted(p, seq):
            return StoppedPair(replace(p.first, at=p.first.at+3*i, sequence=seq),
                               replace(p.second, at=p.second.at+3*i, sequence=seq+1))
        before.append(shifted(pairs[i], i*4))
        after.append(shifted(pairs[i+1], i*4+2))
        holds.append(replace(receipt, **{name:getattr(receipt,name)+3*i for name in
            ('down_started_at','down_completed_at','up_started_at','up_completed_at')}))
    return before, after, holds, heading


def test_distinct_stationary_pairs_fit_without_rewriting_timestamps(fitter):
    before,after,receipts,heading=separated()
    result=reduce_probe_legs(before,after,receipts,legacy=fitter,horizontal_error=.01,record_id='separate')
    assert result['estimate']['run_speed']==pytest.approx(30.)
    assert result['estimate']['turn_rate']==pytest.approx(170.)
    assert result['estimate']['turn_latency']==pytest.approx(.03)
    assert result['estimate']['final_heading']==pytest.approx(heading)
    assert result['before_pairs'][1]['first']['at']==before[1].first.at
    assert result['after_pairs'][0]['second']['at']!=before[1].first.at
    assert 'pairs' not in result and result['verified_speed_upper_bound'] is None
    assert not result['input_authorized'] and not result['current_heading_verified']
    assert fitter.Calibration.from_json(result) is None


@pytest.mark.parametrize('fault',('gap_translation','reused_pair','wrong_key','equal_turns','cancelled','epoch'))
def test_separated_probe_contradictions_refused(fitter,fault):
    before,after,receipts,_=separated()
    if fault=='gap_translation':
        p=before[1];coords=tuple(v+.2 for v in p.first.raw_yxz[:2])+(p.first.raw_yxz[2],)
        before[1]=StoppedPair(replace(p.first,raw_yxz=coords),replace(p.second,raw_yxz=coords))
    elif fault=='reused_pair':before[1]=after[0]
    elif fault=='wrong_key':receipts[1]=replace(receipts[1],key_code=105)
    elif fault=='equal_turns':receipts[3]=replace(receipts[3],requested_seconds=.05)
    elif fault=='cancelled':receipts[0]=replace(receipts[0],completion='stopped')
    else:before[1]=replace(before[1],first=replace(before[1].first,log_epoch=8))
    with pytest.raises(CalibrationUnavailable):
        reduce_probe_legs(before,after,receipts,legacy=fitter,horizontal_error=.01,record_id='bad')


@pytest.fixture
def completed(probe,tmp_path):
    """Genuine transactions, synthetic receipts; no sender or game execution."""
    h=probe;bounds=replace(h.probe.bounds,maximum_requested_hold=.15,maximum_actual_hold=.18,
                         forward_speed_upper_bound=10.)
    root=CampProbePreparation(h.checkpoint,h.height,h.lease,probe_kind='forward',bounds=bounds,
        bounds_basis=h.probe.bounds_basis,owner_binding=h.camp_binding,
        binding_reader=h.probe.binding_reader,clock=h.clock,local_wall_clock=h.wall)
    config=tmp_path/'calibration-hotkey.ini';config.write_text('synthetic F1 = /location\n')
    hotkey=OwnerLocationHotkey.configured('F1',confirmation_id='synthetic',configuration_paths=(config,))
    lock=threading.RLock()
    r=CampProbeRuntime(root,sender=h.sender,hotkey=hotkey,
        owner_input=SimpleNamespace(sample=lambda:None),stop_lock=lock,
        movement_policy_factory=lambda tx:None,check_current=lambda:None,
        command_state_clear=lambda:True,pump=lambda:None,probes=PROBES)
    h.runtime=r;x,y=4.,2.;heading=0.;p=root
    for i,step in enumerate(PROBES):
        p.prepare();released=h.now
        a,b,baseline=pair(h,x=x,y=y)
        start=p.observe_start(a,b,minimum_log_seq=baseline,released_at=released)
        tx=CampProbeTransaction(p,stop_lock=lock)
        ticket=tx.stage(start,movement_key=step.key_code,requested_seconds=step.seconds)
        at=h.now
        receipt=PulseReceipt(step.key_code,step.seconds,at+.001,at+.0012,
                             at+.0012+step.seconds,at+.0014+step.seconds,'elapsed')
        h.now=receipt.up_completed_at+.001
        seal=tx.seal_release(ticket,receipt)
        seconds=(receipt.maximum_held_seconds+receipt.up_started_at-receipt.down_completed_at)/2
        if step.key=='forward':
            y+=math.cos(math.radians(heading))*10*seconds
            x+=math.sin(math.radians(heading))*10*seconds
        else:heading+=(1 if step.key=='right' else -1)*170*(seconds-.03)
        # Printed locations have two decimals, just like the existing fixture.
        x,y=round(x,2),round(y,2)
        a,b,_=pair(h,x=x,y=y);tx.prepare_endpoint(seal,a,b)
        h.now+=3.  # Slow geometry/confirmation must not replace immediate samples.
        a,b,baseline=pair(h,x=x,y=y)
        result=tx.confirm_endpoint(a,b,minimum_log_seq=baseline)
        reference=tx.retain_endpoint(result)
        r.transactions.append(tx);r.results.append(result);r.reference=reference;r.index=i+1
        if i<6:
            released=h.now;a,b,baseline=pair(h,x=x,y=y)
            height=measure_camp_stopped_height(reference,h.reader,a,b,minimum_log_seq=baseline,
                released_at=released,owner_binding=h.camp_binding,binding_reader=p.binding_reader,
                clock=h.clock,local_wall_clock=h.wall)
            p=CampProbePreparation(reference,height,h.lease,probe_kind=PROBES[i+1].key,
                bounds=bounds,bounds_basis=root.bounds_basis,owner_binding=h.camp_binding,
                binding_reader=p.binding_reader,clock=h.clock,local_wall_clock=h.wall)
    r.preparation=p;r.phase='complete'
    return h


@pytest.mark.parametrize('f',['compact_long'],indirect=True)
def test_completed_transactions_reduce_actual_initial_pairs_and_confirmations(completed,fitter):
    h=completed;r=h.runtime
    result=reduce_camp_probes(r,legacy=fitter,record_id='synthetic-transaction-chain')
    assert result['estimate']['run_speed']==pytest.approx(10.,abs=.05)
    assert result['confirmed_at']==r.results[-1].second.received_monotonic
    assert len(result['retained_evidence'])==7 and result['verified_speed_upper_bound'] is None
    assert not result['input_authorized'] and not result['real_client_accepted']
    for i,tx in enumerate(r.transactions):
        assert result['after_pairs'][i]['first']['at']==tx._planning_pair[0].received_monotonic
        assert result['retained_evidence'][i]['confirmation'][0]['received_monotonic']>tx.seal.receipt.up_completed_at+2.5
    assert r.lease.active and h.reader.latest is r.results[-1].second and h.drain_events()==()
    r.transactions[0].cancel('F9 ancestor stop')
    with pytest.raises(ValueError):reduce_camp_probes(r,legacy=fitter,record_id='cancelled')


@pytest.mark.parametrize('f',['compact_long'],indirect=True)
@pytest.mark.parametrize('fault',('results_order','lease_released','callback_stop','callback_replace','callback_error'))
def test_changed_owned_scope_cannot_publish_a_fit(completed,fitter,fault):
    h=completed;r=h.runtime
    if fault=='results_order':r.results[0],r.results[1]=r.results[1],r.results[0]
    elif fault=='lease_released':r.release()
    else:
        actual=fitter.fit_calibration
        def fit(*args,**kwargs):
            result=actual(*args,**kwargs)
            if fault=='callback_stop':r.cancel('F9 during fitter')
            else:r.results=list(reversed(r.results))
            if fault=='callback_error':raise fitter.CalibrationError('Synthetic failed fit after scope change')
            return result
        fitter=SimpleNamespace(**{name:getattr(fitter,name) for name in
            ('bearing','Loc','wrap180','LATENCY_MAX','CalibrationError')},fit_calibration=fit)
    with pytest.raises(ValueError) as raised:reduce_camp_probes(r,legacy=fitter,record_id='changed')
    assert not isinstance(raised.value,CalibrationUnavailable)
    assert h.drain_events()==()
