"""Initial trip accounting on actual collectors; game state is synthetic.

Deterministic tests report synthetic input receipts. The integration cases use
the retained helper and actual watchdog on anonymous pipes, never a game device.
"""
from dataclasses import replace
from datetime import datetime, timedelta
import math
import threading
import time
from types import SimpleNamespace

import pytest

from eql_automation.initial_itinerary_measurement import InitialItineraryMeasurement
from eql_automation.location_log import LocationLogReader
from eql_automation.motion_collection import (
    CommandReceipt, MotionExperimentDriver, MotionExperimentSession, MotionRequest,
    ReleasedPulse,
)
from eql_automation.native_region_policy import encoded
from eql_automation.uinput_watchdog import PulseReceipt
from eql_automation.unbound_location_log import UnboundLocationReader
from test_itinerary_policy_budget import root_budget
from test_journey_input_budget import bounds as ordinary_bounds
from test_motion_collection import retained
from test_owner_supervised_motion import h as pipe, feedback, complete
from test_route_step_sender import after_down


def source_reader(log, names, append, clock):
    names.write_text('68^Butcherblock Mountains^0^0\n54^The Greater Faydark^0^0\n')
    reader = LocationLogReader(log, names, expected_character='Probe', expected_server='private')
    append('You have entered Butcherblock Mountains.')
    reader.poll(now=clock())
    assert reader.zone_id == 68
    return reader


@pytest.fixture
def f(tmp_path, retained, request):
    h = SimpleNamespace(now=100., generation=1, owner=1, mode='measurement',
        point=(0., 0., 0.), heading=350., requests=[], reported=[], location_requests=[])
    h.clock = lambda:h.now
    h.wall = lambda:datetime(2026, 11, 15, 8)+timedelta(seconds=h.now-100.)
    h.log = tmp_path/'eqlog_Probe_private.txt'
    h.log.touch()
    def append(body):
        with h.log.open('a') as stream:
            stream.write(h.wall().strftime('[%a %b %d %H:%M:%S %Y] ')+body+'\n')
    h.append = append
    h.source = source_reader(h.log, tmp_path/'ZoneNames.txt', append, h.clock)
    h.reader = UnboundLocationReader(h.log, expected_character='Probe', expected_server='private')
    h.lock = threading.RLock()
    h.session = MotionExperimentSession(h.reader, zone_id=None, zone_display_name=None,
        zone_short_name=None, relative=True, generation=h.generation,
        generation_reader=lambda:h.generation, mode_reader=lambda:h.mode,
        binding_reader=lambda:('synthetic-owner', h.owner), record_id='initial-trip-measurement',
        horizontal_error=.01, legacy=retained[2], clock=h.clock, local_wall_clock=h.wall,
        stop_lock=h.lock)
    h.root = root_budget(clock=h.clock, lock=h.lock, binding=lambda:(h.owner,),
                        **getattr(request, 'param', {}))
    h.bounds = replace(ordinary_bounds(), forward_speed_upper_bound=40.)
    h.basis = encoded(dict(kind='synthetic-independent-initial-hypotheses', game_motion_verified=False))
    h.options = dict(bounds=h.bounds, bounds_basis=h.basis, source_reader=h.source)
    h.account = InitialItineraryMeasurement(h.session, h.root, **h.options)

    def location(request):
        h.account.check()
        h.location_requests.append(request)
        start = h.clock()
        append('Your Location is '+', '.join(f'{v:.2f}' for v in h.point))
        return CommandReceipt(start, h.clock())
    h.location = location

    def pulse(request):
        expiry = h.account.observe(request, 'pulse_start')
        assert h.now <= expiry <= h.root.expires_at-h.bounds.maximum_actual_hold
        h.account.observe(request, 'pulse_held')
        start = h.now
        probe = request.probe
        receipt = PulseReceipt(probe.key_code, probe.seconds, start, start+.0002,
            start+.0002+probe.seconds, start+.0004+probe.seconds, 'elapsed')
        h.now = receipt.up_completed_at
        h.account.observe(request, 'pulse_end')
        released = ReleasedPulse(receipt, h.now)
        h.account.released(request, released)
        h.requests.append(request)
        h.reported.append(released)
        held = ((receipt.up_started_at-receipt.down_completed_at)+receipt.maximum_held_seconds)/2
        if probe.key == 'forward':
            angle = math.radians(h.heading)
            h.point = (h.point[0]+math.cos(angle)*30.*held,
                       h.point[1]+math.sin(angle)*30.*held, 0.)
        else:
            h.heading = (h.heading+(-1 if probe.key=='right' else 1)*170.*max(0., held-.03))%360
        return released
    h.pulse = pulse
    h.driver = MotionExperimentDriver(h.session, request_location=location, run_pulse=pulse)
    return h


def pending(f):
    """Obtain a real first MotionRequest without letting any executor send it."""
    for _ in range(100):
        f.now += .025
        action = f.session.tick()
        if isinstance(action, MotionRequest):return action
        if action is not None:f.session.command_sent(action, f.location(action))
    pytest.fail('Collector did not create an initial motion request')


def run(f):
    for _ in range(1600):
        if f.session.phase == 'complete':return
        f.now += .025
        f.driver.tick()
    pytest.fail('Synthetic initial experiment did not finish')


def test_all_seven_actual_requests_charge_original_root_before_synthetic_down(f):
    deadline = f.root.expires_at
    run(f)
    assert f.session.phase == 'complete' and f.account.complete
    assert len(f.requests) == len(f.account.reservations) == len(f.account.releases) == 7
    assert f.root.snapshot()['reserved_pulses'] == 7
    assert f.root.snapshot()['reserved_maximum_hold'] == pytest.approx(7*f.bounds.maximum_actual_hold)
    expected = 4*(f.bounds.forward_speed_upper_bound*f.bounds.maximum_actual_hold+f.bounds.post_release_drift)
    expected += 3*(f.bounds.pivot_displacement_upper_bound+f.bounds.post_release_drift)
    assert f.root.snapshot()['reserved_displacement_hypothesis'] == pytest.approx(expected)
    assert f.root.expires_at == f.account.release_deadline == deadline
    assert all(reservation.request is request for reservation, request in zip(f.account.reservations, f.requests))
    assert not f.account.snapshot()['input_authorized']
    assert not f.account.snapshot()['real_client_accepted']


def test_second_account_cannot_restart_initial_measurement_or_refund_allowance(f):
    with pytest.raises(ValueError):
        InitialItineraryMeasurement(f.session, f.root, **f.options)
    assert f.root.snapshot()['reserved_pulses'] == 0


def test_initial_account_cannot_attach_after_collection_has_started(f):
    untouched_root = root_budget(clock=f.clock, lock=f.lock)
    pending(f)
    with pytest.raises(ValueError, match='untouched initial experiment'):
        InitialItineraryMeasurement(f.session, untouched_root, **f.options)
    assert untouched_root.snapshot()['reserved_pulses'] == 0


def test_initial_account_cannot_give_an_older_session_a_later_root_deadline(f):
    f.now += .01
    later_root = root_budget(clock=f.clock, lock=f.lock)
    with pytest.raises(ValueError, match='deadline must precede'):
        InitialItineraryMeasurement(f.session, later_root, **f.options)
    assert later_root.snapshot()['reserved_pulses'] == 0


def test_finished_initial_measurement_retains_original_charges_across_first_zone(f):
    deadline = f.root.expires_at
    run(f)
    for phase, zone in (('crossing', 68), ('loading', None), ('arrival', 54),
                        ('bootstrap', 54), ('walking', 54)):
        f.root.advance(f.root.stage, phase, zone_id=zone)
        f.root.check()
        assert f.root.snapshot()['reserved_pulses'] == 7
        assert f.root.expires_at == deadline
    assert f.root.stage.leg_index == 1


@pytest.mark.parametrize('f, accepted', [
    (dict(maximum_pulses=1), 1),
    (dict(maximum_total_hold=.19), 0),
    (dict(maximum_displacement_reserve=1.), 0),
], indirect=['f'])
def test_each_initial_root_limit_blocks_the_next_unfunded_request(f, accepted):
    with pytest.raises((ValueError, RuntimeError)):
        run(f)
    assert len(f.requests) == len(f.account.releases) == accepted
    assert f.root.snapshot()['reserved_pulses'] == accepted
    assert not f.root.valid


@pytest.mark.parametrize('fault', ('owner', 'generation', 'source_zone', 'source_epoch', 'bounds', 'basis', 'stage', 'deadline'))
def test_changed_context_refuses_without_charging_movement(f, fault):
    request = pending(f)
    if fault == 'owner':f.owner += 1
    elif fault == 'generation':f.generation += 1
    elif fault == 'source_zone':f.source.zone_id = 54
    elif fault == 'source_epoch':f.source.tail.epoch += 1
    elif fault == 'bounds':object.__setattr__(f.bounds, 'forward_speed_upper_bound', 1.)
    elif fault == 'basis':f.account.bounds_basis = encoded({'changed':True})
    elif fault == 'stage':
        with pytest.raises(ValueError):
            f.root.advance(f.root.stage, 'crossing', zone_id=68)
    else:f.now = f.root.expires_at+.001
    with pytest.raises((ValueError, RuntimeError)):
        f.account.observe(request, 'pulse_start')
    assert f.root.snapshot()['reserved_pulses'] == 0 and not f.account.releases
    with pytest.raises(ValueError):
        _ = f.account.complete
    assert not f.requests


@pytest.mark.parametrize('fault', ('copied_request', 'wrong_pending', 'duplicate_start', 'changed_request', 'copied_reservation'))
def test_exact_pending_request_and_reservation_cannot_be_replayed(f, fault):
    request = pending(f)
    if fault == 'copied_request':
        with pytest.raises((ValueError, RuntimeError)):
            f.account.observe(replace(request), 'pulse_start')
        assert f.root.snapshot()['reserved_pulses'] == 0
        return
    if fault == 'wrong_pending':
        f.session.pending = replace(request)
        with pytest.raises((ValueError, RuntimeError)):
            f.account.observe(request, 'pulse_start')
        assert f.root.snapshot()['reserved_pulses'] == 0
        return
    f.account.observe(request, 'pulse_start')
    with pytest.raises((ValueError, RuntimeError)):
        if fault == 'duplicate_start':f.account.observe(request, 'pulse_start')
        elif fault == 'changed_request':
            object.__setattr__(request, 'expires_at', request.expires_at+1.)
            f.account.observe(request, 'pulse_held')
        else:f.root.check(replace(f.account.reservations[-1]))
    assert f.root.snapshot()['reserved_pulses'] == 1 and not f.account.releases


@pytest.mark.parametrize('f', [dict(maximum_seconds=1., maximum_total_hold=.8)], indirect=True)
def test_late_start_deadline_reserves_the_declared_maximum_hold(f):
    request = pending(f)
    f.now = f.root.expires_at-f.bounds.maximum_actual_hold+.001
    with pytest.raises((ValueError, RuntimeError)):
        f.account.observe(request, 'pulse_start')
    assert f.root.snapshot()['reserved_pulses'] == 0 and not f.requests


@pytest.mark.parametrize('f', [dict(maximum_seconds=.9, maximum_total_hold=.8)], indirect=True)
def test_down_deadline_leaves_root_hold_margin_without_renewing_request(f):
    request = pending(f)
    original = request.expires_at
    expiry = f.account.observe(request, 'pulse_start')
    assert expiry == pytest.approx(f.root.expires_at-f.bounds.maximum_actual_hold)
    assert expiry < request.expires_at == original
    assert f.root.snapshot()['reserved_pulses'] == 1


@pytest.mark.parametrize('fault', ('overhold', 'late_release', 'wrong_key', 'cancelled'))
def test_invalid_release_cannot_publish_completion_or_refund_charge(f, fault):
    request = pending(f)
    f.account.observe(request, 'pulse_start')
    start = f.now
    receipt = PulseReceipt(request.probe.key_code, request.probe.seconds,
        start, start+.0002, start+.0002+request.probe.seconds, start+.0004+request.probe.seconds, 'elapsed')
    f.now = receipt.up_completed_at
    f.account.observe(request, 'pulse_end')
    if fault == 'overhold':
        receipt = replace(receipt, up_started_at=start+.201, up_completed_at=start+.202)
        f.now = receipt.up_completed_at
    elif fault == 'late_release':
        f.now = f.root.expires_at+.001
        receipt = replace(receipt, up_completed_at=f.now)
    elif fault == 'wrong_key':receipt = replace(receipt, key_code=105)
    else:receipt = replace(receipt, completion='interrupted')
    with pytest.raises((ValueError, RuntimeError)):
        f.account.released(request, ReleasedPulse(receipt, f.now))
    assert f.root.snapshot()['reserved_pulses'] == 1 and not f.account.releases
    with pytest.raises(ValueError):
        _ = f.account.complete


def configure_pipe(h, tmp_path, monkeypatch, **limits):
    h.seed()
    h.source = source_reader(h.log, tmp_path/'InitialZoneNames.txt', h.append, time.monotonic)
    h.account = None
    h.root = root_budget(clock=time.monotonic, lock=h.engine.g0_stop_lock, **limits)
    def account(pending, session):
        h.account = InitialItineraryMeasurement(session, h.root,
            bounds=replace(ordinary_bounds(), forward_speed_upper_bound=40.),
            bounds_basis=encoded({'kind':'synthetic-owner-initial-hypotheses'}), source_reader=h.source)
        return h.account
    monkeypatch.setattr(h.engine, '_supervised_measurement_account', account)
    feedback(h, monkeypatch)


def test_owner_hook_all_seven_pipe_pulses_share_root_and_location_deadline(pipe, tmp_path, monkeypatch):
    import eql_automation.supervised_motion as module
    h = pipe
    configure_pipe(h, tmp_path, monkeypatch)
    original = module.send_location_hotkey
    deadlines = []
    def location(*args, **kwargs):
        deadlines.append(kwargs['release_deadline'])
        return original(*args, **kwargs)
    monkeypatch.setattr(module, 'send_location_hotkey', location)
    h.motion();h.motion_due()
    result = complete(h, timeout=20)
    assert result['outcome'] == 'complete', (result['reason'], h.notices)
    assert h.account.complete and len(h.account.releases) == 7
    assert h.root.snapshot()['reserved_pulses'] == 7
    assert deadlines == [h.root.expires_at]*16
    downs = [code for kind, code, value in h.events if kind == 1 and value == 1]
    assert [code for code in downs if code != 62] == [103,106,103,106,103,105,103]
    assert all((1,code,0) in h.events for code in set(downs)) and not h.sender.held


def test_root_exhaustion_blocks_first_movement_down_in_actual_pipe(pipe, tmp_path, monkeypatch):
    h = pipe
    configure_pipe(h, tmp_path, monkeypatch, maximum_total_hold=.19)
    h.motion();h.motion_due()
    result = complete(h)
    assert result['outcome'] == 'stopped'
    assert h.root.snapshot()['reserved_pulses'] == 0
    assert not any(kind == 1 and value == 1 and code in (103,105,106) for kind,code,value in h.events)
    assert not h.sender.held and not h.account.releases


@pytest.mark.parametrize('deadline', ('permit', 'root'))
def test_delayed_selected_pulse_cannot_send_down_after_deadline(pipe, tmp_path, monkeypatch, deadline):
    import eql_automation.motion_executors as module
    h = pipe
    configure_pipe(h, tmp_path, monkeypatch, maximum_seconds=3.)
    original = module.selected_key_pulse_receipt
    selected = []
    def delayed(fd, select, **options):
        def delayed_select():
            permit = select()
            selected.append(permit)
            assert h.root.snapshot()['reserved_pulses'] == 1
            expires = permit.expires_at if deadline == 'permit' else h.root.expires_at
            time.sleep(max(0., expires-time.monotonic())+.01)
            return permit
        return original(fd, delayed_select, **options)
    monkeypatch.setattr(module, 'selected_key_pulse_receipt', delayed)
    h.motion();h.motion_due()
    result = complete(h)
    assert selected and result['outcome'] == 'stopped'
    assert h.root.snapshot()['reserved_pulses'] == 1
    assert not any(kind == 1 and value == 1 and code in (103,105,106) for kind,code,value in h.events)
    assert not h.sender.held and not h.account.releases


@pytest.mark.parametrize('fault', ('cancel', 'stage'))
def test_root_revocation_after_actual_down_always_releases(pipe, tmp_path, monkeypatch, fault):
    h = pipe
    configure_pipe(h, tmp_path, monkeypatch)
    revoked = []
    def revoke():
        driver = h.engine.motion_collection_driver
        if revoked or driver is None or driver.session.phase != 'pulsing':return
        revoked.append(True)
        if fault == 'cancel':h.root.cancel('F9 root cancellation during initial measurement')
        else:h.root.advance(h.root.stage, 'crossing', zone_id=68)
    after_down(monkeypatch, revoke)
    h.motion();h.motion_due()
    result = complete(h)
    assert revoked and result['outcome'] == 'stopped'
    assert (1,103,1) in h.events and (1,103,0) in h.events
    assert not h.sender.held and not h.account.releases
    assert h.root.snapshot()['reserved_pulses'] == 1
