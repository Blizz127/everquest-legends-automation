"""Real retained engine/watchdog pipe; synthetic focus, inputs and game log."""
from dataclasses import replace
import time

import pytest

from eql_automation.g2_safety_provider import GameWindowIdentity
from eql_automation.motion_calibration import Probe
from eql_automation.scene_log_veto import SceneLogVeto
from eql_automation.supervised_camp_probe import (
    SupervisedCampProbeDeclaration,SupervisedCampProbeScope)
from test_owner_camp_probe import configure,finish
from test_owner_camp_position import camp
from test_camp_floor_checkpoint import checkpoint
from test_source_motion import f
from test_route_floor_commit import legacy
from test_motion_collection import retained
from test_owner_journey_runtime import h
from test_route_step_sender import after_down
from test_owner_camp_standard_route import standard_execution,finish_standard


def policy_factory(h,p,bounds,*,maximum_hold=None):
    e=h.engine
    veto=p.probe_log_veto  # Retained from before initial position collection.
    h.supervised_veto=veto;h.supervised_scope=None
    def create(tx):
        if h.supervised_scope is None:
            r=p.runtime
            d=SupervisedCampProbeDeclaration('synthetic-owner-continuation',bounds.record_id,True,
                len(r.probes)*bounds.maximum_actual_hold if maximum_hold is None else maximum_hold)
            h.supervised_scope=SupervisedCampProbeScope(r,declaration=d,monitor=p.monitor,
                gate=e.gate,expected_window=GameWindowIdentity(*p.window),log_veto=veto,
                check_current=lambda:e._camp_position_current(p),started_at=p.probe_started,
                expires_at=min(p.probe_started+p.probe_plan.maximum_seconds,r.started+r.maximum_seconds))
        return h.supervised_scope.policy(tx)
    return create


def configure_supervised(h,monkeypatch,*,two=False,maximum_hold=None):
    probes=(Probe('forward',103,.02),Probe('right',106,.15)) if two else (Probe('forward',103,.02),)
    configure(h,monkeypatch,probes=probes);e=h.engine;base=e._camp_probe_plan
    def plan(p):
        original=base(p)
        bounds=replace(original.bounds,maximum_requested_hold=.15,maximum_actual_hold=.18)
        return replace(original,bounds=bounds,policy_factory=policy_factory(h,p,bounds,maximum_hold=maximum_hold))
    e._camp_probe_plan=plan


def until_pulse(h,*,index=0):
    deadline=time.monotonic()+15.
    while time.monotonic()<deadline:
        p=h.engine.camp_position
        if p is None:pytest.fail('\n'.join(h.notices))
        r=p.runtime
        if r is not None and r.phase=='pulse' and r.index==index:
            h.drain();return p,r,r.policy
        h.tick();h.drain();time.sleep(.01)
    pytest.fail('Probe never reached ready phase: '+'\n'.join(h.notices))


@pytest.fixture
def ready(camp,monkeypatch):
    h=camp;configure_supervised(h,monkeypatch);h.recovered()
    p,r,policy=until_pulse(h)
    return h,p,r,policy


def no_movement(h):
    h.drain()
    assert not [(kind,key,value) for kind,key,value in h.events if kind==1 and value==1 and key in (103,105,106)]


@pytest.mark.parametrize('fault',('foreign_veto','generation'))
def test_veto_must_belong_to_retained_owner_generation(ready,fault):
    h,p,r,policy=ready;s=h.supervised_scope
    foreign=SceneLogVeto(p.reader.tail.path,expected_character=p.reader.expected_character,
        expected_server=p.reader.expected_server,cancel_generation=p.generation+1,clock=time.monotonic)
    if fault=='generation':
        foreign=s.log_veto;foreign.cancel_generation+=1
    r.phase='collect_start'
    with pytest.raises(ValueError):
        SupervisedCampProbeScope(r,declaration=s.declaration,monitor=p.monitor,gate=h.engine.gate,
            expected_window=GameWindowIdentity(*p.window),log_veto=foreign,
            check_current=s.current,started_at=s.started_at,expires_at=s.expires_at)
    no_movement(h)


def test_shared_policy_completes_turn_after_down_permission_expires(camp,monkeypatch):
    h=camp;configure_supervised(h,monkeypatch,two=True);h.recovered();p=h.engine.camp_position
    finish(h);s=h.supervised_scope
    record=h.engine.camp_position_last_result
    assert record['outcome']=='probe_complete','\n'.join(h.notices)
    assert record['probe']['completed_probes']==2 and len(s._policies)==2
    assert s.reserved_hold==pytest.approx(.36)
    second=s._policies[1];receipt=p.runtime.transactions[1].seal.receipt
    assert receipt.requested_seconds==.15
    assert receipt.up_started_at>second._authorization.expires_at
    assert s.log_veto is h.supervised_veto and s.owner_input is p.monitor.observer
    assert not h.engine.sender.held and h.engine.live_zone_tracker.lease is None
    snapshot=s.snapshot()
    assert not snapshot['independent_scene_verified'] and not snapshot['motion_bounds_verified']
    assert not snapshot['real_client_accepted'] and not h.commands


@pytest.mark.parametrize('fault',('activity','coverage','topology','stale','second_sample'))
def test_current_physical_observation_refuses_down(ready,monkeypatch,fault):
    h,p,r,policy=ready;s=h.supervised_scope;sample=s.owner_input.sample;calls=[]
    def observed():
        value=sample();calls.append(1)
        if fault=='activity':return replace(value,activity=True)
        if fault=='coverage':return replace(value,coverage_complete=False)
        if fault=='topology':return replace(value,topology_generation=value.topology_generation+1)
        if fault=='stale':return replace(value,started_at=value.started_at-.2)
        if len(calls)>1:return replace(value,activity=True)
        return value
    monkeypatch.setattr(s.owner_input,'sample',observed)
    with pytest.raises((ValueError,RuntimeError)):policy.check()
    assert not s.valid
    no_movement(h)


@pytest.mark.parametrize('fault',('focus','generation','deadline','bounds','monitor','transaction','veto_tail'))
def test_scope_cannot_change_between_observation_and_admission(ready,fault):
    h,p,r,policy=ready;s=h.supervised_scope
    if fault=='focus':h.engine.gate.focused_window=lambda:None
    elif fault=='generation':h.engine.cancel_generation+=1
    elif fault=='deadline':s.expires_at+=1.
    elif fault=='bounds':object.__setattr__(s.root.bounds,'maximum_actual_hold',.19)
    elif fault=='monitor':s.monitor=object()
    elif fault=='transaction':r.transaction=object()
    else:
        replacement=SceneLogVeto(p.reader.tail.path,expected_character=p.reader.expected_character,
            expected_server=p.reader.expected_server,cancel_generation=p.generation,clock=time.monotonic)
        s.log_veto.tail=replacement.tail
    with pytest.raises((ValueError,RuntimeError,AttributeError)):policy.check()
    assert not s.valid
    no_movement(h)


@pytest.mark.parametrize('fault',('duplicate','foreign','wrong_duration','budget'))
def test_ticket_and_aggregate_reservation_are_single_use(ready,fault):
    h,p,r,policy=ready;s=h.supervised_scope;t=r.transaction
    policy.check()
    if fault=='budget':
        # Build a new explicit small-budget declaration before constructing a
        # replacement scope, not a mutation of an already-bound declaration.
        d=replace(s.declaration,maximum_total_hold=.17)
        r.phase='collect_start'
        smaller=SupervisedCampProbeScope(r,declaration=d,monitor=p.monitor,gate=h.engine.gate,
            expected_window=GameWindowIdentity(*p.window),log_veto=s.log_veto,
            check_current=s.current,started_at=s.started_at,expires_at=s.expires_at)
        policy=smaller.policy(t);r.policy=policy;r.phase='pulse';s=smaller;policy.check()
    ticket=t.stage(r.start,movement_key=103,requested_seconds=.01 if fault=='wrong_duration' else .02)
    if fault in ('budget','wrong_duration'):
        with pytest.raises(ValueError):policy.authorize(ticket)
        assert s.reserved_hold==0.
    else:
        auth=policy.authorize(ticket);reserved=s.reserved_hold
        with pytest.raises(ValueError):
            if fault=='duplicate':policy.authorize(ticket)
            else:policy.still_authorized(replace(auth))
        assert s.reserved_hold==reserved==.18
    assert not s.valid
    no_movement(h)


def test_hazard_between_probes_stays_latched(camp,monkeypatch):
    h=camp;configure_supervised(h,monkeypatch,two=True);h.recovered()
    p,r,policy=until_pulse(h,index=1);s=h.supervised_scope
    with p.reader.tail.path.open('a') as out:
        out.write(h.engine.camp_wall().strftime('[%a %b %d %H:%M:%S %Y] ')+
            'You have taken 1 damage from Poison.\n')
    assert s.log_veto.poll().reason=='incoming_attack'
    original=s._policies[0]
    assert policy.scope is original.scope and policy.scope.log_veto is h.supervised_veto
    with pytest.raises(ValueError):policy.check()
    h.tick();h.drain()
    assert not s.valid and s.log_veto.poll().reason=='incoming_attack'
    assert (1,106,1) not in h.events and not h.engine.sender.held


def test_hazard_during_initial_position_collection_cannot_be_skipped(camp,monkeypatch):
    h=camp;configure_supervised(h,monkeypatch);h.recovered();p=h.engine.camp_position
    original=p.probe_log_veto
    with p.reader.tail.path.open('a') as out:
        out.write(h.engine.camp_wall().strftime('[%a %b %d %H:%M:%S %Y] ')+
            'You have taken 1 damage from Poison.\n')
    finish(h)
    assert h.engine.camp_position_last_result['outcome']=='stopped'
    assert h.supervised_scope is not None,'\n'.join(h.notices)
    assert h.supervised_scope.log_veto is original and original.poll().reason=='incoming_attack'
    no_movement(h)


@pytest.mark.parametrize('fault',('veto','tail'))
def test_replacing_recovery_veto_stops_before_any_probe(camp,monkeypatch,fault):
    h=camp;configure_supervised(h,monkeypatch);h.recovered();p=h.engine.camp_position
    replacement=SceneLogVeto(p.reader.tail.path,expected_character=p.reader.expected_character,
        expected_server=p.reader.expected_server,cancel_generation=p.generation,clock=time.monotonic)
    if fault=='veto':p.probe_log_veto=replacement
    else:p.probe_log_veto.tail=replacement.tail
    finish(h)
    assert h.engine.camp_position_last_result['outcome']=='stopped'
    no_movement(h)


def test_activity_during_long_turn_releases_before_scope_cleanup(camp,monkeypatch):
    h=camp;configure_supervised(h,monkeypatch,two=True);h.recovered();fired=[]
    def disturb():
        p=h.engine.camp_position
        if p is not None and p.runtime is not None and p.runtime.input_kind=='movement' and p.runtime.index==1:
            fired.append(True);sample=p.monitor.observer.sample
            monkeypatch.setattr(p.monitor.observer,'sample',lambda:replace(sample(),activity=True))
    after_down(monkeypatch,disturb)
    finish(h)
    assert fired==[True] and h.engine.camp_position_last_result['outcome']=='stopped'
    down=h.events.index((1,106,1));assert (1,106,0) in h.events[down+1:]
    assert not h.engine.sender.held and h.engine.live_zone_tracker.lease is None
    assert not h.commands


@pytest.mark.parametrize('f',['compact_long'],indirect=True)
def test_seven_supervised_probes_keep_veto_and_observer_through_source_route(camp,monkeypatch,legacy):
    h=camp
    def veto(p):
        h.supervised_scope._check()
        return h.supervised_veto
    standard_execution(h,monkeypatch,legacy,policy_provider=policy_factory,source_veto_provider=veto)
    p=finish_standard(h);s=h.supervised_scope
    assert len(s._policies)==7 and s.reserved_hold==pytest.approx(7*.18)
    assert p.route_runtime.policy.log_veto is s.log_veto is h.supervised_veto
    assert p.route_runtime.policy.owner_input is s.owner_input is p.monitor.observer
    assert s.expires_at==p.probe_started+p.probe_plan.maximum_seconds


@pytest.mark.parametrize('f',['compact_long'],indirect=True)
def test_hazard_after_seven_probes_is_not_rebaselined_by_route(camp,monkeypatch,legacy):
    h=camp
    def veto(p):
        with p.reader.tail.path.open('a') as out:
            out.write(h.engine.camp_wall().strftime('[%a %b %d %H:%M:%S %Y] ')+
                'You have taken 1 damage from Poison.\n')
        return h.supervised_veto
    standard_execution(h,monkeypatch,legacy,policy_provider=policy_factory,source_veto_provider=veto)
    h.recovered();p=h.engine.camp_position;deadline=time.monotonic()+60.
    while h.engine.camp_position is not None and time.monotonic()<deadline:
        h.tick();h.drain();time.sleep(.01)
    assert h.engine.camp_position is None,'\n'.join(h.notices)
    assert h.engine.camp_position_last_result['outcome']=='stopped'
    assert len(h.receipts)==7 and p.route_runtime.ledger.steps==0
    assert p.route_runtime.policy.log_veto is h.supervised_veto
    assert h.supervised_veto.poll().reason=='incoming_attack'
    assert not h.engine.sender.held and h.engine.live_zone_tracker.lease is None and not h.commands
