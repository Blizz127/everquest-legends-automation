"""Actual source observers retain their final callback and publication checks.

All positions and scope callbacks are synthetic. These tests send no input.
"""
from copy import copy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from eql_automation.source_observer import SourceItineraryObserver
from test_route_floor_commit import legacy
from test_source_motion import f


@pytest.fixture
def observed(f):
    s = SimpleNamespace(now=f.observer.last_at, owner=f.owner, mode=f.mode,
        generation=f.generation, clock_hook=None, events=[], cancelled=None,
        focused=True, window=42, process=(10, 100))

    def clock():
        s.events.append('clock')
        hook, s.clock_hook = s.clock_hook, None
        if hook is not None:
            hook()
        return s.now

    def binding():
        s.events.append('binding')
        if (s.cancelled is not None or not s.focused or s.window != 42
                or s.process != (10, 100)):
            raise ValueError('Synthetic owner/window binding revoked')
        return s.owner

    def mode():
        s.events.append('mode')
        return s.mode

    def generation():
        s.events.append('generation')
        return s.generation

    # Establish the exact callback identities before the constructor pins them.
    s.observer = SourceItineraryObserver(f.plan, f.reader,
        height_calibration=f.observer.calibration, binding_reader=binding,
        mode_reader=mode, generation_reader=generation,
        generation=s.generation, clock=clock)
    s.observer.observe(f.second.raw_fix, checked_chain=f.ledger.chain)
    s.now += .01
    s.events.clear()
    return s


def published_state(observer):
    return observer.last_at, observer.last_seq, observer._issued, tuple(observer._issued)


def assert_unpublished(observer, before):
    assert observer.last_at == before[0]
    assert observer.last_seq == before[1]
    assert observer._issued is before[2]
    assert tuple(observer._issued) == before[3]


def test_check_reads_one_binding_after_clock_before_publishing(observed):
    s = observed
    before = published_state(s.observer)
    assert s.observer.check() == s.now
    assert s.events == ['clock', 'binding', 'mode', 'generation']
    assert s.observer.last_at == s.now > before[0]
    assert s.observer.last_seq == before[1]
    assert tuple(s.observer._issued) == before[3]


@pytest.mark.parametrize('fault', ('f8', 'f9', 'focus', 'window', 'process'))
def test_final_binding_failure_after_clock_cannot_publish(observed, fault):
    s = observed

    def revoke():
        if fault in ('f8', 'f9'):
            s.cancelled = fault
        elif fault == 'focus':
            s.focused = False
        elif fault == 'window':
            s.window += 1
        else:
            s.process = (10, 101)

    s.clock_hook = revoke
    before = published_state(s.observer)
    with pytest.raises(ValueError, match='binding revoked'):
        s.observer.check()
    assert s.events == ['clock', 'binding']
    assert_unpublished(s.observer, before)


@pytest.mark.parametrize('fault', (
    'owner', 'mode', 'generation', 'zone', 'zone_generation', 'zone_name',
    'log_identity', 'log_epoch', 'partial', 'plan', 'itinerary',
    'binding_callback', 'mode_callback', 'generation_callback', 'clock_callback',
    'classifier',
))
def test_final_pins_reject_changes_from_clock(observed, fault):
    s = observed
    observer = s.observer

    def change():
        if fault == 'owner':
            s.owner = ('changed-owner',)
        elif fault == 'mode':
            s.mode = 'assist'
        elif fault == 'generation':
            s.generation += 1
        elif fault == 'zone':
            observer.reader.zone_id += 1
        elif fault == 'zone_generation':
            observer.reader.zone_generation += 1
        elif fault == 'zone_name':
            observer.reader.zone_display_name = 'Changed zone'
        elif fault == 'log_identity':
            device, inode = observer.reader.tail.identity
            observer.reader.tail.identity = (device, inode + 1)
        elif fault == 'log_epoch':
            observer.reader.tail.epoch += 1
        elif fault == 'partial':
            observer.reader.tail.partial = b'[unfinished'
        elif fault == 'plan':
            observer.plan = replace(observer.plan)
        elif fault == 'itinerary':
            observer.itinerary = replace(observer.itinerary)
        elif fault == 'binding_callback':
            observer.binding_reader = lambda:s.owner
        elif fault == 'mode_callback':
            observer.mode_reader = lambda:s.mode
        elif fault == 'generation_callback':
            observer.generation_reader = lambda:s.generation
        elif fault == 'clock_callback':
            observer.clock = lambda:s.now
        else:
            object.__setattr__(observer.policy, 'classifier', copy(observer.policy.classifier))

    s.clock_hook = change
    before = published_state(observer)
    with pytest.raises(ValueError, match='owner, height, mode or log binding changed'):
        observer.check()
    assert s.events[0] == 'clock'
    assert_unpublished(observer, before)


@pytest.mark.parametrize('fault', ('owner', 'generation'))
def test_classifier_callback_revocation_is_checked_after_clock(observed, monkeypatch, fault):
    s = observed
    policy_type = type(s.observer.policy)
    original = policy_type.check_classifier

    def check_classifier(policy):
        original(policy)
        s.events.append('classifier')
        if fault == 'owner':
            s.owner = ('changed-owner',)
        else:
            s.generation += 1

    monkeypatch.setattr(policy_type, 'check_classifier', check_classifier)
    before = published_state(s.observer)
    with pytest.raises(ValueError, match='owner, height, mode or log binding changed'):
        s.observer.check()
    assert s.events == ['classifier', 'clock', 'binding', 'mode', 'generation']
    assert_unpublished(s.observer, before)
