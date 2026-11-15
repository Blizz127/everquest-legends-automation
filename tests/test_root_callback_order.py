"""Root and final owner callbacks keep sticky cancellation and deadline guards.

The actual budget/owner wrappers use synthetic clocks, windows and requests;
these tests send no input.
"""
from dataclasses import replace
import threading
from types import SimpleNamespace

import pytest

from eql_automation.owner_zone_itinerary import make_zone_itinerary_engine
from eql_automation.zone_itinerary_budget import ZoneItineraryBudget, ZoneItineraryDeclaration
from test_journey_input_budget import bounds, ticket as ordinary_ticket
from test_owner_zone_itinerary import Base, owner, start, synthetic_legs


@pytest.fixture
def root_scope():
    s = SimpleNamespace(now=10., events=[], clock_calls=0, clock_hooks={}, binding_hook=None)

    def clock():
        s.events.append('clock')
        s.clock_calls += 1
        hook = s.clock_hooks.pop(s.clock_calls, None)
        if hook is not None:
            hook()
        return s.now

    def binding():
        s.events.append('binding')
        hook, s.binding_hook = s.binding_hook, None
        if hook is not None:
            hook()
        return (1, 'synthetic-root-owner')

    legs, _ = synthetic_legs({'Butcherblock Mountains':68,
                              'The Greater Faydark':54, 'Clan Crushbone':58})
    declaration = ZoneItineraryDeclaration('callback-order-root', legs, 120., 12, 2.4, 100.)
    s.root = ZoneItineraryBudget(declaration, clock=clock, stop_lock=threading.RLock(),
        owner_binding=(1, 'synthetic-root-owner'), binding_reader=binding)
    s.now += .01
    s.events.clear()
    s.clock_calls = 0
    return s


def test_root_reads_one_binding_between_its_clock_samples(root_scope):
    s = root_scope
    assert s.root.check() == s.now
    assert s.events == ['clock', 'binding', 'clock']
    assert s.root.last_at == s.root._last_at == s.now
    assert s.root.valid and not s.root._checking


@pytest.mark.parametrize('clock_call', (1, 2))
@pytest.mark.parametrize('fault', (
    'cancel', 'stage', 'leg', 'deadline', 'balance', 'last_at', 'binding_callback', 'clock_callback',
))
def test_clock_root_mutation_cancels_before_publishing(root_scope, clock_call, fault):
    s = root_scope
    root = s.root
    previous = root._last_at

    def change():
        if fault == 'cancel':
            root.cancel('F9 during root clock')
        elif fault == 'stage':
            root.stage = replace(root.stage, epoch=root.stage.epoch + 1)
        elif fault == 'leg':
            object.__setattr__(root.leg, 'source_name', 'Changed during clock')
        elif fault == 'deadline':
            root.expires_at += 1.
        elif fault == 'balance':
            root._hold += .01
        elif fault == 'last_at':
            root.last_at -= 1.
        elif fault == 'binding_callback':
            root.binding_reader = lambda:root.owner_binding
        else:
            root.clock = lambda:s.now

    s.clock_hooks[clock_call] = change
    with pytest.raises(ValueError):
        root.check()
    assert not root.valid and not root._checking
    assert root._last_at == previous
    assert root._pulses == 0 and not root._reservations
    with pytest.raises(ValueError):
        root.check()


@pytest.mark.parametrize('boundary', ('first_clock', 'binding', 'second_clock'))
@pytest.mark.parametrize('nested', ('check', 'reserve', 'advance'))
def test_caught_reentry_from_callbacks_still_cancels_root(root_scope, boundary, nested):
    s = root_scope
    root = s.root
    stage, previous = root.stage, root.last_at
    caught = []

    def reenter():
        try:
            if nested == 'check':
                root.check()
            elif nested == 'reserve':
                root.reserve(ordinary_ticket(), bounds=bounds())
            else:
                root.advance(root.stage, 'crossing', zone_id=68)
        except ValueError as error:
            caught.append(str(error))

    if boundary == 'binding':
        s.binding_hook = reenter
    else:
        s.clock_hooks[1 if boundary == 'first_clock' else 2] = reenter
    with pytest.raises(ValueError, match='reentered'):
        root.check()
    assert len(caught) == 1 and 'reentered' in caught[0]
    assert not root.valid and not root._checking and not root._mutating
    assert root.stage is stage and root.last_at == root._last_at == previous
    assert root._pulses == 0 and not root._reservations


@pytest.fixture
def checked_owner(owner):
    s = owner
    s.events, s.clock_calls, s.clock_hooks = [], 0, {}
    s.window, s.pid, s.ticks = 7, 8, '9'

    def clock():
        s.events.append('clock')
        s.clock_calls += 1
        hook = s.clock_hooks.pop(s.clock_calls, None)
        if hook is not None:
            hook()
        return s.now

    def windows():
        s.events.append('binding')
        return [SimpleNamespace(id=s.window)]

    s.gate.windows = windows
    s.gate.game_session = lambda:dict(pid=s.pid, start_ticks=s.ticks)
    # Pin the callback before constructing either the engine or its root.
    s.engine = make_zone_itinerary_engine(Base,
        itinerary_provider=lambda *_:s.plan, clock=clock)(s)
    start(s)
    s.owner = s.engine.zone_itinerary_owner
    assert s.owner is not None
    s.events.clear()
    s.clock_calls = 0
    s.now += .01
    return s


def test_owner_retains_two_bindings_and_final_read_after_root_clock(checked_owner):
    s = checked_owner
    assert s.owner.check() == s.owner.root.owner_binding
    assert s.events == ['clock', 'binding', 'clock', 'binding']


@pytest.mark.parametrize('fault', ('f8', 'f9', 'window', 'process', 'job'))
def test_final_owner_binding_rejects_revocation_from_second_clock(checked_owner, fault):
    s = checked_owner
    root, stage = s.owner.root, s.owner.root.stage

    def revoke():
        if fault in ('f8', 'f9'):
            # Model the immediate owner token revocation before dispatch of
            # the stop action; root.cancel has not yet supplied another veto.
            s.engine.cancel_generation += 1
            s.engine.cancelled = True
            if fault == 'f9':
                s.engine.stopping = True
        elif fault == 'window':
            s.window += 1
        elif fault == 'process':
            s.ticks = '10'
        else:
            s.engine.jobs.put(('another-job', None))

    s.clock_hooks[2] = revoke
    with pytest.raises(ValueError, match='Itinerary owner'):
        s.owner.check()
    assert s.events == ['clock', 'binding', 'clock', 'binding']
    assert root.stage is stage and root._pulses == 0 and not root._reservations
    assert not s.engine.sender.held


@pytest.mark.parametrize('action', ('f8', 'f9'))
def test_dispatched_stop_from_second_clock_sticks_before_final_owner_read(checked_owner, action):
    s = checked_owner
    root, stage = s.owner.root, s.owner.root.stage

    def stop():
        if action == 'f8':
            s.engine.handle_job('arm', s.engine.cancel_generation)
        else:
            s.engine.stop_action('F9 during second root clock')

    s.clock_hooks[2] = stop
    with pytest.raises(ValueError, match='F8|F9'):
        s.owner.check()
    assert not root.valid and not root._checking
    assert root.stage is stage and root._pulses == 0 and not root._reservations
    assert s.engine.zone_itinerary_owner is None and not s.engine.sender.held
    assert (s.engine._journey_assist is not None) == (action == 'f8')
