"""Real observer/ledger/planner; synthetic client positions and no input."""
from copy import deepcopy
from dataclasses import replace
import threading
import time

import pytest

from eql_automation.fixed_route_follower import RouteHalt
from eql_automation.route_floor_commit import _chain_snapshot
from eql_automation.source_stair_preflight import SourceStairHint,SourceStairPreflight
from eql_automation import source_stair_preflight as runtime
from test_source_motion import f
from test_route_floor_commit import legacy


pytestmark=pytest.mark.parametrize('f',['stair_preflight'],indirect=True)


def preflight(f):
    f.real=False;f.now=time.monotonic()
    hint=SourceStairHint((4.,2.),(4.,10.),f.stair_groups,1.2)
    return SourceStairPreflight(f.ledger,policy=f.policy,hint=hint,
        released_at=f.first.raw_fix.received_monotonic-.2)


def replies(f,pre):
    first=pre.observe_reply(f.position())
    f.now+=.4
    second=pre.observe_reply(f.position())
    return first,second


def test_slow_real_preflight_refreshes_only_exact_stopped_reference(f,monkeypatch):
    l=f.ledger;chain=l.chain;floor=_chain_snapshot(chain);pose=deepcopy(vars(l.pose))
    original=l.reference;cal=l.observer.calibration
    scope=(f.policy.started,f.policy.origin,f.policy.reserved_hold)
    planner=runtime.plan_stair_flight
    def slow(*args,**kwargs):
        f.now+=.8
        return planner(*args,**kwargs)
    monkeypatch.setattr(runtime,'plan_stair_flight',slow)
    pre=preflight(f);cache=pre.prepare()
    assert f.now-original.observed_at>.5
    with pytest.raises(ValueError):l.validate_reference()
    record=cache.record()
    assert record['checked_radius']>l.bounds.body_radius
    assert record['stair_plan']['flight']['phase_count']==9
    assert not record['full_motion_coverage_checked'] and not record['input_authorized']
    assert not record['source_execution_wired'] and not record['real_client_accepted']
    pair=replies(f,pre);start=pre.bind_start(*pair)
    assert l.reference is original and l.phase=='stair_preflight'
    assert pre.consume_start(start) is cache
    assert l.phase=='ready' and l._busy is None and l.reference is pair[1]
    assert l.chain is chain and _chain_snapshot(chain)==floor and vars(l.pose)==pose
    assert l.steps==l.serial==0 and l.observer.calibration is cal
    assert (f.policy.started,f.policy.origin,f.policy.reserved_hold)==scope
    assert l.validate_reference()==f.now and not f.drain_events()
    with pytest.raises(RuntimeError):pre.consume_start(start)
    assert l.phase=='ready'


@pytest.mark.parametrize('position',[dict(x=4.01),dict(y=2.01),dict(z=2.71)])
def test_small_changed_printed_departure_is_not_silently_replanned(f,position):
    pre=preflight(f);pre.prepare();original=f.ledger.reference
    with pytest.raises((RuntimeError,ValueError),match='departure changed'):
        pre.observe_reply(f.position(**position))
    assert f.ledger.phase=='stopped' and f.ledger.reference is original
    assert not f.drain_events()


@pytest.mark.parametrize('change',['query','storage','pose','bounds','owner','generation','input','focus','scope'])
def test_binding_or_physical_change_during_preflight_stops_without_input(f,monkeypatch,change):
    pre=preflight(f);planner=runtime.plan_stair_flight
    def changed(*args,**kwargs):
        if change=='query':f.ledger.terrain.source_faces_for_footprint=lambda _:()
        elif change=='storage':f.ledger.terrain.sources=tuple(list(f.ledger.terrain.sources))
        elif change=='pose':f.ledger.pose.heading+=1.
        elif change=='bounds':f.ledger.bounds=replace(f.ledger.bounds,body_radius=.2)
        elif change=='owner':f.owner=('changed',)
        elif change=='generation':f.generation+=1
        elif change=='input':f.active=True
        elif change=='focus':f.focus=False
        else:f.policy.started+=1.
        return planner(*args,**kwargs)
    monkeypatch.setattr(runtime,'plan_stair_flight',changed)
    with pytest.raises((RuntimeError,ValueError)):pre.prepare()
    assert f.ledger.phase=='stopped' and pre.cache is None and not f.drain_events()


def test_cancel_is_not_blocked_by_geometry_and_no_late_cache_is_published(f,monkeypatch):
    pre=preflight(f);planner=runtime.plan_stair_flight;done=threading.Event()
    def cancelled(*args,**kwargs):
        def stop():pre.cancel('F9 during planning');done.set()
        thread=threading.Thread(target=stop);thread.start()
        assert done.wait(.5);thread.join()
        return planner(*args,**kwargs)
    monkeypatch.setattr(runtime,'plan_stair_flight',cancelled)
    with pytest.raises(RuntimeError):pre.prepare()
    assert pre.cache is None and f.ledger.phase=='stopped' and not f.drain_events()


def test_preflight_does_not_extend_original_scope(f,monkeypatch):
    pre=preflight(f);planner=runtime.plan_stair_flight
    def expired(*args,**kwargs):
        f.now=f.policy.started+f.policy.declaration.maximum_seconds+.01
        return planner(*args,**kwargs)
    monkeypatch.setattr(runtime,'plan_stair_flight',expired)
    with pytest.raises((RuntimeError,ValueError)):pre.prepare()
    assert pre.cache is None and f.ledger.phase=='stopped' and not f.drain_events()


@pytest.mark.parametrize('change',['pair_clone','start_clone','stale','cache','old_fix','cancel_final',
                                  'collection_boundary','release_boundary'])
def test_start_requires_issued_pair_sealed_cache_and_current_lease(f,change):
    pre=preflight(f);pre.prepare();pair=replies(f,pre);original=f.ledger.reference
    if change=='pair_clone':
        with pytest.raises(RuntimeError):pre.bind_start(pair[0],replace(pair[1]))
    else:
        start=pre.bind_start(*pair)
        if change=='start_clone':start=replace(start)
        elif change=='stale':f.now+=.501
        elif change=='cache':object.__setattr__(pre.cache,'payload',b'{}')
        elif change=='old_fix':object.__setattr__(original,'observed_at',original.observed_at+.01)
        elif change=='collection_boundary':pre.minimum_seq-=1
        elif change=='release_boundary':pre._released_at-=1.
        else:f.clock_hook=lambda:pre.cancel('F9 at final check')
        with pytest.raises((RuntimeError,ValueError)):pre.consume_start(start)
    assert f.ledger.phase=='stopped' and f.ledger.reference is original and not f.drain_events()


def test_consumed_preflight_cannot_cancel_successor(f):
    pre=preflight(f);pre.prepare();start=pre.bind_start(*replies(f,pre))
    successor=object()
    with f.ledger.lock:
        pre.consume_start(start)
        f.ledger.phase,f.ledger._busy='transfer',successor
    pre.cancel('late ancestor cleanup')
    assert f.ledger.phase=='transfer' and f.ledger._busy is successor and not f.drain_events()


def test_idle_observation_cannot_be_used_as_a_movement_scene(f):
    pre=preflight(f);f.now+=.8
    idle=f.policy.observe_preflight(pre._lease)
    assert idle.input_authorized is False
    with pytest.raises(RouteHalt):f.policy.validate_scene(idle)
    assert f.policy.reserved_hold==0 and not f.drain_events()


def test_reply_arriving_during_geometry_cannot_be_reused_after_preparation(f,monkeypatch):
    pre=preflight(f);planner=runtime.plan_stair_flight;early=[]
    def received(*args,**kwargs):
        early.append(f.position())
        return planner(*args,**kwargs)
    monkeypatch.setattr(runtime,'plan_stair_flight',received)
    pre.prepare()
    with pytest.raises(RuntimeError,match='completed stair preflight'):pre.observe_reply(early[0])
    assert f.ledger.phase=='stopped' and not f.drain_events()


def test_original_height_calibration_expiry_is_not_renewed(f,monkeypatch):
    pre=preflight(f);planner=runtime.plan_stair_flight
    def expired(*args,**kwargs):
        f.now=f.observer.calibration.valid_until_monotonic+.01
        return planner(*args,**kwargs)
    monkeypatch.setattr(runtime,'plan_stair_flight',expired)
    with pytest.raises((RuntimeError,ValueError)):pre.prepare()
    assert pre.cache is None and f.ledger.phase=='stopped' and not f.drain_events()


@pytest.mark.parametrize('stage',['bind','consume'])
@pytest.mark.parametrize('change',['focus','input'])
def test_final_pair_validation_cannot_hide_physical_change(f,monkeypatch,stage,change):
    pre=preflight(f);pre.prepare();pair=replies(f,pre)
    start=pre.bind_start(*pair) if stage=='consume' else None
    validate=f.observer.validate
    def changed(fix,*args,**kwargs):
        result=validate(fix,*args,**kwargs)
        if fix is pair[1]:
            if change=='focus':f.focus=False
            else:f.active=True
        return result
    monkeypatch.setattr(f.observer,'validate',changed)
    with pytest.raises(RuntimeError):
        if stage=='bind':pre.bind_start(*pair)
        else:pre.consume_start(start)
    assert f.ledger.phase=='stopped' and not f.drain_events()


def test_freshness_is_measured_from_reply_receipt_not_later_observation(f,monkeypatch):
    pre=preflight(f);pre.prepare();first=pre.observe_reply(f.position())
    f.now+=.4;raw=f.position();f.now+=.2
    second=pre.observe_reply(raw)
    assert second.observed_at>raw.received_monotonic
    start=pre.bind_start(first,second)
    assert start.expires_at==raw.received_monotonic+.5
    f.now=raw.received_monotonic+.49
    check=pre.check;calls=[]
    def late():
        calls.append(True)
        if len(calls)==2:f.now+=.02
        return check()
    monkeypatch.setattr(pre,'check',late)
    with pytest.raises(RuntimeError,match='expired during final'):pre.consume_start(start)
    assert f.ledger.phase=='stopped' and not f.drain_events()
