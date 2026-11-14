"""Historical stopped-floor ownership; synthetic observations, no game input."""
import pytest

from eql_automation.camp_floor_checkpoint import CampFloorCheckpoint
from eql_automation.camp_motion_continuity import CampInputContinuity
from eql_automation.route_floor_commit import _chain_snapshot
from test_source_motion import f
from test_route_floor_commit import legacy
from test_camp_motion_continuity import monitor_fixture


@pytest.fixture
def checkpoint(f):
    f.real=False;f.now=max(f.observer.last_at,f.second.raw_fix.received_monotonic+.01)
    f.checkpoint=CampFloorCheckpoint(f.ledger)
    return f


def test_fork_keeps_exact_arrival_layer_without_keeping_old_observer_active(checkpoint):
    f=checkpoint;c=f.checkpoint;original=_chain_snapshot(f.ledger.chain)
    assert c._chain is not f.ledger.chain
    assert c._reference is f.ledger.reference and c._calibration is f.observer.calibration
    historical=c._calibration.valid_until_monotonic
    f.mode='off';f.generation+=1;f.reader.latest=None;f.now=historical+100.
    with pytest.raises(ValueError):f.observer.check()
    c.check();branch=c.fork()
    assert branch is not c._chain and branch.previous.proof_sha256==f.ledger.chain.previous.proof_sha256
    assert branch.floor_at((4.,2.))[0]==.2
    assert _chain_snapshot(f.ledger.chain)==original and c._calibration.valid_until_monotonic==historical
    record=c.snapshot(include_evidence=True)
    assert record['historical_floor_only'] and not record['current_height_verified']
    assert record['evidence']['requires_fresh_stopped_pair'] and record['evidence']['requires_fresh_height']
    branch.seed_evidence_sha256='f'*64
    assert c.fork().seed_evidence_sha256!=branch.seed_evidence_sha256


@pytest.mark.parametrize('fault',('floor','reference','height','reader','zone','log_epoch','partial',
                                 'source','static','policy','model','payload',
                                 'height_value','height_raw','height_flag'))
def test_mutated_history_or_source_scope_is_permanently_discarded(checkpoint,fault,tmp_path):
    f=checkpoint;c=f.checkpoint
    if fault=='floor':c._chain.seed_evidence_sha256='f'*64
    elif fault=='reference':c._reference=object()
    elif fault=='height':c._height_bytes=b'{}'
    elif fault=='height_value':object.__setattr__(c._calibration,'raw_z_minus_source_z',9.)
    elif fault=='height_raw':object.__setattr__(c._calibration.evidence.first.raw_fix,'log_epoch',999)
    elif fault=='height_flag':object.__setattr__(c._calibration.evidence.first,'geometry_verified',False)
    elif fault=='reader':c._reader=object()
    elif fault=='zone':f.reader.zone_generation+=1
    elif fault=='log_epoch':f.reader.tail.epoch+=1
    elif fault=='partial':f.reader.tail.partial='partial'
    elif fault=='source':c._terrain.sources=tuple(list(c._terrain.sources))
    elif fault=='static':c._static.inventory_sha256='f'*64
    elif fault=='policy':c._classifier.inventory_sha256='f'*64
    elif fault=='model':(tmp_path/'EQGraphics.dll').write_bytes(b'changed')
    else:c._payload=b'{}'
    with pytest.raises(ValueError):c.check()
    assert not c.valid and c._chain is None
    with pytest.raises(ValueError):c.fork()


@pytest.mark.parametrize('stop',('F8','F9','F11','quit','physical_input','floor_replaced'))
def test_monitor_discard_releases_its_exact_checkpoint(checkpoint,stop):
    c=checkpoint.checkpoint;m,backend,device,clock=monitor_fixture()
    m=CampInputContinuity(m.observer,topology=m.topology,basis=m.basis,
        binding=m.binding,clock=m.clock,floor=c)
    m.check(m.binding)
    if stop=='physical_input':
        device.pending=[(1,106,1),(1,106,0)]
        with pytest.raises(ValueError):m.check(m.binding)
    elif stop=='floor_replaced':
        m.floor=None
        with pytest.raises(ValueError):m.check(m.binding)
    else:m.close(stop)
    assert not c.valid and c._chain is None and not m.valid
    with pytest.raises(ValueError):c.fork()


@pytest.mark.parametrize('fault',('cancel','expired','pending','wrong_reference'))
def test_capture_requires_exact_current_idle_stopped_source_ledger(f,fault):
    f.real=False;f.now=max(f.observer.last_at,f.second.raw_fix.received_monotonic+.01)
    if fault=='cancel':f.ledger.cancel('F9')
    elif fault=='expired':f.now+=.51
    elif fault=='pending':f.ledger._pending=object()
    else:f.ledger.reference=f.first
    with pytest.raises((ValueError,RuntimeError)):CampFloorCheckpoint(f.ledger)


def test_reentrant_model_check_cannot_return_after_discard(checkpoint,monkeypatch):
    from eql_automation.installed_region_model import InstalledRegionModel
    c=checkpoint.checkpoint;original=InstalledRegionModel.check_policy
    def discard(model,policy):
        original(model,policy);c.invalidate('F9 during source check')
    monkeypatch.setattr(InstalledRegionModel,'check_policy',discard)
    with pytest.raises(ValueError):c.check()
    assert not c.valid and c._chain is None


def test_final_capture_clock_change_does_not_escape_source_scope(f,monkeypatch):
    from eql_automation.installed_region_model import InstalledRegionModel
    f.real=False;f.now=max(f.observer.last_at,f.second.raw_fix.received_monotonic+.01)
    original=InstalledRegionModel.check_policy;calls=[]
    def arm_clock_change(model,policy):
        original(model,policy);calls.append(1)
        if len(calls)==2:f.clock_hook=lambda:setattr(f,'generation',f.generation+1)
    monkeypatch.setattr(InstalledRegionModel,'check_policy',arm_clock_change)
    with pytest.raises(ValueError):CampFloorCheckpoint(f.ledger)


def test_final_monitor_binding_check_performs_no_full_floor_callback(checkpoint,monkeypatch):
    c=checkpoint.checkpoint;m,backend,device,clock=monitor_fixture()
    m=CampInputContinuity(m.observer,topology=m.topology,basis=m.basis,
        binding=m.binding,clock=m.clock,floor=c)
    calls=[];original=c.check
    def delayed():
        original();calls.append(1);clock[0]+=.6
    monkeypatch.setattr(c,'check',delayed)
    m.check_binding(m.binding);assert not calls
    m.check(m.binding);assert len(calls)==1 and m.valid
    assert m.last_observed_at==clock[0]
