"""Actual two-crossing/terminal contracts with synthetic feedback and receipts.

The existing integration fixture supplies real readers, floors, probe reducers,
source runtimes and crossings. Its location replies and low-level pulse receipts
are explicitly simulated; this does not claim client or device acceptance.
"""
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

import test_zone_itinerary_runtime as crossing_fixture
from eql_automation.camp_session import NpcCandidate
from eql_automation.camp_source_runtime import CampSourceRuntime
from eql_automation.destination_bootstrap_runtime import DestinationBootstrapRuntime
from eql_automation.native_region_policy import encoded
from eql_automation.owner_source_assets import SourceDestinationAssets
from eql_automation.owner_source_crossing import OwnerSourceCrossingRuntime
from eql_automation.owner_navigation_preflight import settings_identity
from eql_automation.owner_itinerary_camp_arrival import ItineraryCampArrival
from eql_automation.portal_precision import SourceFace
from eql_automation.section_continuation import SectionArrival
from eql_automation.source_destinations import destination_spec
from eql_automation.source_itinerary import SourceItineraryGuide, SourceStepHint, SourceWalkHint
from eql_automation.source_motion import SourceMotionTicket
from eql_automation.zone_itinerary_budget import ZoneItineraryDeclaration, ZoneItineraryTerminalCamp
from eql_automation.zone_itinerary_runtime import ZoneItineraryPlan
from test_motion_calibration import legacy as fitter
from test_route_floor_commit import legacy


@pytest.fixture
def terminal(tmp_path, monkeypatch, legacy, fitter, request):
    # Declare the terminal before the original root and first crossing exist.
    # Never replace an active root, edit its pins, or renew its original clock.
    def declaration(*args, **kwargs):
        value = ZoneItineraryDeclaration(*args, **kwargs)
        spec = destination_spec('slave-mines')
        camp = ZoneItineraryTerminalCamp(spec.identifier, spec.zone, spec.zone_id,
            'Clan Crushbone', spec.file_sha256, value.legs[-1].catalog_sha256)
        return replace(value, terminal_camp=camp)
    monkeypatch.setattr(crossing_fixture, 'ZoneItineraryDeclaration', declaration)
    generator = crossing_fixture.itinerary.__wrapped__(tmp_path, monkeypatch, legacy, fitter, request)
    f = next(generator)
    try:
        f.engine.settings = SimpleNamespace(game_dir=str(tmp_path), character='Probe', server='private', level=7)
        f.engine.camp_session = f.engine.autopilot = None
        f.journey.settings = settings_identity(f.engine.settings)
        f.journey.camp_motion = None
        f.journey.continue_camps = f.journey._continue_camps = False
        f.crushbone = crossing_fixture.planner(tmp_path/'terminal-crushbone',
            f.butcher.installed_region_model, zone='crushbone', zone_id=58,
            name='Clan Crushbone', split=80.)
        guide = SourceItineraryGuide('crushbone', *f.crushbone.pins[2:], 'e'*64,
            .1, 6., (4., 12.), (SourceWalkHint((4., 3.), (4., 12.)),))
        f.terminal_step = getattr(request, 'param', None) == 'step'
        if f.terminal_step:
            def face(points, index):
                return SourceFace(tuple((y, x, z) for x, y, z in points), 0, 'Diffuse', 10, index)
            def rectangle(y0, y1, z, index):
                a, b, c, d = (0., y0, z), (10., y0, z), (10., y1, z), (0., y1, z)
                return face((a, b, c), index), face((a, c, d), index + 1)
            source = f.crushbone.source
            source.sources = (*rectangle(-50., 9.3, .2, 0), *rectangle(9.3, 100., .5125, 2),
                face(((0., 9.3, .2), (10., 9.3, .2), (10., 9.3, .5125)), 4),
                face(((0., 9.3, .2), (10., 9.3, .5125), (0., 9.3, .5125)), 5))
            coordinates = np.asarray([value.vertices_wld for value in source.sources])[:, :, [1, 0, 2]]
            source.source_minimum, source.source_maximum = coordinates.min(axis=1), coordinates.max(axis=1)
            guide = replace(guide, operations=(SourceWalkHint((4., 3.), (4., 9.1)),
                SourceStepHint((4., 9.1), (4., 9.5), ((10, 2),), .5, 1.),
                SourceWalkHint((4., 9.5), (4., 12.))))
            append = f.append
            def stepped_location(body):
                if f.reader.zone_id == 58 and f.y > 9.3 and body.startswith('Your Location is '):
                    body = body.rsplit(', ', 1)[0] + ', 3.0125'
                append(body)
            f.append = stepped_location
        f.terminal_assets = SourceDestinationAssets(f.crushbone, guide,
            'Synthetic terminal camp', encoded({'synthetic': True, 'client_verified': False}), 'slave-mines')
        f.provider_calls = []
        def destination(identifier):
            f.provider_calls.append(('destination', identifier))
            return f.terminal_assets if identifier == 'slave-mines' else f.assets
        def sections(assets):
            f.provider_calls.append(('sections', assets.destination_id))
            return None if assets is f.terminal_assets else f.sections
        def crossing(identifier):
            f.provider_calls.append(('crossing', identifier))
            assert identifier != 'slave-mines', 'Terminal camp must never load a crossing corridor'
            return next(value for value in f.specs if value.destination_id == identifier)
        f.plan = ZoneItineraryPlan(f.root.declaration, f.bounds, f.basis,
                                  destination, sections, crossing)
        f.candidates = (NpcCandidate('synthetic orc', (5,), 'a'*64, ((1, 2),)),)
        f.engine._load_camp_candidates = lambda zone: f.candidates
        yield f
    finally:
        next(generator, None)
        # A successful token intentionally owns the still-open observer after
        # navigation retires. This fixture has no real camp/device to own it.
        if f.closed_observer == 0:
            f.owner_input.close()


def reach_terminal(f, *, phase='terminal_ready'):
    crossing_fixture.complete_first(f)
    crossing_fixture.run_until(f, lambda: f.controller.phase == phase
        and f.root.stage.kind == 'terminal_camp')
    return f.controller


def assert_clean_stop(f, sent, pulses):
    assert f.controller.phase == 'stopped'
    assert len(f.sent) == sent and len(f.pulses) == pulses
    assert not f.sender.held and not f.root.valid
    f.controller.release()
    assert f.closed_observer == 1
    assert f.tracker.lease is None
    f.controller.release()
    assert f.closed_observer == 1


@pytest.mark.parametrize('terminal', [None, 'sections', 'step'], indirect=True)
def test_terminal_uses_fresh_crushbone_probes_and_actual_source_before_transfer(terminal):
    f = terminal
    root, observer, expiry = f.root, f.owner_input, f.root.expires_at
    r = reach_terminal(f)
    assert r.root is root and r.owner_input is observer and root.expires_at == expiry
    assert root.declaration.target_count == 3
    assert root.stage.kind == 'terminal_camp' and root.stage.phase == 'walking'
    assert root.stage.leg_index == 2 and root.leg.destination_id == 'slave-mines'
    assert f.transitions == [(68, 'The Greater Faydark'), (54, 'Clan Crushbone')]
    assert len(r.records) == 2 and all(value['kind'] == 'crossing' for value in r.records)
    assert f.reader.zone_id == 58 and f.journey.destination_assets is f.terminal_assets
    boots = f.children['bootstrap']
    assert len(boots) == 2 and all(type(value) is DestinationBootstrapRuntime for value in boots)
    assert all(len(value.runtime.results) == 7 for value in boots)
    assert boots[0] is not boots[1] and boots[0].bootstrap is not boots[1].bootstrap
    assert boots[0].calibration is not boots[1].calibration
    assert type(f.first) is OwnerSourceCrossingRuntime
    assert len(f.children['crossing']) == 1 and type(f.children['crossing'][0]) is OwnerSourceCrossingRuntime
    arrival = r.terminal_arrival
    assert type(arrival) is SectionArrival and type(arrival.runtime) is CampSourceRuntime
    assert arrival.runtime is r.source and arrival.runtime.phase == 'complete'
    assert arrival.runtime.ledger is not f.children['source'][0].ledger
    assert arrival.checkpoint.valid and arrival.budget is r.child_budget
    assert arrival.budget.parent_budget is root
    assert len(f.terminal_assets.guide.operations) == (3 if f.terminal_step else 1)
    assert root.snapshot()['reserved_pulses'] == len(f.pulses)
    terminal_pulses = [pulse for zone, pulse in f.pulses if zone == 58]
    assert len(terminal_pulses) > 7, 'Terminal source movement must charge after its seven probes'
    step_reservations = [row[0] for row in root._reservations.values()
        if row[0].stage.kind == 'terminal_camp' and row[0].stage.phase == 'walking'
        and type(row[0].ticket) is SourceMotionTicket
        and 'plan_sha256' in row[0].ticket.geometry.record()]
    assert bool(step_reservations) is f.terminal_step
    assert not f.closed_observer and f.tracker.lease is r.lease and r.lease.active
    assert all(deadline == expiry for _, _, deadline in f.sent)
    assert ('crossing', 'slave-mines') not in f.provider_calls
    assert ('destination', 'slave-mines') in f.provider_calls
    assert not r.snapshot()['real_client_accepted']

    before = root._balance, len(f.sent), len(f.pulses)
    token = r.transfer_terminal_arrival(candidates=f.candidates)
    assert type(token) is ItineraryCampArrival and token is r.terminal_transfer
    assert token.arrival is arrival and token.root is root and token.candidates is f.candidates
    assert token.monitor is f.journey.camp_motion and token.monitor.observer is observer
    token.check_identity()
    assert r.closed and r.phase == 'terminal_transferred'
    assert root.valid and root.stage.kind == 'terminal_camp' and root.stage.phase == 'complete'
    assert root.expires_at == expiry
    assert before == (root._balance, len(f.sent), len(f.pulses))
    assert arrival.runtime.phase == 'complete' and arrival.checkpoint.valid
    assert f.tracker.lease is None and not r.lease.active and not f.closed_observer
    assert not f.sender.held
    with pytest.raises((ValueError, RuntimeError)):
        r.transfer_terminal_arrival(candidates=f.candidates)
    assert not f.closed_observer


@pytest.mark.parametrize('fault', ('generation', 'probe_generation', 'focus', 'activity', 'hazard', 'expiry', 'candidate_callback'))
def test_terminal_bootstrap_refuses_owner_changes_without_input_or_observer_leak(terminal, fault):
    f = terminal
    reach_terminal(f, phase='load_destination')
    if fault == 'probe_generation':
        crossing_fixture.run_until(f, lambda: f.controller.phase == 'bootstrap'
            and f.controller.bootstrap.runtime is not None
            and len(f.controller.bootstrap.runtime.results) == 1)
    sent, pulses = len(f.sent), len(f.pulses)
    if fault in ('generation', 'probe_generation'):
        f.engine.cancel_generation += 1
    elif fault == 'focus': f.focus = False
    elif fault == 'activity': f.active = True
    elif fault == 'hazard': f.append('Training dummy hits YOU for 2 points of damage.')
    elif fault == 'candidate_callback':
        def cancelled_candidates(zone):
            f.engine.cancel_generation += 1
            return f.candidates
        f.engine._load_camp_candidates = cancelled_candidates
    else: f.now = f.root.expires_at + .01
    with pytest.raises((ValueError, RuntimeError)):
        f.controller.tick()
    assert_clean_stop(f, sent, pulses)


@pytest.mark.parametrize('fault', ('stale_arrival', 'generation', 'focus', 'hazard', 'published_stop', 'reentry'))
def test_terminal_transfer_rechecks_freshness_and_owner_before_retiring(terminal, fault):
    f = terminal
    r = reach_terminal(f)
    sent, pulses = len(f.sent), len(f.pulses)
    if fault == 'stale_arrival': f.now += .51
    elif fault == 'generation': f.current_hook = lambda: setattr(f.engine, 'cancel_generation', 2)
    elif fault == 'focus': f.current_hook = lambda: setattr(f, 'focus', False)
    elif fault == 'hazard': f.current_hook = lambda: f.append('Training dummy hits YOU for 2 points of damage.')
    elif fault == 'published_stop':
        def stop_after_publication():
            if f.journey.camp_motion is not None:
                f.engine.cancel_generation += 1
            else:
                f.current_hook = stop_after_publication
        f.current_hook = stop_after_publication
    else:
        sample = f.owner_input.sample
        attempts = []
        def recursive_sample():
            if not attempts:
                attempts.append('attempted')
                with pytest.raises(ValueError, match='reentered'):
                    r.transfer_terminal_arrival(candidates=f.candidates)
                attempts.append('refused')
            return sample()
        f.owner_input.sample = recursive_sample
    with pytest.raises((ValueError, RuntimeError)):
        r.transfer_terminal_arrival(candidates=f.candidates)
    if fault == 'reentry': assert attempts == ['attempted', 'refused']
    assert_clean_stop(f, sent, pulses)
