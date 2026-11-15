"""Real destination bootstrap/fit/adoption; explicitly simulated input receipts."""
from dataclasses import asdict, replace
from hashlib import sha256
from types import SimpleNamespace

import pytest

import eql_automation.camp_source_runtime as source_module
import eql_automation.destination_source_runtime as adoption
from eql_automation.camp_source_runtime import CampSourceRuntime
from eql_automation.destination_floor_bootstrap import DestinationFloorCheckpoint
from eql_automation.destination_source_runtime import DestinationSourceDeclaration, start_destination_source
from eql_automation.journey_input_budget import JourneyBudgetDeclaration, JourneyInputBudget
from eql_automation.location_hotkey import HotkeyReceipt
from eql_automation.native_region_policy import encoded
from eql_automation.source_itinerary import SourceItineraryGuide, SourceWalkHint
from eql_automation.source_section_manifest import parse_walking_sections
from eql_automation.source_walk_sections import plan_walk_sections
from eql_automation.supervised_source import SupervisedSourcePolicy
from eql_automation.uinput_watchdog import PulseReceipt
from test_destination_bootstrap_runtime import runtime, advance
from test_destination_floor_bootstrap import destination
from test_itinerary_policy_budget import root_budget
from test_motion_calibration import legacy as fitter
from test_route_floor_commit import legacy


@pytest.fixture
def prepared(runtime, legacy, monkeypatch):
    f = runtime
    advance(f, lambda:f.runtime.phase == 'complete')
    f.mode = 'camp_route'
    f.source_hook = None
    def current():
        if f.source_hook is not None:
            hook, f.source_hook = f.source_hook, None
            hook()
    f.source_options = dict(declaration=DestinationSourceDeclaration(
        'synthetic-destination-source', True, 60., 32, 10., 2., .25), legacy=legacy,
        check_current=current, mode_reader=lambda:f.mode,
        generation_reader=lambda:f.generation, generation=f.generation)
    f.source = None
    def location(sender, **options):
        assert f.source.current_input_key() == 59
        assert options['release_deadline'] == f.source.input_release_deadline <= f.runtime.expires_at
        options['ensure_current']()
        if f.send_hook is not None:
            hook, f.send_hook = f.send_hook, None
            hook()
        options['ensure_current']()
        began = f.now
        f.now += .01
        receipt = PulseReceipt(59, .005, began, began+.001, began+.006, f.now, 'elapsed')
        f.sent.append(receipt)
        f.release_deadlines.append(options['release_deadline'])
        f.append(f'Your Location is {f.y:.2f}, {f.x:.2f}, 2.70')
        return HotkeyReceipt(receipt, f.now)
    monkeypatch.setattr(source_module, 'send_location_hotkey', location)
    def forbidden(*args, **kwargs):raise AssertionError('No source movement should occur during startup')
    monkeypatch.setattr(source_module, 'run_checked_source_step', forbidden)
    return f


def prepare_route(f, *, sectioned=False):
    p = f.planner
    ops = (SourceWalkHint((f.x, f.y), (f.x, f.y+.5)),)
    if sectioned:ops += (SourceWalkHint((f.x, f.y+.5), (f.x, f.y+1.)),)
    guide = SourceItineraryGuide('gfaydark', p.pins[2], p.pins[3], 'f'*64,
                                 .1, 6., ops[-1].end, ops)
    sections = None
    if sectioned:
        record = plan_walk_sections(f.runtime.runtime.reference.fork(), guide, p,
            bounds=f.bounds, maximum_length=.75, minimum_length=.25, candidate_spacing=.1,
            check_context=f.runtime._check_context, clock=f.clock)
        sections = parse_walking_sections(guide, record)
        assert len(sections.guides) == 2
    f.runtime.prepare_route(guide, sections=sections)
    advance(f, lambda:f.runtime.phase == 'route_ready')
    return guide, sections


def start(f, **options):
    f.source = start_destination_source(f.runtime, **(f.source_options | options))
    return f.source


def startup(f):
    for _ in range(300):
        if f.source.phase != 'startup':
            assert f.source.phase == 'ready'
            return
        f.source.tick()
        f.now += .01
    pytest.fail('Destination source did not collect its new startup pair')


def test_adoption_uses_actual_destination_fit_and_retains_owning_scope(prepared):
    f = prepared
    prepare_route(f)
    parent, probe, lease = f.runtime, f.runtime.runtime, f.lease
    estimate = parent.calibration['estimate']['estimate']
    sent = len(f.sent)
    source = start(f)
    assert type(source) is CampSourceRuntime and type(parent.floor) is DestinationFloorCheckpoint
    assert source.probe is probe and source.lease is lease and source.owner_input is parent.owner_input
    assert source.clock is parent.clock and source.lock is parent.lock and source.probe.log_veto is parent.log_veto
    assert parent.phase == probe.phase == 'route_ready' and lease.active
    assert not parent.closed and not probe.closed and not f.closed_observer
    assert source.phase == 'startup' and source.policy is None and len(f.sent) == sent
    assert source.plan.heading == estimate['final_heading']
    assert source.plan.motion.run_speed == estimate['run_speed']
    assert source.plan.motion.turn_rate == estimate['turn_rate']
    assert source.plan.motion.turn_latency == estimate['turn_latency']
    assert source.plan.motion.right_sign == estimate['right_sign'] and source.plan.motion.back_speed == 0.
    original, onward = asdict(probe.root.bounds), asdict(source.plan.bounds)
    assert onward['maximum_requested_hold'] == .1
    assert all(onward[k] == v for k,v in original.items() if k not in ('record_id', 'maximum_requested_hold'))


def test_adoption_requires_another_new_stopped_pair_before_policy(prepared):
    f = prepared
    prepare_route(f)
    route_start = f.runtime.runtime.route_start.height
    source = start(f)
    sent = len(f.sent)
    startup(f)
    assert len(f.sent) == sent+2 and len(f.movements) == 7
    assert type(source.policy) is SupervisedSourcePolicy
    assert source.policy.owner_input is f.owner_input and source.policy.log_veto is f.veto
    assert source.policy.declaration.owner_supervised_continuation is True
    assert source.policy.declaration.open_flat_clear is False
    pair = source.pairs[0]['raw_fixes']
    assert pair[0]['log_line_seq'] > route_start.second.log_line_seq
    assert pair[1]['log_line_seq'] == pair[0]['log_line_seq']+1
    assert source.ledger.steps == 0 and not source.snapshot()['real_client_accepted']


@pytest.mark.parametrize('runtime', ['budget'], indirect=True)
def test_root_advances_once_after_fit_and_accounts_source_proposal(prepared):
    f = prepared
    prepare_route(f)
    old_stage, expiry = f.budget.stage, f.budget.expires_at
    source = start(f)
    assert old_stage.phase == 'bootstrap' and f.budget.stage.phase == 'walking'
    assert f.budget.stage.epoch == old_stage.epoch+1
    assert f.budget.snapshot()['reserved_pulses'] == 7
    startup(f)
    assert source.policy.journey_budget is f.budget and f.budget.expires_at == expiry
    geometry = source.ledger.prepare('forward')
    scene = source.policy.observe()
    ticket = source.ledger.stage(geometry, requested_seconds=.02)
    authorization = source.policy.authorize(ticket, scene)
    assert source.policy.still_authorized(authorization, source.policy.observe()) is True
    assert f.budget.snapshot()['reserved_pulses'] == 8
    assert not f.sender.held and len(f.movements) == 7  # Proposal only; no source DOWN.


@pytest.mark.parametrize('runtime', ['budget'], indirect=True)
def test_section_zero_retains_preconstructed_child_and_walking_stage(prepared):
    f = prepared
    guide, sections = prepare_route(f, sectioned=True)
    f.budget.advance(f.budget.stage, 'walking', zone_id=54)
    stage = f.budget.stage
    declaration = JourneyBudgetDeclaration(sha256(encoded(guide.record())).hexdigest(),
        f.budget.leg.destination_id, 'zone_crossing', 2, 50., 32, 2., 20.)
    child = JourneyInputBudget(declaration, clock=f.clock, stop_lock=f.lock,
        owner_binding=f.owner, binding_reader=f.binding, parent_budget=f.budget)
    source = start(f, journey_budget=child)
    startup(f)
    assert f.budget.stage is stage and source.policy.journey_budget is child
    assert child.parent_budget is f.budget and child.parent_stage is stage
    assert source.observer.itinerary.record()['goal'] == list(sections.guides[0].goal)
    assert source.probe.route_sections is sections
    assert source.policy.declaration.maximum_seconds <= child.expires_at-f.now+.02


@pytest.mark.parametrize('runtime', ['budget'], indirect=True)
@pytest.mark.parametrize('fault', ('expired_start', 'fit'))
def test_refused_fit_cannot_advance_root_or_publish_source(prepared, fault):
    f = prepared
    prepare_route(f)
    stage = f.budget.stage
    if fault == 'expired_start':f.now += .6
    else:f.runtime.calibration['estimate']['estimate']['final_heading'] += 1.
    with pytest.raises((ValueError, RuntimeError)):start(f)
    assert f.source is None and f.budget.stage is stage
    assert f.runtime.phase == 'stopped' and not f.budget.valid and not f.lease.active


def test_second_adoption_refuses_without_stopping_first_source(prepared):
    f = prepared
    prepare_route(f)
    source = start(f)
    with pytest.raises(ValueError, match='only be adopted once'):
        start_destination_source(f.runtime, **f.source_options)
    source.check_current()
    assert source.phase == 'startup' and f.runtime.phase == 'route_ready' and f.lease.active


@pytest.mark.parametrize('fault', ('mode', 'generation', 'cancel'))
def test_reentrant_owner_change_during_motion_construction_never_adopts(prepared, fault):
    f = prepared
    prepare_route(f)
    original = f.source_options['legacy']
    class ChangedMotion(original.Motion):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            if fault == 'mode':f.mode = 'assist'
            elif fault == 'generation':f.generation += 1
            else:f.runtime.cancel('F9 during fresh motion adoption')
    altered = SimpleNamespace(**vars(original))
    altered.Motion = ChangedMotion
    with pytest.raises((ValueError, RuntimeError)):start(f, legacy=altered)
    assert f.source is None and f.runtime.phase == 'stopped' and not f.lease.active


@pytest.mark.parametrize('runtime', ['budget'], indirect=True)
def test_cancel_after_source_constructor_cannot_publish_live_result(prepared, monkeypatch):
    f = prepared
    prepare_route(f)
    original = adoption.CampSourceRuntime
    constructed = []
    def cancelled(*args, **kwargs):
        result = original(*args, **kwargs)
        constructed.append(result)
        f.runtime.cancel('F8 takeover immediately after adoption')
        return result
    monkeypatch.setattr(adoption, 'CampSourceRuntime', cancelled)
    with pytest.raises((ValueError, RuntimeError)):start(f)
    assert f.source is None and constructed[0].phase == 'stopped'
    assert not f.budget.valid and not f.lease.active and f.runtime.phase == 'stopped'


def test_stop_inside_startup_location_callback_cannot_create_policy(prepared):
    f = prepared
    prepare_route(f)
    source = start(f)
    sent = len(f.sent)
    f.send_hook = lambda:f.runtime.cancel('F9 during new source startup')
    with pytest.raises((ValueError, RuntimeError)):startup(f)
    assert source.phase == f.runtime.phase == 'stopped'
    assert source.policy is None and len(f.sent) == sent and not f.lease.active


@pytest.mark.parametrize('fault', ('focus', 'activity'))
def test_startup_scene_veto_immediately_cancels_retained_parent(prepared, fault):
    f = prepared
    prepare_route(f)
    source = start(f)
    sent = len(f.sent)
    if fault == 'focus':f.focus = False
    else:f.active = True
    with pytest.raises((ValueError, RuntimeError)):startup(f)
    assert source.phase == f.runtime.phase == 'stopped'
    assert source.policy is None and len(f.sent) == sent and not f.lease.active


def test_startup_policy_failure_immediately_cancels_retained_parent(prepared, monkeypatch):
    f = prepared
    prepare_route(f)
    source = start(f)
    def refused(*args, **kwargs):raise ValueError('synthetic policy admission refusal')
    monkeypatch.setattr(adoption, 'SupervisedSourcePolicy', refused)
    with pytest.raises(ValueError, match='policy admission refusal'):startup(f)
    assert source.phase == f.runtime.phase == 'stopped' and not f.lease.active


def test_explicit_source_duration_is_not_renewed_by_startup(prepared):
    f = prepared
    prepare_route(f)
    start_time = f.now
    source = start(f, declaration=replace(f.source_options['declaration'], maximum_seconds=2.))
    startup(f)
    assert source.policy.declaration.maximum_seconds < 2.
    assert source.input_release_deadline == source.policy.release_deadline == start_time+2.
    assert f.release_deadlines[-2:] == [start_time+2.]*2
    assert source.observer.calibration.valid_until_monotonic == start_time+2.
    f.now = start_time+2.001
    sent = len(f.sent)
    with pytest.raises((ValueError, RuntimeError)):source.tick()
    assert source.phase == f.runtime.phase == 'stopped' and len(f.sent) == sent


def test_final_reader_callback_cannot_outlive_shorter_source_deadline(prepared):
    f = prepared
    prepare_route(f)
    calls = []
    def generation():
        calls.append(1)
        if len(calls) == 2:f.now += 3.
        return f.generation
    with pytest.raises(ValueError, match='deadline'):
        start(f, declaration=replace(f.source_options['declaration'], maximum_seconds=2.),
              generation_reader=generation)
    assert f.source is None and f.runtime.phase == 'stopped' and not f.lease.active


@pytest.mark.parametrize('remaining', (.20, .17))
def test_source_movement_admission_uses_shorter_absolute_release_deadline(prepared, remaining):
    f = prepared
    prepare_route(f)
    source = start(f, declaration=replace(f.source_options['declaration'], maximum_seconds=1.))
    startup(f)
    f.now = source.input_release_deadline-remaining
    geometry = source.ledger.prepare('forward')
    scene = source.policy.observe()
    ticket = source.ledger.stage(geometry, requested_seconds=.02)
    if remaining < ticket.maximum_actual_hold:
        with pytest.raises(RuntimeError, match='release deadline'):
            source.policy.authorize(ticket, scene)
        assert source.policy.reserved_hold == 0.
    else:
        authorization = source.policy.authorize(ticket, scene)
        assert authorization.expires_at == pytest.approx(source.input_release_deadline-ticket.maximum_actual_hold)
        assert authorization.expires_at < ticket.proposed_at+.05
    assert not f.sender.held and len(f.movements) == 7


@pytest.mark.parametrize('runtime', ['budget'], indirect=True)
def test_foreign_budget_is_refused_before_claim_or_root_advance(prepared):
    f = prepared
    prepare_route(f)
    other = root_budget(clock=f.clock, lock=f.lock)
    stage = f.budget.stage
    with pytest.raises(ValueError, match='original root'):start(f, journey_budget=other)
    assert f.budget.stage is stage and f.budget.valid and other.valid
    assert not hasattr(f.runtime, '_source_adoption_claim')


@pytest.mark.parametrize('change', ({'owner_supervised_continuation':False}, {'maximum_seconds':float('nan')},
                                    {'maximum_steps':0}, {'walk_half_width':0.}))
def test_explicit_limits_required_before_parent_claim(prepared, change):
    f = prepared
    prepare_route(f)
    with pytest.raises(ValueError):start(f, declaration=replace(f.source_options['declaration'], **change))
    assert not hasattr(f.runtime, '_source_adoption_claim') and f.lease.active
