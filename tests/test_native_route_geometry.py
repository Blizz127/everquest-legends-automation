"""Native region policy over actual geometry checks and pipe-only movement."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from eql_automation.bsp_volume import BspVolumeView
from eql_automation.fixed_route_follower import RouteHalt
from eql_automation.native_region_policy import NativeZeroRegionTrialPolicy
from eql_automation.route_geometry import RouteGeometryPreparer
from eql_automation.supervised_route import SupervisedRoutePolicy
from eql_automation.uinput_watchdog import PulseError
from test_client_classification import view, leaf
from test_installed_region_model import files
from test_native_region_policy import MISSING
from test_route_floor_commit import legacy
from test_route_geometry import build, stage
from test_route_step_sender import after_down
from test_supervised_route import setup as supervised, pipe


def native(f, *, nodes=MISSING, enabled=True):
    r, old = f.runner, f.prepare
    r.route=replace(r.route,zone='crushbone')
    r.height_calibration=replace(r.height_calibration,zone_short_name='crushbone',zone_id=58)
    r.geometry_evidence=replace(r.geometry_evidence,zone_short_name='crushbone')
    r.binding=(58,*r.binding[1:])
    raw=replace(f.reference.raw_fix,zone_id=58)
    f.reference=replace(f.reference,raw_fix=raw,zone_short_name='crushbone',
        height_calibration=r.height_calibration,
        source_floor=replace(f.reference.source_floor,raw_fix=raw),
        mesh_projection=replace(f.reference.mesh_projection,raw_fix=raw))
    bsp=BspVolumeView(SimpleNamespace(nodes=MISSING,labels_by_region={}),
                      region_count=3,wld_sha256=old.source.wld_sha256)
    classifier=view(nodes,wld_pin=old.source.wld_sha256)
    policy=NativeZeroRegionTrialPolicy(r.route.mesh_sha256,old.source.archive_sha256,
        old.source.wld_sha256,old.static_inventory_sha256,bsp.inventory_sha256,
        classifier.inventory_sha256,classifier) if enabled else None
    f.prepare=RouteGeometryPreparer(f.ledger,ground=old.ground,source=old.source,
        static=old.static,bsp=bsp,bounds=old.bounds,static_inventory_sha256=old.static_inventory_sha256,
        vertical_window=old.vertical_window,maximum_source_z_difference=old.maximum_source_z_difference,
        region_policy=policy)
    return f


def fixture(legacy, **kwargs):
    f=native(build(legacy),**kwargs);f.scene=SimpleNamespace(reference_fix=f.reference)
    return f


def owner(tmp_path,legacy,monkeypatch, *, real=False):
    model=files(tmp_path,monkeypatch)
    f=native(supervised(tmp_path,legacy,real=real));old=f.policy
    f.policy=SupervisedRoutePolicy(f.prepare,declaration=old.declaration,gate=old.gate,
        owner_input=old.owner_input,log_veto=old.log_veto,expected_log_path=old.log_path,
        expected_window=old.window,topology_generation=old.topology,check_current=old.check_current,
        installed_region_model=model)
    f.options.update(prepare_step=f.prepare,authorize_step=f.policy.authorize,
        still_authorized=f.policy.still_authorized,supervised_policy=f.policy)
    return f


def test_default_missing_child_stays_refused(legacy):
    f=fixture(legacy,enabled=False)
    with pytest.raises(ValueError,match='missing_bsp_child'):stage(f)


@pytest.mark.parametrize('heading',[90.,0.])
def test_native_zero_binds_forward_and_pivot_to_exact_cell_without_rewriting_bsp(legacy,heading):
    f=fixture(legacy);f.runner.pose.heading=heading
    f.prepare.bounds=replace(f.prepare.bounds,maximum_requested_hold=.05)
    ticket=stage(f);r=f.prepare.record_for(ticket)
    assert not r.bsp.candidate and r.bsp.reason=='missing_bsp_child'
    assert r.terrain.candidate and r.static.candidate and f.prepare.regions_allowed(r)
    assert r.native_region_evidence.record()['native_body']['geometry_sha256']==ticket.preparation.geometry_sha256
    assert not r.input_authorized and f.ledger.chain is f.chain


@pytest.mark.parametrize('nodes',[(leaf(2),),(leaf(3),),((0.,0.,0.,0.,0,1,1),)])
def test_nonzero_or_unresolved_native_cell_refuses_before_staging(legacy,nodes):
    f=fixture(legacy,nodes=nodes)
    with pytest.raises(ValueError):stage(f)
    assert f.ledger._pending is None and f.runner.steps==0


@pytest.mark.parametrize('change',['policy','classifier','seal','record','inventory','mode'])
def test_changed_issued_record_or_region_context_refuses(legacy,change):
    f=fixture(legacy);ticket=stage(f);p=f.prepare;r=p.record_for(ticket)
    if change=='policy':p.region_policy=replace(p.region_policy)
    elif change=='classifier':object.__setattr__(p.region_policy,'classifier',view(MISSING,wld_pin=p.source.wld_sha256))
    elif change=='seal':object.__setattr__(r.native_region_evidence,'sha256','f'*64)
    elif change=='record':p._record=replace(r)
    elif change=='inventory':p.region_policy.classifier.inventory_sha256='f'*64
    else:f.state['mode']='full_auto'
    with pytest.raises((ValueError,RouteHalt)):p.record_for(ticket)


def test_replaced_cached_evidence_cannot_be_staged_even_with_identical_payload(legacy):
    f=fixture(legacy);p=f.prepare;p.precompute(f.scene)
    trials=dict(p._cache[4]);value=list(trials['forward']);value[-1]=replace(value[-1]);trials['forward']=tuple(value)
    p._cache=(*p._cache[:4],trials)
    with pytest.raises(ValueError):p(f.runner.propose(f.clock()),f.scene)
    assert f.ledger._pending is None


def test_slow_native_classification_does_not_renew_reference(legacy,monkeypatch):
    f=fixture(legacy);original=NativeZeroRegionTrialPolicy.evaluate
    def slow(self,*args):
        result=original(self,*args);f.state['now']+=.51;return result
    monkeypatch.setattr(NativeZeroRegionTrialPolicy,'evaluate',slow)
    with pytest.raises(ValueError,match='expired'):stage(f)


def test_native_supervised_pipe_releases_before_committing_floor(tmp_path,legacy,monkeypatch):
    f=owner(tmp_path,legacy,monkeypatch,real=True);pipe(f)
    try:
        result=f.run()
        assert result.authorization_scope=='owner_supervised_conditional_trial'
        assert not result.real_client_accepted and not f.sender.held
        assert f.runner.steps==1 and f.ledger.chain is not f.chain
    finally:f.close()
    assert (1,103,1) in f.events and f.events[-2:]==[(1,103,0),(0,0,0)]


def test_cancel_during_native_pipe_down_releases_without_commit(tmp_path,legacy,monkeypatch):
    f=owner(tmp_path,legacy,monkeypatch,real=True);pipe(f)
    after_down(monkeypatch,lambda:f.policy.cancel('Owner stop'))
    try:
        with pytest.raises((ValueError,RouteHalt,PulseError)):f.run()
        assert f.runner.steps==0 and f.ledger.chain is f.chain and not f.sender.held
    finally:f.close()
    assert (1,103,1) in f.events and f.events[-2:]==[(1,103,0),(0,0,0)]


@pytest.mark.parametrize('change',['assist','full_auto','strict','binary','record_after_callback'])
def test_native_sender_refuses_wrong_scope_or_changed_binary_before_down(tmp_path,legacy,monkeypatch,change):
    f=owner(tmp_path,legacy,monkeypatch);pipe(f)
    if change in ('assist','full_auto'):f.state['mode']=change
    elif change=='strict':f.options['supervised_policy']=None
    elif change=='binary':(tmp_path/'EQGraphics.dll').write_bytes(b'changed')
    else:
        original=f.policy.validate_scene
        def changed(*args):
            original(*args)
            if f.prepare._record is not None:f.prepare._record=replace(f.prepare._record)
        f.policy.validate_scene=changed
    try:
        with pytest.raises((ValueError,RouteHalt)):f.run()
        assert f.runner.steps==0 and f.ledger.chain is f.chain
    finally:f.close()
    assert not f.events
