"""Terminal camp steps retain actual child/root accounting; game feedback is synthetic."""
from copy import copy
from dataclasses import replace
import time

import pytest

from eql_automation.journey_input_budget import JourneyBudgetDeclaration, JourneyInputBudget
from eql_automation.source_destinations import destination_spec
from eql_automation.source_step_sender import run_checked_source_step
from eql_automation.source_transfer import SourceTransferController, SourceTransitionFix
from eql_automation.source_walk_driver import SourceWalkDriver, SourceStepBoundary
from eql_automation.supervised_source import SupervisedSourcePolicy
from eql_automation.uinput_watchdog import PulseReceipt
from eql_automation.zone_itinerary_budget import (
    ZoneItineraryBudget, ZoneItineraryDeclaration, ZoneItineraryLeg, ZoneItineraryTerminalCamp,
)
from test_route_step_sender import after_down
from test_source_motion import f, legacy
from test_source_transfer import replies


pytestmark = pytest.mark.parametrize('f', ['step'], indirect=True)


def terminal_budgets(f, *, maximum_seconds=120., maximum_pulses=32,
                     maximum_total_hold=2.):
    """Synthetic crossing metadata, followed by the registered Slave Mines camp."""
    legs = []
    for identifier, source, destination_zone, destination_id, destination in (
        ('butcher-gfay-crossing', 'Butcherblock Mountains', 'gfaydark', 54, 'The Greater Faydark'),
        ('gfay-butcher-crushbone-crossing', 'The Greater Faydark', 'crushbone', 58, 'Clan Crushbone'),
    ):
        spec = destination_spec(identifier)
        legs.append(ZoneItineraryLeg(identifier, spec.zone, spec.zone_id, source,
            destination_zone, destination_id, destination, spec.file_sha256,
            'a' * 64, 'b' * 64, 'c' * 64))
    camp = destination_spec('slave-mines')
    terminal = ZoneItineraryTerminalCamp('slave-mines', camp.zone, camp.zone_id,
        'Clan Crushbone', camp.file_sha256, 'c' * 64)
    declaration = ZoneItineraryDeclaration('synthetic-terminal-step', tuple(legs),
        maximum_seconds, maximum_pulses, maximum_total_hold, 100., terminal)
    root = ZoneItineraryBudget(declaration, clock=f.clock, stop_lock=f.ledger.lock,
        owner_binding=(f.generation,), binding_reader=lambda: (f.generation,))
    for index, leg in enumerate(legs):
        for phase, zone_id in (('crossing', leg.source_zone_id), ('loading', None),
                               ('arrival', leg.destination_zone_id),
                               ('bootstrap', leg.destination_zone_id),
                               ('walking', leg.destination_zone_id)):
            root.advance(root.stage, phase, zone_id=zone_id)
    assert root.stage.kind == 'terminal_camp' and root.stage.phase == 'walking'
    assert root.leg is terminal and root.stage.leg_index == len(legs)
    child = JourneyInputBudget(JourneyBudgetDeclaration(f.plan.itinerary.sha256,
        terminal.destination_id, 'camp', 1, 60., 16, 1.6, 50.),
        clock=f.clock, stop_lock=f.ledger.lock, owner_binding=(f.generation,),
        binding_reader=lambda: (f.generation,), parent_budget=root)
    return root, child


def attach(f, child, *, scope='camp_continuation'):
    old = f.policy
    declaration = replace(old.declaration, scope=scope,
        open_flat_clear=scope != 'camp_continuation',
        owner_supervised_continuation=scope == 'camp_continuation')
    f.policy = SupervisedSourcePolicy(f.ledger, declaration=declaration,
        gate=old.gate, owner_input=old.owner_input, log_veto=old.log_veto,
        expected_window=old.window, topology_generation=old.topology,
        check_current=old.check_current, journey_budget=child)
    return f.policy


def begin(f, driver):
    boundary = driver.next_action()
    assert type(boundary) is SourceStepBoundary
    controller = SourceTransferController(driver, boundary)
    f.policy.bind_transfer(controller)
    return controller


def run_pipe(f, controller):
    return run_checked_source_step(f.sender, controller, policy=f.policy,
        kind='forward', requested_seconds=.02, command_state_clear=lambda: True,
        pump=lambda: None)


def account(root, child, count, hold):
    for budget in (root, child):
        result = budget.snapshot()
        assert result['reserved_pulses'] == count
        assert result['reserved_maximum_hold'] == pytest.approx(hold)


def authorize_and_release(f, controller):
    """Actual authorization/accounting; only the release receipt is synthetic."""
    command = controller.next_command()
    geometry = controller.prepare(command.kind)
    scene = f.policy.observe()
    ticket = controller.stage(geometry, requested_seconds=command.requested_seconds)
    authorization = f.policy.authorize(ticket, scene)
    assert f.policy.still_authorized(authorization, scene)
    assert f.policy._journey_reservation.ticket is ticket
    at, duration = ticket.proposed_at, ticket.requested_seconds
    result = PulseReceipt(ticket.movement_key, duration, at + .001, at + .001,
        at + .001 + duration, at + .001 + duration, 'elapsed')
    f.now = result.up_completed_at + .001
    return controller.seal_release(ticket, result)


def test_real_pipe_transfer_charges_child_and_root_once_and_retains_budget_for_next_approach(f):
    root, child = terminal_budgets(f)
    policy = attach(f, child)
    driver = SourceWalkDriver(f.ledger)
    started = (root.started, root.expires_at, child.started, child.expires_at, policy.started)
    controller = begin(f, driver)
    original = f.ledger.chain
    seal = run_pipe(f, controller)
    assert f.drain_events()[:4] == ((1, 103, 1), (0, 0, 0), (1, 103, 0), (0, 0, 0))
    assert f.ledger.chain is original and f.ledger.steps == 0 and not f.sender.held
    account(root, child, 1, .05)
    assert policy._journey_reservation.ticket is seal.ticket
    outcome = controller.acknowledge_stopped(seal, *replies(f, controller, seal, y=2.2, z=2.7))
    assert outcome.kind == 'approach'
    policy.finish_transfer(controller)
    assert policy.ledger is f.ledger and f.ledger.steps == 1
    assert policy.journey_budget is child and child.parent_budget is root
    assert policy.reserved_hold == pytest.approx(.05)
    following = begin(f, driver)
    assert following is not controller and following.ordinary is f.ledger
    assert policy.ledger is following and policy.journey_budget is child
    assert (root.started, root.expires_at, child.started, child.expires_at, policy.started) == started
    account(root, child, 1, .05)


def test_eight_authorized_approaches_and_conditional_landing_spend_one_continuous_budget(f):
    f.real = False
    f.now = time.monotonic()
    root, child = terminal_budgets(f)
    policy = attach(f, child)
    driver = SourceWalkDriver(f.ledger)
    controller = begin(f, driver)
    started = (root.started, root.expires_at, child.started, child.expires_at, policy.started)
    stage = root.stage
    results = []
    for index, (y, z) in enumerate(((2.2, 2.7), (2.4, 2.7), (2.6, 2.7), (2.8, 2.7),
                                   (3., 2.7), (3.15, 2.7), (3.35, 3.01), (3.55, 3.01)), 1):
        previous = f.ledger.chain
        seal = authorize_and_release(f, controller)
        assert f.ledger.chain is previous and f.ledger.phase == 'transfer'
        account(root, child, index, .05 * index)
        outcome = controller.acknowledge_stopped(seal,
            *replies(f, controller, seal, y=y, z=z))
        results.append(outcome.kind)
        if outcome.kind == 'in_transfer':
            assert type(outcome.reference) is SourceTransitionFix
            assert not outcome.reference.observed_grounded and f.ledger.chain is previous
        else:
            policy.finish_transfer(controller)
            assert policy.ledger is f.ledger and policy.journey_budget is child
            if outcome.kind == 'approach':
                controller = begin(f, driver)
        assert root.stage is stage and child.parent_stage is stage
        assert policy.reserved_hold == pytest.approx(index * .05)
        assert (root.started, root.expires_at, child.started, child.expires_at, policy.started) == started
    assert results == ['approach'] * 6 + ['in_transfer', 'landed']
    assert f.ledger.steps == 8 and driver._active_step is None
    assert driver.next_action().target[:2] == (4., 3.9)
    assert f.drain_events() == () and not f.sender.held


def test_terminal_root_cancel_after_down_releases_without_committing_floor(f, monkeypatch):
    root, child = terminal_budgets(f)
    attach(f, child)
    controller = begin(f, SourceWalkDriver(f.ledger))
    original = f.ledger.chain
    after_down(monkeypatch, lambda: root.cancel('F9 during terminal step DOWN'))
    with pytest.raises((ValueError, RuntimeError)):
        run_pipe(f, controller)
    events = f.drain_events()
    assert (1, 103, 1) in events and (1, 103, 0) in events
    assert f.sender.release_calls >= 1 and not f.sender.held
    assert f.ledger.chain is original and f.ledger.steps == 0
    account(root, child, 1, .05)


def test_expired_terminal_root_refuses_before_down_without_spending_reservations(f):
    f.real = False
    f.now = time.monotonic()
    root, child = terminal_budgets(f, maximum_seconds=.2, maximum_total_hold=.1)
    attach(f, child)
    controller = begin(f, SourceWalkDriver(f.ledger))
    original = f.ledger.chain
    f.now = root.expires_at + .001
    with pytest.raises((ValueError, RuntimeError)):
        run_pipe(f, controller)
    assert f.drain_events() == () and not f.sender.held
    assert f.ledger.chain is original and f.ledger.steps == 0
    account(root, child, 0, 0.)


@pytest.mark.parametrize('fault', ('duplicate', 'copied'))
def test_terminal_transfer_ticket_cannot_charge_twice_or_be_replayed(f, fault):
    f.real = False
    f.now = time.monotonic()
    root, child = terminal_budgets(f)
    policy = attach(f, child)
    controller = begin(f, SourceWalkDriver(f.ledger))
    geometry = controller.prepare('forward')
    scene = policy.observe()
    ticket = controller.stage(geometry, requested_seconds=.02)
    policy.authorize(ticket, scene)
    account(root, child, 1, .05)
    with pytest.raises((ValueError, RuntimeError)):
        policy.authorize(ticket if fault == 'duplicate' else replace(ticket), scene)
    account(root, child, 1, .05)
    assert policy.reserved_hold == pytest.approx(.05)
    assert f.ledger.steps == 0 and f.drain_events() == ()


@pytest.mark.parametrize('fault', ('generation', 'zone', 'stage', 'ledger'))
def test_changed_terminal_transfer_scope_refuses_before_any_down(f, fault):
    root, child = terminal_budgets(f)
    policy = attach(f, child)
    controller = begin(f, SourceWalkDriver(f.ledger))
    original = f.ledger.chain
    if fault == 'generation':
        f.generation += 1
    elif fault == 'zone':
        f.reader.zone_id = 54
    elif fault == 'stage':
        root.advance(root.stage, 'arrival', zone_id=58)
    else:
        policy.ledger = copy(controller)
    with pytest.raises((ValueError, RuntimeError)):
        run_pipe(f, controller)
    assert f.drain_events() == () and not f.sender.held
    assert f.ledger.chain is original and f.ledger.steps == 0
    account(root, child, 0, 0.)


@pytest.mark.parametrize('fault', ('removed', 'replaced', 'empty', 'short', 'list'))
def test_terminal_transfer_context_cannot_be_removed_or_replaced_after_binding(f, fault):
    root, child = terminal_budgets(f)
    policy = attach(f, child)
    controller = begin(f, SourceWalkDriver(f.ledger))
    context = policy._budgeted_transfer_context
    assert context == (controller, f.ledger, child, root, root.stage)
    if fault == 'removed':
        policy._budgeted_transfer_context = None
    elif fault == 'replaced':
        policy._budgeted_transfer_context = (copy(controller), *context[1:])
    elif fault == 'empty':
        policy._budgeted_transfer_context = ()
    elif fault == 'short':
        policy._budgeted_transfer_context = context[:2]
    else:
        policy._budgeted_transfer_context = list(context)
    with pytest.raises((ValueError, RuntimeError)):
        run_pipe(f, controller)
    assert f.drain_events() == () and f.ledger.steps == 0 and not f.sender.held
    account(root, child, 0, 0.)


@pytest.mark.parametrize('controller_type', ('stair', 'contact', 'foreign'))
def test_terminal_scope_admits_only_its_exact_ordinary_conditional_step(f, controller_type):
    from eql_automation.source_contact_controller import SourceContactController
    from eql_automation.source_stair_controller import SourceStairController
    root, child = terminal_budgets(f)
    policy = attach(f, child)
    controller = begin(f, SourceWalkDriver(f.ledger))
    if controller_type == 'foreign':
        candidate = copy(controller)
        candidate.ordinary = copy(f.ledger)
    else:
        # Admission-only test: no stair/contact geometry or receipts are faked.
        kind = SourceStairController if controller_type == 'stair' else SourceContactController
        candidate = object.__new__(kind)
    with pytest.raises(RuntimeError, match='current terminal camp'):
        policy._terminal_transfer_context(candidate)
    assert policy.ledger is controller and policy._budgeted_transfer_context[0] is controller
    assert f.drain_events() == () and f.ledger.steps == 0
    account(root, child, 0, 0.)


@pytest.mark.parametrize('scope', ('direct_root', 'standalone', 'ordinary_route'))
def test_other_budget_and_route_scopes_do_not_gain_conditional_transfer_permission(f, scope):
    root, child = terminal_budgets(f)
    selected = child
    if scope == 'direct_root':
        selected = root
    elif scope == 'standalone':
        selected = JourneyInputBudget(child.declaration, clock=f.clock, stop_lock=f.ledger.lock,
            owner_binding=(f.generation,), binding_reader=lambda: (f.generation,))
    policy = attach(f, selected, scope='local_trial' if scope == 'ordinary_route' else 'camp_continuation')
    driver = SourceWalkDriver(f.ledger)
    controller = SourceTransferController(driver, driver.next_action())
    with pytest.raises(RuntimeError, match='current terminal camp'):
        policy.bind_transfer(controller)
    assert policy.ledger is f.ledger and policy._budgeted_transfer_context is None
    assert f.drain_events() == () and f.ledger.steps == 0
    account(root, child, 0, 0.)


@pytest.mark.parametrize('fault', ('root_cancel', 'missing_context'))
def test_completed_approach_cannot_restore_ordinary_policy_after_budget_revocation(f, fault):
    f.real = False
    f.now = time.monotonic()
    root, child = terminal_budgets(f)
    policy = attach(f, child)
    controller = begin(f, SourceWalkDriver(f.ledger))
    seal = authorize_and_release(f, controller)
    outcome = controller.acknowledge_stopped(seal,
        *replies(f, controller, seal, y=2.2, z=2.7))
    assert outcome.kind == 'approach' and f.ledger.phase == 'ready'
    reached = f.ledger.chain
    if fault == 'root_cancel':
        root.cancel('Trip stopped before approach handback')
    else:
        policy._budgeted_transfer_context = None
    with pytest.raises((ValueError, RuntimeError)):
        policy.finish_transfer(controller)
    assert policy.ledger is controller and policy.journey_budget is child
    assert f.ledger.chain is reached and f.ledger.steps == 1
    account(root, child, 1, .05)
    assert f.drain_events() == () and not f.sender.held


def test_terminal_transfer_down_deadline_leaves_reserved_hold_before_original_root_expiry(f):
    f.real = False
    f.now = time.monotonic()
    root, child = terminal_budgets(f, maximum_seconds=.2, maximum_total_hold=.1)
    policy = attach(f, child)
    controller = begin(f, SourceWalkDriver(f.ledger))
    original = (root.started, root.expires_at, child.started, child.expires_at,
                controller.reference, controller.reference.raw_fix.received_monotonic)
    geometry = controller.prepare('forward')
    f.now = root.expires_at - .06
    scene = policy.observe()
    ticket = controller.stage(geometry, requested_seconds=.02)
    authorization = policy.authorize(ticket, scene)
    assert authorization.expires_at == root.expires_at - ticket.maximum_actual_hold
    assert authorization.expires_at < ticket.proposed_at + .05
    assert authorization.issued_at <= authorization.expires_at
    assert (root.started, root.expires_at, child.started, child.expires_at,
            controller.reference, controller.reference.raw_fix.received_monotonic) == original
    assert policy._journey_reservation.ticket is ticket
    account(root, child, 1, .05)
    assert f.drain_events() == () and not f.sender.held and f.ledger.steps == 0
