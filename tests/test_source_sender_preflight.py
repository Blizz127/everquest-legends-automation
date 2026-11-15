"""Source geometry may defer scene sampling, but cannot defer structural stops."""
from contextlib import ExitStack
from dataclasses import replace
import os
import time
from types import SimpleNamespace

import pytest

import eql_automation.source_step_sender as bridge
from test_route_floor_commit import legacy
from test_source_motion import f


def at_geometry_boundary(monkeypatch, ledger, boundary, mutate):
    """Keep actual geometry checks, injecting before or after their publication."""
    name = '_geometry' if boundary == 'during' else 'prepare'
    original = getattr(ledger, name)
    calls = []

    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        calls.append(boundary)
        mutate()
        return result

    monkeypatch.setattr(ledger, name, changed)
    return calls


def forbid_watchdog(monkeypatch):
    calls = []

    def unexpected(*args, **kwargs):
        calls.append(True)
        pytest.fail('Invalid sender or reference reached the watchdog')

    monkeypatch.setattr(bridge, 'selected_key_pulse_receipt', unexpected)
    return calls


def assert_stopped_without_input(f, chain):
    assert f.ledger.phase == 'stopped' and f.ledger.steps == 0
    assert f.ledger.chain is chain
    assert f.sender.release_calls == 0 and not f.sender.held
    assert f.sender._eql_route_operation is None
    assert f.drain_events() == ()


@pytest.mark.parametrize('boundary', ('during', 'after'))
@pytest.mark.parametrize('change', ('sender', 'descriptor', 'reference', 'cancel'))
def test_geometry_mutations_stop_before_watchdog(f, monkeypatch, boundary, change):
    chain = f.ledger.chain
    started = forbid_watchdog(monkeypatch)
    with ExitStack() as cleanup:
        if change == 'descriptor':
            # Reuse the same descriptor number for another pipe: identity must
            # be checked even though sender.ui and fileno() are unchanged.
            saved = os.dup(f.wr)
            other_read, other_write = os.pipe()
            for fd in (saved, other_read, other_write):
                cleanup.callback(os.close, fd)
            cleanup.callback(os.dup2, saved, f.wr)

        def mutate():
            if change == 'sender':
                f.sender.ui = SimpleNamespace(fileno=lambda: f.wr)
            elif change == 'descriptor':
                os.dup2(other_write, f.wr)
            elif change == 'reference':
                f.ledger.reference = replace(f.ledger.reference)
            else:
                f.ledger.cancel('Owner OFF during source preparation')

        prepared = at_geometry_boundary(monkeypatch, f.ledger, boundary, mutate)
        expected = ('Owner OFF during source preparation' if change == 'cancel'
                    else 'reference changed|issued source observation')
        with pytest.raises((RuntimeError, ValueError), match=expected):
            f.run()
        assert prepared == [boundary] and started == []
        assert_stopped_without_input(f, chain)


def test_reference_that_expires_after_geometry_stops_before_watchdog(f, monkeypatch):
    chain = f.ledger.chain
    started = forbid_watchdog(monkeypatch)

    def expire():
        f.now = max(time.monotonic(), f.ledger.reference.raw_fix.received_monotonic + .51)
        f.real = False

    prepared = at_geometry_boundary(monkeypatch, f.ledger, 'after', expire)
    with pytest.raises(ValueError, match='issued source observation|expired'):
        f.run()
    assert prepared == ['after'] and started == []
    assert_stopped_without_input(f, chain)


@pytest.mark.parametrize('hazard', ('owner_input', 'incoming_attack'))
def test_geometry_hazard_is_vetoed_by_first_full_scene_before_selection(f, monkeypatch, hazard):
    chain = f.ledger.chain
    started, selected, observed = [], [], []
    actual_pulse = bridge.selected_key_pulse_receipt
    actual_observe = f.policy.observe

    def watch_pulse(fd, select, **kwargs):
        started.append(True)

        def watch_selection():
            selected.append(True)
            return select()

        return actual_pulse(fd, watch_selection, **kwargs)

    def watch_scene(*args, **kwargs):
        observed.append(bool(started))
        return actual_observe(*args, **kwargs)

    def queue_hazard():
        if hazard == 'owner_input':
            f.active = True
        else:
            f.append('Training dummy hits YOU for 2 points of damage.')

    monkeypatch.setattr(bridge, 'selected_key_pulse_receipt', watch_pulse)
    monkeypatch.setattr(f.policy, 'observe', watch_scene)
    prepared = at_geometry_boundary(monkeypatch, f.ledger, 'during', queue_hazard)
    with pytest.raises(RuntimeError):
        f.run()
    assert prepared == ['during'] and started == [True]
    assert observed == [True] and selected == []
    assert f.ledger.reason == 'Source owner activity or log/observation veto'
    assert_stopped_without_input(f, chain)
